"""
Facility-configurable AI claim vetting rules.

Managers define structured conditions + suggested actions in the DB.
No arbitrary code execution — fixed field allow-list and operators only.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set

from sqlalchemy.orm import Session

from app.models.ai_claim_vetting import AiClaimVettingRule
from app.services.ai_claim_vetting.schemas import SuggestedAction, VettingFinding
from app.utils.ghims_card import is_ghana_card

ALLOWED_RULE_FIELDS: Set[str] = {
    "memberNo",
    "hin",
    "ghanaCard",
    "specialtyAttended",
    "principalGDRG",
    "claimCheckCode",
    "hospitalRecNo",
    "cardSerialNo",
    "typeOfService",
    "typeOfAttendance",
}

ALLOWED_OPS: Set[str] = {
    "starts_with",
    "not_starts_with",
    "ends_with",
    "equals",
    "not_equals",
    "contains",
    "is_empty",
    "is_not_empty",
    "length_eq",
    "length_ne",
    "length_between",
    "regex",
    # Composite: non-empty HIN that is not 10 chars starting with 00
    "hin_format_invalid",
}


def _field_value(payload: Dict[str, Any], field: str) -> str:
    aliases = {
        "memberNo": ("memberNo", "member_no"),
        "hin": ("hin", "HIN"),
        "ghanaCard": ("ghanaCard", "ghana_card"),
        "specialtyAttended": ("specialtyAttended", "specialty_attended", "specialty"),
        "principalGDRG": ("principalGDRG", "principal_gdrg"),
    }
    keys = aliases.get(field, (field,))
    for key in keys:
        val = payload.get(key)
        if val is not None and str(val).strip() != "":
            return str(val)
    for key in keys:
        if key in payload:
            return str(payload.get(key) or "")
    return ""


def _condition_matches(payload: Dict[str, Any], condition: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(condition, dict):
        return False
    field = (condition.get("field") or "").strip()
    op = (condition.get("op") or "").strip().lower()
    if field not in ALLOWED_RULE_FIELDS or op not in ALLOWED_OPS:
        return False

    value = _field_value(payload, field)
    expected = condition.get("value")

    if bool(condition.get("skip_if_ghana_card")) and is_ghana_card(value):
        return False
    if bool(condition.get("skip_if_hin_shaped")):
        digits = re.sub(r"\D", "", value)
        if len(digits) == 10 and digits.startswith("00"):
            return False

    if op == "hin_format_invalid":
        v = value.strip()
        if not v:
            return False
        return not (len(v) == 10 and v.startswith("00"))
    if op == "is_empty":
        return value.strip() == ""
    if op == "is_not_empty":
        return value.strip() != ""
    if op == "starts_with":
        return value.startswith(str(expected if expected is not None else ""))
    if op == "not_starts_with":
        return not value.startswith(str(expected if expected is not None else ""))
    if op == "ends_with":
        return value.endswith(str(expected if expected is not None else ""))
    if op == "equals":
        return value == str(expected if expected is not None else "")
    if op == "not_equals":
        return value != str(expected if expected is not None else "")
    if op == "contains":
        return str(expected if expected is not None else "") in value
    if op == "length_eq":
        try:
            return len(value.strip()) == int(expected)
        except (TypeError, ValueError):
            return False
    if op == "length_ne":
        try:
            return len(value.strip()) != int(expected)
        except (TypeError, ValueError):
            return False
    if op == "length_between":
        try:
            lo = int(condition.get("min", 0))
            hi = int(condition.get("max", 0))
            n = len(value.strip())
            return lo <= n <= hi
        except (TypeError, ValueError):
            return False
    if op == "regex":
        pattern = str(expected or "")
        if not pattern:
            return False
        try:
            return re.search(pattern, value) is not None
        except re.error:
            return False
    return False


def _format_template(template: Optional[str], *, value: str, field: str, rule_name: str) -> str:
    text = (template or "").strip()
    if not text:
        return ""
    return (
        text.replace("{value}", value)
        .replace("{field}", field)
        .replace("{rule_name}", rule_name)
    )


def evaluate_rule(rule: AiClaimVettingRule, payload: Dict[str, Any]) -> Optional[VettingFinding]:
    if not rule.enabled:
        return None
    condition = rule.condition or {}
    if not _condition_matches(payload, condition):
        return None

    field = (condition.get("field") or "").strip()
    value = _field_value(payload, field)
    name = rule.name or rule.rule_code

    finding_text = _format_template(
        rule.finding_template, value=value, field=field, rule_name=name
    ) or f"{name}: '{value}' failed check on {field}."
    recommendation = _format_template(
        rule.recommendation_template, value=value, field=field, rule_name=name
    ) or (rule.description or "Review and correct this field.")

    action_raw = dict(rule.suggested_action or {})
    action_type = (action_raw.get("type") or "review_only").strip()
    details = action_raw.get("details") if isinstance(action_raw.get("details"), dict) else {}
    action = SuggestedAction(
        type=action_type,
        field=action_raw.get("field") or field,
        value=action_raw.get("value"),
        details={
            **details,
            "rule_id": rule.id,
            "rule_code": rule.rule_code,
            "current_value": value,
            "field": action_raw.get("field") or field,
            "prefix": (action_raw.get("value") or details.get("prefix"))
            if action_type == "strip_prefix"
            else None,
        },
    )

    return VettingFinding(
        rule_code=rule.rule_code,
        finding=finding_text[:500],
        severity=(rule.severity or "warning").strip() or "warning",
        explanation=(rule.description or finding_text).strip(),
        recommendation=recommendation,
        suggested_action=action,
        requires_human_review=True if rule.requires_human_review is None else bool(rule.requires_human_review),
    )


def run_configurable_rules(
    db: Session,
    payload: Dict[str, Any],
    *,
    analysis_mode: str = "phase1",
) -> List[VettingFinding]:
    """Load enabled facility rules for this analysis mode and evaluate against payload."""
    mode = (analysis_mode or "phase1").strip().lower()
    rows = (
        db.query(AiClaimVettingRule)
        .filter(AiClaimVettingRule.enabled == True)  # noqa: E712
        .order_by(AiClaimVettingRule.priority.asc(), AiClaimVettingRule.id.asc())
        .all()
    )
    findings: List[VettingFinding] = []
    for rule in rows:
        modes = rule.analysis_modes or ["phase1"]
        if isinstance(modes, str):
            modes = [modes]
        mode_ok = mode in modes or "all" in modes
        if not mode_ok and mode in ("coding", "thorough") and "phase1" in modes:
            mode_ok = True
        if not mode_ok:
            continue
        applies = (rule.applies_to or "ghims_import").strip().lower()
        if applies not in ("ghims_import", "both", "all"):
            continue
        finding = evaluate_rule(rule, payload or {})
        if finding:
            findings.append(finding)
    return findings


SEED_RULES: List[Dict[str, Any]] = [
    {
        "rule_code": "member_no_leading_hyphen",
        "name": "Member No leading hyphen",
        "description": (
            "Records sometimes prefix Member No with '-'. "
            "ClaimIT / NHIA numbers should not begin with a hyphen."
        ),
        "enabled": True,
        "severity": "critical",
        "priority": 10,
        "analysis_modes": ["phase1", "coding", "thorough"],
        "applies_to": "ghims_import",
        "is_system": True,
        "condition": {"field": "memberNo", "op": "starts_with", "value": "-"},
        "suggested_action": {
            "type": "strip_prefix",
            "field": "memberNo",
            "value": "-",
            "details": {"prefix": "-"},
        },
        "finding_template": "Member No begins with a hyphen ('{value}').",
        "recommendation_template": "Remove the leading hyphen from Member No.",
        "requires_human_review": True,
    },
    {
        "rule_code": "member_no_length_not_8",
        "name": "Member No length not 8",
        "description": (
            "Typical NHIA member numbers are 8 characters. "
            "Skips Ghana Card format and 10-digit HIN-shaped values starting with 00."
        ),
        "enabled": True,
        "severity": "warning",
        "priority": 20,
        "analysis_modes": ["phase1", "coding", "thorough"],
        "applies_to": "ghims_import",
        "is_system": True,
        "condition": {
            "field": "memberNo",
            "op": "length_ne",
            "value": 8,
            "skip_if_ghana_card": True,
            "skip_if_hin_shaped": True,
        },
        "suggested_action": {"type": "review_only", "field": "memberNo"},
        "finding_template": "Member No '{value}' is not 8 characters.",
        "recommendation_template": "Confirm the Member No against NHIA (usually 8 digits, no leading hyphen).",
        "requires_human_review": True,
    },
    {
        "rule_code": "hin_format_check",
        "name": "HIN format (10 digits, starts with 00)",
        "description": "When HIN is present it is normally 10 characters and begins with 00.",
        "enabled": True,
        "severity": "warning",
        "priority": 30,
        "analysis_modes": ["phase1", "coding", "thorough"],
        "applies_to": "ghims_import",
        "is_system": True,
        "condition": {"field": "hin", "op": "hin_format_invalid"},
        "suggested_action": {"type": "review_only", "field": "hin"},
        "finding_template": "HIN '{value}' may be invalid (expect 10 characters starting with 00).",
        "recommendation_template": "Confirm HIN is 10 characters and begins with 00.",
        "requires_human_review": True,
    },
]


def ensure_seed_rules(db: Session) -> int:
    """Insert missing system seed rules. Returns number inserted."""
    inserted = 0
    for seed in SEED_RULES:
        exists = (
            db.query(AiClaimVettingRule.id)
            .filter(AiClaimVettingRule.rule_code == seed["rule_code"])
            .first()
        )
        if exists:
            continue
        db.add(
            AiClaimVettingRule(
                rule_code=seed["rule_code"],
                name=seed["name"],
                description=seed.get("description"),
                enabled=bool(seed.get("enabled", True)),
                severity=seed.get("severity") or "warning",
                priority=int(seed.get("priority") or 100),
                analysis_modes=seed.get("analysis_modes") or ["phase1"],
                applies_to=seed.get("applies_to") or "ghims_import",
                is_system=bool(seed.get("is_system", True)),
                condition=seed.get("condition") or {},
                suggested_action=seed.get("suggested_action"),
                finding_template=seed.get("finding_template"),
                recommendation_template=seed.get("recommendation_template"),
                requires_human_review=bool(seed.get("requires_human_review", True)),
            )
        )
        inserted += 1
    if inserted:
        db.commit()
    return inserted
