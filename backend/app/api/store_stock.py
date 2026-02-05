"""
Store Stock management API endpoints
Handles stock addition, approval workflow, and inventory management
"""
from typing import Optional, List
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from pydantic import BaseModel
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role, require_module_permission
from app.core.datetime_utils import utcnow
from app.models.user import User
from app.models.store_stock import StoreStock, StockStatus
from app.models.vendor import Vendor
from app.models.store import Store
from app.models.product_price import ProductPrice
from app.models.store_staff_assignment import StoreStaffAssignment, StoreRole
from app.core.notifications import create_notifications_for_roles, create_notification_for_user
from app.models.notification import NotificationType

router = APIRouter(prefix="/store-stock", tags=["store-stock"])


# Request/Response Models
class StoreStockCreate(BaseModel):
    store_id: int
    product_code: str
    product_name: str
    vendor_id: int
    batch_number: str
    expiry_date: date
    quantity: float
    unit_price: Optional[float] = None
    receipt_number: Optional[str] = None
    notes: Optional[str] = None


class StoreStockApproveRequest(BaseModel):
    approval: bool  # True to approve, False to reject
    rejection_reason: Optional[str] = None  # Required if rejecting


class StoreStockUpdate(BaseModel):
    product_code: Optional[str] = None
    product_name: Optional[str] = None
    vendor_id: Optional[int] = None
    batch_number: Optional[str] = None
    expiry_date: Optional[date] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    receipt_number: Optional[str] = None
    notes: Optional[str] = None


class StoreStockResponse(BaseModel):
    id: int
    store_id: int
    store_name: Optional[str] = None
    product_code: str
    product_name: str
    vendor_id: int
    vendor_name: Optional[str] = None
    batch_number: str
    expiry_date: date
    quantity: float
    unit_price: Optional[float] = None
    receipt_number: Optional[str] = None
    notes: Optional[str] = None
    status: str
    created_by: int
    created_by_name: Optional[str] = None
    created_at: str
    approved_by: Optional[int] = None
    approved_by_name: Optional[str] = None
    approved_at: Optional[str] = None
    rejection_reason: Optional[str] = None
    updated_at: str
    
    class Config:
        from_attributes = True


class StoreStockSummaryResponse(BaseModel):
    """Summary of stock by product"""
    product_code: str
    product_name: str
    total_quantity: float
    approved_quantity: float
    pending_quantity: float
    batches: List[StoreStockResponse]
    
    class Config:
        from_attributes = True


def check_user_is_store_manager(db: Session, user_id: int, store_id: int) -> bool:
    """Check if user is Store Manager of the store"""
    assignment = db.query(StoreStaffAssignment).filter(
        and_(
            StoreStaffAssignment.store_id == store_id,
            StoreStaffAssignment.user_id == user_id,
            StoreStaffAssignment.is_active == True,
            StoreStaffAssignment.role == StoreRole.STORE_MANAGER
        )
    ).first()
    return assignment is not None


def check_user_is_department_head(db: Session, user_id: int, store_id: int) -> bool:
    """Check if user is Department Head of the store"""
    assignment = db.query(StoreStaffAssignment).filter(
        and_(
            StoreStaffAssignment.store_id == store_id,
            StoreStaffAssignment.user_id == user_id,
            StoreStaffAssignment.is_active == True,
            StoreStaffAssignment.role == StoreRole.DEPARTMENT_HEAD
        )
    ).first()
    return assignment is not None


