"""
Parse GHIMS-exported claims XML to editable dictionaries and rebuild XML.
"""
from typing import Dict, Any, List
import re
import xml.etree.ElementTree as ET


def _text(el: ET.Element, tag: str) -> str:
    val = el.findtext(tag)
    return (val or "").strip()


def _parse_claim_element(claim_el: ET.Element) -> Dict[str, Any]:
    diagnoses = []
    for d in claim_el.findall("diagnosis"):
        diagnoses.append({
            "gdrgCode": _text(d, "gdrgCode"),
            "icd10": _text(d, "icd10"),
            "diagnosis": _text(d, "diagnosis"),
        })

    investigations = []
    for inv in claim_el.findall("investigation"):
        investigations.append({
            "serviceDate": _text(inv, "serviceDate"),
            "gdrgCode": _text(inv, "gdrgCode"),
        })

    medicines = []
    for med in claim_el.findall("medicine"):
        prescription_el = med.find("prescription")
        medicines.append({
            "medicineCode": _text(med, "medicineCode"),
            "dispensedQty": _text(med, "dispensedQty"),
            "serviceDate": _text(med, "serviceDate"),
            "prescription": {
                "dose": _text(prescription_el, "dose") if prescription_el is not None else "",
                "frequency": _text(prescription_el, "frequency") if prescription_el is not None else "",
                "duration": _text(prescription_el, "duration") if prescription_el is not None else "",
                "unparsed": _text(prescription_el, "unparsed") if prescription_el is not None else "",
            },
        })

    procedures = []
    for p in claim_el.findall("procedure"):
        procedures.append({
            "serviceDate": _text(p, "serviceDate"),
            "gdrgCode": _text(p, "gdrgCode"),
            "description": _text(p, "description"),
            "icd10": _text(p, "icd10"),
            "diagnosis": _text(p, "diagnosis"),
        })

    service_dates = [d.text.strip() for d in claim_el.findall("dateOfService") if d.text and d.text.strip()]

    payload = {
        "claimID": _text(claim_el, "claimID"),
        "claimCheckCode": _text(claim_el, "claimCheckCode"),
        "preAuthorizationCodes": _text(claim_el, "preAuthorizationCodes"),
        "physicianID": _text(claim_el, "physicianID"),
        "memberNo": _text(claim_el, "memberNo"),
        "cardSerialNo": _text(claim_el, "cardSerialNo"),
        "surname": _text(claim_el, "surname"),
        "otherNames": _text(claim_el, "otherNames"),
        "dateOfBirth": _text(claim_el, "dateOfBirth"),
        "gender": _text(claim_el, "gender"),
        "hospitalRecNo": _text(claim_el, "hospitalRecNo"),
        "isDependant": _text(claim_el, "isDependant"),
        "typeOfService": _text(claim_el, "typeOfService"),
        "isUnbundled": _text(claim_el, "isUnbundled"),
        "includesPharmacy": _text(claim_el, "includesPharmacy"),
        "typeOfAttendance": _text(claim_el, "typeOfAttendance"),
        "serviceOutcome": _text(claim_el, "serviceOutcome"),
        "specialtyAttended": _text(claim_el, "specialtyAttended"),
        "principalGDRG": _text(claim_el, "principalGDRG"),
        "dateOfService": service_dates,
        "diagnoses": diagnoses,
        "investigations": investigations,
        "medicines": medicines,
        "procedures": procedures,
    }
    return payload


def parse_claims_xml(xml_content: str) -> Dict[str, Any]:
    """
    Parse claims XML and return extracted claim rows.
    Expected shape:
      <claims>
        <claim>
          <claimID>CLA-12345</claimID>
        </claim>
      </claims>
    """
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        return {"claims": []}

    claims: List[Dict[str, Any]] = []
    idx = 0
    for claim_el in root.findall(".//claim"):
        claim_id_text = claim_el.findtext("claimID")
        if not claim_id_text:
            continue
        claim_id = str(claim_id_text).strip()
        if not claim_id:
            continue
        idx += 1
        claims.append({
            "claim_id": claim_id,
            "row_index": idx,
            "payload": _parse_claim_element(claim_el),
        })

    return {"claims": claims}


