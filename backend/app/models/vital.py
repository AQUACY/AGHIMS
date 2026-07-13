"""
Vitals model
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class Vital(Base):
    """Patient vitals model"""
    __tablename__ = "vitals"
    
    id = Column(Integer, primary_key=True, index=True)
    encounter_id = Column(Integer, ForeignKey("encounters.id"), unique=True, nullable=False)
    bp = Column(String(50))  # Blood pressure (e.g., "120/80")
    temperature = Column(Float)  # Temperature in Celsius
    pulse = Column(Integer)  # Pulse rate
    respiration = Column(Integer)  # Respiration rate
    weight = Column(Float)  # Weight in kg
    height = Column(Float)  # Height in cm
    bmi = Column(Float)  # Body Mass Index
    spo2 = Column(Integer)  # Oxygen saturation percentage
    rbs = Column(Float)  # Random Blood Sugar (mmol/L)
    fbs = Column(Float)  # Fasting Blood Sugar (mmol/L)
    upt = Column(String(50))  # Urine Pregnancy Test result
    rdt_malaria = Column(String(50))  # Malaria RDT result
    retro_rdt = Column(String(50))  # Retro RDT result
    remarks = Column(Text)
    recorded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    recorded_at = Column(DateTime, default=utcnow_callable)
    
    # Relationships
    encounter = relationship("Encounter", back_populates="vitals")
    
    def __repr__(self):
        return f"<Vital for Encounter {self.encounter_id}>"

