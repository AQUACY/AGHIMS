"""
X-ray Result model
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class XrayResult(Base):
    """X-ray result model"""
    __tablename__ = "xray_results"
    
    id = Column(Integer, primary_key=True, index=True)
    investigation_id = Column(Integer, ForeignKey("investigations.id"), nullable=False, unique=True)
    results_text = Column(Text, nullable=True)  # Text results/findings
    attachment_path = Column(String(500), nullable=True)  # Path to uploaded PDF/image attachment
    entered_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    investigation = relationship("Investigation", back_populates="xray_result", uselist=False)
    
    def __repr__(self):
        return f"<XrayResult {self.investigation_id}>"

