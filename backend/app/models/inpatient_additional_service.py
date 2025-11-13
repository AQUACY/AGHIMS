"""
Inpatient Additional Service model - tracks additional services used by IPD patients
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class InpatientAdditionalService(Base):
    """Tracks additional services used by admitted patients"""
    __tablename__ = "inpatient_additional_services"
    
    id = Column(Integer, primary_key=True, index=True)
    ward_admission_id = Column(Integer, ForeignKey("ward_admissions.id"), nullable=False)
    encounter_id = Column(Integer, ForeignKey("encounters.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("additional_services.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)  # When service started
    end_time = Column(DateTime, nullable=True)  # When service stopped (null if still active)
    units_used = Column(Float, nullable=True)  # Calculated units (hours, days, etc.)
    total_cost = Column(Float, nullable=True)  # Calculated total cost
    is_billed = Column(Boolean, default=False)  # Whether this has been added to bill
    bill_item_id = Column(Integer, nullable=True)  # Reference to bill item if billed
    notes = Column(Text, nullable=True)  # Optional notes
    started_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    stopped_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    ward_admission = relationship("WardAdmission", back_populates="additional_services")
    encounter = relationship("Encounter")
    service = relationship("AdditionalService", back_populates="patient_services")
    starter = relationship("User", foreign_keys=[started_by])
    stopper = relationship("User", foreign_keys=[stopped_by])
    
    def __repr__(self):
        status = "Active" if self.end_time is None else "Stopped"
        return f"<InpatientAdditionalService {self.id} - {status}>"

