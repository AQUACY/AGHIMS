"""
Pharmacy Requisition model - tracks ward requests for pharmacy items
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.datetime_utils import utcnow_callable
import enum


class RequisitionStatus(str, enum.Enum):
    """Requisition status enum"""
    PENDING = "pending"  # Created by ward, awaiting pharmacy head approval
    APPROVED = "approved"  # Approved by pharmacy head, awaiting store manager fulfillment
    REJECTED = "rejected"  # Rejected by pharmacy head
    PARTIALLY_FULFILLED = "partially_fulfilled"  # Partially fulfilled by store manager
    FULFILLED = "fulfilled"  # Fully fulfilled by store manager
    CANCELLED = "cancelled"  # Cancelled by ward


class PharmacyRequisition(Base):
    """Tracks requisitions from departments to stores"""
    __tablename__ = "pharmacy_requisitions"
    
    id = Column(Integer, primary_key=True, index=True)
    requisition_number = Column(String(50), unique=True, nullable=False, index=True)  # Auto-generated requisition number
    department_id = Column(Integer, ForeignKey("wards.id"), nullable=False, index=True)  # Department requesting
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)  # Store being requested from
    ward = Column(String(100), nullable=True, index=True)  # Legacy field - kept for backward compatibility
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # Department IC/Deputy who created request
    status = Column(SQLEnum(RequisitionStatus), default=RequisitionStatus.PENDING, nullable=False, index=True)
    
    # Approval fields
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Pharmacy Head who approved
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)  # Reason if rejected
    
    # Fulfillment tracking
    fulfilled_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Store Manager who fulfilled
    fulfilled_at = Column(DateTime, nullable=True)
    
    notes = Column(Text, nullable=True)  # Additional notes from requester
    
    created_at = Column(DateTime, default=utcnow_callable, nullable=False, index=True)
    updated_at = Column(DateTime, default=utcnow_callable, onupdate=utcnow_callable, nullable=False)
    
    # Relationships
    department = relationship("Ward", foreign_keys=[department_id])
    store = relationship("Store", foreign_keys=[store_id])
    requester = relationship("User", foreign_keys=[requested_by])
    approver = relationship("User", foreign_keys=[approved_by])
    fulfiller = relationship("User", foreign_keys=[fulfilled_by])
    items = relationship("RequisitionItem", back_populates="requisition", cascade="all, delete-orphan")
    history = relationship("RequisitionHistory", back_populates="requisition", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<PharmacyRequisition {self.requisition_number} - Dept: {self.department_id} - Store: {self.store_id} - {self.status}>"

