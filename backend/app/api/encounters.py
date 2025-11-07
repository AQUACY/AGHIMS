"""
Encounter management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from app.core.database import get_db
from app.core.dependencies import require_role, get_current_user
from app.models.user import User
from app.models.encounter import Encounter, EncounterStatus

router = APIRouter(prefix="/encounters", tags=["encounters"])


class EncounterResponse(BaseModel):
    """Encounter response model"""
    id: int
    patient_id: int
    ccc_number: Optional[str]
    status: str
    department: str
    procedure_g_drg_code: Optional[str] = None
    procedure_name: Optional[str] = None
    created_at: datetime
    archived: bool = False
    
    class Config:
        from_attributes = True


class EncounterUpdate(BaseModel):
    """Encounter update model"""
    department: Optional[str] = None
    ccc_number: Optional[str] = None
    status: Optional[str] = None
    procedure_g_drg_code: Optional[str] = None
    procedure_name: Optional[str] = None


@router.get("/{encounter_id}", response_model=EncounterResponse)
def get_encounter(
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get encounter by ID"""
    encounter = db.query(Encounter).filter(Encounter.id == encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    return encounter


@router.get("/{encounter_id}/bill-total")
def get_encounter_bill_total(
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get total bill amount for an encounter"""
    from app.models.bill import Bill
    
    bills = db.query(Bill).filter(Bill.encounter_id == encounter_id).all()
    total_amount = sum(bill.total_amount for bill in bills)
    
    return {
        "encounter_id": encounter_id,
        "total_bill_amount": total_amount,
        "bill_count": len(bills)
    }


@router.put("/{encounter_id}/status")
def update_encounter_status(
    encounter_id: int,
    new_status: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Doctor", "PA", "Records", "Admin"]))
):
    """Update encounter status"""
    from app.models.bill import Bill
    
    encounter = db.query(Encounter).filter(Encounter.id == encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Validate status transition
    valid_transitions = {
        "draft": ["in_consultation", "awaiting_services", "finalized"],  # Allow draft to go to awaiting_services
        "in_consultation": ["draft", "awaiting_services", "finalized"],
        "awaiting_services": ["draft", "in_consultation", "awaiting_services", "finalized"],
        "finalized": ["draft", "in_consultation", "awaiting_services", "finalized"]  # Cannot transition from finalized
    }
    
    if new_status not in valid_transitions.get(encounter.status, []):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from {encounter.status} to {new_status}"
        )
    
    # If finalizing, require diagnosis, follow-up date, outcome, and payment
    if new_status == "finalized":
        from app.models.consultation_notes import ConsultationNotes
        from app.models.diagnosis import Diagnosis
        from app.models.bill import Bill
        
        # Require at least one diagnosis
        diagnoses = db.query(Diagnosis).filter(Diagnosis.encounter_id == encounter_id).all()
        if not diagnoses or len(diagnoses) == 0:
            raise HTTPException(status_code=400, detail="Cannot finalize encounter. At least one diagnosis is required.")
        
        # Require consultation notes with outcome and follow-up date
        notes = db.query(ConsultationNotes).filter(ConsultationNotes.encounter_id == encounter_id).first()
        if not notes:
            raise HTTPException(status_code=400, detail="Cannot finalize encounter. Consultation notes are required.")
        
        if not (notes.outcome and notes.outcome.strip()):
            raise HTTPException(status_code=400, detail="Cannot finalize encounter. Consultation outcome is required.")
        
        if not notes.follow_up_date:
            raise HTTPException(status_code=400, detail="Cannot finalize encounter. Follow-up date is required.")
        
        # Determine if patient is insured (has CCC number)
        is_insured = encounter.ccc_number is not None and encounter.ccc_number.strip() != ""
        
        # Check for unpaid bills
        # For insured clients: bills can be 0 (fully covered) or must be paid
        # For non-insured clients: all bills must be paid
        unpaid_bills = db.query(Bill).filter(
            Bill.encounter_id == encounter_id,
            Bill.is_paid == False,
            Bill.total_amount > 0
        ).all()
        
        if unpaid_bills:
            unpaid_amount = sum(bill.total_amount for bill in unpaid_bills)
            if is_insured:
                # For insured clients, if there's an unpaid amount > 0, it must be paid
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot finalize encounter. There are {len(unpaid_bills)} unpaid bill(s) totaling GHC {unpaid_amount:.2f}. Please ensure all bills are paid before finalizing."
                )
            else:
                # For non-insured clients, all bills must be paid
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot finalize encounter. There are {len(unpaid_bills)} unpaid bill(s) totaling GHC {unpaid_amount:.2f}. Please ensure all bills are paid before finalizing."
                )
        
        encounter.finalized_at = datetime.utcnow()
    
    encounter.status = new_status
    db.commit()
    db.refresh(encounter)
    return {"encounter_id": encounter.id, "status": encounter.status}


@router.get("/patient/{patient_id}", response_model=List[EncounterResponse])
def get_patient_encounters(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all encounters for a patient (excluding archived)"""
    encounters = db.query(Encounter).filter(
        Encounter.patient_id == patient_id,
        Encounter.archived == False
    ).order_by(Encounter.created_at.desc()).all()
    return encounters


@router.put("/{encounter_id}", response_model=EncounterResponse)
def update_encounter(
    encounter_id: int,
    encounter_data: EncounterUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Records", "Doctor", "PA", "Admin"]))
):
    """Update encounter details"""
    encounter = db.query(Encounter).filter(Encounter.id == encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    if encounter.archived:
        raise HTTPException(status_code=400, detail="Cannot update archived encounter")
    
    # Update fields if provided
    if encounter_data.department is not None:
        encounter.department = encounter_data.department
    if encounter_data.procedure_g_drg_code is not None:
        encounter.procedure_g_drg_code = encounter_data.procedure_g_drg_code
    if encounter_data.procedure_name is not None:
        encounter.procedure_name = encounter_data.procedure_name
    if encounter_data.ccc_number is not None:
        # Enforce single insured encounter per patient per day
        if encounter_data.ccc_number and encounter_data.ccc_number.strip():
            from sqlalchemy import func
            existing_other = db.query(Encounter).filter(
                Encounter.patient_id == encounter.patient_id,
                Encounter.id != encounter_id,
                Encounter.archived == False,
                Encounter.ccc_number.isnot(None),
                Encounter.ccc_number != "",
                func.date(Encounter.created_at) == func.date(encounter.created_at)
            ).first()
            if existing_other:
                raise HTTPException(
                    status_code=400,
                    detail="An insured encounter already exists today for this patient. This encounter cannot have a CCC number."
                )
        encounter.ccc_number = encounter_data.ccc_number
    if encounter_data.status is not None:
        # Validate status transition if provided
        valid_transitions = {  
            "draft": ["in_consultation", "awaiting_services", "finalized"],
            "in_consultation": ["draft", "awaiting_services", "finalized"],
            "awaiting_services": ["draft", "in_consultation", "awaiting_services", "finalized"],
            "finalized": ["draft","in_consultation", "awaiting_services", "finalized"]
        }
        if encounter_data.status not in valid_transitions.get(encounter.status, []):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot transition from {encounter.status} to {encounter_data.status}"
            )
        
        # If finalizing, require diagnosis, follow-up date, outcome, and payment
        if encounter_data.status == "finalized":
            from app.models.bill import Bill
            from app.models.consultation_notes import ConsultationNotes
            from app.models.diagnosis import Diagnosis
            
            # Require at least one diagnosis
            diagnoses = db.query(Diagnosis).filter(Diagnosis.encounter_id == encounter_id).all()
            if not diagnoses or len(diagnoses) == 0:
                raise HTTPException(status_code=400, detail="Cannot finalize encounter. At least one diagnosis is required.")
            
            # Require consultation notes with outcome and follow-up date
            notes = db.query(ConsultationNotes).filter(ConsultationNotes.encounter_id == encounter_id).first()
            if not notes:
                raise HTTPException(status_code=400, detail="Cannot finalize encounter. Consultation notes are required.")
            
            if not (notes.outcome and notes.outcome.strip()):
                raise HTTPException(status_code=400, detail="Cannot finalize encounter. Consultation outcome is required.")
            
            if not notes.follow_up_date:
                raise HTTPException(status_code=400, detail="Cannot finalize encounter. Follow-up date is required.")
            
            # Determine if patient is insured (has CCC number)
            is_insured = encounter.ccc_number is not None and encounter.ccc_number.strip() != ""
            
            # Check for unpaid bills
            # For insured clients: bills can be 0 (fully covered) or must be paid
            # For non-insured clients: all bills must be paid
            unpaid_bills = db.query(Bill).filter(
                Bill.encounter_id == encounter_id,
                Bill.is_paid == False,
                Bill.total_amount > 0
            ).all()
            
            if unpaid_bills:
                unpaid_amount = sum(bill.total_amount for bill in unpaid_bills)
                if is_insured:
                    # For insured clients, if there's an unpaid amount > 0, it must be paid
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot finalize encounter. There are {len(unpaid_bills)} unpaid bill(s) totaling GHC {unpaid_amount:.2f}. Please ensure all bills are paid before finalizing."
                    )
                else:
                    # For non-insured clients, all bills must be paid
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot finalize encounter. There are {len(unpaid_bills)} unpaid bill(s) totaling GHC {unpaid_amount:.2f}. Please ensure all bills are paid before finalizing."
                    )
            
            encounter.finalized_at = datetime.utcnow()
        
        encounter.status = encounter_data.status
    
    encounter.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(encounter)
    return encounter