_FREQUENCY_TIMES_PER_DAY = {
    "BDS": 2,
    "BID": 2,
    "TID": 3,
    "TDS": 3,
    "QDS": 4,
    "QID": 4,
}


def _normalize_frequency_for_export(frequency: str) -> str:
    raw = str(frequency or "").strip()
    if not raw:
        return ""

    # Strip trailing shorthand in brackets, e.g. "8 HOURLY (TDS)" -> "8 HOURLY"
    stripped = re.sub(r"\s*\((?:TDS|TID|BDS|BID|QID|QDS)\)\s*$", "", raw, flags=re.IGNORECASE).strip()
    shorthand = stripped.upper()
    if shorthand in _FREQUENCY_TIMES_PER_DAY:
        return f"{_FREQUENCY_TIMES_PER_DAY[shorthand]} DAILY"
    return stripped.upper()


def _normalize_duration_for_export(duration: str) -> str:
    raw = str(duration or "").strip()
    if not raw:
        return ""
    compact = re.sub(r"\s+", " ", raw)
    num_only = re.match(r"^(\d+(?:\.\d+)?)$", compact)
    if num_only:
        return f"{num_only.group(1)} days"
    day_based = re.match(r"^(\d+(?:\.\d+)?)\s*day(?:s)?$", compact, flags=re.IGNORECASE)
    if day_based:
        return f"{day_based.group(1)} days"
    return compact


def build_claims_xml_from_payloads(payloads: List[Dict[str, Any]]) -> str:
    root = ET.Element("claims")
    for payload in payloads:
        claim_el = ET.SubElement(root, "claim")
        simple_tags = [
            "claimID", "claimCheckCode", "preAuthorizationCodes", "physicianID", "memberNo",
            "cardSerialNo", "surname", "otherNames", "dateOfBirth", "gender", "hospitalRecNo",
            "isDependant", "typeOfService", "isUnbundled", "includesPharmacy", "typeOfAttendance",
            "serviceOutcome", "specialtyAttended", "principalGDRG",
        ]
        for tag in simple_tags:
            ET.SubElement(claim_el, tag).text = str(payload.get(tag, "") or "")

        for dt in payload.get("dateOfService", [])[:4]:
            ET.SubElement(claim_el, "dateOfService").text = str(dt or "")

        for diag in payload.get("diagnoses", []):
            d = ET.SubElement(claim_el, "diagnosis")
            ET.SubElement(d, "gdrgCode").text = str(diag.get("gdrgCode", "") or "")
            ET.SubElement(d, "icd10").text = str(diag.get("icd10", "") or "")
            ET.SubElement(d, "diagnosis").text = str(diag.get("diagnosis", "") or "")

        for inv in payload.get("investigations", []):
            i = ET.SubElement(claim_el, "investigation")
            ET.SubElement(i, "serviceDate").text = str(inv.get("serviceDate", "") or "")
            ET.SubElement(i, "gdrgCode").text = str(inv.get("gdrgCode", "") or "")

        for med in payload.get("medicines", []):
            m = ET.SubElement(claim_el, "medicine")
            ET.SubElement(m, "medicineCode").text = str(med.get("medicineCode", "") or "")
            ET.SubElement(m, "dispensedQty").text = str(med.get("dispensedQty", "") or "")
            ET.SubElement(m, "serviceDate").text = str(med.get("serviceDate", "") or "")
            p = ET.SubElement(m, "prescription")
            pres = med.get("prescription", {}) or {}
            ET.SubElement(p, "unparsed").text = str(pres.get("unparsed", "") or "")

        for proc in payload.get("procedures", []):
            pr = ET.SubElement(claim_el, "procedure")
            ET.SubElement(pr, "serviceDate").text = str(proc.get("serviceDate", "") or "")
            ET.SubElement(pr, "gdrgCode").text = str(proc.get("gdrgCode", "") or "")
            ET.SubElement(pr, "description").text = str(proc.get("description", "") or "")
            ET.SubElement(pr, "icd10").text = str(proc.get("icd10", "") or "")
            ET.SubElement(pr, "diagnosis").text = str(proc.get("diagnosis", "") or "")

    xml_body = ET.tostring(root, encoding="unicode")
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_body}'
