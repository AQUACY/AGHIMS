"""
Requisition Item model - tracks individual items in a pharmacy requisition
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class RequisitionItem(Base):
    """Individual items in a pharmacy requisition"""
    __tablename__ = "requisition_items"
    
    id = Column(Integer, primary_key=True, index=True)
    requisition_id = Column(Integer, ForeignKey("pharmacy_requisitions.id"), nullable=False, index=True)
    product_code = Column(String(50), nullable=False, index=True)
    product_name = Column(String(500), nullable=False)
    requested_quantity = Column(Float, nullable=False)  # Quantity requested by ward
    fulfilled_quantity = Column(Float, nullable=False, default=0.0)  # Quantity fulfilled by store manager
    unit_price = Column(Float, nullable=True)  # Price per unit (for reference)
    notes = Column(Text, nullable=True)  # Item-specific notes
    
    created_at = Column(DateTime, default=utcnow_callable, nullable=False)
    updated_at = Column(DateTime, default=utcnow_callable, onupdate=utcnow_callable, nullable=False)
    
    # Relationships
    requisition = relationship("PharmacyRequisition", back_populates="items")
    
    def __repr__(self):
        return f"<RequisitionItem {self.product_name} - Req: {self.requested_quantity}, Fulfilled: {self.fulfilled_quantity}>"

