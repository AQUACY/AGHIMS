"""
Lab Result Template management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.core.database import get_db
from app.core.dependencies import require_role, get_current_user
from app.models.user import User
from app.models.lab_result_template import LabResultTemplate

router = APIRouter(prefix="/lab-templates", tags=["lab-templates"])


@router.get("/generate-sample-id")
def generate_sample_id(
    source: Optional[str] = None,  # 'opd' or 'inpatient' - if not provided, checks both
    investigation_id: Optional[int] = None,  # Optional: if provided, determines source automatically
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Lab", "Lab Head", "Admin"]))
):
    """
    Generate next sequential sample ID in format: YYMMNNNNN
    - YY: 2-digit year (e.g., 25 for 2025)
    - MM: 2-digit month (e.g., 11 for November)
    - NNNNN: 5-digit sequential number (e.g., 00001, 00002)
    
    Example: 251100001 (first sample in November 2025)
    
    IMPORTANT: Always checks BOTH OPD and IPD tables to ensure sequential numbering
    across both tables. This prevents duplicate sample IDs regardless of source.
    If OPD has 251100001, the next IPD request will get 251100002, and vice versa.
    
    The source and investigation_id parameters are optional and used for logging/context only.
    """
    from app.models.lab_result import LabResult
    from app.models.inpatient_lab_result import InpatientLabResult
    from app.models.investigation import Investigation
    from app.models.inpatient_investigation import InpatientInvestigation
    from datetime import datetime
    import json
    
    # If investigation_id is provided, determine source automatically
    if investigation_id and not source:
        ipd_investigation = db.query(InpatientInvestigation).filter(InpatientInvestigation.id == investigation_id).first()
        if ipd_investigation:
            source = 'inpatient'
        else:
            opd_investigation = db.query(Investigation).filter(Investigation.id == investigation_id).first()
            if opd_investigation:
                source = 'opd'
    
    now = datetime.utcnow()
    year = now.year % 100  # Last 2 digits of year (e.g., 25 for 2025)
    month = now.month
    
    # Format: YYMM
    year_month_prefix = f"{year:02d}{month:02d}"
    
    # Find the highest sample number for this year/month
    # IMPORTANT: Always check BOTH tables to ensure sequential numbering across OPD and IPD
    # This prevents duplicate sample IDs regardless of which table the request comes from
    max_sample_num = 0
    found_sample_ids = []  # For debugging
    
    # Import logging for debugging
    import logging
    logger = logging.getLogger(__name__)
    
    # Force a fresh query by expiring all objects in the session
    # This ensures we see the latest committed data
    db.expire_all()
    
    # Check OPD lab results (always check, regardless of source)
    # Use a more efficient query - get all results with template_data
    # Use .all() to force evaluation and get fresh data
    opd_results = db.query(LabResult).filter(
        LabResult.template_data.isnot(None)
    ).all()
    
    logger.info(f"Checking {len(opd_results)} OPD lab results for sample IDs with prefix {year_month_prefix}")
    print(f"[SAMPLE_ID_DEBUG] Checking {len(opd_results)} OPD lab results for sample IDs with prefix {year_month_prefix}")
    
    for result in opd_results:
        if result.template_data:
            try:
                # Log the raw template_data to see what we're working with
                print(f"[SAMPLE_ID_DEBUG] OPD investigation_id={result.investigation_id}, template_data type: {type(result.template_data)}, value: {result.template_data}")
                
                # Handle both dict and JSON string formats
                template_data = None
                if isinstance(result.template_data, dict):
                    template_data = result.template_data
                elif isinstance(result.template_data, str):
                    # Try to parse as JSON string
                    try:
                        template_data = json.loads(result.template_data)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse OPD template_data as JSON for investigation_id={result.investigation_id}: {e}")
                        print(f"[SAMPLE_ID_DEBUG] Failed to parse OPD JSON: {e}")
                        continue
                else:
                    logger.warning(f"Unexpected template_data type: {type(result.template_data)} for investigation_id={result.investigation_id}")
                    print(f"[SAMPLE_ID_DEBUG] Unexpected OPD template_data type: {type(result.template_data)}")
                    continue
                
                if not isinstance(template_data, dict):
                    print(f"[SAMPLE_ID_DEBUG] OPD template_data is not a dict after parsing: {type(template_data)}")
                    continue
                
                sample_no = template_data.get('sample_no', '')
                print(f"[SAMPLE_ID_DEBUG] OPD investigation_id={result.investigation_id}, sample_no: '{sample_no}' (type: {type(sample_no)})")
                logger.debug(f"OPD investigation_id={result.investigation_id}, sample_no from template_data: '{sample_no}' (type: {type(sample_no)})")
                # Check if sample_no matches the current year/month pattern (9 characters: YYMMNNNNN = 2+2+5)
                if sample_no and isinstance(sample_no, str):
                    sample_no = sample_no.strip()
                    logger.debug(f"OPD sample_no after strip: '{sample_no}', len={len(sample_no)}, prefix match: {sample_no[:4] == year_month_prefix if len(sample_no) >= 4 else False}")
                    print(f"[SAMPLE_ID_DEBUG] OPD sample_no after strip: '{sample_no}', len={len(sample_no)}, prefix: {sample_no[:4] if len(sample_no) >= 4 else 'N/A'}, expected: {year_month_prefix}")
                    if len(sample_no) == 9 and sample_no[:4] == year_month_prefix:
                        try:
                            sample_num = int(sample_no[4:])  # Extract the last 5 digits
                            found_sample_ids.append(f"OPD:{sample_no}")
                            logger.info(f"Found OPD sample ID: {sample_no} (num: {sample_num})")
                            if sample_num > max_sample_num:
                                max_sample_num = sample_num
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Failed to parse sample number from {sample_no}: {e}")
                elif sample_no:
                    logger.warning(f"OPD sample_no is not a string: {sample_no} (type: {type(sample_no)})")
            except Exception as e:
                logger.error(f"Error processing OPD result investigation_id={result.investigation_id}: {e}", exc_info=True)
    
    # Check IPD lab results (always check, regardless of source)
    # Force fresh query
    ipd_results = db.query(InpatientLabResult).filter(
        InpatientLabResult.template_data.isnot(None)
    ).all()
    
    logger.info(f"Checking {len(ipd_results)} IPD lab results for sample IDs with prefix {year_month_prefix}")
    print(f"[SAMPLE_ID_DEBUG] Checking {len(ipd_results)} IPD lab results for sample IDs with prefix {year_month_prefix}")
    
    for result in ipd_results:
        if result.template_data:
            try:
                # Log the raw template_data to see what we're working with
                print(f"[SAMPLE_ID_DEBUG] IPD investigation_id={result.investigation_id}, template_data type: {type(result.template_data)}, value: {result.template_data}")
                
                # Handle both dict and JSON string formats
                template_data = None
                if isinstance(result.template_data, dict):
                    template_data = result.template_data
                elif isinstance(result.template_data, str):
                    # Try to parse as JSON string
                    try:
                        template_data = json.loads(result.template_data)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse IPD template_data as JSON for investigation_id={result.investigation_id}: {e}")
                        print(f"[SAMPLE_ID_DEBUG] Failed to parse IPD JSON: {e}")
                        continue
                else:
                    logger.warning(f"Unexpected template_data type: {type(result.template_data)} for investigation_id={result.investigation_id}")
                    print(f"[SAMPLE_ID_DEBUG] Unexpected IPD template_data type: {type(result.template_data)}")
                    continue
                
                if not isinstance(template_data, dict):
                    print(f"[SAMPLE_ID_DEBUG] IPD template_data is not a dict after parsing: {type(template_data)}")
                    continue
                
                sample_no = template_data.get('sample_no', '')
                print(f"[SAMPLE_ID_DEBUG] IPD investigation_id={result.investigation_id}, sample_no: '{sample_no}' (type: {type(sample_no)})")
                logger.debug(f"IPD investigation_id={result.investigation_id}, sample_no from template_data: '{sample_no}' (type: {type(sample_no)})")
                # Check if sample_no matches the current year/month pattern (9 characters: YYMMNNNNN = 2+2+5)
                if sample_no and isinstance(sample_no, str):
                    sample_no = sample_no.strip()
                    logger.debug(f"IPD sample_no after strip: '{sample_no}', len={len(sample_no)}, prefix match: {sample_no[:4] == year_month_prefix if len(sample_no) >= 4 else False}")
                    print(f"[SAMPLE_ID_DEBUG] IPD sample_no after strip: '{sample_no}', len={len(sample_no)}, prefix: {sample_no[:4] if len(sample_no) >= 4 else 'N/A'}, expected: {year_month_prefix}")
                    if len(sample_no) == 9 and sample_no[:4] == year_month_prefix:
                        try:
                            sample_num = int(sample_no[4:])  # Extract the last 5 digits
                            found_sample_ids.append(f"IPD:{sample_no}")
                            logger.info(f"Found IPD sample ID: {sample_no} (num: {sample_num})")
                            if sample_num > max_sample_num:
                                max_sample_num = sample_num
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Failed to parse sample number from {sample_no}: {e}")
                elif sample_no:
                    logger.warning(f"IPD sample_no is not a string: {sample_no} (type: {type(sample_no)})")
            except Exception as e:
                logger.error(f"Error processing IPD result investigation_id={result.investigation_id}: {e}", exc_info=True)
    
    # Generate next sample number (always increment, even if max_sample_num is 0)
    # This ensures sequential numbering across both OPD and IPD tables
    # NOTE: Even if the current investigation already has a sample ID, we generate a new one
    # based on the global max, allowing users to regenerate if needed
    next_sample_num = max_sample_num + 1
    
    # Format: YYMMNNNNN (8 digits total)
    sample_id = f"{year_month_prefix}{next_sample_num:05d}"
    
    # Log for debugging
    logger.info(f"Generated sample ID: {sample_id} (max found: {max_sample_num}, year_month: {year_month_prefix}, source: {source}, investigation_id: {investigation_id})")
    logger.info(f"Found {len(found_sample_ids)} sample IDs: {found_sample_ids[:10]}")  # Log first 10 for debugging
    print(f"[SAMPLE_ID_DEBUG] Generated sample ID: {sample_id} (max found: {max_sample_num}, year_month: {year_month_prefix})")
    print(f"[SAMPLE_ID_DEBUG] Found {len(found_sample_ids)} sample IDs: {found_sample_ids}")
    
    return {"sample_id": sample_id}


class TemplateField(BaseModel):
    """Template field definition"""
    name: str  # Field identifier (e.g., "WBC")
    label: str  # Display label (e.g., "White Blood Cell Count")
    type: str  # "numeric", "text", "percentage"
    unit: Optional[str] = None  # Unit (e.g., "10^3/uL", "g/dL")
    reference_min: Optional[float] = None
    reference_max: Optional[float] = None
    order: int  # Display order
    group: Optional[str] = None  # Group name for organizing fields
    required: bool = False


class TemplateMessageField(BaseModel):
    """Template message field definition"""
    name: str  # Field identifier (e.g., "WBC IP Message")
    label: str  # Display label
    type: str = "text"  # "text", "textarea"
    order: int
    required: bool = False


class TemplateStructure(BaseModel):
    """Template structure"""
    fields: List[TemplateField]
    message_fields: Optional[List[TemplateMessageField]] = []
    patient_fields: Optional[List[str]] = []  # e.g., ["age", "ward", "doctor"]


class LabResultTemplateCreate(BaseModel):
    """Lab result template creation model"""
    g_drg_code: Optional[str] = None  # Optional, for reference
    procedure_name: str  # Required - primary matching field
    template_name: str
    template_structure: Dict[str, Any]  # JSON structure


class LabResultTemplateUpdate(BaseModel):
    """Lab result template update model"""
    g_drg_code: Optional[str] = None
    procedure_name: Optional[str] = None
    template_name: Optional[str] = None
    template_structure: Optional[Dict[str, Any]] = None
    is_active: Optional[int] = None


class LabResultTemplateResponse(BaseModel):
    """Lab result template response model"""
    id: int
    g_drg_code: Optional[str] = None  # Optional since it can be None
    procedure_name: str
    template_name: str
    template_structure: Dict[str, Any]
    created_by: int
    updated_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    is_active: int
    created_by_name: Optional[str] = None
    updated_by_name: Optional[str] = None
    
    class Config:
        from_attributes = True


@router.post("", response_model=LabResultTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    template_data: LabResultTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Lab Head"]))
):
    """Create a new lab result template"""
    # Check if template already exists for this procedure name
    existing = db.query(LabResultTemplate).filter(
        LabResultTemplate.procedure_name == template_data.procedure_name,
        LabResultTemplate.is_active == 1
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"An active template already exists for procedure: {template_data.procedure_name}"
        )
    
    # Validate template structure
    if not template_data.template_structure or "fields" not in template_data.template_structure:
        raise HTTPException(
            status_code=400,
            detail="Template structure must include 'fields' array"
        )
    
    template = LabResultTemplate(
        g_drg_code=template_data.g_drg_code,
        procedure_name=template_data.procedure_name,
        template_name=template_data.template_name,
        template_structure=template_data.template_structure,
        created_by=current_user.id
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    # Get user names
    created_user = db.query(User).filter(User.id == template.created_by).first()
    
    return LabResultTemplateResponse(
        id=template.id,
        g_drg_code=template.g_drg_code or None,  # Handle None case
        procedure_name=template.procedure_name,
        template_name=template.template_name,
        template_structure=template.template_structure,
        created_by=template.created_by,
        updated_by=template.updated_by,
        created_at=template.created_at,
        updated_at=template.updated_at,
        is_active=template.is_active,
        created_by_name=created_user.full_name if created_user else None,
        updated_by_name=None
    )


@router.get("", response_model=List[LabResultTemplateResponse])
def get_templates(
    procedure_name: Optional[str] = None,
    g_drg_code: Optional[str] = None,
    is_active: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Lab Head", "Lab"]))
):
    """Get all lab result templates, optionally filtered by procedure name, G-DRG code, or active status"""
    query = db.query(LabResultTemplate)
    
    if procedure_name:
        query = query.filter(LabResultTemplate.procedure_name == procedure_name)
    
    if g_drg_code:
        query = query.filter(LabResultTemplate.g_drg_code == g_drg_code)
    
    if is_active is not None:
        query = query.filter(LabResultTemplate.is_active == is_active)
    else:
        # Default to active templates only for non-admin users
        if current_user.role not in ["Admin", "Lab Head"]:
            query = query.filter(LabResultTemplate.is_active == 1)
    
    templates = query.order_by(LabResultTemplate.template_name).all()
    
    # Get user names
    result = []
    for template in templates:
        created_user = db.query(User).filter(User.id == template.created_by).first()
        updated_user = db.query(User).filter(User.id == template.updated_by).first() if template.updated_by else None
        
        result.append(LabResultTemplateResponse(
            id=template.id,
            g_drg_code=template.g_drg_code or None,  # Handle None case
            procedure_name=template.procedure_name,
            template_name=template.template_name,
            template_structure=template.template_structure,
            created_by=template.created_by,
            updated_by=template.updated_by,
            created_at=template.created_at,
            updated_at=template.updated_at,
            is_active=template.is_active,
            created_by_name=created_user.full_name if created_user else None,
            updated_by_name=updated_user.full_name if updated_user else None
        ))
    
    return result


@router.get("/by-procedure/{procedure_name}", response_model=Optional[LabResultTemplateResponse])
def get_template_by_procedure(
    procedure_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get active template for a specific procedure name"""
    template = db.query(LabResultTemplate).filter(
        LabResultTemplate.procedure_name == procedure_name,
        LabResultTemplate.is_active == 1
    ).first()
    
    if not template:
        return None
    
    # Get user names
    created_user = db.query(User).filter(User.id == template.created_by).first()
    updated_user = db.query(User).filter(User.id == template.updated_by).first() if template.updated_by else None
    
    return LabResultTemplateResponse(
        id=template.id,
        g_drg_code=template.g_drg_code or None,  # Handle None case
        procedure_name=template.procedure_name,
        template_name=template.template_name,
        template_structure=template.template_structure,
        created_by=template.created_by,
        updated_by=template.updated_by,
        created_at=template.created_at,
        updated_at=template.updated_at,
        is_active=template.is_active,
        created_by_name=created_user.full_name if created_user else None,
        updated_by_name=updated_user.full_name if updated_user else None
    )


