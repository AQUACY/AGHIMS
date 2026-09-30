"""Correct-errors must open the imported claim that already has type of attendance set."""
import unittest
from types import SimpleNamespace

from app.services.ghims_month_workbench import (
    SOURCE_GHIMS_LIVE,
    apply_main_attendance,
    choose_canonical_import_item,
)


def _item(item_id, batch_id, attendance, merged_into_id=None):
    return SimpleNamespace(
        id=item_id,
        batch_id=batch_id,
        merged_into_id=merged_into_id,
        payload={"typeOfAttendance": attendance},
    )


class CanonicalClaimLinkTests(unittest.TestCase):
    def test_fix_link_prefers_the_xml_claim_over_the_later_ghims_copy(self):
        xml_claim = _item(32144, 1, "EAE")
        live_copy = _item(42288, 2, "EMC")
        chosen = choose_canonical_import_item(
            [live_copy, xml_claim],
            {1: "xml", 2: SOURCE_GHIMS_LIVE},
        )
        self.assertIs(chosen, xml_claim)

    def test_officer_attendance_beats_an_older_raw_ghims_code(self):
        raw = _item(10, 1, "EME")
        edited = _item(20, 2, "CFU")
        chosen = choose_canonical_import_item(
            [raw, edited],
            {1: "xml", 2: SOURCE_GHIMS_LIVE},
        )
        self.assertIs(chosen, edited)

    def test_raw_copy_takes_the_main_attendance_and_an_officer_value_is_left_alone(self):
        payload = {"typeOfAttendance": "EMC"}
        self.assertTrue(apply_main_attendance(payload, "EAE"))
        self.assertEqual(payload["typeOfAttendance"], "EAE")
        self.assertFalse(apply_main_attendance(payload, "CFU"))
        self.assertEqual(payload["typeOfAttendance"], "EAE")
        self.assertFalse(apply_main_attendance({"typeOfAttendance": "EMC"}, "EME"))


if __name__ == "__main__":
    unittest.main()
