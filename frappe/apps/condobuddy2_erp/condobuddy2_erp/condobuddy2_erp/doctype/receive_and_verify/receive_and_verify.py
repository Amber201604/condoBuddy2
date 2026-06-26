# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ReceiveandVerify(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from erpnext.accounts.doctype.purchase_taxes_and_charges.purchase_taxes_and_charges import PurchaseTaxesandCharges
		from erpnext.buying.doctype.table_delivery_history.table_delivery_history import TableDeliveryHistory
		from erpnext.buying.doctype.table_ordered_vs_received.table_ordered_vs_received import TableOrderedvsReceived
		from frappe.types import DF

		amended_from: DF.Link | None
		compensation__discount: DF.Check
		custom_flow_name: DF.Link | None
		custom_project_name: DF.Link | None
		delivery_date_1: DF.Datetime | None
		delivery_date_2: DF.Datetime | None
		delivery_date_3: DF.Datetime | None
		delivery_date_4: DF.Datetime | None
		delivery_problem_found: DF.Literal["Yes", "No"]
		estimated_next_arrival: DF.Date | None
		fix_invoice__correct_billing: DF.Check
		flow_step: DF.Int
		fulfillment_status: DF.Literal["Waiting for Delivery", "Partly Received", "Delivery Has Problem", "Completed, All Received"]
		future_deliveries: DF.Literal["Yes", "No"]
		inspection_details_1: DF.SmallText | None
		inspection_details_2: DF.SmallText | None
		inspection_details_3: DF.SmallText | None
		inspection_details_4: DF.SmallText | None
		pr_count: DF.Int
		purchase_order: DF.Link | None
		resend_missing_items: DF.Check
		return__replace: DF.Check
		supplier_warehouse: DF.Link | None
		table_1st_delivery: DF.Table[TableDeliveryHistory]
		table_2nd_delivery: DF.Table[TableDeliveryHistory]
		table_3rd_delivery: DF.Table[TableDeliveryHistory]
		table_4th_delivery: DF.Table[TableDeliveryHistory]
		table_oredered_received: DF.Table[TableOrderedvsReceived]
		taxes: DF.Table[PurchaseTaxesandCharges]
		write_off_small_amount: DF.Check
	# end: auto-generated types
	pass
