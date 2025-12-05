"""
Store model - for managing stores (Main Store, Pharmacy Store, etc.)
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class Store(Base):
    """Store model for managing different stores"""
    __tablename__ = "stores"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow_callable, nullable=False)
    updated_at = Column(DateTime, default=utcnow_callable, onupdate=utcnow_callable, nullable=False)
    
    # Relationships
    staff_assignments = relationship("StoreStaffAssignment", back_populates="store", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Store {self.name} (Active: {self.is_active})>"

