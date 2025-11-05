"""
Vitals endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from app.core.database import get_db
from app.core.dependencies import require_role, get_current_user
from app.models.user import User
from app.models.vital import Vital
from app.models.encounter import Encounter
from app.models.patient import Patient

router = APIRouter(prefix="/vitals", tags=["vitals"])


class VitalCreate(BaseModel):
    """Vital creation model"""
    encounter_id: int
    bp: Optional[str] = None
    temperature: Optional[float] = None
    pulse: Optional[int] = None
    respiration: Optional[int] = None
    weight: Optional[float] = None
    height: Optional[float] = None
    bmi: Optional[float] = None
    spo2: Optional[int] = None
    rbs: Optional[float] = None
    fbs: Optional[float] = None
    upt: Optional[str] = None
    rdt_malaria: Optional[str] = None
    retro_rdt: Optional[str] = None
    remarks: Optional[str] = None


class VitalResponse(BaseModel):
    """Vital response model"""
    id: int
    encounter_id: int
    bp: Optional[str]
    temperature: Optional[float]
    pulse: Optional[int]
    respiration: Optional[int]
    weight: Optional[float]
    height: Optional[float]
    bmi: Optional[float]
    spo2: Optional[int]
    rbs: Optional[float]
    fbs: Optional[float]
    upt: Optional[str]
    rdt_malaria: Optional[str]
    retro_rdt: Optional[str]
    remarks: Optional[str]
    
    class Config:
        from_attributes = True


@router.get("/encounter/{encounter_id}", response_model=VitalResponse)
def get_vitals(
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "Admin", "Records"]))
):
    """Get vitals for an encounter"""
    vital = db.query(Vital).filter(Vital.encounter_id == encounter_id).first()
    if not vital:
        raise HTTPException(status_code=404, detail="Vitals not found")
    return vital


@router.get("/date/{date}")
def get_encounters_with_vitals_by_date(
    date: str,
    card_number: Optional[str] = Query(None, description="Filter by patient card number"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all encounters for a specific date with their vitals, filterable by card number"""
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())
        
        # Base query for encounters on the date
        query = db.query(Encounter).join(Patient).filter(
            Encounter.created_at >= start_datetime,
            Encounter.created_at <= end_datetime,
            Encounter.archived == False
        )
        
        # Filter by card number if provided
        if card_number and card_number.strip():
            query = query.filter(Patient.card_number.ilike(f"%{card_number.strip()}%"))
        
        encounters = query.order_by(Encounter.created_at.desc()).all()
        
        # Include patient information and vitals
        result = []
        for encounter in encounters:
            # Get vitals for this encounter if exists
            vital = db.query(Vital).filter(Vital.encounter_id == encounter.id).first()
            
            patient = encounter.patient
            result.append({
                "id": encounter.id,
                "patient_id": encounter.patient_id,
                "patient_name": f"{patient.name} {patient.surname or ''}".strip(),
                "patient_card_number": patient.card_number,
                "ccc_number": encounter.ccc_number,
                "status": encounter.status,
                "department": encounter.department,
                "created_at": encounter.created_at,
                "has_vitals": vital is not None,
                "vitals": {
                    "id": vital.id if vital else None,
                    "bp": vital.bp if vital else None,
                    "temperature": vital.temperature if vital else None,
                    "pulse": vital.pulse if vital else None,
                    "respiration": vital.respiration if vital else None,
                    "weight": vital.weight if vital else None,
                    "height": vital.height if vital else None,
                    "bmi": vital.bmi if vital else None,
                    "spo2": vital.spo2 if vital else None,
                    "rbs": vital.rbs if vital else None,
                    "fbs": vital.fbs if vital else None,
                    "upt": vital.upt if vital else None,
                    "rdt_malaria": vital.rdt_malaria if vital else None,
                    "retro_rdt": vital.retro_rdt if vital else None,
                    "remarks": vital.remarks if vital else None,
                    "recorded_at": vital.recorded_at if vital else None,
                } if vital else None
            })
        
        return result
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")


@router.get("/")
def get_today_encounters_with_vitals(
    card_number: Optional[str] = Query(None, description="Filter by patient card number"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get today's encounters with their vitals, filterable by card number"""
    today = datetime.now().date()
    today_str = today.strftime("%Y-%m-%d")
    return get_encounters_with_vitals_by_date(today_str, card_number, db, current_user)


@router.post("/", response_model=VitalResponse, status_code=status.HTTP_201_CREATED)
def create_vitals(
    vital_data: VitalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "Admin", "Records"]))
):
    """Record patient vitals"""
    # Check encounter exists and is in draft status
    encounter = db.query(Encounter).filter(Encounter.id == vital_data.encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # if encounter.status != "draft":
    #     raise HTTPException(
    #         status_code=400,
    #         detail="Vitals can only be recorded for encounters in draft status"
    #     )
    
    # Check if vitals already exist
    existing = db.query(Vital).filter(Vital.encounter_id == vital_data.encounter_id).first()
    
    if existing:
        # Update existing vitals
        for key, value in vital_data.dict(exclude={"encounter_id"}).items():
            setattr(existing, key, value)
        existing.recorded_by = current_user.id
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # Create new vitals
        vital = Vital(**vital_data.dict(), recorded_by=current_user.id)
        db.add(vital)
        db.commit()
        db.refresh(vital)
        return vital

