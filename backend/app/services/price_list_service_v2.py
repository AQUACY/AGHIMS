"""
New Price list service for separate table structure
Handles different Excel file types with all columns preserved
"""
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import UploadFile
from typing import List, Dict
from app.models.procedure_price import ProcedurePrice
from app.models.surgery_price import SurgeryPrice
from app.models.product_price import ProductPrice
from app.models.unmapped_drg_price import UnmappedDRGPrice


def extract_medication_code_from_product_name(product_name: str) -> tuple:
    """
    Extract medication code from product name string
    Format examples:
    - "Allopurinol (300 mg) (ALLOPUTA2 | Allopurinol )" -> ("ALLOPUTA2", "Allopurinol (300 mg)")
    - "Amino Acid Solution (AMIACIIN1 | Amino Acid Solution )" -> ("AMIACIIN1", "Amino Acid Solution")
    - "Product Name (CODE | Product Name )" -> ("CODE", "Product Name")
    
    Returns: (medication_code, clean_product_name)
    """
    import re
    
    if not product_name:
        return None, None
    
    product_name = product_name.strip()
    
    # Pattern: (MEDICATION_CODE | Product Name ) at the end
    # Medication code is alphanumeric (uppercase letters and numbers, typically 5-15 chars)
    # Pattern matches: (CODE | anything )
    pattern = r'\(([A-Z0-9]{3,20})\s*\|\s*[^)]+\)\s*$'
    match = re.search(pattern, product_name)
    
    if match:
        medication_code = match.group(1).strip()
        # Remove the medication code part from the product name to get clean name
        # Remove: (CODE | anything ) at the end
        clean_name = re.sub(r'\s*\([A-Z0-9]+\s*\|\s*[^)]+\)\s*$', '', product_name).strip()
        return medication_code, clean_name
    
    # Try alternative pattern: just (CODE) at the end if pipe pattern not found
    alt_pattern = r'\(([A-Z0-9]{3,20})\)\s*$'
    alt_match = re.search(alt_pattern, product_name)
    if alt_match:
        medication_code = alt_match.group(1).strip()
        clean_name = re.sub(r'\s*\([A-Z0-9]+\)\s*$', '', product_name).strip()
        return medication_code, clean_name
    
    # If pattern not found, return None for code, full name as product name
    return None, product_name


