"""
Ward model - for managing hospital wards
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class Ward(Base):
    """Hospital ward model"""
    __tablename__ = "wards"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow_callable, nullable=False)
    updated_at = Column(DateTime, default=utcnow_callable, onupdate=utcnow_callable, nullable=False)
    
    def __repr__(self):
        return f"<Ward {self.name} (Active: {self.is_active})>"

