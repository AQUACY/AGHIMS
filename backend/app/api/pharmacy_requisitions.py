"""
Pharmacy Requisitions API endpoints
Handles ward requests for pharmacy items with approval and fulfillment workflow
"""
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from pydantic import BaseModel
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.core.datetime_utils import utcnow
from app.models.user import User
from app.models.ward_stock import WardStock
from app.models.pharmacy_requisition import PharmacyRequisition, RequisitionStatus
from app.models.requisition_item import RequisitionItem
from app.models.requisition_history import RequisitionHistory, HistoryAction
from app.core.notifications import create_notifications_for_roles, create_notification_for_user
from app.models.notification import NotificationType

router = APIRouter(prefix="/pharmacy-requisitions", tags=["pharmacy-requisitions"])


# Request/Response Models
class RequisitionItemCreate(BaseModel):
    product_code: str
    product_name: str
    requested_quantity: float
    notes: Optional[str] = None


class RequisitionCreate(BaseModel):
    ward: str
    items: List[RequisitionItemCreate]
    notes: Optional[str] = None


class RequisitionItemResponse(BaseModel):
    id: int
    requisition_id: int
    product_code: str
    product_name: str
    requested_quantity: float
    fulfilled_quantity: float
    unit_price: Optional[float] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class RequisitionHistoryResponse(BaseModel):
    id: int
    requisition_id: int
    action: str
    performed_by: int
    performed_by_name: Optional[str] = None
    notes: Optional[str] = None
    timestamp: datetime
    item_id: Optional[int] = None
    quantity_fulfilled: Optional[float] = None
    
    class Config:
        from_attributes = True


class PharmacyRequisitionResponse(BaseModel):
    id: int
    requisition_number: str
    ward: str
    requested_by: int
    requested_by_name: Optional[str] = None
    status: str
    approved_by: Optional[int] = None
    approved_by_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    fulfilled_by: Optional[int] = None
    fulfilled_by_name: Optional[str] = None
    fulfilled_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    items: List[RequisitionItemResponse] = []
    history: List[RequisitionHistoryResponse] = []
    
    class Config:
        from_attributes = True


class RequisitionApproveRequest(BaseModel):
    rejection_reason: Optional[str] = None  # Required if rejecting


class RequisitionFulfillItemRequest(BaseModel):
    item_id: int
    fulfilled_quantity: float
    notes: Optional[str] = None


class RequisitionFulfillRequest(BaseModel):
    items: List[RequisitionFulfillItemRequest]
    notes: Optional[str] = None


class WardStockResponse(BaseModel):
    id: int
    ward: str
    product_code: str
    product_name: str
    quantity: float
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


def generate_requisition_number(db: Session) -> str:
    """Generate unique requisition number"""
    # Format: REQ-YYYYMMDD-XXXX (e.g., REQ-20240115-0001)
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"REQ-{today}-"
    
    # Get the last requisition number for today
    last_requisition = db.query(PharmacyRequisition).filter(
        PharmacyRequisition.requisition_number.like(f"{prefix}%")
    ).order_by(PharmacyRequisition.requisition_number.desc()).first()
    
    if last_requisition:
        # Extract sequence number and increment
        try:
            sequence = int(last_requisition.requisition_number.split("-")[-1])
            sequence += 1
        except (ValueError, IndexError):
            sequence = 1
    else:
        sequence = 1
    
    return f"{prefix}{sequence:04d}"


def check_pending_requisitions(db: Session, ward: str, product_code: str) -> Optional[PharmacyRequisition]:
    """Check if there's a pending requisition for the same item from the same ward"""
    pending_statuses = [RequisitionStatus.PENDING, RequisitionStatus.APPROVED]
    
    # Find requisitions with pending status that have this product
    pending_requisitions = db.query(PharmacyRequisition).filter(
        and_(
            PharmacyRequisition.ward == ward,
            PharmacyRequisition.status.in_(pending_statuses)
        )
    ).all()
    
    for req in pending_requisitions:
        # Check if any item in this requisition matches the product
        item = db.query(RequisitionItem).filter(
            and_(
                RequisitionItem.requisition_id == req.id,
                RequisitionItem.product_code == product_code,
                RequisitionItem.fulfilled_quantity < RequisitionItem.requested_quantity  # Not fully fulfilled
            )
        ).first()
        
        if item:
            return req
    
    return None


