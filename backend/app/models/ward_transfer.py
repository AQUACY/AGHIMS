"""
Ward Transfer model - tracks transfers of patients between wards
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class WardTransfer(Base):
    """Stores transfers of patients between wards"""
    __tablename__ = "ward_transfers"

    id = Column(Integer, primary_key=True, index=True)
    ward_admission_id = Column(Integer, ForeignKey("ward_admissions.id"), nullable=False)
    from_ward = Column(String(100), nullable=False)  # Ward patient is transferring from
    to_ward = Column(String(100), nullable=False)  # Ward patient is transferring to
    transfer_reason = Column(Text, nullable=True)  # Reason for transfer
    status = Column(String(20), default="pending", nullable=False)  # pending, accepted, rejected
    transferred_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # User who initiated transfer
    accepted_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # User who accepted transfer
    rejected_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # User who rejected transfer
    rejection_reason = Column(Text, nullable=True)  # Reason for rejection
    transferred_at = Column(DateTime, default=utcnow_callable, nullable=False)
    accepted_at = Column(DateTime, nullable=True)  # When transfer was accepted
    rejected_at = Column(DateTime, nullable=True)  # When transfer was rejected
    created_at = Column(DateTime, default=utcnow_callable)
    updated_at = Column(DateTime, default=utcnow_callable, onupdate=utcnow_callable)

    # Relationships
    ward_admission = relationship("WardAdmission", back_populates="transfers")
    transferrer = relationship("User", foreign_keys=[transferred_by])
    accepter = relationship("User", foreign_keys=[accepted_by])
    rejecter = relationship("User", foreign_keys=[rejected_by])

    def __repr__(self):
        return f"<WardTransfer {self.id} - From {self.from_ward} to {self.to_ward}>"

