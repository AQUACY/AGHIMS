"""
ClaimIT import report batch and error records.
Stores uploaded report batches and which claims had errors/warnings so officers can correct and re-export.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class ClaimItReportBatch(Base):
    """A single uploaded ClaimIT import report (HTML)."""
    __tablename__ = "claimit_report_batches"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=True)  # Optional label, e.g. "Mar 2026 import"
    file_name = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime, default=utcnow_callable)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    # Summary from report overview: { "total", "passed", "warning", "failed", "report_date", "claim_months": [...] }
    summary = Column(JSON, nullable=True)
    # Count of claims with errors/warnings in this batch (for display)
    error_count = Column(Integer, default=0)

    errors = relationship("ClaimItReportError", back_populates="batch", cascade="all, delete-orphan")


class ClaimItReportError(Base):
    """One claim that had ERROR or WARNING in a ClaimIT report."""
    __tablename__ = "claimit_report_errors"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("claimit_report_batches.id"), nullable=False)
    claim_claim_id = Column(String(50), nullable=False, index=True)  # CLA-XXXXX from report
    outcome = Column(String(20), nullable=False)  # ERROR, WARNING
    # List of error/warning messages from report (e.g. ["Member No. must be provided"])
    error_messages = Column(JSON, nullable=False)  # ["msg1", "msg2"]
    row_index = Column(Integer, nullable=True)  # Row number in report table
    completed_at = Column(DateTime, nullable=True)
    completed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    batch = relationship("ClaimItReportBatch", back_populates="errors")
