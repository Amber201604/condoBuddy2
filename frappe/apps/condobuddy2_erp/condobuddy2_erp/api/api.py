import frappe
from frappe import _

@frappe.whitelist()
def get_resident_portal_data():
	"""Get all data for resident portal dashboard"""
	user = frappe.session.user
	resident = frappe.db.get_value("Resident", {"user_account": user}, "name")
	
	if not resident:
		frappe.throw(_("Resident profile not found"))
	
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
			"name": resident_doc.full_name,
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
def create_visitor(visitor_name, host_resident, visit_type, **kwargs):
	"""Create a visitor pre-registration"""
	visitor = frappe.get_doc({
		"doctype": "Visitor",
		"visitor_name": visitor_name,
		"host_resident": host_resident,
		"visit_type": visit_type,
		**kwargs
	}).insert()
	
	return {"visitor_id": visitor.name, "qr_code": visitor.qr_code}


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
	data = frappe.request.get_json()
	
	alert = frappe.get_doc({
		"doctype": "CCTV Alert" if data.get("type") == "cctv" else "IoT Sensor Event",
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
