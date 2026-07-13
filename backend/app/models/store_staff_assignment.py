"""
Store Staff Assignment model - for assigning Store Managers and Department Heads to stores
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable
import enum


class StoreRole(str, enum.Enum):
    """Store staff role enum"""
    STORE_MANAGER = "store_manager"
    DEPARTMENT_HEAD = "department_head"


class StoreStaffAssignment(Base):
    """Assigns staff to stores with roles (Store Manager/Department Head)"""
    __tablename__ = "store_staff_assignments"
    
    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(SQLEnum(StoreRole), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow_callable, nullable=False)
    updated_at = Column(DateTime, default=utcnow_callable, onupdate=utcnow_callable, nullable=False)
    
    # Relationships
    store = relationship("Store", back_populates="staff_assignments")
    user = relationship("User", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<StoreStaffAssignment {self.user_id} - {self.store_id} - {self.role}>"

