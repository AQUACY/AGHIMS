"""
Pre-issued codes for confidential consultations.

A code is prepared ahead of time, then given to one client for a visit
and its follow-up. Service points work with the code. The register is
where the code is mapped back to the client.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class ConfidentialCode(Base):
    __tablename__ = "confidential_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(32), unique=True, index=True, nullable=False)
    status = Column(String(20), default="available", nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True, index=True)
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utcnow_callable, nullable=False)

    patient = relationship("Patient")

    def __repr__(self):
        return f"<ConfidentialCode {self.code} {self.status}>"
