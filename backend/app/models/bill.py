"""
Bill and receipt models
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable


class Bill(Base):
    """Bill model"""
    __tablename__ = "bills"
    
    id = Column(Integer, primary_key=True, index=True)
    encounter_id = Column(Integer, ForeignKey("encounters.id"), nullable=False)
    bill_number = Column(String(50), unique=True, index=True, nullable=False)
    total_amount = Column(Float, nullable=False, default=0.0)
    paid_amount = Column(Float, nullable=False, default=0.0)
    is_paid = Column(Boolean, default=False)
    is_insured = Column(Boolean, default=False)  # Whether using insurance pricing
    miscellaneous = Column(Text)  # Additional items
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utcnow_callable)
    paid_at = Column(DateTime, nullable=True)
    
    # Relationships
    encounter = relationship("Encounter", back_populates="bills")
    bill_items = relationship("BillItem", back_populates="bill", cascade="all, delete-orphan")
    receipts = relationship("Receipt", back_populates="bill", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Bill {self.bill_number} - {self.total_amount}>"


class BillItem(Base):
    """Bill item model"""
    __tablename__ = "bill_items"
    
    id = Column(Integer, primary_key=True, index=True)
    bill_id = Column(Integer, ForeignKey("bills.id"), nullable=False)
    item_code = Column(String(50), nullable=False)
    item_name = Column(String(500), nullable=False)
    category = Column(String(50))  # surgery, procedure, product, consumable, drg
    quantity = Column(Float, default=1.0, nullable=False)  # Changed to Float to support fractional quantities (e.g., 6.15 hours)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    created_at = Column(DateTime, default=utcnow_callable)
    
    # Relationships
    bill = relationship("Bill", back_populates="bill_items")
    
    def __repr__(self):
        return f"<BillItem {self.item_name} - {self.total_price}>"


class Receipt(Base):
    """Receipt model"""
    __tablename__ = "receipts"
    
    id = Column(Integer, primary_key=True, index=True)
    bill_id = Column(Integer, ForeignKey("bills.id"), nullable=False)
    receipt_number = Column(String(50), unique=True, index=True, nullable=False)
    amount_paid = Column(Float, nullable=False)
    payment_method = Column(String(50))  # cash, card, mobile_money, etc.
    issued_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    issued_at = Column(DateTime, default=utcnow_callable)
    refunded = Column(Boolean, default=False)  # Whether this receipt has been refunded
    refunded_at = Column(DateTime, nullable=True)
    refunded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    bill = relationship("Bill", back_populates="receipts")
    receipt_items = relationship("ReceiptItem", back_populates="receipt", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Receipt {self.receipt_number} - {self.amount_paid}>"


class ReceiptItem(Base):
    """Receipt item model - tracks which bill items were paid"""
    __tablename__ = "receipt_items"
    
    id = Column(Integer, primary_key=True, index=True)
    receipt_id = Column(Integer, ForeignKey("receipts.id"), nullable=False)
    bill_item_id = Column(Integer, ForeignKey("bill_items.id"), nullable=False)
    amount_paid = Column(Float, nullable=False)  # Amount paid for this specific item
    
    # Relationships
    receipt = relationship("Receipt", back_populates="receipt_items")
    bill_item = relationship("BillItem")
    
    def __repr__(self):
        return f"<ReceiptItem {self.id} - {self.amount_paid}>"

