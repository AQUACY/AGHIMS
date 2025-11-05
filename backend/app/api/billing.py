"""
Billing endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel, Field
from typing import Optional, List, Union
from datetime import datetime
from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.user import User
from app.models.encounter import Encounter
from app.models.patient import Patient
from app.models.bill import Bill, BillItem, Receipt, ReceiptItem
from app.models.price_list import PriceListItem
from app.services.price_list_service_v2 import get_price_from_all_tables
import random

router = APIRouter(prefix="/billing", tags=["billing"])


def determine_service_group(item_name: str, category: str, investigation_type: Optional[str] = None) -> str:
    """Determine service group based on item name, category, and investigation type"""
    item_name_lower = item_name.lower()
    
    # Check item name prefixes
    if item_name_lower.startswith("diagnosis:"):
        return "Diagnose"
    elif item_name_lower.startswith("prescription:"):
        return "Pharmacy"
    elif item_name_lower.startswith("investigation:"):
        # Use investigation type if available
        if investigation_type:
            if investigation_type.lower() == "lab":
                return "Lab"
            elif investigation_type.lower() == "scan":
                return "Scan"
            elif investigation_type.lower() == "xray":
                return "X-ray"
        # Fallback to checking item name
        if "lab" in item_name_lower:
            return "Lab"
        elif "scan" in item_name_lower:
            return "Scan"
        elif "xray" in item_name_lower or "x-ray" in item_name_lower:
            return "X-ray"
        return "Investigation"  # Fallback
    elif category == "surgery":
        return "Surgery"
    elif category == "product" or category == "pharmacy":
        return "Pharmacy"
    elif category == "drg":
        return "Diagnose"
    else:
        return "Other"


class BillItemCreate(BaseModel):
    """Bill item creation model - allows None for item_code and category for miscellaneous items"""
    # Using Optional[str] = None allows None values - this is standard Pydantic behavior
    item_code: Optional[str] = None  # Optional - for miscellaneous items without codes (can be None/null)
    item_name: str  # Required - name/description of the item
    category: Optional[str] = None  # Optional - for miscellaneous items without category (can be None/null)
    quantity: int = 1
    unit_price: Optional[float] = None  # Optional custom price. If not provided, will look up from price list
    
    class Config:
        # Pydantic configuration - this is compatible with both v1 and v2
        from_attributes = True


class BillCreate(BaseModel):
    """Bill creation model"""
    encounter_id: int
    items: List[BillItemCreate]
    miscellaneous: Optional[str] = None


class BillItemPaymentInfo(BaseModel):
    """Payment information for a bill item"""
    receipt_id: int
    receipt_item_id: int
    receipt_number: str
    amount_paid: float
    payment_method: Optional[str] = None
    issued_at: datetime
    refunded: bool = False
    
    class Config:
        from_attributes = True


class BillItemResponse(BaseModel):
    """Bill item response model with payment info"""
    id: int
    item_code: str
    item_name: str
    category: str
    quantity: int
    unit_price: float
    total_price: float
    amount_paid: float = 0.0  # Total amount paid for this item across all receipts
    remaining_balance: float = 0.0  # Remaining balance for this item
    payment_info: List[BillItemPaymentInfo] = []  # List of receipts that paid for this item
    
    class Config:
        from_attributes = True


class BillResponse(BaseModel):
    """Bill response model"""
    id: int
    encounter_id: int
    bill_number: str
    total_amount: float
    paid_amount: float
    is_paid: bool
    miscellaneous: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class BillDetailResponse(BillResponse):
    """Bill detail response with items"""
    bill_items: List[BillItemResponse]


class ReceiptItemCreate(BaseModel):
    """Receipt item creation model"""
    bill_item_id: int
    amount_paid: float
    receipt_number: Optional[str] = None  # Manual receipt number (optional)


class ReceiptCreate(BaseModel):
    """Receipt creation model"""
    bill_id: int
    payment_method: str = "cash"
    receipt_items: Optional[List[ReceiptItemCreate]] = None  # Optional itemized payments
    receipt_number: Optional[str] = None  # Manual receipt number (if all items use same receipt)


class ManualReceiptCreate(BaseModel):
    """Manual receipt creation model for bill item"""
    receipt_number: str  # Manually entered receipt number
    amount_paid: float
    payment_method: str = "cash"


@router.post("/", response_model=BillResponse, status_code=status.HTTP_201_CREATED)
def create_bill(
    bill_data: BillCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Billing", "Admin"]))
):
    """Create a bill for an encounter"""
    encounter = db.query(Encounter).filter(Encounter.id == bill_data.encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    patient = encounter.patient
    
    # Determine if insured based on encounter CCC number
    # If encounter has CCC number, client has active insurance, otherwise cash/carry
    is_insured_encounter = encounter.ccc_number is not None and encounter.ccc_number.strip() != ""
    
    # Find or create an unpaid bill for this encounter
    existing_bill = db.query(Bill).filter(
        Bill.encounter_id == bill_data.encounter_id,
        Bill.is_paid == False  # Only use unpaid bills
    ).first()
    
    if existing_bill:
        # Add items to existing unpaid bill
        bill = existing_bill
        total_amount = bill.total_amount
    else:
        # Create new bill
        bill_number = f"BILL-{random.randint(100000, 999999)}"
        bill = Bill(
            encounter_id=bill_data.encounter_id,
            bill_number=bill_number,
            is_insured=is_insured_encounter,
            miscellaneous=bill_data.miscellaneous,
            created_by=current_user.id
        )
        db.add(bill)
        db.flush()
        total_amount = 0.0
    
    # Create bill items (check for duplicates first)
    for item_data in bill_data.items:
        # Handle optional fields - use defaults for items without codes/categories
        item_code = item_data.item_code or "MISC"
        category = item_data.category or "other"
        
        # Check if this item already exists in the bill
        # For items without codes, match by name only
        if item_data.item_code:
            existing_item = db.query(BillItem).filter(
                BillItem.bill_id == bill.id,
                BillItem.item_code == item_data.item_code,
                BillItem.item_name == item_data.item_name,
                BillItem.category == category
            ).first()
        else:
            # For items without codes, match by name and category only
            existing_item = db.query(BillItem).filter(
                BillItem.bill_id == bill.id,
                BillItem.item_code == "MISC",
                BillItem.item_name == item_data.item_name,
                BillItem.category == category
            ).first()
        
        if existing_item:
            # Item already exists, skip or update quantity
            continue
        
        # Get price - use custom price if provided, otherwise look up from price list
        if item_data.unit_price is not None and item_data.unit_price >= 0:
            # Use custom price provided by user (for miscellaneous items)
            unit_price = item_data.unit_price
        elif item_data.item_code:
            # Only look up price if item_code is provided
            unit_price = get_price_from_all_tables(db, item_data.item_code, is_insured_encounter)
        else:
            # Items without codes must have a custom price
            raise HTTPException(
                status_code=400,
                detail=f"Custom price is required for items without item codes. Please provide unit_price for '{item_data.item_name}'"
            )
        
        total_price = unit_price * item_data.quantity
        
        bill_item = BillItem(
            bill_id=bill.id,
            item_code=item_code,
            item_name=item_data.item_name,
            category=category,
            quantity=item_data.quantity,
            unit_price=unit_price,
            total_price=total_price
        )
        db.add(bill_item)
        total_amount += total_price
    
    bill.total_amount = total_amount
    db.commit()
    db.refresh(bill)
    
    return bill


@router.post("/receipt", status_code=status.HTTP_201_CREATED)
def create_receipt(
    receipt_data: ReceiptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Billing", "Admin"]))
):
    """Create a receipt for a paid bill with optional itemized payments"""
    bill = db.query(Bill).filter(Bill.id == receipt_data.bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    if bill.is_paid:
        raise HTTPException(status_code=400, detail="Bill is already fully paid")
    
    # Calculate total amount to be paid
    total_paid = 0.0
    
    if receipt_data.receipt_items:
        # Itemized payment - validate all items belong to this bill
        bill_item_ids = {item.bill_item_id for item in receipt_data.receipt_items}
        bill_items = db.query(BillItem).filter(
            BillItem.id.in_(bill_item_ids),
            BillItem.bill_id == bill.id
        ).all()
        
        if len(bill_items) != len(receipt_data.receipt_items):
            raise HTTPException(status_code=400, detail="Some bill items do not belong to this bill")
        
        # Create a map for quick lookup
        bill_item_map = {item.id: item for item in bill_items}
        
        # Validate amounts and calculate total
        for receipt_item_data in receipt_data.receipt_items:
            bill_item = bill_item_map[receipt_item_data.bill_item_id]
            if receipt_item_data.amount_paid > bill_item.total_price:
                raise HTTPException(
                    status_code=400,
                    detail=f"Amount paid ({receipt_item_data.amount_paid}) exceeds bill item price ({bill_item.total_price}) for {bill_item.item_name}"
                )
            if receipt_item_data.amount_paid <= 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Amount paid must be greater than 0 for {bill_item.item_name}"
                )
            total_paid += receipt_item_data.amount_paid
    else:
        # Full payment - pay entire bill
        total_paid = bill.total_amount
    
    if total_paid <= 0:
        raise HTTPException(status_code=400, detail="Total payment amount must be greater than 0")
    
    if total_paid > bill.total_amount:
        raise HTTPException(status_code=400, detail="Total payment exceeds bill amount")
    
    # Group items by receipt number if provided, otherwise create one receipt
    receipts_created = []
    
    if receipt_data.receipt_items:
        # Group items by receipt number
        receipts_map = {}  # receipt_number -> {items: [], total: 0}
        
        for receipt_item_data in receipt_data.receipt_items:
            # Use receipt_number from item if provided, otherwise use global receipt_number, otherwise generate
            item_receipt_number = (
                receipt_item_data.receipt_number or 
                receipt_data.receipt_number or 
                None
            )
            
            if not item_receipt_number:
                # If no receipt number provided at all, generate one
                item_receipt_number = f"REC-{random.randint(100000, 999999)}"
            
            if item_receipt_number not in receipts_map:
                receipts_map[item_receipt_number] = {
                    "items": [],
                    "total": 0.0
                }
            
            receipts_map[item_receipt_number]["items"].append(receipt_item_data)
            receipts_map[item_receipt_number]["total"] += receipt_item_data.amount_paid
        
        # Create receipts for each unique receipt number
        for receipt_number, receipt_data_map in receipts_map.items():
            # Check if receipt number already exists (for same bill)
            existing_receipt = db.query(Receipt).filter(
                Receipt.receipt_number == receipt_number,
                Receipt.bill_id == bill.id
            ).first()
            
            if existing_receipt:
                receipt = existing_receipt
                # Update receipt amount
                receipt.amount_paid += receipt_data_map["total"]
            else:
                # Create new receipt
                receipt = Receipt(
                    bill_id=bill.id,
                    receipt_number=receipt_number,
                    amount_paid=receipt_data_map["total"],
                    payment_method=receipt_data.payment_method,
                    issued_by=current_user.id
                )
                db.add(receipt)
                db.flush()
            
            # Create receipt items
            for receipt_item_data in receipt_data_map["items"]:
                # Check if receipt item already exists
                existing_item = db.query(ReceiptItem).filter(
                    ReceiptItem.receipt_id == receipt.id,
                    ReceiptItem.bill_item_id == receipt_item_data.bill_item_id
                ).first()
                
                if not existing_item:
                    receipt_item = ReceiptItem(
                        receipt_id=receipt.id,
                        bill_item_id=receipt_item_data.bill_item_id,
                        amount_paid=receipt_item_data.amount_paid
                    )
                    db.add(receipt_item)
            
            receipts_created.append({
                "receipt_id": receipt.id,
                "receipt_number": receipt.receipt_number,
                "amount_paid": receipt_data_map["total"]
            })
    else:
        # Full payment - use provided receipt number or generate
        receipt_number = receipt_data.receipt_number or f"REC-{random.randint(100000, 999999)}"
        
        # Check if receipt number already exists
        existing_receipt = db.query(Receipt).filter(
            Receipt.receipt_number == receipt_number,
            Receipt.bill_id == bill.id
        ).first()
        
        if existing_receipt:
            receipt = existing_receipt
            receipt.amount_paid += total_paid
        else:
            receipt = Receipt(
                bill_id=bill.id,
                receipt_number=receipt_number,
                amount_paid=total_paid,
                payment_method=receipt_data.payment_method,
                issued_by=current_user.id
            )
            db.add(receipt)
            db.flush()
        
        # Create receipt items for all bill items
        for item in bill.bill_items:
            receipt_item = ReceiptItem(
                receipt_id=receipt.id,
                bill_item_id=item.id,
                amount_paid=item.total_price
            )
            db.add(receipt_item)
        
        receipts_created.append({
            "receipt_id": receipt.id,
            "receipt_number": receipt.receipt_number,
            "amount_paid": total_paid
        })
    
    # Update bill
    bill.paid_amount += total_paid
    if bill.paid_amount >= bill.total_amount:
        bill.is_paid = True
        bill.paid_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "receipts": receipts_created,
        "total_amount": total_paid
    }


@router.delete("/bill/{bill_id}")
def delete_bill(
    bill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Delete a bill - Admin only"""
    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    # Check if bill has any receipts (query directly to ensure we get the count)
    receipt_count = db.query(Receipt).filter(Receipt.bill_id == bill_id).count()
    if receipt_count > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete bill with receipts. Please delete or refund all receipts first."
        )
    
    # Delete bill items first (cascade should handle this, but explicit deletion is safer)
    db.query(BillItem).filter(BillItem.bill_id == bill_id).delete()
    
    # Delete the bill
    db.delete(bill)
    db.commit()
    
    return {"message": "Bill deleted successfully", "bill_id": bill_id}


