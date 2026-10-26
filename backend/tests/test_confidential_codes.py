"""Confidential visit codes hide identity at service points and still reveal it for claims."""
import unittest
from types import SimpleNamespace

from app.services.confidential import (
    CLAIM_REVEAL_ROLES,
    REGISTER_ROLES,
    format_code,
    redact_service_payload,
    user_has_role,
)


class FormatCodeTests(unittest.TestCase):
    def test_scrn_padding(self):
        self.assertEqual(format_code("scrn", 1, 4), "SCRN0001")
        self.assertEqual(format_code("SCRN", 12, 3), "SCRN012")

    def test_rejects_blank_prefix(self):
        with self.assertRaises(ValueError):
            format_code("---", 1, 4)


class RedactionTests(unittest.TestCase):
    def _payload(self):
        return {
            "patient_name": "Ama Mensah",
            "patient_card_number": "GH-1",
            "patient_insurance_id": "NHIS-9",
            "patient_age": 34,
            "ccc_number": "12345",
            "department": "General",
        }

    def test_service_point_sees_the_code_only(self):
        shown = redact_service_payload(self._payload(), confidential=True, code="SCRN0001", reveal=False)
        self.assertEqual(shown["patient_name"], "SCRN0001")
        self.assertIsNone(shown["patient_card_number"])
        self.assertIsNone(shown["patient_insurance_id"])
        self.assertIsNone(shown["ccc_number"])
        self.assertEqual(shown["department"], "General")
        self.assertTrue(shown["is_confidential"])

    def test_claim_reveal_keeps_the_client(self):
        shown = redact_service_payload(self._payload(), confidential=True, code="SCRN0001", reveal=True)
        self.assertEqual(shown["patient_name"], "Ama Mensah")
        self.assertEqual(shown["patient_card_number"], "GH-1")
        self.assertEqual(shown["confidential_code"], "SCRN0001")

    def test_ordinary_visit_is_unchanged(self):
        shown = redact_service_payload(self._payload(), confidential=False, code=None, reveal=False)
        self.assertEqual(shown["patient_name"], "Ama Mensah")
        self.assertFalse(shown["is_confidential"])


class RoleTests(unittest.TestCase):
    def test_nurse_cannot_open_the_register(self):
        nurse = SimpleNamespace(role="Nurse", additional_roles=[], id=1)
        self.assertFalse(user_has_role(nurse, REGISTER_ROLES))

    def test_claims_can_reveal_a_claim(self):
        officer = SimpleNamespace(role="Claims", additional_roles=[], id=2)
        self.assertTrue(user_has_role(officer, CLAIM_REVEAL_ROLES))

    def test_additional_doctor_role_counts(self):
        user = SimpleNamespace(role="Records", additional_roles=[SimpleNamespace(role="Doctor")], id=3)
        self.assertTrue(user_has_role(user, REGISTER_ROLES))


if __name__ == "__main__":
    unittest.main()
