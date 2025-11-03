"""
Encounter model
"""
from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Text, Enum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base


class EncounterStatus(str, enum.Enum):
    """Encounter status enumeration"""
    DRAFT = "draft"
    IN_CONSULTATION = "in_consultation"
    AWAITING_SERVICES = "awaiting_services"
    FINALIZED = "finalized"


class Department(str, enum.Enum):
    """Department enumeration"""
    GENERAL = "General"
    PEDIATRICS = "Pediatrics"
    ENT = "ENT"
    EYE = "Eye"
    EMERGENCY = "Emergency"


class Encounter(Base):
    """Patient encounter model"""
    __tablename__ = "encounters"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    ccc_number = Column(String(50), nullable=True)  # CCC number for this encounter
    status = Column(String(50), default=EncounterStatus.DRAFT.value, nullable=False)
    department = Column(String(100), nullable=False)  # Service Type (Department/Clinic) from procedures
    procedure_g_drg_code = Column(String(50), nullable=True)  # G-DRG code of selected procedure
    procedure_name = Column(String(500), nullable=True)  # Service Name of selected procedure
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    finalized_at = Column(DateTime, nullable=True)
    archived = Column(Boolean, default=False, nullable=False)  # Soft delete flag
    
    # Relationships
    patient = relationship("Patient", back_populates="encounters")
    vitals = relationship("Vital", back_populates="encounter", uselist=False, cascade="all, delete-orphan")
    diagnoses = relationship("Diagnosis", back_populates="encounter", cascade="all, delete-orphan")
    prescriptions = relationship("Prescription", back_populates="encounter", cascade="all, delete-orphan")
    investigations = relationship("Investigation", back_populates="encounter", cascade="all, delete-orphan")
    bills = relationship("Bill", back_populates="encounter", cascade="all, delete-orphan")
    claims = relationship("Claim", back_populates="encounter", cascade="all, delete-orphan")
    consultation_notes = relationship("ConsultationNotes", back_populates="encounter", cascade="all, delete-orphan", uselist=False)
    
    def __repr__(self):
        return f"<Encounter {self.id} - {self.status}>"

