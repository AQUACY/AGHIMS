"""
Line items (bill items) for a companion visit.
Lab, scan, xray, drugs added for copayment billing.

Items are never truly removed by normal users; they are cancelled (strike-through) with reason,
who cancelled, and when. Only the ghost superadmin hard-deletes.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class CompanionVisitItem(Base):
    """A single line item on a companion visit (e.g. lab investigation, drug)."""
    __tablename__ = "companion_visit_items"

    id = Column(Integer, primary_key=True, index=True)
    companion_visit_id = Column(Integer, ForeignKey("companion_visits.id", ondelete="CASCADE"), nullable=False, index=True)
    item_code = Column(String(50), nullable=False)  # e.g. g_drg_code
    item_name = Column(String(500), nullable=False)
    category = Column(String(30), nullable=False)  # lab, scan, xray, drug
    unit_price = Column(Float, nullable=False)  # copayment amount (e.g. per hour for oxygen)
    quantity = Column(Float, default=1.0, nullable=False)  # e.g. hours for oxygen
    start_time = Column(DateTime, nullable=True)  # for time-based services (e.g. oxygen)
    end_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow_callable)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    cancelled = Column(Boolean, default=False, nullable=False, index=True)
    cancelled_at = Column(DateTime, nullable=True)
    cancelled_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    cancel_reason = Column(Text, nullable=True)
    receipt_number = Column(String(50), nullable=True)  # set when this line is paid; prevents delete
    paid_at = Column(DateTime, nullable=True)
    # Who received the payment and how (for Management reporting)
    paid_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    payment_method = Column(String(50), nullable=True)  # cash, card, mobile_money, etc.

    def __repr__(self):
        return f"<CompanionVisitItem {self.item_code} - {self.item_name}>"
