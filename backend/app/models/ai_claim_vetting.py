"""
AI claim vetting findings, batch jobs, and human decisions (audit trail).
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class AiClaimVettingJob(Base):
    """Background batch analyze run over GHIMS import items."""

    __tablename__ = "ai_claim_vetting_jobs"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("claim_xml_import_batches.id"), nullable=False, index=True)
    # queued | running | completed | failed
    status = Column(String(20), nullable=False, default="queued", index=True)
    total_items = Column(Integer, nullable=False, default=0)
    processed_items = Column(Integer, nullable=False, default=0)
    findings_count = Column(Integer, nullable=False, default=0)
    item_ids = Column(JSON, nullable=True)  # requested item ids
    analysis_mode = Column(String(20), nullable=False, default="standard")  # standard | thorough
    error_message = Column(Text, nullable=True)
    summary_by_rule = Column(JSON, nullable=True)  # {rule_code: count} after complete

    started_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow_callable, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    started_by = relationship("User", foreign_keys=[started_by_id])
    findings = relationship("AiClaimVettingFinding", back_populates="job")


class AiClaimVettingFinding(Base):
    """One AI/rules recommendation awaiting (or after) human review."""

    __tablename__ = "ai_claim_vetting_findings"

    id = Column(Integer, primary_key=True, index=True)
    # ghims_import | native_claim | sample
    source_type = Column(String(30), nullable=False, index=True)
    source_id = Column(Integer, nullable=True, index=True)  # ClaimXmlImportItem.id or Claim.id
    claim_claim_id = Column(String(50), nullable=True, index=True)
    job_id = Column(Integer, ForeignKey("ai_claim_vetting_jobs.id"), nullable=True, index=True)

    rule_code = Column(String(64), nullable=False, index=True)
    finding = Column(String(500), nullable=False)
    severity = Column(String(30), nullable=False, default="warning")
    explanation = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)
    suggested_action = Column(JSON, nullable=True)
    requires_human_review = Column(Boolean, nullable=False, default=True)

    provider = Column(String(40), nullable=False, default="rules")
    # pending | accepted | rejected | edited
    status = Column(String(20), nullable=False, default="pending", index=True)
    human_decision_note = Column(Text, nullable=True)
    decided_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    decided_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=utcnow_callable, nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    decided_by = relationship("User", foreign_keys=[decided_by_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    job = relationship("AiClaimVettingJob", back_populates="findings")


class AiClaimVettingRule(Base):
    """Facility-owned configurable vetting rule (manager CRUD)."""

    __tablename__ = "ai_claim_vetting_rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_code = Column(String(64), nullable=False, unique=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True, index=True)
    severity = Column(String(30), nullable=False, default="warning")
    priority = Column(Integer, nullable=False, default=100)
    analysis_modes = Column(JSON, nullable=True)  # ["phase1","coding","thorough"]
    applies_to = Column(String(30), nullable=False, default="ghims_import")
    is_system = Column(Boolean, nullable=False, default=False)  # seeded; can disable, limited edit
    condition = Column("condition", JSON, nullable=False)  # reserved word in MySQL — explicit name
    suggested_action = Column(JSON, nullable=True)
    finding_template = Column(String(500), nullable=True)
    recommendation_template = Column(Text, nullable=True)
    requires_human_review = Column(Boolean, nullable=False, default=True)

    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow_callable, nullable=False)
    updated_at = Column(DateTime, default=utcnow_callable, onupdate=utcnow_callable, nullable=True)

    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])
