"""
Requisition History model - audit trail for requisition status changes
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable
import enum


class HistoryAction(str, enum.Enum):
    """History action types"""
    CREATED = "created"
    UPDATED = "updated"
    APPROVED = "approved"
    REJECTED = "rejected"
    FULFILLED = "fulfilled"
    PARTIALLY_FULFILLED = "partially_fulfilled"
    CANCELLED = "cancelled"
    ITEM_FULFILLED = "item_fulfilled"  # Individual item fulfillment


class RequisitionHistory(Base):
    """Audit trail for requisition status changes and actions"""
    __tablename__ = "requisition_history"
    
    id = Column(Integer, primary_key=True, index=True)
    requisition_id = Column(Integer, ForeignKey("pharmacy_requisitions.id"), nullable=False, index=True)
    action = Column(SQLEnum(HistoryAction), nullable=False, index=True)
    performed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    notes = Column(Text, nullable=True)  # Additional notes about the action
    timestamp = Column(DateTime, default=utcnow_callable, nullable=False, index=True)
    
    # For item-specific actions
    item_id = Column(Integer, ForeignKey("requisition_items.id"), nullable=True)  # If action is on specific item
    quantity_fulfilled = Column(Float, nullable=True)  # Quantity fulfilled if action is fulfillment
    
    # Relationships
    requisition = relationship("PharmacyRequisition", back_populates="history")
    user = relationship("User", foreign_keys=[performed_by])
    item = relationship("RequisitionItem", foreign_keys=[item_id])
    
    def __repr__(self):
        return f"<RequisitionHistory {self.requisition_id} - {self.action} by {self.performed_by}>"

