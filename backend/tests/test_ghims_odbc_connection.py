"""Connection strings must match the ODBC driver that is actually installed."""
import unittest

from app.services.ghims_live_compare import ghims_odbc_connection_string


class GhimsOdbcConnectionTests(unittest.TestCase):
    def test_modern_driver_trusts_the_hospital_certificate(self):
        conn = ghims_odbc_connection_string(
            "ODBC Driver 18 for SQL Server",
            "10.10.16.20,1433",
            "GHHIMS02",
            "reader",
            "secret",
        )
        self.assertIn("Encrypt=yes;", conn)
        self.assertIn("TrustServerCertificate=yes;", conn)

    def test_legacy_sql_server_driver_omits_attributes_it_rejects(self):
        conn = ghims_odbc_connection_string(
            "SQL Server",
            "10.10.16.20,1433",
            "GHHIMS02",
            "reader",
            "secret",
        )
        self.assertNotIn("Encrypt=", conn)
        self.assertNotIn("TrustServerCertificate=", conn)
        self.assertIn("DRIVER={SQL Server};", conn)


if __name__ == "__main__":
    unittest.main()
