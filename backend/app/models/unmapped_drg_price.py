"""
Unmapped DRG Price List model
"""
from sqlalchemy import Column, Integer, String, Float, Boolean
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class UnmappedDRGPrice(Base):
    """Unmapped DRG price list item model"""
    __tablename__ = "unmapped_drg_prices"
    
    id = Column(Integer, primary_key=True, index=True)
    sr_no = Column(String(50), nullable=True)
    g_drg_code = Column(String(50), nullable=False, index=True)
    service_ty = Column(String(100), nullable=True)  # First Service Ty column
    service_type = Column(String(100), nullable=True, index=True)  # Department/Clinic (used as category)
    service_id = Column(String(100), nullable=True)
    service_name = Column(String(500), nullable=False)
    base_rate = Column(Float, nullable=False, default=0.0)  # Cash price
    nhia_app = Column(Float, nullable=True)  # NHIA Approved price (insured price)
    nhia_claim_co_payment = Column(Float, nullable=True)
    clinic_bill_effective = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<UnmappedDRGPrice {self.g_drg_code} - {self.service_name}>"

