"""
Inpatient Inventory Debit model - tracks products/consumables used for ward admissions
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class InpatientInventoryDebit(Base):
    """Tracks products/consumables used for inpatients (e.g., gloves, gauze, infusion sets)"""
    __tablename__ = "inpatient_inventory_debits"
    
    id = Column(Integer, primary_key=True, index=True)
    ward_admission_id = Column(Integer, ForeignKey("ward_admissions.id"), nullable=False)
    encounter_id = Column(Integer, ForeignKey("encounters.id"), nullable=False)
    product_code = Column(String(50), nullable=False)  # Product/medication code
    product_name = Column(String(500), nullable=False)  # Product name
    quantity = Column(Float, nullable=False, default=1.0)  # Quantity used
    unit_price = Column(Float, nullable=False)  # Price per unit at time of use
    total_price = Column(Float, nullable=False)  # Total cost
    notes = Column(Text, nullable=True)  # Optional notes
    is_billed = Column(Boolean, default=False)  # Whether added to bill
    bill_item_id = Column(Integer, nullable=True)  # Reference to bill item if billed
    is_released = Column(Boolean, default=False)  # Whether pharmacy has released the inventory
    released_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # User who released the inventory
    released_at = Column(DateTime, nullable=True)  # When inventory was released
    used_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # User who recorded the usage
    used_at = Column(DateTime, default=datetime.utcnow, nullable=False)  # When product was used
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    ward_admission = relationship("WardAdmission", back_populates="inventory_debits")
    encounter = relationship("Encounter")
    user = relationship("User", foreign_keys=[used_by])
    
    def __repr__(self):
        return f"<InpatientInventoryDebit {self.product_name} - Qty: {self.quantity}>"