@router.post("", response_model=StoreStockResponse, status_code=status.HTTP_201_CREATED)
def add_stock(
    stock_data: StoreStockCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Store Manager", "Admin"])),
    _module_check: User = Depends(require_module_permission("inventory", "create"))
):
    """
    Add new stock to a store.
    Only Store Managers can add stock to their assigned stores.
    Stock is created with PENDING status and requires Department Head approval.
    """
    # Verify store exists
    store = db.query(Store).filter(Store.id == stock_data.store_id).first()
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found"
        )
    
    # Verify vendor exists
    vendor = db.query(Vendor).filter(Vendor.id == stock_data.vendor_id).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )
    
    # Verify product exists in price list
    product = db.query(ProductPrice).filter(
        ProductPrice.medication_code == stock_data.product_code
    ).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with code '{stock_data.product_code}' not found in price list. Please add it first in Price List Management."
        )
    
    # Check if user is Store Manager of this store (Admin can bypass)
    if current_user.role != "Admin":
        if not check_user_is_store_manager(db, current_user.id, stock_data.store_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Store Managers can add stock to their assigned stores"
            )
    
    # Check if stock with same store-product-batch already exists
    existing = db.query(StoreStock).filter(
        and_(
            StoreStock.store_id == stock_data.store_id,
            StoreStock.product_code == stock_data.product_code,
            StoreStock.batch_number == stock_data.batch_number
        )
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stock with batch number '{stock_data.batch_number}' already exists for this product in this store. Please update existing stock instead."
        )
    
    # Create stock entry
    stock = StoreStock(
        store_id=stock_data.store_id,
        product_code=stock_data.product_code,
        product_name=stock_data.product_name,
        vendor_id=stock_data.vendor_id,
        batch_number=stock_data.batch_number,
        expiry_date=stock_data.expiry_date,
        quantity=stock_data.quantity,
        unit_price=stock_data.unit_price,
        receipt_number=stock_data.receipt_number,
        notes=stock_data.notes,
        status=StockStatus.PENDING,
        created_by=current_user.id
    )
    db.add(stock)
    db.commit()
    db.refresh(stock)
    
    # Notify Department Head of the store
    department_heads = db.query(StoreStaffAssignment).filter(
        and_(
            StoreStaffAssignment.store_id == stock_data.store_id,
            StoreStaffAssignment.role == StoreRole.DEPARTMENT_HEAD,
            StoreStaffAssignment.is_active == True
        )
    ).all()
    
    for assignment in department_heads:
        create_notification_for_user(
            db=db,
            user_id=assignment.user_id,
            notification_type=NotificationType.STOCK_PENDING_APPROVAL,
            title="Stock Pending Approval",
            message=f"New stock added for {stock_data.product_name} (Batch: {stock_data.batch_number}) requires your approval",
            related_id=stock.id
        )
    
    db.commit()
    
    # Load relationships for response
    db.refresh(stock)
    return {
        "id": stock.id,
        "store_id": stock.store_id,
        "store_name": stock.store.name if stock.store else None,
        "product_code": stock.product_code,
        "product_name": stock.product_name,
        "vendor_id": stock.vendor_id,
        "vendor_name": stock.vendor.name if stock.vendor else None,
        "batch_number": stock.batch_number,
        "expiry_date": stock.expiry_date,
        "quantity": stock.quantity,
        "unit_price": stock.unit_price,
        "receipt_number": stock.receipt_number,
        "notes": stock.notes,
        "status": stock.status.value,
        "created_by": stock.created_by,
        "created_by_name": stock.creator.full_name if stock.creator else None,
        "created_at": stock.created_at.isoformat() if stock.created_at else None,
        "approved_by": stock.approved_by,
        "approved_by_name": None,
        "approved_at": stock.approved_at.isoformat() if stock.approved_at else None,
        "rejection_reason": stock.rejection_reason,
        "updated_at": stock.updated_at.isoformat() if stock.updated_at else None
    }


