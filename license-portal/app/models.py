from sqlalchemy import Column, DateTime, Integer, String, Text
from app.database import Base
from datetime import datetime


class LicenseRecord(Base):
    __tablename__ = "license_registry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    license_id = Column(String(48), unique=True, nullable=False, index=True)
    customer_label = Column(String(255), nullable=False, default="")
    facility_code = Column(String(64), nullable=True)
    valid_from = Column(DateTime, nullable=False)
    valid_until = Column(DateTime, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
