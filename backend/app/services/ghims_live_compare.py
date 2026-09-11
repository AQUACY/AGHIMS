"""
Read-only live compare against government GHIMS (Microsoft SQL Server).

Maps AGHIMS imported claim payload.claimID -> Visitation.VisitationID.
Never writes to GHIMS.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import re

from app.core.config import settings

try:
    import pyodbc
except ImportError:  # pragma: no cover
    pyodbc = None


class GhimsLiveConfigError(RuntimeError):
    pass


class GhimsLiveNotFound(RuntimeError):
    pass



CANCELLED_RX_STATUS = {"P003", "P005"}
UNAVAILABLE_RX_STATUS = {"P004"}
CANCELLED_LAB_STATUS = {"L005"}
CANCELLED_INV_STATUS = {"R007"}
CANCELLED_EMR_STATUS = {"E003"}


def _status_state(status_id, status_name="", cancelled_ids=None, unavailable_ids=None):
    sid = str(status_id or "").strip().upper()
    name = str(status_name or "").lower()
    cancelled_ids = cancelled_ids or set()
    unavailable_ids = unavailable_ids or set()
    if sid in cancelled_ids or "cancel" in name:
        return "cancelled"
    if sid in unavailable_ids or "unavailable" in name:
        return "unavailable"
    return "active"


def _best_item_state(states):
    states = [s for s in states if s]
    if "active" in states:
        return "active"
    if "unavailable" in states:
        return "unavailable"
    if "cancelled" in states:
        return "cancelled"
    return "active"


def _index_states(rows, id_key, status_id_key, status_name_key, cancelled_ids, unavailable_ids=None):
    by_id = {}
    for row in rows or []:
        st = _status_state(row.get(status_id_key), row.get(status_name_key), cancelled_ids, unavailable_ids)
        row["state"] = st
        kid = str(row.get(id_key) or "").strip()
        if not kid:
            continue
        by_id.setdefault(kid, []).append(st)
    return {k: _best_item_state(v) for k, v in by_id.items()}

def _norm(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip()).lower()


def _norm_code(s: Any) -> str:
    return str(s or "").strip().upper()


def _strip_emr_html(s):
    import re
    s = str(s or "")
    s = re.sub(r"(?is)<script.*?>.*?</script>", " ", s)
    s = re.sub(r"(?is)<style.*?>.*?</style>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = s.replace("&nbsp;", " ").replace("&amp;", "&")
    s = re.sub(r"&#\d+;", " ", s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _is_encoded_blob(s: str) -> bool:
    t = s or ""
    return ("?%+*" in t) or ("RXXX" in t.upper()) or ("||" in t and t.upper().startswith(("E0", "TH0", "EMR")))


def _parse_prescription_blob(raw: str):
    out = []
    blob = _strip_emr_html(raw)
    if not blob:
        return out
    for chunk in re.split(r"~~+", blob):
        chunk = chunk.strip(" .;\n\r\t")
        if not chunk:
            continue
        bits = [b.strip() for b in chunk.split("||")]
        drug_id = bits[0] if bits else ""
        if not drug_id or drug_id.lower() in ("03", "none"):
            continue
        if "?%+*" in chunk or drug_id.startswith("03"):
            continue
        if "RXXX" not in drug_id.upper():
            continue
        out.append({
            "drug_id": drug_id,
            "dose": bits[1] if len(bits) > 1 else "",
            "route": bits[2] if len(bits) > 2 else "",
            "frequency": bits[3] if len(bits) > 3 else "",
            "duration": bits[4] if len(bits) > 4 else "",
        })
    return out


def _lookup_catalog(cur, ids):
    """Resolve EMR RXXX ids against Drug then LabTest. Returns id -> {kind, name}."""
    wanted = sorted({d for d in ids if d})
    catalog = {}
    if not wanted:
        return catalog
    for i in range(0, len(wanted), 40):
        batch = wanted[i:i + 40]
        placeholders = ",".join(["?"] * len(batch))
        cur.execute(
            f"SELECT DrugID, DrugName FROM dbo.Drug WHERE DrugID IN ({placeholders})",
            batch,
        )
        for row in cur.fetchall():
            catalog[str(row[0])] = {"kind": "drug", "name": str(row[1] or "").strip()}
        missing = [x for x in batch if x not in catalog]
        if not missing:
            continue
        ph = ",".join(["?"] * len(missing))
        cur.execute(
            f"SELECT LabTestID, LabTestName FROM dbo.LabTest WHERE LabTestID IN ({ph})",
            missing,
        )
        for row in cur.fetchall():
            catalog[str(row[0])] = {"kind": "lab", "name": str(row[1] or "").strip()}
    # Suffix fallback for truncated EMR ids (e.g. BB037305T vs E0032-RXXXBB037305T)
    still = [x for x in wanted if x not in catalog]
    for sid in still:
        like = "%" + sid
        cur.execute(
            "SELECT TOP 1 DrugID, DrugName FROM dbo.Drug WHERE DrugID LIKE ?",
            like,
        )
        row = cur.fetchone()
        if row:
            catalog[sid] = {"kind": "drug", "name": str(row[1] or "").strip()}
            continue
        cur.execute(
            "SELECT TOP 1 LabTestID, LabTestName FROM dbo.LabTest WHERE LabTestID LIKE ?",
            like,
        )
        row = cur.fetchone()
        if row:
            catalog[sid] = {"kind": "lab", "name": str(row[1] or "").strip()}
    return catalog


def _label_looks_prescription(label: str) -> bool:
    return "DRUG PRESCRIPTION" in (label or "").upper()


def _label_looks_investigation(label: str) -> bool:
    return "INVESTIGATION" in (label or "").upper()


def build_emr_records(emr_rows, catalog, rx_state_by_id=None, lab_state_by_id=None):
    by_req = {}
    order = []
    for row in emr_rows or []:
        rid = str(row.get("EMRRequestID") or "").strip() or "unknown"
        if rid not in by_req:
            emr_st = _status_state(
                row.get("EMRRequestStatusID"), row.get("EMRRequestStatusName"), CANCELLED_EMR_STATUS
            )
            by_req[rid] = {
                "request_id": rid,
                "date": row.get("NoteDate"),
                "entered_by": row.get("EnteredBy") or row.get("SystemUserID") or "",
                "title": row.get("EMRDataName") or row.get("EMRCompTabName") or "Clinical record",
                "emr_status": row.get("EMRRequestStatusName") or "",
                "cancelled": emr_st == "cancelled",
                "fields": [],
                "prescriptions": [],
                "investigations": [],
            }
            order.append(rid)
        rec = by_req[rid]
        title = row.get("EMRDataName") or rec["title"]
        if title:
            rec["title"] = title
        label = _strip_emr_html(row.get("LabelHtml") or "")
        value = _strip_emr_html(row.get("ValueText") or "")
        extras = [
            _strip_emr_html(str(row.get(k) or ""))
            for k in ("Column3", "Column4", "Column5", "Column6")
        ]
        extra_txt = " | ".join([e for e in extras if e and not _is_encoded_blob(e)])
        blob_raw = row.get("ValueText") or ""
        if _label_looks_prescription(label) or _label_looks_investigation(label) or ("RXXX" in str(blob_raw).upper()):
            parsed = _parse_prescription_blob(blob_raw)
            for p in parsed:
                info = catalog.get(p["drug_id"]) or {}
                kind = info.get("kind")
                name = info.get("name") or p["drug_id"]
                rec_cancelled = rec.get("cancelled")
                if kind == "lab" or (kind is None and _label_looks_investigation(label)):
                    st = "cancelled" if rec_cancelled else (lab_state_by_id or {}).get(p["drug_id"], "active")
                    rec["investigations"].append({
                        "no": len(rec["investigations"]) + 1,
                        "name": name,
                        "lab_test_id": p["drug_id"],
                        "state": st,
                    })
                else:
                    st = "cancelled" if rec_cancelled else (rx_state_by_id or {}).get(p["drug_id"], "active")
                    rec["prescriptions"].append({
                        "no": len(rec["prescriptions"]) + 1,
                        "name": name,
                        "drug_id": p["drug_id"],
                        "dose": p["dose"] if kind != "lab" else "",
                        "route": p["route"] if kind != "lab" else "",
                        "frequency": p["frequency"] if kind != "lab" else "",
                        "duration": p["duration"] if kind != "lab" else "",
                        "state": st,
                    })
            continue
        if not label and not value:
            continue
        if _is_encoded_blob(value):
            continue
        rec["fields"].append({
            "label": label or (row.get("EMRCompTabName") or "Note"),
            "value": value or extra_txt,
            "tab": row.get("EMRCompTabName") or row.get("EMRDataName") or "",
        })
    return [by_req[k] for k in order]


def ghims_mssql_configured() -> bool:
    return bool(
        (settings.GHIMS_MSSQL_HOST or "").strip()
        and (settings.GHIMS_MSSQL_DATABASE or "").strip()
        and (settings.GHIMS_MSSQL_USER or "").strip()
        and (settings.GHIMS_MSSQL_PASSWORD or "").strip()
    )


def _connect():
    if pyodbc is None:
        raise GhimsLiveConfigError(
            "pyodbc is not installed in the backend environment. "
            "Install it with: pip install pyodbc"
        )
    if not ghims_mssql_configured():
        raise GhimsLiveConfigError(
            "GHIMS MSSQL is not configured. Set GHIMS_MSSQL_HOST, "
            "GHIMS_MSSQL_DATABASE, GHIMS_MSSQL_USER, and GHIMS_MSSQL_PASSWORD."
        )
    host = settings.GHIMS_MSSQL_HOST.strip()
    port = int(settings.GHIMS_MSSQL_PORT or 1433)
    database = settings.GHIMS_MSSQL_DATABASE.strip()
    user = settings.GHIMS_MSSQL_USER.strip()
    password = settings.GHIMS_MSSQL_PASSWORD
    driver = (settings.GHIMS_MSSQL_ODBC_DRIVER or "ODBC Driver 18 for SQL Server").strip()
    server = f"{host},{port}"
    conn_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
        "Connection Timeout=20;"
    )
    return pyodbc.connect(conn_str)


def _rows_as_dicts(cursor) -> List[Dict[str, Any]]:
    cols = [d[0] for d in cursor.description] if cursor.description else []
    out = []
    for row in cursor.fetchall():
        item = {}
        for i, c in enumerate(cols):
            v = row[i]
            if hasattr(v, "isoformat"):
                try:
                    v = v.isoformat(sep=" ", timespec="seconds")
                except TypeError:
                    v = v.isoformat()
            item[c] = v
        out.append(item)
    return out


def fetch_ghims_visit_bundle(visitation_id: str) -> Dict[str, Any]:
    """Fetch visit header + clinical children for one VisitationID."""
    vid = (visitation_id or "").strip()
    if not vid:
        raise GhimsLiveNotFound("No claimID / VisitationID provided.")

    cn = _connect()
    try:
        cur = cn.cursor()
        cur.execute(
            """
            SELECT TOP 1
              v.VisitationID, v.PatientID, v.InsuranceNo, v.VisitDate,
              v.VisitTypeID, v.VisitStatusID, v.MedicalServiceID,
              v.ServiceNo, v.VisitInfo1, v.VisitInfo2,
              p.FirstName, p.SurName, p.OtherName, p.PatientName, p.BirthDate
            FROM dbo.Visitation v
            LEFT JOIN dbo.Patient p ON p.PatientID = v.PatientID
            WHERE v.VisitationID = ?
            """,
            vid,
        )
        visit_rows = _rows_as_dicts(cur)
        if not visit_rows:
            raise GhimsLiveNotFound(f"No GHIMS visitation found for VisitationID '{vid}'.")
        visit = visit_rows[0]

        # Diagnoses (+ disease labels when available)
        cur.execute(
            """
            SELECT
              d.VisitationID, d.DiseaseID, d.DiseaseCategoryID, d.DiseaseTypeID,
              d.ConsultReviewDate, d.MainInfo1, d.MainInfo2,
              dis.DiseaseName, dis.Description AS DiseaseDescription,
              dis.DiseaseInfo1, dis.DiseaseInfo2
            FROM dbo.Diagnosis d
            LEFT JOIN dbo.Disease dis ON dis.DiseaseID = d.DiseaseID
            WHERE d.VisitationID = ?
            ORDER BY d.ConsultReviewDate, d.DiseaseID
            """,
            vid,
        )
        diagnoses = _rows_as_dicts(cur)

        # Prescriptions
        cur.execute(
            """
            SELECT
              pr.PrescriptionID, pr.VisitationID, pr.DrugID, pr.Qty, pr.UnitCost,
              pr.FinalAmt, pr.PrescriptionDate, pr.PrescInfo1, pr.PrescribeInfo1,
              pr.PrescriptionStatusID,
              ps.PrescriptionStatusName,
              dr.DrugName
            FROM dbo.Prescription pr
            LEFT JOIN dbo.Drug dr ON dr.DrugID = pr.DrugID
            LEFT JOIN dbo.PrescriptionStatus ps ON ps.PrescriptionStatusID = pr.PrescriptionStatusID
            WHERE pr.VisitationID = ?
            ORDER BY pr.PrescriptionDate, pr.PrescriptionID
            """,
            vid,
        )
        prescriptions = _rows_as_dicts(cur)

        # Doctor-ordered labs
        cur.execute(
            """
            SELECT
              l.LabByDoctorID, l.VisitationID, l.LabTestID, l.Qty, l.UnitCost,
              l.FinalAmt, l.PrescriptionDate, l.LabByDoctorInfo1,
              l.LabByDoctorStatusID,
              ls.LabByDoctorStatusName,
              t.LabTestName, t.LabTestInfo1
            FROM dbo.LabByDoctor l
            LEFT JOIN dbo.LabTest t ON t.LabTestID = l.LabTestID
            LEFT JOIN dbo.LabByDoctorStatus ls ON ls.LabByDoctorStatusID = l.LabByDoctorStatusID
            WHERE l.VisitationID = ?
            ORDER BY l.PrescriptionDate, l.LabByDoctorID
            """,
            vid,
        )
        labs = _rows_as_dicts(cur)

        # Investigation rows (lab request line items)
        cur.execute(
            """
            SELECT
              i.LabRequestID, i.VisitationID, i.LabTestID, i.Qty, i.UnitCost,
              i.FinalAmt, i.RequestDate, i.ClinicalDiagnosis,
              i.RequestStatusID,
              rs.RequestStatusName,
              t.LabTestName, t.LabTestInfo1
            FROM dbo.Investigation i
            LEFT JOIN dbo.LabTest t ON t.LabTestID = i.LabTestID
            LEFT JOIN dbo.RequestStatus rs ON rs.RequestStatusID = i.RequestStatusID
            WHERE i.VisitationID = ?
            ORDER BY i.RequestDate, i.LabRequestID, i.LabTestID
            """,
            vid,
        )
        investigations = _rows_as_dicts(cur)

        # Consultation / history notes live in EMRResults (Patient History Taking),
        # not ComplaintHistory (often empty even when EMR notes exist).
        cur.execute(
            """
            SELECT
              i.VisitationID,
              req.EMRDate1 AS NoteDate,
              req.SystemUserID,
              req.EMRRequestStatusID,
              ers.EMRRequestStatusName,
              st.StaffName AS EnteredBy,
              r.EMRRequestID,
              r.EMRDataID,
              d.EMRDataName,
              r.EMRCompTabID,
              t.EMRCompTabName,
              r.EMRComponentID,
              r.CompPos,
              r.Column1 AS LabelHtml,
              r.Column2 AS ValueText,
              r.Column3 AS Column3,
              r.Column4 AS Column4,
              r.Column5 AS Column5,
              r.Column6 AS Column6
            FROM dbo.EMRRequestItems i
            JOIN dbo.EMRRequest req ON req.EMRRequestID = i.EMRRequestID
            JOIN dbo.EMRResults r
              ON r.EMRRequestID = i.EMRRequestID
             AND r.EMRDataID = i.EMRDataID
            LEFT JOIN dbo.EMRData d ON d.EMRDataID = r.EMRDataID
            LEFT JOIN dbo.EMRCompTab t ON t.EMRCompTabID = r.EMRCompTabID
            LEFT JOIN dbo.SystemUser su ON su.SystemUserID = req.SystemUserID
            LEFT JOIN dbo.Staff st ON st.StaffID = su.StaffID
            LEFT JOIN dbo.EMRRequestStatus ers ON ers.EMRRequestStatusID = req.EMRRequestStatusID
            WHERE i.VisitationID = ?
            ORDER BY req.EMRDate1, r.EMRRequestID, r.CompPos, r.EMRComponentID
            """,
            vid,
        )
        emr_rows = _rows_as_dicts(cur)
        rx_ids: List[str] = []
        for row in emr_rows:
            rx_ids.extend([p["drug_id"] for p in _parse_prescription_blob(row.get("ValueText") or "")])
        catalog = _lookup_catalog(cur, rx_ids)
        rx_state_by_id = _index_states(
            prescriptions, "DrugID", "PrescriptionStatusID", "PrescriptionStatusName",
            CANCELLED_RX_STATUS, UNAVAILABLE_RX_STATUS,
        )
        lab_state_by_id = _index_states(
            labs, "LabTestID", "LabByDoctorStatusID", "LabByDoctorStatusName",
            CANCELLED_LAB_STATUS,
        )
        inv_state_by_id = _index_states(
            investigations, "LabTestID", "RequestStatusID", "RequestStatusName",
            CANCELLED_INV_STATUS,
        )
        for kid, st in inv_state_by_id.items():
            if kid not in lab_state_by_id or st == "cancelled":
                if lab_state_by_id.get(kid) != "active":
                    lab_state_by_id[kid] = st
        emr_records = build_emr_records(emr_rows, catalog, rx_state_by_id, lab_state_by_id)

        # Keep legacy ComplaintHistory as a fallback supplement
        cur.execute(
            """
            SELECT VisitationID, ConsultReviewDate, ComplaintHistory, ComplaintHistTypeID
            FROM dbo.ComplaintHistory
            WHERE VisitationID = ?
            ORDER BY ConsultReviewDate
            """,
            vid,
        )
        complaint_history_rows = _rows_as_dicts(cur)

        # NHIA-shaped claim lines (optional enrichment)
        claim_lines: List[Dict[str, Any]] = []
        try:
            cur.execute(
                """
                SELECT claimID, hospitalRecNo, memberNo, typeOfService, typeOfAttendance,
                       code, description, qty, cost, serviceDate, gdrgCode, serviceName,
                       diagnosis, icd10, isProcedure, medicineCode, medicineName, drugName
                FROM dbo.vwNHIAClaimLines
                WHERE claimID = ?
                """,
                vid,
            )
            claim_lines = _rows_as_dicts(cur)
        except Exception:
            claim_lines = []

        return {
            "visitation_id": vid,
            "visit": visit,
            "diagnoses": diagnoses,
            "prescriptions": prescriptions,
            "labs": labs,
            "investigations": investigations,
            "emr_notes": emr_rows,
            "emr_records": emr_records,
            "complaint_history": complaint_history_rows,
            "nhia_claim_lines": claim_lines,
        }
    finally:
        cn.close()


def _claim_diagnoses(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(payload.get("diagnoses") or [])


def _claim_medicines(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(payload.get("medicines") or [])


def _claim_investigations(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(payload.get("investigations") or [])


def _claim_procedures(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(payload.get("procedures") or [])


def _ghims_diag_label(row: Dict[str, Any]) -> str:
    return (
        row.get("DiseaseName")
        or row.get("diagnosis")
        or row.get("MainInfo1")
        or row.get("DiseaseID")
        or ""
    )


def _ghims_diag_keys(row: Dict[str, Any]) -> List[str]:
    keys = []
    for k in (
        _norm_code(row.get("ICD10")),
        _norm_code(row.get("icd10")),
        _norm_code(row.get("GDRG")),
        _norm_code(row.get("gdrgCode")),
        _norm(_ghims_diag_label(row)),
        _norm_code(row.get("DiseaseID")),
    ):
        if k:
            keys.append(k)
    return keys


def _claim_diag_keys(row: Dict[str, Any]) -> List[str]:
    keys = []
    for k in (
        _norm_code(row.get("icd10")),
        _norm_code(row.get("gdrgCode")),
        _norm(row.get("diagnosis")),
    ):
        if k:
            keys.append(k)
    return keys


def _ghims_med_keys(row: Dict[str, Any]) -> List[str]:
    keys = []
    for k in (
                _norm_code(row.get("medicineCode")),
        _norm(row.get("DrugName")),
        _norm(row.get("drugName")),
        _norm_code(row.get("DrugID")),
    ):
        if k:
            keys.append(k)
    return keys


def _claim_med_keys(row: Dict[str, Any]) -> List[str]:
    keys = []
    for k in (
        _norm_code(row.get("medicineCode")),
        _norm(row.get("_serviceName")),
        _norm(row.get("product_name")),
        _norm(row.get("item_name")),
    ):
        if k:
            keys.append(k)
    return keys


def _ghims_lab_keys(row: Dict[str, Any]) -> List[str]:
    keys = []
    for k in (
                _norm(row.get("LabTestName")),
        _norm_code(row.get("LabTestID")),
        _norm_code(row.get("gdrgCode")),
        _norm_code(row.get("code")),
    ):
        if k:
            keys.append(k)
    return keys


def _claim_inv_keys(row: Dict[str, Any]) -> List[str]:
    keys = []
    for k in (_norm_code(row.get("gdrgCode")),):
        if k:
            keys.append(k)
    return keys


def _overlap(a: List[str], b: List[str]) -> bool:
    sa, sb = set(a), set(b)
    return bool(sa and sb and (sa & sb))


def _diff_lists(
    ghims_items: List[Dict[str, Any]],
    claim_items: List[Dict[str, Any]],
    ghims_key_fn,
    claim_key_fn,
    ghims_label_fn,
    claim_label_fn,
) -> Dict[str, Any]:
    matched = []
    missing_on_claim = []
    missing_on_ghims = []
    used_claim = set()

    for g in ghims_items:
        gkeys = ghims_key_fn(g)
        found_idx = None
        for i, c in enumerate(claim_items):
            if i in used_claim:
                continue
            if _overlap(gkeys, claim_key_fn(c)):
                found_idx = i
                break
        if found_idx is None:
            missing_on_claim.append({"ghims": g, "label": ghims_label_fn(g)})
        else:
            used_claim.add(found_idx)
            matched.append({
                "ghims": g,
                "claim": claim_items[found_idx],
                "label": ghims_label_fn(g) or claim_label_fn(claim_items[found_idx]),
            })

    for i, c in enumerate(claim_items):
        if i in used_claim:
            continue
        missing_on_ghims.append({"claim": c, "label": claim_label_fn(c)})

    return {
        "matched": matched,
        "missing_on_claim": missing_on_claim,
        "missing_on_ghims": missing_on_ghims,
        "counts": {
            "ghims": len(ghims_items),
            "claim": len(claim_items),
            "matched": len(matched),
            "missing_on_claim": len(missing_on_claim),
            "missing_on_ghims": len(missing_on_ghims),
        },
    }


def compare_payload_to_ghims(payload: Dict[str, Any], bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Build gap report between imported claim payload and live GHIMS bundle."""
    payload = payload or {}

    # Prefer NHIA view diagnosis/medicine lines when present (closer to claim XML shape)
    nhia = bundle.get("nhia_claim_lines") or []
    nhia_dx = [r for r in nhia if (r.get("diagnosis") or r.get("icd10") or r.get("gdrgCode")) and not r.get("medicineCode") and not r.get("isProcedure")]
    # Deduplicate dx by icd10/gdrg/diagnosis
    seen = set()
    nhia_dx_unique = []
    for r in nhia_dx:
        key = (_norm_code(r.get("icd10")), _norm_code(r.get("gdrgCode")), _norm(r.get("diagnosis")))
        if key in seen:
            continue
        seen.add(key)
        nhia_dx_unique.append(r)

    ghims_dx_src = nhia_dx_unique or bundle.get("diagnoses") or []

    def _dx_keys(r):
        return [k for k in (
            _norm_code(r.get("icd10")),
            _norm_code(r.get("ICD10")),
            _norm_code(r.get("gdrgCode")),
            _norm_code(r.get("GDRG")),
            _norm_code(r.get("code")),
            _norm(r.get("diagnosis")),
            _norm(r.get("DiseaseName")),
            _norm(r.get("serviceName")),
            _norm_code(r.get("DiseaseID")),
        ) if k]

    dx = _diff_lists(
        ghims_dx_src,
        _claim_diagnoses(payload),
        _dx_keys,
        _claim_diag_keys,
        (lambda r: r.get("DiseaseName") or r.get("diagnosis") or r.get("serviceName") or r.get("DiseaseID") or ""),
        (lambda r: r.get("diagnosis") or r.get("icd10") or r.get("gdrgCode") or ""),
    )

    nhia_meds = [r for r in nhia if r.get("medicineCode") or r.get("medicineName") or r.get("drugName")]
    ghims_med_src = nhia_meds or bundle.get("prescriptions") or []
    ghims_med_src = [r for r in ghims_med_src if (r.get("state") or "active") == "active"]
    meds = _diff_lists(
        ghims_med_src,
        _claim_medicines(payload),
        (lambda r: [k for k in (_norm_code(r.get("medicineCode")), _norm(r.get("medicineName")), _norm(r.get("drugName")), *_ghims_med_keys(r)) if k]),
        _claim_med_keys,
        (lambda r: r.get("medicineName") or r.get("drugName") or r.get("DrugName") or r.get("medicineCode") or r.get("DrugID") or ""),
        (lambda r: r.get("medicineCode") or ""),
    )

    # Labs/investigations: merge LabByDoctor + Investigation as GHIMS side
    lab_rows = [r for r in (list(bundle.get("labs") or []) + list(bundle.get("investigations") or [])) if (r.get("state") or "active") == "active"]
    inv = _diff_lists(
        lab_rows,
        _claim_investigations(payload),
        _ghims_lab_keys,
        _claim_inv_keys,
        (lambda r: r.get("LabTestName") or r.get("LabTestCode") or r.get("LabTestID") or ""),
        (lambda r: r.get("gdrgCode") or ""),
    )

    # Procedures from NHIA lines
    nhia_procs = [r for r in nhia if r.get("isProcedure")]
    procs = _diff_lists(
        nhia_procs,
        _claim_procedures(payload),
        (lambda r: [k for k in (_norm_code(r.get("gdrgCode")), _norm_code(r.get("code")), _norm(r.get("description")), _norm_code(r.get("icd10"))) if k]),
        (lambda r: [k for k in (_norm_code(r.get("gdrgCode")), _norm(r.get("description")), _norm_code(r.get("icd10"))) if k]),
        (lambda r: r.get("description") or r.get("serviceName") or r.get("gdrgCode") or r.get("code") or ""),
        (lambda r: r.get("description") or r.get("gdrgCode") or ""),
    )

    records = bundle.get("emr_records") or []
    complaint_texts = []
    addable_from_emr = []
    for rec in records:
        for fld in rec.get("fields") or []:
            if fld.get("value"):
                complaint_texts.append({
                    "date": rec.get("date"),
                    "section": rec.get("title") or fld.get("tab"),
                    "label": fld.get("label"),
                    "text": fld.get("value"),
                    "entered_by": rec.get("entered_by"),
                })
        for p in rec.get("prescriptions") or []:
            if (p.get("state") or "active") != "active":
                continue
            addable_from_emr.append({
                "id": f"rx-{rec.get('request_id')}-{p.get('drug_id')}",
                "kind": "medicine",
                "label": p.get("name") or p.get("drug_id"),
                "detail": " · ".join([x for x in (p.get("dose"), p.get("route"), p.get("frequency"), p.get("duration")) if x]),
                "record_date": rec.get("date"),
                "entered_by": rec.get("entered_by"),
                "add": {
                    "medicineCode": "",
                    "_serviceName": p.get("name") or "",
                    "dispensedQty": "",
                    "serviceDate": str(rec.get("date") or "")[:10],
                    "prescription": {
                        "dose": p.get("dose") or "",
                        "frequency": p.get("frequency") or "",
                        "duration": p.get("duration") or "",
                        "unparsed": " ".join([x for x in (p.get("dose"), p.get("route"), p.get("frequency"), p.get("duration")) if x]),
                    },
                },
            })
        for inv_row in rec.get("investigations") or []:
            if (inv_row.get("state") or "active") != "active":
                continue
            name = inv_row.get("name") or inv_row.get("label") or ""
            lab_id = inv_row.get("lab_test_id") or ""
            if not name:
                continue
            addable_from_emr.append({
                "id": f"lab-{rec.get('request_id')}-{lab_id or name}",
                "kind": "investigation",
                "label": name,
                "detail": lab_id,
                "record_date": rec.get("date"),
                "entered_by": rec.get("entered_by"),
                "add": {
                    "serviceDate": str(rec.get("date") or "")[:10],
                    "gdrgCode": "",
                    "_serviceName": name,
                },
            })

    return {
        "diagnoses": dx,
        "medicines": meds,
        "investigations": inv,
        "procedures": procs,
        "complaints": complaint_texts,
        "records": records,
        "addable": addable_from_emr,
        "summary": {
            "missing_on_claim_total": (
                dx["counts"]["missing_on_claim"]
                + meds["counts"]["missing_on_claim"]
                + inv["counts"]["missing_on_claim"]
                + procs["counts"]["missing_on_claim"]
            ),
            "missing_on_ghims_total": (
                dx["counts"]["missing_on_ghims"]
                + meds["counts"]["missing_on_ghims"]
                + inv["counts"]["missing_on_ghims"]
                + procs["counts"]["missing_on_ghims"]
            ),
        },
    }


def build_live_compare_for_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """End-to-end: resolve VisitationID from payload.claimID and compare."""
    payload = payload or {}
    visitation_id = str(payload.get("claimID") or "").strip()
    bundle = fetch_ghims_visit_bundle(visitation_id)
    gaps = compare_payload_to_ghims(payload, bundle)
    visit = bundle.get("visit") or {}
    return {
        "ok": True,
        "visitation_id": visitation_id,
        "hospital_rec_no": payload.get("hospitalRecNo") or visit.get("PatientID"),
        "visit": visit,
        "ghims": {
            "diagnoses": bundle.get("diagnoses") or [],
            "prescriptions": bundle.get("prescriptions") or [],
            "labs": bundle.get("labs") or [],
            "investigations": bundle.get("investigations") or [],
            "emr_notes": bundle.get("emr_notes") or [],
            "emr_records": bundle.get("emr_records") or [],
            "complaint_history": bundle.get("complaint_history") or [],
            "nhia_claim_lines": bundle.get("nhia_claim_lines") or [],
        },
        "gaps": gaps,
    }
