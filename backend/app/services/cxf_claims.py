"""
Parse ClaimIT CFX packages (zlib + PHP-serialized) and compare/convert to GHIMS claims XML.
"""
from __future__ import annotations

import re
import zlib
import xml.etree.ElementTree as ET
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from app.services.claim_xml_import_parser import (
    build_claims_xml_from_payloads,
    parse_claims_xml,
)


class CxfParseError(ValueError):
    """Raised when a CFX file cannot be parsed."""


# ---------- PHP unserialize (byte-based; PHP string lengths are bytes) ----------

class _PhpUnserializer:
    def __init__(self, data: bytes):
        self.data = data
        self.i = 0
        self.n = len(data)

    def _peek(self) -> int:
        if self.i >= self.n:
            raise CxfParseError("Unexpected end of PHP serialized data")
        return self.data[self.i]

    def _eat(self, expected: bytes) -> None:
        if not self.data.startswith(expected, self.i):
            raise CxfParseError(f"Expected {expected!r} at pos {self.i}")
        self.i += len(expected)

    def _read_until(self, ch: bytes) -> bytes:
        j = self.data.find(ch, self.i)
        if j < 0:
            raise CxfParseError(f"Expected {ch!r} after pos {self.i}")
        out = self.data[self.i:j]
        self.i = j + 1
        return out

    def parse(self) -> Any:
        return self._parse_value()

    def _parse_value(self) -> Any:
        t = self._peek()
        if t == ord(b"N"):
            self._eat(b"N;")
            return None
        if t == ord(b"b"):
            self._eat(b"b:")
            v = self._read_until(b";")
            return v == b"1"
        if t == ord(b"i"):
            self._eat(b"i:")
            return int(self._read_until(b";"))
        if t == ord(b"d"):
            self._eat(b"d:")
            return float(self._read_until(b";"))
        if t == ord(b"s"):
            return self._parse_string()
        if t == ord(b"a"):
            return self._parse_array()
        if t == ord(b"O"):
            return self._parse_object()
        if t in (ord(b"R"), ord(b"r")):
            self._eat(bytes([t]) + b":")
            self._read_until(b";")
            return None
        raise CxfParseError(f"Unsupported PHP type {bytes([t])!r} at pos {self.i}")

    def _parse_string(self) -> str:
        self._eat(b"s:")
        length = int(self._read_until(b":"))
        self._eat(b'"')
        raw = self.data[self.i:self.i + length]
        self.i += length
        self._eat(b'";')
        return raw.decode("utf-8", errors="replace")

    def _parse_array(self) -> Any:
        self._eat(b"a:")
        count = int(self._read_until(b":"))
        self._eat(b"{")
        items: Dict[Any, Any] = {}
        all_int_keys = True
        for _ in range(count):
            key = self._parse_value()
            val = self._parse_value()
            items[key] = val
            if not isinstance(key, int):
                all_int_keys = False
        self._eat(b"}")
        if all_int_keys and items:
            keys = sorted(items.keys())
            if keys == list(range(len(keys))):
                return [items[k] for k in keys]
        return items

    def _parse_object(self) -> Dict[str, Any]:
        self._eat(b"O:")
        name_len = int(self._read_until(b":"))
        self._eat(b'"')
        class_name = self.data[self.i:self.i + name_len].decode("utf-8", errors="replace")
        self.i += name_len
        self._eat(b'":')
        prop_count = int(self._read_until(b":"))
        self._eat(b"{")
        props: Dict[str, Any] = {"__class__": class_name}
        for _ in range(prop_count):
            key = self._parse_value()
            val = self._parse_value()
            if isinstance(key, str):
                key = key.split("\x00")[-1]
            props[str(key)] = val
        self._eat(b"}")
        return props


def php_unserialize(data: bytes) -> Any:
    return _PhpUnserializer(data).parse()


def _as_list(obj: Any) -> List[Any]:
    if obj is None:
        return []
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        # int-keyed dict
        try:
            keys = sorted(obj.keys(), key=lambda k: int(k) if str(k).isdigit() else str(k))
        except Exception:
            keys = list(obj.keys())
        return [obj[k] for k in keys]
    return []


def _s(val: Any) -> str:
    if val is None:
        return ""
    return str(val).strip()


def _norm_ccc(val: Any) -> str:
    return _s(val)


