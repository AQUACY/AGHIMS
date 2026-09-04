"""
Helpers for merging same-member claims (GHIMS import + HMS).
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple


def normalize_member_no(value: Any) -> str:
    return str(value or "").strip()


def member_no_from_ghims_payload(payload: Optional[dict]) -> str:
    return normalize_member_no((payload or {}).get("memberNo"))


def parse_service_date(value: Any) -> Optional[date]:
    raw = str(value or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        if "T" in raw:
            return datetime.fromisoformat(raw).date()
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def month_key_from_date(value: Any) -> Optional[Tuple[int, int]]:
    parsed = value if isinstance(value, date) and not isinstance(value, datetime) else parse_service_date(value)
    if parsed is None and isinstance(value, datetime):
        parsed = value.date()
    if parsed is None:
        return None
    return parsed.year, parsed.month


def month_label(key: Optional[Tuple[int, int]]) -> Optional[str]:
    if not key:
        return None
    return f"{key[0]:04d}-{key[1]:02d}"


def ghims_payload_dates(payload: Optional[dict]) -> List[str]:
    dates = (payload or {}).get("dateOfService")
    if not isinstance(dates, list):
        return []
    return [str(d).strip() for d in dates if str(d or "").strip()]


def ghims_payload_month_key(payload: Optional[dict]) -> Optional[Tuple[int, int]]:
    for raw in ghims_payload_dates(payload):
        key = month_key_from_date(raw)
        if key:
            return key
    return None


def same_month(left: Any, right: Any) -> bool:
    a = month_key_from_date(left)
    b = month_key_from_date(right)
    if a is None or b is None:
        return True
    return a == b


def _norm_code(value: Any) -> str:
    return str(value or "").strip().upper()


def _as_list(value: Any) -> List[dict]:
    if not isinstance(value, list):
        return []
    return [x for x in value if isinstance(x, dict)]


def _copy_row(row: dict, keys: Iterable[str]) -> dict:
    out = {}
    for key in keys:
        if key in row:
            out[key] = row.get(key)
    return out


def merge_ghims_payloads(
    target_payload: dict,
    source_payload: dict,
    keep_dates_from: str = "target",
) -> Tuple[dict, Dict[str, int], List[str]]:
    """
    Return (merged_payload, items_added, warnings).
    Line-item service dates are preserved. Claim-level dateOfService follows keep_dates_from.
    """
    target = dict(target_payload or {})
    source = dict(source_payload or {})
    warnings: List[str] = []
    added = {"diagnoses": 0, "investigations": 0, "medicines": 0, "procedures": 0}

    target_specialty = _norm_code(target.get("specialtyAttended"))
    source_specialty = _norm_code(source.get("specialtyAttended"))
    if target_specialty and source_specialty and target_specialty != source_specialty:
        warnings.append(
            "Specialties differ — merging may cause NHIA rejection."
        )

    target_att = _norm_code(target.get("typeOfAttendance"))
    source_att = _norm_code(source.get("typeOfAttendance"))
    if target_att and source_att and target_att != source_att:
        warnings.append("Type of attendance differs between the two claims.")

    # Diagnoses: union by GDRG (or icd10+text if no GDRG). Keep target principal.
    diagnoses = _as_list(target.get("diagnoses"))
    seen_dx = set()
    for d in diagnoses:
        key = _norm_code(d.get("gdrgCode")) or f"{_norm_code(d.get('icd10'))}|{str(d.get('diagnosis') or '').strip().lower()}"
        if key:
            seen_dx.add(key)
    for d in _as_list(source.get("diagnoses")):
        key = _norm_code(d.get("gdrgCode")) or f"{_norm_code(d.get('icd10'))}|{str(d.get('diagnosis') or '').strip().lower()}"
        if key and key in seen_dx:
            continue
        if not (
            str(d.get("gdrgCode") or "").strip()
            or str(d.get("icd10") or "").strip()
            or str(d.get("diagnosis") or "").strip()
        ):
            continue
        row = _copy_row(d, ("gdrgCode", "icd10", "diagnosis"))
        row["isPrincipal"] = False
        diagnoses.append(row)
        if key:
            seen_dx.add(key)
        added["diagnoses"] += 1
    target["diagnoses"] = diagnoses

    # Investigations: union by GDRG; keep each added row's original serviceDate.
    investigations = _as_list(target.get("investigations"))
    seen_inv = {_norm_code(i.get("gdrgCode")) for i in investigations if _norm_code(i.get("gdrgCode"))}
    for inv in _as_list(source.get("investigations")):
        code = _norm_code(inv.get("gdrgCode"))
        if not code:
            continue
        if code in seen_inv:
            continue
        investigations.append(_copy_row(inv, ("serviceDate", "gdrgCode")))
        seen_inv.add(code)
        added["investigations"] += 1
    target["investigations"] = investigations

    # Medicines: always add source rows (same drug can appear twice).
    medicines = _as_list(target.get("medicines"))
    for med in _as_list(source.get("medicines")):
        if not (
            str(med.get("medicineCode") or "").strip()
            or str(med.get("_serviceName") or "").strip()
        ):
            continue
        row = dict(med)
        medicines.append(row)
        added["medicines"] += 1
    target["medicines"] = medicines
    if medicines:
        target["includesPharmacy"] = "1"

    # Procedures: union by GDRG.
    procedures = _as_list(target.get("procedures"))
    seen_proc = {_norm_code(p.get("gdrgCode")) for p in procedures if _norm_code(p.get("gdrgCode"))}
    for proc in _as_list(source.get("procedures")):
        code = _norm_code(proc.get("gdrgCode"))
        if not (
            code
            or str(proc.get("description") or "").strip()
            or str(proc.get("icd10") or "").strip()
        ):
            continue
        if code and code in seen_proc:
            continue
        procedures.append(_copy_row(proc, ("serviceDate", "gdrgCode", "description", "icd10", "diagnosis")))
        if code:
            seen_proc.add(code)
        added["procedures"] += 1
    target["procedures"] = procedures

    if keep_dates_from == "source":
        source_dates = ghims_payload_dates(source)
        if source_dates:
            target["dateOfService"] = list(source_dates)

    target["claimCheckCode"] = ""
    return target, added, warnings


def serialize_ghims_related_item(item, batch=None, target_payload: Optional[dict] = None) -> dict:
    payload = item.payload or {}
    dates = ghims_payload_dates(payload)
    specialty = str(payload.get("specialtyAttended") or "").strip()
    target_specialty = str((target_payload or {}).get("specialtyAttended") or "").strip()
    invs = _as_list(payload.get("investigations"))
    meds = _as_list(payload.get("medicines"))
    procs = _as_list(payload.get("procedures"))
    diags = _as_list(payload.get("diagnoses"))
    return {
        "id": item.id,
        "claim_claim_id": item.claim_claim_id,
        "status": item.status,
        "specialty": specialty,
        "attendance_type": str(payload.get("typeOfAttendance") or "").strip(),
        "dateOfService": dates,
        "principal_gdrg": str(payload.get("principalGDRG") or "").strip(),
        "batch_id": item.batch_id,
        "batch_file_name": getattr(batch, "file_name", None) if batch is not None else None,
        "investigations_count": len([i for i in invs if str(i.get("gdrgCode") or "").strip()]),
        "medicines_count": len([
            m for m in meds
            if str(m.get("medicineCode") or "").strip() or str(m.get("_serviceName") or "").strip()
        ]),
        "procedures_count": len([
            p for p in procs
            if str(p.get("gdrgCode") or "").strip() or str(p.get("description") or "").strip()
        ]),
        "diagnoses_count": len([
            d for d in diags
            if str(d.get("gdrgCode") or "").strip() or str(d.get("diagnosis") or "").strip()
        ]),
        "specialty_mismatch": bool(
            specialty and target_specialty and _norm_code(specialty) != _norm_code(target_specialty)
        ),
    }


def service_month_sql_expr(column, dialect_name: str):
    """Return a SQL expression yielding YYYY-MM for a datetime/date column."""
    from sqlalchemy import func

    name = (dialect_name or "").lower()
    if "mysql" in name:
        return func.date_format(column, "%Y-%m")
    return func.strftime("%Y-%m", column)


def find_duplicate_member_months(
    db,
    *,
    start_dt=None,
    end_dt=None,
    exclude_merged: bool = True,
) -> set:
    """
    Return set of (member_no, 'YYYY-MM') for members with 2+ claims in the same month.
    Uses Claim.member_no + Encounter.finalized_at (fallback created_at).
    """
    from sqlalchemy import func, case
    from app.models.claim import Claim, ClaimStatus
    from app.models.encounter import Encounter

    dialect = ""
    try:
        dialect = db.get_bind().dialect.name
    except Exception:
        pass

    visit_dt = case(
        (Encounter.finalized_at.isnot(None), Encounter.finalized_at),
        else_=Encounter.created_at,
    )
    month_col = service_month_sql_expr(visit_dt, dialect)

    q = (
        db.query(Claim.member_no, month_col.label("ym"), func.count(Claim.id))
        .join(Encounter, Claim.encounter_id == Encounter.id)
        .filter(Claim.member_no.isnot(None), Claim.member_no != "")
    )
    if exclude_merged:
        q = q.filter(Claim.status != ClaimStatus.MERGED.value)
    if start_dt is not None:
        q = q.filter(visit_dt >= start_dt)
    if end_dt is not None:
        q = q.filter(visit_dt < end_dt)

    rows = q.group_by(Claim.member_no, month_col).having(func.count(Claim.id) > 1).all()
    out = set()
    for member_no, ym, _cnt in rows:
        m = normalize_member_no(member_no)
        y = str(ym or "").strip()
        if m and y:
            out.add((m, y))
    return out


def merge_hms_claim_details(db, target, source, keep_dates_from: str = "target"):
    """
    Copy line items from source claim onto target.
    Line-item service dates are preserved. keep_dates_from is accepted for API
    parity with GHIMS (HMS has no claim-level dateOfService array).
    Returns (items_added, warnings).
    """
    from app.models.claim_detail import (
        ClaimDiagnosis,
        ClaimInvestigation,
        ClaimPrescription,
        ClaimProcedure,
    )

    warnings: List[str] = []
    added = {"diagnoses": 0, "investigations": 0, "medicines": 0, "procedures": 0}
    _ = keep_dates_from  # reserved for future claim-level date handling

    target_specialty = _norm_code(target.specialty_attended)
    source_specialty = _norm_code(source.specialty_attended)
    if target_specialty and source_specialty and target_specialty != source_specialty:
        warnings.append("Specialties differ — merging may cause NHIA rejection.")

    target_att = _norm_code(target.type_of_attendance)
    source_att = _norm_code(source.type_of_attendance)
    if target_att and source_att and target_att != source_att:
        warnings.append("Type of attendance differs between the two claims.")

    # Diagnoses: union by GDRG (or icd10+description)
    seen_dx = set()
    for d in list(target.claim_diagnoses or []):
        key = _norm_code(d.gdrg_code) or f"{_norm_code(d.icd10)}|{str(d.description or '').strip().lower()}"
        if key:
            seen_dx.add(key)
    max_dx_order = max([int(d.display_order or 0) for d in (target.claim_diagnoses or [])] or [0])
    for d in list(source.claim_diagnoses or []):
        key = _norm_code(d.gdrg_code) or f"{_norm_code(d.icd10)}|{str(d.description or '').strip().lower()}"
        if key and key in seen_dx:
            continue
        if key:
            seen_dx.add(key)
        max_dx_order += 1
        db.add(
            ClaimDiagnosis(
                claim_id=target.id,
                diagnosis_id=d.diagnosis_id,
                description=d.description,
                icd10=d.icd10,
                gdrg_code=d.gdrg_code,
                is_chief=False,
                display_order=max_dx_order,
            )
        )
        added["diagnoses"] += 1

    max_inv = max([int(i.display_order or 0) for i in (target.claim_investigations or [])] or [0])
    for inv in list(source.claim_investigations or []):
        max_inv += 1
        db.add(
            ClaimInvestigation(
                claim_id=target.id,
                investigation_id=inv.investigation_id,
                description=inv.description,
                gdrg_code=inv.gdrg_code,
                service_date=inv.service_date,
                investigation_type=inv.investigation_type,
                display_order=max_inv,
            )
        )
        added["investigations"] += 1

    max_med = max([int(p.display_order or 0) for p in (target.claim_prescriptions or [])] or [0])
    for rx in list(source.claim_prescriptions or []):
        max_med += 1
        db.add(
            ClaimPrescription(
                claim_id=target.id,
                prescription_id=rx.prescription_id,
                description=rx.description,
                code=rx.code,
                price=rx.price,
                quantity=rx.quantity,
                total_cost=rx.total_cost,
                service_date=rx.service_date,
                dose=rx.dose,
                frequency=rx.frequency,
                duration=rx.duration,
                unparsed=rx.unparsed,
                display_order=max_med,
            )
        )
        added["medicines"] += 1

    max_proc = max([int(p.display_order or 0) for p in (target.claim_procedures or [])] or [0])
    for proc in list(source.claim_procedures or []):
        max_proc += 1
        db.add(
            ClaimProcedure(
                claim_id=target.id,
                description=proc.description,
                gdrg_code=proc.gdrg_code,
                icd10=proc.icd10,
                service_date=proc.service_date,
                display_order=max_proc,
            )
        )
        added["procedures"] += 1

    if not target.includes_pharmacy and added["medicines"]:
        target.includes_pharmacy = True

    return added, warnings


def serialize_hms_related_claim(claim, encounter=None, target_specialty: str = "") -> dict:
    enc = encounter or getattr(claim, "encounter", None)
    first_visit = None
    second_visit = None
    if enc and enc.created_at:
        first_visit = enc.created_at.date().isoformat()
    if enc and enc.finalized_at:
        second_visit = enc.finalized_at.date().isoformat()
    specialty = str(claim.specialty_attended or "").strip()
    return {
        "id": claim.id,
        "claim_id": claim.claim_id,
        "status": claim.status,
        "specialty": specialty,
        "attendance_type": str(claim.type_of_attendance or "").strip(),
        "first_visit": first_visit,
        "second_visit": second_visit,
        "principal_gdrg": str(claim.principal_gdrg or "").strip(),
        "investigations_count": len(getattr(claim, "claim_investigations", None) or []),
        "medicines_count": len(getattr(claim, "claim_prescriptions", None) or []),
        "procedures_count": len(getattr(claim, "claim_procedures", None) or []),
        "diagnoses_count": len(getattr(claim, "claim_diagnoses", None) or []),
        "specialty_mismatch": bool(
            specialty and target_specialty and _norm_code(specialty) != _norm_code(target_specialty)
        ),
    }
