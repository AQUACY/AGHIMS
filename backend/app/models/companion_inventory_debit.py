"""
Companion inventory debit — stock issued against a copayment visit without an internal encounter.
Department is chosen at entry. Optional charge to client creates a CompanionVisitItem (inventory_debit).
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class CompanionInventoryDebit(Base):
    __tablename__ = "companion_inventory_debits"

    id = Column(Integer, primary_key=True, index=True)
    companion_visit_id = Column(Integer, ForeignKey("companion_visits.id", ondelete="CASCADE"), nullable=False, index=True)
    requesting_department = Column(String(200), nullable=False)
    product_code = Column(String(50), nullable=False)
    product_name = Column(String(500), nullable=False)
    quantity = Column(Float, nullable=False, default=1.0)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    notes = Column(Text, nullable=True)
    recorded_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utcnow_callable)

    is_released = Column(Boolean, default=False, nullable=False)
    released_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    released_at = Column(DateTime, nullable=True)

    charged_to_client = Column(Boolean, default=False, nullable=False)
    companion_visit_item_id = Column(Integer, ForeignKey("companion_visit_items.id", ondelete="SET NULL"), nullable=True)
    charged_at = Column(DateTime, nullable=True)

    visit = relationship("CompanionVisit", backref="inventory_debits")
    recorded_by = relationship("User", foreign_keys=[recorded_by_id])
    released_by = relationship("User", foreign_keys=[released_by_id])
    bill_line = relationship("CompanionVisitItem", foreign_keys=[companion_visit_item_id])

    def __repr__(self):
        return f"<CompanionInventoryDebit {self.product_code} qty={self.quantity}>"
