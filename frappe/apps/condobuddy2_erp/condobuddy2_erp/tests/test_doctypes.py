#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CondoBuddy2 — Frappe App Unit & Integration Tests
Run: bench --site <site> run-tests --app condobuddy2_erp
"""

import frappe
from frappe.tests.utils import FrappeTestCase


class TestUnit(FrappeTestCase):
	def setUp(self):
		frappe.db.sql("DELETE FROM `tabUnit` WHERE unit_number LIKE 'TEST-%'")
		frappe.db.commit()

	def test_create_unit(self):
		unit = frappe.get_doc({
			"doctype": "Unit",
			"unit_number": "TEST-101",
			"floor": 1,
			"tower": "A",
			"unit_type": "2 Bedroom",
			"status": "Vacant"
		}).insert()
		self.assertEqual(unit.unit_number, "TEST-101")
		self.assertEqual(unit.status, "Vacant")

	def test_unique_unit_number(self):
		frappe.get_doc({
			"doctype": "Unit",
			"unit_number": "TEST-102",
			"status": "Vacant"
		}).insert()
		with self.assertRaises(frappe.exceptions.ValidationError):
			frappe.get_doc({
				"doctype": "Unit",
				"unit_number": "TEST-102",
				"status": "Occupied"
			}).insert()


class TestResident(FrappeTestCase):
	def setUp(self):
		frappe.db.sql("DELETE FROM `tabResident` WHERE first_name LIKE 'Test%'")
		frappe.db.commit()

	def test_create_resident(self):
		# Create unit first
		unit = frappe.get_doc({
			"doctype": "Unit",
			"unit_number": "TEST-201",
			"status": "Occupied"
		}).insert()
		
		resident = frappe.get_doc({
			"doctype": "Resident",
			"first_name": "Test",
			"last_name": "User",
			"unit": unit.name,
			"email": "test@example.com",
			"resident_type": "Owner"
		}).insert()
		
		self.assertEqual(resident.full_name, "Test User")
		self.assertEqual(resident.unit, unit.name)


class TestFacility(FrappeTestCase):
	def setUp(self):
		frappe.db.sql("DELETE FROM `tabFacility` WHERE facility_name LIKE 'Test%'")
		frappe.db.commit()

	def test_create_facility(self):
		fac = frappe.get_doc({
			"doctype": "Facility",
			"facility_name": "Test Meeting Room",
			"facility_type": "Meeting Room",
			"capacity": 10,
			"requires_approval": 1,
			"max_booking_hours": 2
		}).insert()
		self.assertTrue(fac.requires_approval)
		self.assertEqual(fac.max_booking_hours, 2)


class TestFacilityBooking(FrappeTestCase):
	def setUp(self):
		frappe.db.sql("DELETE FROM `tabFacility Booking` WHERE purpose LIKE 'Test%'")
		frappe.db.sql("DELETE FROM `tabFacility` WHERE facility_name LIKE 'Test%'")
		frappe.db.sql("DELETE FROM `tabResident` WHERE first_name LIKE 'Test%'")
		frappe.db.sql("DELETE FROM `tabUnit` WHERE unit_number LIKE 'TEST-%'")
		frappe.db.commit()

	def test_booking_conflict(self):
		unit = frappe.get_doc({
			"doctype": "Unit",
			"unit_number": "TEST-301",
			"status": "Occupied"
		}).insert()
		
		resident = frappe.get_doc({
			"doctype": "Resident",
			"first_name": "Test",
			"unit": unit.name,
			"resident_type": "Owner"
		}).insert()
		
		fac = frappe.get_doc({
			"doctype": "Facility",
			"facility_name": "Test Gym",
			"facility_type": "Gym"
		}).insert()
		
		from datetime import date
		booking1 = frappe.get_doc({
			"doctype": "Facility Booking",
			"facility": fac.name,
			"resident": resident.name,
			"unit": unit.name,
			"booking_date": date.today(),
			"start_time": "10:00:00",
			"end_time": "11:00:00",
			"purpose": "Test session"
		}).insert()
		
		with self.assertRaises(frappe.exceptions.ValidationError):
			frappe.get_doc({
				"doctype": "Facility Booking",
				"facility": fac.name,
				"resident": resident.name,
				"unit": unit.name,
				"booking_date": date.today(),
				"start_time": "10:30:00",
				"end_time": "11:30:00",
				"purpose": "Test overlapping"
			}).insert()

	def test_max_booking_hours(self):
		unit = frappe.get_doc({
			"doctype": "Unit",
			"unit_number": "TEST-302",
			"status": "Occupied"
		}).insert()
		
		resident = frappe.get_doc({
			"doctype": "Resident",
			"first_name": "Test",
			"unit": unit.name
		}).insert()
		
		fac = frappe.get_doc({
			"doctype": "Facility",
			"facility_name": "Test Pool",
			"facility_type": "Swimming Pool",
			"max_booking_hours": 1
		}).insert()
		
		from datetime import date
		with self.assertRaises(frappe.exceptions.ValidationError):
			frappe.get_doc({
				"doctype": "Facility Booking",
				"facility": fac.name,
				"resident": resident.name,
				"unit": unit.name,
				"booking_date": date.today(),
				"start_time": "10:00:00",
				"end_time": "13:00:00",
				"purpose": "Test too long"
			}).insert()


class TestVisitor(FrappeTestCase):
	def setUp(self):
		frappe.db.sql("DELETE FROM `tabVisitor` WHERE visitor_name LIKE 'Test%'")
		frappe.db.sql("DELETE FROM `tabResident` WHERE first_name LIKE 'Test%'")
		frappe.db.sql("DELETE FROM `tabUnit` WHERE unit_number LIKE 'TEST-%'")
		frappe.db.commit()

	def test_visitor_qr_generation(self):
		unit = frappe.get_doc({
			"doctype": "Unit",
			"unit_number": "TEST-401",
			"status": "Occupied"
		}).insert()
		
		resident = frappe.get_doc({
			"doctype": "Resident",
			"first_name": "Test",
			"unit": unit.name
		}).insert()
		
		visitor = frappe.get_doc({
			"doctype": "Visitor",
			"visitor_name": "Test Guest",
			"host_resident": resident.name,
			"visit_type": "Guest"
		}).insert()
		
		self.assertTrue(visitor.qr_code)
		self.assertEqual(len(visitor.qr_code), 16)
		self.assertEqual(visitor.host_unit, unit.name)


class TestAccessLog(FrappeTestCase):
	def setUp(self):
		frappe.db.sql("DELETE FROM `tabAccess Log` WHERE device_id = 'TEST-DEV-001'")
		frappe.db.commit()

	def test_create_access_log(self):
		log = frappe.get_doc({
			"doctype": "Access Log",
			"timestamp": frappe.utils.now(),
			"event_type": "Entry",
			"device_id": "TEST-DEV-001",
			"device_location": "Main Gate",
			"access_granted": 1,
			"method": "QR Code"
		}).insert()
		self.assertEqual(log.event_type, "Entry")
		self.assertTrue(log.access_granted)


class TestCCTVAlert(FrappeTestCase):
	def setUp(self):
		frappe.db.sql("DELETE FROM `tabCCTV Alert` WHERE camera_id = 'TEST-CAM-001'")
		frappe.db.commit()

	def test_create_alert(self):
		alert = frappe.get_doc({
			"doctype": "CCTV Alert",
			"camera_id": "TEST-CAM-001",
			"camera_location": "Lobby",
			"timestamp": frappe.utils.now(),
			"event_type": "Motion Detected"
		}).insert()
		self.assertEqual(alert.event_type, "Motion Detected")


class TestPackage(FrappeTestCase):
	def setUp(self):
		frappe.db.sql("DELETE FROM `tabPackage` WHERE tracking_number LIKE 'TEST-%'")
		frappe.db.sql("DELETE FROM `tabUnit` WHERE unit_number LIKE 'TEST-%'")
		frappe.db.commit()

	def test_package_lifecycle(self):
		unit = frappe.get_doc({
			"doctype": "Unit",
			"unit_number": "TEST-501",
			"status": "Occupied"
		}).insert()
		
		pkg = frappe.get_doc({
			"doctype": "Package",
			"tracking_number": "TEST-TRACK-001",
			"carrier": "Canada Post",
			"unit": unit.name,
			"status": "Received"
		}).insert()
		
		self.assertEqual(pkg.status, "Received")
		
		pkg.status = "Notified"
		pkg.save()
		self.assertEqual(pkg.status, "Notified")
		
		pkg.status = "Picked Up"
		pkg.save()
		self.assertEqual(pkg.status, "Picked Up")


class TestIoTSensor(FrappeTestCase):
	def setUp(self):
		frappe.db.sql("DELETE FROM `tabIoT Sensor` WHERE device_id LIKE 'TEST-%'")
		frappe.db.commit()

	def test_sensor_status(self):
		sensor = frappe.get_doc({
			"doctype": "IoT Sensor",
			"device_id": "TEST-SMOKE-001",
			"sensor_name": "Test Smoke Sensor",
			"sensor_type": "Smoke",
			"location": "Hallway 3A",
			"status": "Online"
		}).insert()
		
		self.assertEqual(sensor.status, "Online")
		self.assertEqual(sensor.sensor_type, "Smoke")

