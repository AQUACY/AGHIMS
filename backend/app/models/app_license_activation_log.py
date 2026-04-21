"""
Append-only log of license activations (replace = new row + updated singleton state).
"""
from sqlalchemy import Column, DateTime, Integer, String
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class AppLicenseActivationLog(Base):
    __tablename__ = "app_license_activation_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    activated_at = Column(DateTime, nullable=False, default=utcnow_callable)
    license_public_id = Column(String(64), nullable=False, index=True)
    customer_label = Column(String(255), nullable=False, default="")
    valid_until = Column(DateTime, nullable=True)
    facility_code_in_license = Column(String(64), nullable=True)
