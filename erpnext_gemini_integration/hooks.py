from __future__ import unicode_literals
import frappe
import os
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

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "erpnext_gemini_integration/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "erpnext_gemini_integration.install.before_install"
# after_install = "erpnext_gemini_integration.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "erpnext_gemini_integration.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "*": {
        "on_submit": "erpnext_gemini_integration.modules.workflow.on_document_submit",
        
    }
}
#"before_save": "erpnext_gemini_integration.modules.workflow.before_document_save",
# Scheduled Tasks
# ---------------

scheduler_events = {
    "daily": [
        "erpnext_gemini_integration.modules.workflow.run_daily_analysis",
    ],
    "hourly": [
        "erpnext_gemini_integration.modules.workflow.run_hourly_analysis",
    ],
}

# Testing
# -------

# before_tests = "erpnext_gemini_integration.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "erpnext_gemini_integration.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "erpnext_gemini_integration.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]


# User Data Protection
# --------------------

user_data_fields = [
    {
        "doctype": "{doctype}",
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

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"erpnext_gemini_integration.auth.validate"
# ]

# API Endpoints
# ------------

api_endpoints = [
    {
        "path": "/gemini/chat",
        "method": "erpnext_gemini_integration.api.chat_api.process_message"
    },
    {
        "path": "/gemini/analyze",
        "method": "erpnext_gemini_integration.api.chat_api.analyze_document"
    },
]
