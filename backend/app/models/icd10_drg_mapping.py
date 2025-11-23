"""
ICD-10 to DRG Code Mapping model
"""
from sqlalchemy import Column, Integer, String, Text, Boolean
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class ICD10DRGMapping(Base):
    """ICD-10 code to DRG code mapping model"""
    __tablename__ = "icd10_drg_mappings"
    
    id = Column(Integer, primary_key=True, index=True)
    drg_code = Column(String(50), nullable=False, index=True)  # DRG Code (e.g., ASUR01A)
    drg_description = Column(String(500), nullable=True)  # DRG Description
    icd10_code = Column(String(50), nullable=False, index=True)  # ICD-10 Code (e.g., D34.00)
    icd10_description = Column(Text, nullable=True)  # ICD-10 Description
    notes = Column(Text, nullable=True)
    remarks = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<ICD10DRGMapping {self.drg_code} -> {self.icd10_code}>"

