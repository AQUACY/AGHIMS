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
    created_at: datetime
    archived: bool = False
    
    class Config:
        from_attributes = True


class EncounterUpdate(BaseModel):
    """Encounter update model"""
    department: Optional[str] = None
    ccc_number: Optional[str] = None
    status: Optional[str] = None


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
    current_user: User = Depends(require_role(["Doctor", "Records", "Admin"]))
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
    
    # If finalizing, require outcome, auto-generate bills for chief diagnoses, and check that all bills are paid
    if new_status == "finalized":
        # Require consultation outcome to be set
        from app.models.consultation_notes import ConsultationNotes
        notes = db.query(ConsultationNotes).filter(ConsultationNotes.encounter_id == encounter_id).first()
        if not notes or not (notes.outcome and notes.outcome.strip()):
            raise HTTPException(status_code=400, detail="Cannot finalize encounter. Consultation outcome is required.")
        
        # Auto-generate bills for all chief diagnoses that don't have bills yet
        from app.models.diagnosis import Diagnosis
        from app.models.bill import Bill, BillItem
        from app.services.price_list_service_v2 import get_price_from_all_tables
        import random
        
        chief_diagnoses = db.query(Diagnosis).filter(
            Diagnosis.encounter_id == encounter_id,
            Diagnosis.is_chief == True,
            Diagnosis.gdrg_code.isnot(None),
            Diagnosis.gdrg_code != ''
        ).all()
        
        # Determine if insured based on encounter CCC number
        is_insured_encounter = encounter.ccc_number is not None and encounter.ccc_number.strip() != ""
        
        for diagnosis in chief_diagnoses:
            # Check if bill item already exists for this diagnosis
            existing_item = db.query(BillItem).join(Bill).filter(
                Bill.encounter_id == encounter_id,
                BillItem.item_code == diagnosis.gdrg_code,
                BillItem.item_name.like(f"%{diagnosis.diagnosis}%"),
                BillItem.category == "drg"
            ).first()
            
            if not existing_item:
                # Get price for the diagnosis (co-pay for insured, base rate for cash)
                unit_price = get_price_from_all_tables(db, diagnosis.gdrg_code, is_insured_encounter)
                
                if unit_price > 0:
                    # Find or create a bill for this encounter
                    existing_bill = db.query(Bill).filter(
                        Bill.encounter_id == encounter.id,
                        Bill.is_paid == False  # Only use unpaid bills
                    ).first()
                    
                    if existing_bill:
                        # Add bill item to existing bill
                        bill_item = BillItem(
                            bill_id=existing_bill.id,
                            item_code=diagnosis.gdrg_code,
                            item_name=f"Diagnosis: {diagnosis.diagnosis}",
                            category="drg",
                            quantity=1,
                            unit_price=unit_price,
                            total_price=unit_price
                        )
                        db.add(bill_item)
                        existing_bill.total_amount += unit_price
                    else:
                        # Create new bill
                        bill_number = f"BILL-{random.randint(100000, 999999)}"
                        bill = Bill(
                            encounter_id=encounter.id,
                            bill_number=bill_number,
                            is_insured=is_insured_encounter,
                            total_amount=unit_price,
                            created_by=current_user.id
                        )
                        db.add(bill)
                        db.flush()
                        
                        # Create bill item
                        bill_item = BillItem(
                            bill_id=bill.id,
                            item_code=diagnosis.gdrg_code,
                            item_name=f"Diagnosis: {diagnosis.diagnosis}",
                            category="drg",
                            quantity=1,
                            unit_price=unit_price,
                            total_price=unit_price
                        )
                        db.add(bill_item)
        
        # Commit bill changes before checking unpaid bills
        db.commit()
        
        # Check for unpaid bills > 0 only
        unpaid_bills = db.query(Bill).filter(
            Bill.encounter_id == encounter_id,
            Bill.is_paid == False,
            Bill.total_amount > 0
        ).all()
        
        if unpaid_bills:
            unpaid_amount = sum(bill.total_amount for bill in unpaid_bills)
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
    current_user: User = Depends(require_role(["Records", "Doctor", "Admin"]))
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
        
        # If finalizing, require outcome, auto-generate bills for chief diagnoses, and check that all bills are paid
        if encounter_data.status == "finalized":
            from app.models.bill import Bill, BillItem
            from app.models.consultation_notes import ConsultationNotes
            from app.models.diagnosis import Diagnosis
            from app.services.price_list_service_v2 import get_price_from_all_tables
            import random
            
            # Require consultation outcome to be set
            notes = db.query(ConsultationNotes).filter(ConsultationNotes.encounter_id == encounter_id).first()
            if not notes or not (notes.outcome and notes.outcome.strip()):
                raise HTTPException(status_code=400, detail="Cannot finalize encounter. Consultation outcome is required.")
            
            # Auto-generate bills for all chief diagnoses that don't have bills yet
            chief_diagnoses = db.query(Diagnosis).filter(
                Diagnosis.encounter_id == encounter_id,
                Diagnosis.is_chief == True,
                Diagnosis.gdrg_code.isnot(None),
                Diagnosis.gdrg_code != ''
            ).all()
            
            # Determine if insured based on encounter CCC number
            is_insured_encounter = encounter.ccc_number is not None and encounter.ccc_number.strip() != ""
            
            for diagnosis in chief_diagnoses:
                # Check if bill item already exists for this diagnosis
                existing_item = db.query(BillItem).join(Bill).filter(
                    Bill.encounter_id == encounter_id,
                    BillItem.item_code == diagnosis.gdrg_code,
                    BillItem.item_name.like(f"%{diagnosis.diagnosis}%"),
                    BillItem.category == "drg"
                ).first()
                
                if not existing_item:
                    # Get price for the diagnosis (co-pay for insured, base rate for cash)
                    unit_price = get_price_from_all_tables(db, diagnosis.gdrg_code, is_insured_encounter)
                    
                    if unit_price > 0:
                        # Find or create a bill for this encounter
                        existing_bill = db.query(Bill).filter(
                            Bill.encounter_id == encounter.id,
                            Bill.is_paid == False  # Only use unpaid bills
                        ).first()
                        
                        if existing_bill:
                            # Add bill item to existing bill
                            bill_item = BillItem(
                                bill_id=existing_bill.id,
                                item_code=diagnosis.gdrg_code,
                                item_name=f"Diagnosis: {diagnosis.diagnosis}",
                                category="drg",
                                quantity=1,
                                unit_price=unit_price,
                                total_price=unit_price
                            )
                            db.add(bill_item)
                            existing_bill.total_amount += unit_price
                        else:
                            # Create new bill
                            bill_number = f"BILL-{random.randint(100000, 999999)}"
                            bill = Bill(
                                encounter_id=encounter.id,
                                bill_number=bill_number,
                                is_insured=is_insured_encounter,
                                total_amount=unit_price,
                                created_by=current_user.id
                            )
                            db.add(bill)
                            db.flush()
                            
                            # Create bill item
                            bill_item = BillItem(
                                bill_id=bill.id,
                                item_code=diagnosis.gdrg_code,
                                item_name=f"Diagnosis: {diagnosis.diagnosis}",
                                category="drg",
                                quantity=1,
                                unit_price=unit_price,
                                total_price=unit_price
                            )
                            db.add(bill_item)
            
            # Commit bill changes before checking unpaid bills
            db.commit()
            
            # Check for unpaid bills > 0 only
            unpaid_bills = db.query(Bill).filter(
                Bill.encounter_id == encounter_id,
                Bill.is_paid == False,
                Bill.total_amount > 0
            ).all()
            
            if unpaid_bills:
                unpaid_amount = sum(bill.total_amount for bill in unpaid_bills)
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
                "ccc_number": encounter.ccc_number,
                "status": encounter.status,
                "department": encounter.department,
                "created_at": encounter.created_at,
            })
        
        return result
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
