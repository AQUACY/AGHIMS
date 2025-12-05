"""
Department Staff Assignment API endpoints
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.core.datetime_utils import utcnow
from app.models.user import User
from app.models.ward import Ward
from app.models.department_staff_assignment import DepartmentStaffAssignment, DepartmentRole

router = APIRouter(prefix="/department-staff-assignments", tags=["department-staff-assignments"])


# Request/Response Models
class DepartmentStaffAssignmentCreate(BaseModel):
    department_id: int
    user_id: int
    role: DepartmentRole


class DepartmentStaffAssignmentUpdate(BaseModel):
    role: Optional[DepartmentRole] = None
    is_active: Optional[bool] = None


class DepartmentStaffAssignmentResponse(BaseModel):
    id: int
    department_id: int
    department_name: Optional[str] = None
    user_id: int
    user_name: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=List[DepartmentStaffAssignmentResponse])
def get_assignments(
    department_id: Optional[int] = None,
    user_id: Optional[int] = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get department staff assignments"""
    query = db.query(DepartmentStaffAssignment)
    
    if department_id:
        query = query.filter(DepartmentStaffAssignment.department_id == department_id)
    
    if user_id:
        query = query.filter(DepartmentStaffAssignment.user_id == user_id)
    
    if active_only:
        query = query.filter(DepartmentStaffAssignment.is_active == True)
    
    assignments = query.all()
    
    # Build response with names
    result = []
    for assignment in assignments:
        department = db.query(Ward).filter(Ward.id == assignment.department_id).first()
        user = db.query(User).filter(User.id == assignment.user_id).first()
        
        result.append(DepartmentStaffAssignmentResponse(
            id=assignment.id,
            department_id=assignment.department_id,
            department_name=department.name if department else None,
            user_id=assignment.user_id,
            user_name=user.full_name if user else user.username if user else None,
            role=assignment.role.value,
            is_active=assignment.is_active,
            created_at=assignment.created_at,
            updated_at=assignment.updated_at
        ))
    
    return result


@router.post("", response_model=DepartmentStaffAssignmentResponse, status_code=status.HTTP_201_CREATED)
def create_assignment(
    assignment_data: DepartmentStaffAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Create a department staff assignment (Admin only)"""
    # Verify department exists
    department = db.query(Ward).filter(Ward.id == assignment_data.department_id).first()
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )
    
    # Verify user exists
    user = db.query(User).filter(User.id == assignment_data.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if assignment already exists
    existing = db.query(DepartmentStaffAssignment).filter(
        DepartmentStaffAssignment.department_id == assignment_data.department_id,
        DepartmentStaffAssignment.user_id == assignment_data.user_id,
        DepartmentStaffAssignment.role == assignment_data.role
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assignment already exists"
        )
    
    # Create assignment
    assignment = DepartmentStaffAssignment(
        department_id=assignment_data.department_id,
        user_id=assignment_data.user_id,
        role=assignment_data.role,
        is_active=True
    )
    
    try:
        db.add(assignment)
        db.commit()
        db.refresh(assignment)
        
        # Build response
        return DepartmentStaffAssignmentResponse(
            id=assignment.id,
            department_id=assignment.department_id,
            department_name=department.name,
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


@router.put("/{assignment_id}", response_model=DepartmentStaffAssignmentResponse)
def update_assignment(
    assignment_id: int,
    assignment_data: DepartmentStaffAssignmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Update a department staff assignment (Admin only)"""
    assignment = db.query(DepartmentStaffAssignment).filter(
        DepartmentStaffAssignment.id == assignment_id
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
        department = db.query(Ward).filter(Ward.id == assignment.department_id).first()
        user = db.query(User).filter(User.id == assignment.user_id).first()
        
        return DepartmentStaffAssignmentResponse(
            id=assignment.id,
            department_id=assignment.department_id,
            department_name=department.name if department else None,
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
    current_user: User = Depends(require_role(["Admin"]))
):
    """Delete a department staff assignment (Admin only) - Soft delete"""
    assignment = db.query(DepartmentStaffAssignment).filter(
        DepartmentStaffAssignment.id == assignment_id
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

