"""Billable-line rules for live GHIMS co-payment sync."""
import unittest

from app.services.ghims_companion_sync import (
    _new_item_id,
    attach_issued_quantities,
    dispensed_quantity,
    is_cash_visit,
    select_billable_lines,
)


class BillableLineTests(unittest.TestCase):
    def test_new_item_id_is_nested_under_added(self):
        self.assertEqual(_new_item_id({"added": {"id": 42}}), 42)
        self.assertIsNone(_new_item_id({"match_type": "product"}))
        self.assertIsNone(_new_item_id(None))

    def test_cash_sponsors_are_excluded(self):
        self.assertTrue(is_cash_visit("SELF", "I100"))
        self.assertTrue(is_cash_visit("SELFN", "I300"))
        self.assertTrue(is_cash_visit("I101", "CPP"))
        self.assertTrue(is_cash_visit("", ""))
        self.assertFalse(is_cash_visit("I101", "I101"))
        self.assertFalse(is_cash_visit("GHC", "I006"))

    def test_requested_fbc_is_not_billed_until_ready(self):
        lines = select_billable_lines(
            investigations=[
                {
                    "LabRequestID": "LE-1",
                    "LabTestID": "FBC",
                    "RequestStatusID": "RRD001",
                    "LabTestName": "Full Blood Count FBC (Automation)",
                    "Qty": 1,
                }
            ],
            labs=[
                {
                    "LabByDoctorID": "ORDER-1",
                    "LabTestID": "FBC",
                    "LabByDoctorStatusID": "L001",
                    "LabTestName": "Full Blood Count FBC (Automation)",
                    "Qty": 1,
                }
            ],
            prescriptions=[],
        )
        self.assertEqual(lines, [])

    def test_ready_fbc_bills_once_even_if_doctor_order_is_also_validated(self):
        lines = select_billable_lines(
            investigations=[
                {
                    "LabRequestID": "LE-1",
                    "LabTestID": "FBC",
                    "RequestStatusID": "RRD002",
                    "LabTestName": "Full Blood Count FBC (Automation)",
                    "Qty": 1,
                }
            ],
            labs=[
                {
                    "LabByDoctorID": "ORDER-VALID",
                    "LabTestID": "FBC",
                    "LabByDoctorStatusID": "L004",
                    "LabTestName": "Full Blood Count FBC (Automation)",
                    "Qty": 1,
                },
                {
                    "LabByDoctorID": "ORDER-PENDING",
                    "LabTestID": "FBC",
                    "LabByDoctorStatusID": "L001",
                    "LabTestName": "Full Blood Count FBC (Automation)",
                    "Qty": 1,
                },
                {
                    "LabByDoctorID": "RFT",
                    "LabTestID": "RFT",
                    "LabByDoctorStatusID": "L001",
                    "LabTestName": "Renal Function Test",
                    "Qty": 1,
                },
            ],
            prescriptions=[
                {
                    "PrescriptionID": "RX-NEW",
                    "PrescriptionStatusID": "P001",
                    "DrugName": "Paracetamol",
                    "Qty": 10,
                },
                {
                    "PrescriptionID": "RX-DONE",
                    "PrescriptionStatusID": "P002",
                    "DrugName": "Amoxicillin",
                    "Qty": 21,
                },
            ],
        )
        self.assertEqual(
            [(row["source_type"], row["description"], row["quantity"]) for row in lines],
            [
                ("investigation", "Full Blood Count FBC (Automation)", 1.0),
                ("prescription", "Amoxicillin", 21.0),
            ],
        )

    def test_received_lab_without_investigation_is_billable(self):
        lines = select_billable_lines(
            investigations=[],
            labs=[
                {
                    "LabByDoctorID": "US-1",
                    "LabTestID": "US",
                    "LabByDoctorStatusID": "L002",
                    "LabTestName": "Ultrasound",
                    "Qty": 1,
                }
            ],
            prescriptions=[],
        )
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["source_type"], "lab_by_doctor")
        self.assertEqual(lines[0]["description"], "Ultrasound")


