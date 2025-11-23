"""
System information API endpoints
"""
from fastapi import APIRouter
from app.core.datetime_utils import now, utcnow, today
from app.core.config import settings
from datetime import datetime

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/date")
def get_application_date():
    """
    Get the current application date/time.
    
    This endpoint returns the date/time that the application is using,
    which may differ from the system date if APPLICATION_REFERENCE_DATE
    is configured.
    
    Returns:
        dict: Contains application datetime, date, and whether reference date is active
    """
    app_now = now()
    app_utc = utcnow()
    app_today = today()
    system_now = datetime.now()
    system_date = system_now.date()
    
    return {
        "application_datetime": app_now.isoformat(),
        "application_utc": app_utc.isoformat(),
        "application_date": app_today.isoformat(),
        "system_datetime": system_now.isoformat(),
        "system_date": system_date.isoformat(),
        "reference_date_active": bool(settings.APPLICATION_REFERENCE_DATE),
        "reference_date": settings.APPLICATION_REFERENCE_DATE or None,
        "using_system_date": not bool(settings.APPLICATION_REFERENCE_DATE)
    }

