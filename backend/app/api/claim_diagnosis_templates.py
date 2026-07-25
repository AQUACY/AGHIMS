"""
Claim diagnosis template CRUD — auto-fill investigations/medicines from principal diagnosis.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_role, require_module_permission
from app.models.claim_diagnosis_template import ClaimDiagnosisTemplate
from app.models.user import User

router = APIRouter(prefix="/claims/diagnosis-templates", tags=["claim-diagnosis-templates"])


class ClaimDiagnosisTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    match_icd10: Optional[str] = None
    match_diagnosis: Optional[str] = None
    match_gdrg_prefix: Optional[str] = None
    match_keywords: Optional[str] = None
    sample_icd10: Optional[str] = None
    sample_diagnosis: Optional[str] = None
    sample_gdrg: Optional[str] = None
    investigations: List[Dict[str, Any]] = Field(default_factory=list)
    medicines: List[Dict[str, Any]] = Field(default_factory=list)
    is_shared: bool = True
    is_active: bool = True


class ClaimDiagnosisTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    match_icd10: Optional[str] = None
    match_diagnosis: Optional[str] = None
    match_gdrg_prefix: Optional[str] = None
    match_keywords: Optional[str] = None
    sample_icd10: Optional[str] = None
    sample_diagnosis: Optional[str] = None
    sample_gdrg: Optional[str] = None
    investigations: Optional[List[Dict[str, Any]]] = None
    medicines: Optional[List[Dict[str, Any]]] = None
    is_shared: Optional[bool] = None
    is_active: Optional[bool] = None


def _serialize(template: ClaimDiagnosisTemplate, db: Session) -> Dict[str, Any]:
    creator = db.query(User).filter(User.id == template.created_by).first()
    return {
        "id": template.id,
        "name": template.name,
        "description": template.description or "",
        "match_icd10": template.match_icd10 or "",
        "match_diagnosis": template.match_diagnosis or "",
        "match_gdrg_prefix": template.match_gdrg_prefix or "",
        "match_keywords": template.match_keywords or "",
        "sample_icd10": template.sample_icd10 or "",
        "sample_diagnosis": template.sample_diagnosis or "",
        "sample_gdrg": template.sample_gdrg or "",
        "investigations": template.get_investigations(),
        "medicines": template.get_medicines(),
        "created_by": template.created_by,
        "created_by_name": (creator.full_name if creator else None) or (creator.username if creator else None),
        "is_shared": bool(template.is_shared),
        "is_active": bool(template.is_active),
        "created_at": template.created_at.isoformat() if template.created_at else None,
        "updated_at": template.updated_at.isoformat() if template.updated_at else None,
    }


def _normalize_keywords(value: Optional[str]) -> str:
    if not value:
        return ""
    parts = [p.strip() for p in str(value).split(",") if p.strip()]
    return ", ".join(parts)


def _template_matches(
    template: ClaimDiagnosisTemplate,
    *,
    icd10: str,
    diagnosis: str,
    gdrg: str,
) -> bool:
    icd10_u = (icd10 or "").strip().upper()
    diag_l = (diagnosis or "").strip().lower()
    gdrg_u = (gdrg or "").strip().upper()

    match_icd = (template.match_icd10 or "").strip().upper()
    if match_icd and icd10_u and match_icd == icd10_u:
        return True

    match_diag = (template.match_diagnosis or "").strip().lower()
    if match_diag and diag_l and match_diag in diag_l:
        return True

    prefix = (template.match_gdrg_prefix or "").strip().upper()
    if prefix and gdrg_u and gdrg_u.startswith(prefix):
        return True

    keywords = [
        k.strip().lower()
        for k in str(template.match_keywords or "").split(",")
        if k.strip()
    ]
    if keywords and diag_l:
        if any(k in diag_l for k in keywords):
            return True

    # Fall back to sample fields
    sample_icd = (template.sample_icd10 or "").strip().upper()
    if sample_icd and icd10_u and sample_icd == icd10_u:
        return True
    sample_diag = (template.sample_diagnosis or "").strip().lower()
    if sample_diag and diag_l and sample_diag in diag_l:
        return True
    sample_gdrg = (template.sample_gdrg or "").strip().upper()
    if sample_gdrg and gdrg_u and (
        gdrg_u == sample_gdrg or gdrg_u.startswith(sample_gdrg[:4])
    ):
        return True

    return False


@router.get("")
def list_claim_diagnosis_templates(
    include_shared: bool = Query(True),
    active_only: bool = Query(True),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "read")),
):
    q = db.query(ClaimDiagnosisTemplate)
    if include_shared:
        q = q.filter(
            or_(
                ClaimDiagnosisTemplate.created_by == current_user.id,
                ClaimDiagnosisTemplate.is_shared == True,  # noqa: E712
            )
        )
    else:
        q = q.filter(ClaimDiagnosisTemplate.created_by == current_user.id)
    if active_only:
        q = q.filter(ClaimDiagnosisTemplate.is_active == True)  # noqa: E712
    if search and search.strip():
        term = f"%{search.strip()}%"
        q = q.filter(
            or_(
                ClaimDiagnosisTemplate.name.ilike(term),
                ClaimDiagnosisTemplate.match_diagnosis.ilike(term),
                ClaimDiagnosisTemplate.match_keywords.ilike(term),
                ClaimDiagnosisTemplate.sample_diagnosis.ilike(term),
                ClaimDiagnosisTemplate.match_icd10.ilike(term),
            )
        )
    rows = q.order_by(ClaimDiagnosisTemplate.name.asc()).all()
    return [_serialize(t, db) for t in rows]


@router.get("/match")
def match_claim_diagnosis_templates(
    icd10: Optional[str] = Query(None),
    diagnosis: Optional[str] = Query(None),
    gdrg: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "read")),
):
    """Return templates that match the given principal diagnosis."""
    q = db.query(ClaimDiagnosisTemplate).filter(
        ClaimDiagnosisTemplate.is_active == True,  # noqa: E712
        or_(
            ClaimDiagnosisTemplate.created_by == current_user.id,
            ClaimDiagnosisTemplate.is_shared == True,  # noqa: E712
        ),
    )
    rows = q.order_by(ClaimDiagnosisTemplate.name.asc()).all()
    matched = [
        t
        for t in rows
        if _template_matches(
            t,
            icd10=icd10 or "",
            diagnosis=diagnosis or "",
            gdrg=gdrg or "",
        )
    ]
    return [_serialize(t, db) for t in matched]


@router.get("/{template_id}")
def get_claim_diagnosis_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "read")),
):
    template = db.query(ClaimDiagnosisTemplate).filter(ClaimDiagnosisTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if template.created_by != current_user.id and not template.is_shared:
        raise HTTPException(status_code=403, detail="Not allowed to view this template")
    return _serialize(template, db)


@router.post("")
def create_claim_diagnosis_template(
    body: ClaimDiagnosisTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "update")),
):
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Template name is required")
    if not body.investigations and not body.medicines:
        raise HTTPException(status_code=400, detail="Add at least one investigation or medicine")

    template = ClaimDiagnosisTemplate(
        name=name,
        description=(body.description or "").strip() or None,
        match_icd10=(body.match_icd10 or "").strip().upper() or None,
        match_diagnosis=(body.match_diagnosis or "").strip() or None,
        match_gdrg_prefix=(body.match_gdrg_prefix or "").strip().upper() or None,
        match_keywords=_normalize_keywords(body.match_keywords) or None,
        sample_icd10=(body.sample_icd10 or "").strip().upper() or None,
        sample_diagnosis=(body.sample_diagnosis or "").strip() or None,
        sample_gdrg=(body.sample_gdrg or "").strip().upper() or None,
        created_by=current_user.id,
        is_shared=bool(body.is_shared),
        is_active=bool(body.is_active),
    )
    template.set_investigations(body.investigations or [])
    template.set_medicines(body.medicines or [])
    db.add(template)
    db.commit()
    db.refresh(template)
    return _serialize(template, db)


@router.put("/{template_id}")
def update_claim_diagnosis_template(
    template_id: int,
    body: ClaimDiagnosisTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "update")),
):
    template = db.query(ClaimDiagnosisTemplate).filter(ClaimDiagnosisTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if template.created_by != current_user.id and not current_user.has_role("Admin"):
        raise HTTPException(status_code=403, detail="Only the creator or Admin can edit this template")

    data = body.dict(exclude_unset=True)
    if "name" in data and data["name"] is not None:
        name = str(data["name"]).strip()
        if not name:
            raise HTTPException(status_code=400, detail="Template name is required")
        template.name = name
    if "description" in data:
        template.description = (data["description"] or "").strip() or None
    if "match_icd10" in data:
        template.match_icd10 = (data["match_icd10"] or "").strip().upper() or None
    if "match_diagnosis" in data:
        template.match_diagnosis = (data["match_diagnosis"] or "").strip() or None
    if "match_gdrg_prefix" in data:
        template.match_gdrg_prefix = (data["match_gdrg_prefix"] or "").strip().upper() or None
    if "match_keywords" in data:
        template.match_keywords = _normalize_keywords(data["match_keywords"]) or None
    if "sample_icd10" in data:
        template.sample_icd10 = (data["sample_icd10"] or "").strip().upper() or None
    if "sample_diagnosis" in data:
        template.sample_diagnosis = (data["sample_diagnosis"] or "").strip() or None
    if "sample_gdrg" in data:
        template.sample_gdrg = (data["sample_gdrg"] or "").strip().upper() or None
    if "investigations" in data and data["investigations"] is not None:
        template.set_investigations(data["investigations"])
    if "medicines" in data and data["medicines"] is not None:
        template.set_medicines(data["medicines"])
    if "is_shared" in data and data["is_shared"] is not None:
        template.is_shared = bool(data["is_shared"])
    if "is_active" in data and data["is_active"] is not None:
        template.is_active = bool(data["is_active"])

    template.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(template)
    return _serialize(template, db)


@router.delete("/{template_id}")
def delete_claim_diagnosis_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "update")),
):
    template = db.query(ClaimDiagnosisTemplate).filter(ClaimDiagnosisTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if template.created_by != current_user.id and not current_user.has_role("Admin"):
        raise HTTPException(status_code=403, detail="Only the creator or Admin can delete this template")
    db.delete(template)
    db.commit()
    return {"success": True, "id": template_id}
