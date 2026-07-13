"""
Saved government OPD export snapshot for a Companion visit.

Purpose:
- Billing uploads the gov export once.
- System stores the parsed line-items + metadata tied to the visit identifiers.
- Later checks reuse the saved snapshot without requiring re-upload (reduces mistakes).
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, UniqueConstraint
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class CompanionGovernmentOpdExport(Base):
    __tablename__ = "companion_government_opd_exports"

    id = Column(Integer, primary_key=True, index=True)
    companion_visit_id = Column(
        Integer,
        ForeignKey("companion_visits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Identity fields from gov export
    claim_no = Column(String(50), nullable=False, index=True)
    patient_no = Column(String(50), nullable=False, index=True)

    # Metadata for display
    claim_status = Column(String(50), nullable=True)
    insurance_no = Column(String(50), nullable=True)
    patient_name = Column(String(255), nullable=True)
    service_date = Column(String(50), nullable=True)
    service_type = Column(String(50), nullable=True)

    # Stored parsed lines + hash of raw upload to detect changes
    file_sha256 = Column(String(64), nullable=False)
    lines_json = Column(Text, nullable=False)  # JSON string of [{description, quantity, unit, total}]

    imported_at = Column(DateTime, default=utcnow_callable, nullable=False)
    imported_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        UniqueConstraint("companion_visit_id", name="uq_companion_visit_gov_opd_export"),
    )

