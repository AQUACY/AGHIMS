"""
Ward Stock model - tracks available inventory stock per ward
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class WardStock(Base):
    """Tracks available stock of products in each ward"""
    __tablename__ = "ward_stocks"
    
    id = Column(Integer, primary_key=True, index=True)
    ward = Column(String(100), nullable=False, index=True)  # Ward name
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=True, index=True)  # Store that provided the items
    product_code = Column(String(50), nullable=False, index=True)  # Product code
    product_name = Column(String(500), nullable=False)  # Product name
    quantity = Column(Float, nullable=False, default=0.0)  # Available quantity
    created_at = Column(DateTime, default=utcnow_callable, nullable=False)
    updated_at = Column(DateTime, default=utcnow_callable, onupdate=utcnow_callable, nullable=False)
    
    # Relationships
    store = relationship("Store", foreign_keys=[store_id])
    
    # Unique constraint: one record per ward-product-store combination
    __table_args__ = (
        Index('idx_ward_stock_unique', 'ward', 'product_code', 'store_id', unique=True),
    )
    
    def __repr__(self):
        return f"<WardStock {self.ward} - {self.product_name}: {self.quantity}>"

