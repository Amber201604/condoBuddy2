# Copyright (c) 2026, XP and contributors
# For license information, please see license.txt

import json
import time
from base64 import b64encode
from io import BytesIO

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class UserQRCode(Document):
	def before_insert(self):
		self.user = self.user or frappe.session.user
		self.user_id = self.user
		self.regenerate_token()

	def regenerate_token(self):
		self.qr_token = frappe.generate_hash(length=20)
		self.qr_payload = json.dumps(
			{
				"user_id": self.user_id,
				"token": self.qr_token,
				"ts": int(time.time()),
			},
			ensure_ascii=False,
		)
		self.last_refreshed = now_datetime()


def generate_qr_svg(payload):
	from pyqrcode import create as qrcreate

	qr = qrcreate(payload)
	stream = BytesIO()
	try:
		qr.svg(stream, scale=6, background="#ffffff", module_color="#000000")
		svg = stream.getvalue().decode().replace("\n", "")
		return b64encode(svg.encode()).decode()
	finally:
		stream.close()


def get_or_create_user_qr(user=None):
	user = user or frappe.session.user
	if user == "Guest":
		frappe.throw(_("Please login to view your QR code."), frappe.PermissionError)

	if frappe.db.exists("User QR Code", user):
		doc = frappe.get_doc("User QR Code", user)
		if doc.user != user:
			frappe.throw(_("Not permitted"), frappe.PermissionError)
		return doc

	doc = frappe.get_doc(
		{
			"doctype": "User QR Code",
			"user": user,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


def build_qr_response(doc):
	full_name = frappe.db.get_value("User", doc.user, "full_name") or doc.user
	return {
		"user_id": doc.user_id,
		"full_name": full_name,
		"qr_svg": generate_qr_svg(doc.qr_payload),
		"last_refreshed": doc.last_refreshed,
	}


@frappe.whitelist()
def get_my_qr_code():
	doc = get_or_create_user_qr()
	return build_qr_response(doc)


@frappe.whitelist()
def refresh_my_qr_code():
	doc = get_or_create_user_qr()
	doc.regenerate_token()
	doc.save(ignore_permissions=True)
	return build_qr_response(doc)