def _norm_hosp(val: Any) -> str:
    return _s(val).upper()


def decompress_cxf(raw: bytes) -> bytes:
    """CFX = 3-byte header + zlib payload → PHP-serialized bytes."""
    if not raw or len(raw) < 4:
        raise CxfParseError("CFX file is empty or too small")
    last_err: Optional[Exception] = None
    for skip in (3, 0, 1, 2, 4):
        if skip >= len(raw):
            continue
        try:
            return zlib.decompress(raw[skip:])
        except Exception as e:
            last_err = e
            continue
    raise CxfParseError(f"Could not decompress CFX: {last_err}")


def parse_cxf(raw: bytes) -> Dict[str, Any]:
    """
    Parse a ClaimIT CFX file into structured claim records ready for conversion/diff.
    Returns:
      {
        meta: {...},
        claims: [ { guid, header, payload, status, ... }, ... ],
        claim_count: N,
      }
    """
    payload_bytes = decompress_cxf(raw)
    try:
        root = php_unserialize(payload_bytes)
    except CxfParseError:
        raise
    except Exception as e:
        raise CxfParseError(f"Could not unserialize CFX payload: {e}") from e

    if not isinstance(root, dict):
        raise CxfParseError("Unexpected CFX root structure")

    data = root.get("data") if isinstance(root.get("data"), dict) else root
    if not isinstance(data, dict):
        raise CxfParseError("CFX missing data section")

    claims_raw = _as_list(data.get("claims"))
    services_raw = _as_list(data.get("serviceentries"))
    medicines_raw = _as_list(data.get("medicineentries"))

    services_by_guid: Dict[str, List[dict]] = defaultdict(list)
    for row in services_raw:
        if not isinstance(row, dict):
            continue
        guid = _s(row.get("_claim_id"))
        if guid:
            services_by_guid[guid].append(row)

    medicines_by_guid: Dict[str, List[dict]] = defaultdict(list)
    for row in medicines_raw:
        if not isinstance(row, dict):
            continue
        guid = _s(row.get("_claim_id"))
        if guid:
            medicines_by_guid[guid].append(row)

    claims: List[Dict[str, Any]] = []
    status_counts: Dict[str, int] = defaultdict(int)
    for row in claims_raw:
        if not isinstance(row, dict):
            continue
        guid = _s(row.get("guid"))
        if not guid:
            continue
        services = services_by_guid.get(guid, [])
        medicines = medicines_by_guid.get(guid, [])
        payload = cxf_claim_to_payload(row, services, medicines)
        status = _s(row.get("status")) or "UNKNOWN"
        status_counts[status] += 1
        claims.append({
            "guid": guid,
            "status": status,
            "claimCheckCode": _s(row.get("claimCheckCode")),
            "hospitalRecNo": _s(row.get("hospitalRecNo")),
            "memberNo": _s(row.get("memberNo")),
            "surname": _s(row.get("surname")),
            "otherNames": _s(row.get("otherNames")),
            "typeOfService": _s(row.get("typeOfService")),
            "minDOSP": _s(row.get("minDOSP")),
            "maxDOSP": _s(row.get("maxDOSP")),
            "payload": payload,
            "header": row,
        })

    meta = {
        "lockID": _s(root.get("lockID")),
        "dateGenerated": _s(root.get("dateGenerated")),
        "signedByName": _s(root.get("signedByName")),
        "signedByUsername": _s(root.get("signedByUsername")),
        "signedByRole": _s(root.get("signedByRole")),
        "status_counts": dict(status_counts),
    }
    return {
        "meta": meta,
        "claims": claims,
        "claim_count": len(claims),
    }


def _collect_service_dates(header: dict) -> List[str]:
    dates: List[str] = []
    for key in ("minDOSP", "maxDOSP", "serviceProvisionDates"):
        val = header.get(key)
        if val is None:
            continue
        if isinstance(val, list):
            dates.extend(_s(x) for x in val if _s(x))
        elif isinstance(val, dict):
            dates.extend(_s(x) for x in val.values() if _s(x))
        else:
            s = _s(val)
            if s:
                # may be comma-separated
                for part in re.split(r"[,;|\s]+", s):
                    if re.match(r"^\d{4}-\d{2}-\d{2}$", part):
                        dates.append(part)
    # unique sorted
    seen: Set[str] = set()
    out: List[str] = []
    for d in sorted(dates):
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out


