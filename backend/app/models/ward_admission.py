"""
Ward Admission model - tracks patients currently admitted to wards
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class WardAdmission(Base):
    """Stores active ward admissions - patients currently in wards"""
    __tablename__ = "ward_admissions"

    id = Column(Integer, primary_key=True, index=True)
    admission_recommendation_id = Column(Integer, ForeignKey("admission_recommendations.id"), nullable=False, unique=True)
    encounter_id = Column(Integer, ForeignKey("encounters.id"), nullable=False, unique=True)
    ward = Column(String(100), nullable=False)
    bed_id = Column(Integer, ForeignKey("beds.id"), nullable=True)  # Bed assigned to patient
    ccc_number = Column(String(50), nullable=True)  # CCC number for this admission
    emergency_contact_name = Column(String(255), nullable=True)
    emergency_contact_relationship = Column(String(100), nullable=True)
    emergency_contact_number = Column(String(100), nullable=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Doctor under whose care
    admitted_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # User who confirmed admission
    admission_notes = Column(Text, nullable=True)  # Admission notes
    admitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    death_recorded_at = Column(DateTime, nullable=True)  # When patient death was recorded
    death_recorded_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # User who recorded death
    discharged_at = Column(DateTime, nullable=True)  # When patient was discharged
    discharged_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # User who discharged
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    encounter = relationship("Encounter")
    admission_recommendation = relationship("AdmissionRecommendation")
    bed = relationship("Bed")
    doctor = relationship("User", foreign_keys=[doctor_id])
    nurse_notes = relationship("NurseNote", back_populates="ward_admission", cascade="all, delete-orphan")
    nurse_mid_documentations = relationship("NurseMidDocumentation", back_populates="ward_admission", cascade="all, delete-orphan")
    inpatient_vitals = relationship("InpatientVital", back_populates="ward_admission", cascade="all, delete-orphan")
    clinical_reviews = relationship("InpatientClinicalReview", back_populates="ward_admission", cascade="all, delete-orphan")
    transfers = relationship("WardTransfer", back_populates="ward_admission", cascade="all, delete-orphan")
    surgeries = relationship("InpatientSurgery", back_populates="ward_admission", cascade="all, delete-orphan")
    additional_services = relationship("InpatientAdditionalService", back_populates="ward_admission", cascade="all, delete-orphan")
    inventory_debits = relationship("InpatientInventoryDebit", back_populates="ward_admission", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<WardAdmission {self.encounter_id} - {self.ward}>"

