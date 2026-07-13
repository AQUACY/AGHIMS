"""
Admission recommendation model
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class AdmissionRecommendation(Base):
    """Stores admission recommendation details when consultation outcome is admission"""
    __tablename__ = "admission_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    encounter_id = Column(Integer, ForeignKey("encounters.id"), nullable=False, unique=True)
    ward = Column(String(100), nullable=False)
    recommended_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    confirmed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    cancelled = Column(Integer, default=0, nullable=False)  # 0 = not cancelled, 1 = cancelled
    cancelled_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=utcnow_callable)
    updated_at = Column(DateTime, default=utcnow_callable, onupdate=utcnow_callable)

    # Relationships
    encounter = relationship("Encounter")

    def __repr__(self):
        return f"<AdmissionRecommendation {self.encounter_id} - {self.ward}>"


