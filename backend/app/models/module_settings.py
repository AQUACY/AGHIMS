"""
Module Settings model - Controls which modules are active/inactive in the system
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class ModuleSettings(Base):
    """Module settings model for feature flags"""
    __tablename__ = "module_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    module_key = Column(String(100), unique=True, nullable=False, index=True)  # e.g., 'patients', 'billing', 'claims'
    module_name = Column(String(200), nullable=False)  # Display name: 'Patient Management', 'Billing', 'Claims'
    description = Column(Text, nullable=True)  # Description of what the module does
    is_active = Column(Boolean, default=True, nullable=False)  # Whether module is enabled
    allow_read = Column(Boolean, default=True, nullable=False)  # Allow viewing data (even when inactive)
    allow_create = Column(Boolean, default=True, nullable=False)  # Allow creating new records
    allow_update = Column(Boolean, default=True, nullable=False)  # Allow updating records
    allow_delete = Column(Boolean, default=True, nullable=False)  # Allow deleting records
    category = Column(String(50), nullable=True)  # Category: 'core', 'clinical', 'administrative', 'reports'
    display_order = Column(Integer, default=0)  # Order for display in admin panel
    created_at = Column(DateTime, default=utcnow_callable)
    updated_at = Column(DateTime, default=utcnow_callable, onupdate=utcnow_callable)
    
    def __repr__(self):
        return f"<ModuleSettings {self.module_key} - Active: {self.is_active}>"
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'module_key': self.module_key,
            'module_name': self.module_name,
            'description': self.description,
            'is_active': self.is_active,
            'allow_read': self.allow_read,
            'allow_create': self.allow_create,
            'allow_update': self.allow_update,
            'allow_delete': self.allow_delete,
            'category': self.category,
            'display_order': self.display_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
