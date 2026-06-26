import frappe

no_cache = 1


def get_context(context):
	"""Resident portal page context.

	Exposes the CSRF token so the portal's AJAX writes (visitor / booking
	creation) pass CSRF validation for the logged-in resident. The page itself
	stays reachable; data endpoints are scoped to the session user, so guests
	simply see a prompt to sign in.
	"""
	context.csrf_token = frappe.sessions.get_csrf_token()
	context.no_cache = 1
	return context
