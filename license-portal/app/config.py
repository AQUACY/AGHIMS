from pydantic_settings import BaseSettings
from urllib.parse import quote_plus


class Settings(BaseSettings):
    DATABASE_MODE: str = "sqlite"
    SQLITE_DB_PATH: str = "./license_portal.db"
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DATABASE: str = "hms_licenses"
    MYSQL_CHARSET: str = "utf8mb4"
    # If true (default), connect without a schema and run CREATE DATABASE IF NOT EXISTS before opening the app DB.
    MYSQL_AUTOCREATE_DATABASE: bool = True

    ISSUER_SLUG: str = ""
    DISTRIBUTION_ID: str = ""

    RSA_PRIVATE_KEY_FILE: str = ""
    RSA_PRIVATE_KEY_PEM: str = ""

    VERIFY_SHARED_SECRET: str = ""

    PORTAL_ADMIN_USERNAME: str = "license_admin"
    PORTAL_ADMIN_PASSWORD: str = ""
    PORTAL_JWT_SECRET: str = "change-portal-jwt"
    PORTAL_JWT_EXPIRE_MINUTES: int = 480

    HOST: str = "0.0.0.0"
    PORT: int = 9500

    @property
    def DATABASE_URL(self) -> str:
        if self.DATABASE_MODE.lower() == "mysql":
            encoded_password = quote_plus(self.MYSQL_PASSWORD)
            return (
                f"mysql+pymysql://{self.MYSQL_USER}:{encoded_password}"
                f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
                f"?charset={self.MYSQL_CHARSET}"
            )
        return f"sqlite:///{self.SQLITE_DB_PATH}"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
