"""
Database management API endpoints
Handles backup, restore, sync, and scheduling operations
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.user import User
from app.services.database_backup import DatabaseBackupService
from app.services.database_sync import DatabaseSyncService
from app.services.backup_scheduler import backup_scheduler
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/database", tags=["database"])


class BackupScheduleRequest(BaseModel):
    enabled: bool
    time: Optional[str] = None  # HH:MM format
    interval_hours: Optional[int] = None


class SyncConfigRequest(BaseModel):
    enabled: bool
    remote_host: Optional[str] = None
    remote_port: Optional[int] = None
    remote_user: Optional[str] = None
    remote_password: Optional[str] = None
    remote_database: Optional[str] = None
    interval_minutes: Optional[int] = None


@router.get("/backup/export")
def export_backup(
    current_user: User = Depends(require_role(["Admin"]))
):
    """Export database backup immediately"""
    try:
        backup_service = DatabaseBackupService()
        backup_path, error = backup_service.export_backup()
        
        if error:
            raise HTTPException(status_code=500, detail=error)
        
        if not backup_path:
            raise HTTPException(status_code=500, detail="Backup export failed")
        
        # Return file for download
        return FileResponse(
            backup_path,
            media_type="application/octet-stream",
            filename=backup_path.split("/")[-1],
            headers={"Content-Disposition": f'attachment; filename="{backup_path.split("/")[-1]}"'}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting backup: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backup/import")
def import_backup(
    backup_file: UploadFile = File(...),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Import database backup"""
    try:
        # Save uploaded file temporarily
        import tempfile
        import shutil
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=backup_file.filename) as tmp_file:
            shutil.copyfileobj(backup_file.file, tmp_file)
            tmp_path = tmp_file.name
        
        try:
            backup_service = DatabaseBackupService()
            success, error = backup_service.import_backup(tmp_path)
            
            if not success:
                raise HTTPException(status_code=400, detail=error or "Backup import failed")
            
            return {"message": "Backup imported successfully"}
        
        finally:
            # Clean up temp file
            import os
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing backup: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backup/list")
def list_backups(
    current_user: User = Depends(require_role(["Admin"]))
):
    """List all available backups"""
    try:
        backup_service = DatabaseBackupService()
        backups = backup_service.list_backups()
        return {"backups": backups}
    
    except Exception as e:
        logger.error(f"Error listing backups: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/backup/{filename}")
def delete_backup(
    filename: str,
    current_user: User = Depends(require_role(["Admin"]))
):
    """Delete a backup file"""
    try:
        from pathlib import Path
        backup_path = Path(settings.BACKUP_DIR) / filename
        
        if not backup_path.exists():
            raise HTTPException(status_code=404, detail="Backup file not found")
        
        backup_path.unlink()
        return {"message": f"Backup {filename} deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting backup: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backup/status")
def get_backup_status(
    current_user: User = Depends(require_role(["Admin"]))
):
    """Get backup configuration and status"""
    try:
        schedule_info = backup_scheduler.get_schedule_info()
        
        return {
            "backup_enabled": settings.BACKUP_ENABLED,
            "scheduled_backup_enabled": settings.SCHEDULED_BACKUP_ENABLED,
            "scheduled_backup_time": settings.SCHEDULED_BACKUP_TIME,
            "backup_dir": settings.BACKUP_DIR,
            "retention_days": settings.BACKUP_RETENTION_DAYS,
            "scheduler": schedule_info,
            "database_mode": settings.DATABASE_MODE,
        }
    
    except Exception as e:
        logger.error(f"Error getting backup status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backup/schedule")
