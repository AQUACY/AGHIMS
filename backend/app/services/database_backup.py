"""
Database backup and restore service
Supports both SQLite and MySQL databases
"""
import os
import shutil
import subprocess
import logging
import gzip
import json
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
        """Export MySQL database backup using mysqldump or Python fallback"""
        try:
            backup_filename = f"hms_backup_{timestamp}.sql"
            backup_path = self.backup_dir / backup_filename
            
            # Check if mysqldump is available
            mysqldump_path = shutil.which("mysqldump")
            if not mysqldump_path:
                # Fallback: Use Python to export data
                logger.warning("mysqldump not found, using Python-based backup")
                return self._export_mysql_backup_python(timestamp)
            
            # Build mysqldump command
            cmd = [
                mysqldump_path,
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
                # Try Python fallback
                logger.warning(f"mysqldump failed: {error_msg}, trying Python fallback")
                return self._export_mysql_backup_python(timestamp)
            
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
        
        except Exception as e:
            logger.error(f"Error exporting MySQL backup: {e}", exc_info=True)
            # Try Python fallback as last resort
            try:
                return self._export_mysql_backup_python(timestamp)
            except Exception as fallback_error:
                return None, f"Backup failed: {str(e)}. Python fallback also failed: {str(fallback_error)}"
    
    def _export_mysql_backup_python(self, timestamp: str) -> Tuple[Optional[str], Optional[str]]:
        """Export MySQL database backup using Python (fallback when mysqldump not available)"""
        try:
            from app.core.database import engine, Base
            from sqlalchemy import inspect, text
            import app.models  # Import all models
            
            backup_filename = f"hms_backup_{timestamp}.sql"
            backup_path = self.backup_dir / backup_filename
            
            logger.info("Creating MySQL backup using Python (mysqldump not available)")
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                # Write header
                f.write(f"-- MySQL Backup created at {datetime.now().isoformat()}\n")
                f.write(f"-- Database: {settings.MYSQL_DATABASE}\n")
                f.write(f"-- Note: This is a Python-based backup (mysqldump not available)\n")
                f.write("-- For full backup including structure, install MySQL client tools\n\n")
                f.write(f"USE `{settings.MYSQL_DATABASE}`;\n\n")
                
                # Get all tables
                inspector = inspect(engine)
                tables = inspector.get_table_names()
                
                # Export each table
                for table_name in tables:
                    if table_name.startswith('_') or table_name in ['alembic_version']:
                        continue
                    
                    try:
                        # Get table structure
                        columns = inspector.get_columns(table_name)
                        pk_constraint = inspector.get_pk_constraint(table_name)
                        
                        # Write CREATE TABLE statement (simplified)
                        f.write(f"\n-- Table: {table_name}\n")
                        f.write(f"DROP TABLE IF EXISTS `{table_name}`;\n")
                        
                        # Get actual CREATE TABLE from MySQL
                        with engine.connect() as conn:
                            result = conn.execute(
                                text(f"SHOW CREATE TABLE `{table_name}`")
                            )
                            create_table_row = result.first()
                            if create_table_row:
                                f.write(f"{create_table_row[1]};\n\n")
                        
                        # Export data
                        with engine.connect() as conn:
                            result = conn.execute(text(f"SELECT * FROM `{table_name}`"))
                            rows = result.fetchall()
                            
                            if rows:
                                # Get column names
                                col_names = [col['name'] for col in columns]
                                
                                # Write INSERT statements
                                for row in rows:
                                    values = []
                                    for val in row:
                                        if val is None:
                                            values.append('NULL')
                                        elif isinstance(val, str):
                                            # Escape single quotes
                                            escaped = val.replace("'", "''").replace("\\", "\\\\")
                                            values.append(f"'{escaped}'")
                                        elif isinstance(val, (int, float)):
                                            values.append(str(val))
                                        elif isinstance(val, bool):
                                            values.append('1' if val else '0')
                                        else:
                                            escaped = str(val).replace("'", "''").replace("\\", "\\\\")
                                            values.append(f"'{escaped}'")
                                    
                                    f.write(f"INSERT INTO `{table_name}` (`{'`, `'.join(col_names)}`) VALUES ({', '.join(values)});\n")
                        
                    except Exception as e:
                        logger.warning(f"Error exporting table {table_name}: {e}")
                        f.write(f"\n-- Error exporting table {table_name}: {e}\n")
                        continue
            
            # Compress the backup
            compressed_path = self.backup_dir / f"{backup_filename}.gz"
            with open(backup_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Remove uncompressed file
            backup_path.unlink()
            
            logger.info(f"MySQL backup created (Python method): {compressed_path}")
            return str(compressed_path), None
        
        except Exception as e:
            logger.error(f"Error in Python-based MySQL backup: {e}", exc_info=True)
            return None, f"Python backup failed: {str(e)}. Please install MySQL client tools (mysqldump) for better backups."
    
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