def parse_product_excel(df: pd.DataFrame, original_columns: List[str]) -> List[Dict]:
    """
    Parse product/medication Excel file with product-specific columns
    Columns: Sr.No., Sub Categ (twice), Product ID, Product N, Formulati,
    Strength, Base Rate, NHIA App, Claim Am, NHIA Clain, Bill Effecti
    """
    items = []
    
    # Map product-specific columns
    sr_no_col = None
    sub_categ_1_col = None
    sub_categ_2_col = None
    product_id_col = None
    product_name_col = None
    formulation_col = None
    strength_col = None
    base_rate_col = None
    nhia_app_col = None
    claim_amount_col = None
    nhia_claim_col = None
    bill_effective_col = None
    insurance_covered_col = None
    
    # Map columns based on original and normalized names
    for i, orig_col in enumerate(original_columns):
        col = df.columns[i]
        col_lower = col.lower()
        orig_col_lower = str(orig_col).strip().lower()
        
        # Sr.No.
        if 'sr_no' in col_lower or 'sr.' in orig_col_lower:
            sr_no_col = col
        
        # Sub Category (first one)
        elif ('sub_categ' in col_lower or 'subcategory' in col_lower) and not sub_categ_1_col:
            sub_categ_1_col = col
        
        # Sub Category (second one)
        elif ('sub_categ' in col_lower or 'subcategory' in col_lower) and sub_categ_1_col:
            sub_categ_2_col = col
        
        # Product ID
        elif 'product_id' in col_lower or 'productid' in col_lower:
            product_id_col = col
        
        # Product Name (Product N)
        elif 'product_n' in col_lower or ('product' in orig_col_lower and 'n' in orig_col_lower and len(orig_col_lower) < 12):
            product_name_col = col
        
        # Formulation
        elif 'formulati' in col_lower or 'formulation' in col_lower:
            formulation_col = col
        
        # Strength
        elif 'strength' in col_lower:
            strength_col = col
        
        # Base Rate
        elif 'base_rate' in col_lower or (orig_col_lower.startswith('base') and 'rate' in orig_col_lower):
            base_rate_col = col
        
        # NHIA App
        elif 'nhia_app' in col_lower or 'nhia_approved' in col_lower or \
             (orig_col_lower.startswith('nhia') and ('app' in orig_col_lower or 'approved' in orig_col_lower)):
            nhia_app_col = col
        
        # Claim Amount
        elif 'claim_am' in col_lower or 'claim_amount' in col_lower or \
             (orig_col_lower.startswith('claim') and 'am' in orig_col_lower):
            claim_amount_col = col
        
        # NHIA Claim
        elif 'nhia_clain' in col_lower or ('nhia' in orig_col_lower and 'clain' in orig_col_lower):
            nhia_claim_col = col
        
        # Bill Effective
        elif 'bill_effecti' in col_lower or 'bill_effective' in col_lower:
            bill_effective_col = col
        
        # Insurance Covered - Check multiple variations
        elif 'insurance_covered' in col_lower or 'insurancecovered' in col_lower or \
             'insurance_cover' in col_lower or 'insurance cover' in col_lower or \
             (orig_col_lower.startswith('insurance') and 'covered' in orig_col_lower) or \
             (orig_col_lower.startswith('insurance') and 'cover' in orig_col_lower):
            insurance_covered_col = col
    
    # Validate required columns
    if not product_name_col:
        raise ValueError("Missing required column: Product N (Product Name)")
    
    # Debug: Print detected columns
    print(f"DEBUG: Detected columns for product price list:")
    print(f"  - Product Name: {product_name_col}")
    print(f"  - Insurance Covered: {insurance_covered_col}")
    print(f"  - Base Rate: {base_rate_col}")
    print(f"  - All columns: {list(df.columns)}")
    
    # Process rows
    for idx, row in df.iterrows():
        # Skip empty rows or header rows
        if pd.isna(row[product_name_col]) or str(row[product_name_col]).strip() == '':
            continue
        
        product_name_raw = str(row[product_name_col]).strip()
        if product_name_raw.lower() in ['product n', 'product name', 'name', 'nan']:
            continue
        
        # Extract medication code from product name
        medication_code, clean_product_name = extract_medication_code_from_product_name(product_name_raw)
        
        if not medication_code:
            # If no medication code found, try to use product ID as fallback
            if product_id_col and product_id_col in df.columns and not pd.isna(row[product_id_col]):
                medication_code = str(row[product_id_col]).strip()
            else:
                # Skip rows without medication code
                print(f"Warning: Could not extract medication code from: {product_name_raw}")
                continue
        
        # Build item dictionary
        item = {
            'medication_code': medication_code,
            'product_name': product_name_raw,  # Keep full original name
        }
        
        # Optional fields
        if sr_no_col and sr_no_col in df.columns and not pd.isna(row[sr_no_col]):
            item['sr_no'] = str(row[sr_no_col]).strip()
        else:
            item['sr_no'] = None
        
        if sub_categ_1_col and sub_categ_1_col in df.columns and not pd.isna(row[sub_categ_1_col]):
            item['sub_category_1'] = str(row[sub_categ_1_col]).strip()
        else:
            item['sub_category_1'] = None
        
        if sub_categ_2_col and sub_categ_2_col in df.columns and not pd.isna(row[sub_categ_2_col]):
            item['sub_category_2'] = str(row[sub_categ_2_col]).strip()
        else:
            item['sub_category_2'] = None
        
        if product_id_col and product_id_col in df.columns and not pd.isna(row[product_id_col]):
            item['product_id'] = str(row[product_id_col]).strip()
        else:
            item['product_id'] = None
        
        if formulation_col and formulation_col in df.columns and not pd.isna(row[formulation_col]):
            item['formulation'] = str(row[formulation_col]).strip()
        else:
            item['formulation'] = None
        
        if strength_col and strength_col in df.columns and not pd.isna(row[strength_col]):
            item['strength'] = str(row[strength_col]).strip()
        else:
            item['strength'] = None
        
        # Base Rate (cash price)
        item['base_rate'] = 0.0
        if base_rate_col and base_rate_col in df.columns:
            try:
                val = row[base_rate_col]
                if pd.notna(val):
                    item['base_rate'] = float(val)
            except (ValueError, TypeError):
                item['base_rate'] = 0.0
        
        # NHIA App (insured price)
        item['nhia_app'] = None
        if nhia_app_col and nhia_app_col in df.columns:
            try:
                val = row[nhia_app_col]
                if pd.notna(val):
                    item['nhia_app'] = float(val)
            except (ValueError, TypeError):
                item['nhia_app'] = None
        
        # Claim Amount
        item['claim_amount'] = None
        if claim_amount_col and claim_amount_col in df.columns:
            try:
                val = row[claim_amount_col]
                if pd.notna(val):
                    item['claim_amount'] = float(val)
            except (ValueError, TypeError):
                item['claim_amount'] = None
        
        # NHIA Claim
        if nhia_claim_col and nhia_claim_col in df.columns and not pd.isna(row[nhia_claim_col]):
            item['nhia_claim'] = str(row[nhia_claim_col]).strip()
        else:
            item['nhia_claim'] = None
        
        # Bill Effective
        if bill_effective_col and bill_effective_col in df.columns and not pd.isna(row[bill_effective_col]):
            item['bill_effective'] = str(row[bill_effective_col]).strip()
        else:
            item['bill_effective'] = None
        
        # Insurance Covered (default to "yes" if not specified)
        if insurance_covered_col and insurance_covered_col in df.columns:
            insurance_val_raw = row[insurance_covered_col]
            # Check if value is NaN or empty
            if pd.isna(insurance_val_raw) or (isinstance(insurance_val_raw, str) and insurance_val_raw.strip() == ''):
                item['insurance_covered'] = 'yes'  # Default to "yes" if empty
            else:
                insurance_val = str(insurance_val_raw).strip()
                insurance_val_lower = insurance_val.lower()
                # Check for "no" variations (case-insensitive) - be explicit
                if insurance_val_lower in ['no', 'n', 'false', '0', 'f']:
                    item['insurance_covered'] = 'no'
                    print(f"DEBUG: Row {idx+1}: Set insurance_covered='no' from value '{insurance_val}'")
                elif insurance_val_lower in ['yes', 'y', 'true', '1', 't']:
                    item['insurance_covered'] = 'yes'
                    print(f"DEBUG: Row {idx+1}: Set insurance_covered='yes' from value '{insurance_val}'")
                else:
                    # If value exists but is not recognized, default to "yes" for backward compatibility
                    print(f"Warning: Row {idx+1}: Unrecognized insurance_covered value '{insurance_val}' for product {item.get('medication_code', 'N/A')}, defaulting to 'yes'")
                    item['insurance_covered'] = 'yes'
        else:
            # If column doesn't exist, default to "yes"
            if idx < 3:  # Only print for first few rows
                print(f"DEBUG: Row {idx+1}: Insurance Covered column not found, defaulting to 'yes'")
            item['insurance_covered'] = 'yes'  # Default to "yes" if column not found
        
        items.append(item)
    
    if not items:
        raise ValueError("No valid items found in the Excel file. Please check the file format.")
    
    return items


