"""
Inpatient Investigation model - stores investigations for clinical reviews
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base


class InpatientInvestigationType(str, enum.Enum):
    """Investigation type enumeration"""
    LAB = "lab"
    SCAN = "scan"
    XRAY = "xray"


class InpatientInvestigationStatus(str, enum.Enum):
    """Investigation status enumeration"""
    REQUESTED = "requested"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class InpatientInvestigation(Base):
    """Investigation model for inpatient clinical reviews"""
    __tablename__ = "inpatient_investigations"
    
    id = Column(Integer, primary_key=True, index=True)
    clinical_review_id = Column(Integer, ForeignKey("inpatient_clinical_reviews.id"), nullable=False)
    service_type = Column(String(100), nullable=True)  # Service Type (Department/Clinic)
    gdrg_code = Column(String(50), nullable=False)  # GDRG code for the investigation
    procedure_name = Column(String(500), nullable=True)  # Procedure/service name
    investigation_type = Column(String(50), nullable=False)  # lab, scan, xray
    notes = Column(String(1000), nullable=True)  # Notes/remarks from doctor
    price = Column(String(50), nullable=True)  # Price of the investigation
    status = Column(String(50), default=InpatientInvestigationStatus.REQUESTED.value, nullable=False)
    service_date = Column(DateTime, default=datetime.utcnow)
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    confirmed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    completed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    cancelled_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    cancellation_reason = Column(String(1000), nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    clinical_review = relationship("InpatientClinicalReview", back_populates="investigations")
    
    def __repr__(self):
        return f"<InpatientInvestigation {self.gdrg_code} - {self.status}>"

