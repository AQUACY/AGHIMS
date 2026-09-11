"""
Month workbench for GHIMS-approved NHIA claims.

GHIMS "Sponsors to vet" NHIS totals = Visitation WHERE WorkingMonthID AND SponsorID=I101
(not only vwNHIAClaimLines). Lines fill payload details; header-only rows stay sparse.
including claims that may not yet have NHIA lines. Lines still come from
vwNHIAClaimLines when present.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.claim_xml_import import ClaimXmlImportBatch, ClaimXmlImportItem
from app.services.ghims_live_compare import (
    GhimsLiveConfigError,
    _connect,
    _rows_as_dicts,
)


SOURCE_GHIMS_LIVE = "ghims_live"

# GHIMS Sponsors-to-vet "NATIONAL HEALTH INSURANCE SCHEME" / I101
NHIS_SPONSOR_ID = "I101"


def month_key_from_bill_id(bill_month_id: str) -> str:
    """MTH202609 -> 2026-09"""
    s = str(bill_month_id or "").strip().upper()
    if s.startswith("MTH") and len(s) >= 9 and s[3:9].isdigit():
        return f"{s[3:7]}-{s[7:9]}"
    return s.lower()


def bill_id_from_month_key(month_key: str) -> str:
    """2026-09 -> MTH202609"""
    s = str(month_key or "").strip()
    parts = s.replace("_", "-").split("-")
    if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
        return f"MTH{parts[0]}{parts[1].zfill(2)}"
    if s.upper().startswith("MTH"):
        return s.upper()
    return s


def month_label(month_key: str) -> str:
    key = str(month_key or "").strip()
    try:
        dt = datetime.strptime(key, "%Y-%m")
        return dt.strftime("%B %Y claims")
    except ValueError:
        return f"{key} claims"


def _iso_day(val: Any) -> str:
    if not val:
        return ""
    s = str(val).strip()
    if "T" in s:
        s = s.split("T", 1)[0]
    if " " in s:
        s = s.split(" ", 1)[0]
    return s[:10]


def _is_ipd(type_of_service: Any) -> bool:
    tos = str(type_of_service or "").strip().lower()
    return tos.startswith("in") or tos == "ipd"


def _payload_from_nhia_lines(lines: List[Dict[str, Any]]) -> Dict[str, Any]:
    h = lines[0]
    diagnoses: List[Dict[str, Any]] = []
    medicines: List[Dict[str, Any]] = []
    procedures: List[Dict[str, Any]] = []
    investigations: List[Dict[str, Any]] = []
    seen_dx = set()
    seen_med = set()
    seen_proc = set()
    seen_inv = set()

    tos = str(h.get("typeOfService") or "").strip()
    if tos.lower().startswith("in"):
        tos_norm = "IPD"
    elif tos.lower().startswith("out"):
        tos_norm = "OPD"
    else:
        tos_norm = tos or "OPD"

    adm = _iso_day(h.get("admissionDate"))
    dis = _iso_day(h.get("dischargeDate") or h.get("_visitDate2"))

    # IPD: admission + discharge only (do not expand spell into daily rows).
    # OPD: actual service dates only (do not invent a range).
    dates: List[str] = []
    if _is_ipd(tos_norm) or _is_ipd(tos):
        if adm:
            dates.append(adm)
        if dis and dis not in dates:
            dates.append(dis)
    else:
        for r in lines:
            day = _iso_day(r.get("serviceDate") or r.get("admissionDate"))
            if day and day not in dates:
                dates.append(day)
        if not dates and adm:
            dates.append(adm)

    for r in lines:
        day = _iso_day(r.get("serviceDate") or r.get("admissionDate"))
        a_type = str(r.get("aType") or "").strip().lower()
        med_code = str(r.get("medicineCode") or "").strip()
        drug_name = str(r.get("medicineName") or r.get("drugName") or "").strip()
        gdrg = str(r.get("gdrgCode") or r.get("code") or "").strip()
        icd10 = str(r.get("icd10") or "").strip()
        diagnosis = str(r.get("diagnosis") or r.get("description") or r.get("serviceName") or "").strip()
        is_proc = bool(r.get("isProcedure"))

        if med_code or a_type in ("medicine", "drug", "pharmacy") or (drug_name and not gdrg):
            key = (med_code, day, drug_name)
            if key in seen_med:
                continue
            seen_med.add(key)
            rx = str(r.get("rx") or "").strip()
            medicines.append({
                "medicineCode": med_code,
                "_serviceName": drug_name,
                "dispensedQty": str(r.get("qty") or "").strip(),
                "serviceDate": day,
                "prescription": {
                    "dose": "",
                    "frequency": "",
                    "duration": "",
                    "unparsed": rx,
                },
            })
            continue

        if a_type == "diagnosis" or (icd10 and not is_proc and not med_code and a_type != "investigation"):
            key = (icd10, gdrg, diagnosis)
            if key in seen_dx:
                continue
            seen_dx.add(key)
            diagnoses.append({
                "gdrgCode": gdrg,
                "icd10": icd10,
                "diagnosis": diagnosis,
            })
            continue

        if is_proc or a_type == "procedure":
            key = (gdrg, day, diagnosis)
            if key in seen_proc:
                continue
            seen_proc.add(key)
            procedures.append({
                "serviceDate": day,
                "gdrgCode": gdrg,
                "description": diagnosis or str(r.get("serviceName") or ""),
                "icd10": icd10,
                "diagnosis": diagnosis,
            })
            continue

        if gdrg or a_type in ("investigation", "lab", "service"):
            key = (gdrg, day)
            if key in seen_inv:
                continue
            seen_inv.add(key)
            investigations.append({
                "serviceDate": day,
                "gdrgCode": gdrg,
                "_serviceName": str(r.get("serviceName") or diagnosis),
            })

    dates = sorted({d for d in dates if d})
    pharmacy = h.get("hasPharmacy")
    includes = "1" if str(pharmacy) in ("1", "True", "true", "Yes") or medicines else "0"
    principal = ""
    if diagnoses:
        principal = diagnoses[0].get("gdrgCode") or ""
    elif procedures:
        principal = procedures[0].get("gdrgCode") or ""

    return {
        "claimID": str(h.get("claimID") or "").strip(),
        "claimCheckCode": str(h.get("claimCheckCode") or "").strip(),
        "preAuthorizationCodes": "",
        "physicianID": "",
        "memberNo": str(h.get("memberNo") or h.get("_visitInsuranceNo") or h.get("InsuranceNo") or "").strip(),
        "cardSerialNo": "",
        "surname": str(h.get("surname") or "").strip(),
        "otherNames": str(h.get("otherNames") or "").strip(),
        "dateOfBirth": _iso_day(h.get("dateOfBirth")),
        "gender": str(h.get("gender") or "").strip(),
        "hospitalRecNo": str(h.get("hospitalRecNo") or "").strip(),
        "isDependant": "",
        "typeOfService": tos_norm,
        "isUnbundled": "",
        "includesPharmacy": includes,
        "typeOfAttendance": str(h.get("typeOfAttendance") or "").strip(),
        "serviceOutcome": "",
        "specialtyAttended": "",
        "principalGDRG": principal,
        "dateOfService": dates,
        "diagnoses": diagnoses,
        "investigations": investigations,
        "medicines": medicines,
        "procedures": procedures,
        "_ghimsBillMonthID": str(h.get("billMonthID") or "").strip(),
        "_admissionDate": adm,
        "_dischargeDate": dis,
    }


def _sparse_payload_from_header(h: Dict[str, Any]) -> Dict[str, Any]:
    """Header-only claim (e.g. ON ADMISSION / no NHIA lines yet)."""
    tos = str(h.get("typeOfService") or "").strip()
    vt = str(h.get("_visitTypeID") or "").upper()
    if tos.lower().startswith("in") or vt.endswith("-V002") or "IN-PATIENT" in vt or vt == "VST002":
        tos_norm = "IPD"
    elif tos.lower().startswith("out") or vt.endswith("-V001") or "OUT-PATIENT" in vt or vt == "VST001":
        tos_norm = "OPD"
    else:
        tos_norm = tos or "OPD"
    adm = _iso_day(h.get("admissionDate") or h.get("VisitDate") or h.get("visitDate"))
    dis = _iso_day(h.get("dischargeDate") or h.get("_visitDate2"))
    dates: List[str] = []
    if _is_ipd(tos_norm):
        if adm:
            dates.append(adm)
        if dis and dis not in dates:
            dates.append(dis)
    else:
        if adm:
            dates.append(adm)
    return {
        "claimID": str(h.get("claimID") or h.get("VisitationID") or "").strip(),
        "claimCheckCode": str(h.get("claimCheckCode") or "").strip(),
        "preAuthorizationCodes": "",
        "physicianID": "",
        "memberNo": str(h.get("memberNo") or "").strip(),
        "cardSerialNo": "",
        "surname": str(h.get("surname") or "").strip(),
        "otherNames": str(h.get("otherNames") or "").strip(),
        "dateOfBirth": _iso_day(h.get("dateOfBirth")),
        "gender": str(h.get("gender") or "").strip(),
        "hospitalRecNo": str(h.get("hospitalRecNo") or "").strip(),
        "isDependant": "",
        "typeOfService": tos_norm,
        "isUnbundled": "",
        "includesPharmacy": "0",
        "typeOfAttendance": str(h.get("typeOfAttendance") or "").strip(),
        "serviceOutcome": "",
        "specialtyAttended": "",
        "principalGDRG": "",
        "dateOfService": dates,
        "diagnoses": [],
        "investigations": [],
        "medicines": [],
        "procedures": [],
        "_ghimsBillMonthID": str(h.get("billMonthID") or h.get("WorkingMonthID") or "").strip(),
        "_admissionDate": adm,
        "_dischargeDate": dis,
        "_sparseHeader": True,
    }


def _refresh_date_fields(existing_payload: Optional[Dict[str, Any]], rebuilt: Dict[str, Any]) -> Dict[str, Any]:
    """Update only date-of-service / admission / discharge / typeOfService on existing payloads."""
    payload = dict(existing_payload or {})
    payload["dateOfService"] = rebuilt.get("dateOfService") or []
    payload["_admissionDate"] = rebuilt.get("_admissionDate") or ""
    payload["_dischargeDate"] = rebuilt.get("_dischargeDate") or ""
    if rebuilt.get("typeOfService"):
        payload["typeOfService"] = rebuilt["typeOfService"]
    return payload


def _visitation_month_headers(bill_id: str) -> Optional[List[Dict[str, Any]]]:
    """Return Visitation rows for WorkingMonthID if the table/columns exist; else None."""
    cn = _connect()
    try:
        cur = cn.cursor()
        cur.execute(
            """
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME='Visitation'
            """
        )
        cols = {str(r[0]) for r in cur.fetchall()}
        if not cols or "WorkingMonthID" not in cols or "VisitationID" not in cols:
            return None

        # Optional patient/name joins — keep query resilient.
        select_bits = [
            "CAST(v.VisitationID AS varchar(64)) AS claimID",
            "v.WorkingMonthID AS billMonthID",
        ]
        if "ClaimCheckCode" in cols:
            select_bits.append("v.ClaimCheckCode AS claimCheckCode")
        elif "CCC" in cols:
            select_bits.append("v.CCC AS claimCheckCode")
        else:
            select_bits.append("CAST(NULL AS varchar(64)) AS claimCheckCode")

        if "AdmissionDate" in cols:
            select_bits.append("v.AdmissionDate AS admissionDate")
        elif "VisitDate" in cols:
            select_bits.append("v.VisitDate AS admissionDate")
        else:
            select_bits.append("CAST(NULL AS datetime) AS admissionDate")

        if "DischargeDate" in cols:
            select_bits.append("v.DischargeDate AS dischargeDate")
        else:
            select_bits.append("CAST(NULL AS datetime) AS dischargeDate")

        if "TypeOfService" in cols:
            select_bits.append("v.TypeOfService AS typeOfService")
        elif "ServiceType" in cols:
            select_bits.append("v.ServiceType AS typeOfService")
        else:
            select_bits.append("CAST(NULL AS varchar(64)) AS typeOfService")

        if "TypeOfAttendance" in cols:
            select_bits.append("v.TypeOfAttendance AS typeOfAttendance")
        else:
            select_bits.append("CAST(NULL AS varchar(64)) AS typeOfAttendance")

        # Patient fields often live on Patient / Client join
        join_sql = ""
        if "PatientID" in cols:
            # discover Patient columns
            cur.execute(
                """
                SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME='Patient'
                """
            )
            pcols = {str(r[0]) for r in cur.fetchall()}
            if pcols:
                join_sql = " LEFT JOIN dbo.Patient p ON p.PatientID = v.PatientID "
                select_bits.append(
                    ("p.Surname" if "Surname" in pcols else "CAST(NULL AS varchar(128))") + " AS surname"
                )
                other = "p.OtherNames" if "OtherNames" in pcols else (
                    "p.FirstName" if "FirstName" in pcols else "CAST(NULL AS varchar(128))"
                )
                select_bits.append(f"{other} AS otherNames")
                memb = "p.MemberNo" if "MemberNo" in pcols else (
                    "p.NHISNo" if "NHISNo" in pcols else "CAST(NULL AS varchar(64))"
                )
                select_bits.append(f"{memb} AS memberNo")
                hosp = "p.HospitalRecNo" if "HospitalRecNo" in pcols else (
                    "p.FolderNo" if "FolderNo" in pcols else "CAST(NULL AS varchar(64))"
                )
                select_bits.append(f"{hosp} AS hospitalRecNo")
                select_bits.append(
                    ("p.DateOfBirth" if "DateOfBirth" in pcols else "CAST(NULL AS datetime)") + " AS dateOfBirth"
                )
                select_bits.append(
                    ("p.Gender" if "Gender" in pcols else "CAST(NULL AS varchar(32))") + " AS gender"
                )
            else:
                select_bits.extend([
                    "CAST(NULL AS varchar(128)) AS surname",
                    "CAST(NULL AS varchar(128)) AS otherNames",
                    "CAST(NULL AS varchar(64)) AS memberNo",
                    "CAST(NULL AS varchar(64)) AS hospitalRecNo",
                    "CAST(NULL AS datetime) AS dateOfBirth",
                    "CAST(NULL AS varchar(32)) AS gender",
                ])
        else:
            select_bits.extend([
                "CAST(NULL AS varchar(128)) AS surname",
                "CAST(NULL AS varchar(128)) AS otherNames",
                "CAST(NULL AS varchar(64)) AS memberNo",
                "CAST(NULL AS varchar(64)) AS hospitalRecNo",
                "CAST(NULL AS datetime) AS dateOfBirth",
                "CAST(NULL AS varchar(32)) AS gender",
            ])

        sql = f"""
            SELECT {", ".join(select_bits)}
            FROM dbo.Visitation v
            {join_sql}
            WHERE v.WorkingMonthID = ?
              AND (v.SponsorID = ? OR v.InsuranceSchemeID LIKE ?)
            ORDER BY v.VisitationID
        """
        cur.execute(sql, (bill_id, NHIS_SPONSOR_ID, f"%{NHIS_SPONSOR_ID}%"))
        return _rows_as_dicts(cur)
    except Exception:
        return None
    finally:
        cn.close()


def list_ghims_bill_months() -> List[Dict[str, Any]]:
    """Month list counts — prefer Visitation.WorkingMonthID to match GHIMS Sponsors-to-vet totals."""
    cn = _connect()
    try:
        cur = cn.cursor()
        # Prefer Visitation counts when available
        used_visitation = False
        rows: List[Dict[str, Any]] = []
        try:
            cur.execute(
                """
                SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME='Visitation' AND COLUMN_NAME='WorkingMonthID'
                """
            )
            if cur.fetchone():
                cur.execute(
                    """
                    SELECT
                      v.WorkingMonthID AS billMonthID,
                      wm.WorkingMonthName,
                      wm.WorkMonth,
                      COUNT(*) AS claim_count
                    FROM dbo.Visitation v
                    LEFT JOIN dbo.WorkingMonth wm ON wm.WorkingMonthID = v.WorkingMonthID
                    WHERE v.WorkingMonthID IS NOT NULL AND LTRIM(RTRIM(v.WorkingMonthID)) <> ''
                      AND (v.SponsorID = ? OR v.InsuranceSchemeID LIKE ?)
                    GROUP BY v.WorkingMonthID, wm.WorkingMonthName, wm.WorkMonth
                    ORDER BY v.WorkingMonthID DESC
                    """,
                    (NHIS_SPONSOR_ID, f"%{NHIS_SPONSOR_ID}%"),
                )
                rows = _rows_as_dicts(cur)
                used_visitation = True
        except Exception:
            used_visitation = False
            rows = []

        if not used_visitation:
            cur.execute(
                """
                SELECT
                  l.billMonthID,
                  wm.WorkingMonthName,
                  wm.WorkMonth,
                  COUNT(DISTINCT l.claimID) AS claim_count
                FROM dbo.vwNHIAClaimLines l
                LEFT JOIN dbo.WorkingMonth wm ON wm.WorkingMonthID = l.billMonthID
                WHERE l.billMonthID IS NOT NULL AND LTRIM(RTRIM(l.billMonthID)) <> ''
                GROUP BY l.billMonthID, wm.WorkingMonthName, wm.WorkMonth
                ORDER BY l.billMonthID DESC
                """
            )
            rows = _rows_as_dicts(cur)
    finally:
        cn.close()

    out = []
    for r in rows:
        bill_id = str(r.get("billMonthID") or "").strip()
        key = month_key_from_bill_id(bill_id)
        name = str(r.get("WorkMonth") or r.get("WorkingMonthName") or "").strip()
        label = month_label(key) if key.count("-") == 1 else (f"{name} claims" if name else bill_id)
        out.append({
            "month_key": key,
            "bill_month_id": bill_id,
            "label": label,
            "ghims_count": int(r.get("claim_count") or 0),
            "count_source": "visitation" if used_visitation else "vwNHIAClaimLines",
        })
    return out


def fetch_month_claim_headers(month_key: str) -> List[Dict[str, Any]]:
    """Headers for the month — Visitation universe when available, else distinct lines."""
    bill_id = bill_id_from_month_key(month_key)
    vis = _visitation_month_headers(bill_id)
    if vis is not None:
        return vis

    cn = _connect()
    try:
        cur = cn.cursor()
        cur.execute(
            """
            SELECT
              l.claimID,
              MAX(l.claimCheckCode) AS claimCheckCode,
              MAX(l.surname) AS surname,
              MAX(l.otherNames) AS otherNames,
              MAX(l.memberNo) AS memberNo,
              MAX(l.hospitalRecNo) AS hospitalRecNo,
              MAX(l.typeOfService) AS typeOfService,
              MAX(l.typeOfAttendance) AS typeOfAttendance,
              MAX(l.admissionDate) AS admissionDate,
              MAX(l.dischargeDate) AS dischargeDate,
              MAX(l.billMonthID) AS billMonthID
            FROM dbo.vwNHIAClaimLines l
            WHERE l.billMonthID = ?
            GROUP BY l.claimID
            ORDER BY l.claimID
            """,
            bill_id,
        )
        return _rows_as_dicts(cur)
    finally:
        cn.close()


def fetch_month_claim_lines(month_key: str) -> Dict[str, List[Dict[str, Any]]]:
    bill_id = bill_id_from_month_key(month_key)
    cn = _connect()
    try:
        cur = cn.cursor()
        cur.execute(
            """
            SELECT *
            FROM dbo.vwNHIAClaimLines
            WHERE billMonthID = ?
            ORDER BY claimID, serviceDate, aType
            """,
            bill_id,
        )
        rows = _rows_as_dicts(cur)
    finally:
        cn.close()
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
        cid = str(r.get("claimID") or "").strip()
        if cid:
            grouped[cid].append(r)
    return grouped


def get_or_create_month_batch(db: Session, month_key: str, user_id: Optional[int]) -> ClaimXmlImportBatch:
    key = str(month_key or "").strip()
    batch = (
        db.query(ClaimXmlImportBatch)
        .filter(ClaimXmlImportBatch.working_month == key)
        .filter(ClaimXmlImportBatch.source == SOURCE_GHIMS_LIVE)
        .order_by(ClaimXmlImportBatch.id.asc())
        .first()
    )
    if batch:
        return batch
    batch = ClaimXmlImportBatch(
        file_name=month_label(key),
        uploaded_by_id=user_id,
        claim_count=0,
        source=SOURCE_GHIMS_LIVE,
        working_month=key,
        pinned=False,
    )
    db.add(batch)
    db.flush()
    return batch


def existing_items_by_claim_id(db: Session, claim_ids: List[str]) -> Dict[str, ClaimXmlImportItem]:
    if not claim_ids:
        return {}
    items = (
        db.query(ClaimXmlImportItem)
        .filter(ClaimXmlImportItem.claim_claim_id.in_(claim_ids))
        .order_by(ClaimXmlImportItem.id.asc())
        .all()
    )
    out: Dict[str, ClaimXmlImportItem] = {}
    for it in items:
        cid = str(it.claim_claim_id or "").strip()
        if cid and cid not in out:
            out[cid] = it
    return out


def sync_month_from_ghims(
    db: Session,
    month_key: str,
    user_id: Optional[int],
    *,
    create_missing: bool = True,
) -> Dict[str, Any]:
    headers = fetch_month_claim_headers(month_key)
    grouped = fetch_month_claim_lines(month_key)
    # Universe = headers (Visitation) ∪ line claim IDs
    by_id: Dict[str, Dict[str, Any]] = {}
    for h in headers:
        cid = str(h.get("claimID") or "").strip()
        if cid:
            by_id[cid] = h
    for cid in grouped.keys():
        by_id.setdefault(cid, {"claimID": cid, "billMonthID": bill_id_from_month_key(month_key)})

    claim_ids = list(by_id.keys())
    batch = get_or_create_month_batch(db, month_key, user_id)
    existing = existing_items_by_claim_id(db, claim_ids)
    created = 0
    linked = 0
    refreshed = 0
    for cid, header in by_id.items():
        lines = grouped.get(cid) or []
        if lines:
            rebuilt = _payload_from_nhia_lines(lines)
        else:
            rebuilt = _sparse_payload_from_header(header)

        item = existing.get(cid)
        if item:
            linked += 1
            new_payload = _refresh_date_fields(item.payload if isinstance(item.payload, dict) else {}, rebuilt)
            # Detect change without wiping other edits
            old = item.payload if isinstance(item.payload, dict) else {}
            if (
                old.get("dateOfService") != new_payload.get("dateOfService")
                or old.get("_admissionDate") != new_payload.get("_admissionDate")
                or old.get("_dischargeDate") != new_payload.get("_dischargeDate")
                or old.get("typeOfService") != new_payload.get("typeOfService")
            ):
                item.payload = new_payload
                refreshed += 1
            continue
        if not create_missing:
            continue
        member_no = str(rebuilt.get("memberNo") or "").strip() or None
        item = ClaimXmlImportItem(
            batch_id=batch.id,
            claim_claim_id=cid,
            row_index=created + 1,
            status="vetted",
            member_no=member_no,
            payload=rebuilt,
        )
        db.add(item)
        created += 1
        existing[cid] = item
    db.flush()
    batch.claim_count = (
        db.query(ClaimXmlImportItem)
        .filter(ClaimXmlImportItem.batch_id == batch.id)
        .count()
    )
    # Keep batch display name in sync with month label
    try:
        batch.file_name = month_label(month_key)
    except Exception:
        pass
    db.commit()
    db.refresh(batch)
    return {
        "month_key": month_key,
        "label": month_label(month_key),
        "batch_id": batch.id,
        "ghims_count": len(claim_ids),
        "created": created,
        "already_in_aghims": linked,
        "dates_refreshed": refreshed,
    }


def serialize_item_row(item: ClaimXmlImportItem, ghims_header: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    p = item.payload or {} if item else {}
    h = ghims_header or {}
    surname = str(p.get("surname") or h.get("surname") or "").strip()
    other = str(p.get("otherNames") or h.get("otherNames") or "").strip()
    name = " ".join([x for x in (other, surname) if x]).strip() or "—"
    dates = p.get("dateOfService") or []
    if isinstance(dates, list):
        visit = min([str(d)[:10] for d in dates if d], default=None)
        discharge = max([str(d)[:10] for d in dates if d], default=None)
    else:
        visit = str(dates)[:10] if dates else _iso_day(h.get("admissionDate"))
        discharge = _iso_day(h.get("dischargeDate")) or visit
    return {
        "id": item.id if item else None,
        "claim_claim_id": (item.claim_claim_id if item else None) or h.get("claimID"),
        "claim_check_code": p.get("claimCheckCode") or h.get("claimCheckCode"),
        "client_name": name,
        "member_no": p.get("memberNo") or h.get("memberNo"),
        "hospital_rec_no": p.get("hospitalRecNo") or h.get("hospitalRecNo"),
        "type_of_service": p.get("typeOfService") or h.get("typeOfService"),
        "type_of_attendance": p.get("typeOfAttendance") or h.get("typeOfAttendance"),
        "status": item.status if item else "pending_sync",
        "pharmacy_vetted": bool(getattr(item, "pharmacy_vetted_at", None)) if item else False,
        "doctor_vetted": bool(getattr(item, "doctor_vetted_at", None)) if item else False,
        "visit_date": visit or _iso_day(h.get("admissionDate")),
        "discharge_date": discharge or _iso_day(h.get("dischargeDate")),
        "in_aghims": bool(item),
    }
