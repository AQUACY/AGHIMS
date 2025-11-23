"""
Nurse Mid Documentation model - stores nurse mid documentation for ward admissions
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class NurseMidDocumentation(Base):
    """Stores nurse mid documentation for ward admissions"""
    __tablename__ = "nurse_mid_documentations"

    id = Column(Integer, primary_key=True, index=True)
    ward_admission_id = Column(Integer, ForeignKey("ward_admissions.id"), nullable=False)
    patient_problems_diagnosis = Column(Text, nullable=True)  # Patient Problems / Diagnosis
    aim_of_care = Column(Text, nullable=True)  # Aim of Care / Objectives / Outcome Criteria
    nursing_assessment = Column(Text, nullable=True)  # Nursing Assessment
    nursing_orders = Column(Text, nullable=True)  # Nursing Orders
    nursing_intervention = Column(Text, nullable=True)  # Nursing Intervention
    evaluation = Column(Text, nullable=True)  # Evaluation
    documentation = Column(Text, nullable=True)  # Keep for backward compatibility
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utcnow_callable, nullable=False)
    updated_at = Column(DateTime, default=utcnow_callable, onupdate=utcnow_callable)

    # Relationships
    ward_admission = relationship("WardAdmission", back_populates="nurse_mid_documentations")
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<NurseMidDocumentation {self.id} - WardAdmission {self.ward_admission_id}>"

