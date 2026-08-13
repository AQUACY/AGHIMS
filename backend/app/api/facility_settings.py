"""
Facility branding (display name, facility code) and per-user theme colors.

Facility identity is shared. Brand colors are stored per user so one person's
theme does not affect another.
"""
import re
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin_or_super_admin
from app.models.facility_settings import FacilitySettings
from app.models.user import User
from app.models.user_brand_preferences import UserBrandPreferences

router = APIRouter(prefix="/facility-settings", tags=["facility-settings"])

DEFAULT_DISPLAY_NAME = "KDG Health App"
_HEX_RE = re.compile(r"^#([0-9A-Fa-f]{6})$")
_HEX_FIELDS = (
    "bg_color_light",
    "bg_color_dark",
    "accent_color",
    "text_color_light",
    "text_color_dark",
)


def _normalize_hex(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    if not _HEX_RE.match(raw):
        raise ValueError("Color must be a 6-digit hex value like #3b82f6")
    return raw.lower()


def _get_or_create_facility(db: Session) -> FacilitySettings:
    row = db.query(FacilitySettings).order_by(FacilitySettings.id).first()
    if not row:
        row = FacilitySettings(display_name=DEFAULT_DISPLAY_NAME, facility_code=None)
        db.add(row)
        db.commit()
        db.refresh(row)
    elif not (row.display_name or "").strip():
        row.display_name = DEFAULT_DISPLAY_NAME
        db.commit()
        db.refresh(row)
    return row


def _get_or_create_user_theme(db: Session, user_id: int) -> UserBrandPreferences:
    row = (
        db.query(UserBrandPreferences)
        .filter(UserBrandPreferences.user_id == user_id)
        .first()
    )
    if not row:
        row = UserBrandPreferences(user_id=user_id)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _theme_public(row: Optional[UserBrandPreferences]) -> "UserThemePublic":
    if not row:
        return UserThemePublic()
    return UserThemePublic(
        bg_color_light=(row.bg_color_light or "").strip() or None,
        bg_color_dark=(row.bg_color_dark or "").strip() or None,
        accent_color=(row.accent_color or "").strip() or None,
        text_color_light=(row.text_color_light or "").strip() or None,
        text_color_dark=(row.text_color_dark or "").strip() or None,
    )


def _to_public(row: FacilitySettings) -> "FacilitySettingsPublic":
    # Colors on facility_settings are legacy login defaults only; active UI
    # uses per-user theme. Public payload still exposes them for the login page.
    return FacilitySettingsPublic(
        display_name=(row.display_name or DEFAULT_DISPLAY_NAME).strip() or DEFAULT_DISPLAY_NAME,
        facility_code=(row.facility_code or "").strip() or None,
        bg_color_light=(row.bg_color_light or "").strip() or None,
        bg_color_dark=(row.bg_color_dark or "").strip() or None,
        accent_color=(row.accent_color or "").strip() or None,
        text_color_light=(getattr(row, "text_color_light", None) or "").strip() or None,
        text_color_dark=(getattr(row, "text_color_dark", None) or "").strip() or None,
    )


class FacilitySettingsPublic(BaseModel):
    display_name: str
    facility_code: Optional[str] = None
    bg_color_light: Optional[str] = None
    bg_color_dark: Optional[str] = None
    accent_color: Optional[str] = None
    text_color_light: Optional[str] = None
    text_color_dark: Optional[str] = None


class FacilityIdentityUpdate(BaseModel):
    """Shared facility name/code. Colors are not updated here."""

    display_name: str = Field(..., min_length=1, max_length=255)
    facility_code: Optional[str] = Field(None, max_length=64)


class UserThemePublic(BaseModel):
    bg_color_light: Optional[str] = None
    bg_color_dark: Optional[str] = None
    accent_color: Optional[str] = None
    text_color_light: Optional[str] = None
    text_color_dark: Optional[str] = None


class UserThemeUpdate(BaseModel):
    bg_color_light: Optional[str] = Field(None, max_length=7)
    bg_color_dark: Optional[str] = Field(None, max_length=7)
    accent_color: Optional[str] = Field(None, max_length=7)
    text_color_light: Optional[str] = Field(None, max_length=7)
    text_color_dark: Optional[str] = Field(None, max_length=7)

    @field_validator(*_HEX_FIELDS, mode="before")
    @classmethod
    def validate_hex(cls, v):
        try:
            return _normalize_hex(v)
        except ValueError as e:
            raise ValueError(str(e)) from e


@router.get("/public", response_model=FacilitySettingsPublic)
def get_facility_settings_public(db: Session = Depends(get_db)):
    """Facility identity (+ optional login-page color defaults). No auth."""
    row = _get_or_create_facility(db)
    return _to_public(row)


@router.put("/", response_model=FacilitySettingsPublic)
def update_facility_settings(
    data: FacilityIdentityUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_admin_or_super_admin()),
):
    """Update shared facility name/code only (Admin). Colors are per-user."""
    row = _get_or_create_facility(db)
    row.display_name = (data.display_name or "").strip() or DEFAULT_DISPLAY_NAME
    code = (data.facility_code or "").strip()
    row.facility_code = code if code else None
    db.commit()
    db.refresh(row)
    return _to_public(row)


@router.get("/my-theme", response_model=UserThemePublic)
def get_my_theme(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Current user's personal brand colors."""
    row = (
        db.query(UserBrandPreferences)
        .filter(UserBrandPreferences.user_id == current_user.id)
        .first()
    )
    return _theme_public(row)


@router.put("/my-theme", response_model=UserThemePublic)
def update_my_theme(
    data: UserThemeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Save personal brand colors for the signed-in user only."""
    row = _get_or_create_user_theme(db, current_user.id)
    # Explicit null/empty clears that slot back to theme defaults
    row.bg_color_light = data.bg_color_light
    row.bg_color_dark = data.bg_color_dark
    row.accent_color = data.accent_color
    row.text_color_light = data.text_color_light
    row.text_color_dark = data.text_color_dark
    db.commit()
    db.refresh(row)
    return _theme_public(row)