def parse_excel_price_list_complete(file: UploadFile, file_type: str) -> List[Dict]:
    """
    Parse Excel file and return list of price items with ALL columns preserved
    File types: procedure, surgery, product, unmapped_drg
    
    For procedure/surgery/unmapped_drg:
    Expected columns: Sr.No., G-DRG Code, Service Ty, Service Type, Service ID, 
    Service Name, Base Rate, NHIA App, NHIA Claim Co-Payment, Clinic(0 - (Bill Effective)
    
    For product:
    Expected columns: Sr.No., Sub Categ (twice), Product ID, Product N, Formulati,
    Strength, Base Rate, NHIA App, Claim Am, NHIA Clain, Bill Effecti
    """
    import io
    # Read file content into BytesIO to avoid seekable() issues with SpooledTemporaryFile
    # The file.file is a SpooledTemporaryFile which may not have seekable() in some Python versions
    file_content = file.file.read()
    file.file.seek(0)  # Reset file pointer for potential reuse
    df = pd.read_excel(io.BytesIO(file_content))
    
    # Normalize column names (handle variations)
    original_columns = df.columns.tolist()
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace('-', '_')
    
    # If file_type is explicitly "product", always use product parsing
    if file_type == "product":
        try:
            return parse_product_excel(df, original_columns)
        except Exception as e:
            # If product parsing fails, provide helpful error
            raise ValueError(f"Error parsing product file: {str(e)}. Make sure the file has 'Product N' (Product Name) column with medication codes.")
    
    # Check if this is a product file (has Product N, Product ID, Sub Categ columns)
    # Check in both normalized and original column names
    is_product_file = any(
        'product_n' in col or 
        'product_id' in col or 
        'sub_categ' in col or
        ('product' in col and 'n' in col and len(col) < 12)
        for col in df.columns
    ) or any(
        ('product' in str(col).lower() and ('n' in str(col).lower() or 'id' in str(col).lower())) or
        ('sub' in str(col).lower() and 'categ' in str(col).lower())
        for col in original_columns
    )
    
    # If detected as product file, use product-specific parsing
    if is_product_file:
        try:
            return parse_product_excel(df, original_columns)
        except Exception as e:
            # If product parsing fails, provide helpful error
            raise ValueError(f"Error parsing product file: {str(e)}. Make sure the file has 'Product N' (Product Name) column with medication codes.")
    
    # Otherwise, use procedure/surgery/unmapped_drg parsing
    items = []
    
    # Map column names (handle variations)
    sr_no_col = None
    code_col = None
    service_ty_col = None
    service_type_col = None  # This is the department/clinic (used as category)
    service_id_col = None
    name_col = None
    base_rate_col = None
    nhia_app_col = None
    nhia_co_pay_col = None
    clinic_col = None
    
    # Check original column names too (before normalization)
    for i, orig_col in enumerate(original_columns):
        col = df.columns[i]
        col_lower = col.lower()
        orig_col_lower = str(orig_col).strip().lower()
        
        # Sr.No.
        if 'sr_no' in col_lower or 'sr.' in orig_col_lower or 'serial' in col_lower:
            sr_no_col = col
        
        # G-DRG Code
        elif (('g_drg' in col_lower or 'gdrg' in col_lower) and 'code' in col_lower) or \
             ('g-drg' in orig_col_lower and 'code' in orig_col_lower):
            code_col = col
        
        # Service Type (the full one - department/clinic)
        elif orig_col_lower.startswith('service') and ('type' in orig_col_lower or 'ty' in orig_col_lower):
            if len(orig_col_lower) <= 11 or orig_col_lower == 'service_ty':  # Truncated version
                service_ty_col = col
            else:  # Full "Service Type" - this is the department/clinic
                service_type_col = col
        
        # Service ID
        elif 'service_id' in col_lower or 'serviceid' in col_lower or \
             ('service' in orig_col_lower and 'id' in orig_col_lower and 'type' not in orig_col_lower):
            service_id_col = col
        
        # Service Name
        elif 'service_name' in col_lower or \
             ('service' in orig_col_lower and 'name' in orig_col_lower):
            name_col = col
        
        # Base Rate
        elif 'base_rate' in col_lower or \
             (orig_col_lower.startswith('base') and 'rate' in orig_col_lower):
            base_rate_col = col
        
        # NHIA App / NHIA Approved
        elif 'nhia_app' in col_lower or 'nhia_approved' in col_lower or 'nhiaapp' in col_lower or \
             (orig_col_lower.startswith('nhia') and ('app' in orig_col_lower or 'approved' in orig_col_lower)):
            nhia_app_col = col
        
        # NHIA Claim Co-Payment
        elif ('nhia_claim' in col_lower or 'nhia_co' in col_lower or 
              'co_payment' in col_lower or 'copayment' in col_lower or
              ('nhia' in orig_col_lower and ('claim' in orig_col_lower or 'co' in orig_col_lower or 'pay' in orig_col_lower))):
            nhia_co_pay_col = col
        
        # Clinic Bill Effective (may be truncated)
        elif 'clinic' in col_lower or 'bill_effective' in col_lower or \
             ('clinic' in orig_col_lower or 'bill' in orig_col_lower):
            clinic_col = col
    
    # Validate required columns (skip validation if we already handled product file)
    if not code_col:
        raise ValueError("Missing required column: G-DRG Code. For product files, make sure 'Product N' column exists with medication codes.")
    if not name_col:
        raise ValueError("Missing required column: Service Name")
    
    # Process rows
    for idx, row in df.iterrows():
        # Skip empty rows or header rows
        if pd.isna(row[code_col]) or str(row[code_col]).strip() == '':
            continue
        
        # Skip if code looks like a header
        code_str = str(row[code_col]).strip()
        if code_str.lower() in ['g-drg code', 'g_drg_code', 'code', 'nan', 'none']:
            continue
        
        item_name = str(row[name_col]).strip() if not pd.isna(row[name_col]) else ''
        if not item_name or item_name.lower() in ['service name', 'name', 'nan']:
            continue
        
        # Build item dictionary with all columns
        item = {
            'g_drg_code': code_str,
            'service_name': item_name,
            'service_type': None,  # Will be set from Service Type column
        }
        
        # Optional fields
        if sr_no_col and sr_no_col in df.columns and not pd.isna(row[sr_no_col]):
            item['sr_no'] = str(row[sr_no_col]).strip()
        else:
            item['sr_no'] = None
        
        if service_ty_col and service_ty_col in df.columns and not pd.isna(row[service_ty_col]):
            item['service_ty'] = str(row[service_ty_col]).strip()
        else:
            item['service_ty'] = None
        
        # Service Type (department/clinic) - this is the category
        if service_type_col and service_type_col in df.columns and not pd.isna(row[service_type_col]):
            service_type_val = row[service_type_col]
            if pd.notna(service_type_val):
                service_type = str(service_type_val).strip()
                if service_type.lower() not in ['service type', 'type', 'department', 'nan']:
                    item['service_type'] = service_type
        
        if service_id_col and service_id_col in df.columns and not pd.isna(row[service_id_col]):
            item['service_id'] = str(row[service_id_col]).strip()
        else:
            item['service_id'] = None
        
        # Base Rate (cash price)
        item['base_rate'] = 0.0
        if base_rate_col and base_rate_col in df.columns:
            try:
                val = row[base_rate_col]
                if pd.notna(val):
                    item['base_rate'] = float(val)
            except (ValueError, TypeError):
                item['base_rate'] = 0.0
        
        # NHIA App (insured price)
        item['nhia_app'] = None
        if nhia_app_col and nhia_app_col in df.columns:
            try:
                val = row[nhia_app_col]
                if pd.notna(val):
                    item['nhia_app'] = float(val)
            except (ValueError, TypeError):
                item['nhia_app'] = None
        
        # NHIA Claim Co-Payment
        item['nhia_claim_co_payment'] = None
        if nhia_co_pay_col and nhia_co_pay_col in df.columns:
            try:
                val = row[nhia_co_pay_col]
                if pd.notna(val):
                    item['nhia_claim_co_payment'] = float(val)
            except (ValueError, TypeError):
                item['nhia_claim_co_payment'] = None
        
        # Clinic Bill Effective
        if clinic_col and clinic_col in df.columns and not pd.isna(row[clinic_col]):
            item['clinic_bill_effective'] = str(row[clinic_col]).strip()
        else:
            item['clinic_bill_effective'] = None
        
        items.append(item)
    
    if not items:
        raise ValueError("No valid items found in the Excel file. Please check the file format.")
    
    return items


