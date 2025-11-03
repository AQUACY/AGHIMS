"""
Price list model
"""
from sqlalchemy import Column, Integer, String, Float, Boolean
from app.core.database import Base


class PriceListItem(Base):
    """Price list item model"""
    __tablename__ = "price_list_items"
    
    id = Column(Integer, primary_key=True, index=True)
    item_code = Column(String(50), nullable=False, index=True)
    item_name = Column(String(500), nullable=False)
    category = Column(String(50), nullable=False)  # surgery, procedure, product, consumable, drg
    insured_price = Column(Float, nullable=False, default=0.0)  # NHIA rate
    cash_price = Column(Float, nullable=False, default=0.0)  # Cash price
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<PriceListItem {self.item_code} - {self.item_name}>"

