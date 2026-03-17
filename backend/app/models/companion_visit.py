"""
Companion (copayment) visit model.

Tracks service requests that originate from the external government system.
Client identity is by external_card_number and external_visit_number only;
no internal patient_id or encounter_id is used.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class CompanionVisit(Base):
    """
    A visit/service record in Companion mode, keyed by external system identifiers.
    Created by Records when they receive card number + visit number from the government system.
    """
    __tablename__ = "companion_visits"

    id = Column(Integer, primary_key=True, index=True)
    external_card_number = Column(String(50), nullable=False, index=True)
    external_visit_number = Column(String(50), nullable=False, index=True)
    client_name = Column(String(255), nullable=True)  # Optional display name from Records
    status = Column(String(20), default="open", nullable=False)  # open | closed
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utcnow_callable)
    updated_at = Column(DateTime, default=utcnow_callable, onupdate=utcnow_callable)

    # Close audit
    closed_at = Column(DateTime, nullable=True)
    closed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Reopen audit (only Admin can reopen; reason required)
    reopened_at = Column(DateTime, nullable=True)
    reopened_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reopen_reason = Column(Text, nullable=True)

    # Undertaking: client agreement to pay later; Management approves; deposit solidifies agreement
    undertaking_status = Column(String(20), nullable=True)  # null | pending | approved | rejected
    undertaking_deposit_amount = Column(Float, nullable=True)  # amount client deposited (may not map to items)
    undertaking_deposit_receipt_number = Column(String(50), nullable=True)
    undertaking_requested_at = Column(DateTime, nullable=True)
    undertaking_requested_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    undertaking_approved_at = Column(DateTime, nullable=True)
    undertaking_approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    undertaking_unapproved_at = Column(DateTime, nullable=True)
    undertaking_unapproved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    undertaking_unapprove_reason = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "external_card_number",
            "external_visit_number",
            name="uq_companion_visit_card_visit",
        ),
    )

    def __repr__(self):
        return f"<CompanionVisit {self.external_card_number}/{self.external_visit_number} - {self.status}>"
