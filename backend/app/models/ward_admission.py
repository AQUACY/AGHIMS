"""
Ward Admission model - tracks patients currently admitted to wards
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
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
    admitted_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # User who confirmed admission
    admitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    discharged_at = Column(DateTime, nullable=True)  # When patient was discharged
    discharged_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # User who discharged
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    encounter = relationship("Encounter")
    admission_recommendation = relationship("AdmissionRecommendation")

    def __repr__(self):
        return f"<WardAdmission {self.encounter_id} - {self.ward}>"

