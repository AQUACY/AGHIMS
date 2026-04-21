"""
Local cache of the installation license (signed document + last online check).
Generation records live only on the separate license portal database.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class AppLicenseState(Base):
    __tablename__ = "app_license_state"

    id = Column(Integer, primary_key=True, default=1)
    license_public_id = Column(String(64), nullable=True, index=True)
    signed_document_json = Column(Text, nullable=True)
    last_online_check_at = Column(DateTime, nullable=True)
    last_online_ok_at = Column(DateTime, nullable=True)
    last_server_valid_until = Column(DateTime, nullable=True)
    # When LICENSE_VERIFY_URL is set: first successful online verify must occur within
    # LICENSE_ONLINE_BOOTSTRAP_MAX_DAYS after this timestamp (set on activate / legacy anchor).
    license_activated_at = Column(DateTime, nullable=True)
    # Monotonic wall-clock checkpoint used to detect large backward clock jumps.
    last_evaluated_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=utcnow_callable, onupdate=utcnow_callable)
