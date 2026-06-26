app_name = "condobuddy2_erp"
app_title = "CondoBuddy2 ERP"
app_publisher = "CondoBuddy Team"
app_description = "Smart Community Platform for Property Management"
app_email = "admin@condobuddy.ca"
app_license = "mit"
app_version = "1.0.0"

# Resident portal assets.
# The resident portal page (`www/resident-portal.html`) links these directly,
# so they are intentionally NOT added to `app_include_*` (which would load them
# into the Frappe Desk admin UI and is unnecessary).

# Website
website_context = {
	"favicon": "/assets/condobuddy2_erp/images/favicon.png",
	"splash_image": "/assets/condobuddy2_erp/images/logo.png",
}

# Fixtures
# Ship the management Desk homepage (Workspace) so the most-used functions are
# listed front and center. Synced on `install-app` and `bench migrate`.
fixtures = [
	{"dt": "Workspace", "filters": [["module", "=", "CondoBuddy2 ERP"]]},
]

# Boot session
# on_session_creation = "condobuddy2_erp.api.boot.boot_session"

# DocType Events
doc_events = {
    "Purchase Order": {
        "on_submit": [
            "condobuddy2_erp.condobuddy2_erp.doctype.project.project.update_flow_step_on_document_submit",
            "condobuddy2_erp.condobuddy2_erp.sub_flow_doc_events.on_submit",
        ],
        "on_cancel": [
            "condobuddy2_erp.condobuddy2_erp.doctype.project.project.update_flow_step_on_document_submit",
            "condobuddy2_erp.condobuddy2_erp.sub_flow_doc_events.on_cancel",
        ],
    },
    "Purchase Receipt": {
        "on_submit": "condobuddy2_erp.condobuddy2_erp.doctype.project.project.update_flow_step_on_document_submit",
        "on_cancel": "condobuddy2_erp.condobuddy2_erp.doctype.project.project.update_flow_step_on_document_submit",
    },
    "Stock Entry": {
        "on_submit": "condobuddy2_erp.condobuddy2_erp.sub_flow_doc_events.on_submit",
        "on_cancel": "condobuddy2_erp.condobuddy2_erp.sub_flow_doc_events.on_cancel",
    },
}

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
