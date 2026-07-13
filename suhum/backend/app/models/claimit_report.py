"""
ClaimIT import report batch and error records for Suhum GHIMS workflow.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class ClaimItReportBatch(Base):
    __tablename__ = "claimit_report_batches"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=True)
    file_name = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime, default=utcnow_callable)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    summary = Column(JSON, nullable=True)
    error_count = Column(Integer, default=0)
    ghims_import_batch_id = Column(Integer, ForeignKey("claim_xml_import_batches.id"), nullable=True, index=True)

    errors = relationship("ClaimItReportError", back_populates="batch", cascade="all, delete-orphan")


class ClaimItReportError(Base):
    __tablename__ = "claimit_report_errors"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("claimit_report_batches.id"), nullable=False)
    claim_claim_id = Column(String(50), nullable=False, index=True)
    outcome = Column(String(20), nullable=False)
    error_messages = Column(JSON, nullable=False)
    row_index = Column(Integer, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    completed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    ghims_import_item_id = Column(Integer, ForeignKey("claim_xml_import_items.id"), nullable=True, index=True)

    batch = relationship("ClaimItReportBatch", back_populates="errors")