@router.get("/encounter/{encounter_id}", response_model=List[BillResponse])
def get_encounter_bills(
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Billing", "Admin"]))
):
    """Get all bills for an encounter"""
    # Query bills and explicitly refresh to ensure we get the latest data
    bills = db.query(Bill).filter(Bill.encounter_id == encounter_id).order_by(Bill.created_at.desc()).all()
    # Refresh each bill to ensure all attributes are loaded
    for bill in bills:
        db.refresh(bill)
    return bills


class ReceiptInfo(BaseModel):
    """Receipt information"""
    id: int
    receipt_number: str
    amount_paid: float
    payment_method: Optional[str] = None
    refunded: bool
    issued_at: datetime
    
    class Config:
        from_attributes = True


class BillDetailResponseWithReceipt(BillDetailResponse):
    """Bill detail response with receipt info"""
    receipt: Optional[ReceiptInfo] = None


@router.get("/bill/{bill_id}", response_model=BillDetailResponseWithReceipt)
def get_bill_details(
    bill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Billing", "Admin"]))
):
    """Get detailed bill information with all bill items and receipt"""
    # Eager load all relationships
    bill = db.query(Bill)\
        .options(
            joinedload(Bill.bill_items),
            joinedload(Bill.receipts).joinedload(Receipt.receipt_items)
        )\
        .filter(Bill.id == bill_id)\
        .first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    # Get all non-refunded receipts for this bill
    non_refunded_receipts = [r for r in bill.receipts if not r.refunded]
    latest_receipt = non_refunded_receipts[-1] if non_refunded_receipts else None
    
    # Get all investigations for this encounter to determine service groups
    from app.models.investigation import Investigation
    investigations = db.query(Investigation).filter(
        Investigation.encounter_id == bill.encounter_id
    ).all()
    # Create a map of item_code (gdrg_code) to investigation_type
    item_code_to_investigation_type = {}
    for inv in investigations:
        if inv.gdrg_code:
            item_code_to_investigation_type[inv.gdrg_code] = inv.investigation_type
    
    # Build bill items with payment information
    bill_items_with_payment = []
    for item in bill.bill_items:
        # Get all receipt items for this bill item from non-refunded receipts
        receipt_items_for_item = []
        total_paid_for_item = 0.0
        
        # Get all receipts (including refunded) to show in payment info
        for receipt in bill.receipts:
            for receipt_item in receipt.receipt_items:
                if receipt_item.bill_item_id == item.id:
                    receipt_items_for_item.append({
                        "receipt_id": receipt.id,
                        "receipt_item_id": receipt_item.id,
                        "receipt_number": receipt.receipt_number,
                        "amount_paid": receipt_item.amount_paid,
                        "payment_method": receipt.payment_method,
                        "issued_at": receipt.issued_at,
                        "refunded": receipt.refunded,
                    })
                    # Only count non-refunded receipts towards paid amount
                    if not receipt.refunded:
                        total_paid_for_item += receipt_item.amount_paid
        
        remaining_balance = item.total_price - total_paid_for_item
        
        # Determine service group
        service_group = "Other"
        if item.category == "product":
            service_group = "Pharmacy"
        elif item.category in ["procedure", "surgery", "drg"]:
            # Check investigation type for labs/scans/xrays
            investigation_type = item_code_to_investigation_type.get(item.item_code)
            if investigation_type == "Lab":
                service_group = "Lab"
            elif investigation_type == "Scan":
                service_group = "Scan"
            elif investigation_type == "X-ray":
                service_group = "X-ray"
            elif item.category == "drg":
                service_group = "Diagnose"
            elif item.category == "surgery":
                service_group = "Surgery"
            else:
                service_group = "Other"
        elif item.category == "drg":
            service_group = "Diagnose"
        elif item.category == "surgery":
            service_group = "Surgery"
        
        bill_items_with_payment.append({
            "id": item.id,
            "item_code": item.item_code,
            "item_name": item.item_name,
            "category": item.category,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "total_price": item.total_price,
            "amount_paid": total_paid_for_item,
            "remaining_balance": remaining_balance,
            "payment_info": receipt_items_for_item,
            "service_group": service_group,
        })
    
    # Build response
    response_data = {
        "id": bill.id,
        "encounter_id": bill.encounter_id,
        "bill_number": bill.bill_number,
        "total_amount": bill.total_amount,
        "paid_amount": bill.paid_amount,
        "is_paid": bill.is_paid,
        "miscellaneous": bill.miscellaneous,
        "created_at": bill.created_at,
        "bill_items": bill_items_with_payment,
        "receipt": None
    }
    
    # Add latest receipt info if exists
    if latest_receipt:
        response_data["receipt"] = {
            "id": latest_receipt.id,
            "receipt_number": latest_receipt.receipt_number,
            "amount_paid": latest_receipt.amount_paid,
            "payment_method": latest_receipt.payment_method,
            "refunded": latest_receipt.refunded,
            "issued_at": latest_receipt.issued_at,
        }
    
    return response_data


