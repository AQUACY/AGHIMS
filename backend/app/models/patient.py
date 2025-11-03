"""
Patient model
"""
from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class Patient(Base):
    """Patient/Client model"""
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    surname = Column(String(255))
    other_names = Column(String(255))
    gender = Column(String(10), nullable=False)  # M, F
    age = Column(Integer)
    date_of_birth = Column(Date)
    card_number = Column(String(50), unique=True, index=True, nullable=False)  # Format: ER-A25-AAA0001
    insured = Column(Boolean, default=False)
    insurance_id = Column(String(100), nullable=True)  # NHIS member number
    insurance_start_date = Column(Date, nullable=True)
    insurance_end_date = Column(Date, nullable=True)
    ccc_number = Column(String(50), nullable=True)  # 5-digit CCC number
    contact = Column(String(100))
    address = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    encounters = relationship("Encounter", back_populates="patient", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Patient {self.card_number} - {self.name}>"