@router.post("", response_model=PharmacyRequisitionResponse, status_code=status.HTTP_201_CREATED)
def create_requisition(
    requisition_data: RequisitionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """
    Create a new pharmacy requisition from a ward.
    Prevents duplicate requests for items that have pending requisitions.
    """
    if not requisition_data.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requisition must contain at least one item"
        )
    
    # Check for pending requisitions for each item
    pending_items = []
    for item_data in requisition_data.items:
        pending_req = check_pending_requisitions(db, requisition_data.ward, item_data.product_code)
        if pending_req:
            pending_items.append({
                "product_code": item_data.product_code,
                "product_name": item_data.product_name,
                "requisition_number": pending_req.requisition_number,
                "status": pending_req.status.value
            })
    
    if pending_items:
        # Format error message with pending items details
        error_detail = {
            "message": "Cannot create requisition. Some items have pending requisitions that must be approved or rejected first.",
            "pending_items": pending_items
        }
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_detail
        )
    
    # Generate requisition number
    requisition_number = generate_requisition_number(db)
    
    # Create requisition
    requisition = PharmacyRequisition(
        requisition_number=requisition_number,
        ward=requisition_data.ward,
        requested_by=current_user.id,
        status=RequisitionStatus.PENDING,
        notes=requisition_data.notes
    )
    db.add(requisition)
    db.flush()
    
    # Create requisition items
    for item_data in requisition_data.items:
        item = RequisitionItem(
            requisition_id=requisition.id,
            product_code=item_data.product_code,
            product_name=item_data.product_name,
            requested_quantity=item_data.requested_quantity,
            notes=item_data.notes
        )
        db.add(item)
    
    # Create history entry
    history = RequisitionHistory(
        requisition_id=requisition.id,
        action=HistoryAction.CREATED,
        performed_by=current_user.id,
        notes=f"Requisition created by {current_user.full_name or current_user.username}"
    )
    db.add(history)
    
    # Create notification for Pharmacy Head
    try:
        create_notifications_for_roles(
            db=db,
            roles=["Pharmacy Head", "Admin"],
            notification_type=NotificationType.REQUISITION_CREATED,
            title=f"New Requisition from {requisition_data.ward}",
            message=f"Requisition {requisition_number} has been created by {current_user.full_name or current_user.username} from {requisition_data.ward}. Please review and approve.",
            related_id=requisition.id,
            related_type="requisition"
        )
    except Exception as e:
        # Don't let notification failures break the requisition creation
        print(f"Warning: Failed to create notification: {e}")
    
    db.commit()
    db.refresh(requisition)
    
    # Load relationships
    requisition.items = db.query(RequisitionItem).filter(
        RequisitionItem.requisition_id == requisition.id
    ).all()
    
    # Get user names
    requester = db.query(User).filter(User.id == requisition.requested_by).first()
    
    response = PharmacyRequisitionResponse(
        id=requisition.id,
        requisition_number=requisition.requisition_number,
        ward=requisition.ward,
        requested_by=requisition.requested_by,
        requested_by_name=requester.full_name if requester else requester.username if requester else None,
        status=requisition.status.value,
        approved_by=requisition.approved_by,
        approved_at=requisition.approved_at,
        rejection_reason=requisition.rejection_reason,
        fulfilled_by=requisition.fulfilled_by,
        fulfilled_at=requisition.fulfilled_at,
        notes=requisition.notes,
        created_at=requisition.created_at,
        updated_at=requisition.updated_at,
        items=[RequisitionItemResponse(**item.__dict__) for item in requisition.items],
        history=[]
    )
    
    return response


