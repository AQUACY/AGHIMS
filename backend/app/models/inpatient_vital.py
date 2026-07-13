"""
Inpatient Vital model - stores vitals for ward admissions
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class InpatientVital(Base):
    """Stores vitals for ward admissions"""
    __tablename__ = "inpatient_vitals"

    id = Column(Integer, primary_key=True, index=True)
    ward_admission_id = Column(Integer, ForeignKey("ward_admissions.id"), nullable=False)
    temperature = Column(Float, nullable=True)
    blood_pressure_systolic = Column(Integer, nullable=True)
    blood_pressure_diastolic = Column(Integer, nullable=True)
    pulse = Column(Integer, nullable=True)
    respiratory_rate = Column(Integer, nullable=True)
    oxygen_saturation = Column(Float, nullable=True)
    weight = Column(Float, nullable=True)
    height = Column(Float, nullable=True)
    bmi = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    recorded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    recorded_at = Column(DateTime, default=utcnow_callable, nullable=False)
    created_at = Column(DateTime, default=utcnow_callable)
    updated_at = Column(DateTime, default=utcnow_callable, onupdate=utcnow_callable)

    # Relationships
    ward_admission = relationship("WardAdmission", back_populates="inpatient_vitals")
    recorder = relationship("User", foreign_keys=[recorded_by])

    def __repr__(self):
        return f"<InpatientVital {self.id} - WardAdmission {self.ward_admission_id}>"

