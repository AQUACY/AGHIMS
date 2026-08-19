"""
Per-user brand / theme color preferences.

Facility name and code stay on facility_settings (shared). Colors are personal
so one user's theme does not change another user's UI.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class UserBrandPreferences(Base):
    __tablename__ = "user_brand_preferences"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_brand_preferences_user_id"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    # Optional brand colors (#RRGGBB). Null = use app theme defaults.
    bg_color_light = Column(String(7), nullable=True)
    bg_color_dark = Column(String(7), nullable=True)
    accent_color = Column(String(7), nullable=True)
    text_color_light = Column(String(7), nullable=True)
    text_color_dark = Column(String(7), nullable=True)
    updated_at = Column(DateTime, default=utcnow_callable, onupdate=utcnow_callable)

    user = relationship("User", backref="brand_preferences", uselist=False)

    def __repr__(self):
        return f"<UserBrandPreferences user_id={self.user_id}>"