def _build_prescription_unparsed(med: dict) -> Dict[str, str]:
    dose_value = _s(med.get("dose_value"))
    dose_unit = _s(med.get("dose_unit"))
    freq_desc = _s(med.get("frequency_desc")) or _s(med.get("frequency_value"))
    freq_unit = _s(med.get("frequency_unit"))
    dur_value = _s(med.get("duration_value"))
    dur_unit = _s(med.get("duration_unit"))
    dur_desc = _s(med.get("duration_desc"))
    unparsed = _s(med.get("unparsed"))
    extra = _s(med.get("extraDirections"))

    dose = " ".join(x for x in [dose_value, dose_unit] if x).strip()
    frequency = " ".join(x for x in [freq_desc, freq_unit] if x).strip()
    if dur_desc:
        duration = dur_desc
    else:
        duration = " ".join(x for x in [dur_value, dur_unit] if x).strip()

    if not unparsed:
        parts = [p for p in [dose, frequency, duration, extra] if p]
        unparsed = ", ".join(parts)

    return {
        "dose": dose,
        "frequency": frequency,
        "duration": duration,
        "unparsed": unparsed,
    }


def cxf_claim_to_payload(header: dict, services: List[dict], medicines: List[dict]) -> Dict[str, Any]:
    guid = _s(header.get("guid"))
    diagnoses: List[dict] = []
    investigations: List[dict] = []
    procedures: List[dict] = []
    for svc in services:
        et = _s(svc.get("entryType")).lower()
        if et == "diag":
            diagnoses.append({
                "gdrgCode": _s(svc.get("gdrgCode")),
                "icd10": _s(svc.get("icd10")) or _s(svc.get("suggestedICD10")),
                "diagnosis": _s(svc.get("description")),
            })
        elif et == "inve":
            investigations.append({
                "serviceDate": _s(svc.get("serviceDate")),
                "gdrgCode": _s(svc.get("gdrgCode")),
            })
        elif et == "proc":
            procedures.append({
                "serviceDate": _s(svc.get("serviceDate")),
                "gdrgCode": _s(svc.get("gdrgCode")),
                "description": _s(svc.get("description")),
                "icd10": _s(svc.get("icd10")),
                "diagnosis": "",
            })

    meds: List[dict] = []
    for med in medicines:
        meds.append({
            "medicineCode": _s(med.get("medicineCode")),
            "dispensedQty": _s(med.get("dispensedQty") if med.get("dispensedQty") is not None else med.get("qty")),
            "serviceDate": _s(med.get("serviceDate")),
            "prescription": _build_prescription_unparsed(med),
        })

    is_dep = header.get("isDependant")
    if is_dep is None:
        is_dependant = ""
    elif str(is_dep) in ("1", "true", "True", "Y", "y"):
        is_dependant = "1"
    else:
        is_dependant = "0"

    return {
        "claimID": guid,
        "claimCheckCode": _s(header.get("claimCheckCode")),
        "preAuthorizationCodes": _s(header.get("preAuthorizationCodes")),
        "physicianID": _s(header.get("physicianID")),
        "memberNo": _s(header.get("memberNo")),
        "cardSerialNo": _s(header.get("cardSerialNo")),
        "surname": _s(header.get("surname")),
        "otherNames": _s(header.get("otherNames")),
        "dateOfBirth": _s(header.get("dateOfBirth")),
        "gender": _s(header.get("gender")),
        "hospitalRecNo": _s(header.get("hospitalRecNo")),
        "isDependant": is_dependant,
        "typeOfService": _s(header.get("typeOfService")),
        "isUnbundled": _s(header.get("isUnbundled")) or "0",
        "includesPharmacy": _s(header.get("includesPharmacy")) or ("1" if meds else "0"),
        "typeOfAttendance": _s(header.get("typeOfAttendance")),
        "serviceOutcome": _s(header.get("serviceOutcome")),
        "specialtyAttended": _s(header.get("specialtyAttended")),
        "principalGDRG": _s(header.get("principalGDRG")),
        "dateOfService": _collect_service_dates(header),
        "diagnoses": diagnoses,
        "investigations": investigations,
        "medicines": meds,
        "procedures": procedures,
    }


