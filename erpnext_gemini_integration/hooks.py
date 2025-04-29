from __future__ import unicode_literals
import frappe
import os # Keep os import as it might be used by hooks added in main
from frappe import _

app_name = "erpnext_gemini_integration"
app_title = "ERPNext Gemini Integration"
app_publisher = "Golive-Solutions"
app_description = "App for ERPNext Gemini Integration"
app_email = "info@golive-solutions.com"
app_license = "MIT"


# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = ["/assets/erpnext_gemini_integration/css/chat_widget.css"]
app_include_js = ["/assets/erpnext_gemini_integration/js/chat_widget.js"]

# include js, css files in header of web template
web_include_css = ["/assets/erpnext_gemini_integration/css/chat_widget.css"]
web_include_js = ["/assets/erpnext_gemini_integration/js/chat_widget.js"]

# Installation
# ------------
# Keep after_install hook from origin/main
# after_install = "erpnext_gemini_integration.utils.install.after_install"

# Document Events
# ---------------
# Keep doc_events from origin/main as workflow.py is kept
doc_events = {
    "*": {
        "on_submit": "erpnext_gemini_integration.modules.workflow.on_document_submit",
        # Add other events if they were present in origin/main and needed
    }
}

# Scheduled Tasks
# ---------------
# Keep scheduler_events from origin/main as workflow.py is kept
scheduler_events = {
    "daily": [
        "erpnext_gemini_integration.modules.workflow.run_daily_analysis",
    ],
    "hourly": [
        "erpnext_gemini_integration.modules.workflow.run_hourly_analysis",
    ],
}


# User Data Protection
# --------------------
# Keep user_data_fields from origin/main
user_data_fields = [
    {
        "doctype": "{doctype}", # Placeholder, should be reviewed if used
        "filter_by": "{filter_by}",
        "redact_fields": ["{field1}", "{field2}"],
        "partial": 1,
    },
    {
        "doctype": "Gemini Conversation",
        "filter_by": "user",
        "redact_fields": ["content"],
        "partial": 1,
    },
]


# API Endpoints
# ------------
# Keep cleaned api_endpoints from HEAD (manus-improvements)
api_endpoints = [
    {
        "path": "/gemini/chat",
        "method": "erpnext_gemini_integration.api.chat_api.process_message"
    },
]

# Boot Info
# ---------
# Keep boot_session from origin/main
boot_session = "erpnext_gemini_integration.utils.boot.boot_session"