@router.get("", response_model=List[PharmacyRequisitionResponse])
def get_requisitions(
    ward: Optional[str] = Query(None, description="Filter by ward"),
    status: Optional[str] = Query(None, description="Filter by status"),
    start_date: Optional[str] = Query(None, description="Filter by start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter by end date (YYYY-MM-DD)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all requisitions with optional filtering"""
    query = db.query(PharmacyRequisition)
    
    # Apply filters based on user role
    # Note: Ward filtering by user role would need a user-ward mapping table
    # For now, all users can see all requisitions, but can filter by ward
    
    if ward:
        query = query.filter(PharmacyRequisition.ward == ward)
    
    if status:
        try:
            status_enum = RequisitionStatus(status)
            query = query.filter(PharmacyRequisition.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}"
            )
    
    # Date range filtering
    if start_date:
        try:
            start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
            # Set to start of day
            start_datetime = start_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
            query = query.filter(PharmacyRequisition.created_at >= start_datetime)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid start_date format. Expected YYYY-MM-DD, got: {start_date}"
            )
    
    if end_date:
        try:
            end_datetime = datetime.strptime(end_date, "%Y-%m-%d")
            # Set to end of day
            end_datetime = end_datetime.replace(hour=23, minute=59, second=59, microsecond=999999)
            query = query.filter(PharmacyRequisition.created_at <= end_datetime)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid end_date format. Expected YYYY-MM-DD, got: {end_date}"
            )
    
    # Pagination
    offset = (page - 1) * page_size
    requisitions = query.order_by(PharmacyRequisition.created_at.desc()).offset(offset).limit(page_size).all()
    
    # Build response with relationships
    result = []
    for req in requisitions:
        req.items = db.query(RequisitionItem).filter(RequisitionItem.requisition_id == req.id).all()
        req.history = db.query(RequisitionHistory).filter(
            RequisitionHistory.requisition_id == req.id
        ).order_by(RequisitionHistory.timestamp.desc()).all()
        
        # Get user names
        requester = db.query(User).filter(User.id == req.requested_by).first()
        approver = db.query(User).filter(User.id == req.approved_by).first() if req.approved_by else None
        fulfiller = db.query(User).filter(User.id == req.fulfilled_by).first() if req.fulfilled_by else None
        
        history_list = []
        for hist in req.history:
            hist_user = db.query(User).filter(User.id == hist.performed_by).first()
            history_list.append(RequisitionHistoryResponse(
                id=hist.id,
                requisition_id=hist.requisition_id,
                action=hist.action.value,
                performed_by=hist.performed_by,
                performed_by_name=hist_user.full_name if hist_user else hist_user.username if hist_user else None,
                notes=hist.notes,
                timestamp=hist.timestamp,
                item_id=hist.item_id,
                quantity_fulfilled=hist.quantity_fulfilled
            ))
        
        result.append(PharmacyRequisitionResponse(
            id=req.id,
            requisition_number=req.requisition_number,
            ward=req.ward,
            requested_by=req.requested_by,
            requested_by_name=requester.full_name if requester else requester.username if requester else None,
            status=req.status.value,
            approved_by=req.approved_by,
            approved_by_name=approver.full_name if approver else approver.username if approver else None,
            approved_at=req.approved_at,
            rejection_reason=req.rejection_reason,
            fulfilled_by=req.fulfilled_by,
            fulfilled_by_name=fulfiller.full_name if fulfiller else fulfiller.username if fulfiller else None,
            fulfilled_at=req.fulfilled_at,
            notes=req.notes,
            created_at=req.created_at,
            updated_at=req.updated_at,
            items=[RequisitionItemResponse(**item.__dict__) for item in req.items],
            history=history_list
        ))
    
    return result


