from pydantic_settings import BaseSettings
from urllib.parse import quote_plus


class Settings(BaseSettings):
    DATABASE_MODE: str = "sqlite"
    SQLITE_DB_PATH: str = "./suhum.db"
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DATABASE: str = "suhum"
    MYSQL_CHARSET: str = "utf8mb4"
    MYSQL_AUTOCREATE_DATABASE: bool = True

    JWT_SECRET: str = "change-suhum-jwt-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480

    CORS_ORIGINS: str = "http://localhost:9002,http://127.0.0.1:9002"

    HOST: str = "0.0.0.0"
    PORT: int = 8100

    FACILITY_NAME: str = "Suhum Claims"
    FACILITY_CODE: str = ""

    # NHIA CCC (NeHFAMS OTAC API)
    NHIA_INTEGRATION_ENABLED: bool = True
    NHIA_CCC_BASE_URL: str = "https://otac.nhia.gov.gh"
    NHIA_USERNAME: str = ""
    NHIA_PASSWORD: str = ""
    NHIA_DEFAULT_OTAC: str = ""
    NHIA_API_KEY: str = ""
    NHIA_API_SECRET: str = ""
    NHIA_SESSION_TTL_SECONDS: int = 1800
    NHIA_REQUEST_TIMEOUT_SECONDS: float = 30.0
    NHIA_SSL_VERIFY: bool = True
    NHIA_SSL_CA_BUNDLE: str = ""
    NHIA_DEFAULT_CARD_TYPE: str = "NHISCARD"

    # Bootstrap first admin when users table is empty
    SUHUM_ADMIN_USERNAME: str = "admin"
    SUHUM_ADMIN_PASSWORD: str = "suhum123"

    # Price list sync from main HMS (used by scripts/sync_price_list_from_main.py)
    MAIN_DATABASE_URL: str = ""

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

    @property
    def cors_origin_list(self) -> list[str]:
        raw = (self.CORS_ORIGINS or "").strip()
        if not raw:
            return []
        return [x.strip() for x in raw.split(",") if x.strip()]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
