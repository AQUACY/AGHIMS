"""
Ward management API endpoints
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
from app.models.ward import Ward, DepartmentType

router = APIRouter(prefix="/wards", tags=["wards"])


# Request/Response Models
class WardCreate(BaseModel):
    name: str
    department_type: DepartmentType = DepartmentType.WARD
    is_active: bool = True


class WardUpdate(BaseModel):
    name: Optional[str] = None
    department_type: Optional[DepartmentType] = None
    is_active: Optional[bool] = None


class WardResponse(BaseModel):
    id: int
    name: str
    department_type: DepartmentType
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=List[WardResponse])
def get_wards(
    active_only: bool = False,
    department_type: Optional[DepartmentType] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all departments/wards (or only active ones, optionally filtered by type)"""
    query = db.query(Ward)
    
    if active_only:
        query = query.filter(Ward.is_active == True)
    
    if department_type:
        query = query.filter(Ward.department_type == department_type)
    
    wards = query.order_by(Ward.name.asc()).all()
    return wards


@router.get("/{ward_id}", response_model=WardResponse)
def get_ward(
    ward_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific ward by ID"""
    ward = db.query(Ward).filter(Ward.id == ward_id).first()
    
    if not ward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ward not found"
        )
    
    return ward


@router.post("", response_model=WardResponse, status_code=status.HTTP_201_CREATED)
def create_ward(
    ward_data: WardCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Create a new ward (Admin only)"""
    # Check if ward name already exists
    existing_ward = db.query(Ward).filter(Ward.name == ward_data.name).first()
    if existing_ward:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ward with name '{ward_data.name}' already exists"
        )
    
    # Create new ward/department
    new_ward = Ward(
        name=ward_data.name,
        department_type=ward_data.department_type,
        is_active=ward_data.is_active
    )
    
    try:
        db.add(new_ward)
        db.commit()
        db.refresh(new_ward)
        return new_ward
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database error: {str(e)}"
        )


@router.put("/{ward_id}", response_model=WardResponse)
def update_ward(
    ward_id: int,
    ward_data: WardUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Update a ward (Admin only)"""
    ward = db.query(Ward).filter(Ward.id == ward_id).first()
    
    if not ward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ward not found"
        )
    
    # Check if new name conflicts with existing ward
    if ward_data.name and ward_data.name != ward.name:
        existing_ward = db.query(Ward).filter(Ward.name == ward_data.name).first()
        if existing_ward:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Department with name '{ward_data.name}' already exists"
            )
        ward.name = ward_data.name
    
    if ward_data.department_type is not None:
        ward.department_type = ward_data.department_type
    
    if ward_data.is_active is not None:
        ward.is_active = ward_data.is_active
    
    ward.updated_at = utcnow()
    
    try:
        db.commit()
        db.refresh(ward)
        return ward
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database error: {str(e)}"
        )


@router.delete("/{ward_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ward(
    ward_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Delete a ward (Admin only) - Soft delete by setting is_active to False"""
    ward = db.query(Ward).filter(Ward.id == ward_id).first()
    
    if not ward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ward not found"
        )
    
    # Soft delete - set is_active to False instead of actually deleting
    ward.is_active = False
    ward.updated_at = utcnow()
    
    db.commit()
    return None

