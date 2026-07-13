"""
Price list service for uploading and managing prices
"""
import pandas as pd
from sqlalchemy.orm import Session
from fastapi import UploadFile
from app.models.price_list import PriceListItem
from typing import List


def parse_excel_price_list(file: UploadFile, category: str) -> List[dict]:
    """
    Parse Excel file and return list of price items
    Supports two formats:
    1. New format: G-DRG Code, Service Type, Service ID, Service Name, Base Rate, NHIA App, NHIA Claim Co-Payment
    2. Old format: item_code, item_name, category, insured_price, cash_price
    """
    # Read Excel file (skip header row if needed, pandas will auto-detect)
    df = pd.read_excel(file.file)
    
    # Normalize column names (handle variations)
    original_columns = df.columns.tolist()
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace('-', '_')
    
    items = []
    
    # Check if this is the new format (with G-DRG Code, Service Type, Service Name)
    has_new_format = any(col in df.columns for col in ['g_drg_code', 'gdrg_code', 'service_type', 'service_name'])
    
    if has_new_format:
        # New format mapping - handle actual column positions
        # Expected columns: Sr.No., G-DRG Code, Service Ty, Service Type, Service ID, Service Name, Base Rate, NHIA App, etc.
        
        code_col = None
        service_type_col = None  # The department/clinic (second Service Type column)
        service_ty_col = None    # The first "Service Ty" column
        service_id_col = None
        name_col = None
        base_rate_col = None
        nhia_app_col = None
        nhia_co_pay_col = None
        
        # Check original column names too (before normalization)
        # Handle both normalized and original column names
        for i, orig_col in enumerate(original_columns):
            col = df.columns[i]
            col_lower = col.lower()
            orig_col_lower = str(orig_col).strip().lower()
            
            # G-DRG Code (handle variations like "G-DRG Code", "GDRG Code", etc.)
            if (('g_drg' in col_lower or 'gdrg' in col_lower) and 'code' in col_lower) or \
               ('g-drg' in orig_col_lower and 'code' in orig_col_lower) or \
               (orig_col_lower.startswith('g') and 'drg' in orig_col_lower and 'code' in orig_col_lower):
                code_col = col
            
            # Service Type columns - there are two, need to distinguish them
            # "Service Ty" (truncated, 3rd column) vs "Service Type" (full, 4th column - department/clinic)
            elif orig_col_lower.startswith('service') and ('type' in orig_col_lower or 'ty' in orig_col_lower):
                # Check if it's the truncated one ("Service Ty") or full one ("Service Type")
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
            
            # NHIA Claim Co-Payment (may be truncated in header)
            elif ('nhia_claim' in col_lower or 'nhia_co' in col_lower or 
                  'co_payment' in col_lower or 'copayment' in col_lower or
                  ('nhia' in orig_col_lower and ('claim' in orig_col_lower or 'co' in orig_col_lower or 'pay' in orig_col_lower))):
                nhia_co_pay_col = col
        
        # If we couldn't find the second Service Type, use the first one
        if not service_type_col and service_ty_col:
            service_type_col = service_ty_col
        
        # Validate required columns for new format
        if not code_col:
            raise ValueError("Missing required column: G-DRG Code. Please ensure your Excel file has a column named 'G-DRG Code'")
        if not name_col:
            raise ValueError("Missing required column: Service Name. Please ensure your Excel file has a column named 'Service Name'")
        
        # Process rows
        for idx, row in df.iterrows():
            # Skip empty rows or header rows
            if pd.isna(row[code_col]) or str(row[code_col]).strip() == '':
                continue
            
            # Skip if code looks like a header
            code_str = str(row[code_col]).strip()
            if code_str.lower() in ['g-drg code', 'g_drg_code', 'code', 'nan', 'none']:
                continue
                
            item_code = code_str
            item_name = str(row[name_col]).strip() if not pd.isna(row[name_col]) else ''
            
            if not item_name or item_name.lower() in ['service name', 'name', 'nan']:
                continue
            
            # Get prices
            # Base Rate = cash price
            cash_price = 0.0
            if base_rate_col and base_rate_col in df.columns:
                try:
                    val = row[base_rate_col]
                    if pd.notna(val):
                        cash_price = float(val)
                except (ValueError, TypeError):
                    cash_price = 0.0
            
            # NHIA Approved = insured price
            insured_price = 0.0
            if nhia_app_col and nhia_app_col in df.columns:
                try:
                    val = row[nhia_app_col]
                    if pd.notna(val):
                        insured_price = float(val)
                except (ValueError, TypeError):
                    insured_price = 0.0
            
            # If NHIA price not found, use base rate as fallback
            if insured_price == 0.0 and cash_price > 0:
                insured_price = cash_price
            
            # Get service type (department/clinic) if available
            service_type = None
            if service_type_col and service_type_col in df.columns and not pd.isna(row[service_type_col]):
                service_type_val = row[service_type_col]
                if pd.notna(service_type_val):
                    service_type = str(service_type_val).strip()
                    # Skip if it's a header
                    if service_type.lower() in ['service type', 'type', 'department', 'nan']:
                        service_type = None
            
            # Append service type (department/clinic) to item name for context
            if service_type:
                item_name_with_dept = f"{item_name} ({service_type})"
            else:
                item_name_with_dept = item_name
            
            items.append({
                'item_code': item_code,
                'item_name': item_name_with_dept,
                'category': category,
                'insured_price': insured_price,
                'cash_price': cash_price,
            })
    else:
        # Old format (backward compatibility)
        required_columns = ['item_code', 'item_name', 'insured_price', 'cash_price']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
        
        for idx, row in df.iterrows():
            # Skip empty rows
            if pd.isna(row['item_code']) or str(row['item_code']).strip() == '':
                continue
                
            items.append({
                'item_code': str(row['item_code']).strip(),
                'item_name': str(row['item_name']).strip(),
                'category': category,
                'insured_price': float(row['insured_price']) if pd.notna(row['insured_price']) else 0.0,
                'cash_price': float(row['cash_price']) if pd.notna(row['cash_price']) else 0.0,
            })
    
    if not items:
        raise ValueError("No valid items found in the Excel file. Please check the file format.")
    
    return items


def upload_price_list(db: Session, items: List[dict], category: str):
    """
    Upload price list items to database
    If item_code exists, update it; otherwise create new
    """
    for item_data in items:
        existing = (
            db.query(PriceListItem)
            .filter(PriceListItem.item_code == item_data['item_code'])
            .first()
        )
        
        if existing:
            # Update existing item
            existing.item_name = item_data['item_name']
            existing.category = category
            existing.insured_price = item_data['insured_price']
            existing.cash_price = item_data['cash_price']
            existing.is_active = True
        else:
            # Create new item
            new_item = PriceListItem(**item_data)
            db.add(new_item)
    
    db.commit()


def get_price(db: Session, item_code: str, is_insured: bool = False) -> float:
    """
    Get price for an item code based on insurance status
    """
    item = db.query(PriceListItem).filter(
        PriceListItem.item_code == item_code,
        PriceListItem.is_active == True
    ).first()
    
    if not item:
        return 0.0
    
    return item.insured_price if is_insured else item.cash_price


def search_price_items(db: Session, search_term: str = None, category: str = None):
    """
    Search price list items
    """
    query = db.query(PriceListItem).filter(PriceListItem.is_active == True)
    
    if search_term:
        query = query.filter(
            (PriceListItem.item_code.contains(search_term)) |
            (PriceListItem.item_name.contains(search_term))
        )
    
    if category:
        query = query.filter(PriceListItem.category == category)
    
    return query.all()

