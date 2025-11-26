"""
Consultation Template model - stores templates for prescriptions and investigations
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable
import json


class ConsultationTemplate(Base):
    """Stores templates for prescriptions and investigations that can be reused"""
    __tablename__ = "consultation_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)  # Template name
    description = Column(Text, nullable=True)  # Optional description
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # User who created the template
    is_shared = Column(Boolean, default=False, nullable=False)  # Whether template is shared with all users
    prescriptions_data = Column(Text, nullable=True)  # JSON string of prescriptions
    investigations_data = Column(Text, nullable=True)  # JSON string of investigations
    created_at = Column(DateTime, default=utcnow_callable, nullable=False)
    updated_at = Column(DateTime, default=utcnow_callable, onupdate=utcnow_callable)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])

    def get_prescriptions(self):
        """Parse and return prescriptions data as list"""
        if not self.prescriptions_data:
            return []
        try:
            return json.loads(self.prescriptions_data)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_prescriptions(self, prescriptions_list):
        """Set prescriptions data from list"""
        self.prescriptions_data = json.dumps(prescriptions_list) if prescriptions_list else None

    def get_investigations(self):
        """Parse and return investigations data as list"""
        if not self.investigations_data:
            return []
        try:
            return json.loads(self.investigations_data)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_investigations(self, investigations_list):
        """Set investigations data from list"""
        self.investigations_data = json.dumps(investigations_list) if investigations_list else None

    def __repr__(self):
        return f"<ConsultationTemplate {self.name} - Created by {self.created_by}>"

