"""
Deterministic Phase-1 claim vetting rules.

Focus:
- ZOOM specialty → OPDC
- Ghana Card used as ClaimIT memberNo → convert to HIN
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.services.ai_claim_vetting.schemas import SuggestedAction, VettingFinding
from app.utils.ghims_card import (
    is_ghana_card,
    needs_hin_conversion,
    resolve_specialty_attended,
)


def _principal_gdrg(payload: Dict[str, Any]) -> str:
    principal = (payload.get("principalGDRG") or payload.get("principal_gdrg") or "").strip()
    if principal:
        return principal
    diagnoses = payload.get("diagnoses") or []
    if isinstance(diagnoses, list):
        for dx in diagnoses:
            if not isinstance(dx, dict):
                continue
            if str(dx.get("isPrincipal") or dx.get("is_principal") or "").strip() in ("1", "true", "True"):
                gdrg = (dx.get("gdrg") or dx.get("GDRG") or "").strip()
                if gdrg:
                    return gdrg
        for dx in diagnoses:
            if isinstance(dx, dict):
                gdrg = (dx.get("gdrg") or dx.get("GDRG") or "").strip()
                if gdrg:
                    return gdrg
    return ""


def _specialty(payload: Dict[str, Any]) -> str:
    return (
        payload.get("specialtyAttended")
        or payload.get("specialty_attended")
        or payload.get("specialty")
        or ""
    ).strip()


def _member_no(payload: Dict[str, Any]) -> str:
    return (payload.get("memberNo") or payload.get("member_no") or "").strip()


def _hin(payload: Dict[str, Any]) -> Optional[str]:
    hin = (payload.get("hin") or payload.get("HIN") or "").strip()
    return hin or None


def rule_specialty_zoom(payload: Dict[str, Any]) -> Optional[VettingFinding]:
    """Flag when export stored ZOOM as Specialty Attended (should be OPDC for ZOOM* services)."""
    specialty = _specialty(payload).upper()
    if specialty != "ZOOM":
        return None

    principal = _principal_gdrg(payload).upper()
    corrected = resolve_specialty_attended(specialty, principal or None)

    return VettingFinding(
        rule_code="specialty_zoom",
        finding="Specialty Attended is incorrectly set to ZOOM.",
        severity="critical",
        explanation=(
            "ZOOM is a service/GDRG family (e.g. dressings), not a ClaimIT specialty. "
            f"Specialty should be '{corrected}' (typically OPDC for ZOOM OPD services)"
            + (f". Principal GDRG: '{principal}'." if principal else ".")
        ),
        recommendation=f"Change Specialty Attended from ZOOM to {corrected}.",
        suggested_action=SuggestedAction(
            type="set_specialty",
            field="specialtyAttended",
            value=corrected,
            details={"from": "ZOOM", "principal_gdrg": principal or None},
        ),
        requires_human_review=True,
    )


def rule_ghana_card_member_no(payload: Dict[str, Any]) -> Optional[VettingFinding]:
    """Flag Ghana Card used as memberNo when ClaimIT needs HIN."""
    member_no = _member_no(payload)
    hin = _hin(payload)
    if not needs_hin_conversion(member_no, hin):
        # Member is Ghana Card but HIN already present elsewhere — still warn if memberNo is GC
        if is_ghana_card(member_no) and hin and not is_ghana_card(hin):
            return VettingFinding(
                rule_code="ghana_card_member_no",
                finding="Member No is still a Ghana Card; HIN is available but not applied to Member No.",
                severity="critical",
                explanation=(
                    "ClaimIT rejects Ghana Card as memberNo. A HIN is already on this claim "
                    f"({hin}) but Member No is still '{member_no}'."
                ),
                recommendation="Set Member No to the HIN and keep the Ghana Card in the Ghana Card field.",
                suggested_action=SuggestedAction(
                    type="apply_existing_hin",
                    field="memberNo",
                    value=hin,
                    details={"ghana_card": member_no, "hin": hin},
                ),
                requires_human_review=True,
            )
        return None

    return VettingFinding(
        rule_code="ghana_card_member_no",
        finding="Member No is a Ghana Card; ClaimIT requires HIN or NHIA number.",
        severity="critical",
        explanation=(
            f"Member No '{member_no}' matches Ghana Card format (GHA-…). "
            "ClaimIT export will fail until Member No is converted to HIN."
        ),
        recommendation="Convert Ghana Card to HIN (NHIA lookup), keep Ghana Card for CCC, set Member No to HIN.",
        suggested_action=SuggestedAction(
            type="convert_ghana_card_to_hin",
            field="memberNo",
            value=None,
            details={"ghana_card": member_no},
        ),
        requires_human_review=True,
    )


def run_phase1_rules(payload: Dict[str, Any]) -> List[VettingFinding]:
    """Run all Phase-1 deterministic rules against a claim-like dict."""
    findings: List[VettingFinding] = []
    for rule in (rule_specialty_zoom, rule_ghana_card_member_no):
        result = rule(payload or {})
        if result:
            findings.append(result)
    return findings
