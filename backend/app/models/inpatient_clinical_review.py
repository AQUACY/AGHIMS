"""
Inpatient Clinical Review model - stores clinical reviews (consultations) for ward admissions
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class InpatientClinicalReview(Base):
    """Stores clinical reviews for ward admissions - serves as consultation for inpatients"""
    __tablename__ = "inpatient_clinical_reviews"

    id = Column(Integer, primary_key=True, index=True)
    ward_admission_id = Column(Integer, ForeignKey("ward_admissions.id"), nullable=False)
    review_notes = Column(Text, nullable=True)  # General review notes
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # Doctor/PA who reviewed
    reviewed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    ward_admission = relationship("WardAdmission", back_populates="clinical_reviews")
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    # Diagnoses, investigations, and prescriptions will be linked via foreign keys when those models are created
    # diagnoses = relationship("InpatientDiagnosis", back_populates="clinical_review", cascade="all, delete-orphan")
    # investigations = relationship("InpatientInvestigation", back_populates="clinical_review", cascade="all, delete-orphan")
    # prescriptions = relationship("InpatientPrescription", back_populates="clinical_review", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<InpatientClinicalReview {self.id} - WardAdmission {self.ward_admission_id}>"

