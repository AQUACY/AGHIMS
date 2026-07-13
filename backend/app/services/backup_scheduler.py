"""
Backup scheduler service
Manages scheduled database backups using APScheduler
"""
import logging
from datetime import datetime, time

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    BackgroundScheduler = None
    CronTrigger = None
    IntervalTrigger = None

from app.core.config import settings
from app.services.database_backup import DatabaseBackupService

logger = logging.getLogger(__name__)


class BackupScheduler:
    """Service for scheduling database backups"""
    
    def __init__(self):
        # Always initialize backup_service (it doesn't require APScheduler)
        self.backup_service = DatabaseBackupService()
        self.scheduled_job_ids = []  # List to store multiple backup job IDs
        self.sync_job_id = None
        
        if not APSCHEDULER_AVAILABLE:
            # Don't raise error, just mark as unavailable
            self.scheduler = None
            self.available = False
            logger.warning("APScheduler is not installed. Scheduled backups will be disabled. Install with: pip install 'apscheduler>=3.10.4'")
            return
        
        self.scheduler = BackgroundScheduler()
        self.available = True
    
    def start(self):
        """Start the backup scheduler"""
        if not self.available:
            logger.warning("Backup scheduler cannot start - APScheduler is not installed")
            return
        
        if not settings.BACKUP_ENABLED:
            logger.info("Backup scheduler is disabled")
            return
        
        try:
            self.scheduler.start()
            logger.info("Backup scheduler started")
            
            # Schedule backups if enabled
            if settings.SCHEDULED_BACKUP_ENABLED:
                self.schedule_backup()
            
            # Schedule sync if enabled
            if settings.SYNC_ENABLED:
                self.schedule_sync()
        
        except Exception as e:
            logger.error(f"Failed to start backup scheduler: {e}", exc_info=True)
    
    def stop(self):
        """Stop the backup scheduler"""
        if not self.available or not self.scheduler:
            return
        
        try:
            if self.scheduler.running:
                self.scheduler.shutdown()
                logger.info("Backup scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping backup scheduler: {e}", exc_info=True)
    
    def schedule_backup(self, backup_times: str = None):
        """Schedule automatic backups (supports multiple times per day)"""
        if not self.available or not self.scheduler:
            logger.warning("Cannot schedule backup - APScheduler is not available")
            return
        
        # Remove existing backup jobs
        for job_id in self.scheduled_job_ids:
            try:
                self.scheduler.remove_job(job_id)
            except:
                pass
        self.scheduled_job_ids = []
        
        try:
            # Use provided times or fall back to settings
            time_string = backup_times or settings.SCHEDULED_BACKUP_TIME
            # Parse scheduled times (comma-separated)
            times = [t.strip() for t in time_string.split(',')]
            
            for idx, time_str in enumerate(times):
                # Parse scheduled time
                time_parts = time_str.split(':')
                hour = int(time_parts[0])
                minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    logger.warning(f"Invalid time format: {time_str}, skipping")
                    continue
                
                # Schedule daily backup
                trigger = CronTrigger(hour=hour, minute=minute)
                
                job_id = f'scheduled_backup_{idx}'
                job = self.scheduler.add_job(
                    self._perform_backup,
                    trigger=trigger,
                    id=job_id,
                    name=f'Scheduled Database Backup ({time_str})',
                    replace_existing=True
                )
                
                self.scheduled_job_ids.append(job_id)
                logger.info(f"Scheduled backup set for {time_str} daily")
            
            if not self.scheduled_job_ids:
                logger.warning("No valid backup times configured")
        
        except Exception as e:
            logger.error(f"Error scheduling backup: {e}", exc_info=True)
    
    def schedule_sync(self):
        """Schedule automatic database sync"""
        if not self.available or not self.scheduler:
            logger.warning("Cannot schedule sync - APScheduler is not available")
            return
        
        if self.sync_job_id:
            self.scheduler.remove_job(self.sync_job_id)
        
        try:
            # Schedule sync at specified interval
            trigger = IntervalTrigger(minutes=settings.SYNC_INTERVAL_MINUTES)
            
            self.sync_job_id = self.scheduler.add_job(
                self._perform_sync,
                trigger=trigger,
                id='scheduled_sync',
                name='Scheduled Database Sync',
                replace_existing=True
            )
            
            logger.info(f"Scheduled sync set for every {settings.SYNC_INTERVAL_MINUTES} minutes")
        
        except Exception as e:
            logger.error(f"Error scheduling sync: {e}", exc_info=True)
    
    def _perform_backup(self):
        """Perform a scheduled backup"""
        if not self.available or not self.backup_service:
            logger.warning("Cannot perform backup - APScheduler/backup service not available")
            return
        
        try:
            logger.info("Starting scheduled backup...")
            backup_path, error = self.backup_service.export_backup()
            
            if error:
                logger.error(f"Scheduled backup failed: {error}")
            else:
                logger.info(f"Scheduled backup completed: {backup_path}")
                
                # Cleanup old backups
                deleted = self.backup_service.cleanup_old_backups()
                if deleted > 0:
                    logger.info(f"Cleaned up {deleted} old backup(s)")
        
        except Exception as e:
            logger.error(f"Error performing scheduled backup: {e}", exc_info=True)
    
    def _perform_sync(self):
        """Perform a scheduled sync"""
        try:
            from app.services.database_sync import DatabaseSyncService
            sync_service = DatabaseSyncService()
            
            logger.info("Starting scheduled database sync...")
            success, message = sync_service.sync_database()
            
            if success:
                logger.info(f"Scheduled sync completed: {message}")
            else:
                logger.error(f"Scheduled sync failed: {message}")
        
        except Exception as e:
            logger.error(f"Error performing scheduled sync: {e}", exc_info=True)
    
    def get_schedule_info(self) -> dict:
        """Get information about scheduled jobs"""
        if not self.available or not self.scheduler:
            return {
                "running": False,
                "jobs": [],
                "available": False,
                "message": "APScheduler is not installed"
            }
        
        jobs = []
        
        # Get all backup jobs
        for job_id in self.scheduled_job_ids:
            try:
                job = self.scheduler.get_job(job_id)
                if job:
                    jobs.append({
                        "id": job.id,
                        "name": job.name,
                        "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                        "trigger": str(job.trigger)
                    })
            except Exception as e:
                logger.warning(f"Error getting job info for {job_id}: {e}")
        
        # Get sync job
        if self.sync_job_id:
            try:
                job = self.scheduler.get_job(self.sync_job_id)
                if job:
                    jobs.append({
                        "id": job.id,
                        "name": job.name,
                        "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                        "trigger": str(job.trigger)
                    })
            except Exception as e:
                logger.warning(f"Error getting sync job info: {e}")
        
        return {
            "running": self.scheduler.running if hasattr(self.scheduler, 'running') else False,
            "jobs": jobs,
            "available": True
        }

# Global scheduler instance
backup_scheduler = BackupScheduler()

