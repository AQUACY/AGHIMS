"""
GHIMS XML import batches and claim rows.
Tracks uploaded XML files and the claim IDs extracted for officer review.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class ClaimXmlImportBatch(Base):
    """One uploaded GHIMS XML file."""
    __tablename__ = "claim_xml_import_batches"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime, default=utcnow_callable)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    claim_count = Column(Integer, default=0)
    # Saved demarcation plan (list of rules) so managers can reopen and edit
    demarcation_rules = Column(JSON, nullable=True)

    items = relationship("ClaimXmlImportItem", back_populates="batch", cascade="all, delete-orphan")


class ClaimXmlImportItem(Base):
    """One claim row extracted from imported XML."""
    __tablename__ = "claim_xml_import_items"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("claim_xml_import_batches.id"), nullable=False, index=True)
    claim_claim_id = Column(String(50), nullable=False, index=True)  # CLA-XXXXX from XML
    row_index = Column(Integer, nullable=True)
    status = Column(String(30), nullable=False, default="draft")  # draft | flagged | pharmacy_vetted | doctor_vetted | vetted | ai_vetted | finalized | merged
    payload = Column(JSON, nullable=False)  # editable claim payload parsed from XML
    member_no = Column(String(100), nullable=True, index=True)  # denormalized from payload.memberNo
    merged_into_id = Column(Integer, ForeignKey("claim_xml_import_items.id"), nullable=True, index=True)
    finalized_at = Column(DateTime, nullable=True)
    flag_comment = Column(String(800), nullable=True)

    # Clinical/pharmacy checkpoints before claims-manager finalize
    pharmacy_vetted_at = Column(DateTime, nullable=True)
    pharmacy_vetted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    doctor_vetted_at = Column(DateTime, nullable=True)
    doctor_vetted_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Ownership / demarcation (workload signal only — does not restrict who can vet)
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    assigned_at = Column(DateTime, nullable=True)
    assigned_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assignment_note = Column(String(255), nullable=True)  # e.g. "OPD", "ANC", "Pedis OPD + IPD"

    batch = relationship("ClaimXmlImportBatch", back_populates="items")