def upload_procedure_prices(db: Session, items: List[Dict]):
    """Upload procedure price list items to database"""
    for item_data in items:
        existing = (
            db.query(ProcedurePrice)
            .filter(ProcedurePrice.g_drg_code == item_data['g_drg_code'])
            .first()
        )
        
        if existing:
            # Update existing item
            for key, value in item_data.items():
                setattr(existing, key, value)
            existing.is_active = True
        else:
            # Create new item
            new_item = ProcedurePrice(**item_data)
            db.add(new_item)
    
    db.commit()


def upload_surgery_prices(db: Session, items: List[Dict]):
    """Upload surgery price list items to database"""
    for item_data in items:
        existing = (
            db.query(SurgeryPrice)
            .filter(SurgeryPrice.g_drg_code == item_data['g_drg_code'])
            .first()
        )
        
        if existing:
            # Update existing item
            for key, value in item_data.items():
                setattr(existing, key, value)
            existing.is_active = True
        else:
            # Create new item
            new_item = SurgeryPrice(**item_data)
            db.add(new_item)
    
    db.commit()


def upload_product_prices(db: Session, items: List[Dict]):
    """Upload product price list items to database"""
    if not items:
        return
    
    for item_data in items:
        try:
            # Products use medication_code instead of g_drg_code
            medication_code = item_data.get('medication_code')
            if not medication_code:
                # Try g_drg_code as fallback for backward compatibility
                medication_code = item_data.get('g_drg_code')
            
            if not medication_code:
                print(f"Warning: Skipping item without medication_code. Keys: {list(item_data.keys())}")
                continue
            
            # Make sure medication_code is in the item_data for model creation
            item_data['medication_code'] = medication_code
            
            # For backward compatibility with old table structure:
            # Set g_drg_code to medication_code (old tables may have NOT NULL constraint)
            item_data['g_drg_code'] = medication_code
            # Set service_name to product_name (old tables may have NOT NULL constraint)
            if 'product_name' in item_data:
                item_data['service_name'] = item_data['product_name']
            
            # Set other service-related fields to None (they're nullable in old structure)
            item_data['service_type'] = None
            item_data['service_id'] = None
            item_data['service_ty'] = None
            item_data['nhia_claim_co_payment'] = None  # Products don't have co-payment
            item_data['clinic_bill_effective'] = None
                
            existing = (
                db.query(ProductPrice)
                .filter(ProductPrice.medication_code == medication_code)
                .first()
            )
            
            if existing:
                # Update existing item
                for key, value in item_data.items():
                    if hasattr(existing, key):  # Only update fields that exist in the model
                        setattr(existing, key, value)
                existing.is_active = True
            else:
                # Create new item - include valid fields AND legacy fields for backward compatibility
                valid_fields = {
                    'sr_no', 'sub_category_1', 'sub_category_2', 'product_id', 
                    'product_name', 'medication_code', 'formulation', 'strength',
                    'base_rate', 'nhia_app', 'claim_amount', 'nhia_claim', 'bill_effective',
                    'insurance_covered',  # New field for insurance coverage
                    # Legacy fields for backward compatibility with existing table structure
                    'g_drg_code', 'service_name', 'service_type', 'service_id', 
                    'service_ty', 'nhia_claim_co_payment', 'clinic_bill_effective'
                }
                filtered_data = {k: v for k, v in item_data.items() if k in valid_fields}
                
                # Ensure service_name is set (database may require it)
                if 'service_name' not in filtered_data or filtered_data['service_name'] is None:
                    filtered_data['service_name'] = filtered_data.get('product_name', '')
                
                # Verify required fields
                if 'medication_code' not in filtered_data:
                    raise ValueError(f"Missing medication_code in item: {item_data}")
                if 'product_name' not in filtered_data:
                    raise ValueError(f"Missing product_name in item: {item_data}")
                
                new_item = ProductPrice(**filtered_data)
                db.add(new_item)
        except Exception as e:
            print(f"Error processing product item: {item_data}")
            print(f"Error: {str(e)}")
            raise
    
    db.commit()