@router.get("", response_model=List[StoreStockResponse])
def get_stock(
    _module_check: User = Depends(require_module_permission("inventory", "read")),
    store_id: Optional[int] = Query(None, description="Filter by store ID"),
    product_code: Optional[str] = Query(None, description="Filter by product code"),
    status: Optional[str] = Query(None, description="Filter by status (pending, approved, rejected, expired)"),
    vendor_id: Optional[int] = Query(None, description="Filter by vendor ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Store Manager", "Department Head", "Pharmacy Head", "Admin"]))
):
    """Get stock entries with optional filters"""
    query = db.query(StoreStock)
    
    if store_id:
        query = query.filter(StoreStock.store_id == store_id)
    
    if product_code:
        query = query.filter(StoreStock.product_code == product_code)
    
    if status:
        try:
            # Convert to uppercase to match enum values
            status_upper = status.upper()
            status_enum = StockStatus(status_upper)
            query = query.filter(StoreStock.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {', '.join([s.value for s in StockStatus])}"
            )
    
    if vendor_id:
        query = query.filter(StoreStock.vendor_id == vendor_id)
    
    stocks = query.order_by(StoreStock.created_at.desc()).all()
    
    # Load relationships
    result = []
    for stock in stocks:
        stock_dict = {
            "id": stock.id,
            "store_id": stock.store_id,
            "store_name": stock.store.name if stock.store else None,
            "product_code": stock.product_code,
            "product_name": stock.product_name,
            "vendor_id": stock.vendor_id,
            "vendor_name": stock.vendor.name if stock.vendor else None,
            "batch_number": stock.batch_number,
            "expiry_date": stock.expiry_date,
            "quantity": stock.quantity,
            "unit_price": stock.unit_price,
            "receipt_number": stock.receipt_number,
            "notes": stock.notes,
            "status": stock.status.value,
            "created_by": stock.created_by,
            "created_by_name": stock.creator.full_name if stock.creator else None,
            "created_at": stock.created_at.isoformat() if stock.created_at else None,
            "approved_by": stock.approved_by,
            "approved_by_name": stock.approver.full_name if stock.approver else None,
            "approved_at": stock.approved_at.isoformat() if stock.approved_at else None,
            "rejection_reason": stock.rejection_reason,
            "updated_at": stock.updated_at.isoformat() if stock.updated_at else None
        }
        result.append(stock_dict)
    
    return result


@router.put("/{stock_id}/approve", response_model=StoreStockResponse)
def approve_stock(
    stock_id: int,
    approval_data: StoreStockApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Department Head", "Admin"]))
):
    """
    Approve or reject stock entry.
    Only Department Heads can approve stock for their assigned stores.
    """
    stock = db.query(StoreStock).filter(StoreStock.id == stock_id).first()
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock entry not found"
        )
    
    # Check if already processed
    if stock.status != StockStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stock entry is already {stock.status.value if hasattr(stock.status, 'value') else stock.status}. Cannot approve/reject."
        )
    
    # Check if user is Department Head of this store (Admin can bypass)
    if current_user.role != "Admin":
        if not check_user_is_department_head(db, current_user.id, stock.store_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Department Heads can approve stock for their assigned stores"
            )
    
    if approval_data.approval:
        # Approve
        stock.status = StockStatus.APPROVED
        stock.approved_by = current_user.id
        stock.approved_at = utcnow()
        stock.rejection_reason = None
        
        # Notify store manager
        create_notification_for_user(
            db=db,
            user_id=stock.created_by,
            notification_type=NotificationType.STOCK_APPROVED,
            title="Stock Approved",
            message=f"Stock for {stock.product_name} (Batch: {stock.batch_number}) has been approved",
            related_id=stock.id
        )
    else:
        # Reject
        if not approval_data.rejection_reason:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rejection reason is required when rejecting stock"
            )
        
        stock.status = StockStatus.REJECTED
        stock.approved_by = current_user.id
        stock.approved_at = utcnow()
        stock.rejection_reason = approval_data.rejection_reason
        
        # Notify store manager
        create_notification_for_user(
            db=db,
            user_id=stock.created_by,
            notification_type=NotificationType.STOCK_REJECTED,
            title="Stock Rejected",
            message=f"Stock for {stock.product_name} (Batch: {stock.batch_number}) has been rejected: {approval_data.rejection_reason}",
            related_id=stock.id
        )
    
    db.commit()
    db.refresh(stock)
    
    return {
        "id": stock.id,
        "store_id": stock.store_id,
        "store_name": stock.store.name if stock.store else None,
        "product_code": stock.product_code,
        "product_name": stock.product_name,
        "vendor_id": stock.vendor_id,
        "vendor_name": stock.vendor.name if stock.vendor else None,
        "batch_number": stock.batch_number,
        "expiry_date": stock.expiry_date,
        "quantity": stock.quantity,
        "unit_price": stock.unit_price,
        "receipt_number": stock.receipt_number,
        "notes": stock.notes,
        "status": stock.status.value,
        "created_by": stock.created_by,
        "created_by_name": stock.creator.full_name if stock.creator else None,
        "created_at": stock.created_at.isoformat() if stock.created_at else None,
        "approved_by": stock.approved_by,
        "approved_by_name": stock.approver.full_name if stock.approver else None,
        "approved_at": stock.approved_at.isoformat() if stock.approved_at else None,
        "rejection_reason": stock.rejection_reason,
        "updated_at": stock.updated_at.isoformat() if stock.updated_at else None
    }


