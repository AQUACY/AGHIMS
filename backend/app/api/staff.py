"""
Staff management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import pandas as pd
from io import BytesIO

from app.core.database import get_db
from app.core.security import get_password_hash
from app.core.dependencies import get_current_user, require_role
from app.models.user import User

router = APIRouter(prefix="/staff", tags=["staff"])


class StaffCreate(BaseModel):
    """Staff creation model"""
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: str
    role: str
    is_active: bool = True


class StaffUpdate(BaseModel):
    """Staff update model"""
    username: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class StaffResponse(BaseModel):
    """Staff response model"""
    id: int
    username: str
    email: Optional[str]
    full_name: Optional[str]
    role: str
    is_active: bool

    class Config:
        from_attributes = True


@router.get("/", response_model=List[StaffResponse])
def get_all_staff(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Get all staff members - Admin only"""
    staff = db.query(User).all()
    return staff


@router.post("/", response_model=StaffResponse, status_code=status.HTTP_201_CREATED)
def create_staff(
    staff_data: StaffCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Create a new staff member - Admin only"""
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == staff_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{staff_data.username}' already exists"
        )
    
    # Check if email already exists (if provided)
    if staff_data.email:
        existing_email = db.query(User).filter(User.email == staff_data.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email '{staff_data.email}' already exists"
            )
    
    # Create new user
    hashed_password = get_password_hash(staff_data.password)
    new_user = User(
        username=staff_data.username,
        email=staff_data.email,
        full_name=staff_data.full_name,
        hashed_password=hashed_password,
        role=staff_data.role,
        is_active=staff_data.is_active
    )
    
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database error: {str(e)}"
        )


@router.put("/{user_id}", response_model=StaffResponse)
def update_staff(
    user_id: int,
    staff_data: StaffUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Update a staff member - Admin only"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staff member with ID {user_id} not found"
        )
    
    # Check username uniqueness if changing username
    if staff_data.username and staff_data.username != user.username:
        existing_user = db.query(User).filter(User.username == staff_data.username).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Username '{staff_data.username}' already exists"
            )
        user.username = staff_data.username
    
    # Check email uniqueness if changing email
    if staff_data.email and staff_data.email != user.email:
        existing_email = db.query(User).filter(User.email == staff_data.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email '{staff_data.email}' already exists"
            )
        user.email = staff_data.email
    
    # Update other fields
    if staff_data.full_name is not None:
        user.full_name = staff_data.full_name
    if staff_data.password:
        user.hashed_password = get_password_hash(staff_data.password)
    if staff_data.role:
        user.role = staff_data.role
    if staff_data.is_active is not None:
        user.is_active = staff_data.is_active
    
    try:
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database error: {str(e)}"
        )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_staff(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Delete/deactivate a staff member - Admin only"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staff member with ID {user_id} not found"
        )
    
    # Don't allow deleting yourself
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account"
        )
    
    # Soft delete by deactivating
    user.is_active = False
    db.commit()
    return None


@router.post("/import")
def import_staff_from_excel(
    file: UploadFile = File(...),
    default_password: str = Query("password123", description="Default password for imported staff"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """
    Import staff from Excel file - Admin only
    Expected columns: username, full_name, Gender, Email, role, is_active
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an Excel file (.xlsx or .xls)"
        )
    
    try:
        # Read Excel file
        contents = file.file.read()
        df = pd.read_excel(BytesIO(contents))
        
        # Validate required columns
        required_columns = ['username', 'full_name', 'Email', 'role']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )
        
        # Process rows
        imported = []
        errors = []
        hashed_password = get_password_hash(default_password)
        
        for index, row in df.iterrows():
            try:
                username = str(row['username']).strip() if pd.notna(row['username']) else None
                if not username:
                    errors.append(f"Row {index + 2}: Username is required")
                    continue
                
                # Check if user already exists
                existing_user = db.query(User).filter(User.username == username).first()
                if existing_user:
                    errors.append(f"Row {index + 2}: Username '{username}' already exists")
                    continue
                
                # Extract data
                full_name = str(row['full_name']).strip() if pd.notna(row['full_name']) else None
                email_raw = str(row['Email']).strip() if pd.notna(row['Email']) and str(row['Email']).strip().lower() != 'nan' else None
                role = str(row['role']).strip() if pd.notna(row['role']) else None
                
                if not role:
                    errors.append(f"Row {index + 2}: Role is required")
                    continue
                
                # Handle placeholder/default emails - set to None to avoid unique constraint violations
                email = None
                if email_raw:
                    email_lower = email_raw.lower().strip()
                    # Common placeholder email patterns
                    placeholder_emails = [
                        'default@gmail.com',
                        'default@email.com',
                        'n/a',
                        'na',
                        'none',
                        '',
                    ]
                    if email_lower not in placeholder_emails:
                        email = email_raw.strip()
                
                # Check email uniqueness if provided (and not None)
                if email:
                    existing_email = db.query(User).filter(User.email == email).first()
                    if existing_email:
                        errors.append(f"Row {index + 2}: Email '{email}' already exists")
                        continue
                
                # Handle is_active - default to True if not provided or NaN
                is_active = True
                if 'is_active' in df.columns:
                    is_active_val = row['is_active']
                    if pd.notna(is_active_val):
                        try:
                            is_active = bool(float(is_active_val))  # Handle both 1.0 and 1
                        except:
                            is_active = True
                
                # Create user
                new_user = User(
                    username=username,
                    email=email if email else None,
                    full_name=full_name,
                    hashed_password=hashed_password,
                    role=role,
                    is_active=is_active
                )
                
                db.add(new_user)
                imported.append(username)
                
            except Exception as e:
                errors.append(f"Row {index + 2}: {str(e)}")
        
        # Commit all successful imports
        try:
            db.commit()
            return {
                "message": f"Successfully imported {len(imported)} staff member(s)",
                "imported": imported,
                "errors": errors,
                "total_rows": len(df)
            }
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Database error during import: {str(e)}"
            )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error processing Excel file: {str(e)}"
        )
