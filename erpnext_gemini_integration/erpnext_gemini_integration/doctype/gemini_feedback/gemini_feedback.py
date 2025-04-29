# Copyright (c) 2025, Golive-Solutions and contributors
# For license information, please see license.txt


from __future__ import unicode_literals
import frappe
import json
from frappe import _
from frappe.model.document import Document

class GeminiFeedback(Document):
    """
    DocType for Gemini Feedback
    
    This class handles:
    - User feedback on AI responses
    - Data collection for hallucination mitigation
    - Quality improvement metrics
    """
    
    def validate(self):
        """Validate feedback before saving"""
        self.validate_feedback_type()
    
    def validate_feedback_type(self):
        """Validate feedback type"""
        valid_feedback_types = ["positive", "negative", "neutral"]
        if self.feedback not in valid_feedback_types:
            frappe.throw(_("Invalid feedback type. Must be one of: {0}").format(", ".join(valid_feedback_types)))
    
    def before_save(self):
        """Actions to perform before saving"""
        # Ensure timestamp is set
        if not self.timestamp:
            self.timestamp = frappe.utils.now()
        
        # Ensure user is set
        if not self.user:
            self.user = frappe.session.user
    
    def after_insert(self):
        """Actions to perform after inserting"""
        # Update feedback stats
        self.update_feedback_stats()
    
    def update_feedback_stats(self):
        """Update feedback statistics"""
        try:
            # Get message
            message = frappe.get_doc("Gemini Message", self.message)
            
            # Get conversation
            conversation = frappe.get_doc("Gemini Conversation", message.conversation)
            
            # Update feedback count in settings
            settings = frappe.get_single("Gemini Assistant Settings")
            
            if self.feedback == "positive":
                settings.positive_feedback_count = (settings.positive_feedback_count or 0) + 1
            elif self.feedback == "negative":
                settings.negative_feedback_count = (settings.negative_feedback_count or 0) + 1
            
            settings.save(ignore_permissions=True)
            
        except Exception as e:
            frappe.log_error(f"Error updating feedback stats: {str(e)}")
