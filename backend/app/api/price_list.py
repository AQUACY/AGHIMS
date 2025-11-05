"""
Price list management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Response
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
import csv
import io
from app.core.database import get_db
from app.core.dependencies import require_role, get_current_user
from app.models.user import User
from app.models.icd10_drg_mapping import ICD10DRGMapping
from app.models.procedure_price import ProcedurePrice
from app.models.surgery_price import SurgeryPrice
from app.models.unmapped_drg_price import UnmappedDRGPrice
from app.models.product_price import ProductPrice
from app.services.price_list_service_v2 import (
    parse_excel_price_list_complete,
    upload_procedure_prices,
    upload_surgery_prices,
    upload_product_prices,
    upload_unmapped_drg_prices,
    search_price_items_all_tables
)

router = APIRouter(prefix="/price-list", tags=["price-list"])
class PriceItemUpdate(BaseModel):
    # Common
    service_name: Optional[str] = None
    service_type: Optional[str] = None
    base_rate: Optional[float] = None
    nhia_app: Optional[float] = None
    nhia_claim_co_payment: Optional[float] = None
    is_active: Optional[bool] = None
    # Product-specific
    product_name: Optional[str] = None
    claim_amount: Optional[float] = None
    insurance_covered: Optional[str] = None  # "yes" or "no"

@router.put("/item/{file_type}/{item_id}")
def update_price_item(
    file_type: str,  # procedure, surgery, product, unmapped_drg
    item_id: int,
    update: PriceItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Update a single price list item by type and id (Admin only)"""
    valid_types = ["procedure", "surgery", "product", "unmapped_drg"]
    if file_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid file_type. Must be one of: {', '.join(valid_types)}")
    
    if file_type == "product":
        item = db.query(ProductPrice).filter(ProductPrice.id == item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Product price item not found")
        
        # Update fields
        if update.product_name is not None:
            item.product_name = update.product_name
        if update.base_rate is not None:
            item.base_rate = update.base_rate
        if update.nhia_app is not None:
            item.nhia_app = update.nhia_app
        if update.nhia_claim_co_payment is not None:
            item.nhia_claim_co_payment = update.nhia_claim_co_payment
        if update.claim_amount is not None:
            item.claim_amount = update.claim_amount
        if update.insurance_covered is not None:
            item.insurance_covered = update.insurance_covered
        if update.is_active is not None:
            item.is_active = update.is_active
    
    elif file_type == "procedure":
        item = db.query(ProcedurePrice).filter(ProcedurePrice.id == item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Procedure price item not found")
        
        if update.service_name is not None:
            item.service_name = update.service_name
        if update.service_type is not None:
            item.service_type = update.service_type
        if update.base_rate is not None:
            item.base_rate = update.base_rate
        if update.nhia_app is not None:
            item.nhia_app = update.nhia_app
        if update.nhia_claim_co_payment is not None:
            item.nhia_claim_co_payment = update.nhia_claim_co_payment
        if update.is_active is not None:
            item.is_active = update.is_active
    
    elif file_type == "surgery":
        item = db.query(SurgeryPrice).filter(SurgeryPrice.id == item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Surgery price item not found")
        
        if update.service_name is not None:
            item.service_name = update.service_name
        if update.service_type is not None:
            item.service_type = update.service_type
        if update.base_rate is not None:
            item.base_rate = update.base_rate
        if update.nhia_app is not None:
            item.nhia_app = update.nhia_app
        if update.nhia_claim_co_payment is not None:
            item.nhia_claim_co_payment = update.nhia_claim_co_payment
        if update.is_active is not None:
            item.is_active = update.is_active
    
    elif file_type == "unmapped_drg":
        item = db.query(UnmappedDRGPrice).filter(UnmappedDRGPrice.id == item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Unmapped DRG price item not found")
        
        if update.service_name is not None:
            item.service_name = update.service_name
        if update.service_type is not None:
            item.service_type = update.service_type
        if update.base_rate is not None:
            item.base_rate = update.base_rate
        if update.nhia_app is not None:
            item.nhia_app = update.nhia_app
        if update.nhia_claim_co_payment is not None:
            item.nhia_claim_co_payment = update.nhia_claim_co_payment
        if update.is_active is not None:
            item.is_active = update.is_active
    
    db.commit()
    db.refresh(item)
    return {"message": f"Successfully updated {file_type} item", "item_id": item_id}


@router.post("/upload/icd10-mapping", status_code=status.HTTP_200_OK)
async def upload_icd10_drg_mapping(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """
    Upload ICD-10 to DRG code mapping from CSV file
    
    CSV should have columns:
    DRG Code, DRG Description, ICD-10 Code, ICD-10 Description, Notes, Remarks
    
    This will create mappings between ICD-10 codes and existing DRG codes
    without modifying any prices in the price list tables.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV file")
    
    # Read CSV content
    content = await file.read()
    try:
        text_content = content.decode('utf-8')
    except UnicodeDecodeError:
        try:
            text_content = content.decode('latin-1')
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="Unable to decode CSV file. Please ensure it's UTF-8 or Latin-1 encoded.")
    
    # Parse CSV
    csv_reader = csv.DictReader(io.StringIO(text_content))
    
    # Get CSV column names for debugging and normalization
    fieldnames = csv_reader.fieldnames
    if not fieldnames:
        raise HTTPException(status_code=400, detail="CSV file appears to be empty or invalid")
    
    # Normalize column names - strip whitespace and handle BOM
    normalized_columns = {}
    for col in fieldnames:
        normalized = col.strip().strip('\ufeff')  # Strip BOM if present
        normalized_columns[normalized] = col
    
    print(f"CSV columns found: {fieldnames}")
    print(f"Normalized columns: {list(normalized_columns.keys())}")
    
    # Helper function to find column by multiple possible names (case-insensitive, handles spaces)
    def find_column_key(row_dict, possible_names):
        """Find the actual key in the row dict that matches one of the possible names"""
        for possible_name in possible_names:
            possible_lower = possible_name.lower().strip()
            for actual_key in row_dict.keys():
                if actual_key.lower().strip() == possible_lower:
                    return actual_key
        return None
    
    # Validate CSV has data rows
    csv_reader = csv.DictReader(io.StringIO(text_content))
    row_count = sum(1 for row in csv_reader)
    
    if row_count == 0:
        raise HTTPException(status_code=400, detail="CSV file appears to have no data rows")
    
    # Create a test reader to check first data row
    test_reader = csv.DictReader(io.StringIO(text_content))
    test_row = next(test_reader, None)
    if test_row is None:
        raise HTTPException(status_code=400, detail="CSV file has no data rows")
    
    # Check if we can find DRG Code column (including d_drg_code variant)
    drg_code_test = find_column_key(test_row, ['DRG Code', 'drg_code', 'DRG_Code', 'drg code', 'DRGCODE', 'd_drg_code', 'D_DRG_Code', 'D_DRG_CODE'])
    if not drg_code_test:
        raise HTTPException(
            status_code=400,
            detail=f"Could not find 'DRG Code' column. Available columns: {list(test_row.keys())}. Please ensure your CSV has a 'DRG Code' column."
        )
    
    # Reset CSV reader to start from beginning
    csv_reader = csv.DictReader(io.StringIO(text_content))
    
    results = {
        "success": [],
        "errors": [],
        "total": 0,
        "skipped_no_drg": 0,
        "summary": ""
    }
    
    row_num = 0
    for row in csv_reader:
        row_num += 1
        results["total"] += 1
        
        try:
            # Extract fields with multiple possible column names
            drg_code = find_column_key(row, ['DRG Code', 'drg_code', 'DRG_Code', 'drg code', 'DRGCODE', 'd_drg_code', 'D_DRG_Code', 'D_DRG_CODE'])
            drg_description = find_column_key(row, ['DRG Description', 'drg_description', 'DRG_Description', 'drg description', 'DRGDESCRIPTION'])
            icd10_code = find_column_key(row, ['ICD-10 Code', 'ICD10 Code', 'icd10_code', 'ICD10_Code', 'icd-10 code', 'ICD10CODE', 'ICD10'])
            icd10_description = find_column_key(row, ['ICD-10 Description', 'ICD10 Description', 'icd10_description', 'ICD10_Description', 'icd-10 description', 'ICD10DESCRIPTION'])
            notes = find_column_key(row, ['Notes', 'notes', 'NOTES', 'Note', 'note'])
            remarks = find_column_key(row, ['Remarks', 'remarks', 'REMARKS', 'Remark', 'remark'])
            
            # Skip rows without DRG code
            if not drg_code or not row.get(drg_code) or not str(row[drg_code]).strip():
                results["skipped_no_drg"] += 1
                results["errors"].append({
                    "row": row_num,
                    "error": "Skipped (no DRG code)"
                })
                continue
            
            drg_code_value = str(row[drg_code]).strip()
            drg_desc_value = row.get(drg_description, '').strip() if drg_description else ''
            icd10_code_value = row.get(icd10_code, '').strip() if icd10_code else ''
            icd10_desc_value = row.get(icd10_description, '').strip() if icd10_description else ''
            notes_value = row.get(notes, '').strip() if notes else ''
            remarks_value = row.get(remarks, '').strip() if remarks else ''
            
            # Skip rows without ICD-10 code
            if not icd10_code_value:
                results["skipped_no_drg"] += 1
                results["errors"].append({
                    "row": row_num,
                    "error": "Skipped (no ICD-10 code)"
                })
                continue
            
            # Check if mapping already exists
            existing = db.query(ICD10DRGMapping).filter(
                ICD10DRGMapping.drg_code == drg_code_value,
                ICD10DRGMapping.icd10_code == icd10_code_value
            ).first()
            
            if existing:
                # Update existing mapping
                existing.drg_description = drg_desc_value if drg_desc_value else existing.drg_description
                existing.icd10_description = icd10_desc_value if icd10_desc_value else existing.icd10_description
                existing.notes = notes_value if notes_value else existing.notes
                existing.remarks = remarks_value if remarks_value else existing.remarks
                existing.is_active = True
            else:
                # Create new mapping
                new_mapping = ICD10DRGMapping(
                    drg_code=drg_code_value,
                    drg_description=drg_desc_value,
                    icd10_code=icd10_code_value,
                    icd10_description=icd10_desc_value,
                    notes=notes_value,
                    remarks=remarks_value,
                    is_active=True
                )
                db.add(new_mapping)
            
            results["success"].append({
                "row": row_num,
                "drg_code": drg_code_value,
                "icd10_code": icd10_code_value
            })
            
        except Exception as e:
            results["errors"].append({
                "row": row_num,
                "error": str(e)
            })
    
    try:
        db.commit()
        results["summary"] = f"Total rows: {results['total']}, Successfully imported: {len(results['success'])}, Failed: {len(results['errors'])}"
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to commit mappings: {str(e)}"
        )
    
    return results


@router.post("/upload/{file_type}")
async def upload_price_list_file(
    file_type: str,  # procedure, surgery, product, unmapped_drg
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Billing"]))
):
    """Upload Excel price list file by file type"""
    # Validate file type
    valid_types = ["procedure", "surgery", "product", "unmapped_drg"]
    if file_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Must be one of: {', '.join(valid_types)}"
        )
    
    # Validate file type
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="File must be an Excel file (.xlsx or .xls)"
        )
    
    try:
        # Parse Excel file (extracts all columns, uses Service Type as category)
        # The parse function handles file reading internally to avoid seekable() issues
        items = parse_excel_price_list_complete(file, file_type)
        
        # Upload to appropriate table based on file type
        if file_type == "procedure":
            upload_procedure_prices(db, items)
        elif file_type == "surgery":
            upload_surgery_prices(db, items)
        elif file_type == "product":
            upload_product_prices(db, items)
        elif file_type == "unmapped_drg":
            upload_unmapped_drg_prices(db, items)
        
        return {
            "message": f"Successfully uploaded {len(items)} items to {file_type} table",
            "file_type": file_type,
            "count": len(items)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}"
        )


@router.get("/search")
def search_price_items_endpoint(
    search_term: Optional[str] = None,
    service_type: Optional[str] = None,  # Service Type (department/clinic) filter
    file_type: Optional[str] = None,  # Filter by file type: procedure, surgery, product, unmapped_drg
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Billing", "Doctor", "Admin"]))
):
    """Search price list items across all tables"""
    results = search_price_items_all_tables(db, search_term, service_type, file_type)
    
    # Format results
    formatted_results = []
    for type_name, item in results:
        # Handle products differently (they have different field names)
        if type_name == 'product':
            cash_price = float(item.base_rate) if item.base_rate else 0.0
            nhia_app = float(item.nhia_app) if item.nhia_app else None
            nhia_claim_co_payment = float(item.nhia_claim_co_payment) if item.nhia_claim_co_payment is not None else None
            # For products: insured patients pay Co-Payment if available, otherwise Base Rate
            co_payment = nhia_claim_co_payment if nhia_claim_co_payment is not None else cash_price
            
            result_item = {
                "id": item.id,
                "file_type": type_name,
                "medication_code": item.medication_code,
                "product_name": item.product_name,
                "product_id": item.product_id,
                "sub_category_1": item.sub_category_1,
                "sub_category_2": item.sub_category_2,
                "formulation": item.formulation,
                "strength": item.strength,
                "base_rate": cash_price,
                "nhia_app": nhia_app,
                "nhia_claim_co_payment": nhia_claim_co_payment,
                "claim_amount": float(item.claim_amount) if item.claim_amount else None,
                "nhia_claim": item.nhia_claim,
                "bill_effective": item.bill_effective,
                "insurance_covered": item.insurance_covered or "yes",  # Include insurance_covered field
                "is_active": item.is_active,  # Include is_active field
                # For backward compatibility with billing page
                "g_drg_code": item.medication_code,  # Map medication_code to g_drg_code
                "service_name": item.product_name,  # Map product_name to service_name
                "service_type": item.sub_category_1 or item.sub_category_2,  # Use sub_category as service_type
                "item_code": item.medication_code,
                "item_name": item.product_name,
                "category": item.sub_category_1 or item.sub_category_2 or type_name,
                "cash_price": cash_price,
                "insured_price": co_payment,  # Products: Co-Payment for insured if available, else Base Rate
                # Additional fields
                "sr_no": item.sr_no,
            }
        else:
            # Procedure, Surgery, UnmappedDRG format
            cash_price = float(item.base_rate) if item.base_rate else 0.0
            nhia_app = float(item.nhia_app) if item.nhia_app else None
            nhia_claim_co_payment = float(item.nhia_claim_co_payment) if item.nhia_claim_co_payment is not None else None
            
            result_item = {
                "id": item.id,
                "file_type": type_name,
                "g_drg_code": item.g_drg_code,
                "service_name": item.service_name,
                "service_type": item.service_type,
                "base_rate": cash_price,
                "nhia_app": nhia_app,
                "nhia_claim_co_payment": nhia_claim_co_payment,
                "is_active": item.is_active,
                # For backward compatibility with billing page
                "item_code": item.g_drg_code,
                "item_name": item.service_name,
                "category": item.service_type or type_name,
                "cash_price": cash_price,
                "insured_price": nhia_claim_co_payment if nhia_claim_co_payment is not None else cash_price,
            }
        
        formatted_results.append(result_item)
    
    return formatted_results


@router.get("/procedures/by-service-type")
def get_procedures_by_service_type(
    service_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Billing", "Doctor", "Admin", "Records", "PA", "Nurse", "Pharmacy", "Lab", "Scan", "Xray", "Claims"]))
):
    """Get procedures grouped by service type. If service_type is provided, returns array. Otherwise returns grouped object."""
    from sqlalchemy import func
    
    if service_type:
        # When a specific service_type is provided, return a simple array
        procedures = db.query(ProcedurePrice).filter(
            ProcedurePrice.service_type == service_type,
            ProcedurePrice.is_active == True
        ).all()
        
        # Return as array
        return [
            {
                "id": proc.id,
                "g_drg_code": proc.g_drg_code,
                "service_name": proc.service_name,
                "base_rate": float(proc.base_rate) if proc.base_rate else 0.0,
                "nhia_app": float(proc.nhia_app) if proc.nhia_app else None,
                "nhia_claim_co_payment": float(proc.nhia_claim_co_payment) if proc.nhia_claim_co_payment is not None else None,
            }
            for proc in procedures
        ]
    else:
        # When no service_type is provided, return grouped by service_type
        procedures = db.query(ProcedurePrice).filter(
            ProcedurePrice.is_active == True
        ).all()
        
        # Group by service_type
        grouped = {}
        for proc in procedures:
            st = proc.service_type or "Unknown"
            if st not in grouped:
                grouped[st] = []
            grouped[st].append({
                "id": proc.id,
                "g_drg_code": proc.g_drg_code,
                "service_name": proc.service_name,
                "base_rate": float(proc.base_rate) if proc.base_rate else 0.0,
                "nhia_app": float(proc.nhia_app) if proc.nhia_app else None,
                "nhia_claim_co_payment": float(proc.nhia_claim_co_payment) if proc.nhia_claim_co_payment is not None else None,
            })
        
        return grouped


@router.get("/service-types")
def get_service_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Allow all authenticated users
):
    """Get all unique service types from procedure prices"""
    from sqlalchemy import distinct
    
    service_types = db.query(distinct(ProcedurePrice.service_type)).filter(
        ProcedurePrice.service_type.isnot(None),
        ProcedurePrice.is_active == True
    ).all()
    
    return [st[0] for st in service_types if st[0]]


@router.get("/icd10/search")
def search_icd10_codes(
    search_term: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Doctor", "Billing", "Admin", "Records", "PA", "Nurse", "Pharmacy", "Lab", "Scan", "Xray", "Claims"]))
):
    """Search ICD-10 codes"""
    from sqlalchemy import or_
    
    query = db.query(ICD10DRGMapping).filter(ICD10DRGMapping.is_active == True)
    
    if search_term:
        search_filter = or_(
            ICD10DRGMapping.icd10_code.ilike(f"%{search_term}%"),
            ICD10DRGMapping.icd10_description.ilike(f"%{search_term}%")
        )
        query = query.filter(search_filter)
    
    mappings = query.distinct(ICD10DRGMapping.icd10_code).limit(limit).all()
    
    results = []
    seen_codes = set()
    for mapping in mappings:
        if mapping.icd10_code not in seen_codes:
            seen_codes.add(mapping.icd10_code)
            results.append({
                "icd10_code": mapping.icd10_code,
                "icd10_description": mapping.icd10_description or "",
                "drg_codes": []
            })
    
    # Get DRG codes for each ICD-10 code
    for result in results:
        drg_mappings = db.query(ICD10DRGMapping).filter(
            ICD10DRGMapping.icd10_code == result["icd10_code"],
            ICD10DRGMapping.is_active == True
        ).distinct(ICD10DRGMapping.drg_code).all()
        
        result["drg_codes"] = [m.drg_code for m in drg_mappings]
    
    return results


@router.get("/icd10/{icd10_code}/drg-codes")
def get_drg_codes_from_icd10(
    icd10_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Doctor", "Billing", "Admin"]))
):
    """Get all DRG codes mapped to a specific ICD-10 code"""
    from app.models.icd10_drg_mapping import ICD10DRGMapping
    
    mappings = db.query(ICD10DRGMapping).filter(
        ICD10DRGMapping.icd10_code == icd10_code,
        ICD10DRGMapping.is_active == True
    ).distinct(ICD10DRGMapping.drg_code).all()
    
    if not mappings:
        return []
    
    results = []
    for mapping in mappings:
        results.append({
            "drg_code": mapping.drg_code,
            "drg_description": mapping.drg_description or "",
            "icd10_code": mapping.icd10_code,
            "icd10_description": mapping.icd10_description or ""
        })
    
    return results


@router.get("/export/product/csv")
def export_product_price_list_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Billing"]))
):
    """Export product price list as CSV file"""
    # Query all product prices
    products = db.query(ProductPrice).filter(ProductPrice.is_active == True).order_by(ProductPrice.product_name).all()
    
    if not products:
        raise HTTPException(status_code=404, detail="No product prices found")
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header row
    writer.writerow([
        'Product N',  # Product Name with embedded code
        'Medication Code',
        'Product Name',
        'Sub Category 1',
        'Sub Category 2',
        'Product ID',
        'Formulation',
        'Strength',
        'Base Rate',
        'NHIA App',
        'NHIA Claim Co-Payment',
        'Claim Amount',
        'NHIA Claim',
        'Bill Effective',
        'Insurance Covered',
        'Is Active'
    ])
    
    # Write data rows
    for product in products:
        # Reconstruct the Product N format: "Product Name (Code) (CODE | Product Name)"
        product_n = product.product_name
        if product.medication_code:
            # If product_name doesn't already contain the code format, construct it
            if f"({product.medication_code}" not in product.product_name:
                product_n = f"{product.product_name} ({product.medication_code} | {product.product_name})"
        
        writer.writerow([
            product_n,
            product.medication_code or '',
            product.product_name or '',
            product.sub_category_1 or '',
            product.sub_category_2 or '',
            product.product_id or '',
            product.formulation or '',
            product.strength or '',
            product.base_rate or 0.0,
            product.nhia_app or '',
            product.nhia_claim_co_payment or '',
            product.claim_amount or '',
            product.nhia_claim or '',
            product.bill_effective or '',
            product.insurance_covered or 'yes',  # Default to 'yes' if not set
            'True' if product.is_active else 'False'
        ])
    
    # Get CSV content
    csv_content = output.getvalue()
    output.close()
    
    # Return CSV file
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=product_price_list.csv"
        }
    )

