"""
Blood Transfusion Type model - stores admin-defined blood transfusion types
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class BloodTransfusionType(Base):
    """Admin-defined blood transfusion types (e.g., Packed Cells, Whole Blood, etc.)"""
    __tablename__ = "blood_transfusion_types"
    
    id = Column(Integer, primary_key=True, index=True)
    type_name = Column(String(255), nullable=False, unique=True)  # e.g., "Packed Cells", "Whole Blood"
    description = Column(Text, nullable=True)  # Optional description
    unit_price = Column(Float, nullable=False)  # Price per unit
    unit_type = Column(String(50), nullable=False, default="unit")  # "unit", "pack", etc.
    is_active = Column(Boolean, default=True)  # Whether type is available
    created_by = Column(Integer, nullable=False)  # Admin who created it
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    requests = relationship("BloodTransfusionRequest", back_populates="transfusion_type")
    
    def __repr__(self):
        return f"<BloodTransfusionType {self.type_name} - {self.unit_price}/{self.unit_type}>"