@router.get("/{requisition_id}", response_model=PharmacyRequisitionResponse)
def get_requisition(
    requisition_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific requisition by ID"""
    requisition = db.query(PharmacyRequisition).filter(PharmacyRequisition.id == requisition_id).first()
    
    if not requisition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requisition not found"
        )
    
    # Load relationships
    requisition.items = db.query(RequisitionItem).filter(RequisitionItem.requisition_id == requisition.id).all()
    requisition.history = db.query(RequisitionHistory).filter(
        RequisitionHistory.requisition_id == requisition.id
    ).order_by(RequisitionHistory.timestamp.desc()).all()
    
    # Get user names
    requester = db.query(User).filter(User.id == requisition.requested_by).first()
    approver = db.query(User).filter(User.id == requisition.approved_by).first() if requisition.approved_by else None
    fulfiller = db.query(User).filter(User.id == requisition.fulfilled_by).first() if requisition.fulfilled_by else None
    
    history_list = []
    for hist in requisition.history:
        hist_user = db.query(User).filter(User.id == hist.performed_by).first()
        history_list.append(RequisitionHistoryResponse(
            id=hist.id,
            requisition_id=hist.requisition_id,
            action=hist.action.value,
            performed_by=hist.performed_by,
            performed_by_name=hist_user.full_name if hist_user else hist_user.username if hist_user else None,
            notes=hist.notes,
            timestamp=hist.timestamp,
            item_id=hist.item_id,
            quantity_fulfilled=hist.quantity_fulfilled
        ))
    
    return PharmacyRequisitionResponse(
        id=requisition.id,
        requisition_number=requisition.requisition_number,
        ward=requisition.ward,
        requested_by=requisition.requested_by,
        requested_by_name=requester.full_name if requester else requester.username if requester else None,
        status=requisition.status.value,
        approved_by=requisition.approved_by,
        approved_by_name=approver.full_name if approver else approver.username if approver else None,
        approved_at=requisition.approved_at,
        rejection_reason=requisition.rejection_reason,
        fulfilled_by=requisition.fulfilled_by,
        fulfilled_by_name=fulfiller.full_name if fulfiller else fulfiller.username if fulfiller else None,
        fulfilled_at=requisition.fulfilled_at,
        notes=requisition.notes,
        created_at=requisition.created_at,
        updated_at=requisition.updated_at,
        items=[RequisitionItemResponse(**item.__dict__) for item in requisition.items],
        history=history_list
    )


@router.put("/{requisition_id}/approve", response_model=PharmacyRequisitionResponse)
def approve_requisition(
    requisition_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Pharmacy Head", "Admin"]))
):
    """Approve a requisition (Pharmacy Head only)"""
    requisition = db.query(PharmacyRequisition).filter(PharmacyRequisition.id == requisition_id).first()
    
    if not requisition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requisition not found"
        )
    
    if requisition.status != RequisitionStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve requisition with status: {requisition.status.value}"
        )
    
    # Update requisition
    requisition.status = RequisitionStatus.APPROVED
    requisition.approved_by = current_user.id
    requisition.approved_at = utcnow()
    
    # Create history entry
    history = RequisitionHistory(
        requisition_id=requisition.id,
        action=HistoryAction.APPROVED,
        performed_by=current_user.id,
        notes=f"Requisition approved by {current_user.full_name or current_user.username}"
    )
    db.add(history)
    
    # Create notifications
    try:
        # Notify Store Manager
        create_notifications_for_roles(
            db=db,
            roles=["Store Manager", "Admin"],
            notification_type=NotificationType.REQUISITION_APPROVED,
            title=f"Requisition Approved: {requisition.requisition_number}",
            message=f"Requisition {requisition.requisition_number} from {requisition.ward} has been approved. Please fulfill the request.",
            related_id=requisition.id,
            related_type="requisition"
        )
        # Notify the requester
        create_notification_for_user(
            db=db,
            user_id=requisition.requested_by,
            notification_type=NotificationType.REQUISITION_APPROVED,
            title=f"Requisition Approved: {requisition.requisition_number}",
            message=f"Your requisition {requisition.requisition_number} has been approved and is ready for fulfillment.",
            related_id=requisition.id,
            related_type="requisition"
        )
    except Exception as e:
        print(f"Warning: Failed to create notification: {e}")
    
    db.commit()
    db.refresh(requisition)
    
    # Return updated requisition (reuse get_requisition logic)
    return get_requisition(requisition_id, db, current_user)


@router.put("/{requisition_id}/reject", response_model=PharmacyRequisitionResponse)
def reject_requisition(
    requisition_id: int,
    rejection_data: RequisitionApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Pharmacy Head", "Admin"]))
):
    """Reject a requisition (Pharmacy Head only)"""
    requisition = db.query(PharmacyRequisition).filter(PharmacyRequisition.id == requisition_id).first()
    
    if not requisition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requisition not found"
        )
    
    if requisition.status != RequisitionStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject requisition with status: {requisition.status.value}"
        )
    
    # Update requisition
    requisition.status = RequisitionStatus.REJECTED
    requisition.approved_by = current_user.id  # Store who rejected it
    requisition.approved_at = utcnow()
    requisition.rejection_reason = rejection_data.rejection_reason
    
    # Create history entry
    history = RequisitionHistory(
        requisition_id=requisition.id,
        action=HistoryAction.REJECTED,
        performed_by=current_user.id,
        notes=f"Requisition rejected by {current_user.full_name or current_user.username}. Reason: {rejection_data.rejection_reason or 'No reason provided'}"
    )
    db.add(history)
    
    # Create notification for the requester
    try:
        create_notification_for_user(
            db=db,
            user_id=requisition.requested_by,
            notification_type=NotificationType.REQUISITION_REJECTED,
            title=f"Requisition Rejected: {requisition.requisition_number}",
            message=f"Your requisition {requisition.requisition_number} has been rejected. Reason: {rejection_data.rejection_reason or 'No reason provided'}",
            related_id=requisition.id,
            related_type="requisition"
        )
    except Exception as e:
        print(f"Warning: Failed to create notification: {e}")
    
    db.commit()
    db.refresh(requisition)
    
    # Return updated requisition
    return get_requisition(requisition_id, db, current_user)


@router.put("/{requisition_id}/cancel", response_model=PharmacyRequisitionResponse)
def cancel_requisition(
    requisition_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a pending requisition (requester or Admin only)"""
    requisition = db.query(PharmacyRequisition).filter(PharmacyRequisition.id == requisition_id).first()

    if not requisition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requisition not found"
        )

    if requisition.status != RequisitionStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel requisition with status: {requisition.status.value}. Only pending requisitions can be cancelled."
        )

    # Only the requester or an Admin can cancel
    if requisition.requested_by != current_user.id and current_user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to cancel this requisition."
        )

    # Update requisition status to REJECTED with a cancellation reason
    requisition.status = RequisitionStatus.REJECTED
    requisition.approved_by = current_user.id  # Store who cancelled it
    requisition.approved_at = utcnow()
    requisition.rejection_reason = "Cancelled by requester."

    # Create history entry
    history = RequisitionHistory(
        requisition_id=requisition.id,
        action=HistoryAction.CANCELLED,
        performed_by=current_user.id,
        notes=f"Requisition cancelled by {current_user.full_name or current_user.username}."
    )
    db.add(history)

    # Create notification for Pharmacy Head (if not the canceller)
    if current_user.role != "Pharmacy Head" and current_user.role != "Admin":
        try:
            create_notifications_for_roles(
                db=db,
                roles=["Pharmacy Head", "Admin"],
                notification_type=NotificationType.REQUISITION_REJECTED,
                title=f"Requisition Cancelled: {requisition.requisition_number}",
                message=f"Requisition {requisition.requisition_number} from {requisition.ward} was cancelled by {current_user.full_name or current_user.username}.",
                related_id=requisition.id,
                related_type="requisition"
            )
        except Exception as e:
            print(f"Warning: Failed to create notification for cancellation: {e}")

    db.commit()
    db.refresh(requisition)

    return get_requisition(requisition_id, db, current_user)


