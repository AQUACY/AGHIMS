from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.core.database import get_db
from app.core.dependencies import (
    create_access_token,
    get_current_user,
    hash_password,
    require_admin,
    verify_password,
)
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str | None = None
    is_admin: bool = False


class UserUpdate(BaseModel):
    full_name: str | None = None
    is_admin: bool | None = None
    is_active: bool | None = None
    password: str | None = None


class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str | None = None
    is_admin: bool = False
    is_active: bool = True
    created_at: str | None = None

    class Config:
        from_attributes = True


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        is_admin=bool(user.is_admin),
        is_active=bool(user.is_active),
        created_at=user.created_at.isoformat() if user.created_at else None,
    )


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class FacilityPublic(BaseModel):
    facility_name: str
    facility_code: str


@router.get("/facility-public", response_model=FacilityPublic)
def facility_public():
    return FacilityPublic(
        facility_name=settings.FACILITY_NAME,
        facility_code=settings.FACILITY_CODE,
    )


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="User account is inactive")
    token = create_access_token(user.username)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return _user_response(current_user)


@router.get("/users", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    users = db.query(User).order_by(User.username).all()
    return [_user_response(u) for u in users]


@router.post("/users", response_model=UserResponse)
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    username = (body.username or "").strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    if len(body.password or "") < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    user = User(
        username=username,
        full_name=(body.full_name or "").strip() or None,
        hashed_password=hash_password(body.password),
        is_admin=bool(body.is_admin),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_response(user)


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    body: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.is_active is False and user.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")
    if body.is_admin is False and user.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot remove your own admin access")

    if body.full_name is not None:
        user.full_name = (body.full_name or "").strip() or None
    if body.is_admin is not None:
        user.is_admin = bool(body.is_admin)
    if body.is_active is not None:
        user.is_active = bool(body.is_active)
    if body.password:
        if len(body.password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        user.hashed_password = hash_password(body.password)

    db.commit()
    db.refresh(user)
    return _user_response(user)


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")
    db.delete(user)
    db.commit()
    return {"deleted": True, "id": user_id}
