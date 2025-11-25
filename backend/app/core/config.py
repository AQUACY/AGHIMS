"""
Application configuration settings
"""
from pydantic_settings import BaseSettings
from urllib.parse import quote_plus


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database Mode: "sqlite" or "mysql"
    DATABASE_MODE: str = "sqlite"
    
    # SQLite Configuration
    SQLITE_DB_PATH: str = "./hms.db"
    
    # MySQL Configuration
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DATABASE: str = "hms"
    MYSQL_CHARSET: str = "utf8mb4"
    
    # JWT Settings
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour
    
    # Facility Settings
    FACILITY_CODE: str = "ER-A25"
    
    # Analyzer Integration Settings (Sysmex XN-330)
    ANALYZER_ENABLED: bool = False  # Set to True to enable analyzer integration
    ANALYZER_HOST: str = "0.0.0.0"  # Host to bind TCP server (0.0.0.0 for all interfaces)
    ANALYZER_PORT: int = 5150  # TCP port to listen on
    ANALYZER_EQUIPMENT_IP: str = "10.10.16.34"  # Equipment IP (for reference/logging)
    ANALYZER_TIMEOUT: int = 30  # Connection timeout in seconds
    
    # Database Backup & Sync Settings
    BACKUP_ENABLED: bool = True  # Enable automatic backups
    BACKUP_DIR: str = "./backups"  # Directory to store backups
    BACKUP_RETENTION_DAYS: int = 30  # Keep backups for this many days
    
    # Scheduled Backup Settings
    SCHEDULED_BACKUP_ENABLED: bool = False  # Enable scheduled backups
    SCHEDULED_BACKUP_TIME: str = "02:00"  # Time(s) to run daily backup (HH:MM format, comma-separated for multiple, e.g., "07:00,19:00")
    SCHEDULED_BACKUP_INTERVAL_HOURS: int = 24  # Backup interval in hours (deprecated, use SCHEDULED_BACKUP_TIME instead)
    
    # Online Sync Settings (Remote MySQL Database)
    SYNC_ENABLED: bool = False  # Enable online sync to remote database
    SYNC_REMOTE_HOST: str = ""  # Remote MySQL host
    SYNC_REMOTE_PORT: int = 3306  # Remote MySQL port
    SYNC_REMOTE_USER: str = ""  # Remote MySQL user
    SYNC_REMOTE_PASSWORD: str = ""  # Remote MySQL password
    SYNC_REMOTE_DATABASE: str = ""  # Remote MySQL database name
    SYNC_INTERVAL_MINUTES: int = 60  # Sync interval in minutes (default: 1 hour)
    
    # Application Date Override Settings
    # When set, the application will use this date instead of the system date
    # Format: "YYYY-MM-DD" or "YYYY-MM-DD HH:MM:SS" (e.g., "2024-01-15" or "2024-01-15 10:30:00")
    # Leave empty to use system date
    APPLICATION_REFERENCE_DATE: str = ""  # Override date for application (empty = use system date)
    
    @property
    def DATABASE_URL(self) -> str:
        """Generate DATABASE_URL based on DATABASE_MODE"""
        if self.DATABASE_MODE.lower() == "mysql":
            # URL encode password to handle special characters
            encoded_password = quote_plus(self.MYSQL_PASSWORD)
            return (
                f"mysql+pymysql://{self.MYSQL_USER}:{encoded_password}"
                f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
                f"?charset={self.MYSQL_CHARSET}"
            )
        else:  # Default to SQLite
            return f"sqlite:///{self.SQLITE_DB_PATH}"
    
    @property
    def SYNC_DATABASE_URL(self) -> str:
        """Generate remote sync DATABASE_URL"""
        if not self.SYNC_ENABLED or not self.SYNC_REMOTE_HOST:
            return ""
        encoded_password = quote_plus(self.SYNC_REMOTE_PASSWORD)
        return (
            f"mysql+pymysql://{self.SYNC_REMOTE_USER}:{encoded_password}"
            f"@{self.SYNC_REMOTE_HOST}:{self.SYNC_REMOTE_PORT}/{self.SYNC_REMOTE_DATABASE}"
            f"?charset={self.MYSQL_CHARSET}"
        )
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

