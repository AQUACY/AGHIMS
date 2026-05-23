"""
Module Settings API endpoints - Manage feature flags for system modules
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, field_serializer, model_serializer
from datetime import datetime
from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.user import User
from app.models.module_settings import ModuleSettings

router = APIRouter(prefix="/module-settings", tags=["module-settings"])

MODE_MODULE_DEFAULTS = {
    "mode_hms": {
        "module_name": "HMS Mode",
        "description": "Facility switch for Hospital Management System mode availability",
        "category": "core",
        "display_order": 1001,
    },
    "mode_companion": {
        "module_name": "Companion Mode",
        "description": "Facility switch for Companion mode availability",
        "category": "core",
        "display_order": 1002,
    },
    "mode_inventory": {
        "module_name": "Inventory Mode",
        "description": "Facility switch for Inventory mode availability",
        "category": "core",
        "display_order": 1003,
    },
    "ghims": {
        "module_name": "GHIMS Card Numbers",
        "description": "When enabled, new patients use manual GHIMS card numbers (e.g. E-0032-26050735) instead of auto-generated HMS cards.",
        "category": "core",
        "display_order": 1004,
    },
}


def ensure_bootstrap_modules(db: Session) -> None:
    """Create facility-mode and GHIMS module rows if missing (e.g. after deploy without init script)."""
    for module_key, defaults in MODE_MODULE_DEFAULTS.items():
        existing = (
            db.query(ModuleSettings)
            .filter(ModuleSettings.module_key == module_key)
            .first()
        )
        if existing:
            continue
        db.add(
            ModuleSettings(
                module_key=module_key,
                module_name=defaults["module_name"],
                description=defaults["description"],
                is_active=False if module_key == "ghims" else True,
                allow_read=True,
                allow_create=True,
                allow_update=True,
                allow_delete=True,
                category=defaults["category"],
                display_order=defaults["display_order"],
            )
        )
    db.commit()


class ModuleSettingsResponse(BaseModel):
    """Response model for module settings"""
    id: int
    module_key: str
    module_name: str
    description: Optional[str] = None
    is_active: bool
    allow_read: bool
    allow_create: bool
    allow_update: bool
    allow_delete: bool
    category: Optional[str] = None
    display_order: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    class Config:
        from_attributes = True


class ModuleSettingsUpdate(BaseModel):
    """Update model for module settings"""
    is_active: Optional[bool] = None
    allow_read: Optional[bool] = None
    allow_create: Optional[bool] = None
    allow_update: Optional[bool] = None
    allow_delete: Optional[bool] = None
    display_order: Optional[int] = None


class ModuleStatusResponse(BaseModel):
    """Response model for checking module status"""
    module_key: str
    is_active: bool
    allow_read: bool
    allow_create: bool
    allow_update: bool
    allow_delete: bool


@router.get("/", response_model=List[ModuleSettingsResponse])
def get_all_module_settings(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Get all module settings, optionally filtered by category"""
    ensure_bootstrap_modules(db)
    query = db.query(ModuleSettings)
    
    if category:
        query = query.filter(ModuleSettings.category == category)
    
    modules = query.order_by(ModuleSettings.display_order, ModuleSettings.module_name).all()
    
    # Convert to response format with serialized datetimes
    result = []
    for module in modules:
        result.append(ModuleSettingsResponse(
            id=module.id,
            module_key=module.module_key,
            module_name=module.module_name,
            description=module.description,
            is_active=module.is_active,
            allow_read=module.allow_read,
            allow_create=module.allow_create,
            allow_update=module.allow_update,
            allow_delete=module.allow_delete,
            category=module.category,
            display_order=module.display_order,
            created_at=module.created_at.isoformat() if module.created_at else None,
            updated_at=module.updated_at.isoformat() if module.updated_at else None
        ))
    return result


