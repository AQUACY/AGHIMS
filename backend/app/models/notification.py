"""
Notification model - for system notifications and alerts
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable
import enum


class NotificationType(str, enum.Enum):
    """Notification types"""
    REQUISITION_CREATED = "requisition_created"
    REQUISITION_APPROVED = "requisition_approved"
    REQUISITION_REJECTED = "requisition_rejected"
    REQUISITION_FULFILLED = "requisition_fulfilled"
    REQUISITION_PARTIALLY_FULFILLED = "requisition_partially_fulfilled"
    REQUISITION_FULFILLMENT_REVERTED = "requisition_fulfillment_reverted"


class Notification(Base):
    """System notifications for users"""
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # Target user
    notification_type = Column(SQLEnum(NotificationType), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    related_id = Column(Integer, nullable=True)  # Related entity ID (e.g., requisition_id)
    related_type = Column(String(100), nullable=True)  # Related entity type (e.g., "requisition")
    created_at = Column(DateTime, default=utcnow_callable, nullable=False, index=True)
    read_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<Notification {self.id} - {self.notification_type.value} for user {self.user_id}>"

