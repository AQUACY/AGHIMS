"""
Read-only GHIMS pull into Companion (co-payment) visits.

Insured visits only. A lab is billable once GHIMS shows it was done
(investigation Ready / Partially Ready, or — when no investigation row
exists — received at lab / results entered / validated). A medicine is
billable only when the prescription status is Dispensed.

Never writes to GHIMS.
"""
from __future__ import annotations

import json
import logging
import re
import threading
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.datetime_utils import utcnow
from app.models.companion_visit import CompanionVisit
from app.models.companion_visit_item import CompanionVisitItem
from app.models.module_settings import ModuleSettings
from app.models.user import User
from app.services.ghims_live_compare import _connect, _rows_as_dicts, ghims_mssql_configured

logger = logging.getLogger(__name__)

MODULE_KEY = "companion_ghims_live"
SOURCE_LIVE = "ghims_live"
SYNC_CANCEL_REASON = "No longer completed in GHIMS"
UNPRICED_ITEM_CODE = "UNPRICED"

# Cash / self-pay. GHIMS bills these patients itself.
CASH_SPONSOR_IDS = {"SELF", "SELFN"}
CASH_INSURANCE_TYPE_IDS = {"I100", "CPP"}

# Investigation.RequestStatus: RRD002 Ready, RRD003 Partially Ready.
# RRD001 Not Ready is still only a request.
INVESTIGATION_DONE_STATUSES = {"RRD002", "RRD003"}
# LabByDoctor, used only when that test has no Investigation row.
# L002 Received at Lab, L003 Results Entered, L004 Results Validated.
LAB_DONE_STATUSES = {"L002", "L003", "L004"}
# PrescriptionStatus P002 Dispensed Prescription.
DISPENSED_RX_STATUSES = {"P002"}

ADMISSION_LOOKBACK_DAYS = 14
SYNC_MIN_INTERVAL_SECONDS = 90
# Skip a visit GHIMS already refreshed this recently. Stops every page open from reading GHIMS again.
VISIT_REFRESH_SECONDS = 90

_sync_lock = threading.Lock()
_last_recent_sync = 0.0
_scheduler = None


def is_cash_visit(sponsor_id: Any, insurance_type_id: Any) -> bool:
    """True when GHIMS is already billing this visit as self-pay / cash."""
    sponsor = str(sponsor_id or "").strip().upper()
    ins_type = str(insurance_type_id or "").strip().upper()
    if sponsor in CASH_SPONSOR_IDS or ins_type in CASH_INSURANCE_TYPE_IDS:
        return True
    if not sponsor and not ins_type:
        return True
    return False


