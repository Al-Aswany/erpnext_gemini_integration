# -*- coding: utf-8 -*-
# Copyright (c) 2025, Your Name and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe import _
from frappe.utils import cint, now_datetime

class GeminiAuditLog:
    """
    Audit logging system for Gemini Assistant
    
    This class handles:
    - Logging all AI interactions
    - Tracking document modifications initiated by AI
    - Providing audit reports for compliance
    """
    
    def __init__(self, user=None):
        """
        Initialize the audit logger
        
        Args:
            user (str, optional): The user. Defaults to current user.
        """
        self.user = user or frappe.session.user
    
    def log_interaction(self, interaction_type, prompt, response, metadata=None):
        """
        Log an AI interaction
        
        Args:
            interaction_type (str): Type of interaction (query, function_call, document_event)
            prompt (str): The prompt sent to Gemini
            response (dict): The response from Gemini
            metadata (dict, optional): Additional metadata about the interaction
            
        Returns:
            str: ID of the audit log
        """
        try:
            # Create audit log
            audit_log = frappe.new_doc("Gemini Audit Log")
            audit_log.user = self.user
            audit_log.timestamp = now_datetime()
            audit_log.action = interaction_type
            
            # Set related document if provided in metadata
            if metadata and metadata.get("doctype"):
                audit_log.doctype = metadata.get("doctype")
            
            if metadata and metadata.get("docname"):
                audit_log.document = metadata.get("docname")
            
            # Set prompt and response
            audit_log.prompt = prompt
            audit_log.response = response.get("text", "") if isinstance(response, dict) else str(response)
            
            # Set actions taken if provided in metadata
            if metadata and metadata.get("actions_taken"):
                audit_log.actions_taken = json.dumps(metadata.get("actions_taken"))
            
            audit_log.insert(ignore_permissions=True)
            
            return audit_log.name
            
        except Exception as e:
            frappe.log_error(f"Error logging Gemini interaction: {str(e)}")
            return None
    
    def log_document_change(self, doctype, docname, changes, prompt=None, response=None):
        """
        Log a document change initiated by AI
        
        Args:
            doctype (str): DocType name
            docname (str): Document name
            changes (dict): Changes made to the document
            prompt (str, optional): The prompt that led to the change
            response (dict, optional): The response that led to the change
            
        Returns:
            str: ID of the audit log
        """
        try:
            # Create audit log
            audit_log = frappe.new_doc("Gemini Audit Log")
            audit_log.user = self.user
            audit_log.timestamp = now_datetime()
            audit_log.action = "document_change"
            audit_log.doctype = doctype
            audit_log.document = docname
            
            # Set prompt and response if provided
            if prompt:
                audit_log.prompt = prompt
            
            if response:
                audit_log.response = response.get("text", "") if isinstance(response, dict) else str(response)
            
            # Set changes as actions taken
            audit_log.actions_taken = json.dumps({
                "changes": changes
            })
            
            audit_log.insert(ignore_permissions=True)
            
            return audit_log.name
            
        except Exception as e:
            frappe.log_error(f"Error logging document change: {str(e)}")
            return None
    
    def log_function_call(self, function_name, args, result, prompt=None, response=None):
        """
        Log a function call initiated by AI
        
        Args:
            function_name (str): Name of the function
            args (dict): Arguments passed to the function
            result (dict): Result of the function call
            prompt (str, optional): The prompt that led to the function call
            response (dict, optional): The response that led to the function call
            
        Returns:
            str: ID of the audit log
        """
        try:
            # Create audit log
            audit_log = frappe.new_doc("Gemini Audit Log")
            audit_log.user = self.user
            audit_log.timestamp = now_datetime()
            audit_log.action = "function_call"
            
            # Set prompt and response if provided
            if prompt:
                audit_log.prompt = prompt
            
            if response:
                audit_log.response = response.get("text", "") if isinstance(response, dict) else str(response)
            
            # Set function call details as actions taken
            audit_log.actions_taken = json.dumps({
                "function_call": {
                    "name": function_name,
                    "args": args,
                    "result": result
                }
            })
            
            audit_log.insert(ignore_permissions=True)
            
            return audit_log.name
            
        except Exception as e:
            frappe.log_error(f"Error logging function call: {str(e)}")
            return None
    
    def get_user_audit_logs(self, user=None, limit=20):
        """
        Get audit logs for a user
        
        Args:
            user (str, optional): The user. Defaults to current user.
            limit (int, optional): Maximum number of logs to return
            
        Returns:
            list: List of audit logs
        """
        try:
            user = user or self.user
            
            # Check if user has permission to view other users' logs
            if user != self.user and not frappe.has_permission("Gemini Audit Log", "read"):
                frappe.throw(_("You don't have permission to view audit logs for other users"))
            
            # Get audit logs
            logs = frappe.get_all(
                "Gemini Audit Log",
                filters={"user": user},
                fields=["name", "timestamp", "action", "doctype", "document", "prompt", "response", "actions_taken"],
                order_by="timestamp desc",
                limit=cint(limit)
            )
            
            # Process logs
            for log in logs:
                if log.actions_taken:
                    log.actions_taken = json.loads(log.actions_taken)
            
            return logs
            
        except Exception as e:
            frappe.log_error(f"Error getting user audit logs: {str(e)}")
            return []
    
    def get_document_audit_logs(self, doctype, docname, limit=20):
        """
        Get audit logs for a document
        
        Args:
            doctype (str): DocType name
            docname (str): Document name
            limit (int, optional): Maximum number of logs to return
            
        Returns:
            list: List of audit logs
        """
        try:
            # Check if user has permission to view document
            if not frappe.has_permission(doctype, "read", docname):
                frappe.throw(_("You don't have permission to view this document"))
            
            # Get audit logs
            logs = frappe.get_all(
                "Gemini Audit Log",
                filters={"doctype": doctype, "document": docname},
                fields=["name", "timestamp", "user", "action", "prompt", "response", "actions_taken"],
                order_by="timestamp desc",
                limit=cint(limit)
            )
            
            # Process logs
            for log in logs:
                if log.actions_taken:
                    log.actions_taken = json.loads(log.actions_taken)
            
            return logs
            
        except Exception as e:
            frappe.log_error(f"Error getting document audit logs: {str(e)}")
            return []
    
    def generate_audit_report(self, filters=None, from_date=None, to_date=None):
        """
        Generate an audit report
        
        Args:
            filters (dict, optional): Filters to apply
            from_date (str, optional): Start date for report
            to_date (str, optional): End date for report
            
        Returns:
            dict: Audit report data
        """
        try:
            # Check if user has permission to generate audit reports
            if not frappe.has_permission("Gemini Audit Log", "report"):
                frappe.throw(_("You don't have permission to generate audit reports"))
            
            # Prepare filters
            query_filters = {}
            
            if filters:
                query_filters.update(filters)
            
            if from_date:
                query_filters["timestamp"] = [">=", from_date]
            
            if to_date:
                if "timestamp" in query_filters:
                    query_filters["timestamp"] = ["between", [from_date, to_date]]
                else:
                    query_filters["timestamp"] = ["<=", to_date]
            
            # Get audit logs
            logs = frappe.get_all(
                "Gemini Audit Log",
                filters=query_filters,
                fields=["name", "timestamp", "user", "action", "doctype", "document", "prompt", "response", "actions_taken"],
                order_by="timestamp desc"
            )
            
            # Process logs
            for log in logs:
                if log.actions_taken:
                    log.actions_taken = json.loads(log.actions_taken)
            
            # Generate summary statistics
            summary = {
                "total_interactions": len(logs),
                "users": {},
                "actions": {},
                "doctypes": {}
            }
            
            for log in logs:
                # Count by user
                if log.user not in summary["users"]:
                    summary["users"][log.user] = 0
                summary["users"][log.user] += 1
                
                # Count by action
                if log.action not in summary["actions"]:
                    summary["actions"][log.action] = 0
                summary["actions"][log.action] += 1
                
                # Count by doctype
                if log.doctype:
                    if log.doctype not in summary["doctypes"]:
                        summary["doctypes"][log.doctype] = 0
                    summary["doctypes"][log.doctype] += 1
            
            return {
                "logs": logs,
                "summary": summary
            }
            
        except Exception as e:
            frappe.log_error(f"Error generating audit report: {str(e)}")
            return {
                "logs": [],
                "summary": {
                    "total_interactions": 0,
                    "users": {},
                    "actions": {},
                    "doctypes": {}
                }
            }
