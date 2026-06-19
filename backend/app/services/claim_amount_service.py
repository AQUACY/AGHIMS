"""
Claim revenue amounts from price list (claim_amount preferred).
"""
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.procedure_price import ProcedurePrice
from app.models.product_price import ProductPrice
from app.models.surgery_price import SurgeryPrice
from app.models.unmapped_drg_price import UnmappedDRGPrice


def _amount_from_price_row(row) -> float:
    if getattr(row, "claim_amount", None) is not None:
        return float(row.claim_amount)
    if getattr(row, "nhia_app", None) is not None:
        return float(row.nhia_app)
    return float(row.base_rate) if getattr(row, "base_rate", None) else 0.0


class PriceAmountCache:
    """In-memory code -> claim amount map built from a few bulk DB reads."""

    def __init__(self) -> None:
        self._by_code: Dict[str, float] = {}

    @classmethod
    def build(cls, db: Session) -> "PriceAmountCache":
        cache = cls()

        def set_amount(code: Optional[str], amount: float, prefer: bool = False) -> None:
            if not code:
                return
            key = str(code).strip()
            if not key:
                return
            if prefer or key not in cache._by_code:
                cache._by_code[key] = amount

        for model in (ProcedurePrice, SurgeryPrice, UnmappedDRGPrice):
            rows = db.query(model).filter(model.is_active == True).all()
            for row in rows:
                code = getattr(row, "g_drg_code", None)
                if not code:
                    continue
                has_claim = getattr(row, "claim_amount", None) is not None
                set_amount(code, _amount_from_price_row(row), prefer=has_claim)

        product_rows = db.query(ProductPrice).filter(ProductPrice.is_active == True).all()
        for row in product_rows:
            amount = _amount_from_price_row(row)
            has_claim = getattr(row, "claim_amount", None) is not None
            for code_attr in ("medication_code", "product_id"):
                code = getattr(row, code_attr, None)
                set_amount(code, amount, prefer=has_claim)

        return cache

    def get(self, code: str) -> float:
        if not code:
            return 0.0
        return self._by_code.get(str(code).strip(), 0.0)


def get_claim_amount_from_price_list(
    db: Session,
    item_code: str,
    is_insured: bool = True,
    cache: Optional[Dict[str, float]] = None,
    price_cache: Optional[PriceAmountCache] = None,
) -> float:
    """NHIA claim amount for a code: claim_amount, then nhia_app, then base_rate."""
    if not is_insured or not item_code:
        return 0.0

    code = str(item_code).strip()
    if not code:
        return 0.0

    if price_cache is not None:
        return price_cache.get(code)

    if cache is not None and code in cache:
        return cache[code]

    tables = [
        db.query(ProcedurePrice).filter(
            ProcedurePrice.g_drg_code == code, ProcedurePrice.is_active == True
        ),
        db.query(SurgeryPrice).filter(
            SurgeryPrice.g_drg_code == code, SurgeryPrice.is_active == True
        ),
        db.query(UnmappedDRGPrice).filter(
            UnmappedDRGPrice.g_drg_code == code, UnmappedDRGPrice.is_active == True
        ),
    ]

    candidates = []
    for query in tables:
        item = query.first()
        if item:
            candidates.append(item)

    if candidates:
        for item in candidates:
            if getattr(item, "claim_amount", None) is not None:
                amount = float(item.claim_amount)
                if cache is not None:
                    cache[code] = amount
                return amount
        item = candidates[0]
        if getattr(item, "nhia_app", None) is not None:
            amount = float(item.nhia_app)
        else:
            amount = float(item.base_rate) if item.base_rate else 0.0
        if cache is not None:
            cache[code] = amount
        return amount

    product = (
        db.query(ProductPrice)
        .filter(
            ((ProductPrice.medication_code == code) | (ProductPrice.product_id == code)),
            ProductPrice.is_active == True,
        )
        .first()
    )

    if product:
        if getattr(product, "claim_amount", None) is not None:
            amount = float(product.claim_amount)
        elif getattr(product, "nhia_app", None) is not None:
            amount = float(product.nhia_app)
        else:
            amount = float(product.base_rate) if product.base_rate else 0.0
        if cache is not None:
            cache[code] = amount
        return amount

    if cache is not None:
        cache[code] = 0.0
    return 0.0


def _line_code(row: Dict[str, Any], *keys: str) -> str:
    for key in keys:
        val = row.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return ""