@router.post("/bill-item/{bill_item_id}/receipt")
def add_manual_receipt_to_bill_item(
    bill_item_id: int,
    receipt_data: ManualReceiptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Billing", "Admin"]))
):
    """Manually add a receipt number for a specific bill item (for auditing)"""
    bill_item = db.query(BillItem).filter(BillItem.id == bill_item_id).first()
    if not bill_item:
        raise HTTPException(status_code=404, detail="Bill item not found")
    
    bill = bill_item.bill
    
    # Check if receipt number already exists
    existing_receipt = db.query(Receipt).filter(
        Receipt.receipt_number == receipt_data.receipt_number
    ).first()
    
    receipt = None
    if existing_receipt:
        # Use existing receipt if it belongs to the same bill
        if existing_receipt.bill_id != bill.id:
            raise HTTPException(
                status_code=400,
                detail=f"Receipt number {receipt_data.receipt_number} already exists for a different bill"
            )
        receipt = existing_receipt
    else:
        # Create new receipt with manual receipt number
        receipt = Receipt(
            bill_id=bill.id,
            receipt_number=receipt_data.receipt_number,
            amount_paid=receipt_data.amount_paid,
            payment_method=receipt_data.payment_method,
            issued_by=current_user.id
        )
        db.add(receipt)
        db.flush()
    
    # Check if receipt item already exists
    existing_receipt_item = db.query(ReceiptItem).filter(
        ReceiptItem.receipt_id == receipt.id,
        ReceiptItem.bill_item_id == bill_item_id
    ).first()
    
    if existing_receipt_item:
        raise HTTPException(
            status_code=400,
            detail=f"This receipt number is already associated with this bill item"
        )
    
    # Validate amount doesn't exceed remaining balance
    # Calculate already paid amount for this item
    total_paid_for_item = 0.0
    for r in bill.receipts:
        if not r.refunded:
            for ri in r.receipt_items:
                if ri.bill_item_id == bill_item_id:
                    total_paid_for_item += ri.amount_paid
    
    remaining_balance = bill_item.total_price - total_paid_for_item
    
    if receipt_data.amount_paid > remaining_balance:
        raise HTTPException(
            status_code=400,
            detail=f"Amount paid ({receipt_data.amount_paid}) exceeds remaining balance ({remaining_balance:.2f}) for this item"
        )
    
    if receipt_data.amount_paid <= 0:
        raise HTTPException(
            status_code=400,
            detail="Amount paid must be greater than 0"
        )
    
    # Create receipt item
    receipt_item = ReceiptItem(
        receipt_id=receipt.id,
        bill_item_id=bill_item_id,
        amount_paid=receipt_data.amount_paid
    )
    db.add(receipt_item)
    
    # Update receipt total if it's a new receipt
    if not existing_receipt:
        receipt.amount_paid = receipt_data.amount_paid
    else:
        receipt.amount_paid += receipt_data.amount_paid
    
    # Update bill paid amount (only if receipt is not refunded)
    if not receipt.refunded:
        bill.paid_amount += receipt_data.amount_paid
        if bill.paid_amount >= bill.total_amount:
            bill.is_paid = True
            bill.paid_at = datetime.utcnow()
    
    db.commit()
    db.refresh(receipt)
    db.refresh(receipt_item)
    
    return {
        "receipt_id": receipt.id,
        "receipt_number": receipt.receipt_number,
        "amount_paid": receipt_data.amount_paid,
        "bill_item_id": bill_item_id
    }


