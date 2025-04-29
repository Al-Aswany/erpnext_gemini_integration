# -*- coding: utf-8 -*-
# Copyright (c) 2025, Your Name and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe import _
from frappe.utils import cint
from erpnext_gemini_integration.api.gemini_wrapper import GeminiWrapper

@frappe.whitelist()
def process_message(message, conversation_id=None, files=None, context=None):
    """
    Process a message using the Gemini API
    
    Args:
        message (str): The message to process
        conversation_id (str, optional): The conversation ID
        files (str, optional): JSON string of file information
        context (str, optional): JSON string of context information
        
    Returns:
        dict: Response from Gemini API
    """
    try:
        # Check permissions
        if not frappe.has_permission("Gemini Assistant Settings", "read"):
            frappe.throw(_("You don't have permission to use the Gemini Assistant"))
        
        # Parse files and context
        file_list = json.loads(files) if files else None
        context_dict = json.loads(context) if context else {}
        
        # Get conversation history if conversation_id is provided
        if conversation_id:
            context_dict["history"] = _get_conversation_history(conversation_id)
        
        # Initialize Gemini wrapper
        gemini = GeminiWrapper()
        
        # Generate response
        response = gemini.generate_content(message, context=context_dict, files=file_list)
        
        # Handle function calls
        if not response.get("error") and response.get("function_call"):
            function_result = gemini.execute_function_call(response["function_call"], context=context_dict)
            
            if not function_result.get("error"):
                # Generate a follow-up response with the function result
                follow_up_context = context_dict.copy()
                follow_up_context["function_result"] = function_result.get("result")
                
                follow_up_prompt = f"I executed the function {response['function_call']['name']} and got the following result: {json.dumps(function_result.get('result'))}. Please provide a user-friendly response based on this result."
                
                follow_up_response = gemini.generate_content(follow_up_prompt, context=follow_up_context)
                
                if not follow_up_response.get("error"):
                    response["text"] = follow_up_response.get("text")
                    response["function_result"] = function_result.get("result")
        
        # Log the interaction
        message_id = gemini.log_interaction(
            message, 
            response, 
            conversation_id=conversation_id, 
            context=context_dict
        )
        
        # Add message_id to response
        response["message_id"] = message_id
        
        # Add conversation_id to response
        if conversation_id:
            response["conversation_id"] = conversation_id
        else:
            # Get the conversation_id from the logged message
            if message_id:
                msg_doc = frappe.get_doc("Gemini Message", message_id)
                response["conversation_id"] = msg_doc.conversation
        
        return response
        
    except Exception as e:
        frappe.log_error(f"Error processing message with Gemini API: {str(e)}")
        return {
            "error": True,
            "message": f"Error: {str(e)}"
        }

@frappe.whitelist()
def analyze_document(file_url, prompt, context=None):
    """
    Analyze a document using the Gemini API
    
    Args:
        file_url (str): The URL of the file to analyze
        prompt (str): The prompt for analysis
        context (str, optional): JSON string of context information
        
    Returns:
        dict: Response from Gemini API
    """
    try:
        # Check permissions
        if not frappe.has_permission("Gemini Assistant Settings", "read"):
            frappe.throw(_("You don't have permission to use the Gemini Assistant"))
        
        # Get file path from URL
        from frappe.utils.file_manager import get_file_path
        file_path = get_file_path(file_url)
        
        # Parse context
        context_dict = json.loads(context) if context else {}
        
        # Initialize Gemini wrapper
        gemini = GeminiWrapper()
        
        # Process document
        response = gemini.process_document(file_path, prompt)
        
        # Log the interaction
        gemini.log_interaction(
            f"Document analysis: {prompt}", 
            response, 
            context=context_dict
        )
        
        return response
        
    except Exception as e:
        frappe.log_error(f"Error analyzing document with Gemini API: {str(e)}")
        return {
            "error": True,
            "message": f"Error: {str(e)}"
        }

@frappe.whitelist()
def get_conversation_history(conversation_id, limit=10):
    """
    Get conversation history
    
    Args:
        conversation_id (str): The conversation ID
        limit (int, optional): Maximum number of messages to return
        
    Returns:
        list: List of messages in the conversation
    """
    try:
        # Check permissions
        if not frappe.has_permission("Gemini Conversation", "read"):
            frappe.throw(_("You don't have permission to access conversation history"))
        
        # Get conversation
        conversation = frappe.get_doc("Gemini Conversation", conversation_id)
        
        # Check if user has access to this conversation
        if conversation.user != frappe.session.user and not frappe.has_permission("Gemini Conversation", "write"):
            frappe.throw(_("You don't have permission to access this conversation"))
        
        # Get messages
        messages = frappe.get_all(
            "Gemini Message",
            filters={"conversation": conversation_id},
            fields=["name", "timestamp", "role", "content", "actions_taken"],
            order_by="timestamp desc",
            limit=cint(limit)
        )
        
        # Process messages
        for msg in messages:
            if msg.actions_taken:
                msg.actions_taken = json.loads(msg.actions_taken)
        
        return messages
        
    except Exception as e:
        frappe.log_error(f"Error getting conversation history: {str(e)}")
        return {
            "error": True,
            "message": f"Error: {str(e)}"
        }

@frappe.whitelist()
def record_feedback(message_id, feedback):
    """
    Record feedback for a message
    
    Args:
        message_id (str): The message ID
        feedback (str): The feedback (positive/negative)
        
    Returns:
        dict: Success/error message
    """
    try:
        # Check permissions
        if not frappe.has_permission("Gemini Message", "write"):
            frappe.throw(_("You don't have permission to provide feedback"))
        
        # Get message
        message = frappe.get_doc("Gemini Message", message_id)
        
        # Check if user has access to this message
        conversation = frappe.get_doc("Gemini Conversation", message.conversation)
        if conversation.user != frappe.session.user and not frappe.has_permission("Gemini Conversation", "write"):
            frappe.throw(_("You don't have permission to provide feedback for this message"))
        
        # Create feedback log
        feedback_log = frappe.new_doc("Gemini Feedback")
        feedback_log.message = message_id
        feedback_log.user = frappe.session.user
        feedback_log.timestamp = frappe.utils.now()
        feedback_log.feedback = feedback
        feedback_log.insert()
        
        return {
            "success": True,
            "message": _("Feedback recorded successfully")
        }
        
    except Exception as e:
        frappe.log_error(f"Error recording feedback: {str(e)}")
        return {
            "error": True,
            "message": f"Error: {str(e)}"
        }

def _get_conversation_history(conversation_id, max_messages=5):
    """
    Get conversation history in a format suitable for Gemini API
    
    Args:
        conversation_id (str): The conversation ID
        max_messages (int, optional): Maximum number of messages to include
        
    Returns:
        list: List of message objects for Gemini API
    """
    from google.generativeai.types import Content, Part
    
    try:
        # Get messages
        messages = frappe.get_all(
            "Gemini Message",
            filters={"conversation": conversation_id},
            fields=["role", "content"],
            order_by="timestamp asc",
            limit=max_messages
        )
        
        # Convert to Gemini format
        history = []
        for msg in messages:
            role = "user" if msg.role == "user" else "model"
            history.append(Content(role=role, parts=[Part(text=msg.content)]))
        
        return history
        
    except Exception as e:
        frappe.log_error(f"Error getting conversation history for Gemini: {str(e)}")
        return []
