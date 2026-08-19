"""
Clinical / coding rules for AI claim vetting (DRG & code consistency).

Used in standard scans (diagnosis DRG) and thorough mode (also procedures/meds).
Suggestions only — humans choose the correct code before apply.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.services.ai_claim_vetting.code_checks import (
    allowed_drgs_for_icd10,
    dx_gdrg,
    dx_icd10,
    medicine_code_exists,
    normalize_code,
    service_gdrg_exists,
)
from app.services.ai_claim_vetting.schemas import SuggestedAction, VettingFinding


def _format_allowed(allowed: List[Dict[str, str]], limit: int = 6) -> str:
    parts = []
    for row in allowed[:limit]:
        desc = row.get("drg_description") or ""
        parts.append(f"{row['drg_code']}" + (f" ({desc})" if desc else ""))
    extra = len(allowed) - limit
    text = "; ".join(parts) if parts else "(none)"
    if extra > 0:
        text += f"; +{extra} more"
    return text


def rule_diagnosis_drg_mismatch(db: Session, payload: Dict[str, Any]) -> List[VettingFinding]:
    findings: List[VettingFinding] = []
    diagnoses = payload.get("diagnoses") or []
    if not isinstance(diagnoses, list):
        return findings

    for idx, dx in enumerate(diagnoses):
        if not isinstance(dx, dict):
            continue
        icd = dx_icd10(dx)
        gdrg = dx_gdrg(dx)
        if not icd or not gdrg:
            continue
        allowed = allowed_drgs_for_icd10(db, icd)
        if not allowed:
            findings.append(
                VettingFinding(
                    rule_code="diagnosis_icd_unmapped",
                    finding=f"Diagnosis ICD-10 '{icd}' has no active ICD→DRG mapping.",
                    severity="review_needed",
                    explanation=(
                        f"Row {idx + 1}: ICD-10 '{icd}' with GDRG '{gdrg}' — "
                        "no mapped DRGs found in the facility ICD-10–DRG table. "
                        "Confirm coding or update the mapping list."
                    ),
                    recommendation="Review ICD-10 / GDRG against ICD-10 DRG Mapping, or update mappings.",
                    suggested_action=SuggestedAction(
                        type="review_diagnosis_codes",
                        field=f"diagnoses[{idx}].gdrgCode",
                        value=gdrg,
                        details={
                            "index": idx,
                            "icd10": icd,
                            "current_gdrg": gdrg,
                            "diagnosis": (dx.get("diagnosis") or "")[:200],
                            "allowed_drgs": [],
                        },
                    ),
                )
            )
            continue

        allowed_codes = {normalize_code(a["drg_code"]) for a in allowed}
        if gdrg in allowed_codes:
            continue

        preferred = allowed[0]["drg_code"] if len(allowed) == 1 else None
        findings.append(
            VettingFinding(
                rule_code="diagnosis_drg_mismatch",
                finding=f"Diagnosis GDRG '{gdrg}' does not match ICD-10 '{icd}' mappings.",
                severity="critical",
                explanation=(
                    f"Row {idx + 1} ({(dx.get('diagnosis') or 'diagnosis')[:80]}): "
                    f"GDRG '{gdrg}' is not among mapped DRGs for ICD-10 '{icd}'. "
                    f"Allowed: {_format_allowed(allowed)}."
                ),
                recommendation=(
                    f"Choose the correct GDRG"
                    + (f" (suggested: {preferred})" if preferred else " from the mapped list")
                    + "."
                ),
                suggested_action=SuggestedAction(
                    type="set_diagnosis_gdrg",
                    field=f"diagnoses[{idx}].gdrgCode",
                    value=preferred,
                    details={
                        "index": idx,
                        "icd10": icd,
                        "current_gdrg": gdrg,
                        "diagnosis": (dx.get("diagnosis") or "")[:200],
                        "allowed_drgs": allowed,
                        "preferred": preferred,
                        "sync_principal": True,
                    },
                ),
            )
        )
    return findings


def rule_procedure_drg_mismatch(db: Session, payload: Dict[str, Any]) -> List[VettingFinding]:
    findings: List[VettingFinding] = []
    procedures = payload.get("procedures") or []
    if not isinstance(procedures, list):
        return findings

    for idx, proc in enumerate(procedures):
        if not isinstance(proc, dict):
            continue
        icd = normalize_code(proc.get("icd10") or proc.get("ICD10"))
        gdrg = normalize_code(proc.get("gdrgCode") or proc.get("gdrg") or proc.get("GDRG"))
        if not icd or not gdrg:
            # Thorough: unknown GDRG vs price list when no ICD
            if gdrg and not service_gdrg_exists(db, gdrg):
                findings.append(
                    VettingFinding(
                        rule_code="procedure_gdrg_unknown",
                        finding=f"Procedure GDRG '{gdrg}' not found in price lists.",
                        severity="warning",
                        explanation=(
                            f"Procedure row {idx + 1}: GDRG '{gdrg}' was not found in "
                            "procedure, surgery, or unmapped DRG price tables."
                        ),
                        recommendation="Confirm the GDRG against Price List / Unmapped DRG list.",
                        suggested_action=SuggestedAction(
                            type="review_procedure_gdrg",
                            field=f"procedures[{idx}].gdrgCode",
                            value=gdrg,
                            details={"index": idx, "current_gdrg": gdrg, "allowed_drgs": []},
                        ),
                    )
                )
            continue

        allowed = allowed_drgs_for_icd10(db, icd)
        if not allowed:
            continue
        allowed_codes = {normalize_code(a["drg_code"]) for a in allowed}
        if gdrg in allowed_codes:
            continue
        preferred = allowed[0]["drg_code"] if len(allowed) == 1 else None
        findings.append(
            VettingFinding(
                rule_code="procedure_drg_mismatch",
                finding=f"Procedure GDRG '{gdrg}' does not match ICD-10 '{icd}' mappings.",
                severity="critical",
                explanation=(
                    f"Procedure row {idx + 1}: GDRG '{gdrg}' is not mapped for ICD-10 '{icd}'. "
                    f"Allowed: {_format_allowed(allowed)}."
                ),
                recommendation=(
                    "Choose the correct procedure GDRG from the mapped list"
                    + (f" (suggested: {preferred})" if preferred else "")
                    + "."
                ),
                suggested_action=SuggestedAction(
                    type="set_procedure_gdrg",
                    field=f"procedures[{idx}].gdrgCode",
                    value=preferred,
                    details={
                        "index": idx,
                        "icd10": icd,
                        "current_gdrg": gdrg,
                        "allowed_drgs": allowed,
                        "preferred": preferred,
                    },
                ),
            )
        )
    return findings


def rule_medicine_code_unknown(db: Session, payload: Dict[str, Any]) -> List[VettingFinding]:
    findings: List[VettingFinding] = []
    medicines = payload.get("medicines") or payload.get("medications") or []
    if not isinstance(medicines, list):
        return findings

    for idx, med in enumerate(medicines):
        if not isinstance(med, dict):
            continue
        code = (med.get("medicineCode") or med.get("medication_code") or med.get("code") or "").strip()
        if not code:
            continue
        if medicine_code_exists(db, code):
            continue
        findings.append(
            VettingFinding(
                rule_code="medicine_code_unknown",
                finding=f"Medicine code '{code}' not found in the product price list.",
                severity="warning",
                explanation=(
                    f"Medicine row {idx + 1}: code '{code}' is not in product_prices. "
                    "It may be mistyped or missing from the NHIA medicine list."
                ),
                recommendation="Search Price List for the correct medicine code and update this row.",
                suggested_action=SuggestedAction(
                    type="review_medicine_code",
                    field=f"medicines[{idx}].medicineCode",
                    value=code,
                    details={"index": idx, "current_code": code, "allowed_drgs": []},
                ),
            )
        )
    return findings


def rule_investigation_gdrg_unknown(db: Session, payload: Dict[str, Any]) -> List[VettingFinding]:
    findings: List[VettingFinding] = []
    investigations = payload.get("investigations") or []
    if not isinstance(investigations, list):
        return findings

    for idx, inv in enumerate(investigations):
        if not isinstance(inv, dict):
            continue
        gdrg = normalize_code(inv.get("gdrgCode") or inv.get("gdrg") or inv.get("GDRG"))
        if not gdrg:
            continue
        if service_gdrg_exists(db, gdrg):
            continue
        findings.append(
            VettingFinding(
                rule_code="investigation_gdrg_unknown",
                finding=f"Investigation GDRG '{gdrg}' not found in price lists.",
                severity="warning",
                explanation=(
                    f"Investigation row {idx + 1}: GDRG '{gdrg}' was not found in "
                    "procedure / surgery / unmapped DRG tables."
                ),
                recommendation="Confirm the investigation GDRG against the price list.",
                suggested_action=SuggestedAction(
                    type="review_investigation_gdrg",
                    field=f"investigations[{idx}].gdrgCode",
                    value=gdrg,
                    details={"index": idx, "current_gdrg": gdrg, "allowed_drgs": []},
                ),
            )
        )
    return findings


def run_coding_rules(
    db: Session,
    payload: Dict[str, Any],
    *,
    thorough: bool = False,
) -> List[VettingFinding]:
    """
    Coding consistency checks.
    Standard: diagnosis ICD↔DRG.
    Thorough: + procedure / medicine / investigation code checks.
    """
    findings: List[VettingFinding] = []
    findings.extend(rule_diagnosis_drg_mismatch(db, payload or {}))
    if thorough:
        findings.extend(rule_procedure_drg_mismatch(db, payload or {}))
        findings.extend(rule_medicine_code_unknown(db, payload or {}))
        findings.extend(rule_investigation_gdrg_unknown(db, payload or {}))
    return findings
