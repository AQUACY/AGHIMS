"""
Analyzer integration API endpoints
For testing and managing analyzer connections
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.core.database import get_db
from app.core.dependencies import require_role, get_current_user
from app.core.config import settings
from app.models.user import User
from app.services.astm_parser import ASTMParser
from app.services.analyzer_mapper import AnalyzerMapper
from app.services.analyzer_server import get_analyzer_server

router = APIRouter(prefix="/analyzer", tags=["analyzer"])


class TestASTMRequest(BaseModel):
    """Request model for testing ASTM parsing"""
    astm_data: str  # Raw ASTM message as string


class AnalyzerStatusResponse(BaseModel):
    """Response model for analyzer status"""
    enabled: bool
    host: str
    port: int
    equipment_ip: str
    running: bool
    status: str


@router.get("/status", response_model=AnalyzerStatusResponse)
def get_analyzer_status(
    current_user: User = Depends(require_role(["Lab", "Lab Head", "Admin"]))
):
    """Get analyzer server status"""
    server = get_analyzer_server()
    thread_alive = server.thread.is_alive() if server.thread else False
    socket_bound = server.server_socket is not None
    
    status = "unknown"
    if not settings.ANALYZER_ENABLED:
        status = "disabled"
    elif server.running and thread_alive and socket_bound:
        status = "running"
    elif server.running and not thread_alive:
        status = "thread_died"
    elif not server.running:
        status = "stopped"
    
    return {
        "enabled": settings.ANALYZER_ENABLED,
        "host": settings.ANALYZER_HOST,
        "port": settings.ANALYZER_PORT,
        "equipment_ip": settings.ANALYZER_EQUIPMENT_IP,
        "running": server.running and thread_alive,
        "status": status,
        "thread_alive": thread_alive,
        "socket_bound": socket_bound
    }


@router.post("/test-parse")
def test_parse_astm(
    request: TestASTMRequest,
    current_user: User = Depends(require_role(["Lab", "Lab Head", "Admin"]))
):
    """
    Test ASTM message parsing (for development/testing)
    Accepts raw ASTM message and returns parsed structure
    """
    parser = ASTMParser()
    
    try:
        # Convert string to bytes
        data = request.astm_data.encode('ascii', errors='ignore')
        
        # Parse
        records = parser.parse_frame(data)
        extracted = parser.extract_results(records)
        
        return {
            "success": True,
            "records": records,
            "extracted": extracted
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error parsing ASTM data: {str(e)}"
        )


@router.post("/test-map")
def test_map_results(
    sample_id: str = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Lab", "Lab Head", "Admin"]))
):
    """
    Test mapping analyzer results to lab result template
    Finds investigation by sample ID and shows what would be mapped
    """
    mapper = AnalyzerMapper(db)
    
    # Find investigation
    investigation_info = mapper.find_investigation_by_sample_id(sample_id)
    
    if not investigation_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No investigation found for sample ID: {sample_id}"
        )
    
    investigation, is_inpatient = investigation_info
    
    # Get lab result and template
    from app.models.lab_result import LabResult
    from app.models.inpatient_lab_result import InpatientLabResult
    from app.models.lab_result_template import LabResultTemplate
    
    if is_inpatient:
        lab_result = db.query(InpatientLabResult).filter(
            InpatientLabResult.investigation_id == investigation.id
        ).first()
    else:
        lab_result = db.query(LabResult).filter(
            LabResult.investigation_id == investigation.id
        ).first()
    
    if not lab_result or not lab_result.template_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab result or template not found"
        )
    
    template = db.query(LabResultTemplate).filter(
        LabResultTemplate.id == lab_result.template_id
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    # Example ASTM data for testing
    example_astm_data = {
        'sample_id': sample_id,
        'patient_id': '',
        'specimen_id': sample_id,
        'results': {
            'WBC': '4.79',
            'RBC': '3.61',
            'HGB': '9.4',
            'HCT': '29.8',
            'MCV': '82.5',
            'MCH': '31.5',
            'MCHC': '31.5',
            'PLT': '150',
        },
        'units': {
            'WBC': '10^3/uL',
            'RBC': '10^6/uL',
            'HGB': 'g/dL',
            'HCT': '%',
            'MCV': 'fL',
            'MCH': 'pg',
            'MCHC': 'g/dL',
            'PLT': '10^3/uL',
        },
        'flags': {},
        'comments': []
    }
    
    # Map to template
    mapped_data = mapper.map_astm_to_template(example_astm_data, template.template_structure)
    
    return {
        "success": True,
        "investigation_id": investigation.id,
        "is_inpatient": is_inpatient,
        "template_id": template.id,
        "template_name": template.template_name,
        "example_astm_data": example_astm_data,
        "mapped_data": mapped_data
    }


@router.post("/restart")
def restart_analyzer_server(
    current_user: User = Depends(require_role(["Lab Head", "Admin"]))
):
    """Restart the analyzer server"""
    server = get_analyzer_server()
    
    if server.running:
        server.stop()
        import time
        time.sleep(1)  # Brief pause
    
    server.start()
    
    return {
        "success": True,
        "message": "Analyzer server restarted",
        "running": server.running
    }

