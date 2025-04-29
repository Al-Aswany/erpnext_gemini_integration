# Copyright (c) 2025, Golive-Solutions and contributors
# For license information, please see license.txt



from __future__ import unicode_literals
import frappe
import json
from frappe import _
from frappe.model.document import Document

class GeminiAuditLog(Document):
    """
    DocType for Gemini Audit Log
    
    This class handles:
    - Storing audit logs for AI interactions
    - Tracking document modifications initiated by AI
    - Supporting compliance requirements
    """
    
    def validate(self):
        """Validate audit log before saving"""
        self.validate_actions_taken()
    
    def validate_actions_taken(self):
        """Validate actions_taken JSON"""
        if self.actions_taken:
            try:
                json.loads(self.actions_taken)
            except Exception:
                frappe.throw(_("Invalid actions_taken JSON"))
    
    def before_save(self):
        """Actions to perform before saving"""
        # Ensure timestamp is set
        if not self.timestamp:
            self.timestamp = frappe.utils.now()
        
        # Ensure user is set
        if not self.user:
            self.user = frappe.session.user
