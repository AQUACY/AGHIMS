"""
Product Price List model
"""
from sqlalchemy import Column, Integer, String, Float, Boolean
from app.core.database import Base


class ProductPrice(Base):
    """Product price list item model (Medications/Products)"""
    __tablename__ = "product_prices"
    
    id = Column(Integer, primary_key=True, index=True)
    sr_no = Column(String(50), nullable=True)
    sub_category_1 = Column(String(100), nullable=True)  # First Sub Category column
    sub_category_2 = Column(String(100), nullable=True)  # Second Sub Category column
    product_id = Column(String(100), nullable=True)
    product_name = Column(String(500), nullable=False)  # Full product name as provided
    medication_code = Column(String(50), nullable=False, index=True)  # Extracted medication code (G-DRG code)
    g_drg_code = Column(String(50), nullable=True)  # Backward compatibility: same as medication_code for old table structure
    formulation = Column(String(200), nullable=True)
    strength = Column(String(200), nullable=True)
    base_rate = Column(Float, nullable=False, default=0.0)  # Cash price
    nhia_app = Column(Float, nullable=True)  # NHIA Approved price (insured price)
    claim_amount = Column(Float, nullable=True)  # Claim Amount column
    nhia_claim = Column(String(100), nullable=True)  # NHIA Claim column
    bill_effective = Column(String(100), nullable=True)  # Bill Effective column
    insurance_covered = Column(String(10), nullable=True, default="yes")  # "yes" or "no" - whether product is covered by insurance
    is_active = Column(Boolean, default=True)
    
    # Legacy fields (for backward compatibility with old table structure)
    service_ty = Column(String(100), nullable=True)
    service_type = Column(String(100), nullable=True)
    service_id = Column(String(100), nullable=True)
    service_name = Column(String(500), nullable=True)
    nhia_claim_co_payment = Column(Float, nullable=True)
    clinic_bill_effective = Column(String(100), nullable=True)
    
    def __repr__(self):
        return f"<ProductPrice {self.medication_code} - {self.product_name}>"

