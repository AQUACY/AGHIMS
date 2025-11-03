"""
Admission recommendation model
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class AdmissionRecommendation(Base):
    """Stores admission recommendation details when consultation outcome is admission"""
    __tablename__ = "admission_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    encounter_id = Column(Integer, ForeignKey("encounters.id"), nullable=False, unique=True)
    ward = Column(String(100), nullable=False)
    recommended_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    encounter = relationship("Encounter")

    def __repr__(self):
        return f"<AdmissionRecommendation {self.encounter_id} - {self.ward}>"