@router.get("/available-procedures")
def get_available_lab_procedures(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Lab Head", "Lab"]))
):
    """Get list of available lab procedures from investigations and price list"""
    from app.models.investigation import Investigation
    from app.models.inpatient_investigation import InpatientInvestigation
    from app.models.procedure_price import ProcedurePrice
    from sqlalchemy import func, distinct
    
    procedures = []
    
    # Get unique procedure names from existing lab investigations
    opd_procedures = db.query(
        distinct(Investigation.procedure_name),
        Investigation.gdrg_code
    ).filter(
        Investigation.investigation_type == "lab",
        Investigation.procedure_name.isnot(None),
        Investigation.procedure_name != ""
    ).all()
    
    ipd_procedures = db.query(
        distinct(InpatientInvestigation.procedure_name),
        InpatientInvestigation.gdrg_code
    ).filter(
        InpatientInvestigation.investigation_type == "lab",
        InpatientInvestigation.procedure_name.isnot(None),
        InpatientInvestigation.procedure_name != ""
    ).all()
    
    # Combine and deduplicate
    procedure_map = {}
    for proc_name, gdrg_code in opd_procedures + ipd_procedures:
        if proc_name and proc_name not in procedure_map:
            procedure_map[proc_name] = gdrg_code
    
    # Also get from price list with "Lab" service type
    price_list_procedures = db.query(ProcedurePrice).filter(
        ProcedurePrice.service_type.ilike("%lab%"),
        ProcedurePrice.is_active == True
    ).all()
    
    for proc in price_list_procedures:
        if proc.service_name and proc.service_name not in procedure_map:
            procedure_map[proc.service_name] = proc.g_drg_code
    
    # Convert to list format
    for proc_name, gdrg_code in procedure_map.items():
        procedures.append({
            "service_name": proc_name,
            "g_drg_code": gdrg_code or ""
        })
    
    # Sort by procedure name
    procedures.sort(key=lambda x: x["service_name"])
    
    return procedures


