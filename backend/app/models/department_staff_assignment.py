"""
Department Staff Assignment model - for assigning IC and Deputies to departments
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable
import enum


class DepartmentRole(str, enum.Enum):
    """Department staff role enum"""
    IC = "ic"  # In-Charge
    DEPUTY = "deputy"  # Deputy


class DepartmentStaffAssignment(Base):
    """Assigns staff to departments with roles (IC/Deputy)"""
    __tablename__ = "department_staff_assignments"
    
    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("wards.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(SQLEnum(DepartmentRole), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow_callable, nullable=False)
    updated_at = Column(DateTime, default=utcnow_callable, onupdate=utcnow_callable, nullable=False)
    
    # Relationships
    department = relationship("Ward", back_populates="staff_assignments")
    user = relationship("User", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<DepartmentStaffAssignment {self.user_id} - {self.department_id} - {self.role}>"

