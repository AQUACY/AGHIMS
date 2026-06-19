"""
Suhum — standalone GHIMS XML import and price list portal.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.database import Base, engine
from app.core.dependencies import hash_password
from app.database import SessionLocal
from app.models.user import User
import app.models  # noqa: F401 — register all tables for create_all
from app.api import auth, ghims_import, price_list, vetting_guide

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Suhum", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(price_list.router, prefix="/api")
app.include_router(ghims_import.router, prefix="/api")
app.include_router(vetting_guide.router, prefix="/api")


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    _ensure_default_admin()


def _ensure_default_admin():
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            user = User(
                username=settings.SUHUM_ADMIN_USERNAME,
                full_name="Administrator",
                hashed_password=hash_password(settings.SUHUM_ADMIN_PASSWORD),
                is_admin=True,
            )
            db.add(user)
            db.commit()
            logger.info(
                "Created default admin user '%s' (change password after first login)",
                settings.SUHUM_ADMIN_USERNAME,
            )
    finally:
        db.close()


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "suhum"}