@router.get("/summary/by-product", response_model=List[StoreStockSummaryResponse])
def get_stock_summary_by_product(
    _module_check: User = Depends(require_module_permission("inventory", "read")),
    store_id: Optional[int] = Query(None, description="Filter by store ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Store Manager", "Department Head", "Pharmacy Head", "Admin"]))
):
    """Get stock summary grouped by product"""
    query = db.query(StoreStock)
    
    if store_id:
        query = query.filter(StoreStock.store_id == store_id)
    
    # Only show approved stock for summary
    query = query.filter(StoreStock.status == StockStatus.APPROVED)
    
    stocks = query.order_by(StoreStock.product_name, StoreStock.expiry_date).all()
    
    # Group by product
    product_groups = {}
    for stock in stocks:
        key = stock.product_code
        if key not in product_groups:
            product_groups[key] = {
                "product_code": stock.product_code,
                "product_name": stock.product_name,
                "total_quantity": 0.0,
                "approved_quantity": 0.0,
                "pending_quantity": 0.0,
                "batches": []
            }
        
        product_groups[key]["total_quantity"] += stock.quantity
        product_groups[key]["approved_quantity"] += stock.quantity
        
        # Add batch info
        batch_info = {
            "id": stock.id,
            "store_id": stock.store_id,
            "store_name": stock.store.name if stock.store else None,
            "product_code": stock.product_code,
            "product_name": stock.product_name,
            "vendor_id": stock.vendor_id,
            "vendor_name": stock.vendor.name if stock.vendor else None,
            "batch_number": stock.batch_number,
            "expiry_date": stock.expiry_date,
            "quantity": stock.quantity,
            "unit_price": stock.unit_price,
            "receipt_number": stock.receipt_number,
            "notes": stock.notes,
            "status": stock.status.value,
            "created_by": stock.created_by,
            "created_by_name": stock.creator.full_name if stock.creator else None,
            "created_at": stock.created_at.isoformat() if stock.created_at else None,
            "approved_by": stock.approved_by,
            "approved_by_name": stock.approver.full_name if stock.approver else None,
            "approved_at": stock.approved_at.isoformat() if stock.approved_at else None,
            "rejection_reason": stock.rejection_reason,
            "updated_at": stock.updated_at.isoformat() if stock.updated_at else None
        }
        product_groups[key]["batches"].append(batch_info)
    
    return list(product_groups.values())


@router.get("/{stock_id}", response_model=StoreStockResponse)
def get_stock_item(
    stock_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Store Manager", "Department Head", "Pharmacy Head", "Admin"])),
    _module_check: User = Depends(require_module_permission("inventory", "read"))
):
    """Get a specific stock entry by ID"""
    stock = db.query(StoreStock).filter(StoreStock.id == stock_id).first()
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock entry not found"
        )
    
    return {
        "id": stock.id,
        "store_id": stock.store_id,
        "store_name": stock.store.name if stock.store else None,
        "product_code": stock.product_code,
        "product_name": stock.product_name,
        "vendor_id": stock.vendor_id,
        "vendor_name": stock.vendor.name if stock.vendor else None,
        "batch_number": stock.batch_number,
        "expiry_date": stock.expiry_date,
        "quantity": stock.quantity,
        "unit_price": stock.unit_price,
        "receipt_number": stock.receipt_number,
        "notes": stock.notes,
        "status": stock.status.value,
        "created_by": stock.created_by,
        "created_by_name": stock.creator.full_name if stock.creator else None,
        "created_at": stock.created_at.isoformat() if stock.created_at else None,
        "approved_by": stock.approved_by,
        "approved_by_name": stock.approver.full_name if stock.approver else None,
        "approved_at": stock.approved_at.isoformat() if stock.approved_at else None,
        "rejection_reason": stock.rejection_reason,
        "updated_at": stock.updated_at.isoformat() if stock.updated_at else None
    }


