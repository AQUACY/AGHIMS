"""
Authentication endpoints
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.config import settings
from app.models.user import User
from app.models.user_role import UserRole
from app.core.inventory_access import (
    get_assigned_store_ids,
    get_ic_managed_ward_names,
    get_inventory_access_flags,
    get_inventory_dashboard_scope,
)
from app.core.dependencies import get_current_user
from app.core.audit import log_activity
from sqlalchemy.orm import joinedload
from typing import List

router = APIRouter(prefix="/auth", tags=["auth"])


class Token(BaseModel):
    """Token response model"""
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """User response model"""
    id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str
    additional_roles: List[str] = []  # List of additional role names
    is_super_admin: bool = False
    is_department_ic_or_deputy: bool = False  # Active IC or Deputy on any department (ward)
    has_store_manager_assignment: bool = False  # Active StoreStaffAssignment as store manager
    has_store_department_head_assignment: bool = False  # Active assignment as store-linked department head
    can_access_inventory_mode: bool = False  # Assignments + key roles (see /me implementation)
    inventory_dashboard_can_filter_stores: bool = False
    inventory_dashboard_can_filter_departments: bool = False
    ic_managed_department_names: List[str] = []
    assigned_store_ids: List[int] = []

    class Config:
        from_attributes = True


@router.post("/login", response_model=Token)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """User login endpoint"""
    user = db.query(User).filter(User.username == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    # Debug: Log token expiration setting
    print(f"DEBUG: Creating token with expiration: {settings.ACCESS_TOKEN_EXPIRE_MINUTES} minutes")
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role},
        expires_delta=access_token_expires
    )
    
    # Log successful login (skip for super admin / ghost account)
    from app.core.audit import is_super_admin
    if not is_super_admin(user):
        log_activity(
            db=db,
            user=user,
            request=request,
            action="LOGIN",
            resource_type="User",
            resource_id=user.id,
            details={"username": user.username, "role": user.role},
            summary=f"User {user.full_name or user.username} ({user.role}) logged in."
        )

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user information including additional roles"""
    # Load additional roles
    user_with_roles = db.query(User).options(joinedload(User.additional_roles)).filter(User.id == current_user.id).first()
    
    additional_roles = []
    if user_with_roles:
        additional_roles = [ur.role for ur in user_with_roles.additional_roles]

    inv = get_inventory_access_flags(db, current_user, additional_roles)
    is_super = bool(getattr(current_user, "is_super_admin", False))
    dash_scope = get_inventory_dashboard_scope(db, current_user, additional_roles)
    ic_names = get_ic_managed_ward_names(db, current_user.id)
    store_ids = get_assigned_store_ids(db, current_user.id)

    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "additional_roles": additional_roles,
        "is_super_admin": is_super,
        "is_department_ic_or_deputy": inv.is_department_ic_or_deputy,
        "has_store_manager_assignment": inv.has_store_manager_assignment,
        "has_store_department_head_assignment": inv.has_store_department_head_assignment,
        "can_access_inventory_mode": inv.can_access_inventory_mode,
        "inventory_dashboard_can_filter_stores": dash_scope.unrestricted_filters,
        "inventory_dashboard_can_filter_departments": dash_scope.unrestricted_filters,
        "ic_managed_department_names": ic_names,
        "assigned_store_ids": store_ids,
    }


class PasswordChange(BaseModel):
    """Password change request model"""
    current_password: str
    new_password: str


@router.post("/change-password", status_code=status.HTTP_200_OK)
def change_password(
    request: Request,
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password (minimum 6 characters)
    if len(password_data.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters long"
        )
    
    # Hash and update password
    current_user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()
    db.refresh(current_user)
    
    # Set audit summary for middleware to log (no separate log_activity to avoid duplicate)
    from app.core.audit import set_audit_summary
    set_audit_summary(request, f"User {current_user.full_name or current_user.username} changed their password.")
    
    return {"message": "Password changed successfully"}


@router.post("/refresh", response_model=Token)
def refresh_token(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Refresh the access token"""
    # Verify user is still active
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Create new token with same expiration
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(current_user.id), "role": current_user.role},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}