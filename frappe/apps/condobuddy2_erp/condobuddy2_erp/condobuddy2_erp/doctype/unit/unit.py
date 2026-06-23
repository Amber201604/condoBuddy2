import frappe
from frappe.model.document import Document

class Unit(Document):
	def validate(self):
		self.full_address = f"{self.tower} - {self.unit_number}" if self.tower else self.unit_number
		
		# Ensure unit number is unique
		if frappe.db.exists("Unit", {"unit_number": self.unit_number, "name": ("!=", self.name)}):
			frappe.throw(f"Unit number {self.unit_number} already exists")
