"""
Prescription model
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class Prescription(Base):
    """Prescription model"""
    __tablename__ = "prescriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    encounter_id = Column(Integer, ForeignKey("encounters.id"), nullable=False)
    medicine_code = Column(String(50), nullable=False)  # Medicine/item code
    medicine_name = Column(String(500), nullable=False)
    dose = Column(String(100))  # e.g., "500"
    unit = Column(String(50), nullable=True)  # e.g., "MG", "ML", "TAB"
    frequency = Column(String(100))  # e.g., "BDS", "TDS", "OD"
    frequency_value = Column(Integer, nullable=True)  # Numeric value for frequency (e.g., 2 for BDS)
    duration = Column(String(100))  # e.g., "7 DAYS"
    instructions = Column(Text, nullable=True)  # Instructions for the drug
    quantity = Column(Integer, nullable=False)  # Dispensed quantity (auto-calculated: dose * frequency_value * duration)
    unparsed = Column(Text)  # Original prescription text
    prescribed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    confirmed_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Doctor who confirmed the prescription
    dispensed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    confirmed_at = Column(DateTime, nullable=True)  # When prescription was confirmed
    service_date = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    encounter = relationship("Encounter", back_populates="prescriptions")
    
    def __repr__(self):
        return f"<Prescription {self.medicine_code} - Qty: {self.quantity}>"