def select_billable_lines(
    investigations: List[Dict[str, Any]],
    labs: List[Dict[str, Any]],
    prescriptions: List[Dict[str, Any]],
    sales: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Turn GHIMS rows for one visit into billable co-payment lines.

    Investigation status wins for a lab test. A pending request (or an
    investigation that is Not Ready) does not become a line, even if a
    doctor order exists. Medicines come from pharmacy dispense sales when
    present (even if the prescription is still marked New); otherwise a
    Dispensed prescription is used.
    """
    inv_by_test: Dict[str, List[Dict[str, Any]]] = {}
    for row in investigations or []:
        tid = str(row.get("LabTestID") or "").strip()
        inv_by_test.setdefault(tid, []).append(row)

    lines: List[Dict[str, Any]] = []

    for tid, rows in inv_by_test.items():
        for row in rows:
            status = str(row.get("RequestStatusID") or "").strip().upper()
            if status not in INVESTIGATION_DONE_STATUSES:
                continue
            source_id = f"{row.get('LabRequestID')}|{row.get('LabTestID')}".strip("|")
            name = str(row.get("LabTestName") or "").strip() or tid
            qty = _positive_qty(row.get("Qty"))
            if not source_id or not name or qty <= 0:
                continue
            lines.append(
                {
                    "source_type": "investigation",
                    "source_id": source_id[:150],
                    "description": name[:500],
                    "quantity": qty,
                    "service_at": _parse_visit_date(
                        row.get("BillProcessDate") or row.get("RequestDate")
                    ),
                }
            )

    tests_with_investigation = set(inv_by_test.keys())
    for row in labs or []:
        tid = str(row.get("LabTestID") or "").strip()
        if tid in tests_with_investigation:
            continue
        status = str(row.get("LabByDoctorStatusID") or "").strip().upper()
        if status not in LAB_DONE_STATUSES:
            continue
        source_id = str(row.get("LabByDoctorID") or "").strip()
        name = str(row.get("LabTestName") or "").strip() or tid
        qty = _positive_qty(row.get("Qty"))
        if not source_id or not name or qty <= 0:
            continue
        lines.append(
            {
                "source_type": "lab_by_doctor",
                "source_id": source_id[:150],
                "description": name[:500],
                "quantity": qty,
                "service_at": _parse_visit_date(
                    row.get("PrescriptionDate") or row.get("LabByDoctorDate1")
                ),
            }
        )

    sales = list(sales or [])
    attach_issued_quantities(prescriptions or [], sales)
    covered_rx: set = set()
    covered_drug: set = set()
    for sale in sales:
        qty = dispensed_quantity(sale)
        drug_id = str(sale.get("DrugID") or "").strip()
        rx_id = str(sale.get("PrescriptionID") or "").strip()
        sale_id = str(sale.get("DrugSaleID") or "").strip()
        name = (
            str(sale.get("DrugName") or "").strip()
            or drug_id
        )
        source_id = rx_id or f"{sale_id}|{drug_id}".strip("|")
        if not source_id or not name or qty <= 0:
            continue
        lines.append(
            {
                "source_type": "prescription",
                "source_id": source_id[:150],
                "description": name[:500],
                "quantity": qty,
                "generic": str(sale.get("ProdInfo2") or sale.get("generic") or "").strip()[:200],
                "service_at": _parse_visit_date(sale.get("DispenseDate") or sale.get("service_at")),
            }
        )
        if rx_id:
            covered_rx.add(rx_id)
        if drug_id:
            covered_drug.add(drug_id)

    for row in prescriptions or []:
        status = str(row.get("PrescriptionStatusID") or "").strip().upper()
        if status not in DISPENSED_RX_STATUSES:
            continue
        source_id = str(row.get("PrescriptionID") or "").strip()
        drug_id = str(row.get("DrugID") or "").strip()
        if source_id in covered_rx or (drug_id and drug_id in covered_drug):
            continue
        name = str(row.get("DrugName") or "").strip() or drug_id
        qty = dispensed_quantity(row)
        if not source_id or not name or qty <= 0:
            continue
        lines.append(
            {
                "source_type": "prescription",
                "source_id": source_id[:150],
                "description": name[:500],
                "quantity": qty,
                "generic": str(row.get("ProdInfo2") or "").strip()[:200],
                "service_at": _parse_visit_date(
                    row.get("DispenseDate") or row.get("PrescriptionDate")
                ),
            }
        )
    return lines


def live_sync_enabled(db: Session) -> bool:
    if not ghims_mssql_configured():
        return False
    row = (
        db.query(ModuleSettings)
        .filter(ModuleSettings.module_key == MODULE_KEY)
        .first()
    )
    return bool(row and row.is_active)


def sync_recent_if_due(db: Session) -> None:
    """Fill today's insured bills. Skips when another sync is already running."""
    global _last_recent_sync
    if not live_sync_enabled(db):
        return
    now = time.monotonic()
    if now - _last_recent_sync < SYNC_MIN_INTERVAL_SECONDS:
        return
    if not _sync_lock.acquire(blocking=False):
        return
    try:
        if time.monotonic() - _last_recent_sync < SYNC_MIN_INTERVAL_SECONDS:
            return
        sync_recent(db)
        _last_recent_sync = time.monotonic()
    finally:
        _sync_lock.release()


def visit_needs_ghims_refresh(visit: CompanionVisit, max_age_seconds: int = VISIT_REFRESH_SECONDS) -> bool:
    """True when a live-synced visit has not been read from GHIMS recently."""
    if visit is None:
        return False
    source = (visit.source or "").strip()
    synced_at = getattr(visit, "ghims_synced_at", None)
    if source != SOURCE_LIVE and synced_at is None:
        return False
    if synced_at is None:
        return True
    try:
        age = (utcnow() - synced_at).total_seconds()
    except TypeError:
        return True
    return age >= max_age_seconds


def schedule_patient_sync(card_number: str) -> None:
    """Refresh one card without blocking the page that asked for the list."""
    card = (card_number or "").strip()
    if not card:
        return
    _spawn(_job_patient_sync, card)


def schedule_visitation_sync(visitation_id: str) -> None:
    vid = (visitation_id or "").strip()
    if not vid:
        return
    _spawn(_job_visitation_sync, vid)


def schedule_visit_refresh(visit_id: int) -> None:
    if not visit_id:
        return
    _spawn(_job_visit_refresh, visit_id)


def _spawn(target, *args) -> None:
    threading.Thread(target=target, args=args, daemon=True).start()


def _job_patient_sync(card_number: str) -> None:
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        sync_patient_card(db, card_number)
    except Exception:
        logger.exception("Background GHIMS card sync failed")
        db.rollback()
    finally:
        db.close()


def _job_visitation_sync(visitation_id: str) -> None:
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        sync_visitation(db, visitation_id)
    except Exception:
        logger.exception("Background GHIMS visit sync failed")
        db.rollback()
    finally:
        db.close()


def _job_visit_refresh(visit_id: int) -> None:
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        if not live_sync_enabled(db):
            return
        visit = db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).first()
        if visit is None or not visit_needs_ghims_refresh(visit):
            return
        refresh_companion_visit(db, visit)
    except Exception:
        logger.exception("Background GHIMS visit refresh failed")
        db.rollback()
    finally:
        db.close()


def sync_patient_card(db: Session, card_number: str) -> None:
    """Pull recent insured visits for one GHIMS patient number."""
    card = (card_number or "").strip()
    if not card or not live_sync_enabled(db):
        return
    if not _sync_lock.acquire(blocking=False):
        return
    try:
        headers = _fetch_headers_for_patient(card)
        _apply_headers(db, headers)
    finally:
        _sync_lock.release()


def sync_visitation(db: Session, visitation_id: str) -> None:
    """Pull one GHIMS visit if it is insured and has something billable."""
    vid = (visitation_id or "").strip()
    if not vid or not live_sync_enabled(db):
        return
    if not _sync_lock.acquire(blocking=False):
        return
    try:
        headers = _fetch_header(vid)
        _apply_headers(db, headers, force=True)
    finally:
        _sync_lock.release()


def refresh_companion_visit(db: Session, visit: CompanionVisit, *, force: bool = False) -> Dict[str, Any]:
    """Re-read the visit already stored in Copayment."""
    summary: Dict[str, Any] = {
        "updated": False,
        "drug_lines": 0,
        "drug_qty_gt_one": 0,
        "pharmacy_sale_rows": 0,
        "note": None,
    }
    if visit is None or not live_sync_enabled(db):
        summary["note"] = "Live GHIMS sync is off."
        return summary
    vid = (visit.external_visit_number or "").strip()
    if not vid:
        summary["note"] = "This visit has no GHIMS visit number."
        return summary
    if not force and not visit_needs_ghims_refresh(visit):
        summary["note"] = "Already refreshed recently."
        return summary
    acquired = (
        _sync_lock.acquire(blocking=True, timeout=45)
        if force
        else _sync_lock.acquire(blocking=False)
    )
    if not acquired:
        if force:
            raise TimeoutError("GHIMS sync is already running. Try again in a moment.")
        summary["note"] = "Another GHIMS sync is running."
        return summary
    try:
        headers = _fetch_header(vid)
        actor_id = _sync_actor_id(db)
        if not headers:
            if (visit.source or "") == SOURCE_LIVE:
                visit.ghims_sync_note = "This visit number was not found in GHIMS."
                visit.ghims_synced_at = utcnow()
                db.commit()
            summary["note"] = "Visit number was not found in GHIMS."
            return summary
        header = headers[0]
        if is_cash_visit(header.get("SponsorID"), header.get("InsuranceTypeID")):
            visit.ghims_synced_at = utcnow()
            db.commit()
            summary["note"] = "This visit is cash/self-pay in GHIMS."
            return summary
        sales = _fetch_issued_sales([vid], force_reload_plan=force)
        summary["pharmacy_sale_rows"] = len(sales)
        bundle = _fetch_bundles([vid]).get(vid) or _empty_bundle()
        if not summary["pharmacy_sale_rows"]:
            summary["pharmacy_sale_rows"] = len(bundle.get("sales") or [])
        # Force path already attached sales inside _fetch_bundles; count resulting drug qty.
        drug_lines = [
            line
            for line in select_billable_lines(
                bundle.get("investigations") or [],
                bundle.get("labs") or [],
                bundle.get("prescriptions") or [],
                bundle.get("sales") or sales,
            )
            if line.get("source_type") == "prescription"
        ]
        summary["drug_lines"] = len(drug_lines)
        summary["drug_qty_gt_one"] = sum(1 for line in drug_lines if float(line.get("quantity") or 0) > 1.001)
        changed = _apply_one(db, header, actor_id, bundle=bundle, existing=visit)
        summary["updated"] = bool(changed)
        if summary["drug_lines"] and summary["drug_qty_gt_one"] == 0 and summary["pharmacy_sale_rows"] == 0:
            summary["note"] = (
                "GHIMS returned no pharmacy sale quantities for this visit, "
                "so drug quantity stayed at the prescription value (often 1)."
            )
            if force:
                visit.ghims_sync_note = summary["note"]
                db.commit()
        elif summary["drug_lines"] and summary["drug_qty_gt_one"] == 0:
            summary["note"] = (
                f"Found {summary['pharmacy_sale_rows']} pharmacy sale row(s), "
                "but each dispensed drug still resolved to quantity 1."
            )
            if force:
                visit.ghims_sync_note = summary["note"]
                db.commit()
        elif force and (visit.ghims_sync_note or "").startswith("GHIMS returned no pharmacy"):
            visit.ghims_sync_note = None
            db.commit()
        elif force and (visit.ghims_sync_note or "").startswith("Found ") and "quantity 1" in (visit.ghims_sync_note or ""):
            visit.ghims_sync_note = None
            db.commit()
        return summary
    finally:
        _sync_lock.release()


def sync_recent(db: Session) -> None:
    headers = _fetch_recent_headers()
    _apply_headers(db, headers)


def run_scheduled_sync() -> None:
    from app.core.database import SessionLocal

    if not ghims_mssql_configured():
        return
    db = SessionLocal()
    try:
        if not live_sync_enabled(db):
            return
        if not _sync_lock.acquire(blocking=False):
            return
        try:
            sync_recent(db)
            global _last_recent_sync
            _last_recent_sync = time.monotonic()
        finally:
            _sync_lock.release()
    except Exception:
        logger.exception("GHIMS co-payment scheduled sync failed")
        db.rollback()
    finally:
        db.close()


def start_companion_ghims_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        logger.warning("APScheduler is not installed; GHIMS co-payment sync will run when Copayment is opened")
        return
    scheduler = BackgroundScheduler()
    from datetime import datetime as _dt

    scheduler.add_job(
        run_scheduled_sync,
        "interval",
        minutes=3,
        id="companion_ghims_live",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        next_run_time=_dt.now(),
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info("GHIMS co-payment sync scheduler started")


def stop_companion_ghims_scheduler() -> None:
    global _scheduler
    if _scheduler is None:
        return
    try:
        _scheduler.shutdown(wait=False)
    except Exception:
        logger.exception("Failed to stop GHIMS co-payment sync scheduler")
    _scheduler = None


def _new_item_id(extra: Optional[Dict[str, Any]]) -> Optional[int]:
    """Line id from _try_add_visit_item_from_government_line. It lives under added.id."""
    if not extra:
        return None
    if extra.get("id"):
        return extra.get("id")
    added = extra.get("added") if isinstance(extra.get("added"), dict) else None
    if not added:
        return None
    return added.get("id")


def _find_new_item(db: Session, extra: Dict[str, Any]) -> Optional[CompanionVisitItem]:
    item_id = _new_item_id(extra)
    if not item_id:
        return None
    return db.query(CompanionVisitItem).filter(CompanionVisitItem.id == item_id).first()


def _claim_unsourced_item(existing_items: List[CompanionVisitItem], description: str) -> Optional[CompanionVisitItem]:
    """Attach a GHIMS id to a line created before source ids were saved."""
    target = _norm_name(description)
    if not target:
        return None
    for item in existing_items:
        if item.ghims_source_id or item.cancelled:
            continue
        if item.paid_at or (item.receipt_number or "").strip():
            continue
        if _norm_name(item.item_name) == target:
            return item
    return None


def _norm_name(value: Any) -> str:
    return " ".join(str(value or "").split()).lower()


def _parse_visit_date(value: Any):
    from datetime import datetime

    if value is None:
        return None
    if hasattr(value, "year") and hasattr(value, "month"):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[:19] if fmt != "%Y-%m-%d" else text[:10], fmt)
        except ValueError:
            continue
    return None


def _positive_qty(value: Any) -> float:
    try:
        qty = float(value if value is not None else 1)
    except (TypeError, ValueError):
        return 0.0
    if qty <= 0:
        return 0.0
    return qty


def _stated_qty(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, str) and not value.strip():
        return 0.0
    return _positive_qty(value)


def dispensed_quantity(row: Dict[str, Any]) -> float:
    """Best pharmacy quantity. Prescription.Qty is often 1 and is the last resort."""
    # GHIMS pharmacy screen uses DispenseAmt1; Qty on the sale line is often still 1.
    dispense_amt = max(
        _stated_qty(row.get("DispenseAmt1")),
        _stated_qty(row.get("DispenseAmt2")),
    )
    issued = max(_stated_qty(row.get("IssuedQty")), dispense_amt)
    requested = _stated_qty(row.get("RequestedQty"))
    nhia = _stated_qty(row.get("NhiaQty"))
    prescribed = _stated_qty(row.get("Qty"))
    derived = _qty_from_directions(row)
    if dispense_amt > 0:
        return dispense_amt
    if issued > 1:
        return issued
    if requested > 1:
        return requested
    if nhia > 1:
        return nhia
    if derived > 1:
        return derived
    if issued > 0:
        return issued
    if requested > 0:
        return requested
    if nhia > 0:
        return nhia
    if derived > 0:
        return derived
    return prescribed if prescribed > 0 else _positive_qty(row.get("Qty"))


_FREQ_PER_DAY = {
    "od": 1,
    "qd": 1,
    "daily": 1,
    "nocte": 1,
    "hs": 1,
    "stat": 1,
    "bd": 2,
    "bid": 2,
    "tds": 3,
    "tid": 3,
    "qds": 4,
    "qid": 4,
}


def _qty_from_directions(row: Dict[str, Any]) -> float:
    """Estimate tablets/capsules from dose × frequency × days when Qty stayed at 1."""
    name = str(row.get("DrugName") or "").lower()
    form_hint = any(word in name for word in ("tablet", "capsule", "tab", "cap", "pill"))
    blob = " || ".join(
        str(row.get(key) or "").strip()
        for key in ("PrescribeInfo1", "PrescInfo1", "PrescribeInfo2", "PrescInfo2")
        if str(row.get(key) or "").strip()
    )
    if not blob:
        return 0.0
    bits = [b.strip() for b in re.split(r"[|]+", blob) if b.strip()]
    dose = 0.0
    freq = 0.0
    days = 0.0
    for bit in bits:
        low = bit.lower().strip()
        if low in _FREQ_PER_DAY:
            freq = float(_FREQ_PER_DAY[low])
            continue
        match = re.search(r"(\d+(?:\.\d+)?)", bit)
        if not match:
            continue
        num = float(match.group(1))
        if dose <= 0 and re.search(r"\b(tab|cap|tablet|capsule|mg|ml)\b", low):
            dose = num
            continue
        if dose <= 0 and not re.search(r"\b(day|days|/7|/52|week)\b", low):
            dose = num
            continue
        if days <= 0 and (re.search(r"\b(day|days|/7)\b", low) or (num <= 90 and freq > 0)):
            days = num
            continue
        if days <= 0 and num > 1:
            days = num
    if dose <= 0:
        dose = 1.0
    if freq <= 0 or days <= 0:
        return 0.0
    # Only invent a pack size for solid oral forms, or when directions clearly multiply.
    qty = dose * freq * days
    if qty <= 1:
        return 0.0
    if form_hint or qty >= 2:
        return float(qty)
    return 0.0


def _base_visit_id(value: Any) -> str:
    vid = str(value or "").strip()
    if vid.upper().endswith("-C"):
        return vid[:-2]
    return vid


def _visit_id_keys(visitation_ids: List[str]) -> List[str]:
    keys: List[str] = []
    seen = set()
    for raw in visitation_ids:
        base = _base_visit_id(raw)
        for key in (base, f"{base}-C"):
            if key and key not in seen:
                seen.add(key)
                keys.append(key)
    return keys


def attach_issued_quantities(
    prescriptions: List[Dict[str, Any]],
    sales: List[Dict[str, Any]],
) -> None:
    """Copy pharmacy dispense qty/date onto the matching prescription row."""
    if not prescriptions or not sales:
        return
    by_rx: Dict[tuple, Dict[str, Any]] = {}
    by_drug: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)
    for sale in sales:
        qty = dispensed_quantity(sale)
        if qty <= 0:
            continue
        vid = _base_visit_id(sale.get("VisitationID"))
        drug = str(sale.get("DrugID") or "").strip()
        rx = str(sale.get("PrescriptionID") or "").strip()
        payload = {
            "IssuedQty": qty,
            "DispenseAmt1": qty,
            "DispenseDate": sale.get("DispenseDate"),
        }
        if rx:
            key = (vid, rx)
            prev = by_rx.get(key)
            if prev is None or float(prev.get("IssuedQty") or 0) < qty:
                by_rx[key] = payload
        if vid and drug:
            by_drug[(vid, drug)].append(payload)
    for row in prescriptions:
        vid = _base_visit_id(row.get("VisitationID"))
        rx = str(row.get("PrescriptionID") or "").strip()
        found = by_rx.get((vid, rx))
        if not found:
            drug = str(row.get("DrugID") or "").strip()
            candidates = list(by_drug.get((vid, drug)) or [])
            found = candidates[0] if len(candidates) == 1 else None
        if not found:
            continue
        row["IssuedQty"] = found["IssuedQty"]
        row["DispenseAmt1"] = found["DispenseAmt1"]
        if found.get("DispenseDate"):
            row["DispenseDate"] = found["DispenseDate"]


def attach_nhia_quantities(
    prescriptions: List[Dict[str, Any]],
    nhia_rows: List[Dict[str, Any]],
) -> None:
    """Use NHIA claim-line qty when pharmacy sale qty is still missing."""
    if not prescriptions or not nhia_rows:
        return
    by_drug: Dict[tuple, float] = defaultdict(float)
    by_name: Dict[tuple, float] = defaultdict(float)
    for row in nhia_rows:
        qty = _stated_qty(row.get("qty") if row.get("qty") is not None else row.get("Qty"))
        if qty <= 0:
            continue
        vid = str(row.get("claimID") or row.get("VisitationID") or "").strip()
        drug = str(row.get("DrugID") or row.get("medicineCode") or "").strip()
        name = _norm_name(
            row.get("medicineName") or row.get("drugName") or row.get("description") or ""
        )
        if vid and drug:
            by_drug[(vid, drug)] += qty
        if vid and name:
            by_name[(vid, name)] += qty
    for row in prescriptions:
        if max(_stated_qty(row.get("IssuedQty")), _stated_qty(row.get("RequestedQty")), _stated_qty(row.get("NhiaQty"))) > 1:
            continue
        vid = str(row.get("VisitationID") or "").strip()
        drug = str(row.get("DrugID") or "").strip()
        name = _norm_name(row.get("DrugName") or "")
        qty = by_drug.get((vid, drug), 0.0) or by_name.get((vid, name), 0.0)
        if qty > 0:
            row["NhiaQty"] = qty


def _sync_actor_id(db: Session) -> Optional[int]:
    admin = (
        db.query(User)
        .filter(User.role == "Admin", User.is_active == True)  # noqa: E712
        .order_by(User.id.asc())
        .first()
    )
    if admin:
        return admin.id
    any_user = db.query(User).filter(User.is_active == True).order_by(User.id.asc()).first()  # noqa: E712
    return any_user.id if any_user else None


def _apply_headers(db: Session, headers: List[Dict[str, Any]], *, force: bool = False) -> None:
    actor_id = _sync_actor_id(db)
    insured = [
        h
        for h in headers
        if not is_cash_visit(h.get("SponsorID"), h.get("InsuranceTypeID"))
        and str(h.get("VisitationID") or "").strip()
        and str(h.get("PatientID") or "").strip()
    ]
    if not insured:
        return
    vids = [str(h["VisitationID"]).strip() for h in insured]
    existing_by_vid: Dict[str, CompanionVisit] = {}
    if vids:
        rows = (
            db.query(CompanionVisit)
            .filter(CompanionVisit.external_visit_number.in_(vids))
            .all()
        )
        existing_by_vid = {(row.external_visit_number or "").strip(): row for row in rows}
    pending: List[Dict[str, Any]] = []
    for header in insured:
        vid = str(header["VisitationID"]).strip()
        current = existing_by_vid.get(vid)
        if current is not None and not force and not visit_needs_ghims_refresh(current):
            continue
        pending.append(header)
    if not pending:
        return
    bundles = _fetch_bundles([str(h["VisitationID"]).strip() for h in pending])
    created = 0
    for header in pending:
        vid = str(header["VisitationID"]).strip()
        try:
            with db.begin_nested():
                bundle = bundles.get(vid) or {"investigations": [], "labs": [], "prescriptions": []}
                if _apply_one(
                    db,
                    header,
                    actor_id,
                    bundle=bundle,
                    existing=existing_by_vid.get(vid),
                    commit=False,
                ):
                    created += 1
        except Exception:
            logger.exception("GHIMS co-payment sync failed for visit %s", header.get("VisitationID"))
    if created or db.dirty or db.new:
        db.commit()
    if created:
        logger.info("GHIMS co-payment sync updated %s insured visit(s)", created)


def _apply_one(
    db: Session,
    header: Dict[str, Any],
    actor_id: Optional[int],
    bundle: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    existing: Optional[CompanionVisit] = None,
    commit: bool = True,
) -> bool:
    vid = str(header.get("VisitationID") or "").strip()
    card = str(header.get("PatientID") or "").strip()
    if not vid or not card:
        return False
    if bundle is None:
        bundle = _fetch_bundles([vid]).get(vid) or _empty_bundle()
    lines = select_billable_lines(
        bundle.get("investigations") or [],
        bundle.get("labs") or [],
        bundle.get("prescriptions") or [],
        bundle.get("sales") or [],
    )
    visit = existing
    if visit is None:
        visit = (
            db.query(CompanionVisit)
            .filter(
                CompanionVisit.external_card_number == card,
                CompanionVisit.external_visit_number == vid,
            )
            .first()
        )
    if visit is None:
        if not lines or actor_id is None:
            return False
        name = str(header.get("PatientName") or "").strip() or None
        visit = CompanionVisit(
            external_card_number=card[:50],
            external_visit_number=vid[:50],
            client_name=(name[:255] if name else None),
            status="open",
            created_by=actor_id,
            source=SOURCE_LIVE,
        )
        db.add(visit)
        db.flush()
    elif not (visit.client_name or "").strip():
        name = str(header.get("PatientName") or "").strip()
        if name:
            visit.client_name = name[:255]
    visit_date = _parse_visit_date(header.get("VisitDate"))
    if visit_date is not None:
        visit.ghims_visit_date = visit_date

    existing_items = (
        db.query(CompanionVisitItem)
        .filter(CompanionVisitItem.companion_visit_id == visit.id)
        .all()
    )
    if _billable_lines_match_items(lines, existing_items):
        if visit_needs_ghims_refresh(visit):
            visit.ghims_synced_at = utcnow()
            if commit:
                db.commit()
        return False

    mutate = (visit.status or "open") != "closed"
    unmatched, missing_on_closed = _upsert_lines(
        db, visit, lines, actor_id, mutate=mutate, existing_items=existing_items
    )
    visit.ghims_synced_at = utcnow()
    visit.ghims_unmatched_json = json.dumps(unmatched, ensure_ascii=False) if unmatched else None
    if not mutate and missing_on_closed:
        visit.ghims_sync_note = (
            "GHIMS has completed services that are not on this closed visit. "
            "Reopen the visit to add them."
        )
    elif (visit.ghims_sync_note or "").startswith("GHIMS has completed"):
        visit.ghims_sync_note = None
    if commit:
        db.commit()
    return True


def _is_missing_price(reason: Optional[str]) -> bool:
    text = (reason or "").strip().lower()
    return text in {"no price list match found", "matched price item has no code"}


def _add_unpriced_line(
    db: Session,
    visit: CompanionVisit,
    line: Dict[str, Any],
    actor_id: Optional[int],
) -> Optional[CompanionVisitItem]:
    """Keep a completed GHIMS service on the bill when the price list has no co-payment yet."""
    name = str(line.get("description") or "").strip()
    source_id = str(line.get("source_id") or "").strip()
    source_type = str(line.get("source_type") or "").strip()
    if not name or not source_id or not source_type:
        return None
    category = "drug" if source_type == "prescription" else "lab"
    item = CompanionVisitItem(
        companion_visit_id=visit.id,
        item_code=UNPRICED_ITEM_CODE,
        item_name=name[:500],
        category=category,
        unit_price=0.0,
        quantity=float(line["quantity"]),
        start_time=line.get("service_at"),
        created_by_id=actor_id,
        needs_copay_price=True,
        ghims_source_type=source_type[:30],
        ghims_source_id=source_id[:150],
    )
    db.add(item)
    db.flush()
    return item


def _quantity_is_locked(item: CompanionVisitItem) -> bool:
    """A recorded payment keeps the quantity that was billed. A zero co-payment does not."""
    if getattr(item, "paid_at", None):
        return True
    if (getattr(item, "receipt_number", None) or "").strip():
        return True
    if (getattr(item, "admission_deposit_line_receipt", None) or "").strip():
        return True
    return False


def _billable_lines_match_items(lines: List[Dict[str, Any]], items: List[CompanionVisitItem]) -> bool:
    """True when stored bill lines already match the completed GHIMS services."""
    from app.api.companion_visits import _companion_item_is_paid

    active = {
        (it.ghims_source_type, it.ghims_source_id): it
        for it in items
        if it.ghims_source_type and it.ghims_source_id and not it.cancelled
    }
    if any(getattr(it, "needs_copay_price", False) and not it.cancelled for it in items):
        return False
    seen = set()
    for line in lines:
        key = (line["source_type"], line["source_id"])
        seen.add(key)
        item = active.get(key)
        if item is None:
            return False
        if _quantity_is_locked(item):
            continue
        if abs(float(item.quantity or 0) - float(line["quantity"])) > 0.001:
            return False
    for key, item in active.items():
        if key in seen or _companion_item_is_paid(item):
            continue
        return False
    return True


def _upsert_lines(
    db: Session,
    visit: CompanionVisit,
    lines: List[Dict[str, Any]],
    actor_id: Optional[int],
    *,
    mutate: bool,
    existing_items: Optional[List[CompanionVisitItem]] = None,
) -> tuple[List[Dict[str, Any]], bool]:
    from app.api.companion_visits import (
        _companion_item_is_paid,
        _lookup_government_line_price,
        _try_add_visit_item_from_government_line,
    )

    if existing_items is None:
        existing_items = (
            db.query(CompanionVisitItem)
            .filter(CompanionVisitItem.companion_visit_id == visit.id)
            .all()
        )
    by_key = {
        (it.ghims_source_type, it.ghims_source_id): it
        for it in existing_items
        if it.ghims_source_type and it.ghims_source_id
    }
    seen = set()
    unmatched: List[Dict[str, Any]] = []
    missing_on_closed = False

    for line in lines:
        key = (line["source_type"], line["source_id"])
        seen.add(key)
        item = by_key.get(key)
        if item is not None:
            if _quantity_is_locked(item):
                continue
            if item.cancelled and (item.cancel_reason or "") != SYNC_CANCEL_REASON:
                continue
            if not mutate:
                continue
            if item.cancelled and (item.cancel_reason or "") == SYNC_CANCEL_REASON:
                item.cancelled = False
                item.cancelled_at = None
                item.cancelled_by_id = None
                item.cancel_reason = None
            if getattr(item, "needs_copay_price", False):
                match = _lookup_government_line_price(
                    db,
                    line["description"],
                    generic=line.get("generic"),
                    source_type=line.get("source_type"),
                )
                if match:
                    item.item_code = match["item_code"][:50]
                    item.item_name = match["item_name"][:500]
                    item.category = match["category"] or item.category
                    item.unit_price = float(match["unit_price"])
                    item.needs_copay_price = False
            if abs(float(item.quantity or 0) - float(line["quantity"])) > 0.001:
                item.quantity = float(line["quantity"])
            if line.get("service_at") and getattr(item, "start_time", None) != line.get("service_at"):
                item.start_time = line.get("service_at")
            continue
        if not mutate:
            missing_on_closed = True
            continue
        claimed = _claim_unsourced_item(existing_items, line["description"])
        if claimed is not None:
            claimed.ghims_source_type = line["source_type"]
            claimed.ghims_source_id = line["source_id"]
            by_key[key] = claimed
            if abs(float(claimed.quantity or 0) - float(line["quantity"])) > 0.001:
                claimed.quantity = float(line["quantity"])
            if line.get("service_at"):
                claimed.start_time = line.get("service_at")
            continue
        ok, extra, reason = _try_add_visit_item_from_government_line(
            db,
            visit.id,
            line["description"],
            float(line["quantity"]),
            actor_id,
            generic=line.get("generic"),
            source_type=line.get("source_type"),
        )
        if not ok or not extra:
            if _is_missing_price(reason):
                pending = _add_unpriced_line(db, visit, line, actor_id)
                if pending is not None:
                    by_key[key] = pending
                    existing_items.append(pending)
                    continue
            unmatched.append(
                {
                    "description": line["description"],
                    "quantity": line["quantity"],
                    "reason": reason or "No price list match found",
                }
            )
            continue
        new_item = _find_new_item(db, extra)
        if new_item is None:
            unmatched.append(
                {
                    "description": line["description"],
                    "quantity": line["quantity"],
                    "reason": "Saved the bill line but could not attach the GHIMS id",
                }
            )
            continue
        new_item.ghims_source_type = line["source_type"]
        new_item.ghims_source_id = line["source_id"]
        if line.get("service_at"):
            new_item.start_time = line.get("service_at")
        by_key[key] = new_item

    if mutate:
        now = utcnow()
        for key, item in by_key.items():
            if key in seen or item.cancelled or _companion_item_is_paid(item):
                continue
            item.cancelled = True
            item.cancelled_at = now
            item.cancelled_by_id = actor_id
            item.cancel_reason = SYNC_CANCEL_REASON
        sourced_names = {
            _norm_name(item.item_name)
            for item in list(existing_items) + list(by_key.values())
            if item.ghims_source_id and not item.cancelled
        }
        for item in existing_items:
            if item.ghims_source_id or item.cancelled:
                continue
            if item.paid_at or (item.receipt_number or "").strip():
                continue
            if _norm_name(item.item_name) in sourced_names:
                db.delete(item)
    return unmatched, missing_on_closed


def _fetch_recent_headers() -> List[Dict[str, Any]]:
    sql = f"""
        SELECT
          v.VisitationID, v.PatientID, v.InsuranceNo, v.VisitDate,
          v.VisitModeID, v.SponsorID, v.InsuranceTypeID,
          p.PatientName
        FROM dbo.Visitation v
        LEFT JOIN dbo.Patient p ON p.PatientID = v.PatientID
        WHERE ISNULL(v.SponsorID, '') NOT IN ('SELF', 'SELFN')
          AND ISNULL(v.InsuranceTypeID, '') NOT IN ('I100', 'CPP')
          AND (ISNULL(v.SponsorID, '') <> '' OR ISNULL(v.InsuranceTypeID, '') <> '')
          AND v.VisitDate >= CAST(GETDATE() AS date)
    """
    return _query(sql)


def _fetch_headers_for_patient(card: str) -> List[Dict[str, Any]]:
    sql = f"""
        SELECT
          v.VisitationID, v.PatientID, v.InsuranceNo, v.VisitDate,
          v.VisitModeID, v.SponsorID, v.InsuranceTypeID,
          p.PatientName
        FROM dbo.Visitation v
        LEFT JOIN dbo.Patient p ON p.PatientID = v.PatientID
        WHERE v.PatientID = ?
          AND (
            v.VisitDate >= DATEADD(day, -{int(ADMISSION_LOOKBACK_DAYS)}, CAST(GETDATE() AS date))
            OR v.VisitModeID = 'V006'
          )
    """
    return _query(sql, [card])


def _fetch_header(visitation_id: str) -> List[Dict[str, Any]]:
    sql = """
        SELECT TOP 1
          v.VisitationID, v.PatientID, v.InsuranceNo, v.VisitDate,
          v.VisitModeID, v.SponsorID, v.InsuranceTypeID,
          p.PatientName
        FROM dbo.Visitation v
        LEFT JOIN dbo.Patient p ON p.PatientID = v.PatientID
        WHERE v.VisitationID = ?
    """
    return _query(sql, [visitation_id])


def _fetch_bundles(visitation_ids: List[str]) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    bundles: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
        vid: _empty_bundle() for vid in visitation_ids
    }
    for chunk in _chunks(visitation_ids, 80):
        marks = ",".join("?" for _ in chunk)
        inv = _query(
            f"""
            SELECT
              i.VisitationID, i.LabRequestID, i.LabTestID, i.RequestStatusID, i.Qty,
              i.BillProcessDate, i.RequestDate,
              t.LabTestName
            FROM dbo.Investigation i
            LEFT JOIN dbo.LabTest t ON t.LabTestID = i.LabTestID
            WHERE i.VisitationID IN ({marks})
            """,
            chunk,
        )
        labs = _query(
            f"""
            SELECT
              l.VisitationID, l.LabByDoctorID, l.LabTestID, l.LabByDoctorStatusID, l.Qty,
              l.PrescriptionDate, l.LabByDoctorDate1,
              t.LabTestName
            FROM dbo.LabByDoctor l
            LEFT JOIN dbo.LabTest t ON t.LabTestID = l.LabTestID
            WHERE l.VisitationID IN ({marks})
            """,
            chunk,
        )
        try:
            rxs = _query(
                f"""
                SELECT
                  pr.VisitationID, pr.PrescriptionID, pr.DrugID, pr.Qty, pr.PrescriptionStatusID,
                  pr.PrescribeInfo1, pr.PrescInfo1, pr.PrescriptionDate,
                  dr.DrugName, dr.ProdInfo2
                FROM dbo.Prescription pr
                LEFT JOIN dbo.Drug dr ON dr.DrugID = pr.DrugID
                WHERE pr.VisitationID IN ({marks})
                """,
                chunk,
            )
        except Exception:
            rxs = _query(
                f"""
                SELECT
                  pr.VisitationID, pr.PrescriptionID, pr.DrugID, pr.Qty, pr.PrescriptionStatusID,
                  pr.PrescriptionDate,
                  dr.DrugName, dr.ProdInfo2
                FROM dbo.Prescription pr
                LEFT JOIN dbo.Drug dr ON dr.DrugID = pr.DrugID
                WHERE pr.VisitationID IN ({marks})
                """,
                chunk,
            )
        sales = _fetch_issued_sales(chunk)
        attach_issued_quantities(rxs, sales)
        attach_nhia_quantities(rxs, _fetch_nhia_medicine_qty(chunk))
        for row in inv:
            bundles.setdefault(_base_visit_id(row.get("VisitationID")), _empty_bundle())["investigations"].append(row)
        for row in labs:
            bundles.setdefault(_base_visit_id(row.get("VisitationID")), _empty_bundle())["labs"].append(row)
        for row in rxs:
            bundles.setdefault(_base_visit_id(row.get("VisitationID")), _empty_bundle())["prescriptions"].append(row)
        for row in sales:
            bundles.setdefault(_base_visit_id(row.get("VisitationID")), _empty_bundle())["sales"].append(row)
        for vid in chunk:
            base = _base_visit_id(vid)
            bundles.setdefault(base, _empty_bundle())
            if base != vid:
                bundles[vid] = bundles[base]
    return bundles


def _empty_bundle() -> Dict[str, List[Dict[str, Any]]]:
    return {"investigations": [], "labs": [], "prescriptions": [], "sales": []}


def _chunks(values: List[str], size: int) -> List[List[str]]:
    return [values[i : i + size] for i in range(0, len(values), size)]


def _normalize_sale_row(row: Dict[str, Any]) -> Dict[str, Any]:
    qty = dispensed_quantity(row)
    out = dict(row)
    out["IssuedQty"] = qty
    if qty > 0:
        out["Qty"] = qty
    return out


def _fetch_issued_sales(visitation_ids: List[str], *, force_reload_plan: bool = False) -> List[Dict[str, Any]]:
    """Pharmacy dispense lines from DrugSaleItems and DrugSaleItems2, including visit-C ids."""
    del force_reload_plan
    keys = _visit_id_keys(visitation_ids)
    if not keys:
        return []
    out: List[Dict[str, Any]] = []
    seen = set()
    for chunk in _chunks(keys, 80):
        marks = ",".join("?" for _ in chunk)
        queries = [
            (
                "DrugSaleItems2",
                f"""
                SELECT
                  d.DrugSaleID, d.VisitationID, d.DrugID, d.PrescriptionID,
                  d.DispenseAmt1, d.DispenseAmt2, d.DispenseDate, d.Qty,
                  dr.DrugName, dr.ProdInfo2
                FROM dbo.DrugSaleItems2 d
                LEFT JOIN dbo.Drug dr ON dr.DrugID = d.DrugID
                WHERE d.VisitationID IN ({marks})
                """,
            ),
            (
                "DrugSaleItems",
                f"""
                SELECT
                  d.DrugSaleID, d.VisitationID, d.DrugID,
                  CAST(NULL AS nvarchar(128)) AS PrescriptionID,
                  CAST(NULL AS float) AS DispenseAmt1,
                  CAST(NULL AS float) AS DispenseAmt2,
                  d.DispenseDate, d.Qty,
                  dr.DrugName, dr.ProdInfo2
                FROM dbo.DrugSaleItems d
                LEFT JOIN dbo.Drug dr ON dr.DrugID = d.DrugID
                WHERE d.VisitationID IN ({marks})
                """,
            ),
        ]
        for table, sql in queries:
            try:
                rows = _query(sql, chunk)
            except Exception:
                logger.exception("Could not read GHIMS %s dispense quantities", table)
                continue
            for row in rows:
                normalized = _normalize_sale_row(row)
                key = (
                    str(normalized.get("DrugSaleID") or "").strip(),
                    str(normalized.get("DrugID") or "").strip(),
                    str(normalized.get("PrescriptionID") or "").strip(),
                )
                if key in seen or dispensed_quantity(normalized) <= 0:
                    continue
                seen.add(key)
                out.append(normalized)
    return out


def _fetch_nhia_medicine_qty(visitation_ids: List[str]) -> List[Dict[str, Any]]:
    keys = _visit_id_keys(visitation_ids)
    if not keys:
        return []
    out: List[Dict[str, Any]] = []
    for chunk in _chunks(keys, 80):
        marks = ",".join("?" for _ in chunk)
        try:
            out.extend(
                _query(
                    f"""
                    SELECT
                      claimID, medicineCode, medicineName, drugName, description, qty, aType
                    FROM dbo.vwNHIAClaimLines
                    WHERE claimID IN ({marks})
                    """,
                    chunk,
                )
            )
        except Exception:
            logger.exception("Could not read GHIMS NHIA medicine quantities")
            return out
    return out


def _query(sql: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
    cn = _connect()
    try:
        cur = cn.cursor()
        cur.execute(sql, params or [])
        return _rows_as_dicts(cur)
    finally:
        cn.close()


def repair_duplicate_live_sync(db: Session) -> Dict[str, int]:
    """
    Remove unpaid synced visits that are not from today, and extra copies of a line.
    Leaves manual and Excel visits alone. Skips any synced visit that already has a payment.
    """
    from datetime import date

    from app.models.companion_government_ipd_export import CompanionGovernmentIpdExport
    from app.models.companion_government_opd_export import CompanionGovernmentOpdExport
    from app.models.companion_inventory_debit import CompanionInventoryDebit

    visits = db.query(CompanionVisit).filter(CompanionVisit.source == SOURCE_LIVE).all()
    if not visits:
        return {"visits_removed": 0, "lines_removed": 0, "visits_kept": 0}

    dates = _fetch_visit_dates([v.external_visit_number for v in visits])
    today = date.today()
    remove_ids: List[int] = []
    kept: List[CompanionVisit] = []
    for visit in visits:
        if _visit_has_payment(db, visit.id):
            kept.append(visit)
            continue
        raw = dates.get((visit.external_visit_number or "").strip())
        visit_date = _parse_visit_date(raw)
        day = visit_date.date() if visit_date is not None and hasattr(visit_date, "date") else None
        if day is None or day < today:
            remove_ids.append(visit.id)
        else:
            if visit_date is not None:
                visit.ghims_visit_date = visit_date
            kept.append(visit)

    _delete_visits(db, remove_ids, CompanionVisitItem, CompanionGovernmentOpdExport, CompanionGovernmentIpdExport, CompanionInventoryDebit)
    db.flush()
    db.expire_all()

    lines_removed = 0
    for visit in kept:
        items = (
            db.query(CompanionVisitItem)
            .filter(CompanionVisitItem.companion_visit_id == visit.id)
            .order_by(CompanionVisitItem.id.asc())
            .all()
        )
        seen = set()
        for item in items:
            if item.paid_at or (item.receipt_number or "").strip():
                continue
            key = _norm_name(item.item_name)
            if key in seen:
                db.delete(item)
                lines_removed += 1
            else:
                seen.add(key)
    db.commit()
    return {"visits_removed": len(remove_ids), "lines_removed": lines_removed, "visits_kept": len(kept)}


def _visit_has_payment(db: Session, visit_id: int) -> bool:
    items = (
        db.query(CompanionVisitItem)
        .filter(CompanionVisitItem.companion_visit_id == visit_id)
        .all()
    )
    for item in items:
        if item.paid_at or (item.receipt_number or "").strip():
            return True
    return False


def _fetch_visit_dates(visitation_ids: List[str]) -> Dict[str, Any]:
    found: Dict[str, Any] = {}
    clean = [vid.strip() for vid in visitation_ids if vid and vid.strip()]
    for chunk in _chunks(clean, 80):
        marks = ",".join("?" for _ in chunk)
        rows = _query(
            f"""
            SELECT VisitationID, VisitDate
            FROM dbo.Visitation
            WHERE VisitationID IN ({marks})
            """,
            chunk,
        )
        for row in rows:
            found[str(row.get("VisitationID") or "").strip()] = row.get("VisitDate")
    return found


def _delete_visits(db: Session, visit_ids: List[int], item_model, opd_model, ipd_model, debit_model) -> None:
    for chunk in _chunks(visit_ids, 200):
        if not chunk:
            continue
        db.query(item_model).filter(item_model.companion_visit_id.in_(chunk)).delete(synchronize_session=False)
        db.query(opd_model).filter(opd_model.companion_visit_id.in_(chunk)).delete(synchronize_session=False)
        db.query(ipd_model).filter(ipd_model.companion_visit_id.in_(chunk)).delete(synchronize_session=False)
        db.query(debit_model).filter(debit_model.companion_visit_id.in_(chunk)).delete(synchronize_session=False)
        db.query(CompanionVisit).filter(CompanionVisit.id.in_(chunk)).delete(synchronize_session=False)
