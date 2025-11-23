"""
Lab Result Template model - stores templates for lab procedures with reference ranges
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class LabResultTemplate(Base):
    """Lab result template model"""
    __tablename__ = "lab_result_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    g_drg_code = Column(String(50), nullable=True, index=True)  # G-DRG code (optional, for reference)
    procedure_name = Column(String(500), nullable=False, index=True)  # Procedure name (e.g., "Full Blood Count") - PRIMARY MATCHING FIELD
    template_name = Column(String(200), nullable=False)  # Template name/identifier (e.g., "FBC")
    
    # Template structure stored as JSON
    # Structure: {
    #   "fields": [
    #     {
    #       "name": "WBC",
    #       "label": "White Blood Cell Count",
    #       "type": "numeric",
    #       "unit": "10^3/uL",
    #       "reference_min": 3.00,
    #       "reference_max": 15.00,
    #       "order": 1,
    #       "group": "Basic Parameters"
    #     },
    #     ...
    #   ],
    #   "message_fields": [
    #     {"name": "WBC IP Message", "type": "text", "order": 1},
    #     ...
    #   ],
    #   "patient_fields": ["age", "ward", "doctor"]  # Optional patient fields to display
    # }
    template_structure = Column(JSON, nullable=False)
    
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow_callable)
    updated_at = Column(DateTime, default=utcnow_callable, onupdate=utcnow_callable)
    is_active = Column(Integer, default=1)  # 1 = active, 0 = inactive
    
    def __repr__(self):
        return f"<LabResultTemplate {self.template_name} - {self.procedure_name}>"