@router.put("/{requisition_id}/fulfill", response_model=PharmacyRequisitionResponse)
def fulfill_requisition(
    requisition_id: int,
    fulfill_data: RequisitionFulfillRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Store Manager", "Admin"]))
):
    """Fulfill a requisition (Store Manager only). Supports partial fulfillment."""
    requisition = db.query(PharmacyRequisition).filter(PharmacyRequisition.id == requisition_id).first()
    
    if not requisition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requisition not found"
        )
    
    if requisition.status != RequisitionStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot fulfill requisition with status: {requisition.status.value}"
        )
    
    if not fulfill_data.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide at least one item to fulfill"
        )
    
    # Get all requisition items
    requisition_items = db.query(RequisitionItem).filter(
        RequisitionItem.requisition_id == requisition_id
    ).all()
    
    items_dict = {item.id: item for item in requisition_items}
    
    # Process fulfillment for each item
    total_fulfilled = 0
    total_requested = 0
    
    for fulfill_item in fulfill_data.items:
        if fulfill_item.item_id not in items_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Item ID {fulfill_item.item_id} not found in requisition"
            )
        
        item = items_dict[fulfill_item.item_id]
        
        # Validate fulfillment quantity
        if fulfill_item.fulfilled_quantity < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Fulfilled quantity cannot be negative for item {item.product_name}"
            )
        
        remaining = item.requested_quantity - item.fulfilled_quantity
        if fulfill_item.fulfilled_quantity > remaining:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot fulfill {fulfill_item.fulfilled_quantity} for {item.product_name}. Remaining: {remaining}"
            )
        
        # Update item fulfillment
        item.fulfilled_quantity += fulfill_item.fulfilled_quantity
        
        # Update or create ward stock
        ward_stock = db.query(WardStock).filter(
            and_(
                WardStock.ward == requisition.ward,
                WardStock.product_code == item.product_code
            )
        ).first()
        
        if ward_stock:
            ward_stock.quantity += fulfill_item.fulfilled_quantity
        else:
            ward_stock = WardStock(
                ward=requisition.ward,
                product_code=item.product_code,
                product_name=item.product_name,
                quantity=fulfill_item.fulfilled_quantity
            )
            db.add(ward_stock)
        
        # Create history entry for item fulfillment
        history = RequisitionHistory(
            requisition_id=requisition.id,
            action=HistoryAction.ITEM_FULFILLED,
            performed_by=current_user.id,
            item_id=item.id,
            quantity_fulfilled=fulfill_item.fulfilled_quantity,
            notes=f"Fulfilled {fulfill_item.fulfilled_quantity} of {item.product_name}. {fulfill_item.notes or ''}"
        )
        db.add(history)
        
        total_fulfilled += item.fulfilled_quantity
        total_requested += item.requested_quantity
    
    # Check if all items are fully fulfilled
    all_items = db.query(RequisitionItem).filter(RequisitionItem.requisition_id == requisition_id).all()
    all_fulfilled = all(item.fulfilled_quantity >= item.requested_quantity for item in all_items)
    
    if all_fulfilled:
        requisition.status = RequisitionStatus.FULFILLED
        requisition.fulfilled_at = utcnow()
        action = HistoryAction.FULFILLED
    else:
        requisition.status = RequisitionStatus.PARTIALLY_FULFILLED
        action = HistoryAction.PARTIALLY_FULFILLED
    
    requisition.fulfilled_by = current_user.id
    if not requisition.fulfilled_at:
        requisition.fulfilled_at = utcnow()
    
    # Create overall fulfillment history entry
    history = RequisitionHistory(
        requisition_id=requisition.id,
        action=action,
        performed_by=current_user.id,
        notes=f"Requisition fulfillment by {current_user.full_name or current_user.username}. {fulfill_data.notes or ''}"
    )
    db.add(history)
    
    # Create notifications
    try:
        notification_type = NotificationType.REQUISITION_FULFILLED if all_fulfilled else NotificationType.REQUISITION_PARTIALLY_FULFILLED
        status_text = "fully fulfilled" if all_fulfilled else "partially fulfilled"
        
        # Notify the requester
        create_notification_for_user(
            db=db,
            user_id=requisition.requested_by,
            notification_type=notification_type,
            title=f"Requisition {status_text.title()}: {requisition.requisition_number}",
            message=f"Your requisition {requisition.requisition_number} from {requisition.ward} has been {status_text}. Items are now available in your ward stock.",
            related_id=requisition.id,
            related_type="requisition"
        )
    except Exception as e:
        print(f"Warning: Failed to create notification: {e}")
    
    db.commit()
    db.refresh(requisition)
    
    # Return updated requisition
    return get_requisition(requisition_id, db, current_user)


@router.get("/ward-stock/{ward}", response_model=List[WardStockResponse])
def get_ward_stock(
    ward: str,
    product_code: Optional[str] = Query(None, description="Filter by product code"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get ward stock for a specific ward"""
    query = db.query(WardStock).filter(WardStock.ward == ward)
    
    if product_code:
        query = query.filter(WardStock.product_code.ilike(f"%{product_code}%"))
    
    stocks = query.order_by(WardStock.product_name).all()
    
    return [WardStockResponse(**stock.__dict__) for stock in stocks]


@router.get("/ward-stock/{ward}/{product_code}", response_model=WardStockResponse)
def get_ward_stock_item(
    ward: str,
    product_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get specific ward stock item"""
    stock = db.query(WardStock).filter(
        and_(
            WardStock.ward == ward,
            WardStock.product_code == product_code
        )
    ).first()
    
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock not found for ward {ward} and product {product_code}"
        )
    
    return WardStockResponse(**stock.__dict__)

