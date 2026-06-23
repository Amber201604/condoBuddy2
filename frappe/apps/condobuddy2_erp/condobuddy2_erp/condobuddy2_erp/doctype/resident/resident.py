import frappe
from frappe.model.document import Document

class Resident(Document):
	def validate(self):
		self.full_name = f"{self.first_name} {self.last_name or ''}".strip()
		
		# Link to Frappe User if email matches
		if self.email and not self.user_account:
			user = frappe.db.get_value("User", {"email": self.email}, "name")
			if user:
				self.user_account = user
				self.db_set("user_account", user)
