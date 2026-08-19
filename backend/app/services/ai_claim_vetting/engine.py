"""
AI Claim Vetting Engine.

Modes:
- phase1: ClaimIT prep only (ZOOM specialty, Ghana Card → HIN) + facility rules
- coding (alias: standard): phase1 + diagnosis ICD↔DRG mismatch
- thorough: coding + procedure / medicine / investigation checks

Does not modify records; callers persist findings and apply accepted actions.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.services.ai_claim_vetting.clinical_rules import run_coding_rules
from app.services.ai_claim_vetting.configurable_rules import run_configurable_rules
from app.services.ai_claim_vetting.providers import get_provider
from app.services.ai_claim_vetting.schemas import VettingAnalyzeResult

VALID_MODES = frozenset({"phase1", "coding", "standard", "thorough", "llm"})


def normalize_analysis_mode(mode: Optional[str]) -> str:
    raw = (mode or "phase1").strip().lower()
    if raw == "standard":
        return "coding"
    if raw in ("phase1", "coding", "thorough", "llm"):
        return raw
    return "phase1"


def analyze_claim_payload(
    payload: Dict[str, Any],
    *,
    provider_name: Optional[str] = None,
    db: Optional[Session] = None,
    mode: str = "phase1",
) -> VettingAnalyzeResult:
    """Run the configured provider (+ DB coding / facility rules when db is provided)."""
    analysis_mode = normalize_analysis_mode(mode)
    # Dedicated local-AI assist path — model only, no phase rules mixed in.
    if analysis_mode == "llm":
        provider = get_provider(provider_name or "ollama_assist")
    else:
        provider = get_provider(provider_name)
    findings = list(provider.analyze(payload or {}))

    if db is not None and analysis_mode != "llm":
        findings.extend(
            run_configurable_rules(db, payload or {}, analysis_mode=analysis_mode)
        )
        if analysis_mode in ("coding", "thorough"):
            findings.extend(
                run_coding_rules(
                    db,
                    payload or {},
                    thorough=analysis_mode == "thorough",
                )
            )

    claim_id = (payload or {}).get("claimID") or (payload or {}).get("claim_id")
    label = {
        "phase1": "Phase 1",
        "coding": "coding",
        "thorough": "thorough",
        "llm": "local AI",
    }.get(analysis_mode, analysis_mode)
    if findings:
        summary = f"{len(findings)} issue(s) require human review ({label})."
    else:
        summary = f"No issues found ({label} scan)."
    return VettingAnalyzeResult(
        provider=provider.name,
        findings=findings,
        summary=summary,
        claim_claim_id=str(claim_id) if claim_id else None,
    )
