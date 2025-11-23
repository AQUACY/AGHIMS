"""
Claim model for NHIA claims
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class ClaimStatus(str, enum.Enum):
    """Claim status enumeration"""
    DRAFT = "draft"
    FINALIZED = "finalized"
    REOPENED = "reopened"


class Claim(Base):
    """Claim model for NHIA ClaimIT export"""
    __tablename__ = "claims"
    
    id = Column(Integer, primary_key=True, index=True)
    encounter_id = Column(Integer, ForeignKey("encounters.id"), nullable=False)
    claim_id = Column(String(50), unique=True, index=True, nullable=False)  # CLA-XXXXX format
    claim_check_code = Column(String(100))
    pre_authorization_codes = Column(String(500))
    physician_id = Column(String(50), nullable=False)  # SNO-XXX format
    member_no = Column(String(100), nullable=False)
    card_serial_no = Column(String(100))
    is_dependant = Column(Boolean, default=False)
    type_of_service = Column(String(50), default="OPD")  # OPD, IPD
    is_unbundled = Column(Boolean, default=False)
    includes_pharmacy = Column(Boolean, default=False)
    type_of_attendance = Column(String(50))  # EAE, ANC, etc.
    service_outcome = Column(String(50))  # DISC (discharged)
    specialty_attended = Column(String(100))  # OPDC, OBGY, etc.
    principal_gdrg = Column(String(50))  # Principal GDRG code
    status = Column(String(50), default=ClaimStatus.DRAFT.value, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utcnow_callable)
    finalized_at = Column(DateTime, nullable=True)
    exported_at = Column(DateTime, nullable=True)
    
    # Relationships
    encounter = relationship("Encounter", back_populates="claims")
    claim_diagnoses = relationship("ClaimDiagnosis", back_populates="claim", cascade="all, delete-orphan")
    claim_investigations = relationship("ClaimInvestigation", back_populates="claim", cascade="all, delete-orphan")
    claim_prescriptions = relationship("ClaimPrescription", back_populates="claim", cascade="all, delete-orphan")
    claim_procedures = relationship("ClaimProcedure", back_populates="claim", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Claim {self.claim_id} - {self.status}>"

