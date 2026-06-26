# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class TableDeliveryHistory(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		item_code: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		qty_delivered: DF.Data | None
		reject_resolution: DF.Literal["-", "Resend missing items", "Return / Replace", "Compensation / Discount", "Fix Invoice / Correct Billing", "Write-off (Small Amount)"]
		total_rejecteddamaged: DF.Data | None
	# end: auto-generated types
	pass
