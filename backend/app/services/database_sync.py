"""
Database synchronization service
Syncs local database to remote MySQL database for online backup
"""
import logging
from typing import Optional, Tuple
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.core.database import Base, engine as local_engine
# Import all models to ensure they're registered with Base
import app.models  # This imports all models from __init__.py

logger = logging.getLogger(__name__)


class DatabaseSyncService:
    """Service for syncing local database to remote MySQL database"""
    
    def __init__(self):
        self.remote_engine = None
        self.remote_session = None
        self._initialize_remote_connection()
    
    def _initialize_remote_connection(self):
        """Initialize connection to remote database"""
        if not settings.SYNC_ENABLED or not settings.SYNC_REMOTE_HOST:
            logger.warning("Database sync is disabled or not configured")
            return
        
        try:
            self.remote_engine = create_engine(
                settings.SYNC_DATABASE_URL,
                pool_pre_ping=True,
                echo=False
            )
            self.remote_session = sessionmaker(bind=self.remote_engine)
            logger.info("Remote database connection initialized")
        except Exception as e:
            logger.error(f"Failed to initialize remote database connection: {e}", exc_info=True)
            self.remote_engine = None
            self.remote_session = None
    
    def test_connection(self) -> Tuple[bool, Optional[str]]:
        """Test connection to remote database"""
        if not settings.SYNC_ENABLED:
            return False, "Database sync is disabled"
        
        if not self.remote_engine:
            return False, "Remote database connection not initialized"
        
        try:
            with self.remote_engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.scalar()
            return True, None
        except Exception as e:
            return False, str(e)
    
    def sync_database(self) -> Tuple[bool, Optional[str]]:
        """
        Sync local database to remote database
        This creates/updates tables and syncs data
        """
        if not settings.SYNC_ENABLED:
            return False, "Database sync is disabled"
        
        if not self.remote_engine:
            return False, "Remote database connection not initialized"
        
        try:
            # Step 1: Create tables in remote database if they don't exist
            logger.info("Creating/updating tables in remote database...")
            Base.metadata.create_all(bind=self.remote_engine)
            
            # Step 2: Sync data from local to remote
            logger.info("Syncing data to remote database...")
            sync_count = self._sync_data()
            
            logger.info(f"Database sync completed. Synced {sync_count} records.")
            return True, f"Sync completed. {sync_count} records processed."
        
        except Exception as e:
            logger.error(f"Error syncing database: {e}", exc_info=True)
            return False, str(e)
    
    def _sync_data(self) -> int:
        """Sync data from local to remote database"""
        from app.core.database import SessionLocal
        
        local_db = SessionLocal()
        remote_db = self.remote_session()
        
        sync_count = 0
        
        try:
            # Get all tables from local database
            local_inspector = inspect(local_engine)
            local_tables = local_inspector.get_table_names()
            
            logger.info(f"Found {len(local_tables)} tables in local database: {local_tables}")
            
            for table_name in local_tables:
                try:
                    # Skip system tables
                    if table_name.startswith('_') or table_name in ['alembic_version']:
                        logger.debug(f"Skipping system table: {table_name}")
                        continue
                    
                    # Get table metadata from Base (case-insensitive lookup)
                    table = None
                    for tname, t in Base.metadata.tables.items():
                        if tname.lower() == table_name.lower():
                            table = t
                            break
                    
                    if table is None:
                        logger.warning(f"Table {table_name} not found in Base.metadata, trying direct inspection")
                        # Try to get columns directly from inspector
                        local_columns = local_inspector.get_columns(table_name)
                        if not local_columns:
                            logger.warning(f"No columns found for table {table_name}, skipping")
                            continue
                        
                        # Get primary key from inspector
                        pk_constraint = local_inspector.get_pk_constraint(table_name)
                        if not pk_constraint or not pk_constraint.get('constrained_columns'):
                            logger.warning(f"No primary key found for table {table_name}, skipping")
                            continue
                        
                        pk_column = pk_constraint['constrained_columns'][0]
                        columns = [col['name'] for col in local_columns]
                    else:
                        # Get primary key column from table metadata
                        pk_column = None
                        for col in table.columns:
                            if col.primary_key:
                                pk_column = col.name
                                break
                        
                        if pk_column is None:
                            logger.warning(f"No primary key found for table {table_name}, skipping")
                            continue
                        
                        # Get column names
                        columns = [col.name for col in table.columns]
                    
                    logger.info(f"Syncing table {table_name} (PK: {pk_column}, Columns: {len(columns)})")
                    
                    # Fetch all records from local database
                    local_records = local_db.execute(
                        text(f"SELECT * FROM `{table_name}`")
                    ).fetchall()
                    
                    logger.info(f"Found {len(local_records)} records in local table {table_name}")
                    
                    if len(local_records) == 0:
                        logger.debug(f"Table {table_name} is empty, skipping")
                        continue
                    
                    # Sync each record
                    for idx, local_record in enumerate(local_records):
                        try:
                            # Convert Row to dict
                            if hasattr(local_record, '_asdict'):
                                record_dict = local_record._asdict()
                            elif hasattr(local_record, '_mapping'):
                                record_dict = dict(local_record._mapping)
                            else:
                                # Fallback: zip with column names
                                record_dict = dict(zip(columns, local_record))
                            
                            pk_value = record_dict.get(pk_column)
                            if pk_value is None:
                                logger.warning(f"Primary key value is None for record {idx} in table {table_name}, skipping")
                                continue
                            
                            # Check if record exists in remote
                            existing = remote_db.execute(
                                text(f"SELECT `{pk_column}` FROM `{table_name}` WHERE `{pk_column}` = :pk"),
                                {"pk": pk_value}
                            ).first()
                            
                            if existing:
                                # Update existing record
                                set_parts = [f"`{col}` = :{col}" for col in columns if col != pk_column]
                                if set_parts:
                                    set_clause = ", ".join(set_parts)
                                    update_sql = f"UPDATE `{table_name}` SET {set_clause} WHERE `{pk_column}` = :pk"
                                    remote_db.execute(text(update_sql), {**record_dict, "pk": pk_value})
                                    logger.debug(f"Updated record {pk_value} in table {table_name}")
                            else:
                                # Insert new record
                                cols = ", ".join([f"`{col}`" for col in columns])
                                placeholders = ", ".join([f":{col}" for col in columns])
                                insert_sql = f"INSERT INTO `{table_name}` ({cols}) VALUES ({placeholders})"
                                remote_db.execute(text(insert_sql), record_dict)
                                logger.debug(f"Inserted record {pk_value} into table {table_name}")
                            
                            sync_count += 1
                            
                        except Exception as e:
                            logger.error(f"Error syncing record {idx} in table {table_name}: {e}", exc_info=True)
                            continue
                    
                    remote_db.commit()
                    logger.info(f"Successfully synced {len(local_records)} records from table {table_name}")
                
                except Exception as e:
                    logger.error(f"Error syncing table {table_name}: {e}", exc_info=True)
                    remote_db.rollback()
                    continue
            
            logger.info(f"Total records synced: {sync_count}")
            return sync_count
        
        finally:
            local_db.close()
            remote_db.close()
    
    def get_sync_status(self) -> dict:
        """Get sync status information"""
        if not settings.SYNC_ENABLED:
            return {
                "enabled": False,
                "connected": False,
                "message": "Database sync is disabled"
            }
        
        if not self.remote_engine:
            return {
                "enabled": True,
                "connected": False,
                "message": "Remote database connection not initialized"
            }
        
        try:
            with self.remote_engine.connect() as conn:
                result = conn.execute(text("SELECT DATABASE(), VERSION()"))
                row = result.first()
                db_name = row[0] if row else "Unknown"
                version = row[1] if row else "Unknown"
            
            return {
                "enabled": True,
                "connected": True,
                "database": db_name,
                "version": version,
                "host": settings.SYNC_REMOTE_HOST,
                "port": settings.SYNC_REMOTE_PORT,
            }
        except Exception as e:
            return {
                "enabled": True,
                "connected": False,
                "message": str(e)
            }

