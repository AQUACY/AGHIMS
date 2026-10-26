"""XML imports and GHIMS monthly pulls must not be treated as the same visit."""
import unittest

from app.services.claim_merge import import_pipeline, same_import_pipeline, serialize_ghims_related_item


class ImportPipelineTests(unittest.TestCase):
    def test_blank_and_xml_are_the_xml_pipeline(self):
        self.assertEqual(import_pipeline(None), "xml")
        self.assertEqual(import_pipeline(""), "xml")
        self.assertEqual(import_pipeline("xml"), "xml")
        self.assertEqual(import_pipeline("XML"), "xml")

    def test_live_month_rows_are_a_separate_pipeline(self):
        self.assertEqual(import_pipeline("ghims_live"), "ghims_live")
        self.assertFalse(same_import_pipeline("xml", "ghims_live"))
        self.assertTrue(same_import_pipeline(None, "xml"))
        self.assertTrue(same_import_pipeline("ghims_live", "ghims_live"))

    def test_related_payload_includes_pipeline(self):
        class Batch:
            source = "ghims_live"
            file_name = "June 2026 claims"

        class Item:
            id = 9
            claim_claim_id = "CLA-1"
            status = "draft"
            batch_id = 2
            payload = {"memberNo": "123", "specialtyAttended": "OPD"}

        row = serialize_ghims_related_item(Item(), batch=Batch())
        self.assertEqual(row["batch_source"], "ghims_live")


if __name__ == "__main__":
    unittest.main()