def upload_unmapped_drg_prices(db: Session, items: List[Dict]):
    """Upload unmapped DRG price list items to database"""
    for item_data in items:
        existing = (
            db.query(UnmappedDRGPrice)
            .filter(UnmappedDRGPrice.g_drg_code == item_data['g_drg_code'])
            .first()
        )
        
        if existing:
            # Update existing item
            for key, value in item_data.items():
                setattr(existing, key, value)
            existing.is_active = True
        else:
            # Create new item
            new_item = UnmappedDRGPrice(**item_data)
            db.add(new_item)
    
    db.commit()


def get_price_from_all_tables(db: Session, item_code: str, is_insured: bool = False) -> float:
    """
    Get price for an item code from any price list table based on insurance status
    
    For cash patients: returns Base Rate
    For insured patients: returns Co-Payment (top-up amount that insured patient pays)
    
    For products (drugs):
    - Insured clients: Returns top-up amount (nhia_claim_co_payment), or 0 if null
    - Non-insured clients: Returns base_rate
    """
    print(f"DEBUG get_price_from_all_tables: item_code='{item_code}', is_insured={is_insured}")
    
    # Search in procedure, surgery, and unmapped_drg tables (use g_drg_code)
    tables = [
        ("ProcedurePrice", db.query(ProcedurePrice).filter(ProcedurePrice.g_drg_code == item_code, ProcedurePrice.is_active == True)),
        ("SurgeryPrice", db.query(SurgeryPrice).filter(SurgeryPrice.g_drg_code == item_code, SurgeryPrice.is_active == True)),
        ("UnmappedDRGPrice", db.query(UnmappedDRGPrice).filter(UnmappedDRGPrice.g_drg_code == item_code, UnmappedDRGPrice.is_active == True)),
    ]
    
    for table_name, query in tables:
        item = query.first()
        if item:
            print(f"DEBUG: Found item in {table_name} table")
            if is_insured:
                # For insured patients: use Co-Payment (top-up amount)
                # If Co-Payment is not available, fall back to Base Rate
                if item.nhia_claim_co_payment is not None:
                    print(f"DEBUG: Returning co-payment from {table_name}: {item.nhia_claim_co_payment}")
                    return float(item.nhia_claim_co_payment)
                else:
                    # Fallback to base rate if co-payment not specified
                    print(f"DEBUG: No co-payment, returning base_rate from {table_name}: {item.base_rate}")
                    return float(item.base_rate)
            else:
                # For cash patients: use Base Rate
                print(f"DEBUG: Returning base_rate from {table_name}: {item.base_rate}")
                return float(item.base_rate)
    
    print(f"DEBUG: Item not found in procedure/surgery/unmapped_drg tables, checking ProductPrice table")
    
    # Search in product table (uses medication_code)
    product = db.query(ProductPrice).filter(
        ProductPrice.medication_code == item_code, 
        ProductPrice.is_active == True
    ).first()
    
    if not product:
        print(f"Product NOT FOUND - Code: {item_code}")
        return 0.0
    
    # Check if product is covered by insurance
    insurance_covered = product.insurance_covered
    # Normalize: strip whitespace, convert to lowercase, handle None/empty
    insurance_covered_str = None
    if insurance_covered:
        insurance_covered_str = str(insurance_covered).strip().lower()
        # Handle empty strings
        if insurance_covered_str == '':
            insurance_covered_str = None
    
    # Debug logging
    print(f"Product pricing - Code: {item_code}, Insurance Covered: '{insurance_covered_str}' (raw: '{insurance_covered}', type: {type(insurance_covered)}), Is Insured: {is_insured}, Base Rate: {product.base_rate}")
    
    # Check if product is NOT covered by insurance (case-insensitive, handles 'no', 'NO', ' No ', etc.)
    if insurance_covered_str == 'no':
        # If product is not covered by insurance, always charge base_rate regardless of patient insurance status
        base_rate_value = float(product.base_rate) if product.base_rate is not None else 0.0
        print(f"Product NOT covered by insurance - returning base_rate: {base_rate_value}")
        if base_rate_value <= 0:
            print(f"WARNING: base_rate is 0 or None for product {item_code} - this may prevent bill generation")
        return base_rate_value
    
    # Product is covered by insurance (or insurance_covered is null/yes)
    if is_insured:
        # For insured clients: use top-up (nhia_claim_co_payment)
        # If top-up is null, billed amount is 0
        if product.nhia_claim_co_payment is not None:
            print(f"Insured patient - returning co-payment: {product.nhia_claim_co_payment}")
            return float(product.nhia_claim_co_payment)
        else:
            print(f"Insured patient - no co-payment, returning 0.0")
            return 0.0
    else:
        # For non-insured clients: use Base Rate
        base_rate_value = float(product.base_rate) if product.base_rate is not None else 0.0
        print(f"Cash patient - returning base_rate: {base_rate_value}")
        return base_rate_value
    
    return 0.0


