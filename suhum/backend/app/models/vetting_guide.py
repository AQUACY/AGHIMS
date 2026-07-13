"""Recovered facility visit data from vetting guide CSV uploads."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class VettingGuideUpload(Base):
    __tablename__ = "vetting_guide_uploads"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime, default=utcnow_callable)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    row_count = Column(Integer, default=0)
    matched_claim_ids = Column(Integer, default=0)

    records = relationship("VettingGuideRecord", back_populates="upload", cascade="all, delete-orphan")


class VettingGuideRecord(Base):
    __tablename__ = "vetting_guide_records"

    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(Integer, ForeignKey("vetting_guide_uploads.id"), nullable=False, index=True)
    claim_id = Column(String(50), nullable=False, index=True)
    entity_id = Column(String(50), nullable=True)
    visit_type = Column(String(20), nullable=True)
    service_date = Column(String(20), nullable=True)
    patient_no = Column(String(100), nullable=True)
    patient_name = Column(String(255), nullable=True)
    member_no = Column(String(50), nullable=True)
    raw_row = Column(JSON, nullable=False)
    parsed = Column(JSON, nullable=False)

    upload = relationship("VettingGuideUpload", back_populates="records")

    __table_args__ = (
        Index("ix_vetting_guide_upload_claim", "upload_id", "claim_id", unique=True),
    )
