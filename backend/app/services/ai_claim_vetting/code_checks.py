"""
DB-backed code lookups for AI claim vetting (ICD→DRG, medicine, procedure GDRG).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.icd10_drg_mapping import ICD10DRGMapping
from app.models.procedure_price import ProcedurePrice
from app.models.product_price import ProductPrice
from app.models.surgery_price import SurgeryPrice
from app.models.unmapped_drg_price import UnmappedDRGPrice


def normalize_code(value: Optional[str]) -> str:
    return (value or "").strip().upper()


def allowed_drgs_for_icd10(db: Session, icd10_code: str) -> List[Dict[str, str]]:
    """Return distinct active DRG mappings for an ICD-10 code."""
    code = normalize_code(icd10_code)
    if not code:
        return []
    rows = (
        db.query(ICD10DRGMapping)
        .filter(
            ICD10DRGMapping.is_active == True,  # noqa: E712
            func.upper(ICD10DRGMapping.icd10_code) == code,
        )
        .all()
    )
    results: List[Dict[str, str]] = []
    seen: Set[str] = set()
    for row in rows:
        drg = normalize_code(row.drg_code)
        if not drg or drg in seen:
            continue
        seen.add(drg)
        results.append(
            {
                "drg_code": drg,
                "drg_description": (row.drg_description or "").strip(),
                "icd10_code": (row.icd10_code or "").strip(),
                "icd10_description": (row.icd10_description or "").strip(),
            }
        )
    return results


def medicine_code_exists(db: Session, medicine_code: str) -> bool:
    code = normalize_code(medicine_code)
    if not code:
        return False
    return (
        db.query(ProductPrice.id)
        .filter(func.upper(ProductPrice.medication_code) == code)
        .first()
        is not None
    )


def service_gdrg_exists(db: Session, gdrg_code: str) -> bool:
    code = normalize_code(gdrg_code)
    if not code:
        return False
    for model, col in (
        (ProcedurePrice, ProcedurePrice.g_drg_code),
        (SurgeryPrice, SurgeryPrice.g_drg_code),
        (UnmappedDRGPrice, UnmappedDRGPrice.g_drg_code),
    ):
        if db.query(model.id).filter(func.upper(col) == code).first():
            return True
    return False


def dx_gdrg(dx: Dict[str, Any]) -> str:
    return normalize_code(
        dx.get("gdrgCode") or dx.get("gdrg") or dx.get("GDRG") or dx.get("g_drg_code")
    )


def dx_icd10(dx: Dict[str, Any]) -> str:
    return normalize_code(dx.get("icd10") or dx.get("ICD10") or dx.get("icd10_code"))
