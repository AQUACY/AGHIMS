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
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # 30 minutes
    
    # Facility Settings
    FACILITY_CODE: str = "ER-A25"
    
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
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

