"""
User model for authentication and authorization
"""
from sqlalchemy import Column, Integer, String, Boolean
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
    role = Column(String(50), nullable=False)  # Records, Nurse, Doctor, Billing, Pharmacist, Lab, Claims, Admin, Auditor
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<User {self.username} ({self.role})>"

