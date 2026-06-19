"""GHIMS XML import batches and claim rows."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class ClaimXmlImportBatch(Base):
    __tablename__ = "claim_xml_import_batches"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime, default=utcnow_callable)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    claim_count = Column(Integer, default=0)

    items = relationship("ClaimXmlImportItem", back_populates="batch", cascade="all, delete-orphan")


class ClaimXmlImportItem(Base):
    __tablename__ = "claim_xml_import_items"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("claim_xml_import_batches.id"), nullable=False, index=True)
    claim_claim_id = Column(String(50), nullable=False, index=True)
    row_index = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False, default="draft")
    payload = Column(JSON, nullable=False)
    finalized_at = Column(DateTime, nullable=True)
    flag_comment = Column(String(800), nullable=True)

    batch = relationship("ClaimXmlImportBatch", back_populates="items")