@router.put("/{stock_id}", response_model=StoreStockResponse)
def update_stock(
    stock_id: int,
    stock_data: StoreStockUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Store Manager", "Admin"])),
    _module_check: User = Depends(require_module_permission("inventory", "update"))
):
    """
    Update a stock entry.
    Only Store Managers can update stock for their assigned stores, or Admin.
    Cannot update if stock is already approved (unless Admin).
    """
    stock = db.query(StoreStock).filter(StoreStock.id == stock_id).first()
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock entry not found"
        )
    
    # Check if already approved - only Admin can edit approved stock
    if stock.status == StockStatus.APPROVED and current_user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot edit approved stock. Only Admin can edit approved stock entries."
        )
    
    # Check if user is Store Manager of this store (Admin can bypass)
    if current_user.role != "Admin":
        if not check_user_is_store_manager(db, current_user.id, stock.store_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Store Managers can update stock for their assigned stores"
            )
    
    # Verify vendor if being updated
    if stock_data.vendor_id and stock_data.vendor_id != stock.vendor_id:
        vendor = db.query(Vendor).filter(Vendor.id == stock_data.vendor_id).first()
        if not vendor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vendor not found"
            )
    
    # Verify product if being updated
    if stock_data.product_code and stock_data.product_code != stock.product_code:
        product = db.query(ProductPrice).filter(
            ProductPrice.medication_code == stock_data.product_code
        ).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with code '{stock_data.product_code}' not found in price list"
            )
    
    # Check for duplicate batch if batch number is being changed
    if stock_data.batch_number and stock_data.batch_number != stock.batch_number:
        existing = db.query(StoreStock).filter(
            and_(
                StoreStock.store_id == stock.store_id,
                StoreStock.product_code == (stock_data.product_code or stock.product_code),
                StoreStock.batch_number == stock_data.batch_number,
                StoreStock.id != stock_id
            )
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stock with batch number '{stock_data.batch_number}' already exists for this product in this store"
            )
    
    # Update fields
    update_data = stock_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(stock, field, value)
    
    # If product code or name changed, update product_name
    if stock_data.product_code and stock_data.product_code != stock.product_code:
        if not stock_data.product_name:
            # Get product name from price list
            product = db.query(ProductPrice).filter(
                ProductPrice.medication_code == stock_data.product_code
            ).first()
            if product:
                stock.product_name = product.product_name
    
    db.commit()
    db.refresh(stock)
    
    return {
        "id": stock.id,
        "store_id": stock.store_id,
        "store_name": stock.store.name if stock.store else None,
        "product_code": stock.product_code,
        "product_name": stock.product_name,
        "vendor_id": stock.vendor_id,
        "vendor_name": stock.vendor.name if stock.vendor else None,
        "batch_number": stock.batch_number,
        "expiry_date": stock.expiry_date,
        "quantity": stock.quantity,
        "unit_price": stock.unit_price,
        "receipt_number": stock.receipt_number,
        "notes": stock.notes,
        "status": stock.status.value,
        "created_by": stock.created_by,
        "created_by_name": stock.creator.full_name if stock.creator else None,
        "created_at": stock.created_at.isoformat() if stock.created_at else None,
        "approved_by": stock.approved_by,
        "approved_by_name": stock.approver.full_name if stock.approver else None,
        "approved_at": stock.approved_at.isoformat() if stock.approved_at else None,
        "rejection_reason": stock.rejection_reason,
        "updated_at": stock.updated_at.isoformat() if stock.updated_at else None
    }


@router.delete("/{stock_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_stock(
    stock_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Store Manager", "Admin"])),
    _module_check: User = Depends(require_module_permission("inventory", "delete"))
):
    """
    Delete a stock entry completely.
    Only Store Managers can delete stock for their assigned stores, or Admin.
    Cannot delete if stock is already approved (unless Admin).
    """
    stock = db.query(StoreStock).filter(StoreStock.id == stock_id).first()
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock entry not found"
        )
    
    # Check if already approved - only Admin can delete approved stock
    if stock.status == StockStatus.APPROVED and current_user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete approved stock. Only Admin can delete approved stock entries."
        )
    
    # Check if user is Store Manager of this store (Admin can bypass)
    if current_user.role != "Admin":
        if not check_user_is_store_manager(db, current_user.id, stock.store_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Store Managers can delete stock for their assigned stores"
            )
    
    db.delete(stock)
    db.commit()
    return None

