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
class PriceItemCreate(BaseModel):
    """Price item creation model"""
    # Common fields
    g_drg_code: Optional[str] = None  # For procedure, surgery, unmapped_drg
    medication_code: Optional[str] = None  # For product
    service_name: Optional[str] = None
    service_type: Optional[str] = None
    base_rate: float = 0.0
    nhia_app: Optional[float] = None
    nhia_claim_co_payment: Optional[float] = None
    is_active: bool = True
    # Product-specific
    product_name: Optional[str] = None
    sub_category_1: Optional[str] = None
    sub_category_2: Optional[str] = None
    product_id: Optional[str] = None
    formulation: Optional[str] = None
    strength: Optional[str] = None
    claim_amount: Optional[float] = None
    insurance_covered: Optional[str] = "yes"  # "yes" or "no"
    # Optional fields
    sr_no: Optional[str] = None
    service_ty: Optional[str] = None
    service_id: Optional[str] = None
    clinic_bill_effective: Optional[str] = None

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

@router.post("/item/{file_type}")
def create_price_item(
    file_type: str,  # procedure, surgery, product, unmapped_drg
    item_data: PriceItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Pharmacy Head"]))
):
    """Create a new price list item by type (Admin and Pharmacy Head only)"""
    valid_types = ["procedure", "surgery", "product", "unmapped_drg"]
    if file_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid file_type. Must be one of: {', '.join(valid_types)}")
    
    if file_type == "product":
        if not item_data.medication_code:
            raise HTTPException(status_code=400, detail="medication_code is required for products")
        if not item_data.product_name:
            raise HTTPException(status_code=400, detail="product_name is required for products")
        
        # Check if product with same medication_code already exists
        existing = db.query(ProductPrice).filter(ProductPrice.medication_code == item_data.medication_code).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Product with medication_code '{item_data.medication_code}' already exists")
        
        item = ProductPrice(
            medication_code=item_data.medication_code,
            product_name=item_data.product_name,
            sub_category_1=item_data.sub_category_1,
            sub_category_2=item_data.sub_category_2,
            product_id=item_data.product_id,
            formulation=item_data.formulation,
            strength=item_data.strength,
            base_rate=item_data.base_rate,
            nhia_app=item_data.nhia_app,
            nhia_claim_co_payment=item_data.nhia_claim_co_payment if item_data.nhia_claim_co_payment is not None else 0.0,  # Preserve 0.0, default to 0.0 if None
            claim_amount=item_data.claim_amount,
            insurance_covered=item_data.insurance_covered or "yes",
            is_active=item_data.is_active
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return {"message": "Product price item created successfully", "item_id": item.id}
    
    elif file_type in ["procedure", "surgery", "unmapped_drg"]:
        if not item_data.g_drg_code:
            raise HTTPException(status_code=400, detail="g_drg_code is required")
        if not item_data.service_name:
            raise HTTPException(status_code=400, detail="service_name is required")
        
        # Check if item with same g_drg_code and service_type already exists
        if file_type == "procedure":
            existing = db.query(ProcedurePrice).filter(
                ProcedurePrice.g_drg_code == item_data.g_drg_code,
                ProcedurePrice.service_type == item_data.service_type
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail=f"Procedure with g_drg_code '{item_data.g_drg_code}' and service_type '{item_data.service_type}' already exists")
            
            item = ProcedurePrice(
                g_drg_code=item_data.g_drg_code,
                service_type=item_data.service_type,
                service_ty=item_data.service_ty,
                service_id=item_data.service_id,
                service_name=item_data.service_name,
                base_rate=item_data.base_rate,
                nhia_app=item_data.nhia_app,
                nhia_claim_co_payment=item_data.nhia_claim_co_payment if item_data.nhia_claim_co_payment is not None else 0.0,  # Preserve 0.0, default to 0.0 if None
                clinic_bill_effective=item_data.clinic_bill_effective,
                is_active=item_data.is_active,
                sr_no=item_data.sr_no
            )
        elif file_type == "surgery":
            existing = db.query(SurgeryPrice).filter(
                SurgeryPrice.g_drg_code == item_data.g_drg_code,
                SurgeryPrice.service_type == item_data.service_type
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail=f"Surgery with g_drg_code '{item_data.g_drg_code}' and service_type '{item_data.service_type}' already exists")
            
            item = SurgeryPrice(
                g_drg_code=item_data.g_drg_code,
                service_type=item_data.service_type,
                service_ty=item_data.service_ty,
                service_id=item_data.service_id,
                service_name=item_data.service_name,
                base_rate=item_data.base_rate,
                nhia_app=item_data.nhia_app,
                nhia_claim_co_payment=item_data.nhia_claim_co_payment if item_data.nhia_claim_co_payment is not None else 0.0,  # Preserve 0.0, default to 0.0 if None
                clinic_bill_effective=item_data.clinic_bill_effective,
                is_active=item_data.is_active,
                sr_no=item_data.sr_no
            )
        elif file_type == "unmapped_drg":
            existing = db.query(UnmappedDRGPrice).filter(
                UnmappedDRGPrice.g_drg_code == item_data.g_drg_code,
                UnmappedDRGPrice.service_type == item_data.service_type
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail=f"Unmapped DRG with g_drg_code '{item_data.g_drg_code}' and service_type '{item_data.service_type}' already exists")
            
            item = UnmappedDRGPrice(
                g_drg_code=item_data.g_drg_code,
                service_type=item_data.service_type,
                service_ty=item_data.service_ty,
                service_id=item_data.service_id,
                service_name=item_data.service_name,
                base_rate=item_data.base_rate,
                nhia_app=item_data.nhia_app,
                nhia_claim_co_payment=item_data.nhia_claim_co_payment if item_data.nhia_claim_co_payment is not None else 0.0,  # Preserve 0.0, default to 0.0 if None
                clinic_bill_effective=item_data.clinic_bill_effective,
                is_active=item_data.is_active,
                sr_no=item_data.sr_no
            )
        
        db.add(item)
        db.commit()
        db.refresh(item)
        return {"message": f"{file_type} price item created successfully", "item_id": item.id}

@router.put("/item/{file_type}/{item_id}")
def update_price_item(
    file_type: str,  # procedure, surgery, product, unmapped_drg
    item_id: int,
    update: PriceItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Pharmacy Head"]))
):
    """Update a single price list item by type and id (Admin and Pharmacy Head only)"""
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
    Upload ICD-10 to DRG code mapping from CSV or Excel file
    
    File should have columns:
    DRG Code, DRG Description, ICD-10 Code, ICD-10 Description, Notes, Remarks
    
    This will:
    - Update existing mappings (matched by DRG Code + ICD-10 Code)
    - Create new mappings for combinations that don't exist
    - Set is_active to True for all imported mappings
    """
    import pandas as pd
    
    is_excel = file.filename.endswith(('.xlsx', '.xls'))
    is_csv = file.filename.endswith('.csv')
    
    if not (is_excel or is_csv):
        raise HTTPException(status_code=400, detail="File must be a CSV or Excel file (.csv, .xlsx, .xls)")
    
    # Read file content
    content = await file.read()
    
    # Parse Excel or CSV
    if is_excel:
        # Read Excel file
        try:
            df = pd.read_excel(io.BytesIO(content), engine='openpyxl')
            # Convert DataFrame to list of dictionaries
            rows = df.to_dict('records')
            # Get column names
            fieldnames = list(df.columns)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error reading Excel file: {str(e)}")
    else:
        # Read CSV
        try:
            text_content = content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                text_content = content.decode('latin-1')
            except UnicodeDecodeError:
                raise HTTPException(status_code=400, detail="Unable to decode CSV file. Please ensure it's UTF-8 or Latin-1 encoded.")
        
        # Parse CSV
        csv_reader = csv.DictReader(io.StringIO(text_content))
        rows = list(csv_reader)
        fieldnames = csv_reader.fieldnames if csv_reader.fieldnames else []
    
    # Validate file has columns
    if not fieldnames:
        raise HTTPException(status_code=400, detail="File appears to be empty or invalid")
    
    # Normalize column names - strip whitespace and handle BOM
    normalized_columns = {}
    for col in fieldnames:
        normalized = col.strip().strip('\ufeff')  # Strip BOM if present
        normalized_columns[normalized] = col
    
    print(f"File columns found: {fieldnames}")
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
    
    # Validate file has data rows
    if len(rows) == 0:
        raise HTTPException(status_code=400, detail="File appears to have no data rows")
    
    # Get first row for validation
    test_row = rows[0] if rows else None
    if test_row is None:
        raise HTTPException(status_code=400, detail="File has no data rows")
    
    # Check if we can find DRG Code column (including d_drg_code variant)
    drg_code_test = find_column_key(test_row, ['DRG Code', 'drg_code', 'DRG_Code', 'drg code', 'DRGCODE', 'd_drg_code', 'D_DRG_Code', 'D_DRG_CODE'])
    if not drg_code_test:
        raise HTTPException(
            status_code=400,
            detail=f"Could not find 'DRG Code' column. Available columns: {list(test_row.keys())}. Please ensure your CSV has a 'DRG Code' column."
        )
    
    results = {
        "success": [],
        "errors": [],
        "total": 0,
        "skipped_no_drg": 0,
        "summary": ""
    }
    
    row_num = 0
    for row in rows:
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
            
            # Handle both dict (CSV) and pandas Series (Excel) row types
            def get_value(row, key):
                if key is None:
                    return ''
                if isinstance(row, dict):
                    return str(row.get(key, '')).strip() if row.get(key) is not None else ''
                else:
                    # pandas Series
                    return str(row.get(key, '')).strip() if pd.notna(row.get(key)) else ''
            
            drg_code_value = get_value(row, drg_code)
            drg_desc_value = get_value(row, drg_description)
            icd10_code_value = get_value(row, icd10_code)
            icd10_desc_value = get_value(row, icd10_description)
            notes_value = get_value(row, notes)
            remarks_value = get_value(row, remarks)
            
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
    current_user: User = Depends(require_role(["Admin", "Billing", "Pharmacy Head"]))
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
    current_user: User = Depends(require_role(["Billing", "Doctor", "Admin", "Pharmacy", "Pharmacy Head"]))
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
            
            # Build product name with formulation if available
            product_name_with_formulation = item.product_name
            if item.formulation:
                product_name_with_formulation = f"{item.product_name} ({item.formulation})"
            
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
                "service_name": product_name_with_formulation,  # Map product_name with formulation to service_name
                "service_type": item.sub_category_1 or item.sub_category_2,  # Use sub_category as service_type
                "item_code": item.medication_code,
                "item_name": product_name_with_formulation,  # Include formulation in item_name
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
    current_user: User = Depends(require_role(["Billing", "Doctor", "Admin", "Records", "PA", "Nurse", "Pharmacy", "Pharmacy Head", "Lab", "Scan", "Xray", "Claims"]))
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
    current_user: User = Depends(require_role(["Doctor", "Billing", "Admin", "Records", "PA", "Nurse", "Pharmacy", "Pharmacy Head", "Lab", "Scan", "Xray", "Claims"]))
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


@router.get("/drg-codes/search")
def search_drg_codes(
    search_term: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Billing", "Doctor", "Records", "PA", "Nurse", "Pharmacy", "Pharmacy Head", "Lab", "Scan", "Xray", "Claims"]))
):
    """Search DRG codes across all sources (procedures, surgeries, unmapped DRG, and existing mappings)"""
    from sqlalchemy import or_
    
    # Collect DRG codes from all sources
    drg_codes_map = {}  # {drg_code: {code, description}}
    
    # 1. From ProcedurePrice
    if search_term:
        procedures = db.query(ProcedurePrice).filter(
            ProcedurePrice.g_drg_code.ilike(f"%{search_term}%"),
            ProcedurePrice.is_active == True
        ).distinct(ProcedurePrice.g_drg_code).limit(limit).all()
    else:
        procedures = db.query(ProcedurePrice).filter(
            ProcedurePrice.is_active == True
        ).distinct(ProcedurePrice.g_drg_code).limit(limit).all()
    
    for proc in procedures:
        if proc.g_drg_code:
            drg_codes_map[proc.g_drg_code] = {
                "drg_code": proc.g_drg_code,
                "drg_description": proc.service_name or ""
            }
    
    # 2. From SurgeryPrice
    if search_term:
        surgeries = db.query(SurgeryPrice).filter(
            SurgeryPrice.g_drg_code.ilike(f"%{search_term}%"),
            SurgeryPrice.is_active == True
        ).distinct(SurgeryPrice.g_drg_code).limit(limit).all()
    else:
        surgeries = db.query(SurgeryPrice).filter(
            SurgeryPrice.is_active == True
        ).distinct(SurgeryPrice.g_drg_code).limit(limit).all()
    
    for surg in surgeries:
        if surg.g_drg_code:
            if surg.g_drg_code not in drg_codes_map or not drg_codes_map[surg.g_drg_code]["drg_description"]:
                drg_codes_map[surg.g_drg_code] = {
                    "drg_code": surg.g_drg_code,
                    "drg_description": surg.service_name or ""
                }
    
    # 3. From UnmappedDRGPrice
    if search_term:
        unmapped = db.query(UnmappedDRGPrice).filter(
            UnmappedDRGPrice.g_drg_code.ilike(f"%{search_term}%"),
            UnmappedDRGPrice.is_active == True
        ).distinct(UnmappedDRGPrice.g_drg_code).limit(limit).all()
    else:
        unmapped = db.query(UnmappedDRGPrice).filter(
            UnmappedDRGPrice.is_active == True
        ).distinct(UnmappedDRGPrice.g_drg_code).limit(limit).all()
    
    for unm in unmapped:
        if unm.g_drg_code:
            if unm.g_drg_code not in drg_codes_map or not drg_codes_map[unm.g_drg_code]["drg_description"]:
                drg_codes_map[unm.g_drg_code] = {
                    "drg_code": unm.g_drg_code,
                    "drg_description": unm.service_name or ""
                }
    
    # 4. From ICD10DRGMapping (existing mappings)
    if search_term:
        mappings = db.query(ICD10DRGMapping).filter(
            or_(
                ICD10DRGMapping.drg_code.ilike(f"%{search_term}%"),
                ICD10DRGMapping.drg_description.ilike(f"%{search_term}%")
            ),
            ICD10DRGMapping.is_active == True
        ).distinct(ICD10DRGMapping.drg_code).limit(limit).all()
    else:
        mappings = db.query(ICD10DRGMapping).filter(
            ICD10DRGMapping.is_active == True
        ).distinct(ICD10DRGMapping.drg_code).limit(limit).all()
    
    for mapping in mappings:
        if mapping.drg_code:
            if mapping.drg_code not in drg_codes_map or not drg_codes_map[mapping.drg_code]["drg_description"]:
                drg_codes_map[mapping.drg_code] = {
                    "drg_code": mapping.drg_code,
                    "drg_description": mapping.drg_description or ""
                }
    
    # Convert to list and sort
    results = list(drg_codes_map.values())
    results.sort(key=lambda x: x["drg_code"])
    
    return results[:limit]


# ICD-10 DRG Mapping Management Endpoints
class ICD10DRGMappingCreate(BaseModel):
    """ICD-10 DRG mapping creation model"""
    drg_code: Optional[str] = None  # Optional to allow unmapped ICD-10 codes
    drg_description: Optional[str] = None
    icd10_code: str
    icd10_description: Optional[str] = None
    notes: Optional[str] = None
    remarks: Optional[str] = None
    is_active: bool = True


class ICD10DRGMappingUpdate(BaseModel):
    """ICD-10 DRG mapping update model"""
    drg_code: Optional[str] = None
    drg_description: Optional[str] = None
    icd10_code: Optional[str] = None
    icd10_description: Optional[str] = None
    notes: Optional[str] = None
    remarks: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/icd10-mappings")
def list_icd10_drg_mappings(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    unmapped_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Billing", "Doctor"]))
):
    """List all ICD-10 DRG mappings with pagination and search"""
    from sqlalchemy import or_
    
    query = db.query(ICD10DRGMapping)
    
    # Apply active status filter if provided
    if is_active is not None:
        query = query.filter(ICD10DRGMapping.is_active == is_active)
    
    # Filter for unmapped ICD-10 codes (no DRG code or empty DRG code)
    if unmapped_only:
        query = query.filter(
            or_(
                ICD10DRGMapping.drg_code == '',
                ICD10DRGMapping.drg_code.is_(None)
            )
        )
    
    # Apply search filter if provided
    if search:
        search_filter = or_(
            ICD10DRGMapping.drg_code.ilike(f"%{search}%"),
            ICD10DRGMapping.drg_description.ilike(f"%{search}%"),
            ICD10DRGMapping.icd10_code.ilike(f"%{search}%"),
            ICD10DRGMapping.icd10_description.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
    
    # Get total count before pagination
    total = query.count()
    
    # Apply pagination
    mappings = query.order_by(ICD10DRGMapping.icd10_code, ICD10DRGMapping.drg_code).offset(skip).limit(limit).all()
    
    results = []
    for mapping in mappings:
        results.append({
            "id": mapping.id,
            "drg_code": mapping.drg_code,
            "drg_description": mapping.drg_description or "",
            "icd10_code": mapping.icd10_code,
            "icd10_description": mapping.icd10_description or "",
            "notes": mapping.notes or "",
            "remarks": mapping.remarks or "",
            "is_active": mapping.is_active
        })
    
    return {
        "items": results,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.post("/icd10-mappings")
def create_icd10_drg_mapping(
    mapping_data: ICD10DRGMappingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Create a new ICD-10 DRG mapping"""
    # Allow empty DRG code for unmapped ICD-10 codes
    drg_code = mapping_data.drg_code.strip() if mapping_data.drg_code else ''
    
    # Check if mapping already exists (only if DRG code is provided)
    if drg_code:
        existing = db.query(ICD10DRGMapping).filter(
            ICD10DRGMapping.drg_code == drg_code,
            ICD10DRGMapping.icd10_code == mapping_data.icd10_code
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Mapping between DRG code {drg_code} and ICD-10 code {mapping_data.icd10_code} already exists"
            )
    else:
        # Check if unmapped ICD-10 already exists
        from sqlalchemy import or_
        existing = db.query(ICD10DRGMapping).filter(
            ICD10DRGMapping.icd10_code == mapping_data.icd10_code,
            or_(
                ICD10DRGMapping.drg_code == '',
                ICD10DRGMapping.drg_code.is_(None)
            )
        ).first()
        
        if existing:
            # Update existing unmapped entry
            existing.icd10_description = mapping_data.icd10_description or existing.icd10_description
            existing.notes = mapping_data.notes or existing.notes
            existing.remarks = mapping_data.remarks or existing.remarks
            existing.is_active = mapping_data.is_active
            db.commit()
            db.refresh(existing)
            
            return {
                "id": existing.id,
                "drg_code": existing.drg_code or "",
                "drg_description": existing.drg_description or "",
                "icd10_code": existing.icd10_code,
                "icd10_description": existing.icd10_description or "",
                "notes": existing.notes or "",
                "remarks": existing.remarks or "",
                "is_active": existing.is_active
            }
    
    new_mapping = ICD10DRGMapping(
        drg_code=drg_code,
        drg_description=mapping_data.drg_description,
        icd10_code=mapping_data.icd10_code,
        icd10_description=mapping_data.icd10_description,
        notes=mapping_data.notes,
        remarks=mapping_data.remarks,
        is_active=mapping_data.is_active
    )
    
    db.add(new_mapping)
    db.commit()
    db.refresh(new_mapping)
    
    return {
        "id": new_mapping.id,
        "drg_code": new_mapping.drg_code,
        "drg_description": new_mapping.drg_description or "",
        "icd10_code": new_mapping.icd10_code,
        "icd10_description": new_mapping.icd10_description or "",
        "notes": new_mapping.notes or "",
        "remarks": new_mapping.remarks or "",
        "is_active": new_mapping.is_active
    }


@router.put("/icd10-mappings/{mapping_id}")
def update_icd10_drg_mapping(
    mapping_id: int,
    mapping_data: ICD10DRGMappingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Update an existing ICD-10 DRG mapping"""
    mapping = db.query(ICD10DRGMapping).filter(ICD10DRGMapping.id == mapping_id).first()
    
    if not mapping:
        raise HTTPException(status_code=404, detail="ICD-10 DRG mapping not found")
    
    # Check if updating to a combination that already exists (if drg_code or icd10_code is being changed)
    if mapping_data.drg_code or mapping_data.icd10_code:
        new_drg_code = mapping_data.drg_code if mapping_data.drg_code else mapping.drg_code
        new_icd10_code = mapping_data.icd10_code if mapping_data.icd10_code else mapping.icd10_code
        
        existing = db.query(ICD10DRGMapping).filter(
            ICD10DRGMapping.drg_code == new_drg_code,
            ICD10DRGMapping.icd10_code == new_icd10_code,
            ICD10DRGMapping.id != mapping_id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Mapping between DRG code {new_drg_code} and ICD-10 code {new_icd10_code} already exists"
            )
    
    # Update fields
    if mapping_data.drg_code is not None:
        mapping.drg_code = mapping_data.drg_code
    if mapping_data.drg_description is not None:
        mapping.drg_description = mapping_data.drg_description
    if mapping_data.icd10_code is not None:
        mapping.icd10_code = mapping_data.icd10_code
    if mapping_data.icd10_description is not None:
        mapping.icd10_description = mapping_data.icd10_description
    if mapping_data.notes is not None:
        mapping.notes = mapping_data.notes
    if mapping_data.remarks is not None:
        mapping.remarks = mapping_data.remarks
    if mapping_data.is_active is not None:
        mapping.is_active = mapping_data.is_active
    
    db.commit()
    db.refresh(mapping)
    
    return {
        "id": mapping.id,
        "drg_code": mapping.drg_code,
        "drg_description": mapping.drg_description or "",
        "icd10_code": mapping.icd10_code,
        "icd10_description": mapping.icd10_description or "",
        "notes": mapping.notes or "",
        "remarks": mapping.remarks or "",
        "is_active": mapping.is_active
    }


@router.delete("/icd10-mappings/{mapping_id}")
def delete_icd10_drg_mapping(
    mapping_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Delete an ICD-10 DRG mapping (soft delete by setting is_active to False)"""
    mapping = db.query(ICD10DRGMapping).filter(ICD10DRGMapping.id == mapping_id).first()
    
    if not mapping:
        raise HTTPException(status_code=404, detail="ICD-10 DRG mapping not found")
    
    # Soft delete
    mapping.is_active = False
    db.commit()
    
    return {"message": "ICD-10 DRG mapping deleted successfully"}


@router.get("/export/icd10-mapping/csv")
def export_icd10_drg_mapping_csv(
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Billing", "Doctor"]))
):
    """Export ICD-10 DRG mappings as CSV file"""
    query = db.query(ICD10DRGMapping)
    
    # Apply active status filter if provided
    if is_active is not None:
        query = query.filter(ICD10DRGMapping.is_active == is_active)
    
    # Get all mappings
    mappings = query.order_by(ICD10DRGMapping.icd10_code, ICD10DRGMapping.drg_code).all()
    
    if not mappings:
        raise HTTPException(status_code=404, detail="No ICD-10 DRG mappings found")
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header row
    writer.writerow([
        'DRG Code',
        'DRG Description',
        'ICD-10 Code',
        'ICD-10 Description',
        'Notes',
        'Remarks',
        'Is Active'
    ])
    
    # Write data rows
    for mapping in mappings:
        writer.writerow([
            mapping.drg_code or '',
            mapping.drg_description or '',
            mapping.icd10_code or '',
            mapping.icd10_description or '',
            mapping.notes or '',
            mapping.remarks or '',
            'True' if mapping.is_active else 'False'
        ])
    
    # Get CSV content
    csv_content = output.getvalue()
    output.close()
    
    # Return CSV file
    filename = "icd10_drg_mapping.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get("/export/{file_type}/csv")
def export_price_list_csv(
    file_type: str,  # procedure, surgery, product, unmapped_drg
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Billing", "Pharmacy Head"]))
):
    """Export price list as CSV file by type"""
    valid_types = ["procedure", "surgery", "product", "unmapped_drg"]
    if file_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Must be one of: {', '.join(valid_types)}"
        )
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    if file_type == "product":
        # Query all product prices
        items = db.query(ProductPrice).filter(ProductPrice.is_active == True).order_by(ProductPrice.product_name).all()
        
        if not items:
            raise HTTPException(status_code=404, detail="No product prices found")
        
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
        for item in items:
            # Reconstruct the Product N format: "Product Name (Code) (CODE | Product Name)"
            product_n = item.product_name
            if item.medication_code:
                # If product_name doesn't already contain the code format, construct it
                if f"({item.medication_code}" not in item.product_name:
                    product_n = f"{item.product_name} ({item.medication_code} | {item.product_name})"
            
            writer.writerow([
                product_n,
                item.medication_code or '',
                item.product_name or '',
                item.sub_category_1 or '',
                item.sub_category_2 or '',
                item.product_id or '',
                item.formulation or '',
                item.strength or '',
                item.base_rate or 0.0,
                item.nhia_app or '',
                item.nhia_claim_co_payment if item.nhia_claim_co_payment is not None else 0.0,  # Preserve 0.0, default to 0.0 if None
                item.claim_amount or '',
                item.nhia_claim or '',
                item.bill_effective or '',
                item.insurance_covered or 'yes',  # Default to 'yes' if not set
                'True' if item.is_active else 'False'
            ])
        
        filename = "product_price_list.csv"
    
    elif file_type == "procedure":
        items = db.query(ProcedurePrice).filter(ProcedurePrice.is_active == True).order_by(ProcedurePrice.service_name).all()
        
        if not items:
            raise HTTPException(status_code=404, detail="No procedure prices found")
        
        writer.writerow([
            'Sr.No.',
            'G-DRG Code',
            'Service Ty',
            'Service Type',
            'Service ID',
            'Service Name',
            'Base Rate',
            'NHIA App',
            'NHIA Claim Co-Payment',
            'Clinic Bill Effective',
            'Is Active'
        ])
        
        for item in items:
            writer.writerow([
                item.sr_no or '',
                item.g_drg_code or '',
                item.service_ty or '',
                item.service_type or '',
                item.service_id or '',
                item.service_name or '',
                item.base_rate or 0.0,
                item.nhia_app or '',
                item.nhia_claim_co_payment if item.nhia_claim_co_payment is not None else 0.0,  # Preserve 0.0, default to 0.0 if None
                item.clinic_bill_effective or '',
                'True' if item.is_active else 'False'
            ])
        
        filename = "procedure_price_list.csv"
    
    elif file_type == "surgery":
        items = db.query(SurgeryPrice).filter(SurgeryPrice.is_active == True).order_by(SurgeryPrice.service_name).all()
        
        if not items:
            raise HTTPException(status_code=404, detail="No surgery prices found")
        
        writer.writerow([
            'Sr.No.',
            'G-DRG Code',
            'Service Ty',
            'Service Type',
            'Service ID',
            'Service Name',
            'Base Rate',
            'NHIA App',
            'NHIA Claim Co-Payment',
            'Clinic Bill Effective',
            'Is Active'
        ])
        
        for item in items:
            writer.writerow([
                item.sr_no or '',
                item.g_drg_code or '',
                item.service_ty or '',
                item.service_type or '',
                item.service_id or '',
                item.service_name or '',
                item.base_rate or 0.0,
                item.nhia_app or '',
                item.nhia_claim_co_payment if item.nhia_claim_co_payment is not None else 0.0,  # Preserve 0.0, default to 0.0 if None
                item.clinic_bill_effective or '',
                'True' if item.is_active else 'False'
            ])
        
        filename = "surgery_price_list.csv"
    
    elif file_type == "unmapped_drg":
        items = db.query(UnmappedDRGPrice).filter(UnmappedDRGPrice.is_active == True).order_by(UnmappedDRGPrice.service_name).all()
        
        if not items:
            raise HTTPException(status_code=404, detail="No unmapped DRG prices found")
        
        writer.writerow([
            'Sr.No.',
            'G-DRG Code',
            'Service Ty',
            'Service Type',
            'Service ID',
            'Service Name',
            'Base Rate',
            'NHIA App',
            'NHIA Claim Co-Payment',
            'Clinic Bill Effective',
            'Is Active'
        ])
        
        for item in items:
            writer.writerow([
                item.sr_no or '',
                item.g_drg_code or '',
                item.service_ty or '',
                item.service_type or '',
                item.service_id or '',
                item.service_name or '',
                item.base_rate or 0.0,
                item.nhia_app or '',
                item.nhia_claim_co_payment if item.nhia_claim_co_payment is not None else 0.0,  # Preserve 0.0, default to 0.0 if None
                item.clinic_bill_effective or '',
                'True' if item.is_active else 'False'
            ])
        
        filename = "unmapped_drg_price_list.csv"
    
    # Get CSV content
    csv_content = output.getvalue()
    output.close()
    
    # Return CSV file
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )

