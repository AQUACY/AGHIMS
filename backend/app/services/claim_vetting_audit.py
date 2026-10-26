"""Itemized vetting audit for GHIMS XML import and monthly (ghims_live) claims."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

from app.core.audit import is_super_admin
from app.models.claim_vetting_event import ClaimVettingEvent
from app.models.claim_xml_import import ClaimXmlImportItem
from app.models.user import User

ACTION_LABELS = {
    "imported": "Imported onto HMS",
    "ghims_synced": "Synced from GHIMS",
    "updated": "Edited claim",
    "pharmacy_vetted": "Pharmacy vetted",
    "pharmacy_vet_reverted": "Pharmacy vet reverted",
    "doctor_vetted": "Doctor vetted",
    "doctor_vet_reverted": "Doctor vet reverted",
    "finalized": "Claims finalized",
    "reopened": "Reopened to draft",
    "flagged": "Flagged",
    "assigned": "Assigned",
    "unassigned": "Unassigned",
    "merged": "Merged into another claim",
    "merge_received": "Received merged visit",
    "merge_reverted": "Merge reverted",
    "ai_applied": "AI suggestion applied",
    "ai_vetted": "AI vetted",
}

SCALAR_LABELS = {
    "claimID": "claim ID",
    "claimCheckCode": "claim check code",
    "preAuthorizationCodes": "pre-authorization",
    "physicianID": "physician ID",
    "memberNo": "member number",
    "cardSerialNo": "card serial",
    "surname": "surname",
    "otherNames": "other names",
    "dateOfBirth": "date of birth",
    "gender": "gender",
    "hospitalRecNo": "hospital record number",
    "isDependant": "dependant",
    "typeOfService": "type of service",
    "isUnbundled": "unbundled",
    "includesPharmacy": "includes pharmacy",
    "typeOfAttendance": "attendance type",
    "serviceOutcome": "service outcome",
    "specialtyAttended": "specialty",
    "principalGDRG": "principal GDRG",
    "dateOfService": "date of service",
}

MED_FIELD_LABELS = {
    "medicineCode": "medicine code",
    "medicineName": "medicine name",
    "drugName": "drug name",
    "dispensedQty": "quantity",
    "serviceDate": "service date",
}

RX_FIELD_LABELS = {
    "dose": "dose",
    "frequency": "frequency",
    "duration": "duration",
    "unparsed": "prescription text",
}

DX_FIELD_LABELS = {
    "gdrgCode": "GDRG",
    "icd10": "ICD-10",
    "diagnosis": "diagnosis",
}

INV_FIELD_LABELS = {
    "serviceDate": "service date",
    "gdrgCode": "GDRG",
}

PROC_FIELD_LABELS = {
    "serviceDate": "service date",
    "gdrgCode": "GDRG",
    "description": "description",
    "icd10": "ICD-10",
    "diagnosis": "diagnosis",
}

SKIP_SCALAR_KEYS = {
    "diagnoses",
    "investigations",
    "medicines",
    "procedures",
    "dateOfService",
}


def snapshot_payload(payload: Any) -> Dict[str, Any]:
    try:
        return json.loads(json.dumps(payload or {}, default=str))
    except (TypeError, ValueError):
        return dict(payload) if isinstance(payload, dict) else {}


def _norm(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (list, tuple)):
        parts = [_norm(v) for v in value if _norm(v)]
        return ", ".join(parts)
    if isinstance(value, dict):
        try:
            return json.dumps(value, sort_keys=True, default=str)
        except (TypeError, ValueError):
            return str(value)
    text = str(value).strip()
    try:
        num = float(text)
        if abs(num - round(num)) < 1e-9:
            return str(int(round(num)))
        return ("%f" % num).rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return text


def _display(value: Any) -> str:
    text = _norm(value)
    return text if text else "(empty)"


def _change(
    *,
    kind: str,
    section: str,
    field: Optional[str],
    field_label: str,
    old: Any = None,
    new: Any = None,
    item_label: Optional[str] = None,
    path: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "kind": kind,
        "section": section,
        "item_label": item_label,
        "field": field,
        "field_label": field_label,
        "old": None if kind == "added" else _display(old) if kind != "added" else None,
        "new": None if kind == "removed" else _display(new) if kind != "removed" else None,
        "path": path,
    }


def _scalar_changes(old: Dict[str, Any], new: Dict[str, Any]) -> List[Dict[str, Any]]:
    changes: List[Dict[str, Any]] = []
    keys = set(old.keys()) | set(new.keys())
    for key in sorted(keys):
        if key in SKIP_SCALAR_KEYS or str(key).startswith("_"):
            continue
        if not isinstance(old.get(key), (dict, list)) and not isinstance(new.get(key), (dict, list)):
            if _norm(old.get(key)) == _norm(new.get(key)):
                continue
            label = SCALAR_LABELS.get(key, key)
            kind = "changed"
            if key not in old or (_norm(old.get(key)) == "" and _norm(new.get(key)) != "" and key not in old):
                kind = "changed"
            changes.append(
                _change(
                    kind=kind,
                    section="claim",
                    field=key,
                    field_label=label,
                    old=old.get(key),
                    new=new.get(key),
                    path=key,
                )
            )
    if _norm(old.get("dateOfService")) != _norm(new.get("dateOfService")):
        changes.append(
            _change(
                kind="changed",
                section="claim",
                field="dateOfService",
                field_label="date of service",
                old=old.get("dateOfService"),
                new=new.get("dateOfService"),
                path="dateOfService",
            )
        )
    return changes


def _row_key(row: Dict[str, Any], fields: Sequence[str]) -> Tuple[str, ...]:
    return tuple(_norm(row.get(f)) for f in fields)


def _medicine_label(row: Dict[str, Any]) -> str:
    name = (
        str(row.get("medicineName") or row.get("drugName") or row.get("description") or "").strip()
        or str(row.get("medicineCode") or "").strip()
        or "medicine"
    )
    code = str(row.get("medicineCode") or "").strip()
    if code and code.lower() not in name.lower():
        return f"{name} ({code})"
    return name


def _dx_label(row: Dict[str, Any]) -> str:
    return (
        str(row.get("diagnosis") or "").strip()
        or str(row.get("icd10") or "").strip()
        or str(row.get("gdrgCode") or "").strip()
        or "diagnosis"
    )


def _inv_label(row: Dict[str, Any]) -> str:
    return str(row.get("gdrgCode") or row.get("_serviceName") or "investigation").strip()


def _proc_label(row: Dict[str, Any]) -> str:
    return (
        str(row.get("description") or "").strip()
        or str(row.get("gdrgCode") or "").strip()
        or "procedure"
    )


def _match_rows(
    old_rows: List[Dict[str, Any]],
    new_rows: List[Dict[str, Any]],
    key_fields: Sequence[str],
) -> Tuple[List[Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], int]], List[int], List[int]]:
    used_new = set()
    pairs: List[Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], int]] = []
    unmatched_old: List[int] = []
    for oi, old in enumerate(old_rows):
        old_key = _row_key(old, key_fields)
        found = None
        if any(old_key):
            for ni, new in enumerate(new_rows):
                if ni in used_new:
                    continue
                if _row_key(new, key_fields) == old_key:
                    found = ni
                    break
        if found is None and not any(old_key) and oi < len(new_rows) and oi not in used_new:
            found = oi
        if found is None:
            unmatched_old.append(oi)
            continue
        used_new.add(found)
        pairs.append((old, new_rows[found], found))
    unmatched_new = [i for i in range(len(new_rows)) if i not in used_new]
    return pairs, unmatched_old, unmatched_new


def _dict_field_changes(
    old_row: Dict[str, Any],
    new_row: Dict[str, Any],
    labels: Dict[str, str],
    *,
    section: str,
    item_label: str,
    path_prefix: str,
    nested_key: Optional[str] = None,
    nested_labels: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    changes: List[Dict[str, Any]] = []
    for field, label in labels.items():
        if _norm(old_row.get(field)) == _norm(new_row.get(field)):
            continue
        kind = "changed"
        if _norm(old_row.get(field)) == "" and _norm(new_row.get(field)) != "":
            kind = "changed"
        changes.append(
            _change(
                kind=kind,
                section=section,
                field=field,
                field_label=label,
                old=old_row.get(field),
                new=new_row.get(field),
                item_label=item_label,
                path=f"{path_prefix}.{field}",
            )
        )
    if nested_key and nested_labels:
        old_nested = old_row.get(nested_key) if isinstance(old_row.get(nested_key), dict) else {}
        new_nested = new_row.get(nested_key) if isinstance(new_row.get(nested_key), dict) else {}
        for field, label in nested_labels.items():
            if _norm(old_nested.get(field)) == _norm(new_nested.get(field)):
                continue
            changes.append(
                _change(
                    kind="changed",
                    section=section,
                    field=field,
                    field_label=label,
                    old=old_nested.get(field),
                    new=new_nested.get(field),
                    item_label=item_label,
                    path=f"{path_prefix}.{nested_key}.{field}",
                )
            )
    return changes


def _list_changes(
    old_payload: Dict[str, Any],
    new_payload: Dict[str, Any],
    *,
    key: str,
    section: str,
    key_fields: Sequence[str],
    labels: Dict[str, str],
    label_fn,
    nested_key: Optional[str] = None,
    nested_labels: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    old_rows = [r for r in (old_payload.get(key) or []) if isinstance(r, dict)]
    new_rows = [r for r in (new_payload.get(key) or []) if isinstance(r, dict)]
    pairs, unmatched_old, unmatched_new = _match_rows(old_rows, new_rows, key_fields)
    changes: List[Dict[str, Any]] = []
    for old_row, new_row, ni in pairs:
        item_label = label_fn(new_row or old_row or {})
        changes.extend(
            _dict_field_changes(
                old_row or {},
                new_row or {},
                labels,
                section=section,
                item_label=item_label,
                path_prefix=f"{key}[{ni}]",
                nested_key=nested_key,
                nested_labels=nested_labels,
            )
        )
    for oi in unmatched_old:
        row = old_rows[oi]
        changes.append(
            _change(
                kind="removed",
                section=section,
                field=None,
                field_label=section.rstrip("s"),
                old=label_fn(row),
                new=None,
                item_label=label_fn(row),
                path=f"{key}[{oi}]",
            )
        )
    for ni in unmatched_new:
        row = new_rows[ni]
        extra = []
        if section == "medicines":
            qty = _norm(row.get("dispensedQty"))
            dose = _norm((row.get("prescription") or {}).get("dose") if isinstance(row.get("prescription"), dict) else "")
            if qty:
                extra.append(f"qty {qty}")
            if dose:
                extra.append(f"dose {dose}")
        suffix = f" ({', '.join(extra)})" if extra else ""
        changes.append(
            _change(
                kind="added",
                section=section,
                field=None,
                field_label=section.rstrip("s"),
                old=None,
                new=f"{label_fn(row)}{suffix}",
                item_label=label_fn(row),
                path=f"{key}[{ni}]",
            )
        )
    return changes


def diff_claim_payloads(old_payload: Any, new_payload: Any) -> List[Dict[str, Any]]:
    old = snapshot_payload(old_payload)
    new = snapshot_payload(new_payload)
    changes: List[Dict[str, Any]] = []
    changes.extend(_scalar_changes(old, new))
    changes.extend(
        _list_changes(
            old,
            new,
            key="medicines",
            section="medicines",
            key_fields=("medicineCode", "serviceDate"),
            labels=MED_FIELD_LABELS,
            label_fn=_medicine_label,
            nested_key="prescription",
            nested_labels=RX_FIELD_LABELS,
        )
    )
    changes.extend(
        _list_changes(
            old,
            new,
            key="diagnoses",
            section="diagnoses",
            key_fields=("icd10", "gdrgCode"),
            labels=DX_FIELD_LABELS,
            label_fn=_dx_label,
        )
    )
    changes.extend(
        _list_changes(
            old,
            new,
            key="investigations",
            section="investigations",
            key_fields=("gdrgCode", "serviceDate"),
            labels=INV_FIELD_LABELS,
            label_fn=_inv_label,
        )
    )
    changes.extend(
        _list_changes(
            old,
            new,
            key="procedures",
            section="procedures",
            key_fields=("gdrgCode", "serviceDate"),
            labels=PROC_FIELD_LABELS,
            label_fn=_proc_label,
        )
    )
    return changes


def summarize_event(action: str, changes: Optional[List[Dict[str, Any]]], extra: Optional[str] = None) -> str:
    label = ACTION_LABELS.get(action, action.replace("_", " "))
    parts: List[str] = []
    for ch in changes or []:
        item = ch.get("item_label")
        field = ch.get("field_label") or ch.get("field") or ""
        kind = ch.get("kind")
        if kind == "added":
            parts.append(f"added {item or field}: {ch.get('new')}")
        elif kind == "removed":
            parts.append(f"removed {item or field}")
        elif item and field:
            parts.append(f"changed {field} of {item} from {ch.get('old')} to {ch.get('new')}")
        elif field:
            parts.append(f"changed {field} from {ch.get('old')} to {ch.get('new')}")
        if len(parts) >= 6:
            break
    if extra:
        parts.insert(0, extra)
    if not parts:
        return label
    rest = "; ".join(parts)
    if len(rest) > 900:
        rest = rest[:897] + "..."
    return f"{label}: {rest}"


def record_claim_vetting_event(
    db: Session,
    *,
    item: ClaimXmlImportItem,
    action: str,
    user: Optional[User] = None,
    changes: Optional[List[Dict[str, Any]]] = None,
    details: Optional[Dict[str, Any]] = None,
    summary: Optional[str] = None,
    skip_if_empty: bool = False,
) -> Optional[ClaimVettingEvent]:
    if user is not None and is_super_admin(user):
        return None
    change_list = list(changes or [])
    if skip_if_empty and not change_list and action == "updated":
        return None
    event = ClaimVettingEvent(
        item_id=item.id,
        batch_id=getattr(item, "batch_id", None),
        claim_claim_id=getattr(item, "claim_claim_id", None),
        user_id=getattr(user, "id", None) if user else None,
        username=getattr(user, "username", None) if user else "system",
        full_name=getattr(user, "full_name", None) if user else "System",
        role=getattr(user, "role", None) if user else None,
        action=action,
        summary=summary or summarize_event(action, change_list, extra=(details or {}).get("note")),
        changes=change_list or None,
        details=details,
    )
    db.add(event)
    return event


def serialize_claim_vetting_event(event: ClaimVettingEvent) -> Dict[str, Any]:
    return {
        "id": event.id,
        "item_id": event.item_id,
        "claim_claim_id": event.claim_claim_id,
        "action": event.action,
        "action_label": ACTION_LABELS.get(event.action, event.action.replace("_", " ")),
        "summary": event.summary,
        "changes": event.changes or [],
        "details": event.details or {},
        "user_id": event.user_id,
        "username": event.username,
        "full_name": event.full_name or event.username,
        "role": event.role,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


def list_claim_vetting_events(db: Session, item_id: int) -> Dict[str, Any]:
    events = (
        db.query(ClaimVettingEvent)
        .filter(ClaimVettingEvent.item_id == item_id)
        .order_by(ClaimVettingEvent.created_at.asc(), ClaimVettingEvent.id.asc())
        .all()
    )
    serialized = [serialize_claim_vetting_event(e) for e in events]
    actors = []
    seen = set()
    for row in serialized:
        key = row.get("user_id") or row.get("username")
        if key in seen:
            continue
        seen.add(key)
        actors.append(
            {
                "user_id": row.get("user_id"),
                "full_name": row.get("full_name"),
                "username": row.get("username"),
                "role": row.get("role"),
            }
        )
    return {"events": serialized, "actors": actors, "count": len(serialized)}