@router.get("/{module_key}", response_model=ModuleSettingsResponse)
def get_module_setting(
    module_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Get a specific module setting by key"""
    module = db.query(ModuleSettings).filter(ModuleSettings.module_key == module_key).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module setting not found")
    
    return ModuleSettingsResponse(
        id=module.id,
        module_key=module.module_key,
        module_name=module.module_name,
        description=module.description,
        is_active=module.is_active,
        allow_read=module.allow_read,
        allow_create=module.allow_create,
        allow_update=module.allow_update,
        allow_delete=module.allow_delete,
        category=module.category,
        display_order=module.display_order,
        created_at=module.created_at.isoformat() if module.created_at else None,
        updated_at=module.updated_at.isoformat() if module.updated_at else None
    )


@router.get("/status/batch", response_model=dict)
def get_module_status_batch(
    module_keys: str,  # Comma-separated list of module keys
    db: Session = Depends(get_db)
):
    """Get status for multiple modules at once (public endpoint)"""
    keys = [k.strip() for k in module_keys.split(",") if k.strip()]
    if not keys:
        return {}
    
    modules = db.query(ModuleSettings).filter(ModuleSettings.module_key.in_(keys)).all()
    module_dict = {m.module_key: m for m in modules}
    
    result = {}
    for key in keys:
        module = module_dict.get(key)
        if module:
            result[key] = {
                "is_active": module.is_active,
                "allow_read": module.allow_read,
                "allow_create": module.allow_create,
                "allow_update": module.allow_update,
                "allow_delete": module.allow_delete
            }
        else:
            # Default to active if module not found (backward compatibility)
            default_active = False if key == "ghims" else True
            result[key] = {
                "is_active": default_active,
                "allow_read": True,
                "allow_create": True,
                "allow_update": True,
                "allow_delete": True
            }
    
    return result


@router.get("/status/{module_key}", response_model=ModuleStatusResponse)
def get_module_status(
    module_key: str,
    db: Session = Depends(get_db)
):
    """Get module status (public endpoint - no auth required for checking status)"""
    module = db.query(ModuleSettings).filter(ModuleSettings.module_key == module_key).first()
    if not module:
        default_active = False if module_key == "ghims" else True
        return ModuleStatusResponse(
            module_key=module_key,
            is_active=default_active,
            allow_read=True,
            allow_create=True,
            allow_update=True,
            allow_delete=True
        )

    return ModuleStatusResponse(
        module_key=module.module_key,
        is_active=module.is_active,
        allow_read=module.allow_read,
        allow_create=module.allow_create,
        allow_update=module.allow_update,
        allow_delete=module.allow_delete
    )


@router.put("/{module_key}", response_model=ModuleSettingsResponse)
def update_module_setting(
    module_key: str,
    update_data: ModuleSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Update a module setting"""
    module = db.query(ModuleSettings).filter(ModuleSettings.module_key == module_key).first()
    if not module:
        # Auto-create known app-mode module keys so facility mode setup works out-of-the-box.
        if module_key in MODE_MODULE_DEFAULTS:
            defaults = MODE_MODULE_DEFAULTS[module_key]
            module = ModuleSettings(
                module_key=module_key,
                module_name=defaults["module_name"],
                description=defaults["description"],
                is_active=False if module_key == "ghims" else True,
                allow_read=True,
                allow_create=True,
                allow_update=True,
                allow_delete=True,
                category=defaults["category"],
                display_order=defaults["display_order"],
            )
            db.add(module)
            db.flush()
        else:
            raise HTTPException(status_code=404, detail="Module setting not found")
    
    # Update fields if provided
    if update_data.is_active is not None:
        module.is_active = update_data.is_active
    if update_data.allow_read is not None:
        module.allow_read = update_data.allow_read
    if update_data.allow_create is not None:
        module.allow_create = update_data.allow_create
    if update_data.allow_update is not None:
        module.allow_update = update_data.allow_update
    if update_data.allow_delete is not None:
        module.allow_delete = update_data.allow_delete
    if update_data.display_order is not None:
        module.display_order = update_data.display_order
    
    db.commit()
    db.refresh(module)
    
    return ModuleSettingsResponse(
        id=module.id,
        module_key=module.module_key,
        module_name=module.module_name,
        description=module.description,
        is_active=module.is_active,
        allow_read=module.allow_read,
        allow_create=module.allow_create,
        allow_update=module.allow_update,
        allow_delete=module.allow_delete,
        category=module.category,
        display_order=module.display_order,
        created_at=module.created_at.isoformat() if module.created_at else None,
        updated_at=module.updated_at.isoformat() if module.updated_at else None
    )


@router.put("/{module_key}/toggle", response_model=ModuleSettingsResponse)
def toggle_module(
    module_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Quick toggle to enable/disable a module"""
    module = db.query(ModuleSettings).filter(ModuleSettings.module_key == module_key).first()
    if not module:
        # Auto-create known app-mode module keys so toggles work even before seed scripts run.
        if module_key in MODE_MODULE_DEFAULTS:
            defaults = MODE_MODULE_DEFAULTS[module_key]
            module = ModuleSettings(
                module_key=module_key,
                module_name=defaults["module_name"],
                description=defaults["description"],
                is_active=False if module_key == "ghims" else True,
                allow_read=True,
                allow_create=True,
                allow_update=True,
                allow_delete=True,
                category=defaults["category"],
                display_order=defaults["display_order"],
            )
            db.add(module)
            db.flush()
        else:
            raise HTTPException(status_code=404, detail="Module setting not found")
    
    module.is_active = not module.is_active
    db.commit()
    db.refresh(module)
    
    return ModuleSettingsResponse(
        id=module.id,
        module_key=module.module_key,
        module_name=module.module_name,
        description=module.description,
        is_active=module.is_active,
        allow_read=module.allow_read,
        allow_create=module.allow_create,
        allow_update=module.allow_update,
        allow_delete=module.allow_delete,
        category=module.category,
        display_order=module.display_order,
        created_at=module.created_at.isoformat() if module.created_at else None,
        updated_at=module.updated_at.isoformat() if module.updated_at else None
    )


@router.put("/{module_key}/set-permissions", response_model=ModuleSettingsResponse)
def set_module_permissions(
    module_key: str,
    permissions: ModuleSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Set all permissions for a module at once"""
    module = db.query(ModuleSettings).filter(ModuleSettings.module_key == module_key).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module setting not found")
    
    if permissions.allow_read is not None:
        module.allow_read = permissions.allow_read
    if permissions.allow_create is not None:
        module.allow_create = permissions.allow_create
    if permissions.allow_update is not None:
        module.allow_update = permissions.allow_update
    if permissions.allow_delete is not None:
        module.allow_delete = permissions.allow_delete
    
    db.commit()
    db.refresh(module)
    
    return ModuleSettingsResponse(
        id=module.id,
        module_key=module.module_key,
        module_name=module.module_name,
        description=module.description,
        is_active=module.is_active,
        allow_read=module.allow_read,
        allow_create=module.allow_create,
        allow_update=module.allow_update,
        allow_delete=module.allow_delete,
        category=module.category,
        display_order=module.display_order,
        created_at=module.created_at.isoformat() if module.created_at else None,
        updated_at=module.updated_at.isoformat() if module.updated_at else None
    )
