"""
User model for authentication and authorization
"""
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class User(Base):
    """User model for staff authentication"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(String(50), nullable=False)  # Primary role: Records, Nurse, Doctor, PA, Anaesthetist, Billing, Pharmacy, Pharmacy Head, Store Manager, Lab, Lab Head, Scan, Scan Head, Xray, Xray Head, Claims, Management, Admin, Auditor
    is_active = Column(Boolean, default=True)
    
    # Relationship to additional roles
    additional_roles = relationship("UserRole", foreign_keys="UserRole.user_id", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.username} ({self.role})>"
    
    def has_role(self, role: str) -> bool:
        """Check if user has a specific role (primary or additional)"""
        if self.role == role:
            return True
        return any(ur.role == role for ur in self.additional_roles)
    
    def get_all_roles(self) -> list:
        """Get all roles (primary + additional)"""
        roles = [self.role]
        roles.extend([ur.role for ur in self.additional_roles])
        return roles

