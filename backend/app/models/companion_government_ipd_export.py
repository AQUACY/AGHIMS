"""
Saved government IPD (in-patient) invoice snapshot for a Companion visit.

Purpose:
- Billing uploads the IPD invoice once (or re-imports when GHIMS data changes).
- System stores the parsed line-items + metadata tied to the visit.
- Reconcile and add-missing reuse the saved snapshot.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, UniqueConstraint
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class CompanionGovernmentIpdExport(Base):
    __tablename__ = "companion_government_ipd_exports"

    id = Column(Integer, primary_key=True, index=True)
    companion_visit_id = Column(
        Integer,
        ForeignKey("companion_visits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Identity / meta from IPD invoice
    invoice_no = Column(String(50), nullable=True, index=True)
    admission_no = Column(String(50), nullable=True, index=True)
    visit_no = Column(String(50), nullable=True)
    patient_no = Column(String(50), nullable=True, index=True)
    patient_name = Column(String(255), nullable=True)
    invoice_date = Column(String(50), nullable=True)
    admission_date = Column(String(50), nullable=True)
    discharge_date = Column(String(50), nullable=True)
    insurance_no = Column(String(50), nullable=True)
    billing_info = Column(String(255), nullable=True)

    file_sha256 = Column(String(64), nullable=False)
    lines_json = Column(Text, nullable=False)  # JSON [{description, quantity, unit, total}]

    imported_at = Column(DateTime, default=utcnow_callable, nullable=False)
    imported_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        UniqueConstraint("companion_visit_id", name="uq_companion_visit_gov_ipd_export"),
    )
