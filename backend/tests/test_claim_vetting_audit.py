"""Itemized claim vetting audit diffs."""
import unittest

from app.services.claim_vetting_audit import diff_claim_payloads, summarize_event


class ClaimVettingDiffTests(unittest.TestCase):
    def test_medicine_quantity_and_dose_changes(self):
        old = {
            "claimID": "CLA-1",
            "medicines": [
                {
                    "medicineCode": "M001",
                    "medicineName": "Paracetamol",
                    "dispensedQty": "13",
                    "serviceDate": "2026-09-01",
                    "prescription": {"dose": "25 ml", "frequency": "BD", "duration": "3", "unparsed": ""},
                }
            ],
        }
        new = {
            "claimID": "CLA-1",
            "medicines": [
                {
                    "medicineCode": "M001",
                    "medicineName": "Paracetamol",
                    "dispensedQty": "2",
                    "serviceDate": "2026-09-01",
                    "prescription": {"dose": "200 ml", "frequency": "BD", "duration": "3", "unparsed": ""},
                }
            ],
        }
        changes = diff_claim_payloads(old, new)
        by_field = {c["field"]: c for c in changes}
        self.assertEqual(by_field["dispensedQty"]["old"], "13")
        self.assertEqual(by_field["dispensedQty"]["new"], "2")
        self.assertEqual(by_field["dispensedQty"]["field_label"], "quantity")
        self.assertEqual(by_field["dose"]["old"], "25 ml")
        self.assertEqual(by_field["dose"]["new"], "200 ml")
        summary = summarize_event("updated", changes)
        self.assertIn("quantity", summary)
        self.assertIn("13", summary)
        self.assertIn("2", summary)
        self.assertIn("dose", summary)

    def test_added_and_removed_medicine(self):
        old = {"medicines": [{"medicineCode": "A", "dispensedQty": "1", "prescription": {}}]}
        new = {"medicines": [{"medicineCode": "B", "dispensedQty": "4", "prescription": {"dose": "1 tab"}}]}
        changes = diff_claim_payloads(old, new)
        kinds = {c["kind"] for c in changes}
        self.assertIn("removed", kinds)
        self.assertIn("added", kinds)

    def test_specialty_change(self):
        changes = diff_claim_payloads(
            {"specialtyAttended": "OPD"},
            {"specialtyAttended": "OPDC"},
        )
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["field"], "specialtyAttended")
        self.assertEqual(changes[0]["old"], "OPD")
        self.assertEqual(changes[0]["new"], "OPDC")

    def test_no_change_when_numeric_equivalent(self):
        old = {"medicines": [{"medicineCode": "X", "dispensedQty": "2.0", "prescription": {}}]}
        new = {"medicines": [{"medicineCode": "X", "dispensedQty": "2", "prescription": {}}]}
        self.assertEqual(diff_claim_payloads(old, new), [])


if __name__ == "__main__":
    unittest.main()
