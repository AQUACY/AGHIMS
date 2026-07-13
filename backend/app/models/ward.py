"""
Department model - for managing hospital departments/units (including wards)
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable
import enum


class DepartmentType(str, enum.Enum):
    """Department type enum"""
    WARD = "ward"  # Shows in IPD activities
    OPD = "opd"  # Outpatient department
    IT = "it"  # IT unit
    ADMIN = "admin"  # Administration
    PHARMACY = "pharmacy"  # Pharmacy department
    OTHER = "other"  # Other departments


class Ward(Base):
    """Hospital department/unit model (renamed from Ward but keeping table name for backward compatibility)"""
    __tablename__ = "wards"  # Keep table name for backward compatibility
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    department_type = Column(SQLEnum(DepartmentType, values_callable=lambda x: [e.value for e in x]), default=DepartmentType.WARD, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow_callable, nullable=False)
    updated_at = Column(DateTime, default=utcnow_callable, onupdate=utcnow_callable, nullable=False)
    
    # Relationships
    staff_assignments = relationship("DepartmentStaffAssignment", back_populates="department", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Department {self.name} (Type: {self.department_type}, Active: {self.is_active})>"

