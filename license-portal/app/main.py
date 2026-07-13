"""
Standalone license portal: separate database from HMS, RSA-signed license files,
and an online verification endpoint for HMS installations.
"""
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.crypto_sign import build_signed_document, resolved_private_key_pem
from app.database import Base, engine, get_db
from app.models import LicenseRecord

ALGO = "HS256"


def create_portal_token(subject: str) -> str:
    exp = datetime.utcnow() + timedelta(minutes=max(15, int(settings.PORTAL_JWT_EXPIRE_MINUTES)))
    return jwt.encode(
        {"sub": subject, "exp": exp},
        settings.PORTAL_JWT_SECRET,
        algorithm=ALGO,
    )


def decode_portal_token(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.PORTAL_JWT_SECRET, algorithms=[ALGO])
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
        return str(sub)
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")


def get_portal_user(authorization: str = Header(None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    return decode_portal_token(token)


app = FastAPI(title="HMS License Portal", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.is_dir():
    app.mount("/ui", StaticFiles(directory=str(static_dir), html=True), name="ui")


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


@app.get("/")
def root():
    return {"service": "license-portal", "ui": "/ui/", "api_docs": "/docs"}


class LicenseCreate(BaseModel):
    customer_label: str = Field(..., min_length=1, max_length=255)
    facility_code: str | None = Field(None, max_length=64)
    valid_from: datetime
    valid_until: datetime
    notes: str | None = None


class LicenseOut(BaseModel):
    id: int
    license_id: str
    customer_label: str
    facility_code: str | None
    valid_from: datetime
    valid_until: datetime
    notes: str | None

    class Config:
        from_attributes = True


@app.post("/api/portal/login")
def portal_login(form: OAuth2PasswordRequestForm = Depends()):
    if form.username != settings.PORTAL_ADMIN_USERNAME:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    expected = settings.PORTAL_ADMIN_PASSWORD or ""
    if not expected:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "PORTAL_ADMIN_PASSWORD is not set",
        )
    if form.password != expected:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    token = create_portal_token(form.username)
    return {"access_token": token, "token_type": "bearer"}


@app.get("/api/portal/licenses", response_model=list[LicenseOut])
def list_licenses(
    db: Session = Depends(get_db),
    _user: str = Depends(get_portal_user),
):
    rows = db.query(LicenseRecord).order_by(LicenseRecord.id.desc()).all()
    return rows


@app.post("/api/portal/licenses", response_model=LicenseOut)
def create_license(
    data: LicenseCreate,
    db: Session = Depends(get_db),
    _user: str = Depends(get_portal_user),
):
    lid = str(uuid.uuid4())
    fc = (data.facility_code or "").strip() or None
    row = LicenseRecord(
        license_id=lid,
        customer_label=data.customer_label.strip(),
        facility_code=fc,
        valid_from=data.valid_from,
        valid_until=data.valid_until,
        notes=(data.notes or "").strip() or None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@app.get("/api/portal/licenses/{license_id}/signed.json")
def download_signed_license(
    license_id: str,
    db: Session = Depends(get_db),
    _user: str = Depends(get_portal_user),
):
    row = db.query(LicenseRecord).filter(LicenseRecord.license_id == license_id).first()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "License not found")
    issuer = (settings.ISSUER_SLUG or "").strip()
    if not issuer:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "ISSUER_SLUG is not configured")
    pk_pem = resolved_private_key_pem(settings)
    claims = {
        "v": 1,
        "license_id": row.license_id,
        "customer_label": row.customer_label,
        "facility_code": (row.facility_code or "").strip() or None,
        "valid_from": row.valid_from.isoformat() + "Z",
        "valid_until": row.valid_until.isoformat() + "Z",
        "issuer_slug": issuer,
    }
    dist = (settings.DISTRIBUTION_ID or "").strip()
    if dist:
        claims["distribution_id"] = dist
    return build_signed_document(claims, pk_pem)


class VerifyBody(BaseModel):
    license_id: str
    facility_code: str | None = None


@app.post("/api/verify/online")
def verify_online(
    body: VerifyBody,
    db: Session = Depends(get_db),
    x_license_server_key: str = Header("", alias="X-License-Server-Key"),
):
    secret = (settings.VERIFY_SHARED_SECRET or "").strip()
    if not secret or x_license_server_key.strip() != secret:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid license server key")

    row = (
        db.query(LicenseRecord)
        .filter(LicenseRecord.license_id == (body.license_id or "").strip())
        .first()
    )
    if not row:
        return {"ok": False, "reason": "unknown_license"}
    now = datetime.utcnow()
    if now < row.valid_from or now > row.valid_until:
        return {"ok": False, "reason": "out_of_window"}
    fc = (row.facility_code or "").strip()
    if fc:
        req_fc = (body.facility_code or "").strip()
        if req_fc != fc:
            return {"ok": False, "reason": "facility_mismatch"}
    return {
        "ok": True,
        "valid_until": row.valid_until.isoformat() + "Z",
    }
