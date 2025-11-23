"""
Inpatient Surgery model - stores surgeries performed on IPD patients
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class InpatientSurgery(Base):
    """Surgery model for inpatient ward admissions"""
    __tablename__ = "inpatient_surgeries"
    
    id = Column(Integer, primary_key=True, index=True)
    ward_admission_id = Column(Integer, ForeignKey("ward_admissions.id"), nullable=False)
    encounter_id = Column(Integer, ForeignKey("encounters.id"), nullable=False)
    g_drg_code = Column(String(50), nullable=True)  # G-DRG code for surgery
    surgery_name = Column(String(500), nullable=False)  # Name/description of surgery
    surgery_type = Column(String(100), nullable=True)  # Type/category of surgery
    surgeon_name = Column(String(255), nullable=True)  # Name of surgeon
    assistant_surgeon = Column(String(255), nullable=True)  # Assistant surgeon name
    anesthesia_type = Column(String(100), nullable=True)  # Type of anesthesia used
    surgery_date = Column(DateTime, nullable=True)  # Scheduled/performed date
    surgery_notes = Column(Text, nullable=True)  # Pre-operative notes
    operative_notes = Column(Text, nullable=True)  # Operative notes
    post_operative_notes = Column(Text, nullable=True)  # Post-operative notes
    complications = Column(Text, nullable=True)  # Any complications
    is_completed = Column(Boolean, default=False)  # Whether surgery is completed
    completed_at = Column(DateTime, nullable=True)  # When surgery was completed
    completed_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Doctor who completed
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utcnow_callable)
    updated_at = Column(DateTime, default=utcnow_callable, onupdate=utcnow_callable)
    
    # Relationships
    ward_admission = relationship("WardAdmission", back_populates="surgeries")
    encounter = relationship("Encounter")
    
    def __repr__(self):
        return f"<InpatientSurgery {self.id} - {self.surgery_name[:30]}>"

