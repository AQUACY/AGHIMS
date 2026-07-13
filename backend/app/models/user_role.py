"""
User Role model - stores additional roles assigned to users
This allows users to have multiple roles (e.g., a Pharmacist can also have Claims role)
"""
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class UserRole(Base):
    """Additional roles assigned to users (many-to-many relationship)"""
    __tablename__ = "user_roles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # The additional role name
    created_at = Column(DateTime, default=utcnow_callable)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Who assigned this role
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="additional_roles")
    creator = relationship("User", foreign_keys=[created_by])
    
    # Ensure a user can't have the same role assigned twice
    __table_args__ = (
        UniqueConstraint('user_id', 'role', name='unique_user_role'),
    )
    
    def __repr__(self):
        return f"<UserRole user_id={self.user_id} role={self.role}>"

