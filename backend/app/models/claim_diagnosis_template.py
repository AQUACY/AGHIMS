"""
Claim diagnosis templates — reusable investigations + medicines for a principal diagnosis.
Example: Malaria → B/F investigation + Artesunate drug(s).
"""
from __future__ import annotations

import json
from typing import Any, List, Optional

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class ClaimDiagnosisTemplate(Base):
    """User/facility templates that auto-fill claim investigations and medicines."""

    __tablename__ = "claim_diagnosis_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)  # e.g. "Malaria OPD"
    description = Column(Text, nullable=True)

    # Matching against principal diagnosis
    match_icd10 = Column(String(50), nullable=True, index=True)
    match_diagnosis = Column(String(500), nullable=True)  # e.g. "Malaria"
    match_gdrg_prefix = Column(String(20), nullable=True)  # e.g. first 4 of G-DRG
    match_keywords = Column(String(500), nullable=True)  # comma-separated keywords

    # Snapshot of the diagnosis this template was built from (optional)
    sample_icd10 = Column(String(50), nullable=True)
    sample_diagnosis = Column(String(500), nullable=True)
    sample_gdrg = Column(String(50), nullable=True)

    investigations_data = Column(Text, nullable=True)  # JSON list
    medicines_data = Column(Text, nullable=True)  # JSON list

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    is_shared = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow_callable, nullable=False)
    updated_at = Column(DateTime, default=utcnow_callable, onupdate=utcnow_callable)

    creator = relationship("User", foreign_keys=[created_by])

    def get_investigations(self) -> List[Any]:
        if not self.investigations_data:
            return []
        try:
            data = json.loads(self.investigations_data)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, TypeError):
            return []

    def set_investigations(self, items: Optional[List[Any]]) -> None:
        self.investigations_data = json.dumps(items) if items else None

    def get_medicines(self) -> List[Any]:
        if not self.medicines_data:
            return []
        try:
            data = json.loads(self.medicines_data)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, TypeError):
            return []

    def set_medicines(self, items: Optional[List[Any]]) -> None:
        self.medicines_data = json.dumps(items) if items else None

    def __repr__(self) -> str:
        return f"<ClaimDiagnosisTemplate {self.id} {self.name}>"
