import re

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker, declarative_base
from urllib.parse import quote_plus

from app.config import settings


def _ensure_mysql_database_exists() -> None:
    if settings.DATABASE_MODE.lower() != "mysql":
        return
    if not getattr(settings, "MYSQL_AUTOCREATE_DATABASE", True):
        return
    db_name = (settings.MYSQL_DATABASE or "").strip()
    if not db_name or not re.match(r"^[a-zA-Z0-9_]+$", db_name):
        raise ValueError(
            "MYSQL_DATABASE must be a simple identifier (letters, digits, underscore) for auto-create."
        )
    encoded_password = quote_plus(settings.MYSQL_PASSWORD)
    server_url = (
        f"mysql+pymysql://{settings.MYSQL_USER}:{encoded_password}"
        f"@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/"
        f"?charset={settings.MYSQL_CHARSET}"
    )
    admin_engine = create_engine(server_url, pool_pre_ping=True, echo=False)
    try:
        with admin_engine.connect() as conn:
            conn.execute(
                text(
                    f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            )
            conn.commit()
    except OperationalError as e:
        raise RuntimeError(
            f"Could not auto-create MySQL database `{db_name}`: {e}"
        ) from e
    finally:
        admin_engine.dispose()


_ensure_mysql_database_exists()

connect_args = {}
if settings.DATABASE_MODE.lower() == "sqlite":
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True if settings.DATABASE_MODE.lower() == "mysql" else False,
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
