"""
Singleton facility / branding settings for multi-site deployments.
"""
from sqlalchemy import Column, Integer, String, DateTime
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class FacilitySettings(Base):
    __tablename__ = "facility_settings"

    id = Column(Integer, primary_key=True, index=True)
    display_name = Column(String(255), nullable=False, default="KDG Health App")
    facility_code = Column(String(64), nullable=True)
    updated_at = Column(DateTime, default=utcnow_callable, onupdate=utcnow_callable)

    def __repr__(self):
        return f"<FacilitySettings {self.display_name!r} code={self.facility_code!r}>"
