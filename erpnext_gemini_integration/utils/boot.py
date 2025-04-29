# -*- coding: utf-8 -*-
# Copyright (c) 2025, Golive-Solutions and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def boot_session(bootinfo):
    """
    Adds Gemini Assistant configuration to boot info
    
    Args:
        bootinfo: Boot info object passed by Frappe
    """
    # Check if Gemini Assistant is enabled globally
    gemini_enabled = frappe.db.get_global("gemini_assistant_enabled")
    
    # Add to boot info
    bootinfo.gemini_assistant_enabled = int(gemini_enabled or 0)
    
    # Check if user has permission to use Gemini Assistant
    if has_gemini_permission():
        bootinfo.gemini_assistant_enabled = 1
    
    # Add Gemini Assistant settings
    if bootinfo.gemini_assistant_enabled:
        add_gemini_settings(bootinfo)

def has_gemini_permission():
    """
    Check if user has permission to use Gemini Assistant
    
    Returns:
        bool: Whether user has permission
    """
    if frappe.session.user == "Administrator":
        return True
        
    # Check if user has the Gemini Assistant User role
    if frappe.db.exists("Role", "Gemini Assistant User") and frappe.db.get_value("Has Role", {
        "parent": frappe.session.user,
        "role": "Gemini Assistant User"
    }):
        return True
    
    # Check if user has permission to read Gemini Assistant Settings
    if frappe.has_permission("Gemini Assistant Settings", "read"):
        return True
    
    # Check if user is System Manager
    if "System Manager" in frappe.get_roles():
        return True
    
    return False

def add_gemini_settings(bootinfo):
    """
    Add Gemini Assistant settings to boot info
    
    Args:
        bootinfo: Boot info object passed by Frappe
    """
    # Check if settings exist
    if not frappe.db.exists("Gemini Assistant Settings"):
        return
    
    # Get settings from cache or database
    settings = frappe.cache().get_value("gemini_assistant_settings")
    
    if not settings:
        settings_doc = frappe.get_doc("Gemini Assistant Settings")
        
        if not settings_doc:
            return
            
        settings = {
            "enabled": settings_doc.enabled,
            "model": settings_doc.model,
            "temperature": settings_doc.temperature,
            "top_k": settings_doc.top_k,
            "top_p": settings_doc.top_p,
            "max_output_tokens": settings_doc.max_output_tokens,
        }
        
        # Cache settings
        frappe.cache().set_value("gemini_assistant_settings", settings)
    
    # Add settings to boot info
    bootinfo.gemini_assistant_settings = settings 