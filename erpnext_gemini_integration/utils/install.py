# -*- coding: utf-8 -*-
# Copyright (c) 2025, Golive-Solutions and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def after_install():
    """
    Run after app installation
    """
    create_default_settings()
    enable_chat_widget()

def create_default_settings():
    """
    Create default settings for Gemini Assistant
    """
    if not frappe.db.exists("Gemini Assistant Settings"):
        settings = frappe.new_doc("Gemini Assistant Settings")
        settings.enabled = 1
        settings.model = "gemini-pro"
        settings.temperature = 0.7
        settings.top_k = 40
        settings.top_p = 0.95
        settings.max_output_tokens = 2048
        
        # Default safety settings
        settings.safety_settings = """{
            "HARASSMENT": "BLOCK_MEDIUM_AND_ABOVE",
            "HATE_SPEECH": "BLOCK_MEDIUM_AND_ABOVE",
            "SEXUALLY_EXPLICIT": "BLOCK_MEDIUM_AND_ABOVE",
            "DANGEROUS_CONTENT": "BLOCK_MEDIUM_AND_ABOVE"
        }"""
        
        settings.insert(ignore_permissions=True)
        frappe.db.commit()
        
        frappe.msgprint(_("Default Gemini Assistant Settings created"))

def enable_chat_widget():
    """
    Enable the chat widget for all users
    """
    frappe.db.set_value("System Settings", "System Settings", "enable_chat", 1)
    
    # Set global config to enable Gemini Assistant
    frappe.db.set_global("gemini_assistant_enabled", 1)
    
    frappe.db.commit()
    frappe.msgprint(_("Gemini chat widget enabled")) 