"""
Audit Log model for tracking user activities
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class AuditLog(Base):
    """Audit log model for tracking user activities"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    username = Column(String(100), nullable=False, index=True)
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True)  # e.g., "CREATE", "UPDATE", "DELETE", "VIEW", "LOGIN", "LOGOUT"
    resource_type = Column(String(100), nullable=True, index=True)  # e.g., "Patient", "Bill", "Claim", "Encounter"
    resource_id = Column(Integer, nullable=True, index=True)  # ID of the resource being acted upon
    details = Column(Text, nullable=True)  # JSON string or detailed description
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    timestamp = Column(DateTime, default=utcnow_callable, nullable=False, index=True)
    
    # Relationship to user (optional, for easier queries)
    user = relationship("User", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<AuditLog {self.username} - {self.action} - {self.resource_type} - {self.timestamp}>"

