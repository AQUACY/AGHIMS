"""
New Price list service for separate table structure
Handles different Excel file types with all columns preserved
"""
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import UploadFile
from typing import List, Dict, Optional
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
    - Nested parens after the pipe are supported, e.g.
      "Cotrimoxazole Tablet (400+80) mg (COTRIMTA1 | Cotrimoxazole Tablet (400+80) mg)"

    Returns: (medication_code, clean_product_name)
    """
    import re

    if not product_name:
        return None, None

    product_name = product_name.strip()

    # Prefer the last "(CODE |" occurrence so nested parentheses inside the
    # trailing label (e.g. "(400+80) mg") do not break extraction.
    pipe_matches = list(re.finditer(r'\(([A-Z0-9]{3,20})\s*\|\s*', product_name))
    if pipe_matches:
        match = pipe_matches[-1]
        medication_code = match.group(1).strip()
        clean_name = product_name[: match.start()].strip()
        return medication_code, clean_name or product_name

    # Try alternative pattern: just (CODE) at the end if pipe pattern not found
    alt_pattern = r'\(([A-Z0-9]{3,20})\)\s*$'
    alt_match = re.search(alt_pattern, product_name)
    if alt_match:
        medication_code = alt_match.group(1).strip()
        clean_name = re.sub(r'\s*\([A-Z0-9]+\)\s*$', '', product_name).strip()
        return medication_code, clean_name

    # If pattern not found, return None for code, full name as product name
    return None, product_name


def parse_product_excel(df: pd.DataFrame, original_columns: List[str]) -> Dict:
    """
    Parse product/medication Excel/CSV with product-specific columns.

    Returns:
        {
          "items": [parsed item dicts],
          "failed": [{"row": int, "product_name": str, "medication_code": str|None, "reason": str}]
        }
    """
    items = []
    failed = []

    # Map product-specific columns
    sr_no_col = None
    sub_categ_1_col = None
    sub_categ_2_col = None
    product_id_col = None
    product_n_col = None          # "Product N" with embedded code
    product_name_only_col = None  # clean "Product Name"
    medication_code_col = None    # dedicated "Medication Code"
    formulation_col = None
    strength_col = None
    base_rate_col = None
    nhia_app_col = None
    claim_amount_col = None
    nhia_claim_col = None
    nhia_co_pay_col = None
    bill_effective_col = None
    insurance_covered_col = None

    for i, orig_col in enumerate(original_columns):
        col = df.columns[i]
        col_lower = col.lower()
        orig_col_lower = str(orig_col).strip().lower()

        if 'sr_no' in col_lower or 'sr.' in orig_col_lower:
            sr_no_col = col

        elif ('sub_categ' in col_lower or 'subcategory' in col_lower) and not sub_categ_1_col:
            sub_categ_1_col = col

        elif ('sub_categ' in col_lower or 'subcategory' in col_lower) and sub_categ_1_col:
            sub_categ_2_col = col

        elif 'product_id' in col_lower or 'productid' in col_lower:
            product_id_col = col

        # IMPORTANT: do not treat "product_name" as "product_n"
        # ('product_n' is a substring of 'product_name')
        elif col_lower == 'product_n' or orig_col_lower in ('product n', 'product_n'):
            product_n_col = col

        elif col_lower == 'product_name' or orig_col_lower in ('product name', 'product_name'):
            product_name_only_col = col

        elif (
            ('medication' in col_lower and 'code' in col_lower)
            or orig_col_lower in ('medication code', 'medication_code')
        ):
            medication_code_col = col

        elif 'formulati' in col_lower or 'formulation' in col_lower:
            formulation_col = col

        elif 'strength' in col_lower:
            strength_col = col

        elif 'base_rate' in col_lower or (orig_col_lower.startswith('base') and 'rate' in orig_col_lower):
            base_rate_col = col

        elif 'nhia_app' in col_lower or 'nhia_approved' in col_lower or \
             (orig_col_lower.startswith('nhia') and ('app' in orig_col_lower or 'approved' in orig_col_lower)):
            nhia_app_col = col

        elif 'claim_am' in col_lower or 'claim_amount' in col_lower or \
             (orig_col_lower.startswith('claim') and 'am' in orig_col_lower):
            claim_amount_col = col

        elif 'nhia_clain' in col_lower or (
            'nhia' in orig_col_lower and 'clain' in orig_col_lower
            and 'co' not in orig_col_lower and 'pay' not in orig_col_lower
        ):
            nhia_claim_col = col

        elif (
            'nhia_claim' in col_lower or 'nhia_co' in col_lower
            or 'co_payment' in col_lower or 'copayment' in col_lower
            or (
                'nhia' in orig_col_lower
                and ('claim' in orig_col_lower or 'co' in orig_col_lower or 'pay' in orig_col_lower)
                and 'clain' not in orig_col_lower
            )
        ):
            # Avoid stealing plain "NHIA Claim" when "NHIA Claim Co-Payment" exists:
            # if column is exactly nhia_claim / "nhia claim", treat as string claim field.
            if col_lower in ('nhia_claim',) or orig_col_lower in ('nhia claim', 'nhia_claim'):
                if not nhia_claim_col:
                    nhia_claim_col = col
            else:
                nhia_co_pay_col = col

        elif 'bill_effecti' in col_lower or 'bill_effective' in col_lower:
            bill_effective_col = col

        elif 'insurance_covered' in col_lower or 'insurancecovered' in col_lower or \
             'insurance_cover' in col_lower or 'insurance cover' in col_lower or \
             (orig_col_lower.startswith('insurance') and 'covered' in orig_col_lower) or \
             (orig_col_lower.startswith('insurance') and 'cover' in orig_col_lower):
            insurance_covered_col = col

        # Legacy truncated "Product N" style headers without colliding with Product Name
        elif (
            product_n_col is None
            and product_name_only_col is None
            and 'product' in orig_col_lower
            and orig_col_lower.startswith('product')
            and len(orig_col_lower) < 12
            and 'id' not in orig_col_lower
            and 'name' not in orig_col_lower
        ):
            product_n_col = col

    product_name_col = product_n_col or product_name_only_col
    if not product_name_col and not medication_code_col:
        raise ValueError(
            "Missing required columns: need 'Product N' / 'Product Name', "
            "or a 'Medication Code' column."
        )

    print("DEBUG: Detected columns for product price list:")
    print(f"  - Product N: {product_n_col}")
    print(f"  - Product Name: {product_name_only_col}")
    print(f"  - Medication Code: {medication_code_col}")
    print(f"  - Insurance Covered: {insurance_covered_col}")
    print(f"  - Base Rate: {base_rate_col}")
    print(f"  - All columns: {list(df.columns)}")

    for idx, row in df.iterrows():
        row_num = int(idx) + 2  # Excel-style (header is row 1)

        # Resolve display / source name
        name_from_n = None
        name_from_only = None
        if product_n_col and product_n_col in df.columns and not pd.isna(row[product_n_col]):
            name_from_n = str(row[product_n_col]).strip()
        if product_name_only_col and product_name_only_col in df.columns and not pd.isna(row[product_name_only_col]):
            name_from_only = str(row[product_name_only_col]).strip()

        product_name_raw = name_from_n or name_from_only or ''
        if not product_name_raw or product_name_raw.lower() in ('product n', 'product name', 'name', 'nan'):
            # Allow rows that only have medication code + empty name? still skip empty
            code_only = None
            if medication_code_col and medication_code_col in df.columns and not pd.isna(row[medication_code_col]):
                code_only = str(row[medication_code_col]).strip()
            if not code_only:
                continue
            failed.append({
                "row": row_num,
                "product_name": "",
                "medication_code": code_only,
                "reason": "Missing product name (Product N / Product Name)",
            })
            continue

        # Medication code resolution order:
        # 1) dedicated Medication Code column
        # 2) extract from Product N (preferred) then Product Name
        # 3) Product ID fallback
        medication_code = None
        if medication_code_col and medication_code_col in df.columns and not pd.isna(row[medication_code_col]):
            code_val = str(row[medication_code_col]).strip()
            if code_val and code_val.lower() not in ('nan', 'none', 'medication code'):
                medication_code = code_val.upper()

        if not medication_code:
            for candidate in (name_from_n, name_from_only):
                if not candidate:
                    continue
                extracted, _ = extract_medication_code_from_product_name(candidate)
                if extracted:
                    medication_code = extracted
                    break

        if not medication_code:
            if product_id_col and product_id_col in df.columns and not pd.isna(row[product_id_col]):
                medication_code = str(row[product_id_col]).strip()
            else:
                failed.append({
                    "row": row_num,
                    "product_name": product_name_raw,
                    "medication_code": None,
                    "reason": (
                        "Could not find medication code. Provide a 'Medication Code' column "
                        "or embed code in Product N as '(CODE | Name)'."
                    ),
                })
                continue

        # Prefer clean Product Name for storage; else Product N without code suffix
        if name_from_only:
            stored_name = name_from_only
        else:
            _, clean = extract_medication_code_from_product_name(product_name_raw)
            stored_name = clean or product_name_raw

        item = {
            'medication_code': medication_code,
            'product_name': stored_name,
            '_source_row': row_num,
        }

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

        item['base_rate'] = 0.0
        if base_rate_col and base_rate_col in df.columns:
            try:
                val = row[base_rate_col]
                if pd.notna(val):
                    item['base_rate'] = float(val)
            except (ValueError, TypeError):
                item['base_rate'] = 0.0

        item['nhia_app'] = None
        if nhia_app_col and nhia_app_col in df.columns:
            try:
                val = row[nhia_app_col]
                if pd.notna(val):
                    item['nhia_app'] = float(val)
            except (ValueError, TypeError):
                item['nhia_app'] = None

        item['claim_amount'] = None
        if claim_amount_col and claim_amount_col in df.columns:
            try:
                val = row[claim_amount_col]
                if pd.notna(val):
                    item['claim_amount'] = float(val)
            except (ValueError, TypeError):
                item['claim_amount'] = None

        if nhia_claim_col and nhia_claim_col in df.columns and not pd.isna(row[nhia_claim_col]):
            item['nhia_claim'] = str(row[nhia_claim_col]).strip()
        else:
            item['nhia_claim'] = None

        item['nhia_claim_co_payment'] = 0.0
        if nhia_co_pay_col and nhia_co_pay_col in df.columns:
            try:
                val = row[nhia_co_pay_col]
                if pd.notna(val):
                    item['nhia_claim_co_payment'] = float(val)
            except (ValueError, TypeError):
                item['nhia_claim_co_payment'] = 0.0

        if bill_effective_col and bill_effective_col in df.columns and not pd.isna(row[bill_effective_col]):
            item['bill_effective'] = str(row[bill_effective_col]).strip()
        else:
            item['bill_effective'] = None

        if insurance_covered_col and insurance_covered_col in df.columns:
            insurance_val_raw = row[insurance_covered_col]
            if pd.isna(insurance_val_raw) or (isinstance(insurance_val_raw, str) and insurance_val_raw.strip() == ''):
                item['insurance_covered'] = 'yes'
            else:
                insurance_val_lower = str(insurance_val_raw).strip().lower()
                if insurance_val_lower in ['no', 'n', 'false', '0', 'f']:
                    item['insurance_covered'] = 'no'
                elif insurance_val_lower in ['yes', 'y', 'true', '1', 't']:
                    item['insurance_covered'] = 'yes'
                else:
                    item['insurance_covered'] = 'yes'
        else:
            item['insurance_covered'] = 'yes'

        items.append(item)

    if not items and not failed:
        raise ValueError("No valid items found in the file. Please check the file format.")

    return {"items": items, "failed": failed}

def parse_excel_price_list_complete(file: UploadFile, file_type: str) -> Dict:
    """
    Parse Excel/CSV file and return price items with ALL columns preserved.

    Returns:
        {
          "items": [...],
          "failed": [...]   # parse-time failures (mainly products)
        }
    """
    import io
    file_content = file.file.read()
    file.file.seek(0)

    filename = (file.filename or "").lower()
    if filename.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(file_content))
    else:
        df = pd.read_excel(io.BytesIO(file_content))

    # Normalize column names (handle variations)
    original_columns = df.columns.tolist()
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace('-', '_')

    # If file_type is explicitly "product", always use product parsing
    if file_type == "product":
        try:
            return parse_product_excel(df, original_columns)
        except Exception as e:
            raise ValueError(
                f"Error parsing product file: {str(e)}. "
                "Make sure the file has 'Product N' / 'Product Name' and/or 'Medication Code'."
            )

    # Check if this is a product file (has Product N, Product ID, Sub Categ columns)
    is_product_file = any(
        col in ('product_n', 'product_id', 'product_name', 'medication_code')
        or col.startswith('sub_categ')
        for col in df.columns
    ) or any(
        ('product' in str(col).lower() and ('n' in str(col).lower() or 'id' in str(col).lower() or 'name' in str(col).lower()))
        or ('sub' in str(col).lower() and 'categ' in str(col).lower())
        or ('medication' in str(col).lower() and 'code' in str(col).lower())
        for col in original_columns
    )

    if is_product_file:
        try:
            return parse_product_excel(df, original_columns)
        except Exception as e:
            raise ValueError(
                f"Error parsing product file: {str(e)}. "
                "Make sure the file has 'Product N' / 'Product Name' and/or 'Medication Code'."
            )

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
    claim_amount_col = None
    nhia_app_col = None
    nhia_co_pay_col = None
    clinic_col = None
    insurance_covered_col = None
    
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
        
        # Claim Amount (must be before NHIA Claim Co-Payment matcher)
        elif 'claim_amount' in col_lower or 'claim_am' in col_lower or \
             (orig_col_lower.startswith('claim') and 'amount' in orig_col_lower):
            claim_amount_col = col
        
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
        
        # Insurance Covered - Check multiple variations
        elif 'insurance_covered' in col_lower or 'insurancecovered' in col_lower or \
             ('insurance' in orig_col_lower and 'covered' in orig_col_lower):
            insurance_covered_col = col
    
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
        
        # Claim Amount
        item['claim_amount'] = None
        if claim_amount_col and claim_amount_col in df.columns:
            try:
                val = row[claim_amount_col]
                if pd.notna(val):
                    item['claim_amount'] = float(val)
            except (ValueError, TypeError):
                item['claim_amount'] = None
        
        # NHIA Claim Co-Payment (preserve 0 as 0.0, not None)
        item['nhia_claim_co_payment'] = 0.0  # Default to 0.0 instead of None
        if nhia_co_pay_col and nhia_co_pay_col in df.columns:
            try:
                val = row[nhia_co_pay_col]
                if pd.notna(val):
                    # Convert to float and preserve 0 as 0.0
                    co_payment_val = float(val)
                    item['nhia_claim_co_payment'] = co_payment_val  # This will be 0.0 if value is 0
                # If pd.isna(val), keep default 0.0
            except (ValueError, TypeError):
                # If conversion fails, keep default 0.0
                item['nhia_claim_co_payment'] = 0.0
        
        # Clinic Bill Effective
        if clinic_col and clinic_col in df.columns and not pd.isna(row[clinic_col]):
            item['clinic_bill_effective'] = str(row[clinic_col]).strip()
        else:
            item['clinic_bill_effective'] = None
        
        # Insurance Covered (default to "yes" if not specified)
        if insurance_covered_col and insurance_covered_col in df.columns:
            insurance_val_raw = row[insurance_covered_col]
            if pd.notna(insurance_val_raw):
                insurance_val = str(insurance_val_raw).strip().lower()
                if insurance_val in ['no', 'n', 'false', '0']:
                    item['insurance_covered'] = 'no'
                else:
                    item['insurance_covered'] = 'yes'
            else:
                item['insurance_covered'] = 'yes'  # Default to "yes" if empty
        else:
            item['insurance_covered'] = 'yes'  # Default to "yes" if column not found
        
        items.append(item)
    
    if not items:
        raise ValueError("No valid items found in the Excel file. Please check the file format.")

    return {"items": items, "failed": []}


def upload_procedure_prices(db: Session, items: List[Dict]):
    """Upload procedure price list items to database"""
    for item_data in items:
        existing = (
            db.query(ProcedurePrice)
            .filter(ProcedurePrice.g_drg_code == item_data['g_drg_code'])
            .first()
        )
        
        # Ensure insurance_covered is set (default to "yes" if not provided)
        if 'insurance_covered' not in item_data or not item_data['insurance_covered']:
            item_data['insurance_covered'] = 'yes'
        
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


def upload_product_prices(db: Session, items: List[Dict]) -> Dict:
    """
    Upload product price list items to database.

    Returns report:
      {created: int, updated: int, failed: [...], passed: [...]}
    """
    created = 0
    updated = 0
    failed = []
    passed = []

    if not items:
        return {"created": 0, "updated": 0, "failed": [], "passed": []}

    valid_fields = {
        'sr_no', 'sub_category_1', 'sub_category_2', 'product_id',
        'product_name', 'medication_code', 'formulation', 'strength',
        'base_rate', 'nhia_app', 'claim_amount', 'nhia_claim', 'bill_effective',
        'insurance_covered',
        'g_drg_code', 'service_name', 'service_type', 'service_id',
        'service_ty', 'nhia_claim_co_payment', 'clinic_bill_effective'
    }

    for item_data in items:
        # Copy so we can safely pop metadata without mutating caller unexpectedly across retries
        row = dict(item_data)
        source_row = row.pop('_source_row', None)
        medication_code = row.get('medication_code') or row.get('g_drg_code')
        product_name = row.get('product_name')

        try:
            if not medication_code:
                failed.append({
                    "row": source_row,
                    "product_name": product_name,
                    "medication_code": None,
                    "reason": "Missing medication_code",
                })
                continue

            if not product_name:
                failed.append({
                    "row": source_row,
                    "product_name": product_name,
                    "medication_code": medication_code,
                    "reason": "Missing product_name",
                })
                continue

            row['medication_code'] = medication_code
            row['g_drg_code'] = medication_code
            row['service_name'] = product_name
            row['service_type'] = None
            row['service_id'] = None
            row['service_ty'] = None
            if row.get('nhia_claim_co_payment') is None:
                row['nhia_claim_co_payment'] = 0.0
            row['clinic_bill_effective'] = None

            # Savepoint so one bad row does not wipe prior successful rows
            nested = db.begin_nested()
            try:
                existing = (
                    db.query(ProductPrice)
                    .filter(ProductPrice.medication_code == medication_code)
                    .first()
                )

                if existing:
                    for key, value in row.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                    existing.is_active = True
                    action = "updated"
                    updated += 1
                else:
                    filtered_data = {k: v for k, v in row.items() if k in valid_fields}
                    if not filtered_data.get('service_name'):
                        filtered_data['service_name'] = filtered_data.get('product_name', '')
                    new_item = ProductPrice(**filtered_data)
                    db.add(new_item)
                    action = "created"
                    created += 1

                nested.commit()
            except Exception:
                nested.rollback()
                raise

            passed.append({
                "row": source_row,
                "product_name": product_name,
                "medication_code": medication_code,
                "action": action,
            })
        except Exception as e:
            failed.append({
                "row": source_row,
                "product_name": product_name,
                "medication_code": medication_code,
                "reason": str(e),
            })

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        for p in passed:
            failed.append({
                "row": p.get("row"),
                "product_name": p.get("product_name"),
                "medication_code": p.get("medication_code"),
                "reason": f"Commit failed: {str(e)}",
            })
        return {"created": 0, "updated": 0, "failed": failed, "passed": []}

    return {
        "created": created,
        "updated": updated,
        "failed": failed,
        "passed": passed,
    }


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


def get_price_from_all_tables(db: Session, item_code: str, is_insured: bool = False, service_type: Optional[str] = None, procedure_name: Optional[str] = None) -> float:
    """
    Get price for an item code from any price list table based on insurance status
    
    For cash patients: returns Base Rate
    For insured patients: returns Co-Payment (top-up amount that insured patient pays)
    
    For products (drugs):
    - Insured clients: Returns top-up amount (nhia_claim_co_payment), or 0 if null
    - Non-insured clients: Returns base_rate
    
    Args:
        db: Database session
        item_code: G-DRG code or medication code
        is_insured: Whether the patient is insured
        service_type: Optional service type (department/clinic) to filter by for procedures
        procedure_name: Optional procedure/service name to match exactly (helps when G-DRG codes map to multiple procedures)
    """
    print(f"DEBUG get_price_from_all_tables: item_code='{item_code}', is_insured={is_insured}, service_type='{service_type}', procedure_name='{procedure_name}'")
    
    # Search in procedure, surgery, and unmapped_drg tables (use g_drg_code)
    # If service_type is provided, filter by it to get the correct price for that department/clinic
    # If procedure_name is provided, also match by service_name for exact match
    procedure_query = db.query(ProcedurePrice).filter(
        ProcedurePrice.g_drg_code == item_code,
        ProcedurePrice.is_active == True
    )
    if service_type:
        procedure_query = procedure_query.filter(ProcedurePrice.service_type == service_type)
    if procedure_name:
        # Match procedure name exactly (case-insensitive, trimmed)
        procedure_query = procedure_query.filter(func.lower(func.trim(ProcedurePrice.service_name)) == func.lower(func.trim(procedure_name)))
    
    surgery_query = db.query(SurgeryPrice).filter(
        SurgeryPrice.g_drg_code == item_code,
        SurgeryPrice.is_active == True
    )
    if service_type:
        surgery_query = surgery_query.filter(SurgeryPrice.service_type == service_type)
    if procedure_name:
        # Match procedure name exactly (case-insensitive, trimmed)
        surgery_query = surgery_query.filter(func.lower(func.trim(SurgeryPrice.service_name)) == func.lower(func.trim(procedure_name)))
    
    unmapped_query = db.query(UnmappedDRGPrice).filter(
        UnmappedDRGPrice.g_drg_code == item_code,
        UnmappedDRGPrice.is_active == True
    )
    if service_type:
        unmapped_query = unmapped_query.filter(UnmappedDRGPrice.service_type == service_type)
    if procedure_name:
        # Match procedure name exactly (case-insensitive, trimmed)
        unmapped_query = unmapped_query.filter(func.lower(func.trim(UnmappedDRGPrice.service_name)) == func.lower(func.trim(procedure_name)))
    
    tables = [
        ("ProcedurePrice", procedure_query),
        ("SurgeryPrice", surgery_query),
        ("UnmappedDRGPrice", unmapped_query),
    ]
    
    for table_name, query in tables:
        item = query.first()
        if item:
            print(f"DEBUG: Found item in {table_name} table with service_type='{service_type}'")
            
            # Check insurance_covered status (only for ProcedurePrice)
            insurance_covered = None
            if table_name == "ProcedurePrice":
                insurance_covered = getattr(item, 'insurance_covered', None)
                if insurance_covered:
                    insurance_covered = str(insurance_covered).strip().lower()
                else:
                    insurance_covered = 'yes'  # Default to 'yes' if not set
            else:
                # For SurgeryPrice and UnmappedDRGPrice, assume insurance_covered = 'yes' (they don't have this field)
                insurance_covered = 'yes'
            
            # If insurance_covered = "no", always charge base_rate regardless of insurance status
            if insurance_covered == 'no':
                print(f"DEBUG: insurance_covered='no' for {table_name}, returning base_rate: {item.base_rate}")
                return float(item.base_rate)
            
            # If insurance_covered = "yes" (or not set), use normal logic
            if is_insured:
                # For insured patients: use Co-Payment (top-up amount)
                # If Co-Payment is 0 or not available, return 0 (free for insured)
                # CRITICAL: Never return base_rate for insured patients when insurance_covered = "yes"
                if item.nhia_claim_co_payment is not None:
                    co_payment = float(item.nhia_claim_co_payment)
                    print(f"DEBUG: Returning co-payment from {table_name}: {co_payment} (insurance_covered={insurance_covered}, is_insured={is_insured}, base_rate={item.base_rate})")
                    # Explicitly return 0.0 if co-payment is 0 (even if it's 0.0, we want to return 0.0, not base_rate)
                    # This ensures insured patients with co-payment=0 are charged 0.0, not base_rate
                    if co_payment == 0.0:
                        print(f"DEBUG: Co-payment is 0.0, explicitly returning 0.0 (NOT base_rate={item.base_rate}) for insured patient")
                    return co_payment  # This will be 0.0 if co-payment is 0
                else:
                    # No co-payment specified means free for insured patients
                    print(f"DEBUG: No co-payment specified (None), returning 0.0 (free for insured) from {table_name} (insurance_covered={insurance_covered}, base_rate={item.base_rate})")
                    return 0.0
            else:
                # For cash patients: use Base Rate
                print(f"DEBUG: Returning base_rate from {table_name}: {item.base_rate}")
                return float(item.base_rate)
    
    # If service_type or procedure_name was provided but no match found, try fallback strategies
    if service_type or procedure_name:
        # Strategy 1: Try with procedure_name but without service_type filter
        if service_type and procedure_name:
            print(f"DEBUG: No match found with service_type='{service_type}' and procedure_name='{procedure_name}', trying with procedure_name only")
            fallback_tables = [
                ("ProcedurePrice", db.query(ProcedurePrice).filter(
                    ProcedurePrice.g_drg_code == item_code,
                    ProcedurePrice.is_active == True,
                    func.lower(func.trim(ProcedurePrice.service_name)) == func.lower(func.trim(procedure_name))
                )),
                ("SurgeryPrice", db.query(SurgeryPrice).filter(
                    SurgeryPrice.g_drg_code == item_code,
                    SurgeryPrice.is_active == True,
                    func.lower(func.trim(SurgeryPrice.service_name)) == func.lower(func.trim(procedure_name))
                )),
                ("UnmappedDRGPrice", db.query(UnmappedDRGPrice).filter(
                    UnmappedDRGPrice.g_drg_code == item_code,
                    UnmappedDRGPrice.is_active == True,
                    func.lower(func.trim(UnmappedDRGPrice.service_name)) == func.lower(func.trim(procedure_name))
                )),
            ]
            
            for table_name, query in fallback_tables:
                item = query.first()
                if item:
                    print(f"DEBUG: Found item in {table_name} table (with procedure_name='{procedure_name}', without service_type filter)")
                    
                    # Check insurance_covered status (only for ProcedurePrice)
                    insurance_covered = None
                    if table_name == "ProcedurePrice":
                        insurance_covered = getattr(item, 'insurance_covered', None)
                        if insurance_covered:
                            insurance_covered = str(insurance_covered).strip().lower()
                        else:
                            insurance_covered = 'yes'  # Default to 'yes' if not set
                    
                    # If insurance_covered = "no", always charge base_rate
                    if insurance_covered == 'no':
                        print(f"DEBUG: insurance_covered='no' for {table_name}, returning base_rate: {item.base_rate}")
                        return float(item.base_rate)
                    
                    # If insurance_covered = "yes", use normal logic
                    if is_insured:
                        if item.nhia_claim_co_payment is not None:
                            co_payment = float(item.nhia_claim_co_payment)
                            print(f"DEBUG: Returning co-payment from {table_name}: {co_payment}")
                            return co_payment
                        else:
                            print(f"DEBUG: No co-payment specified, returning 0.0 (free for insured) from {table_name}")
                            return 0.0
                    else:
                        print(f"DEBUG: Returning base_rate from {table_name}: {item.base_rate}")
                        return float(item.base_rate)
        
        # Strategy 2: Try with service_type but without procedure_name filter
        if service_type:
            print(f"DEBUG: No match found with service_type='{service_type}' and procedure_name='{procedure_name}', trying with service_type only")
            fallback_tables = [
                ("ProcedurePrice", db.query(ProcedurePrice).filter(
                    ProcedurePrice.g_drg_code == item_code,
                    ProcedurePrice.is_active == True,
                    ProcedurePrice.service_type == service_type
                )),
                ("SurgeryPrice", db.query(SurgeryPrice).filter(
                    SurgeryPrice.g_drg_code == item_code,
                    SurgeryPrice.is_active == True,
                    SurgeryPrice.service_type == service_type
                )),
                ("UnmappedDRGPrice", db.query(UnmappedDRGPrice).filter(
                    UnmappedDRGPrice.g_drg_code == item_code,
                    UnmappedDRGPrice.is_active == True,
                    UnmappedDRGPrice.service_type == service_type
                )),
            ]
            
            for table_name, query in fallback_tables:
                item = query.first()
                if item:
                    print(f"DEBUG: Found item in {table_name} table (with service_type='{service_type}', without procedure_name filter)")
                    
                    # Check insurance_covered status (only for ProcedurePrice)
                    insurance_covered = None
                    if table_name == "ProcedurePrice":
                        insurance_covered = getattr(item, 'insurance_covered', None)
                        if insurance_covered:
                            insurance_covered = str(insurance_covered).strip().lower()
                        else:
                            insurance_covered = 'yes'  # Default to 'yes' if not set
                    
                    # If insurance_covered = "no", always charge base_rate
                    if insurance_covered == 'no':
                        print(f"DEBUG: insurance_covered='no' for {table_name}, returning base_rate: {item.base_rate}")
                        return float(item.base_rate)
                    
                    # If insurance_covered = "yes", use normal logic
                    if is_insured:
                        if item.nhia_claim_co_payment is not None:
                            co_payment = float(item.nhia_claim_co_payment)
                            print(f"DEBUG: Returning co-payment from {table_name}: {co_payment}")
                            return co_payment
                        else:
                            print(f"DEBUG: No co-payment specified, returning 0.0 (free for insured) from {table_name}")
                            return 0.0
                    else:
                        print(f"DEBUG: Returning base_rate from {table_name}: {item.base_rate}")
                        return float(item.base_rate)
        
        # Strategy 3: Try without any filters (just G-DRG code)
        print(f"DEBUG: No match found with filters, trying without any filters (G-DRG code only)")
        fallback_tables = [
            ("ProcedurePrice", db.query(ProcedurePrice).filter(ProcedurePrice.g_drg_code == item_code, ProcedurePrice.is_active == True)),
            ("SurgeryPrice", db.query(SurgeryPrice).filter(SurgeryPrice.g_drg_code == item_code, SurgeryPrice.is_active == True)),
            ("UnmappedDRGPrice", db.query(UnmappedDRGPrice).filter(UnmappedDRGPrice.g_drg_code == item_code, UnmappedDRGPrice.is_active == True)),
        ]
        
        for table_name, query in fallback_tables:
            item = query.first()
            if item:
                print(f"DEBUG: Found item in {table_name} table (G-DRG code only, no filters)")
                
                # Check insurance_covered status (only for ProcedurePrice)
                insurance_covered = None
                if table_name == "ProcedurePrice":
                    insurance_covered = getattr(item, 'insurance_covered', None)
                    if insurance_covered:
                        insurance_covered = str(insurance_covered).strip().lower()
                    else:
                        insurance_covered = 'yes'  # Default to 'yes' if not set
                
                # If insurance_covered = "no", always charge base_rate
                if insurance_covered == 'no':
                    print(f"DEBUG: insurance_covered='no' for {table_name}, returning base_rate: {item.base_rate}")
                    return float(item.base_rate)
                
                # If insurance_covered = "yes", use normal logic
                if is_insured:
                    if item.nhia_claim_co_payment is not None:
                        co_payment = float(item.nhia_claim_co_payment)
                        print(f"DEBUG: Returning co-payment from {table_name}: {co_payment}")
                        return co_payment
                    else:
                        print(f"DEBUG: No co-payment specified, returning 0.0 (free for insured) from {table_name}")
                        return 0.0
                else:
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


def get_surgery_price(db: Session, g_drg_code: str, is_insured: bool = False, service_type: Optional[str] = None) -> float:
    """
    Get price for a surgery from SurgeryPrice table only (prioritizes surgery prices over procedure/day surgery prices)
    
    For cash patients: returns Base Rate
    For insured patients: returns Co-Payment (top-up amount that insured patient pays)
    
    Args:
        db: Database session
        g_drg_code: G-DRG code for the surgery
        is_insured: Whether the patient is insured
        service_type: Optional service type (department/clinic) to filter by
    """
    print(f"DEBUG get_surgery_price: g_drg_code='{g_drg_code}', is_insured={is_insured}, service_type='{service_type}'")
    
    # Search ONLY in SurgeryPrice table (not ProcedurePrice which may contain day surgeries)
    surgery_query = db.query(SurgeryPrice).filter(
        SurgeryPrice.g_drg_code == g_drg_code,
        SurgeryPrice.is_active == True
    )
    if service_type:
        surgery_query = surgery_query.filter(SurgeryPrice.service_type == service_type)
    
    surgery = surgery_query.first()
    
    if surgery:
        print(f"DEBUG: Found surgery in SurgeryPrice table with service_type='{service_type}'")
        if is_insured:
            # For insured patients: use Co-Payment (top-up amount)
            # If Co-Payment is 0 or not available, return 0 (free for insured)
            if surgery.nhia_claim_co_payment is not None:
                co_payment = float(surgery.nhia_claim_co_payment)
                print(f"DEBUG: Returning co-payment from SurgeryPrice: {co_payment}")
                return co_payment
            else:
                # No co-payment specified means free for insured patients
                print(f"DEBUG: No co-payment specified, returning 0.0 (free for insured) from SurgeryPrice")
                return 0.0
        else:
            # For cash patients: use Base Rate
            print(f"DEBUG: Returning base_rate from SurgeryPrice: {surgery.base_rate}")
            return float(surgery.base_rate)
    
    # If service_type was provided but no match found, try without service_type filter as fallback
    if service_type:
        print(f"DEBUG: No match found with service_type='{service_type}', trying without service_type filter")
        fallback_surgery = db.query(SurgeryPrice).filter(
            SurgeryPrice.g_drg_code == g_drg_code,
            SurgeryPrice.is_active == True
        ).first()
        
        if fallback_surgery:
            print(f"DEBUG: Found surgery in SurgeryPrice table (without service_type filter)")
            if is_insured:
                if fallback_surgery.nhia_claim_co_payment is not None:
                    co_payment = float(fallback_surgery.nhia_claim_co_payment)
                    print(f"DEBUG: Returning co-payment from SurgeryPrice: {co_payment}")
                    return co_payment
                else:
                    # No co-payment specified means free for insured patients
                    print(f"DEBUG: No co-payment specified, returning 0.0 (free for insured) from SurgeryPrice")
                    return 0.0
            else:
                print(f"DEBUG: Returning base_rate from SurgeryPrice: {fallback_surgery.base_rate}")
                return float(fallback_surgery.base_rate)
    
    print(f"DEBUG: Surgery NOT FOUND in SurgeryPrice table - Code: {g_drg_code}")
    return 0.0


def search_price_items_all_tables(
    db: Session,
    search_term: str = None,
    service_type: str = None,
    file_type: str = None,
    status_filter: str = "active",
):
    """
    Search price list items across all tables
    file_type: procedure, surgery, product, unmapped_drg, or None (search all)
    status_filter: "active" (default), "archived", or "all"
    """
    results = []
    status = (status_filter or "active").strip().lower()

    def apply_active_filter(query, model):
        if status == "archived":
            return query.filter(model.is_active == False)
        if status == "all":
            return query
        # default: active only
        return query.filter(model.is_active == True)

    # Determine which tables to search
    if file_type == 'procedure' or file_type is None:
        query = apply_active_filter(db.query(ProcedurePrice), ProcedurePrice)
        if search_term:
            query = query.filter(
                (ProcedurePrice.g_drg_code.contains(search_term)) |
                (ProcedurePrice.service_name.contains(search_term))
            )
        if service_type:
            query = query.filter(ProcedurePrice.service_type == service_type)
        results.extend([('procedure', item) for item in query.all()])

    if file_type == 'surgery' or file_type is None:
        query = apply_active_filter(db.query(SurgeryPrice), SurgeryPrice)
        if search_term:
            query = query.filter(
                (SurgeryPrice.g_drg_code.contains(search_term)) |
                (SurgeryPrice.service_name.contains(search_term))
            )
        if service_type:
            query = query.filter(SurgeryPrice.service_type == service_type)
        results.extend([('surgery', item) for item in query.all()])

    if file_type == 'product' or file_type is None:
        query = apply_active_filter(db.query(ProductPrice), ProductPrice)
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
        query = apply_active_filter(db.query(UnmappedDRGPrice), UnmappedDRGPrice)
        if search_term:
            query = query.filter(
                (UnmappedDRGPrice.g_drg_code.contains(search_term)) |
                (UnmappedDRGPrice.service_name.contains(search_term))
            )
        if service_type:
            query = query.filter(UnmappedDRGPrice.service_type == service_type)
        results.extend([('unmapped_drg', item) for item in query.all()])

    return results