@router.delete("/{encounter_id}")
def archive_encounter(
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Archive (soft delete) an encounter - Admin only"""
    encounter = db.query(Encounter).filter(Encounter.id == encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    if encounter.archived:
        raise HTTPException(status_code=400, detail="Encounter is already archived")
    
    # Soft delete - mark as archived
    encounter.archived = True
    encounter.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Encounter archived successfully", "encounter_id": encounter_id}


@router.get("/date/{date}")
def get_encounters_by_date(
    date: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all encounters for a specific date (excluding archived)"""
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())
        
        encounters = db.query(Encounter).filter(
            Encounter.created_at >= start_datetime,
            Encounter.created_at <= end_datetime,
            Encounter.archived == False  # Exclude archived encounters
        ).order_by(Encounter.created_at).all()
        
        # Include patient information
        result = []
        for encounter in encounters:
            result.append({
                "id": encounter.id,
                "patient_id": encounter.patient_id,
                "patient_name": f"{encounter.patient.name} {encounter.patient.surname or ''}".strip(),
                "patient_card_number": encounter.patient.card_number,
                "patient_age": encounter.patient.age,
                "patient_gender": encounter.patient.gender,
                "patient_insurance_id": encounter.patient.insurance_id,
                "patient_address": encounter.patient.address,
                "ccc_number": encounter.ccc_number,
                "status": encounter.status,
                "department": encounter.department,
                "created_at": encounter.created_at,
            })
        
        return result
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
