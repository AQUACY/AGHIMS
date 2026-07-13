"""
Doctor/PA can mark which day surgeries appear as cards on the Companion Add Day Surgery page.
"""
from sqlalchemy import Column, Integer, String, DateTime
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class CompanionActiveDaySurgery(Base):
    """g_drg_code of a day surgery that is shown as a card (regularly requested)."""
    __tablename__ = "companion_active_day_surgeries"

    id = Column(Integer, primary_key=True, index=True)
    g_drg_code = Column(String(50), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=utcnow_callable)

    def __repr__(self):
        return f"<CompanionActiveDaySurgery {self.g_drg_code}>"
