"""
Blood Transfusion Request model - tracks blood transfusion requests
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class BloodTransfusionRequest(Base):
    """Stores blood transfusion requests for patients"""
    __tablename__ = "blood_transfusion_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    ward_admission_id = Column(Integer, ForeignKey("ward_admissions.id"), nullable=False)
    encounter_id = Column(Integer, ForeignKey("encounters.id"), nullable=False)
    transfusion_type_id = Column(Integer, ForeignKey("blood_transfusion_types.id"), nullable=False)
    quantity = Column(Float, nullable=False, default=1.0)  # Number of units requested
    request_reason = Column(Text, nullable=True)  # Reason for blood request
    status = Column(String(20), default="pending", nullable=False)  # pending, accepted, fulfilled, returned, cancelled
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # User who requested
    accepted_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Lab user who accepted
    fulfilled_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Lab user who fulfilled
    returned_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Admin who returned
    bill_item_id = Column(Integer, ForeignKey("bill_items.id"), nullable=True)  # Bill item created when accepted
    return_bill_item_id = Column(Integer, ForeignKey("bill_items.id"), nullable=True)  # Bill item created when returned
    requested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    accepted_at = Column(DateTime, nullable=True)  # When request was accepted
    fulfilled_at = Column(DateTime, nullable=True)  # When blood was fulfilled
    returned_at = Column(DateTime, nullable=True)  # When blood was returned
    cancelled_at = Column(DateTime, nullable=True)  # When request was cancelled
    cancellation_reason = Column(Text, nullable=True)  # Reason for cancellation
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    ward_admission = relationship("WardAdmission", back_populates="blood_transfusion_requests")
    encounter = relationship("Encounter")
    transfusion_type = relationship("BloodTransfusionType", back_populates="requests")
    requester = relationship("User", foreign_keys=[requested_by])
    accepter = relationship("User", foreign_keys=[accepted_by])
    fulfiller = relationship("User", foreign_keys=[fulfilled_by])
    returner = relationship("User", foreign_keys=[returned_by])
    bill_item = relationship("BillItem", foreign_keys=[bill_item_id])
    return_bill_item = relationship("BillItem", foreign_keys=[return_bill_item_id])
    
    def __repr__(self):
        return f"<BloodTransfusionRequest {self.id} - {self.status}>"

