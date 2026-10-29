"""
Confidential consultations: prepared codes, and identity hidden at service points.

Claim generation is a separate path. Claim officers, and doctors, PAs, and
admins opening a claim, still receive the real client.
"""
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.user import User

REGISTER_ROLES = ("Admin", "Doctor", "PA", "Claims")
CLAIM_REVEAL_ROLES = ("Admin", "Doctor", "PA", "Claims")
CODE_POOL_ROLES = ("Admin", "Records")
ISSUE_ROLES = ("Admin", "Records", "Doctor", "PA")

_IDENTITY_CLEAR = (
    "patient_card_number",
    "patient_insurance_id",
    "patient_age",
    "patient_gender",
    "patient_address",
    "patient_surname",
    "patient_other_names",
    "ccc_number",
)


def user_has_role(user: User, allowed: tuple, db: Optional[Session] = None) -> bool:
    if user is None:
        return False
    if getattr(user, "role", None) in allowed:
        return True
    extras = getattr(user, "additional_roles", None)
    if extras:
        for entry in extras:
            role = getattr(entry, "role", entry)
            if role in allowed:
                return True
        return False
    if db is None:
        return False
    from sqlalchemy.orm import joinedload

    loaded = (
        db.query(User)
        .options(joinedload(User.additional_roles))
        .filter(User.id == user.id)
        .first()
    )
    if not loaded or not loaded.additional_roles:
        return False
    return any(entry.role in allowed for entry in loaded.additional_roles)


def format_code(prefix: str, number: int, pad: int) -> str:
    cleaned = "".join(ch for ch in (prefix or "").upper() if ch.isalnum())
    if not cleaned:
        raise ValueError("Code prefix is required")
    if number < 1:
        raise ValueError("Code numbers start at 1")
    if pad < 1 or pad > 8:
        raise ValueError("Code padding must be between 1 and 8")
    return f"{cleaned}{number:0{pad}d}"


def redact_service_payload(payload: dict, *, confidential: bool, code: Optional[str], reveal: bool) -> dict:
    """Replace identity with the visit code on service-point payloads."""
    data = dict(payload)
    data["is_confidential"] = bool(confidential)
    data["confidential_code"] = code if confidential else None
    if not confidential or reveal:
        return data
    label = code or "Confidential"
    if "patient_name" in data:
        data["patient_name"] = label
    for key in _IDENTITY_CLEAR:
        if key in data:
            data[key] = None
    return data


def masked_patient_label(db: Optional[Session], encounter, patient_name: str, patient_card: Optional[str]):
    """Service-point label. Confidential visits show the code and no card."""
    if not encounter or not getattr(encounter, "is_confidential", False):
        return patient_name, patient_card, False, None
    code = code_text(encounter)
    if not code and db is not None and getattr(encounter, "confidential_code_id", None):
        from app.models.confidential import ConfidentialCode

        row = db.query(ConfidentialCode).filter(ConfidentialCode.id == encounter.confidential_code_id).first()
        code = row.code if row else None
    label = code or "Confidential"
    return label, None, True, label


def service_point_name_filter(search_term: str):
    """Name and card match ordinary visits. Confidential visits match the code only."""
    from sqlalchemy import and_, or_

    from app.models.confidential import ConfidentialCode
    from app.models.encounter import Encounter
    from app.models.patient import Patient

    return or_(
        and_(
            or_(Encounter.is_confidential.is_(False), Encounter.is_confidential.is_(None)),
            or_(
                Patient.card_number.ilike(search_term),
                Patient.name.ilike(search_term),
                Patient.surname.ilike(search_term),
            ),
        ),
        and_(Encounter.is_confidential.is_(True), ConfidentialCode.code.ilike(search_term)),
    )


def code_text(encounter) -> Optional[str]:
    if not encounter or not getattr(encounter, "is_confidential", False):
        return None
    link = getattr(encounter, "code_link", None)
    if link is not None and getattr(link, "code", None):
        return link.code
    return None


def ensure_confidential_schema(db: Session) -> None:
    """Add confidential columns on databases created before this module."""
    bind = db.get_bind()
    dialect = bind.dialect.name if hasattr(bind, "dialect") else ""
    flag_type = "TINYINT(1) NOT NULL DEFAULT 0" if dialect == "mysql" else "INTEGER NOT NULL DEFAULT 0"
    id_type = "INTEGER NULL"
    specs = [
        ("encounters", "is_confidential", flag_type),
        ("encounters", "confidential_code_id", id_type),
    ]
    for table, col, typ in specs:
        try:
            db.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {typ}"))
            db.flush()
        except Exception as exc:
            err = str(exc).lower()
            if (
                "duplicate column" in err
                or "already exists" in err
                or "1060" in err
            ):
                continue
            if "doesn't exist" in err or "no such table" in err:
                continue
            raise
