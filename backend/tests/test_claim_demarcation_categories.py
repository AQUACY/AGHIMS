"""Doctor and pharmacy claim demarcation must not share the same owner field."""
import unittest
from types import SimpleNamespace

from app.api.claims import _apply_ownership, normalize_ownership_category


def _item():
    return SimpleNamespace(
        assigned_to_id=None,
        assigned_at=None,
        assigned_by_id=None,
        assignment_note=None,
        pharmacy_assigned_to_id=None,
        pharmacy_assigned_at=None,
        pharmacy_assigned_by_id=None,
        pharmacy_assignment_note=None,
    )


class OwnershipCategoryTests(unittest.TestCase):
    def test_aliases_normalize(self):
        self.assertEqual(normalize_ownership_category("doctors"), "doctor")
        self.assertEqual(normalize_ownership_category("pharmacists"), "pharmacy")
        self.assertEqual(normalize_ownership_category(None), "doctor")

    def test_pharmacy_assign_does_not_clear_doctor(self):
        item = _item()
        _apply_ownership(item, 11, "OPD", by_user_id=1, category="doctor")
        _apply_ownership(item, 22, "Pharmacy share", by_user_id=1, category="pharmacy")
        self.assertEqual(item.assigned_to_id, 11)
        self.assertEqual(item.assignment_note, "OPD")
        self.assertEqual(item.pharmacy_assigned_to_id, 22)
        self.assertEqual(item.pharmacy_assignment_note, "Pharmacy share")

    def test_replace_pharmacy_plan_leaves_doctors(self):
        item = _item()
        _apply_ownership(item, 11, "OPD", by_user_id=1, category="doctor")
        _apply_ownership(item, 22, "Rx", by_user_id=1, category="pharmacy")
        _apply_ownership(item, None, None, by_user_id=1, category="pharmacy")
        self.assertEqual(item.assigned_to_id, 11)
        self.assertIsNone(item.pharmacy_assigned_to_id)
        self.assertIsNone(item.pharmacy_assignment_note)

    def test_replace_doctor_plan_leaves_pharmacy(self):
        item = _item()
        _apply_ownership(item, 11, "OPD", by_user_id=1, category="doctor")
        _apply_ownership(item, 22, "Rx", by_user_id=1, category="pharmacy")
        _apply_ownership(item, None, None, by_user_id=1, category="doctor")
        self.assertIsNone(item.assigned_to_id)
        self.assertEqual(item.pharmacy_assigned_to_id, 22)


if __name__ == "__main__":
    unittest.main()
