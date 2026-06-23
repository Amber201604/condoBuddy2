import frappe
from frappe.model.document import Document

class Visitor(Document):
	def validate(self):
		# Auto-generate QR code if not set
		if not self.qr_code:
			import uuid
			self.qr_code = str(uuid.uuid4())[:16]
		
		# Set host unit from resident
		if self.host_resident and not self.host_unit:
			resident = frappe.get_doc("Resident", self.host_resident)
			if resident.unit:
				self.host_unit = resident.unit

	def on_update(self):
		# Send to FastAPI backend
		try:
			import requests
			core_url = frappe.conf.get("condobuddy_core_url", "http://core:8000")
			webhook_url = f"{core_url}/api/v1/webhooks/visitor"
			
			payload = {
				"visitor_id": self.name,
				"visitor_name": self.visitor_name,
				"visitor_phone": self.visitor_phone,
				"host_resident": self.host_resident,
				"host_unit": self.host_unit,
				"visit_type": self.visit_type,
				"expected_arrival": str(self.expected_arrival) if self.expected_arrival else None,
				"expected_departure": str(self.expected_departure) if self.expected_departure else None,
				"qr_code": self.qr_code,
				"status": self.status
			}
			requests.post(webhook_url, json=payload, timeout=5)
		except Exception:
			frappe.log_error("Visitor Webhook Failed")
