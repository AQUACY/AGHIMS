"""
Bed model - manages beds in wards
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class Bed(Base):
    """Stores bed information for wards"""
    __tablename__ = "beds"

    id = Column(Integer, primary_key=True, index=True)
    ward = Column(String(100), nullable=False)
    bed_number = Column(String(50), nullable=False)  # e.g., "Bed 1", "A1", "101"
    is_occupied = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)  # For soft delete
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Bed {self.bed_number} - {self.ward}>"

