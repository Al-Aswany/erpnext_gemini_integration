# -*- coding: utf-8 -*-
# Copyright (c) 2025, Your Name and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe import _

class GeminiContextManager:
    """
    Context manager for Gemini Assistant
    
    This class handles:
    - Session-based conversation tracking
    - Auto-detection of active module/doctype
    - Context window management for long conversations
    - Relevant document retrieval based on context
    """
    
    def __init__(self, user=None):
        """
        Initialize the context manager
        
        Args:
            user (str, optional): The user. Defaults to current user.
        """
        self.user = user or frappe.session.user
    
    def get_conversation_history(self, session_id, max_messages=5):
        """
        Get conversation history for a session
        
        Args:
            session_id (str): The session ID
            max_messages (int, optional): Maximum number of messages to return
            
        Returns:
            list: List of messages in the conversation
        """
        try:
            # Get conversation by session_id
            conversation = frappe.get_all(
                "Gemini Conversation",
                filters={"session_id": session_id, "user": self.user},
                fields=["name"]
            )
            
            if not conversation:
                return []
            
            conversation_id = conversation[0].name
            
            # Get messages
            messages = frappe.get_all(
                "Gemini Message",
                filters={"conversation": conversation_id},
                fields=["timestamp", "role", "content", "actions_taken"],
                order_by="timestamp asc",
                limit=max_messages
            )
            
            # Process messages
            for msg in messages:
                if msg.actions_taken:
                    msg.actions_taken = json.loads(msg.actions_taken)
            
            return messages
            
        except Exception as e:
            frappe.log_error(f"Error getting conversation history: {str(e)}")
            return []
    
    def detect_active_context(self, page_info=None):
        """
        Detect active module, doctype, and document
        
        Args:
            page_info (dict, optional): Information about the current page
            
        Returns:
            dict: Context information
        """
        try:
            context = {
                "module": None,
                "doctype": None,
                "docname": None
            }
            
            if not page_info:
                return context
            
            # Extract information from page_info
            if page_info.get("doctype"):
                context["doctype"] = page_info.get("doctype")
                
                # Get module for doctype
                meta = frappe.get_meta(context["doctype"])
                context["module"] = meta.module
            
            if page_info.get("docname"):
                context["docname"] = page_info.get("docname")
                
                # Get document information if user has permission
                if context["doctype"] and frappe.has_permission(context["doctype"], "read", context["docname"]):
                    from erpnext_gemini_integration.utils.file_processor import get_document_context
                    context["document"] = get_document_context(context["doctype"], context["docname"])
            
            return context
            
        except Exception as e:
            frappe.log_error(f"Error detecting active context: {str(e)}")
            return {
                "module": None,
                "doctype": None,
                "docname": None
            }
    
    def get_relevant_documents(self, query, context=None):
        """
        Retrieve relevant documents based on query and context
        
        Args:
            query (str): The search query
            context (dict, optional): Context information
            
        Returns:
            list: List of relevant documents
        """
        try:
            results = []
            
            # If context includes a doctype, search within that doctype
            if context and context.get("doctype"):
                doctype = context.get("doctype")
                
                # Get searchable fields for the doctype
                meta = frappe.get_meta(doctype)
                search_fields = ["name"]
                
                for field in meta.fields:
                    if field.fieldtype in ["Data", "Text", "Small Text", "Long Text", 
                                          "Text Editor", "Code", "Link", "Select"]:
                        search_fields.append(field.fieldname)
                
                # Search for documents
                for field in search_fields:
                    docs = frappe.get_all(
                        doctype,
                        filters={field: ["like", f"%{query}%"]},
                        fields=["name", field],
                        limit=5
                    )
                    
                    for doc in docs:
                        if doc.name not in [r.get("name") for r in results]:
                            results.append({
                                "doctype": doctype,
                                "name": doc.name,
                                "field": field,
                                "value": doc.get(field)
                            })
            
            # If no results or no specific doctype, search globally
            if not results:
                from frappe.desk.search import search_widget
                global_results = search_widget(query, "", limit=10)
                
                for r in global_results:
                    results.append({
                        "doctype": r.get("doctype"),
                        "name": r.get("name"),
                        "value": r.get("content")
                    })
            
            return results
            
        except Exception as e:
            frappe.log_error(f"Error getting relevant documents: {str(e)}")
            return []
    
    def update_conversation(self, session_id, message, response):
        """
        Update conversation history
        
        Args:
            session_id (str): The session ID
            message (str): The user message
            response (dict): The response from Gemini
            
        Returns:
            str: Conversation ID
        """
        try:
            # Get or create conversation
            conversation = frappe.get_all(
                "Gemini Conversation",
                filters={"session_id": session_id, "user": self.user},
                fields=["name"]
            )
            
            if conversation:
                conversation_id = conversation[0].name
                conversation_doc = frappe.get_doc("Gemini Conversation", conversation_id)
            else:
                conversation_doc = frappe.new_doc("Gemini Conversation")
                conversation_doc.user = self.user
                conversation_doc.session_id = session_id
                conversation_doc.start_time = frappe.utils.now()
                conversation_doc.active = 1
                conversation_doc.insert()
                conversation_id = conversation_doc.name
            
            # Create user message
            user_message = frappe.new_doc("Gemini Message")
            user_message.conversation = conversation_id
            user_message.timestamp = frappe.utils.now()
            user_message.role = "user"
            user_message.content = message
            user_message.insert()
            
            # Create assistant message
            assistant_message = frappe.new_doc("Gemini Message")
            assistant_message.conversation = conversation_id
            assistant_message.timestamp = frappe.utils.now()
            assistant_message.role = "assistant"
            assistant_message.content = response.get("text", "")
            
            # Add function call if present
            if response.get("function_call"):
                assistant_message.actions_taken = json.dumps({
                    "function_call": response.get("function_call")
                })
            
            assistant_message.insert()
            
            # Update conversation last activity
            conversation_doc.end_time = frappe.utils.now()
            conversation_doc.save()
            
            return conversation_id
            
        except Exception as e:
            frappe.log_error(f"Error updating conversation: {str(e)}")
            return None
    
    def prune_conversation_history(self, conversation_id, max_messages=50):
        """
        Prune conversation history to prevent it from growing too large
        
        Args:
            conversation_id (str): The conversation ID
            max_messages (int, optional): Maximum number of messages to keep
            
        Returns:
            bool: Success or failure
        """
        try:
            # Count messages in conversation
            count = frappe.db.count("Gemini Message", {"conversation": conversation_id})
            
            if count <= max_messages:
                return True
            
            # Get oldest messages to delete
            to_delete = count - max_messages
            
            if to_delete <= 0:
                return True
            
            # Get oldest messages
            old_messages = frappe.get_all(
                "Gemini Message",
                filters={"conversation": conversation_id},
                fields=["name"],
                order_by="timestamp asc",
                limit=to_delete
            )
            
            # Delete oldest messages
            for msg in old_messages:
                frappe.delete_doc("Gemini Message", msg.name)
            
            return True
            
        except Exception as e:
            frappe.log_error(f"Error pruning conversation history: {str(e)}")
            return False
