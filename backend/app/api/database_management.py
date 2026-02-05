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
from app.core.dependencies import require_role, require_module_permission
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
    current_user: User = Depends(require_role(["Admin"])),
    _module_check: User = Depends(require_module_permission("database", "read"))
):
    """Export database backup immediately"""
    from pathlib import Path
    from fastapi.responses import StreamingResponse
    import os
    
    try:
        backup_service = DatabaseBackupService()
        backup_path, error = backup_service.export_backup()
        
        if error:
            logger.error(f"Backup export error: {error}")
            raise HTTPException(status_code=500, detail=error)
        
        if not backup_path:
            logger.error("Backup export returned no path")
            raise HTTPException(status_code=500, detail="Backup export failed")
        
        # Convert to Path object for cross-platform handling
        backup_file = Path(backup_path)
        
        if not backup_file.exists():
            logger.error(f"Backup file does not exist: {backup_path}")
            raise HTTPException(status_code=500, detail=f"Backup file not found: {backup_path}")
        
        # Log backup file details for debugging
        file_size = backup_file.stat().st_size
        file_mtime = backup_file.stat().st_mtime
        logger.info(f"Exporting backup: {backup_file.name}, size: {file_size} bytes, modified: {file_mtime}")
        
        # Get filename from path (works on both Windows and Unix)
        filename = backup_file.name
        
        # Read file and stream it to ensure fresh content
        def generate():
            with open(backup_file, 'rb') as f:
                while True:
                    chunk = f.read(8192)  # Read in 8KB chunks
                    if not chunk:
                        break
                    yield chunk
        
        # Return streaming response with no-cache headers
        return StreamingResponse(
            generate(),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting backup: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backup/import")
def import_backup(
    backup_file: UploadFile = File(...),
    current_user: User = Depends(require_role(["Admin"])),
    _module_check: User = Depends(require_module_permission("database", "create"))
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
    current_user: User = Depends(require_role(["Admin"])),
    _module_check: User = Depends(require_module_permission("database", "delete"))
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
    current_user: User = Depends(require_role(["Admin"])),
    _module_check: User = Depends(require_module_permission("database", "read"))
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
    current_user: User = Depends(require_role(["Admin"])),
    _module_check: User = Depends(require_module_permission("database", "update"))
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
    current_user: User = Depends(require_role(["Admin"])),
    _module_check: User = Depends(require_module_permission("database", "read"))
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
    current_user: User = Depends(require_role(["Admin"])),
    _module_check: User = Depends(require_module_permission("database", "read"))
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
    current_user: User = Depends(require_role(["Admin"])),
    _module_check: User = Depends(require_module_permission("database", "update"))
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
    current_user: User = Depends(require_role(["Admin"])),
    _module_check: User = Depends(require_module_permission("database", "read"))
):
    """Get database information"""
    try:
        from app.core.database import engine
        from sqlalchemy import inspect, text
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        # Get database size (approximate)
        db_size_mb = 0
        if settings.DATABASE_MODE.lower() == "sqlite":
            from pathlib import Path
            db_path = Path(settings.SQLITE_DB_PATH)
            if db_path.exists():
                db_size_bytes = db_path.stat().st_size
                db_size_mb = round(db_size_bytes / (1024 * 1024), 2)
        elif settings.DATABASE_MODE.lower() == "mysql":
            try:
                with engine.connect() as conn:
                    # Query already returns size in MB
                    result = conn.execute(
                        text(f"SELECT ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS db_size_mb FROM information_schema.tables WHERE table_schema='{settings.MYSQL_DATABASE}'")
                    )
                    db_size_mb = result.scalar()
                    if db_size_mb is None:
                        db_size_mb = 0
            except Exception as e:
                logger.warning(f"Could not get MySQL database size: {e}")
                db_size_mb = 0
        
        return {
            "database_mode": settings.DATABASE_MODE,
            "database_url": settings.DATABASE_URL.split('@')[0] + '@***',  # Hide password
            "table_count": len(tables),
            "tables": tables,
            "size_mb": db_size_mb,
        }
    
    except Exception as e:
        logger.error(f"Error getting database info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class CleanupAuditLogsRequest(BaseModel):
    """Request model for audit log cleanup"""
    older_than_days: Optional[int] = None  # If provided, only delete logs older than this many days
    dry_run: bool = False  # If True, only count and report, don't actually delete


@router.post("/cleanup-audit-logs")
def cleanup_audit_logs(
    request: CleanupAuditLogsRequest,
    current_user: User = Depends(require_role(["Admin"]))
):
    """
    Clean up GET request audit logs to reduce database size.
    Only Admin users can perform this operation.
    """
    try:
        import sys
        from pathlib import Path
        # Add backend directory to path to import migration script
        backend_dir = Path(__file__).parent.parent.parent
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        
        from migrate_cleanup_get_audit_logs import cleanup_get_audit_logs
        
        result = cleanup_get_audit_logs(
            older_than_days=request.older_than_days,
            dry_run=request.dry_run
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Unknown error during cleanup")
            )
        
        return {
            "message": "Cleanup completed successfully" if not request.dry_run else "Dry run completed",
            "statistics": {
                "total_logs_before": result.get("total_logs_before", 0),
                "get_logs_count": result.get("get_logs_count", 0),
                "deleted_count": result.get("deleted_count", 0),
                "total_logs_after": result.get("total_logs_after", 0),
                "dry_run": request.dry_run
            }
        }
    
    except Exception as e:
        logger.error(f"Error cleaning up audit logs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))