def compute_claim_summary_dict(
    db: Session,
    type_of_service: str,
    procedures: Optional[List[Dict[str, Any]]] = None,
    investigations: Optional[List[Dict[str, Any]]] = None,
    prescriptions: Optional[List[Dict[str, Any]]] = None,
    principal_gdrg: Optional[str] = None,
    encounter_procedure_gdrg: Optional[str] = None,
    price_cache: Optional[PriceAmountCache] = None,
) -> Dict[str, float]:
    """Build Client Claim Summary amounts from claim line items."""
    cache: Dict[str, float] = {}
    tos = (type_of_service or "OPD").strip().upper()

    def lookup(code: str) -> float:
        return get_claim_amount_from_price_list(
            db, code, cache=cache, price_cache=price_cache
        )

    procedure_codes: List[str] = []
    for proc in procedures or []:
        code = _line_code(proc, "gdrg", "gdrgCode", "gdrg_code")
        if code:
            procedure_codes.append(code)

    if not procedure_codes:
        for fallback in (principal_gdrg, encounter_procedure_gdrg):
            if fallback and str(fallback).strip():
                procedure_codes.append(str(fallback).strip())
                break

    procedure_total = sum(lookup(code) for code in procedure_codes)

    inpatient_amount = procedure_total if tos == "IPD" else 0.0
    outpatient_amount = procedure_total if tos == "OPD" else 0.0

    investigations_amount = 0.0
    for inv in investigations or []:
        code = _line_code(inv, "gdrg", "gdrgCode", "gdrg_code")
        if code:
            investigations_amount += lookup(code)

    pharmacy_amount = 0.0
    for presc in prescriptions or []:
        code = _line_code(
            presc, "code", "medicineCode", "medicine_code", "medicineCode"
        )
        qty_raw = presc.get("quantity")
        if qty_raw is None:
            qty_raw = presc.get("dispensedQty") or presc.get("dispensed_qty")
        try:
            qty = float(qty_raw or 0)
        except (TypeError, ValueError):
            qty = 0.0

        if code and qty > 0:
            pharmacy_amount += lookup(code) * qty
        elif presc.get("total_cost") is not None:
            try:
                pharmacy_amount += float(presc["total_cost"])
            except (TypeError, ValueError):
                pass
        elif presc.get("price") is not None and qty > 0:
            try:
                pharmacy_amount += float(presc["price"]) * qty
            except (TypeError, ValueError):
                pass

    total_amount = inpatient_amount + outpatient_amount + investigations_amount + pharmacy_amount

    return {
        "inpatient_amount": inpatient_amount,
        "outpatient_amount": outpatient_amount,
        "investigations_amount": investigations_amount,
        "pharmacy_amount": pharmacy_amount,
        "total_amount": total_amount,
    }


def compute_claim_summary_from_ghims_payload(
    db: Session,
    payload: Dict[str, Any],
    price_cache: Optional[PriceAmountCache] = None,
) -> Dict[str, float]:
    """Claim summary from imported GHIMS XML payload."""
    if not payload:
        return compute_claim_summary_dict(db, "OPD", price_cache=price_cache)

    medicines = []
    for med in payload.get("medicines") or []:
        if not isinstance(med, dict):
            continue
        try:
            qty = float(med.get("dispensedQty") or 0)
        except (TypeError, ValueError):
            qty = 0.0
        medicines.append(
            {
                "medicineCode": med.get("medicineCode"),
                "dispensedQty": qty,
            }
        )

    return compute_claim_summary_dict(
        db,
        type_of_service=str(payload.get("typeOfService") or payload.get("type_of_service") or "OPD"),
        procedures=payload.get("procedures") or [],
        investigations=payload.get("investigations") or [],
        prescriptions=medicines,
        principal_gdrg=str(payload.get("principalGDRG") or "").strip() or None,
        price_cache=price_cache,
    )


def compute_ghims_batch_claim_totals(
    db: Session,
    items: List[Any],
    price_cache: Optional[PriceAmountCache] = None,
) -> Dict[str, Any]:
    """Compute per-item and batch revenue totals using one shared price cache."""
    cache = price_cache or PriceAmountCache.build(db)
    totals: Dict[int, float] = {}
    batch_revenue = 0.0
    for item in items:
        payload = getattr(item, "payload", None) or {}
        summary = compute_claim_summary_from_ghims_payload(db, payload, price_cache=cache)
        amount = round(float(summary.get("total_amount") or 0.0), 2)
        item_id = int(getattr(item, "id"))
        totals[item_id] = amount
        batch_revenue += amount
    return {
        "totals": totals,
        "total_revenue": round(batch_revenue, 2),
    }


