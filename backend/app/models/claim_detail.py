"""
Claim detail models - stores claim-specific data that may differ from original service records
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class ClaimDiagnosis(Base):
    """Claim-specific diagnosis data"""
    __tablename__ = "claim_diagnoses"
    
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    diagnosis_id = Column(Integer, ForeignKey("diagnoses.id"), nullable=True)  # Reference to original diagnosis
    description = Column(Text, nullable=False)
    icd10 = Column(String(50), nullable=False)
    gdrg_code = Column(String(50))
    is_chief = Column(Boolean, default=False)
    display_order = Column(Integer, default=0)  # For ordering (1-4)
    created_at = Column(DateTime, default=utcnow_callable)
    updated_at = Column(DateTime, default=utcnow_callable, onupdate=utcnow_callable)
    
    # Relationships
    claim = relationship("Claim", back_populates="claim_diagnoses")
    
    def __repr__(self):
        return f"<ClaimDiagnosis {self.gdrg_code} - {self.description[:30]}>"


class ClaimInvestigation(Base):
    """Claim-specific investigation data"""
    __tablename__ = "claim_investigations"
    
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    investigation_id = Column(Integer, ForeignKey("investigations.id"), nullable=True)  # Reference to original investigation
    description = Column(Text)
    gdrg_code = Column(String(50), nullable=False)
    service_date = Column(DateTime, default=utcnow_callable)
    investigation_type = Column(String(50))  # lab, scan, xray
    display_order = Column(Integer, default=0)  # For ordering (1-5)
    created_at = Column(DateTime, default=utcnow_callable)
    updated_at = Column(DateTime, default=utcnow_callable, onupdate=utcnow_callable)
    
    # Relationships
    claim = relationship("Claim", back_populates="claim_investigations")
    
    def __repr__(self):
        return f"<ClaimInvestigation {self.gdrg_code} - {self.status}>"


class ClaimPrescription(Base):
    """Claim-specific prescription data"""
    __tablename__ = "claim_prescriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    prescription_id = Column(Integer, ForeignKey("prescriptions.id"), nullable=True)  # Reference to original prescription
    description = Column(Text, nullable=False)  # Medicine name
    code = Column(String(50), nullable=False)  # Medicine code
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    total_cost = Column(Float, nullable=False)
    service_date = Column(DateTime, default=utcnow_callable)
    dose = Column(String(100))
    frequency = Column(String(100))
    duration = Column(String(100))
    unparsed = Column(Text)
    display_order = Column(Integer, default=0)  # For ordering (1-5)
    created_at = Column(DateTime, default=utcnow_callable)
    updated_at = Column(DateTime, default=utcnow_callable, onupdate=utcnow_callable)
    
    # Relationships
    claim = relationship("Claim", back_populates="claim_prescriptions")
    
    def __repr__(self):
        return f"<ClaimPrescription {self.code} - Qty: {self.quantity}>"


class ClaimProcedure(Base):
    """Claim-specific procedure data"""
    __tablename__ = "claim_procedures"
    
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    description = Column(Text)
    gdrg_code = Column(String(50))
    service_date = Column(DateTime, default=utcnow_callable)
    display_order = Column(Integer, default=0)  # For ordering (1-3)
    created_at = Column(DateTime, default=utcnow_callable)
    updated_at = Column(DateTime, default=utcnow_callable, onupdate=utcnow_callable)
    
    # Relationships
    claim = relationship("Claim", back_populates="claim_procedures")
    
    def __repr__(self):
        return f"<ClaimProcedure {self.gdrg_code} - {self.description[:30]}>"