def search_price_items_all_tables(db: Session, search_term: str = None, service_type: str = None, file_type: str = None):
    """
    Search price list items across all tables
    file_type: procedure, surgery, product, unmapped_drg, or None (search all)
    """
    results = []
    
    # Determine which tables to search
    if file_type == 'procedure' or file_type is None:
        query = db.query(ProcedurePrice).filter(ProcedurePrice.is_active == True)
        if search_term:
            query = query.filter(
                (ProcedurePrice.g_drg_code.contains(search_term)) |
                (ProcedurePrice.service_name.contains(search_term))
            )
        if service_type:
            query = query.filter(ProcedurePrice.service_type == service_type)
        results.extend([('procedure', item) for item in query.all()])
    
    if file_type == 'surgery' or file_type is None:
        query = db.query(SurgeryPrice).filter(SurgeryPrice.is_active == True)
        if search_term:
            query = query.filter(
                (SurgeryPrice.g_drg_code.contains(search_term)) |
                (SurgeryPrice.service_name.contains(search_term))
            )
        if service_type:
            query = query.filter(SurgeryPrice.service_type == service_type)
        results.extend([('surgery', item) for item in query.all()])
    
    if file_type == 'product' or file_type is None:
        query = db.query(ProductPrice).filter(ProductPrice.is_active == True)
        if search_term:
            query = query.filter(
                (ProductPrice.medication_code.contains(search_term)) |
                (ProductPrice.product_name.contains(search_term)) |
                (ProductPrice.product_id.contains(search_term))
            )
        # Products don't have service_type, but can filter by sub_category
        # Use case-insensitive comparison for flexibility
        if service_type:
            query = query.filter(
                (func.lower(ProductPrice.sub_category_1) == func.lower(service_type)) |
                (func.lower(ProductPrice.sub_category_2) == func.lower(service_type))
            )
        results.extend([('product', item) for item in query.all()])
    
    if file_type == 'unmapped_drg' or file_type is None:
        query = db.query(UnmappedDRGPrice).filter(UnmappedDRGPrice.is_active == True)
        if search_term:
            query = query.filter(
                (UnmappedDRGPrice.g_drg_code.contains(search_term)) |
                (UnmappedDRGPrice.service_name.contains(search_term))
            )
        if service_type:
            query = query.filter(UnmappedDRGPrice.service_type == service_type)
        results.extend([('unmapped_drg', item) for item in query.all()])
    
    return results

