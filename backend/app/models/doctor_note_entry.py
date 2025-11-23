"""
Doctor Note Entry model - stores individual doctor notes entries for consultations
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class DoctorNoteEntry(Base):
    """Stores individual doctor notes entries for encounters"""
    __tablename__ = "doctor_note_entries"

    id = Column(Integer, primary_key=True, index=True)
    encounter_id = Column(Integer, ForeignKey("encounters.id"), nullable=False)
    notes = Column(Text, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utcnow_callable, nullable=False)
    updated_at = Column(DateTime, default=utcnow_callable, onupdate=utcnow_callable)

    # Relationships
    encounter = relationship("Encounter", back_populates="doctor_note_entries")
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<DoctorNoteEntry {self.id} - Encounter {self.encounter_id}>"

