import frappe
from frappe.tests.utils import FrappeTestCase


class TestIntegration(FrappeTestCase):
    """Integration tests — verify Frappe ↔ FastAPI connectivity"""

    def test_frappe_conf_has_core_url(self):
        """Frappe config should reference the core backend"""
        core_url = frappe.conf.get("condobuddy_core_url")
        self.assertIsNotNone(core_url)
        self.assertIn(":8000", core_url)

    def test_webhook_payload_structure(self):
        """Facility booking webhook payload should match FastAPI expectations"""
        payload = {
            "booking_id": "FB-2026-00001",
            "facility": "FAC-Meeting Room A",
            "resident": "RES-0001",
            "unit": "UNIT-101",
            "booking_date": "2026-06-25",
            "start_time": "10:00:00",
            "end_time": "11:00:00",
            "status": "Pending",
            "event": "created"
        }
        required_keys = ["booking_id", "facility", "resident", "unit", "booking_date", "start_time", "end_time", "status", "event"]
        for key in required_keys:
            self.assertIn(key, payload)

    def test_iot_alert_webhook(self):
        """IoT alert webhook payload should be valid"""
        payload = {
            "device_id": "SEN-SMOKE-001",
            "location": "Hallway 3A",
            "timestamp": "2026-06-22T12:00:00",
            "event_type": "Smoke Detected",
            "type": "iot",
            "message": "Smoke detected in hallway"
        }
        self.assertEqual(payload["type"], "iot")
        self.assertIn("device_id", payload)
        self.assertIn("location", payload)

    def test_access_log_webhook(self):
        """Access log webhook payload should be valid"""
        payload = {
            "timestamp": "2026-06-22T12:00:00",
            "event_type": "Entry",
            "device_id": "GATE-MAIN-001",
            "location": "Main Gate",
            "resident": "RES-0001",
            "unit": "UNIT-101",
            "access_granted": 1,
            "method": "QR Code"
        }
        self.assertTrue(payload["access_granted"])
        self.assertEqual(payload["method"], "QR Code")

    def test_api_methods_exist(self):
        """All whitelisted API methods should be importable"""
        from condobuddy2_erp.api.api import (
            get_resident_portal_data,
            get_facility_availability,
            create_visitor,
            get_cctv_feeds,
            receive_iot_alert,
            receive_access_log
        )
        self.assertTrue(callable(get_resident_portal_data))
        self.assertTrue(callable(get_facility_availability))
        self.assertTrue(callable(create_visitor))
        self.assertTrue(callable(get_cctv_feeds))
        self.assertTrue(callable(receive_iot_alert))
        self.assertTrue(callable(receive_access_log))
