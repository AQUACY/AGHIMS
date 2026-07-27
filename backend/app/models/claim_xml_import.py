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

    items = relationship("ClaimXmlImportItem", back_populates="batch", cascade="all, delete-orphan")


class ClaimXmlImportItem(Base):
    """One claim row extracted from imported XML."""
    __tablename__ = "claim_xml_import_items"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("claim_xml_import_batches.id"), nullable=False, index=True)
    claim_claim_id = Column(String(50), nullable=False, index=True)  # CLA-XXXXX from XML
    row_index = Column(Integer, nullable=True)
    status = Column(String(30), nullable=False, default="draft")  # draft | flagged | pharmacy_vetted | doctor_vetted | vetted | finalized
    payload = Column(JSON, nullable=False)  # editable claim payload parsed from XML
    finalized_at = Column(DateTime, nullable=True)
    flag_comment = Column(String(800), nullable=True)

    # Clinical/pharmacy checkpoints before claims-manager finalize
    pharmacy_vetted_at = Column(DateTime, nullable=True)
    pharmacy_vetted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    doctor_vetted_at = Column(DateTime, nullable=True)
    doctor_vetted_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    batch = relationship("ClaimXmlImportBatch", back_populates="items")
