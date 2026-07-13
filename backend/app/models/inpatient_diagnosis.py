"""
Inpatient Diagnosis model - stores diagnoses for clinical reviews
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class InpatientDiagnosis(Base):
    """Diagnosis model for inpatient clinical reviews"""
    __tablename__ = "inpatient_diagnoses"
    
    id = Column(Integer, primary_key=True, index=True)
    clinical_review_id = Column(Integer, ForeignKey("inpatient_clinical_reviews.id"), nullable=False)
    icd10 = Column(String(50), nullable=False)  # ICD-10 code
    diagnosis = Column(Text, nullable=False)  # Diagnosis description
    gdrg_code = Column(String(50))  # GDRG code for NHIA
    diagnosis_status = Column(String(20))  # 'new', 'old', or 'recurring'
    is_provisional = Column(Boolean, default=False)
    is_chief = Column(Boolean, default=False)  # Chief/final diagnosis
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utcnow_callable)
    
    # Relationships
    clinical_review = relationship("InpatientClinicalReview", back_populates="diagnoses")
    
    def __repr__(self):
        return f"<InpatientDiagnosis {self.icd10} - {self.diagnosis[:30]}>"

