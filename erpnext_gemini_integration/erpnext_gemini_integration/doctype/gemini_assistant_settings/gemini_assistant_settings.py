# Copyright (c) 2025, Golive-Solutions and contributors
# For license information, please see license.txt



from __future__ import unicode_literals
import frappe
import json
from frappe import _
from frappe.model.document import Document

class GeminiAssistantSettings(Document):
    """
    DocType for Gemini Assistant Settings
    
    This class handles:
    - API key management
    - Model selection
    - Safety settings configuration
    - Feature toggles
    """
    
    def validate(self):
        """Validate settings before saving"""
        self.validate_api_key()
        self.validate_safety_settings()
    
    def validate_api_key(self):
        """Validate API key is set"""
        if not self.get_password("api_key"):
            frappe.throw(_("API key is required"))
    
    def validate_safety_settings(self):
        """Validate safety settings JSON"""
        if self.safety_settings:
            try:
                json.loads(self.safety_settings)
            except Exception:
                frappe.throw(_("Invalid safety settings JSON"))
    
    def on_update(self):
        """Actions to perform when settings are updated"""
        self.clear_cache()
    
    def clear_cache(self):
        """Clear cache for settings"""
        frappe.cache().delete_key("gemini_assistant_settings")