@router.get("/{template_id}", response_model=LabResultTemplateResponse)
def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Lab Head", "Lab"]))
):
    """Get a specific template by ID"""
    template = db.query(LabResultTemplate).filter(LabResultTemplate.id == template_id).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Get user names
    created_user = db.query(User).filter(User.id == template.created_by).first()
    updated_user = db.query(User).filter(User.id == template.updated_by).first() if template.updated_by else None
    
    return LabResultTemplateResponse(
        id=template.id,
        g_drg_code=template.g_drg_code or None,  # Handle None case
        procedure_name=template.procedure_name,
        template_name=template.template_name,
        template_structure=template.template_structure,
        created_by=template.created_by,
        updated_by=template.updated_by,
        created_at=template.created_at,
        updated_at=template.updated_at,
        is_active=template.is_active,
        created_by_name=created_user.full_name if created_user else None,
        updated_by_name=updated_user.full_name if updated_user else None
    )


@router.put("/{template_id}", response_model=LabResultTemplateResponse)
def update_template(
    template_id: int,
    template_data: LabResultTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Lab Head"]))
):
    """Update a lab result template"""
    template = db.query(LabResultTemplate).filter(LabResultTemplate.id == template_id).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Update fields
    if template_data.g_drg_code is not None:
        template.g_drg_code = template_data.g_drg_code
    if template_data.procedure_name is not None:
        # Check if another active template already uses this procedure name
        existing = db.query(LabResultTemplate).filter(
            LabResultTemplate.procedure_name == template_data.procedure_name,
            LabResultTemplate.is_active == 1,
            LabResultTemplate.id != template_id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Another active template already exists for procedure: {template_data.procedure_name}"
            )
        
        template.procedure_name = template_data.procedure_name
    if template_data.template_name is not None:
        template.template_name = template_data.template_name
    if template_data.template_structure is not None:
        # Validate template structure
        if "fields" not in template_data.template_structure:
            raise HTTPException(
                status_code=400,
                detail="Template structure must include 'fields' array"
            )
        template.template_structure = template_data.template_structure
    if template_data.is_active is not None:
        template.is_active = template_data.is_active
    
    template.updated_by = current_user.id
    template.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(template)
    
    # Get user names
    created_user = db.query(User).filter(User.id == template.created_by).first()
    updated_user = db.query(User).filter(User.id == template.updated_by).first() if template.updated_by else None
    
    return LabResultTemplateResponse(
        id=template.id,
        g_drg_code=template.g_drg_code or None,  # Handle None case
        procedure_name=template.procedure_name,
        template_name=template.template_name,
        template_structure=template.template_structure,
        created_by=template.created_by,
        updated_by=template.updated_by,
        created_at=template.created_at,
        updated_at=template.updated_at,
        is_active=template.is_active,
        created_by_name=created_user.full_name if created_user else None,
        updated_by_name=updated_user.full_name if updated_user else None
    )


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin", "Lab Head"]))
):
    """Delete (deactivate) a lab result template"""
    template = db.query(LabResultTemplate).filter(LabResultTemplate.id == template_id).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Soft delete - set is_active to 0
    template.is_active = 0
    template.updated_by = current_user.id
    template.updated_at = datetime.utcnow()
    
    db.commit()
    
    return None

