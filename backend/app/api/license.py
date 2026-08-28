"""
Installation license: public status, activation with setup token, authenticated summary.
"""
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.user import User
from app.services import license_runtime

router = APIRouter(prefix="/license", tags=["license"])


@router.get("/public-status")
def get_public_license_status(db: Session = Depends(get_db)):
    """Used before login (login page, license setup)."""
    return license_runtime.evaluate(db, refresh_online=True)


class LicenseActivateBody(BaseModel):
    document: Dict[str, Any]
    setup_token: str = Field("", description="Must match LICENSE_SETUP_TOKEN")


@router.post("/activate")
def activate_license(
    body: LicenseActivateBody,
    db: Session = Depends(get_db),
    x_license_setup_token: Optional[str] = Header(None, alias="X-License-Setup-Token"),
):
    """
    Import a signed license document. Requires LICENSE_SETUP_TOKEN (body or X-License-Setup-Token header).
    """
    if not license_runtime.enforcement_enabled():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="License enforcement is disabled on this server.",
        )
    expected = (getattr(settings, "LICENSE_SETUP_TOKEN", "") or "").strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LICENSE_SETUP_TOKEN is not configured; cannot activate via API.",
        )
    provided = (body.setup_token or "").strip() or (x_license_setup_token or "").strip()
    if provided != expected:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid setup token.")

    ok, msg = license_runtime.activate_from_document(db, body.document)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return {"ok": True, "detail": msg}


@router.post("/pull-from-portal")
def pull_license_from_portal(db: Session = Depends(get_db)):
    """
    HMS fetches the paid month that covers today from the license portal.
    No setup token or JSON paste. Future paid months are not applied early.
    """
    if not license_runtime.enforcement_enabled():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="License enforcement is disabled on this server.",
        )
    ok, msg, extra = license_runtime.pull_and_activate_from_portal(db, force=True)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    period = (extra or {}).get("period")
    return {"ok": True, "detail": msg, "unchanged": bool((extra or {}).get("unchanged")), "period": period}


@router.get("/status")
def get_license_status_for_staff(
    db: Session = Depends(get_db),
    _user: User = Depends(require_role(["Admin", "Management"])),
):
    """Admin and Management see expiry and online state."""
    return license_runtime.evaluate(db, refresh_online=True)


class LicenseAnalyzeBody(BaseModel):
    document: Dict[str, Any]


@router.post("/analyze")
def analyze_license_document(
    body: LicenseAnalyzeBody,
    db: Session = Depends(get_db),
    _user: User = Depends(require_role(["Admin", "Management"])),
):
    """
    Read-only: verify pasted JSON (signature, issuer, facility, dates) without saving.
    Use this to test tampering; activation still requires setup token.
    """
    return license_runtime.analyze_untrusted_document(db, body.document)


@router.get("/activation-summary")
def get_license_activation_summary(
    db: Session = Depends(get_db),
    _user: User = Depends(require_role(["Admin", "Management"])),
):
    """
    Admin/Management: runtime status, parsed current file (including facility mismatch), and activation history.
    """
    ev = license_runtime.evaluate(db, refresh_online=True)
    row = license_runtime.get_installation_license_row(db)
    current_file = license_runtime.build_panel_current_file(db, row)
    history = license_runtime.list_activation_history(db, 25)
    return {**ev, "current_file": current_file, "activation_history": history}
