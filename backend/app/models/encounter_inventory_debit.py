"""
Encounter Inventory Debit model - tracks products/consumables used for OPD encounters
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class EncounterInventoryDebit(Base):
    """Tracks products/consumables used for OPD encounters (e.g., Malaria RDT, UPT kits)"""
    __tablename__ = "encounter_inventory_debits"
    
    id = Column(Integer, primary_key=True, index=True)
    encounter_id = Column(Integer, ForeignKey("encounters.id"), nullable=False)
    department = Column(String(100), nullable=False)  # Department/ward name from encounter
    product_code = Column(String(50), nullable=False)  # Product/medication code
    product_name = Column(String(500), nullable=False)  # Product name
    quantity = Column(Float, nullable=False, default=1.0)  # Quantity used
    unit_price = Column(Float, nullable=False)  # Price per unit at time of use
    total_price = Column(Float, nullable=False)  # Total cost
    notes = Column(Text, nullable=True)  # Optional notes
    is_billed = Column(Boolean, default=False)  # Whether added to bill
    bill_item_id = Column(Integer, nullable=True)  # Reference to bill item if billed
    used_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # User who recorded the usage
    used_at = Column(DateTime, default=utcnow_callable, nullable=False)  # When product was used
    created_at = Column(DateTime, default=utcnow_callable)
    updated_at = Column(DateTime, default=utcnow_callable, onupdate=utcnow_callable)
    
    # Relationships
    encounter = relationship("Encounter")
    user = relationship("User", foreign_keys=[used_by])
    
    def __repr__(self):
        return f"<EncounterInventoryDebit {self.product_name} - Qty: {self.quantity}>"

