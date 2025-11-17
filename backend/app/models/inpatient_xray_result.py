"""
Inpatient X-ray Result model - stores xray results for IPD investigations
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class InpatientXrayResult(Base):
    """X-ray result model for inpatient investigations"""
    __tablename__ = "inpatient_xray_results"
    
    id = Column(Integer, primary_key=True, index=True)
    investigation_id = Column(Integer, ForeignKey("inpatient_investigations.id"), nullable=False, unique=True)
    results_text = Column(Text, nullable=True)  # Text results/findings
    attachment_path = Column(String(500), nullable=True)  # Path to uploaded PDF/image attachment
    entered_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # User who first entered the result
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # User who last updated the result
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    investigation = relationship("InpatientInvestigation", back_populates="xray_result", uselist=False)
    
    def __repr__(self):
        return f"<InpatientXrayResult {self.investigation_id}>"

