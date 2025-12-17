"""
Middleware for automatic audit logging of all API endpoints
"""
import json
from typing import Optional, Callable
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.audit import create_audit_log, get_client_ip
from app.models.user import User


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that automatically logs API endpoint calls to the audit trail.
    Only logs POST, PUT, PATCH, DELETE requests (not GET requests) to reduce database growth.
    GET requests are excluded as they are read-only operations.
    Login actions are logged separately in auth.py.
    """
    
    # Endpoints to exclude from audit logging (health checks, docs, etc.)
    EXCLUDED_PATHS = {
        "/",
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/api/auth/login",  # Login is logged separately
        "/api/uploads",  # Static file serving
    }
    
    # Paths that should be logged but don't require authentication
    PUBLIC_PATHS = {
        "/api/auth/login",
    }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and log it to audit trail
        Only logs POST, PUT, PATCH, DELETE requests (not GET requests)
        Also logs LOGIN actions which are handled separately in auth.py
        """
        # Skip excluded paths
        if request.url.path in self.EXCLUDED_PATHS or request.url.path.startswith("/api/uploads"):
            return await call_next(request)
        
        # Skip OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Skip GET requests - only log creates, updates, deletes, and logins
        # GET requests are not logged to reduce database growth
        if request.method == "GET":
            return await call_next(request)
        
        # Get database session using context manager pattern
        db_gen = get_db()
        db: Session = next(db_gen)
        
        try:
            # Try to get current user (may fail for unauthenticated requests)
            user: Optional[User] = None
            try:
                # Extract token from Authorization header
                auth_header = request.headers.get("Authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    token = auth_header.split(" ")[1]
                    # Use get_current_user logic to get user
                    from app.core.security import decode_access_token
                    from jose import JWTError
                    try:
                        payload = decode_access_token(token)
                        if payload:
                            user_id = payload.get("sub")
                            if user_id:
                                user = db.query(User).filter(User.id == int(user_id)).first()
                    except (JWTError, ValueError, TypeError):
                        pass  # User not authenticated
            except Exception:
                pass  # User not authenticated, continue with logging
            
            # Determine action based on HTTP method
            action = self._get_action_from_method(request.method)
            
            # Determine resource type from path
            resource_type = self._get_resource_type_from_path(request.url.path)
            
            # Extract resource ID from path if available
            resource_id = self._extract_resource_id_from_path(request.url.path)
            
            # Get query parameters
            query_params = dict(request.query_params)
            
            # Prepare details (we'll log after response to avoid body reading issues)
            details = {
                "endpoint": request.url.path,
                "method": request.method,
                "query_params": query_params if query_params else None,
            }
            
            # If user is authenticated, log with user info
            if user:
                ip_address = get_client_ip(request)
                try:
                    create_audit_log(
                        db=db,
                        user=user,
                        action=action,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        details=details,
                        ip_address=ip_address,
                        endpoint_path=request.url.path,
                        http_method=request.method
                    )
                except Exception as e:
                    # Don't let audit logging failures break the application
                    print(f"Warning: Failed to create audit log: {e}")
            
            # Process the request
            response = await call_next(request)
            
            return response
            
        except Exception as e:
            # If there's an error, still try to process the request
            # but log the error
            print(f"Error in audit middleware: {e}")
            try:
                return await call_next(request)
            except Exception as e2:
                # Re-raise if call_next also fails
                raise e2
        finally:
            # Close database session properly
            try:
                db.close()
            except Exception:
                pass
    
    def _get_action_from_method(self, method: str) -> str:
        """Map HTTP method to audit action"""
        method_upper = method.upper()
        if method_upper == "GET":
            return "VIEW"
        elif method_upper == "POST":
            return "CREATE"
        elif method_upper == "PUT" or method_upper == "PATCH":
            return "UPDATE"
        elif method_upper == "DELETE":
            return "DELETE"
        else:
            return method_upper
    
    def _get_resource_type_from_path(self, path: str) -> Optional[str]:
        """Extract resource type from API path"""
        # Remove /api prefix
        if path.startswith("/api/"):
            path = path[5:]
        
        # Split by /
        parts = path.split("/")
        if parts and parts[0]:
            # Capitalize first letter and remove common suffixes
            resource = parts[0].replace("-", "_").title()
            # Handle special cases
            if resource == "Auth":
                return "Authentication"
            elif resource == "Audit_Logs":
                return "AuditLog"
            elif resource == "Mis_Reports":
                return "MISReport"
            elif resource == "Lab_Templates":
                return "LabTemplate"
            elif resource == "Database_Management":
                return "Database"
            else:
                return resource
        return None
    
    def _extract_resource_id_from_path(self, path: str) -> Optional[int]:
        """Extract resource ID from path if it's a numeric segment"""
        parts = path.split("/")
        for part in reversed(parts):
            # Skip common non-ID segments
            if part in ["export", "finalize", "reopen", "regenerate", "edit-details", "detailed"]:
                continue
            try:
                return int(part)
            except ValueError:
                continue
        return None

