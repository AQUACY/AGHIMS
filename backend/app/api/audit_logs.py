"""
Audit Logs API endpoints
"""
from typing import Optional, List
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from pydantic import BaseModel
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.audit_log import AuditLog
from app.models.user import User

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


class AuditLogResponse(BaseModel):
    """Audit log response model"""
    id: int
    user_id: int
    username: str
    full_name: Optional[str]
    role: str
    action: str
    resource_type: Optional[str]
    resource_id: Optional[int]
    details: Optional[str]
    ip_address: Optional[str]
    timestamp: datetime
    
    class Config:
        from_attributes = True


class AuditLogsListResponse(BaseModel):
    """Response model for audit logs list"""
    total: int
    logs: List[AuditLogResponse]


@router.get("", response_model=AuditLogsListResponse)
def get_audit_logs(
    role: Optional[str] = Query(None, description="Filter by user role"),
    full_name: Optional[str] = Query(None, description="Filter by user full name (partial match)"),
    username: Optional[str] = Query(None, description="Filter by username (partial match)"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    action: Optional[str] = Query(None, description="Filter by action"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Auditor"]))
):
    """
    Get audit logs with filtering options
    
    Only Admin and Auditor roles can access this endpoint.
    """
    # Build query
    query = db.query(AuditLog)
    
    # Apply filters
    filters = []
    
    if role:
        filters.append(AuditLog.role == role)
    
    if full_name:
        filters.append(AuditLog.full_name.ilike(f"%{full_name}%"))
    
    if username:
        filters.append(AuditLog.username.ilike(f"%{username}%"))
    
    if action:
        filters.append(AuditLog.action == action)
    
    if resource_type:
        filters.append(AuditLog.resource_type == resource_type)
    
    # Date range filter
    if start_date:
        try:
            start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
            filters.append(AuditLog.timestamp >= start_datetime)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format. Use YYYY-MM-DD"
            )
    
    if end_date:
        try:
            # Include the entire end date (up to 23:59:59)
            end_datetime = datetime.strptime(end_date, "%Y-%m-%d")
            end_datetime = end_datetime.replace(hour=23, minute=59, second=59, microsecond=999999)
            filters.append(AuditLog.timestamp <= end_datetime)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format. Use YYYY-MM-DD"
            )
    
    # Apply all filters
    if filters:
        query = query.filter(and_(*filters))
    
    # Get total count
    total = query.count()
    
    # Order by timestamp descending (most recent first)
    query = query.order_by(AuditLog.timestamp.desc())
    
    # Apply pagination
    offset = (page - 1) * page_size
    logs = query.offset(offset).limit(page_size).all()
    
    return {
        "total": total,
        "logs": logs
    }


@router.get("/roles", response_model=List[str])
def get_available_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Auditor"]))
):
    """
    Get list of unique roles from audit logs
    """
    roles = db.query(AuditLog.role).distinct().all()
    return [role[0] for role in roles if role[0]]


@router.get("/actions", response_model=List[str])
def get_available_actions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Auditor"]))
):
    """
    Get list of unique actions from audit logs
    """
    actions = db.query(AuditLog.action).distinct().all()
    return [action[0] for action in actions if action[0]]


@router.get("/resource-types", response_model=List[str])
def get_available_resource_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Auditor"]))
):
    """
    Get list of unique resource types from audit logs
    """
    resource_types = db.query(AuditLog.resource_type).distinct().all()
    return [rt[0] for rt in resource_types if rt[0]]


@router.get("/{log_id}", response_model=AuditLogResponse)
def get_audit_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Auditor"]))
):
    """
    Get a specific audit log by ID
    """
    log = db.query(AuditLog).filter(AuditLog.id == log_id).first()
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log not found"
        )
    return log