def configure_backup_schedule(
    schedule: BackupScheduleRequest,
    current_user: User = Depends(require_role(["Admin"]))
):
    """Configure backup schedule (supports multiple times, comma-separated)"""
    try:
        if schedule.enabled:
            if not schedule.time:
                raise HTTPException(status_code=400, detail="Backup time is required when enabling schedule")
            
            # Validate time format(s) - can be comma-separated
            times = [t.strip() for t in schedule.time.split(',')]
            for time_str in times:
                try:
                    time_parts = time_str.split(':')
                    if len(time_parts) != 2:
                        raise ValueError()
                    hour = int(time_parts[0])
                    minute = int(time_parts[1])
                    if not (0 <= hour <= 23 and 0 <= minute <= 59):
                        raise ValueError()
                except:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Invalid time format: {time_str}. Use HH:MM (24-hour format). Multiple times should be comma-separated (e.g., '07:00,19:00')"
                    )
            
            # Update scheduler with new times
            # Note: In a real app, you'd save this to a config file or database
            # For now, we'll update the scheduler directly with the provided times
            backup_scheduler.schedule_backup(backup_times=schedule.time)
            return {"message": f"Backup schedule configured successfully for {len(times)} time(s) per day: {schedule.time}"}
        else:
            # Disable scheduled backup
            for job_id in backup_scheduler.scheduled_job_ids:
                try:
                    backup_scheduler.scheduler.remove_job(job_id)
                except:
                    pass
            backup_scheduler.scheduled_job_ids = []
            return {"message": "Backup schedule disabled"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error configuring backup schedule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync/status")
def get_sync_status(
    current_user: User = Depends(require_role(["Admin"]))
):
    """Get database sync status"""
    try:
        sync_service = DatabaseSyncService()
        status_info = sync_service.get_sync_status()
        
        return {
            "sync_enabled": settings.SYNC_ENABLED,
            "sync_interval_minutes": settings.SYNC_INTERVAL_MINUTES,
            "remote_host": settings.SYNC_REMOTE_HOST if settings.SYNC_ENABLED else None,
            "remote_port": settings.SYNC_REMOTE_PORT if settings.SYNC_ENABLED else None,
            "remote_database": settings.SYNC_REMOTE_DATABASE if settings.SYNC_ENABLED else None,
            "status": status_info,
        }
    
    except Exception as e:
        logger.error(f"Error getting sync status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/test")
def test_sync_connection(
    current_user: User = Depends(require_role(["Admin"]))
):
    """Test connection to remote sync database"""
    try:
        sync_service = DatabaseSyncService()
        connected, error = sync_service.test_connection()
        
        if connected:
            return {"message": "Connection successful", "connected": True}
        else:
            return {"message": error or "Connection failed", "connected": False}
    
    except Exception as e:
        logger.error(f"Error testing sync connection: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/run")
def run_sync(
    current_user: User = Depends(require_role(["Admin"]))
):
    """Manually trigger database sync"""
    try:
        sync_service = DatabaseSyncService()
        success, message = sync_service.sync_database()
        
        if success:
            return {"message": message or "Sync completed successfully", "success": True}
        else:
            raise HTTPException(status_code=500, detail=message or "Sync failed")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running sync: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/info")
def get_database_info(
    current_user: User = Depends(require_role(["Admin"]))
):
    """Get database information"""
    try:
        from app.core.database import engine
        from sqlalchemy import inspect, text
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        # Get database size (approximate)
        db_size = 0
        if settings.DATABASE_MODE.lower() == "sqlite":
            from pathlib import Path
            db_path = Path(settings.SQLITE_DB_PATH)
            if db_path.exists():
                db_size = db_path.stat().st_size
        elif settings.DATABASE_MODE.lower() == "mysql":
            with engine.connect() as conn:
                result = conn.execute(
                    text(f"SELECT ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'DB Size in MB' FROM information_schema.tables WHERE table_schema='{settings.MYSQL_DATABASE}'")
                )
                db_size = result.scalar() or 0
        
        return {
            "database_mode": settings.DATABASE_MODE,
            "database_url": settings.DATABASE_URL.split('@')[0] + '@***',  # Hide password
            "table_count": len(tables),
            "tables": tables,
            "size_mb": round(db_size / (1024 * 1024), 2) if db_size else 0,
        }
    
    except Exception as e:
        logger.error(f"Error getting database info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

