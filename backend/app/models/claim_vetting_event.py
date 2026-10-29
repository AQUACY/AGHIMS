"""Per-claim vetting audit trail (XML import and GHIMS monthly rows)."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class ClaimVettingEvent(Base):
    """One action a person (or AI) took on a GHIMS imported / monthly claim."""

    __tablename__ = "claim_vetting_events"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("claim_xml_import_items.id"), nullable=False, index=True)
    batch_id = Column(Integer, nullable=True, index=True)
    claim_claim_id = Column(String(50), nullable=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    username = Column(String(100), nullable=True, index=True)
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), nullable=True, index=True)

    # imported | updated | pharmacy_vetted | pharmacy_vet_reverted | doctor_vetted |
    # doctor_vet_reverted | finalized | reopened | flagged | assigned | unassigned |
    # merged | merge_reverted | ai_applied | ai_vetted | ghims_synced
    action = Column(String(50), nullable=False, index=True)
    summary = Column(Text, nullable=True)
    changes = Column(JSON, nullable=True)  # itemized [{section, item_label, field, field_label, old, new, kind}]
    details = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=utcnow_callable, nullable=False, index=True)

    user = relationship("User", foreign_keys=[user_id])
    item = relationship("ClaimXmlImportItem", foreign_keys=[item_id])
