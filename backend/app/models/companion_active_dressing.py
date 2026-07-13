"""
Nurse/Doctor/PA can mark which dressing and treatment room services appear as cards on the Companion Dressing room page.
"""
from sqlalchemy import Column, Integer, String, DateTime
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class CompanionActiveDressing(Base):
    """g_drg_code of a dressing/treatment room service that is shown as a card (regularly requested)."""
    __tablename__ = "companion_active_dressings"

    id = Column(Integer, primary_key=True, index=True)
    g_drg_code = Column(String(50), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=utcnow_callable)

    def __repr__(self):
        return f"<CompanionActiveDressing {self.g_drg_code}>"
