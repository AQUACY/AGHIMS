"""
Store Stock model - tracks stock items in stores with batch numbers and expiry dates
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean, Enum as SQLEnum, Date, Index
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable
import enum


class StockStatus(str, enum.Enum):
    """Stock approval status enum"""
    PENDING = "PENDING"  # Created by store manager, awaiting department head approval
    APPROVED = "APPROVED"  # Approved by department head, available for requisitions
    REJECTED = "REJECTED"  # Rejected by department head
    EXPIRED = "EXPIRED"  # Stock has expired (can be set automatically or manually)


class StoreStock(Base):
    """Tracks stock items in stores with batch numbers, expiry dates, and approval workflow"""
    __tablename__ = "store_stocks"
    
    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    product_code = Column(String(50), nullable=False, index=True)  # Product code from ProductPrice
    product_name = Column(String(500), nullable=False)  # Product name
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False, index=True)
    batch_number = Column(String(100), nullable=False, index=True)  # Batch/lot number
    expiry_date = Column(Date, nullable=False, index=True)  # Expiry date
    quantity = Column(Float, nullable=False, default=0.0)  # Quantity in stock
    unit_price = Column(Float, nullable=True)  # Optional: purchase price per unit
    receipt_number = Column(String(100), nullable=True)  # Receipt/invoice number from vendor
    notes = Column(Text, nullable=True)  # Additional notes
    
    # Approval workflow
    status = Column(SQLEnum(StockStatus, values_callable=lambda x: [e.value for e in x]), default=StockStatus.PENDING, nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # Store manager who added stock
    created_at = Column(DateTime, default=utcnow_callable, nullable=False, index=True)
    
    # Approval fields
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Department head who approved
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)  # Reason if rejected
    
    updated_at = Column(DateTime, default=utcnow_callable, onupdate=utcnow_callable, nullable=False)
    
    # Relationships
    store = relationship("Store", foreign_keys=[store_id])
    vendor = relationship("Vendor", back_populates="store_stocks")
    creator = relationship("User", foreign_keys=[created_by])
    approver = relationship("User", foreign_keys=[approved_by])
    
    # Unique constraint: one record per store-product-batch combination
    __table_args__ = (
        Index('idx_store_stock_unique', 'store_id', 'product_code', 'batch_number', unique=True),
    )
    
    def __repr__(self):
        return f"<StoreStock {self.product_name} - Batch: {self.batch_number} - Qty: {self.quantity} - {self.status}>"

