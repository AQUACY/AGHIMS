"""
Store Staff Assignment API endpoints
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role, require_module_permission
from app.core.datetime_utils import utcnow
from app.models.user import User
from app.models.store import Store
from app.models.store_staff_assignment import StoreStaffAssignment, StoreRole

router = APIRouter(prefix="/store-staff-assignments", tags=["store-staff-assignments"])


# Request/Response Models
class StoreStaffAssignmentCreate(BaseModel):
    store_id: int
    user_id: int
    role: StoreRole


class StoreStaffAssignmentUpdate(BaseModel):
    role: Optional[StoreRole] = None
    is_active: Optional[bool] = None


class StoreStaffAssignmentResponse(BaseModel):
    id: int
    store_id: int
    store_name: Optional[str] = None
    user_id: int
    user_name: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=List[StoreStaffAssignmentResponse])
def get_assignments(
    store_id: Optional[int] = None,
    user_id: Optional[int] = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _module_check: User = Depends(require_module_permission("staff", "read"))
):
    """Get store staff assignments"""
    query = db.query(StoreStaffAssignment)
    
    if store_id:
        query = query.filter(StoreStaffAssignment.store_id == store_id)
    
    if user_id:
        query = query.filter(StoreStaffAssignment.user_id == user_id)
    
    if active_only:
        query = query.filter(StoreStaffAssignment.is_active == True)
    
    assignments = query.all()
    
    # Build response with names
    result = []
    for assignment in assignments:
        store = db.query(Store).filter(Store.id == assignment.store_id).first()
        user = db.query(User).filter(User.id == assignment.user_id).first()
        
        result.append(StoreStaffAssignmentResponse(
            id=assignment.id,
            store_id=assignment.store_id,
            store_name=store.name if store else None,
            user_id=assignment.user_id,
            user_name=user.full_name if user else user.username if user else None,
            role=assignment.role.value,
            is_active=assignment.is_active,
            created_at=assignment.created_at,
            updated_at=assignment.updated_at
        ))
    
    return result


@router.post("", response_model=StoreStaffAssignmentResponse, status_code=status.HTTP_201_CREATED)
def create_assignment(
    assignment_data: StoreStaffAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"])),
    _module_check: User = Depends(require_module_permission("staff", "create"))
):
    """Create a store staff assignment (Admin only)"""
    # Verify store exists
    store = db.query(Store).filter(Store.id == assignment_data.store_id).first()
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found"
        )
    
    # Verify user exists
    user = db.query(User).filter(User.id == assignment_data.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if assignment already exists (including inactive ones)
    existing = db.query(StoreStaffAssignment).filter(
        StoreStaffAssignment.store_id == assignment_data.store_id,
        StoreStaffAssignment.user_id == assignment_data.user_id,
        StoreStaffAssignment.role == assignment_data.role
    ).first()
    
    if existing:
        # If assignment exists but is inactive, reactivate it
        if not existing.is_active:
            existing.is_active = True
            existing.updated_at = utcnow()
            db.commit()
            db.refresh(existing)
            
            # Build response
            return StoreStaffAssignmentResponse(
                id=existing.id,
                store_id=existing.store_id,
                store_name=store.name,
                user_id=existing.user_id,
                user_name=user.full_name if user else user.username,
                role=existing.role.value,
                is_active=existing.is_active,
                created_at=existing.created_at,
                updated_at=existing.updated_at
            )
        else:
            # Assignment already exists and is active
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assignment already exists"
            )
    
    # Create new assignment
    assignment = StoreStaffAssignment(
        store_id=assignment_data.store_id,
        user_id=assignment_data.user_id,
        role=assignment_data.role,
        is_active=True
    )
    
    try:
        db.add(assignment)
        db.commit()
        db.refresh(assignment)
        
        # Build response
        return StoreStaffAssignmentResponse(
            id=assignment.id,
            store_id=assignment.store_id,
            store_name=store.name,
            user_id=assignment.user_id,
            user_name=user.full_name if user else user.username,
            role=assignment.role.value,
            is_active=assignment.is_active,
            created_at=assignment.created_at,
            updated_at=assignment.updated_at
        )
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database error: {str(e)}"
        )


@router.put("/{assignment_id}", response_model=StoreStaffAssignmentResponse)
def update_assignment(
    assignment_id: int,
    assignment_data: StoreStaffAssignmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Update a store staff assignment (Admin only)"""
    assignment = db.query(StoreStaffAssignment).filter(
        StoreStaffAssignment.id == assignment_id
    ).first()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )
    
    if assignment_data.role is not None:
        assignment.role = assignment_data.role
    
    if assignment_data.is_active is not None:
        assignment.is_active = assignment_data.is_active
    
    assignment.updated_at = utcnow()
    
    try:
        db.commit()
        db.refresh(assignment)
        
        # Build response
        store = db.query(Store).filter(Store.id == assignment.store_id).first()
        user = db.query(User).filter(User.id == assignment.user_id).first()
        
        return StoreStaffAssignmentResponse(
            id=assignment.id,
            store_id=assignment.store_id,
            store_name=store.name if store else None,
            user_id=assignment.user_id,
            user_name=user.full_name if user else user.username if user else None,
            role=assignment.role.value,
            is_active=assignment.is_active,
            created_at=assignment.created_at,
            updated_at=assignment.updated_at
        )
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database error: {str(e)}"
        )


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"])),
    _module_check: User = Depends(require_module_permission("staff", "delete"))
):
    """Delete a store staff assignment (Admin only) - Soft delete"""
    assignment = db.query(StoreStaffAssignment).filter(
        StoreStaffAssignment.id == assignment_id
    ).first()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )
    
    assignment.is_active = False
    assignment.updated_at = utcnow()
    
    db.commit()
    return None

