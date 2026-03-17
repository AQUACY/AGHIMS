"""
Lab Head can mark which investigations appear as cards on the Companion Add Investigation page.
"""
from sqlalchemy import Column, Integer, String, DateTime
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class CompanionActiveInvestigation(Base):
    """g_drg_code of an investigation that is shown as a card (regularly requested)."""
    __tablename__ = "companion_active_investigations"

    id = Column(Integer, primary_key=True, index=True)
    g_drg_code = Column(String(50), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=utcnow_callable)

    def __repr__(self):
        return f"<CompanionActiveInvestigation {self.g_drg_code}>"
