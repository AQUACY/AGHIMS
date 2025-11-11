"""
Nurse Note model - stores nurse notes for ward admissions
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class NurseNote(Base):
    """Stores nurse notes for ward admissions"""
    __tablename__ = "nurse_notes"

    id = Column(Integer, primary_key=True, index=True)
    ward_admission_id = Column(Integer, ForeignKey("ward_admissions.id"), nullable=False)
    notes = Column(Text, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    strikethrough = Column(Integer, default=0, nullable=False)  # 0 = not strikethrough, 1 = strikethrough
    strikethrough_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # User who strikethrough the note
    strikethrough_at = Column(DateTime, nullable=True)  # When note was strikethrough
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    ward_admission = relationship("WardAdmission", back_populates="nurse_notes")
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<NurseNote {self.id} - WardAdmission {self.ward_admission_id}>"

