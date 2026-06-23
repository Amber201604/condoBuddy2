import frappe
from frappe.model.document import Document
from frappe.utils import now

class FacilityBooking(Document):
	def validate(self):
		# Check for conflicts
		conflicts = frappe.db.sql("""
			SELECT name FROM `tabFacility Booking`
			WHERE facility = %s
			AND booking_date = %s
			AND status NOT IN ('Cancelled', 'Rejected')
			AND name != %s
			AND (
				(start_time < %s AND end_time > %s) OR
				(start_time < %s AND end_time > %s) OR
				(start_time >= %s AND end_time <= %s)
			)
		""", (self.facility, self.booking_date, self.name or "",
			  self.end_time, self.start_time,
			  self.end_time, self.start_time,
			  self.start_time, self.end_time))
		
		if conflicts:
			frappe.throw("This time slot conflicts with an existing booking")
		
		# Check max booking hours
		facility = frappe.get_doc("Facility", self.facility)
		if facility.max_booking_hours:
			from datetime import datetime
			start = datetime.strptime(str(self.start_time), "%H:%M:%S")
			end = datetime.strptime(str(self.end_time), "%H:%M:%S")
			duration = (end - start).total_seconds() / 3600
			if duration > facility.max_booking_hours:
				frappe.throw(f"Max booking duration is {facility.max_booking_hours} hours")

	def on_submit(self):
		# Send to FastAPI backend via webhook
		try:
			import requests
			from frappe.utils import get_url
			
			core_url = frappe.conf.get("condobuddy_core_url", "http://core:8000")
			webhook_url = f"{core_url}/api/v1/webhooks/facility-booking"
			
			payload = {
				"booking_id": self.name,
				"facility": self.facility,
				"resident": self.resident,
				"unit": self.unit,
				"booking_date": str(self.booking_date),
				"start_time": str(self.start_time),
				"end_time": str(self.end_time),
				"status": self.status,
				"event": "created"
			}
			
			requests.post(webhook_url, json=payload, timeout=5)
		except Exception:
			frappe.log_error("Facility Booking Webhook Failed")

	def on_cancel(self):
		try:
			import requests
			core_url = frappe.conf.get("condobuddy_core_url", "http://core:8000")
			webhook_url = f"{core_url}/api/v1/webhooks/facility-booking"
			
			payload = {
				"booking_id": self.name,
				"event": "cancelled"
			}
			requests.post(webhook_url, json=payload, timeout=5)
		except Exception:
			frappe.log_error("Facility Booking Cancel Webhook Failed")
