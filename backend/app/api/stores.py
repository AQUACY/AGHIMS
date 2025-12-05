"""
Store management API endpoints
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
from app.models.store import Store

router = APIRouter(prefix="/stores", tags=["stores"])


# Request/Response Models
class StoreCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: bool = True


class StoreUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class StoreResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=List[StoreResponse])
def get_stores(
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all stores (or only active ones)"""
    query = db.query(Store)
    
    if active_only:
        query = query.filter(Store.is_active == True)
    
    stores = query.order_by(Store.name.asc()).all()
    return stores


@router.get("/{store_id}", response_model=StoreResponse)
def get_store(
    store_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific store by ID"""
    store = db.query(Store).filter(Store.id == store_id).first()
    
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found"
        )
    
    return store


@router.post("", response_model=StoreResponse, status_code=status.HTTP_201_CREATED)
def create_store(
    store_data: StoreCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Create a new store (Admin only)"""
    # Check if store name already exists
    existing_store = db.query(Store).filter(Store.name == store_data.name).first()
    if existing_store:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Store with name '{store_data.name}' already exists"
        )
    
    # Create new store
    new_store = Store(
        name=store_data.name,
        description=store_data.description,
        is_active=store_data.is_active
    )
    
    try:
        db.add(new_store)
        db.commit()
        db.refresh(new_store)
        return new_store
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database error: {str(e)}"
        )


@router.put("/{store_id}", response_model=StoreResponse)
def update_store(
    store_id: int,
    store_data: StoreUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Update a store (Admin only)"""
    store = db.query(Store).filter(Store.id == store_id).first()
    
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found"
        )
    
    # Check if new name conflicts with existing store
    if store_data.name and store_data.name != store.name:
        existing_store = db.query(Store).filter(Store.name == store_data.name).first()
        if existing_store:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Store with name '{store_data.name}' already exists"
            )
        store.name = store_data.name
    
    if store_data.description is not None:
        store.description = store_data.description
    
    if store_data.is_active is not None:
        store.is_active = store_data.is_active
    
    store.updated_at = utcnow()
    
    try:
        db.commit()
        db.refresh(store)
        return store
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database error: {str(e)}"
        )


@router.delete("/{store_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_store(
    store_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Delete a store (Admin only) - Soft delete by setting is_active to False"""
    store = db.query(Store).filter(Store.id == store_id).first()
    
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found"
        )
    
    # Soft delete - set is_active to False instead of actually deleting
    store.is_active = False
    store.updated_at = utcnow()
    
    db.commit()
    return None

