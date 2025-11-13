"""
Additional Service model - stores admin-defined additional services for IPD
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class AdditionalService(Base):
    """Admin-defined additional services (e.g., Oxygen, Private Room, etc.)"""
    __tablename__ = "additional_services"
    
    id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String(255), nullable=False, unique=True)  # e.g., "Oxygen - Adult"
    description = Column(Text, nullable=True)  # Optional description
    price_per_unit = Column(Float, nullable=False)  # Price per hour/unit
    unit_type = Column(String(50), nullable=False, default="hour")  # "hour", "day", "unit"
    is_active = Column(Boolean, default=True)  # Whether service is available
    created_by = Column(Integer, nullable=False)  # Admin who created it
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patient_services = relationship("InpatientAdditionalService", back_populates="service")
    
    def __repr__(self):
        return f"<AdditionalService {self.service_name} - {self.price_per_unit}/{self.unit_type}>"