def compute_encounter_claim_summary(
    db: Session,
    encounter,
    claim=None,
    ward_admission=None,
) -> Dict[str, float]:
    """Estimate claim summary for an encounter (claims list / revenue totals)."""
    from app.models.claim_procedure import ClaimProcedure
    from app.models.claim_investigation import ClaimInvestigation
    from app.models.claim_prescription import ClaimPrescription
    from app.models.inpatient_surgery import InpatientSurgery

    type_of_service = "OPD"
    principal_gdrg = None
    if claim:
        type_of_service = claim.type_of_service or "OPD"
        principal_gdrg = claim.principal_gdrg
    elif ward_admission:
        type_of_service = "IPD"

    procedures: List[Dict[str, Any]] = []
    investigations: List[Dict[str, Any]] = []
    prescriptions: List[Dict[str, Any]] = []

    if claim:
        claim_procs = (
            db.query(ClaimProcedure)
            .filter(ClaimProcedure.claim_id == claim.id)
            .order_by(ClaimProcedure.display_order)
            .all()
        )
        if claim_procs:
            for proc in claim_procs:
                if proc.gdrg_code:
                    procedures.append({"gdrg": proc.gdrg_code})
        else:
            if type_of_service == "IPD" and ward_admission:
                surgeries = (
                    db.query(InpatientSurgery)
                    .filter(
                        InpatientSurgery.ward_admission_id == ward_admission.id,
                        InpatientSurgery.is_completed == True,
                    )
                    .all()
                )
                for surgery in surgeries:
                    if surgery.g_drg_code:
                        procedures.append({"gdrg": surgery.g_drg_code})
            else:
                surgeries = (
                    db.query(InpatientSurgery)
                    .filter(
                        InpatientSurgery.encounter_id == encounter.id,
                        InpatientSurgery.is_completed == True,
                    )
                    .all()
                )
                for surgery in surgeries:
                    if surgery.g_drg_code:
                        procedures.append({"gdrg": surgery.g_drg_code})

        claim_invs = (
            db.query(ClaimInvestigation)
            .filter(ClaimInvestigation.claim_id == claim.id)
            .order_by(ClaimInvestigation.display_order)
            .all()
        )
        if claim_invs:
            for inv in claim_invs:
                if inv.gdrg_code:
                    investigations.append({"gdrg": inv.gdrg_code})
        else:
            for inv in encounter.investigations:
                if inv.status != "cancelled" and inv.gdrg_code:
                    investigations.append({"gdrg": inv.gdrg_code})

        claim_prescs = (
            db.query(ClaimPrescription)
            .filter(ClaimPrescription.claim_id == claim.id)
            .order_by(ClaimPrescription.display_order)
            .all()
        )
        if claim_prescs:
            for presc in claim_prescs:
                if presc.medicine_code:
                    prescriptions.append(
                        {
                            "code": presc.medicine_code,
                            "quantity": presc.quantity,
                            "total_cost": presc.total_cost,
                            "price": presc.price,
                        }
                    )
        else:
            for presc in encounter.prescriptions:
                if presc.dispensed_by and presc.medicine_code:
                    prescriptions.append(
                        {
                            "code": presc.medicine_code,
                            "quantity": presc.quantity,
                        }
                    )
    else:
        for inv in encounter.investigations:
            if inv.status != "cancelled" and inv.gdrg_code:
                investigations.append({"gdrg": inv.gdrg_code})
        for presc in encounter.prescriptions:
            if presc.dispensed_by and presc.medicine_code:
                prescriptions.append(
                    {
                        "code": presc.medicine_code,
                        "quantity": presc.quantity,
                    }
                )
        if ward_admission:
            surgeries = (
                db.query(InpatientSurgery)
                .filter(
                    InpatientSurgery.ward_admission_id == ward_admission.id,
                    InpatientSurgery.is_completed == True,
                )
                .all()
            )
            for surgery in surgeries:
                if surgery.g_drg_code:
                    procedures.append({"gdrg": surgery.g_drg_code})

    return compute_claim_summary_dict(
        db,
        type_of_service=type_of_service,
        procedures=procedures,
        investigations=investigations,
        prescriptions=prescriptions,
        principal_gdrg=principal_gdrg,
        encounter_procedure_gdrg=encounter.procedure_g_drg_code,
    )
