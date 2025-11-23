"""
Consultation Notes model (presenting complaints, doctor notes, follow-up)
"""
from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable
import enum


class ConsultationNotes(Base):
    """Consultation notes model for encounters"""
    __tablename__ = "consultation_notes"
    
    id = Column(Integer, primary_key=True, index=True)
    encounter_id = Column(Integer, ForeignKey("encounters.id"), nullable=False, unique=True)
    presenting_complaints = Column(Text, nullable=True)  # Presenting complaints/history
    doctor_notes = Column(Text, nullable=True)  # Doctor's clinical notes
    follow_up_date = Column(Date, nullable=True)  # Follow-up appointment date
    # Outcome of consultation: referred, discharged, recommended_for_admission
    outcome = Column(String(100), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utcnow_callable)
    updated_at = Column(DateTime, default=utcnow_callable, onupdate=utcnow_callable)
    
    # Relationships
    encounter = relationship("Encounter", back_populates="consultation_notes", uselist=False)
    
    def __repr__(self):
        return f"<ConsultationNotes {self.encounter_id}>"

