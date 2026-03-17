"""
Xray Head can mark which X-rays appear as cards on the Companion Add X-ray page.
"""
from sqlalchemy import Column, Integer, String, DateTime
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class CompanionActiveXray(Base):
    """g_drg_code of an X-ray that is shown as a card (regularly requested)."""
    __tablename__ = "companion_active_xrays"

    id = Column(Integer, primary_key=True, index=True)
    g_drg_code = Column(String(50), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=utcnow_callable)

    def __repr__(self):
        return f"<CompanionActiveXray {self.g_drg_code}>"
