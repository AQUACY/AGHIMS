"""
Notification utility functions for creating and managing notifications
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.notification import Notification, NotificationType
from app.models.user import User


def create_notification(
    db: Session,
    user_id: int,
    notification_type: NotificationType,
    title: str,
    message: str,
    related_id: Optional[int] = None,
    related_type: Optional[str] = None
) -> Notification:
    """
    Create a notification for a user
    
    Args:
        db: Database session
        user_id: Target user ID
        notification_type: Type of notification
        title: Notification title
        message: Notification message
        related_id: Related entity ID (e.g., requisition_id)
        related_type: Related entity type (e.g., "requisition")
    
    Returns:
        Notification: The created notification
    """
    notification = Notification(
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        message=message,
        related_id=related_id,
        related_type=related_type
    )
    
    db.add(notification)
    db.commit()
    db.refresh(notification)
    
    return notification


def create_notifications_for_roles(
    db: Session,
    roles: List[str],
    notification_type: NotificationType,
    title: str,
    message: str,
    related_id: Optional[int] = None,
    related_type: Optional[str] = None
) -> List[Notification]:
    """
    Create notifications for all users with specified roles
    
    Args:
        db: Database session
        roles: List of role names
        notification_type: Type of notification
        title: Notification title
        message: Notification message
        related_id: Related entity ID
        related_type: Related entity type
    
    Returns:
        List[Notification]: Created notifications
    """
    users = db.query(User).filter(
        User.role.in_(roles),
        User.is_active == True
    ).all()
    
    notifications = []
    for user in users:
        notification = create_notification(
            db=db,
            user_id=user.id,
            notification_type=notification_type,
            title=title,
            message=message,
            related_id=related_id,
            related_type=related_type
        )
        notifications.append(notification)
    
    return notifications


def create_notification_for_user(
    db: Session,
    user_id: int,
    notification_type: NotificationType,
    title: str,
    message: str,
    related_id: Optional[int] = None,
    related_type: Optional[str] = None
) -> Notification:
    """
    Create a notification for a specific user (alias for create_notification)
    """
    return create_notification(
        db=db,
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        message=message,
        related_id=related_id,
        related_type=related_type
    )

