"""
Price list management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
import csv
import io
from app.core.database import get_db
from app.core.dependencies import require_role
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
        raise HTTPException(status_code=400, detail="Invalid file type")

    if file_type == "procedure":
        from app.models.procedure_price import ProcedurePrice as Model
    elif file_type == "surgery":
        from app.models.surgery_price import SurgeryPrice as Model
    elif file_type == "product":
        from app.models.product_price import ProductPrice as Model
    else:
        from app.models.unmapped_drg_price import UnmappedDRGPrice as Model

    item = db.query(Model).filter(Model.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    data = update.dict(exclude_unset=True)
    # Map product_name to appropriate field
    if file_type == "product" and "service_name" in data:
        data.pop("service_name")
    if file_type != "product" and "product_name" in data:
        data.pop("product_name")

    # Apply updates to existing fields only
    for key, value in data.items():
        if hasattr(item, key):
            # Handle None values explicitly - allow setting to None for nullable fields
            setattr(item, key, value)
        else:
            # Map common names to model columns where they differ
            if file_type == "product" and key == "product_name" and hasattr(item, "product_name"):
                setattr(item, "product_name", value)
            elif key == "service_name" and hasattr(item, "service_name"):
                setattr(item, "service_name", value)
            elif key == "service_type" and hasattr(item, "service_type"):
                setattr(item, "service_type", value)

    db.commit()
    db.refresh(item)
    return {"message": "Item updated", "id": item.id}


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
        except:
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
    
    # Debug: Log column names found
    print(f"CSV columns found: {fieldnames}")
    print(f"Normalized columns: {list(normalized_columns.keys())}")
    
    # Helper function to find column by multiple possible names (case-insensitive, handles spaces)
    def find_column_key(row_dict, possible_names):
        """Find the actual key in the row dict that matches one of the possible names"""
        row_keys = list(row_dict.keys())
        for possible in possible_names:
            # Try exact match
            if possible in row_keys:
                return possible
            # Try case-insensitive match
            for key in row_keys:
                key_normalized = key.strip().lower()
                possible_normalized = possible.strip().lower()
                if key_normalized == possible_normalized:
                    return key
        # Fallback: try to find any column containing keywords
        if 'drg' in str(possible_names).lower():
            for key in row_keys:
                if 'drg' in key.lower() and 'code' in key.lower():
                    return key
        return None
    
    # Verify we can find required columns by reading first row
    first_row_position = text_content.find('\n')
    if first_row_position == -1:
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
        "imported": 0,
        "failed": 0,
        "skipped_no_drg": 0,
        "skipped_no_icd10": 0
    }
    
    # Get all existing DRG codes from all price tables
    all_drg_codes = set()
    
    # Get DRG codes from procedures
    procedure_codes = db.query(ProcedurePrice.g_drg_code).filter(
        ProcedurePrice.is_active == True
    ).distinct().all()
    all_drg_codes.update([code[0] for code in procedure_codes if code[0]])
    
    # Get DRG codes from surgeries
    surgery_codes = db.query(SurgeryPrice.g_drg_code).filter(
        SurgeryPrice.is_active == True
    ).distinct().all()
    all_drg_codes.update([code[0] for code in surgery_codes if code[0]])
    
    # Get DRG codes from unmapped DRG
    unmapped_codes = db.query(UnmappedDRGPrice.g_drg_code).filter(
        UnmappedDRGPrice.is_active == True
    ).distinct().all()
    all_drg_codes.update([code[0] for code in unmapped_codes if code[0]])
    
    # Get medication codes from products (also considered DRG codes)
    product_codes = db.query(ProductPrice.medication_code).filter(
        ProductPrice.is_active == True
    ).distinct().all()
    all_drg_codes.update([code[0] for code in product_codes if code[0]])
    
    # Helper function to get field value with multiple possible names
    def get_field(row, possible_names, default=''):
        # First try to find the actual column key
        found_key = find_column_key(row, possible_names)
        if found_key and found_key in row:
            value = row[found_key]
            if value is not None and str(value).strip():
                return str(value).strip()
        return default
    
    # Process each row
    # Note: row_num starts at 2 because row 1 is the header
    row_num = 1
    for row in csv_reader:
        row_num += 1
        results["total"] += 1
        
        try:
            # Extract fields with multiple possible column names
            drg_code = get_field(row, ['DRG Code', 'drg_code', 'DRG_Code', 'drg code', 'DRGCODE', 'd_drg_code', 'D_DRG_Code', 'D_DRG_CODE'])
            drg_description = get_field(row, ['DRG Description', 'drg_description', 'DRG_Description', 'drg description', 'DRGDESCRIPTION', 'd_drg_description'], default=None)
            icd10_code = get_field(row, ['ICD-10 Code', 'icd10_code', 'ICD_10_Code', 'icd-10 code', 'ICD10CODE', 'ICD-10', 'ICD10'])
            icd10_description = get_field(row, ['ICD-10 Description', 'icd10_description', 'ICD_10_Description', 'icd-10 description', 'ICD10DESCRIPTION'], default=None)
            notes = get_field(row, ['Notes', 'notes', 'NOTES'], default=None)
            remarks = get_field(row, ['Remarks', 'remarks', 'REMARKS'], default=None)
            
            # Clean up None values to empty strings for validation
            drg_code = drg_code or ''
            icd10_code = icd10_code or ''
            
            # Validate required fields
            if not drg_code:
                results["skipped_no_drg"] += 1
                # Debug: Log first few rows with missing DRG codes
                if row_num <= 5:
                    print(f"Row {row_num} - Column names in row: {list(row.keys())}")
                    print(f"Row {row_num} - Raw row data: {row}")
                    # Try to find any column that might be DRG code
                    for key in row.keys():
                        if 'drg' in key.lower():
                            print(f"  Found potential DRG column '{key}' with value: '{row[key]}'")
                # Only add detailed error for first few rows to avoid huge response
                if len(results["errors"]) < 10:
                    results["errors"].append({
                        "row": row_num,
                        "error": f"DRG Code is missing or empty. Available columns: {list(row.keys())}",
                        "data": dict(row)
                    })
                continue
            
            if not icd10_code:
                results["skipped_no_icd10"] += 1
                # Skip rows without ICD-10 codes (as per user request)
                continue
            
            # Check if DRG code exists in any price table
            if drg_code not in all_drg_codes:
                # DRG code doesn't exist in price tables - create mapping anyway
                # (might be used later or in claims)
                pass
            
            # Check if this mapping already exists
            existing_mapping = db.query(ICD10DRGMapping).filter(
                ICD10DRGMapping.drg_code == drg_code,
                ICD10DRGMapping.icd10_code == icd10_code
            ).first()
            
            if existing_mapping:
                # Update existing mapping
                existing_mapping.drg_description = drg_description or existing_mapping.drg_description
                existing_mapping.icd10_description = icd10_description or existing_mapping.icd10_description
                existing_mapping.notes = notes or existing_mapping.notes
                existing_mapping.remarks = remarks or existing_mapping.remarks
                existing_mapping.is_active = True
                
                results["success"].append({
                    "row": row_num,
                    "drg_code": drg_code,
                    "icd10_code": icd10_code,
                    "action": "updated",
                    "id": existing_mapping.id
                })
            else:
                # Create new mapping
                mapping = ICD10DRGMapping(
                    drg_code=drg_code,
                    drg_description=drg_description,
                    icd10_code=icd10_code,
                    icd10_description=icd10_description,
                    notes=notes,
                    remarks=remarks,
                    is_active=True
                )
                
                db.add(mapping)
                db.flush()
                
                results["success"].append({
                    "row": row_num,
                    "drg_code": drg_code,
                    "icd10_code": icd10_code,
                    "action": "created",
                    "id": mapping.id
                })
            
            results["imported"] += 1
            
        except Exception as e:
            results["errors"].append({
                "row": row_num,
                "error": str(e),
                "data": row
            })
            results["failed"] += 1
            continue
    
    # Commit all successful imports
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to commit mappings: {str(e)}")
    
    return results


@router.post("/upload/{file_type}")
def upload_price_list_file(
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
            status_code=400,
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
            # For insured patients: they pay the Co-Payment (top-up amount)
            # If Co-Payment is not available, fall back to base_rate
            co_payment = float(item.nhia_claim_co_payment) if item.nhia_claim_co_payment is not None else cash_price
            nhia_app = float(item.nhia_app) if item.nhia_app else None
            
            result_item = {
                "id": item.id,
                "file_type": type_name,
                "g_drg_code": item.g_drg_code,
                "service_name": item.service_name,
                "service_type": item.service_type,  # Department/Clinic (category)
                "service_id": item.service_id,
                "base_rate": cash_price,
                "nhia_app": nhia_app,
                "nhia_claim_co_payment": float(item.nhia_claim_co_payment) if item.nhia_claim_co_payment else None,
                # For backward compatibility with billing page
                "item_code": item.g_drg_code,
                "item_name": item.service_name,
                "category": item.service_type or type_name,
                "cash_price": cash_price,  # Base Rate for cash patients
                "insured_price": co_payment,  # Co-Payment for insured patients (top-up amount)
                # Additional fields
                "service_ty": item.service_ty,
                "sr_no": item.sr_no,
                "clinic_bill_effective": item.clinic_bill_effective,
            }
        formatted_results.append(result_item)
    
    return formatted_results


@router.get("/procedures/by-service-type")
def get_procedures_by_service_type(
    service_type: str,  # Service Type (department/clinic)
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Doctor", "Billing", "Admin"]))
):
    """Get all procedures for a specific service type (department/clinic)"""
    from app.models.procedure_price import ProcedurePrice
    
    procedures = db.query(ProcedurePrice).filter(
        ProcedurePrice.service_type == service_type,
        ProcedurePrice.is_active == True
    ).order_by(ProcedurePrice.service_name).all()
    
    return [{
        "id": item.id,
        "g_drg_code": item.g_drg_code,
        "service_name": item.service_name,
        "service_type": item.service_type,
        "service_id": item.service_id,
        "base_rate": float(item.base_rate) if item.base_rate else 0.0,
        "nhia_app": float(item.nhia_app) if item.nhia_app else None,
        "nhia_claim_co_payment": float(item.nhia_claim_co_payment) if item.nhia_claim_co_payment else None,
    } for item in procedures]


@router.get("/service-types")
def get_all_service_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Doctor", "Billing", "Admin"]))
):
    """Get all unique service types (departments/clinics) from procedures"""
    from app.models.procedure_price import ProcedurePrice
    from sqlalchemy import distinct
    
    service_types = db.query(distinct(ProcedurePrice.service_type)).filter(
        ProcedurePrice.service_type.isnot(None),
        ProcedurePrice.service_type != '',
        ProcedurePrice.is_active == True
    ).order_by(ProcedurePrice.service_type).all()
    
    return [st[0] for st in service_types if st[0]]


@router.get("/icd10/search")
def search_icd10_codes(
    search_term: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Doctor", "Billing", "Admin"]))
):
    """Search ICD-10 codes from the mapping table"""
    from app.models.icd10_drg_mapping import ICD10DRGMapping
    
    query = db.query(ICD10DRGMapping).filter(
        ICD10DRGMapping.is_active == True
    )
    
    if search_term:
        search_term = search_term.strip()
        query = query.filter(
            (ICD10DRGMapping.icd10_code.contains(search_term)) |
            (ICD10DRGMapping.icd10_description.contains(search_term)) |
            (ICD10DRGMapping.drg_code.contains(search_term))
        )
    
    # Get distinct ICD-10 codes with their descriptions
    # Group by ICD-10 code to show unique diagnoses
    results = []
    seen_icd10 = set()
    
    for mapping in query.order_by(ICD10DRGMapping.icd10_code, ICD10DRGMapping.icd10_description).limit(limit * 2):
        if mapping.icd10_code and mapping.icd10_code not in seen_icd10:
            seen_icd10.add(mapping.icd10_code)
            results.append({
                "icd10_code": mapping.icd10_code,
                "icd10_description": mapping.icd10_description or "",
                "drg_codes": []  # Will be populated below
            })
            if len(results) >= limit:
                break
    
    # Now get all DRG codes for each ICD-10 code
    for result in results:
        drg_mappings = db.query(ICD10DRGMapping).filter(
            ICD10DRGMapping.icd10_code == result["icd10_code"],
            ICD10DRGMapping.is_active == True
        ).distinct(ICD10DRGMapping.drg_code).all()
        
        result["drg_codes"] = [
            {
                "drg_code": m.drg_code,
                "drg_description": m.drg_description or ""
            }
            for m in drg_mappings
        ]
    
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

