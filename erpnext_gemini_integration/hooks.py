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

