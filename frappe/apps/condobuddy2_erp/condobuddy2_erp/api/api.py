import frappe
import hmac
from frappe import _


def _get_session_resident():
	"""Resolve the Resident record linked to the logged-in user."""
	user = frappe.session.user
	resident = frappe.db.get_value("Resident", {"user_account": user}, "name")
	if not resident:
		frappe.throw(_("Resident profile not found"))
	return resident


def _verify_internal_token():
	"""Verify the X-API-Key header against the configured internal key."""
	expected = frappe.conf.get("internal_api_key", "")
	if not expected:
		frappe.throw("Internal API key not configured", frappe.AuthenticationError)
	provided = frappe.request.headers.get("X-API-Key", "")
	if not hmac.compare_digest(expected, provided):
		frappe.throw("Invalid API key", frappe.AuthenticationError)

@frappe.whitelist()
def get_resident_portal_data():
	"""Get all data for resident portal dashboard"""
	resident = _get_session_resident()
	resident_doc = frappe.get_doc("Resident", resident)
	unit = resident_doc.unit
	
	# Bookings
	bookings = frappe.db.get_all("Facility Booking",
		filters={"resident": resident},
		fields=["name", "facility", "booking_date", "start_time", "end_time", "status"],
		order_by="booking_date desc",
		limit=10)
	
	# Visitors
	visitors = frappe.db.get_all("Visitor",
		filters={"host_resident": resident},
		fields=["name", "visitor_name", "visit_type", "expected_arrival", "status"],
		order_by="expected_arrival desc",
		limit=10)
	
	# Packages
	packages = frappe.db.get_all("Package",
		filters={"unit": unit, "status": ["in", ["Received", "Notified"]]},
		fields=["name", "tracking_number", "carrier", "status", "received_at"],
		order_by="received_at desc",
		limit=10)
	
	# Access logs
	access_logs = frappe.db.get_all("Access Log",
		filters={"unit": unit},
		fields=["name", "timestamp", "event_type", "method", "access_granted"],
		order_by="timestamp desc",
		limit=10)
	
	# Alerts
	alerts = frappe.db.get_all("CCTV Alert",
		fields=["name", "camera_location", "event_type", "timestamp"],
		order_by="timestamp desc",
		limit=5)
	
	return {
		"resident": {
			"id": resident,
			"name": resident_doc.full_name,
			"first_name": resident_doc.first_name,
			"unit": unit,
			"email": resident_doc.email,
			"phone": resident_doc.phone
		},
		"bookings": bookings,
		"visitors": visitors,
		"packages": packages,
		"access_logs": access_logs,
		"alerts": alerts
	}


@frappe.whitelist()
def get_facility_availability(facility, date):
	"""Get available time slots for a facility on a given date"""
	existing = frappe.db.get_all("Facility Booking",
		filters={
			"facility": facility,
			"booking_date": date,
			"status": ["not in", ["Cancelled", "Rejected"]]
		},
		fields=["start_time", "end_time"])
	
	return {"booked_slots": existing}


@frappe.whitelist()
def create_visitor(visitor_name, visit_type="Guest", host_resident=None, **kwargs):
	"""Create a visitor pre-registration for the logged-in resident."""
	if not host_resident:
		host_resident = _get_session_resident()

	allowed = ("visitor_phone", "visitor_email", "expected_arrival", "expected_departure", "notes")
	extra = {k: v for k, v in kwargs.items() if k in allowed and v}

	visitor = frappe.get_doc({
		"doctype": "Visitor",
		"visitor_name": visitor_name,
		"host_resident": host_resident,
		"visit_type": visit_type,
		**extra,
	}).insert()

	return {
		"visitor_id": visitor.name,
		"visitor_name": visitor.visitor_name,
		"qr_code": visitor.qr_code,
		"status": visitor.status,
	}


@frappe.whitelist()
def create_booking(facility, booking_date, start_time, end_time, purpose=None, number_of_guests=None):
	"""Create a facility booking for the logged-in resident."""
	resident = _get_session_resident()
	unit = frappe.db.get_value("Resident", resident, "unit")

	booking = frappe.get_doc({
		"doctype": "Facility Booking",
		"facility": facility,
		"resident": resident,
		"unit": unit,
		"booking_date": booking_date,
		"start_time": start_time,
		"end_time": end_time,
		"purpose": purpose,
		"number_of_guests": number_of_guests,
	}).insert()

	return {
		"booking_id": booking.name,
		"facility": booking.facility,
		"status": booking.status,
	}


@frappe.whitelist()
def get_cctv_feeds():
	"""Get list of CCTV camera feeds from core backend"""
	import requests
	try:
		core_url = frappe.conf.get("condobuddy_core_url", "http://core:8000")
		resp = requests.get(f"{core_url}/api/v1/cctv/feeds", timeout=5)
		return resp.json()
	except Exception as e:
		frappe.log_error(f"CCTV fetch failed: {str(e)}")
		return {"feeds": []}


@frappe.whitelist(allow_guest=True)
def receive_iot_alert():
	"""Webhook endpoint for IoT sensor alerts from core backend"""
	_verify_internal_token()
	data = frappe.request.get_json()
	
	allowed_types = {"cctv", "iot"}
	event_type = data.get("type", "iot")
	if event_type not in allowed_types:
		event_type = "iot"
	
	alert = frappe.get_doc({
		"doctype": "CCTV Alert" if event_type == "cctv" else "IoT Sensor Event",
		"camera_id": data.get("device_id"),
		"camera_location": data.get("location"),
		"timestamp": data.get("timestamp"),
		"event_type": data.get("event_type", "Other"),
		"notes": data.get("message", "")
	}).insert(ignore_permissions=True)
	
	return {"status": "ok", "alert_id": alert.name}


@frappe.whitelist(allow_guest=True)
def receive_access_log():
	"""Webhook endpoint for access control events from core backend"""
	_verify_internal_token()
	data = frappe.request.get_json()
	
	log = frappe.get_doc({
		"doctype": "Access Log",
		"timestamp": data.get("timestamp", frappe.utils.now()),
		"event_type": data.get("event_type", "Entry"),
		"device_id": data.get("device_id"),
		"device_location": data.get("location"),
		"resident": data.get("resident"),
		"unit": data.get("unit"),
		"visitor": data.get("visitor"),
		"access_granted": data.get("access_granted", 1),
		"method": data.get("method", "Unknown")
	}).insert(ignore_permissions=True)
	
	return {"status": "ok", "log_id": log.name}
