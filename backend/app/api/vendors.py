"""
Vendor management API endpoints
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role, require_module_permission
from app.models.user import User
from app.models.vendor import Vendor

router = APIRouter(prefix="/vendors", tags=["vendors"])


# Request/Response Models
class VendorCreate(BaseModel):
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True


class VendorUpdate(BaseModel):
    name: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class VendorResponse(BaseModel):
    id: int
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


@router.get("", response_model=List[VendorResponse])
def get_vendors(
    search: Optional[str] = Query(None, description="Search by name, contact person, phone, or email"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Store Manager", "Department Head", "Pharmacy Head", "Admin"])),
    _module_check: User = Depends(require_module_permission("inventory", "read"))
):
    """Get all vendors with optional search and filter"""
    query = db.query(Vendor)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Vendor.name.ilike(search_term),
                Vendor.contact_person.ilike(search_term),
                Vendor.phone.ilike(search_term),
                Vendor.email.ilike(search_term)
            )
        )
    
    if is_active is not None:
        query = query.filter(Vendor.is_active == is_active)
    
    vendors = query.order_by(Vendor.name).all()
    # Convert datetime fields to strings
    return [
        {
            "id": v.id,
            "name": v.name,
            "contact_person": v.contact_person,
            "phone": v.phone,
            "email": v.email,
            "address": v.address,
            "notes": v.notes,
            "is_active": v.is_active,
            "created_at": v.created_at.isoformat() if v.created_at else None,
            "updated_at": v.updated_at.isoformat() if v.updated_at else None
        }
        for v in vendors
    ]


@router.get("/{vendor_id}", response_model=VendorResponse)
def get_vendor(
    vendor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Store Manager", "Department Head", "Pharmacy Head", "Admin"]))
):
    """Get a specific vendor by ID"""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )
    return {
        "id": vendor.id,
        "name": vendor.name,
        "contact_person": vendor.contact_person,
        "phone": vendor.phone,
        "email": vendor.email,
        "address": vendor.address,
        "notes": vendor.notes,
        "is_active": vendor.is_active,
        "created_at": vendor.created_at.isoformat() if vendor.created_at else None,
        "updated_at": vendor.updated_at.isoformat() if vendor.updated_at else None
    }


@router.post("", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
def create_vendor(
    vendor_data: VendorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Store Manager", "Admin"])),
    _module_check: User = Depends(require_module_permission("inventory", "create"))
):
    """Create a new vendor"""
    # Check if vendor with same name already exists
    existing = db.query(Vendor).filter(Vendor.name == vendor_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Vendor with name '{vendor_data.name}' already exists"
        )
    
    vendor = Vendor(**vendor_data.dict())
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return {
        "id": vendor.id,
        "name": vendor.name,
        "contact_person": vendor.contact_person,
        "phone": vendor.phone,
        "email": vendor.email,
        "address": vendor.address,
        "notes": vendor.notes,
        "is_active": vendor.is_active,
        "created_at": vendor.created_at.isoformat() if vendor.created_at else None,
        "updated_at": vendor.updated_at.isoformat() if vendor.updated_at else None
    }


@router.put("/{vendor_id}", response_model=VendorResponse)
def update_vendor(
    vendor_id: int,
    vendor_data: VendorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Store Manager", "Admin"])),
    _module_check: User = Depends(require_module_permission("inventory", "update"))
):
    """Update a vendor"""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )
    
    # Check if name is being changed and if new name already exists
    if vendor_data.name and vendor_data.name != vendor.name:
        existing = db.query(Vendor).filter(Vendor.name == vendor_data.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Vendor with name '{vendor_data.name}' already exists"
            )
    
    # Update fields
    update_data = vendor_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(vendor, field, value)
    
    db.commit()
    db.refresh(vendor)
    return {
        "id": vendor.id,
        "name": vendor.name,
        "contact_person": vendor.contact_person,
        "phone": vendor.phone,
        "email": vendor.email,
        "address": vendor.address,
        "notes": vendor.notes,
        "is_active": vendor.is_active,
        "created_at": vendor.created_at.isoformat() if vendor.created_at else None,
        "updated_at": vendor.updated_at.isoformat() if vendor.updated_at else None
    }


@router.delete("/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vendor(
    vendor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"])),
    _module_check: User = Depends(require_module_permission("inventory", "delete"))
):
    """Delete a vendor (Admin only)"""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )
    
    db.delete(vendor)
    db.commit()
    return None

