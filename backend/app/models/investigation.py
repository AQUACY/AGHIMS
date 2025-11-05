"""
Investigation model (labs, scans, x-rays)
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base


class InvestigationType(str, enum.Enum):
    """Investigation type enumeration"""
    LAB = "lab"
    SCAN = "scan"
    XRAY = "xray"


class InvestigationStatus(str, enum.Enum):
    """Investigation status enumeration"""
    REQUESTED = "requested"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Investigation(Base):
    """Investigation model (labs, scans, x-rays)"""
    __tablename__ = "investigations"
    
    id = Column(Integer, primary_key=True, index=True)
    encounter_id = Column(Integer, ForeignKey("encounters.id"), nullable=False)
    gdrg_code = Column(String(50), nullable=False)  # GDRG code for the investigation
    procedure_name = Column(String(500), nullable=True)  # Procedure/service name
    investigation_type = Column(String(50), nullable=False)  # lab, scan, xray
    notes = Column(String(1000), nullable=True)  # Notes/remarks from doctor
    price = Column(String(50), nullable=True)  # Price of the investigation (auto-fetched from price list)
    status = Column(String(50), default=InvestigationStatus.REQUESTED.value, nullable=False)
    service_date = Column(DateTime, default=datetime.utcnow)
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    confirmed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    cancelled_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    cancellation_reason = Column(String(1000), nullable=True)  # Reason for cancellation
    cancelled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    encounter = relationship("Encounter", back_populates="investigations")
    lab_result = relationship("LabResult", back_populates="investigation", cascade="all, delete-orphan", uselist=False)
    scan_result = relationship("ScanResult", back_populates="investigation", cascade="all, delete-orphan", uselist=False)
    xray_result = relationship("XrayResult", back_populates="investigation", cascade="all, delete-orphan", uselist=False)
    
    def __repr__(self):
        return f"<Investigation {self.gdrg_code} - {self.status}>"

