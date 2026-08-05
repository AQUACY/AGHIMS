"""
AI Claim Vetting Engine (Phase 1).

Analyzes claim-like payloads for ClaimIT-blocking issues:
- ZOOM specialty → suggest OPDC
- Ghana Card as memberNo → suggest HIN conversion

Does not modify records; callers persist findings and apply accepted actions.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.services.ai_claim_vetting.providers import get_provider
from app.services.ai_claim_vetting.schemas import VettingAnalyzeResult


def analyze_claim_payload(
    payload: Dict[str, Any],
    *,
    provider_name: Optional[str] = None,
) -> VettingAnalyzeResult:
    """Run the configured provider against a claim JSON payload."""
    provider = get_provider(provider_name)
    findings = provider.analyze(payload or {})
    claim_id = (payload or {}).get("claimID") or (payload or {}).get("claim_id")
    if findings:
        summary = f"{len(findings)} issue(s) require human review."
    else:
        summary = "No Phase-1 issues found (specialty ZOOM / Ghana Card memberNo)."
    return VettingAnalyzeResult(
        provider=provider.name,
        findings=findings,
        summary=summary,
        claim_claim_id=str(claim_id) if claim_id else None,
    )
