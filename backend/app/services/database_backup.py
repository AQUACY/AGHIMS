"""
Database backup and restore service
Supports both SQLite and MySQL databases
"""
import os
import shutil
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
from sqlalchemy import create_engine, text
from app.core.config import settings

logger = logging.getLogger(__name__)


class DatabaseBackupService:
    """Service for backing up and restoring databases"""
    
    def __init__(self):
        self.backup_dir = Path(settings.BACKUP_DIR)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def export_backup(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Export database backup
        Returns: (backup_file_path, error_message)
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if settings.DATABASE_MODE.lower() == "sqlite":
                return self._export_sqlite_backup(timestamp)
            elif settings.DATABASE_MODE.lower() == "mysql":
                return self._export_mysql_backup(timestamp)
            else:
                return None, f"Unsupported database mode: {settings.DATABASE_MODE}"
        
        except Exception as e:
            logger.error(f"Error exporting backup: {e}", exc_info=True)
            return None, str(e)
    
    def _export_sqlite_backup(self, timestamp: str) -> Tuple[Optional[str], Optional[str]]:
        """Export SQLite database backup"""
        try:
            db_path = Path(settings.SQLITE_DB_PATH)
            if not db_path.exists():
                return None, f"Database file not found: {db_path}"
            
            backup_filename = f"hms_backup_{timestamp}.db"
            backup_path = self.backup_dir / backup_filename
            
            # Copy SQLite database file
            shutil.copy2(db_path, backup_path)
            
            logger.info(f"SQLite backup created: {backup_path}")
            return str(backup_path), None
        
        except Exception as e:
            logger.error(f"Error exporting SQLite backup: {e}", exc_info=True)
            return None, str(e)
    
    def _export_mysql_backup(self, timestamp: str) -> Tuple[Optional[str], Optional[str]]:
        """Export MySQL database backup using mysqldump"""
        try:
            backup_filename = f"hms_backup_{timestamp}.sql"
            backup_path = self.backup_dir / backup_filename
            
            # Build mysqldump command
            cmd = [
                "mysqldump",
                f"--host={settings.MYSQL_HOST}",
                f"--port={settings.MYSQL_PORT}",
                f"--user={settings.MYSQL_USER}",
                f"--password={settings.MYSQL_PASSWORD}",
                f"--single-transaction",
                f"--routines",
                f"--triggers",
                f"--databases",
                settings.MYSQL_DATABASE,
            ]
            
            # Execute mysqldump
            with open(backup_path, 'w', encoding='utf-8') as f:
                result = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False
                )
            
            if result.returncode != 0:
                error_msg = result.stderr or "Unknown mysqldump error"
                if backup_path.exists():
                    backup_path.unlink()
                return None, f"mysqldump failed: {error_msg}"
            
            # Compress the backup
            compressed_path = self.backup_dir / f"{backup_filename}.gz"
            with open(backup_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Remove uncompressed file
            backup_path.unlink()
            backup_path = compressed_path
            
            logger.info(f"MySQL backup created: {compressed_path}")
            return str(compressed_path), None
        
        except FileNotFoundError:
            return None, "mysqldump not found. Please install MySQL client tools."
        except Exception as e:
            logger.error(f"Error exporting MySQL backup: {e}", exc_info=True)
            return None, str(e)
    
    def import_backup(self, backup_file_path: str) -> Tuple[bool, Optional[str]]:
        """
        Import database backup
        Returns: (success, error_message)
        """
        try:
            backup_path = Path(backup_file_path)
            if not backup_path.exists():
                return False, f"Backup file not found: {backup_file_path}"
            
            if settings.DATABASE_MODE.lower() == "sqlite":
                return self._import_sqlite_backup(backup_path)
            elif settings.DATABASE_MODE.lower() == "mysql":
                return self._import_mysql_backup(backup_path)
            else:
                return False, f"Unsupported database mode: {settings.DATABASE_MODE}"
        
        except Exception as e:
            logger.error(f"Error importing backup: {e}", exc_info=True)
            return False, str(e)
    
    def _import_sqlite_backup(self, backup_path: Path) -> Tuple[bool, Optional[str]]:
        """Import SQLite database backup"""
        try:
            db_path = Path(settings.SQLITE_DB_PATH)
            
            # Create backup of current database before restore
            if db_path.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                pre_restore_backup = self.backup_dir / f"pre_restore_{timestamp}.db"
                shutil.copy2(db_path, pre_restore_backup)
                logger.info(f"Created pre-restore backup: {pre_restore_backup}")
            
            # Copy backup file to database location
            shutil.copy2(backup_path, db_path)
            
            logger.info(f"SQLite backup restored from: {backup_path}")
            return True, None
        
        except Exception as e:
            logger.error(f"Error importing SQLite backup: {e}", exc_info=True)
            return False, str(e)
    
    def _import_mysql_backup(self, backup_path: Path) -> Tuple[bool, Optional[str]]:
        """Import MySQL database backup"""
        try:
            # Check if file is compressed
            is_compressed = backup_path.suffix == '.gz'
            
            # Build mysql command
            cmd = [
                "mysql",
                f"--host={settings.MYSQL_HOST}",
                f"--port={settings.MYSQL_PORT}",
                f"--user={settings.MYSQL_USER}",
                f"--password={settings.MYSQL_PASSWORD}",
                settings.MYSQL_DATABASE,
            ]
            
            # Create pre-restore backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pre_restore_backup, _ = self._export_mysql_backup(f"pre_restore_{timestamp}")
            if pre_restore_backup:
                logger.info(f"Created pre-restore backup: {pre_restore_backup}")
            
            # Import backup
            if is_compressed:
                import gzip
                with gzip.open(backup_path, 'rb') as f_in:
                    result = subprocess.run(
                        cmd,
                        stdin=f_in,
                        stderr=subprocess.PIPE,
                        text=True,
                        check=False
                    )
            else:
                with open(backup_path, 'r', encoding='utf-8') as f_in:
                    result = subprocess.run(
                        cmd,
                        stdin=f_in,
                        stderr=subprocess.PIPE,
                        text=True,
                        check=False
                    )
            
            if result.returncode != 0:
                error_msg = result.stderr or "Unknown mysql import error"
                return False, f"MySQL import failed: {error_msg}"
            
            logger.info(f"MySQL backup restored from: {backup_path}")
            return True, None
        
        except FileNotFoundError:
            return False, "mysql client not found. Please install MySQL client tools."
        except Exception as e:
            logger.error(f"Error importing MySQL backup: {e}", exc_info=True)
            return False, str(e)
    
    def list_backups(self) -> list:
        """List all available backups"""
        backups = []
        try:
            for file_path in self.backup_dir.iterdir():
                if file_path.is_file():
                    stat = file_path.stat()
                    backups.append({
                        "filename": file_path.name,
                        "path": str(file_path),
                        "size": stat.st_size,
                        "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    })
            
            # Sort by creation time (newest first)
            backups.sort(key=lambda x: x["created_at"], reverse=True)
            return backups
        
        except Exception as e:
            logger.error(f"Error listing backups: {e}", exc_info=True)
            return []
    
    def cleanup_old_backups(self) -> int:
        """Remove backups older than retention period"""
        try:
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=settings.BACKUP_RETENTION_DAYS)
            deleted_count = 0
            
            for file_path in self.backup_dir.iterdir():
                if file_path.is_file():
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < cutoff_date:
                        file_path.unlink()
                        deleted_count += 1
                        logger.info(f"Deleted old backup: {file_path.name}")
            
            return deleted_count
        
        except Exception as e:
            logger.error(f"Error cleaning up old backups: {e}", exc_info=True)
            return 0