def convert_cxf_to_xml(raw: bytes) -> Tuple[str, Dict[str, Any]]:
    parsed = parse_cxf(raw)
    payloads = [c["payload"] for c in parsed["claims"]]
    xml_content = build_claims_xml_from_payloads(payloads)
    summary = {
        "claim_count": parsed["claim_count"],
        "meta": parsed.get("meta") or {},
        "status_counts": (parsed.get("meta") or {}).get("status_counts") or {},
    }
    return xml_content, summary


def _fingerprint_payload(payload: dict) -> Dict[str, Any]:
    diags = payload.get("diagnoses") or []
    invs = payload.get("investigations") or []
    meds = payload.get("medicines") or []
    procs = payload.get("procedures") or []
    return {
        "claimCheckCode": _s(payload.get("claimCheckCode")),
        "memberNo": _s(payload.get("memberNo")),
        "hospitalRecNo": _norm_hosp(payload.get("hospitalRecNo")),
        "surname": _s(payload.get("surname")).upper(),
        "otherNames": _s(payload.get("otherNames")).upper(),
        "dateOfBirth": _s(payload.get("dateOfBirth")),
        "typeOfService": _s(payload.get("typeOfService")).upper(),
        "typeOfAttendance": _s(payload.get("typeOfAttendance")).upper(),
        "specialtyAttended": _s(payload.get("specialtyAttended")).upper(),
        "principalGDRG": _s(payload.get("principalGDRG")).upper(),
        "dateOfService": sorted(_s(d) for d in (payload.get("dateOfService") or []) if _s(d)),
        "diagnosis_count": len(diags),
        "investigation_count": len(invs),
        "medicine_count": len(meds),
        "procedure_count": len(procs),
        "icd10_set": sorted({_s(d.get("icd10")).upper() for d in diags if _s(d.get("icd10"))}),
        "medicine_codes": sorted({_s(m.get("medicineCode")).upper() for m in meds if _s(m.get("medicineCode"))}),
        "gdrg_diag": sorted({_s(d.get("gdrgCode")).upper() for d in diags if _s(d.get("gdrgCode"))}),
    }


_COMPARE_FIELDS = [
    "claimCheckCode", "memberNo", "hospitalRecNo", "surname", "otherNames", "dateOfBirth",
    "typeOfService", "typeOfAttendance", "specialtyAttended", "principalGDRG", "dateOfService",
    "diagnosis_count", "investigation_count", "medicine_count", "procedure_count",
    "icd10_set", "medicine_codes", "gdrg_diag",
]


def _field_diffs(xml_fp: dict, cxf_fp: dict) -> List[Dict[str, Any]]:
    diffs = []
    for key in _COMPARE_FIELDS:
        a = xml_fp.get(key)
        b = cxf_fp.get(key)
        if a != b:
            diffs.append({"field": key, "xml": a, "cxf": b})
    return diffs


def _index_cxf_claims(cxf_claims: List[dict]) -> Tuple[Dict[str, List[dict]], Dict[str, List[dict]]]:
    by_ccc: Dict[str, List[dict]] = defaultdict(list)
    by_hosp: Dict[str, List[dict]] = defaultdict(list)
    for c in cxf_claims:
        ccc = _norm_ccc(c.get("claimCheckCode"))
        hosp = _norm_hosp(c.get("hospitalRecNo"))
        if ccc:
            by_ccc[ccc].append(c)
        if hosp:
            by_hosp[hosp].append(c)
    return by_ccc, by_hosp


def _match_xml_to_cxf(
    xml_payload: dict,
    by_ccc: Dict[str, List[dict]],
    by_hosp: Dict[str, List[dict]],
    used_guids: Set[str],
) -> Optional[dict]:
    ccc = _norm_ccc(xml_payload.get("claimCheckCode"))
    hosp = _norm_hosp(xml_payload.get("hospitalRecNo"))

    candidates: List[dict] = []
    if ccc and ccc in by_ccc:
        candidates = [c for c in by_ccc[ccc] if c["guid"] not in used_guids]
        if len(candidates) > 1 and hosp:
            narrowed = [c for c in candidates if _norm_hosp(c.get("hospitalRecNo")) == hosp]
            if narrowed:
                candidates = narrowed
    elif hosp and hosp in by_hosp:
        candidates = [c for c in by_hosp[hosp] if c["guid"] not in used_guids]

    if not candidates:
        return None
    return candidates[0]