class RefreshSkipTests(unittest.TestCase):
    def test_a_visit_synced_just_now_is_not_read_again(self):
        from types import SimpleNamespace
        from datetime import timedelta

        from app.core.datetime_utils import utcnow
        from app.services.ghims_companion_sync import (
            SOURCE_LIVE,
            _billable_lines_match_items,
            visit_needs_ghims_refresh,
        )

        fresh = SimpleNamespace(source=SOURCE_LIVE, ghims_synced_at=utcnow())
        stale = SimpleNamespace(source=SOURCE_LIVE, ghims_synced_at=utcnow() - timedelta(minutes=5))
        manual = SimpleNamespace(source="manual", ghims_synced_at=None)
        self.assertFalse(visit_needs_ghims_refresh(fresh))
        self.assertTrue(visit_needs_ghims_refresh(stale))
        self.assertFalse(visit_needs_ghims_refresh(manual))

        item = SimpleNamespace(
            ghims_source_type="lab_by_doctor",
            ghims_source_id="US-1",
            quantity=1,
            unit_price=5,
            cancelled=False,
            receipt_number="",
            paid_at=None,
            admission_deposit_applied=None,
            payment_method=None,
            admission_deposit_line_receipt=None,
        )
        lines = [{"source_type": "lab_by_doctor", "source_id": "US-1", "quantity": 1}]
        self.assertTrue(_billable_lines_match_items(lines, [item]))
        self.assertFalse(_billable_lines_match_items([], [item]))


class DrugNameMatchTests(unittest.TestCase):
    def test_injection_matches_same_strength_not_the_tablet(self):
        from app.api.companion_visits import _drug_product_fits, _generics_close

        self.assertTrue(
            _drug_product_fits(
                "Furosemide Injection 10mg/ml",
                "FUROSEMIDE",
                "Furosemide  (FUROSEIN1 | Furosemide )",
                "Injection",
                "10 mg/mL in 2 mL",
            )
        )
        self.assertFalse(
            _drug_product_fits(
                "Furosemide Injection 10mg/ml",
                "FUROSEMIDE",
                "Furosemide Tablet 40mg",
                "Tablet",
                "40 mg",
            )
        )
        self.assertTrue(_generics_close("ceftriaxone", "ceftriazone"))
        self.assertFalse(_generics_close("omeprazole", "esomeprazole"))
        self.assertTrue(
            _drug_product_fits(
                "Ceftriaxone Injection 1g",
                "CEFTRIAXONE",
                "Ceftriazone (1 g) (CEFTRIIN3 | Ceftriazone)",
                "Injection",
                "1g",
            )
        )
        self.assertFalse(
            _drug_product_fits(
                "Ceftriaxone Injection 1g",
                "CEFTRIAXONE",
                "Ceftriazone  (500 mg) (CEFTRIIN2 | Ceftriazone )",
                "Injection",
                "500 mg",
            )
        )


