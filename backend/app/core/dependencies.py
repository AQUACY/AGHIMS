"""
Common dependencies for API routes
"""
from typing import Generator, List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from app.core.database import get_db
from app.core.security import decode_access_token
from app.core.config import settings
from app.models.user import User
from app.models.module_settings import ModuleSettings
from app.core.audit import is_super_admin

# Initialize OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user from JWT token
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_access_token(token)
        if payload is None:
            raise credentials_exception
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user


def require_role(allowed_roles: List[str]):
    """
    Dependency factory to require specific roles
    Checks both primary role and additional roles assigned to the user
    """
    def role_checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        # Check primary role
        if current_user.role in allowed_roles:
            return current_user
        
        # Check additional roles (load relationship if not already loaded)
        from sqlalchemy.orm import joinedload
        user_with_roles = db.query(User).options(joinedload(User.additional_roles)).filter(User.id == current_user.id).first()
        
        if user_with_roles:
            # Check if any additional role matches
            user_roles = [ur.role for ur in user_with_roles.additional_roles]
            if any(role in allowed_roles for role in user_roles):
                return current_user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Required roles: {', '.join(allowed_roles)}"
        )
    
    return role_checker


def require_admin_or_super_admin():
    """
    Admin (primary or additional role) or super admin may manage facility-wide configuration.
    """
    def checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if is_super_admin(current_user):
            return current_user
        if current_user.role == "Admin":
            return current_user
        from sqlalchemy.orm import joinedload
        user_with_roles = (
            db.query(User).options(joinedload(User.additional_roles)).filter(User.id == current_user.id).first()
        )
        if user_with_roles and any(ur.role == "Admin" for ur in user_with_roles.additional_roles):
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin or Super Admin required.",
        )

    return checker


def require_module_permission(module_key: str, permission: str = "read"):
    """
    Dependency factory to require module permission
    Checks if module is active and user has the required permission (read, create, update, delete)
    
    Rules:
    - If module is inactive: Block create/update/delete, but allow read if allow_read is True
    - If module is active: Check the specific permission flag (allow_read, allow_create, etc.)
    
    Args:
        module_key: The module key to check (e.g., 'encounters', 'patients', 'claims')
        permission: The permission to check ('read', 'create', 'update', 'delete')
    """
    def permission_checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        # Get module settings
        module = db.query(ModuleSettings).filter(ModuleSettings.module_key == module_key).first()
        
        # If module doesn't exist, allow access (backward compatibility)
        if not module:
            return current_user
        
        # For create/update/delete operations, always block if module is inactive
        # (users cannot create/update/delete even if permissions are enabled when module is inactive)
        if permission in ["create", "update", "delete"]:
            if not module.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"The {module.module_name} module is currently inactive. You cannot {permission} data in this module."
                )
            # If module is active, check the specific permission flag
            permission_map = {
                "create": module.allow_create,
                "update": module.allow_update,
                "delete": module.allow_delete
            }
            if not permission_map[permission]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"You do not have permission to {permission} in the {module.module_name} module"
                )
        elif permission == "read":
            # For read operations:
            # - If module is inactive but allow_read is True: allow read access
            # - If module is active: check allow_read flag
            if not module.is_active:
                # Module is inactive - only allow read if allow_read is enabled
                if not module.allow_read:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"The {module.module_name} module is currently inactive"
                    )
            else:
                # Module is active - check allow_read flag
                if not module.allow_read:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"You do not have permission to read in the {module.module_name} module"
                    )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Invalid permission type: {permission}"
            )
        
        return current_user
    
    return permission_checker

