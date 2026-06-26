# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class TableOrderedvsReceived(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from erpnext.accounts.doctype.purchase_taxes_and_charges.purchase_taxes_and_charges import PurchaseTaxesandCharges
		from frappe.types import DF

		accepted_qty: DF.Float
		amount: DF.Currency
		base_amount: DF.Currency
		bom: DF.Link | None
		damaged_qty: DF.Float
		item_code: DF.Link | None
		material_request: DF.Link | None
		material_request_item: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		purchase_order: DF.Link | None
		purchase_order_item: DF.Data | None
		qty: DF.Float
		sales_order: DF.Link | None
		sales_order_item: DF.Data | None
		stock_qty: DF.Float
		taxes: DF.Table[PurchaseTaxesandCharges]
		wip_composite_asset: DF.Link | None
	# end: auto-generated types
	pass
