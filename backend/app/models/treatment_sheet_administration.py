"""
Treatment Sheet Administration model - tracks when medications are given to patients
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Date, Time
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class TreatmentSheetAdministration(Base):
    """Tracks medication administration for treatment sheet"""
    __tablename__ = "treatment_sheet_administrations"
    
    id = Column(Integer, primary_key=True, index=True)
    ward_admission_id = Column(Integer, ForeignKey("ward_admissions.id"), nullable=False)
    prescription_id = Column(Integer, nullable=False)  # Can be inpatient_prescription.id or prescription.id
    prescription_type = Column(String(20), nullable=False, default="inpatient")  # "inpatient" or "opd"
    administration_date = Column(Date, nullable=False)
    administration_time = Column(Time, nullable=False)
    given_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    signature = Column(String(500), nullable=True)  # Digital signature or initials
    notes = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=utcnow_callable)
    
    # Relationships
    ward_admission = relationship("WardAdmission")
    giver = relationship("User", foreign_keys=[given_by])
    
    def __repr__(self):
        return f"<TreatmentSheetAdministration {self.id} - Prescription {self.prescription_id} ({self.prescription_type})>"

