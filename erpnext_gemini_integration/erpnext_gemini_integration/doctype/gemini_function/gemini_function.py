# Copyright (c) 2025, Golive-Solutions and contributors
# For license information, please see license.txt


from __future__ import unicode_literals
import frappe
import json
from frappe import _
from frappe.model.document import Document

class GeminiFunction(Document):
    """
    DocType for Gemini Function
    
    This class handles:
    - Function declarations for Gemini API
    - Implementation code for functions
    - Permission controls for function execution
    """
    
    def validate(self):
        """Validate function before saving"""
        self.validate_parameters()
        self.validate_implementation()
    
    def validate_parameters(self):
        """Validate parameters JSON"""
        if self.parameters:
            try:
                params = json.loads(self.parameters)
                
                # Check if parameters follow JSONSchema format
                if not isinstance(params, dict):
                    frappe.throw(_("Parameters must be a valid JSON object"))
                
                if "type" not in params:
                    frappe.throw(_("Parameters must include 'type' field"))
                
                if params["type"] != "object":
                    frappe.throw(_("Parameters 'type' must be 'object'"))
                
                if "properties" not in params:
                    frappe.throw(_("Parameters must include 'properties' field"))
                
            except ValueError:
                frappe.throw(_("Invalid parameters JSON"))
    
    def validate_implementation(self):
        """Validate implementation code"""
        if not self.implementation:
            frappe.throw(_("Implementation code is required"))
        
        # Basic security check for dangerous functions
        dangerous_functions = [
            "os.system", 
            "subprocess.call", 
            "subprocess.Popen", 
            "eval(", 
            "exec(", 
            "__import__"
        ]
        
        for func in dangerous_functions:
            if func in self.implementation:
                frappe.throw(_("Implementation contains potentially dangerous function: {0}").format(func))
    
    def execute(self, args, context=None):
        """
        Execute the function
        
        Args:
            args (dict): Arguments for the function
            context (dict, optional): Context information
            
        Returns:
            dict: Result of the function execution
        """
        try:
            # Create a restricted scope for execution
            local_scope = {
                "frappe": frappe,
                "args": args,
                "context": context or {},
                "result": None,
                "_": _,
                "json": json
            }
            
            # Execute the implementation
            exec(self.implementation, {}, local_scope)
            
            return {
                "error": False,
                "result": local_scope.get("result")
            }
            
        except Exception as e:
            frappe.log_error(f"Error executing Gemini function {self.name}: {str(e)}")
            return {
                "error": True,
                "message": str(e)
            }