@router.delete("/receipt-item/{receipt_item_id}")
def delete_receipt_item(
    receipt_item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Billing", "Admin"]))
):
    """Delete a receipt item (manually entered receipt)"""
    receipt_item = db.query(ReceiptItem).filter(ReceiptItem.id == receipt_item_id).first()
    if not receipt_item:
        raise HTTPException(status_code=404, detail="Receipt item not found")
    
    receipt = receipt_item.receipt
    bill = receipt.bill
    
    # Only allow deletion if receipt is not refunded
    if receipt.refunded:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a receipt item from a refunded receipt. Use refund action instead."
        )
    
    amount_to_remove = receipt_item.amount_paid
    
    # Update receipt amount
    receipt.amount_paid -= amount_to_remove
    if receipt.amount_paid <= 0:
        # Delete the receipt if it has no items left
        db.delete(receipt)
    else:
        # Check if receipt has other items
        remaining_items = db.query(ReceiptItem).filter(
            ReceiptItem.receipt_id == receipt.id,
            ReceiptItem.id != receipt_item_id
        ).count()
        
        if remaining_items == 0:
            # Delete receipt if it's empty
            db.delete(receipt)
    
    # Update bill paid amount
    bill.paid_amount -= amount_to_remove
    if bill.paid_amount < 0:
        bill.paid_amount = 0
    
    if bill.paid_amount < bill.total_amount:
        bill.is_paid = False
        bill.paid_at = None
    
    # Delete receipt item
    db.delete(receipt_item)
    db.commit()
    
    return {"message": "Receipt item deleted successfully"}


