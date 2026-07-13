"""
Facility branding (display name, facility code) for multi-site deployments.
"""
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin_or_super_admin
from app.models.facility_settings import FacilitySettings

router = APIRouter(prefix="/facility-settings", tags=["facility-settings"])

DEFAULT_DISPLAY_NAME = "KDG Health App"


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


class FacilitySettingsPublic(BaseModel):
    display_name: str
    facility_code: Optional[str] = None


class FacilitySettingsUpdate(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=255)
    facility_code: Optional[str] = Field(None, max_length=64)


@router.get("/public", response_model=FacilitySettingsPublic)
def get_facility_settings_public(db: Session = Depends(get_db)):
    """Branding for login page and unauthenticated views (no auth)."""
    row = _get_or_create_facility(db)
    return FacilitySettingsPublic(
        display_name=(row.display_name or DEFAULT_DISPLAY_NAME).strip() or DEFAULT_DISPLAY_NAME,
        facility_code=(row.facility_code or "").strip() or None,
    )


@router.put("/", response_model=FacilitySettingsPublic)
def update_facility_settings(
    data: FacilitySettingsUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_admin_or_super_admin()),
):
    row = _get_or_create_facility(db)
    row.display_name = (data.display_name or "").strip() or DEFAULT_DISPLAY_NAME
    code = (data.facility_code or "").strip()
    row.facility_code = code if code else None
    db.commit()
    db.refresh(row)
    return FacilitySettingsPublic(
        display_name=row.display_name,
        facility_code=row.facility_code,
    )