class DispensedQuantityTests(unittest.TestCase):
    def test_issued_quantity_replaces_a_prescription_qty_of_one(self):
        lines = select_billable_lines(
            investigations=[],
            labs=[],
            prescriptions=[
                {
                    "PrescriptionID": "RX-1",
                    "PrescriptionStatusID": "P002",
                    "DrugName": "Furosemide Injection 10mg/ml",
                    "Qty": 1,
                    "IssuedQty": 30,
                }
            ],
        )
        self.assertEqual(lines[0]["quantity"], 30.0)

    def test_sale_lines_are_copied_onto_the_matching_prescription(self):
        rows = [
            {
                "VisitationID": "VE-1",
                "PrescriptionID": "RX-A",
                "DrugID": "D1",
                "Qty": 1,
            },
            {
                "VisitationID": "VE-1",
                "PrescriptionID": "RX-B",
                "DrugID": "D1",
                "Qty": 1,
            },
        ]
        attach_issued_quantities(
            rows,
            [
                {"VisitationID": "VE-1", "PrescriptionID": "RX-A", "DrugID": "D1", "IssuedQty": 10},
                {"VisitationID": "VE-1", "PrescriptionID": "RX-B", "DrugID": "D1", "IssuedQty": 5},
            ],
        )
        self.assertEqual(rows[0]["IssuedQty"], 10)
        self.assertEqual(rows[1]["IssuedQty"], 5)

    def test_drug_sale_still_applies_when_the_prescription_id_does_not_match(self):
        rows = [
            {"VisitationID": "VE-1", "PrescriptionID": "RX-A", "DrugID": "D1", "Qty": 1},
        ]
        attach_issued_quantities(
            rows,
            [{"VisitationID": "VE-1", "PrescriptionID": "SALE-9", "DrugID": "D1", "IssuedQty": 20}],
        )
        self.assertEqual(rows[0]["IssuedQty"], 20)

    def test_requested_qty_wins_when_issued_stayed_at_one(self):
        lines = select_billable_lines(
            investigations=[],
            labs=[],
            prescriptions=[
                {
                    "PrescriptionID": "RX-1",
                    "PrescriptionStatusID": "P002",
                    "DrugName": "Prednisolone Tablet 5mg",
                    "Qty": 1,
                    "IssuedQty": 1,
                    "RequestedQty": 30,
                }
            ],
        )
        self.assertEqual(lines[0]["quantity"], 30.0)

    def test_directions_estimate_tablets_when_sale_qty_is_missing(self):
        lines = select_billable_lines(
            investigations=[],
            labs=[],
            prescriptions=[
                {
                    "PrescriptionID": "RX-1",
                    "PrescriptionStatusID": "P002",
                    "DrugName": "Prednisolone Tablet 5mg",
                    "Qty": 1,
                    "PrescribeInfo1": "1||Oral||TDS||5",
                }
            ],
        )
        self.assertEqual(lines[0]["quantity"], 15.0)

    def test_one_drug_sale_fills_the_only_prescription_when_sale_has_no_prescription_id(self):
        rows = [
            {"VisitationID": "VE-1", "PrescriptionID": "RX-A", "DrugID": "D1", "Qty": 1},
        ]
        attach_issued_quantities(
            rows,
            [{"VisitationID": "VE-1", "DrugID": "D1", "IssuedQty": 14}],
        )
        self.assertEqual(rows[0]["IssuedQty"], 14)

    def test_dispense_cost_is_not_treated_as_quantity(self):
        # GHIMS pharmacy screen: Qty 6, unit 5, initial/final cost 30.
        qty = dispensed_quantity(
            {
                "DrugName": "Magnesium Sulphate Injection 50%",
                "Qty": 6,
                "DispenseAmt1": 30,
                "UnitCost": 5,
                "InitAmt": 30,
                "FinalAmt": 30,
            }
        )
        self.assertEqual(qty, 6.0)

    def test_sale_qty_wins_over_dispense_amount_money_total(self):
        lines = select_billable_lines(
            investigations=[],
            labs=[],
            prescriptions=[
                {
                    "PrescriptionID": "RX-MG",
                    "PrescriptionStatusID": "P002",
                    "DrugID": "MAG",
                    "DrugName": "Magnesium Sulphate Injection 50%",
                    "Qty": 1,
                }
            ],
            sales=[
                {
                    "PrescriptionID": "RX-MG",
                    "DrugSaleID": "DS-1",
                    "DrugID": "MAG",
                    "DrugName": "Magnesium Sulphate Injection 50%",
                    "Qty": 6,
                    "DispenseAmt1": 30,
                    "UnitCost": 5.0,
                    "InitAmt": 30.0,
                    "FinalAmt": 30.0,
                }
            ],
        )
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["quantity"], 6.0)

    def test_sales_line_is_billed_even_when_prescription_is_still_new(self):
        lines = select_billable_lines(
            investigations=[],
            labs=[],
            prescriptions=[
                {
                    "PrescriptionID": "RX-P",
                    "PrescriptionStatusID": "P001",
                    "DrugID": "PARA",
                    "DrugName": "Paracetamol Tablet 500mg",
                    "Qty": 1,
                }
            ],
            sales=[
                {
                    "PrescriptionID": "RX-P",
                    "DrugSaleID": "DS-2",
                    "DrugID": "PARA",
                    "DrugName": "Paracetamol Tablet 500mg",
                    "Qty": 20,
                    "DispenseAmt1": 4.0,
                    "UnitCost": 0.2,
                    "InitAmt": 4.0,
                    "FinalAmt": 4.0,
                }
            ],
        )
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["quantity"], 20.0)


if __name__ == "__main__":
    unittest.main()
