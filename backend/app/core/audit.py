"""
Audit logging utility for tracking user activities
"""
import json
from typing import Optional, Dict, Any
from fastapi import Request
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog
from app.models.user import User


def get_client_ip(request: Request) -> Optional[str]:
    """Extract client IP address from request"""
    if request.client:
        return request.client.host
    # Try to get from headers (for proxies)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    return None


def create_audit_log(
    db: Session,
    user: User,
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None
) -> AuditLog:
    """
    Create an audit log entry
    
    Args:
        db: Database session
        user: User performing the action
        action: Action performed (e.g., "CREATE", "UPDATE", "DELETE", "VIEW", "LOGIN", "LOGOUT")
        resource_type: Type of resource (e.g., "Patient", "Bill", "Claim", "Encounter")
        resource_id: ID of the resource being acted upon
        details: Additional details as a dictionary (will be JSON serialized)
        ip_address: IP address of the client
    
    Returns:
        AuditLog: The created audit log entry
    """
    # Serialize details to JSON string if provided
    details_str = None
    if details:
        try:
            details_str = json.dumps(details, default=str)
        except (TypeError, ValueError):
            details_str = str(details)
    
    audit_log = AuditLog(
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details_str,
        ip_address=ip_address
    )
    
    db.add(audit_log)
    db.commit()
    db.refresh(audit_log)
    
    return audit_log


def log_activity(
    db: Session,
    user: User,
    request: Request,
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None
):
    """
    Convenience function to log activity with automatic IP extraction
    
    Args:
        db: Database session
        user: User performing the action
        request: FastAPI request object
        action: Action performed
        resource_type: Type of resource
        resource_id: ID of the resource
        details: Additional details
    """
    try:
        ip_address = get_client_ip(request)
        create_audit_log(
            db=db,
            user=user,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address
        )
    except Exception as e:
        # Don't let audit logging failures break the application
        print(f"Warning: Failed to create audit log: {e}")
        import traceback
        traceback.print_exc()