@router.post("/receipt/{receipt_id}/refund")
def refund_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Refund a receipt (Admin only)"""
    receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    
    if receipt.refunded:
        raise HTTPException(status_code=400, detail="Receipt has already been refunded")
    
    bill = receipt.bill
    
    # Mark receipt as refunded
    receipt.refunded = True
    receipt.refunded_at = datetime.utcnow()
    receipt.refunded_by = current_user.id
    
    # Update bill payment status - subtract this receipt's amount
    bill.paid_amount -= receipt.amount_paid
    if bill.paid_amount < 0:
        bill.paid_amount = 0
    
    # Check if there are any other non-refunded receipts
    non_refunded_receipts = [r for r in bill.receipts if not r.refunded]
    if bill.paid_amount < bill.total_amount:
        bill.is_paid = False
        bill.paid_at = None
    elif bill.paid_amount >= bill.total_amount and non_refunded_receipts:
        # Still has non-refunded receipts covering the full amount
        bill.is_paid = True
    
    db.commit()
    
    return {
        "receipt_id": receipt.id,
        "receipt_number": receipt.receipt_number,
        "amount_refunded": receipt.amount_paid,
        "refunded_at": receipt.refunded_at
    }


class AutoBillItem(BaseModel):
    """Auto-calculated bill item"""
    item_code: str
    item_name: str
    category: str
    quantity: int = 1
    unit_price: float
    total_price: float
    service_group: str  # Group: Lab, Scan, X-ray, Diagnose, Surgery, Pharmacy
    
    class Config:
        from_attributes = True


class AutoCalculateResponse(BaseModel):
    """Auto-calculate bill items response"""
    encounter_id: int
    patient_insured: bool
    items: List[AutoBillItem]
    total_amount: float


@router.get("/encounter/{encounter_id}/auto-calculate", response_model=AutoCalculateResponse)
def auto_calculate_bill_items(
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Billing", "Admin"]))
):
    """Auto-calculate bill items. NOTE: Diagnoses are excluded for OPD consultations since the initial service request already covers the diagnosis billing."""
    from app.models.diagnosis import Diagnosis
    
    encounter = db.query(Encounter).filter(Encounter.id == encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    patient = encounter.patient
    
    # Determine if insured based on encounter CCC number
    # If encounter has CCC number, client has active insurance, otherwise cash/carry
    is_insured_encounter = encounter.ccc_number is not None and encounter.ccc_number.strip() != ""
    
    bill_items = []
    
    # NOTE: Diagnoses are excluded from auto-calculation for OPD consultations
    # since the initial service request already covers the diagnosis billing.
    # Get diagnoses with GDRG codes - DISABLED FOR OPD
    # diagnoses = db.query(Diagnosis).filter(
    #     Diagnosis.encounter_id == encounter_id,
    #     Diagnosis.gdrg_code.isnot(None),
    #     Diagnosis.gdrg_code != ''
    # ).all()
    # 
    # for diagnosis in diagnoses:
    #     if diagnosis.gdrg_code:
    #         # Check if bill item already exists for this diagnosis
    #         existing_item = db.query(BillItem).join(Bill).filter(
    #             Bill.encounter_id == encounter_id,
    #             BillItem.item_code == diagnosis.gdrg_code,
    #             BillItem.category == "drg"
    #         ).first()
    #         
    #         if not existing_item:
    #             unit_price = get_price_from_all_tables(db, diagnosis.gdrg_code, is_insured_encounter)
    #             if unit_price > 0:
    #                 bill_items.append(AutoBillItem(
    #                     item_code=diagnosis.gdrg_code,
    #                     item_name=f"Diagnosis: {diagnosis.diagnosis}",
    #                     category="drg",
    #                     quantity=1,
    #                     unit_price=unit_price,
    #                     total_price=unit_price,
    #                     service_group="Diagnose"
    #                 ))
    
    return AutoCalculateResponse(
        encounter_id=encounter_id,
        patient_insured=is_insured_encounter,
        items=bill_items,
        total_amount=sum(item.total_price for item in bill_items)
    )