def diff_xml_vs_cxf(xml_text: str, cxf_raw: bytes) -> Dict[str, Any]:
    xml_parsed = parse_claims_xml(xml_text)
    xml_claims = xml_parsed.get("claims") or []
    cxf_parsed = parse_cxf(cxf_raw)
    cxf_claims = cxf_parsed.get("claims") or []

    by_ccc, by_hosp = _index_cxf_claims(cxf_claims)
    used_guids: Set[str] = set()

    matched: List[dict] = []
    xml_only: List[dict] = []

    for row in xml_claims:
        payload = row.get("payload") or {}
        claim_id = _s(row.get("claim_id") or payload.get("claimID"))
        cxf_hit = _match_xml_to_cxf(payload, by_ccc, by_hosp, used_guids)
        xml_fp = _fingerprint_payload(payload)
        summary_row = {
            "claimID": claim_id,
            "claimCheckCode": _s(payload.get("claimCheckCode")),
            "memberNo": _s(payload.get("memberNo")),
            "hospitalRecNo": _s(payload.get("hospitalRecNo")),
            "client_name": " ".join(
                x for x in [_s(payload.get("surname")), _s(payload.get("otherNames"))] if x
            ).strip(),
            "typeOfService": _s(payload.get("typeOfService")),
            "visit_start_date": (payload.get("dateOfService") or [None])[0]
            if payload.get("dateOfService") else None,
        }
        if not cxf_hit:
            xml_only.append(summary_row)
            continue

        used_guids.add(cxf_hit["guid"])
        cxf_fp = _fingerprint_payload(cxf_hit["payload"])
        diffs = _field_diffs(xml_fp, cxf_fp)
        matched.append({
            **summary_row,
            "cxf_guid": cxf_hit["guid"],
            "cxf_status": cxf_hit.get("status"),
            "has_differences": len(diffs) > 0,
            "difference_count": len(diffs),
            "differences": diffs,
        })

    cxf_only: List[dict] = []
    for c in cxf_claims:
        if c["guid"] in used_guids:
            continue
        cxf_only.append({
            "guid": c["guid"],
            "claimCheckCode": c.get("claimCheckCode"),
            "memberNo": c.get("memberNo"),
            "hospitalRecNo": c.get("hospitalRecNo"),
            "client_name": " ".join(
                x for x in [_s(c.get("surname")), _s(c.get("otherNames"))] if x
            ).strip(),
            "typeOfService": c.get("typeOfService"),
            "status": c.get("status"),
            "visit_start_date": c.get("minDOSP") or c.get("maxDOSP"),
        })

    return {
        "summary": {
            "xml_total": len(xml_claims),
            "cxf_total": len(cxf_claims),
            "matched": len(matched),
            "matched_with_differences": sum(1 for m in matched if m["has_differences"]),
            "matched_identical": sum(1 for m in matched if not m["has_differences"]),
            "xml_only": len(xml_only),
            "cxf_only": len(cxf_only),
        },
        "matched": matched,
        "xml_only": xml_only,
        "cxf_only": cxf_only,
        "cxf_meta": cxf_parsed.get("meta") or {},
    }


def build_xml_subset_missing_from_cxf(xml_text: str, cxf_raw: bytes) -> Tuple[str, Dict[str, Any]]:
    """Return original XML claim elements for claims in XML but not matched in CFX."""
    diff = diff_xml_vs_cxf(xml_text, cxf_raw)
    missing_ids = {_s(r["claimID"]) for r in diff["xml_only"] if _s(r.get("claimID"))}
    xml_out = build_xml_for_claim_ids(xml_text, missing_ids)
    return xml_out, {
        "missing_count": len(missing_ids),
        "summary": diff["summary"],
    }


def build_xml_for_claim_ids(xml_text: str, claim_ids: Set[str]) -> str:
    """Subset original GHIMS XML claims by claimID (preserves original content)."""
    wanted = {_s(x) for x in claim_ids if _s(x)}
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise ValueError(f"Invalid XML: {e}") from e

    out_root = ET.Element("claims")
    for claim_el in root.findall(".//claim"):
        cid = (claim_el.findtext("claimID") or "").strip()
        if cid in wanted:
            out_root.append(claim_el)

    xml_body = ET.tostring(out_root, encoding="unicode")
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_body}'
