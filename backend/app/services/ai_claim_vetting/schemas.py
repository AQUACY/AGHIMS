"""Shared schemas for AI claim vetting findings."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SuggestedAction(BaseModel):
    """Machine-readable correction the human can approve."""

    type: str  # set_specialty | convert_ghana_card_to_hin | set_diagnosis_gdrg | set_procedure_gdrg | review_*
    field: Optional[str] = None
    value: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class VettingFinding(BaseModel):
    """One AI/rules finding. Never applied without human approval."""

    rule_code: str
    finding: str
    severity: str  # critical | warning | review_needed
    explanation: str
    recommendation: str
    suggested_action: Optional[SuggestedAction] = None
    requires_human_review: bool = True


class VettingAnalyzeResult(BaseModel):
    """Engine output for a claim-like payload."""

    provider: str
    findings: List[VettingFinding] = Field(default_factory=list)
    summary: str = ""
    claim_claim_id: Optional[str] = None
