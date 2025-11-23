"""
Inpatient Prescription model - stores prescriptions for clinical reviews
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class InpatientPrescription(Base):
    """Prescription model for inpatient clinical reviews"""
    __tablename__ = "inpatient_prescriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    clinical_review_id = Column(Integer, ForeignKey("inpatient_clinical_reviews.id"), nullable=False)
    medicine_code = Column(String(50), nullable=False)  # Medicine/item code
    medicine_name = Column(String(500), nullable=False)
    dose = Column(String(100))  # e.g., "500"
    unit = Column(String(50), nullable=True)  # e.g., "MG", "ML", "TAB"
    frequency = Column(String(100))  # e.g., "BDS", "TDS", "OD"
    frequency_value = Column(Integer, nullable=True)  # Numeric value for frequency
    duration = Column(String(100))  # e.g., "7 DAYS"
    instructions = Column(Text, nullable=True)  # Instructions for the drug
    quantity = Column(Integer, nullable=False)  # Dispensed quantity
    unparsed = Column(Text)  # Original prescription text
    prescribed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    confirmed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    dispensed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    is_external = Column(Integer, default=0, nullable=False)  # 0 = internal, 1 = external
    service_date = Column(DateTime, default=utcnow_callable)
    created_at = Column(DateTime, default=utcnow_callable)
    
    # Relationships
    clinical_review = relationship("InpatientClinicalReview", back_populates="prescriptions")
    
    def __repr__(self):
        return f"<InpatientPrescription {self.medicine_code} - Qty: {self.quantity}>"

