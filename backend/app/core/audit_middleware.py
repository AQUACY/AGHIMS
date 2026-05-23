"""
Middleware for automatic audit logging of all API endpoints
"""
from typing import Optional, Callable
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.audit import create_audit_log, get_client_ip, is_super_admin
from app.core.audit_context import build_platform_audit_summary
from app.models.user import User


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that automatically logs API endpoint calls to the audit trail.
    Logs POST, PUT, PATCH, DELETE (not GET) to limit database growth.
    Summaries use patient card numbers, insurance IDs, bill numbers, etc. — not DB IDs.
    Login is logged separately in auth.py.
    """

    EXCLUDED_PATHS = {
        "/",
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/api/auth/login",
        "/api/uploads",
    }

    PUBLIC_PATHS = {
        "/api/auth/login",
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in self.EXCLUDED_PATHS or request.url.path.startswith(
            "/api/uploads"
        ):
            return await call_next(request)

        if request.method == "OPTIONS":
            return await call_next(request)

        if request.method == "GET":
            return await call_next(request)

        db_gen = get_db()
        db: Session = next(db_gen)

        try:
            user: Optional[User] = None
            try:
                auth_header = request.headers.get("Authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    token = auth_header.split(" ")[1]
                    from app.core.security import decode_access_token
                    from jose import JWTError

                    try:
                        payload = decode_access_token(token)
                        if payload:
                            user_id = payload.get("sub")
                            if user_id:
                                user = (
                                    db.query(User)
                                    .filter(User.id == int(user_id))
                                    .first()
                                )
                    except (JWTError, ValueError, TypeError):
                        pass
            except Exception:
                pass

            action = self._get_action_from_method(request.method)
            resource_type = self._get_resource_type_from_path(request.url.path)
            resource_id = self._extract_resource_id_from_path(request.url.path)
            query_params = dict(request.query_params)
            details = {
                "endpoint": request.url.path,
                "method": request.method,
                "query_params": query_params if query_params else None,
            }

            response = await call_next(request)

            summary = getattr(request.state, "audit_summary", None)
            if not summary:
                summary = build_platform_audit_summary(
                    db,
                    request.url.path,
                    request.method,
                    resource_type,
                    action,
                    resource_id,
                    query_params,
                )

            if user and not is_super_admin(user):
                ip_address = get_client_ip(request)
                try:
                    create_audit_log(
                        db=db,
                        user=user,
                        action=action,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        details=details,
                        summary=summary,
                        ip_address=ip_address,
                        endpoint_path=request.url.path,
                        http_method=request.method,
                    )
                except Exception as e:
                    print(f"Warning: Failed to create audit log: {e}")

            return response

        except Exception as e:
            print(f"Error in audit middleware: {e}")
            try:
                return await call_next(request)
            except Exception as e2:
                raise e2
        finally:
            try:
                db.close()
            except Exception:
                pass

    def _get_action_from_method(self, method: str) -> str:
        method_upper = method.upper()
        if method_upper == "GET":
            return "VIEW"
        if method_upper == "POST":
            return "CREATE"
        if method_upper in ("PUT", "PATCH"):
            return "UPDATE"
        if method_upper == "DELETE":
            return "DELETE"
        return method_upper

    def _get_resource_type_from_path(self, path: str) -> Optional[str]:
        if path.startswith("/api/"):
            path = path[5:]

        parts = path.split("/")
        if parts and parts[0]:
            resource = parts[0].replace("-", "_").title()
            mapping = {
                "Auth": "Authentication",
                "Audit_Logs": "AuditLog",
                "Mis_Reports": "MISReport",
                "Lab_Templates": "LabTemplate",
                "Database_Management": "Database",
                "Companion_Visits": "CompanionVisit",
                "Pharmacy_Requisitions": "PharmacyRequisition",
                "Price_List": "PriceList",
                "Module_Settings": "ModuleSettings",
                "Facility_Settings": "FacilitySettings",
            }
            return mapping.get(resource, resource)
        return None

    def _extract_resource_id_from_path(self, path: str) -> Optional[int]:
        from app.core.audit_context import extract_path_resource_id

        return extract_path_resource_id(path)
