"""
Lab Result model
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class LabResult(Base):
    """Lab result model"""
    __tablename__ = "lab_results"
    
    id = Column(Integer, primary_key=True, index=True)
    investigation_id = Column(Integer, ForeignKey("investigations.id"), nullable=False, unique=True)
    template_id = Column(Integer, ForeignKey("lab_result_templates.id"), nullable=True)  # Link to template if used
    results_text = Column(Text, nullable=True)  # Text results from analyzer (for non-template results)
    template_data = Column(JSON, nullable=True)  # Structured template data (for template-based results)
    # Structure: {
    #   "field_values": {
    #     "WBC": 4.79,
    #     "RBC": 3.61,
    #     ...
    #   },
    #   "messages": {
    #     "WBC IP Message": "...",
    #     "RBC IP Message": "...",
    #     ...
    #   },
    #   "validated_by": "Dr. Name",
    #   "sample_no": "11/0788"
    # }
    attachment_path = Column(String(500), nullable=True)  # Path to uploaded PDF/attachment
    entered_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # User who first entered the result
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # User who last updated the result
    created_at = Column(DateTime, default=utcnow_callable)
    updated_at = Column(DateTime, default=utcnow_callable, onupdate=utcnow_callable)
    
    # Relationships
    investigation = relationship("Investigation", back_populates="lab_result", uselist=False)
    template = relationship("LabResultTemplate", foreign_keys=[template_id])
    
    def __repr__(self):
        return f"<LabResult {self.investigation_id}>"

