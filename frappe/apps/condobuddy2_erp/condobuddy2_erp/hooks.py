app_name = "condobuddy2_erp"
app_title = "CondoBuddy2 ERP"
app_publisher = "CondoBuddy Team"
app_description = "Smart Community Platform for Property Management"
app_email = "admin@condobuddy.ca"
app_license = "mit"
app_version = "1.0.0"

# Web pages
app_include_js = "/assets/condobuddy2_erp/js/condobuddy2.js"
app_include_css = "/assets/condobuddy2_erp/css/condobuddy2.css"

# Website
website_context = {
    "favicon": "/assets/condobuddy2_erp/images/favicon.png",
    "splash_image": "/assets/condobuddy2_erp/images/logo.png",
}

# Boot session
# on_session_creation = "condobuddy2_erp.api.boot.boot_session"

# DocType Events
# Lifecycle handlers (on_submit/on_cancel/on_update/validate) live directly on
# the DocType controller classes, so Frappe invokes them automatically. No
# additional doc_events wiring is needed here.
doc_events = {}

# Scheduled Tasks
# scheduler_events = {
#     "daily": [
#         "condobuddy2_erp.tasks.daily.cleanup_expired_visitors",
#     ],
#     "hourly": [
#         "condobuddy2_erp.tasks.hourly.sync_cctv_alerts",
#     ]
# }

# Website Routes
# website_route_rules = [
#     {"from_route": "/resident-portal/<path:app_path>", "to_route": "resident_portal"},
# ]
