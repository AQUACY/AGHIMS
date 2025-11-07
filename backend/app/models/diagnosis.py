"""
Diagnosis model
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class Diagnosis(Base):
    """Diagnosis model for encounters"""
    __tablename__ = "diagnoses"
    
    id = Column(Integer, primary_key=True, index=True)
    encounter_id = Column(Integer, ForeignKey("encounters.id"), nullable=False)
    icd10 = Column(String(50), nullable=False)  # ICD-10 code
    diagnosis = Column(Text, nullable=False)  # Diagnosis description
    gdrg_code = Column(String(50))  # GDRG code for NHIA
    diagnosis_status = Column(String(20))  # 'new', 'old', or 'recurring'
    is_provisional = Column(Boolean, default=False)
    is_chief = Column(Boolean, default=False)  # Chief/final diagnosis
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    encounter = relationship("Encounter", back_populates="diagnoses")
    
    def __repr__(self):
        return f"<Diagnosis {self.icd10} - {self.diagnosis[:30]}>"

