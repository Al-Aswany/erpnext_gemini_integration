# -*- coding: utf-8 -*-
# Copyright (c) 2025, Your Name and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe import _
from frappe.utils import cint

class GeminiSecurity:
    """
    Security layer for Gemini Assistant
    
    This class handles:
    - Role-based access control for AI features
    - Field-level masking based on user permissions
    - Audit logging for all AI interactions
    - Compliance with data protection regulations
    """
    
    def __init__(self, user=None):
        """
        Initialize the security layer
        
        Args:
            user (str, optional): The user. Defaults to current user.
        """
        self.user = user or frappe.session.user
    
    def can_access_gemini(self):
        """
        Check if user has permission to use Gemini assistant
        
        Returns:
            bool: Whether user has permission
        """
        # Check if user has the Gemini Assistant User role
        if frappe.db.exists("Role", "Gemini Assistant User") and frappe.db.get_value("Has Role", {
            "parent": self.user,
            "role": "Gemini Assistant User"
        }):
            return True
        
        # Check if user has permission to read Gemini Assistant Settings
        if frappe.has_permission("Gemini Assistant Settings", "read", user=self.user):
            return True
        
        # Check if user is System Manager
        if "System Manager" in frappe.get_roles(self.user):
            return True
        
        return False
    
    def filter_sensitive_data(self, doctype, doc_data):
        """
        Mask sensitive fields based on user permissions
        
        Args:
            doctype (str): DocType name
            doc_data (dict): Document data
            
        Returns:
            dict: Filtered document data
        """
        if not doc_data:
            return {}
        
        # If user has full access to the doctype, return all data
        if frappe.has_permission(doctype, "read", user=self.user) and frappe.has_permission(doctype, "write", user=self.user):
            return doc_data
        
        # Get meta for the doctype
        meta = frappe.get_meta(doctype)
        
        # Get sensitive field types
        sensitive_field_types = [
            "Password", 
            "Data", 
            "Small Text", 
            "Text", 
            "Long Text", 
            "Text Editor"
        ]
        
        # Get fields marked as sensitive in customization
        sensitive_fields = []
        customizations = frappe.get_all(
            "Property Setter",
            filters={
                "doc_type": doctype,
                "property": "gemini_sensitive_field",
                "value": "1"
            },
            fields=["field_name"]
        )
        
        for custom in customizations:
            sensitive_fields.append(custom.field_name)
        
        # Filter data
        filtered_data = {}
        for field, value in doc_data.items():
            # Skip if field is not in meta
            if not meta.get_field(field):
                continue
            
            field_meta = meta.get_field(field)
            
            # Skip if field is sensitive and user doesn't have permission
            if field in sensitive_fields or field_meta.fieldtype in sensitive_field_types:
                if not frappe.has_permission(doctype, "read", field=field, user=self.user):
                    filtered_data[field] = "********"
                    continue
            
            # Include field if user has permission
            if frappe.has_permission(doctype, "read", field=field, user=self.user):
                filtered_data[field] = value
        
        return filtered_data
    
    def log_interaction(self, prompt, response, actions_taken=None, doctype=None, docname=None):
        """
        Log AI interaction for audit purposes
        
        Args:
            prompt (str): The prompt sent to Gemini
            response (dict): The response from Gemini
            actions_taken (dict, optional): Actions taken based on response
            doctype (str, optional): Related DocType
            docname (str, optional): Related document name
            
        Returns:
            str: ID of the audit log
        """
        try:
            # Create audit log
            audit_log = frappe.new_doc("Gemini Audit Log")
            audit_log.user = self.user
            audit_log.timestamp = frappe.utils.now()
            
            # Determine action type
            if actions_taken and actions_taken.get("function_call"):
                audit_log.action = "function_call"
            elif doctype and docname:
                audit_log.action = "document_event"
            else:
                audit_log.action = "query"
            
            # Set related document if provided
            if doctype:
                audit_log.doctype = doctype
            
            if docname:
                audit_log.document = docname
            
            # Set prompt and response
            audit_log.prompt = prompt
            audit_log.response = response.get("text", "") if isinstance(response, dict) else str(response)
            
            # Set actions taken
            if actions_taken:
                audit_log.actions_taken = json.dumps(actions_taken)
            
            audit_log.insert(ignore_permissions=True)
            
            return audit_log.name
            
        except Exception as e:
            frappe.log_error(f"Error logging Gemini interaction: {str(e)}")
            return None
    
    def get_user_permissions(self):
        """
        Get user permissions for current user
        
        Returns:
            dict: User permissions
        """
        # Get user permission doctypes
        user_permission_doctypes = frappe.get_all(
            "User Permission",
            filters={"user": self.user},
            fields=["allow", "for_value"],
            distinct=True
        )
        
        # Format permissions
        permissions = {}
        for perm in user_permission_doctypes:
            if perm.allow not in permissions:
                permissions[perm.allow] = []
            
            permissions[perm.allow].append(perm.for_value)
        
        return permissions
    
    def check_function_permission(self, function_name):
        """
        Check if user has permission to execute a function
        
        Args:
            function_name (str): Name of the function
            
        Returns:
            bool: Whether user has permission
        """
        try:
            # Get function doc
            function_doc = frappe.get_doc("Gemini Function", function_name)
            
            # Check if function is enabled
            if not function_doc.enabled:
                return False
            
            # Check if user has required role
            if function_doc.required_role and function_doc.required_role not in frappe.get_roles(self.user):
                return False
            
            return True
            
        except Exception as e:
            frappe.log_error(f"Error checking function permission: {str(e)}")
            return False
    
    def sanitize_prompt(self, prompt):
        """
        Sanitize prompt to remove sensitive information
        
        Args:
            prompt (str): The prompt to sanitize
            
        Returns:
            str: Sanitized prompt
        """
        # This is a basic implementation
        # In a real-world scenario, this would use more sophisticated techniques
        # such as named entity recognition to identify and mask sensitive information
        
        # Get sensitive keywords
        sensitive_keywords = frappe.get_all(
            "Gemini Sensitive Keyword",
            fields=["keyword"]
        )
        
        sanitized_prompt = prompt
        
        # Replace sensitive keywords
        for keyword in sensitive_keywords:
            sanitized_prompt = sanitized_prompt.replace(keyword.keyword, "********")
        
        return sanitized_prompt
    
    def validate_data_access(self, doctype, filters=None):
        """
        Validate if user has access to data based on filters
        
        Args:
            doctype (str): DocType name
            filters (dict, optional): Filters to apply
            
        Returns:
            bool: Whether user has access
        """
        try:
            # Check if user has read permission for doctype
            if not frappe.has_permission(doctype, "read", user=self.user):
                return False
            
            # If no filters, user has general access
            if not filters:
                return True
            
            # Get user permissions
            user_permissions = self.get_user_permissions()
            
            # Check if filters match user permissions
            for field, value in filters.items():
                # Skip if field is not in user permissions
                if field not in user_permissions:
                    continue
                
                # Check if value is in allowed values
                if value not in user_permissions[field]:
                    return False
            
            return True
            
        except Exception as e:
            frappe.log_error(f"Error validating data access: {str(e)}")
            return False
