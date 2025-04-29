# -*- coding: utf-8 -*-
# Copyright (c) 2025, Your Name and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import os
import json
import time
import requests
from frappe import _
from frappe.utils import cint, get_files_path
import frappe.utils.caching
from frappe import get_site_config
from frappe.utils.file_manager import get_file_path
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import logging

_logger = logging.getLogger(__name__)

class GeminiRateLimitError(Exception):
    """Exception raised when Gemini API rate limits are exceeded"""
    pass

class GeminiAPIError(Exception):
    """Exception raised for Gemini API errors"""
    pass

class GeminiWrapper:
    """
    Python wrapper for Google's Gemini API integration with ERPNext
    
    This class handles:
    - Authentication and API key management
    - Rate limit handling and request queuing
    - Multi-modal content processing
    - Error handling and retries
    - Function calling implementation
    """
    
    def __init__(self, user=None):
        """
        Initialize the Gemini API wrapper
        
        Args:
            user (str, optional): The user making the request. Defaults to current user.
        """
        self.user = user or frappe.session.user
        self.settings = self._get_settings()
        self.api_key = self._get_api_key()
        self.model = self.settings.model or "gemini-1.5-pro"
        self.max_tokens = cint(self.settings.max_tokens) or 8192
        self.temperature = float(self.settings.temperature or 0.7)
        self.safety_settings = self._parse_safety_settings()
        self.enable_grounding = self.settings.enable_grounding
        self.enable_function_calling = self.settings.enable_function_calling
        
        # Initialize the Gemini API
        genai.configure(api_key=self.api_key)
        
        # Set up rate limiting parameters
        self.request_count = 0
        self.request_reset_time = time.time() + 60  # Reset counter every minute
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        
    def _get_settings(self):
        """Get Gemini Assistant settings from DocType"""
        try:
            return frappe.get_single("Gemini Assistant Settings")
        except frappe.DoesNotExistError:
            frappe.log_error("Gemini Assistant Settings not found. Using defaults.")
            return frappe._dict({
                "model": "gemini-1.5-pro",
                "max_tokens": 8192,
                "temperature": 0.7,
                "safety_settings": "{}",
                "enable_grounding": 0,
                "enable_function_calling": 1
            })
    
    def _get_api_key(self):
        """
        Securely retrieve API key from settings
        
        Returns:
            str: The Gemini API key
        """
        if self.settings.api_key:
            return self.settings.get_password("api_key")
        
        # Fallback to site_config.json
        config = get_site_config()
        api_key = config.get("gemini_api_key")
        
        if not api_key:
            frappe.log_error("Gemini API key not configured")
            frappe.throw(_("Gemini API key not configured. Please set it in Gemini Assistant Settings."))
        
        return api_key
    
    def _parse_safety_settings(self):
        """
        Parse safety settings from JSON string in settings
        
        Returns:
            list: List of safety setting dictionaries
        """
        try:
            if not self.settings.safety_settings:
                return None
                
            settings = json.loads(self.settings.safety_settings)
            
            # Use a simpler format that's compatible with the current API
            safety_settings = []
            for category, threshold in settings.items():
                safety_settings.append({
                    "category": category,
                    "threshold": threshold
                })
            
            return safety_settings if safety_settings else None
            
        except Exception as e:
            frappe.log_error(f"Error parsing safety settings: {str(e)}")
            return None
    
    def _get_default_safety_settings(self):
        """
        Get default safety settings
        
        Returns:
            list: List of default safety setting dictionaries
        """
        # Return None to use Gemini API defaults
        return None
    
    def _check_rate_limits(self):
        """
        Check if rate limits have been exceeded
        
        Raises:
            GeminiRateLimitError: If rate limits are exceeded
        """
        current_time = time.time()
        
        # Reset counter if a minute has passed
        if current_time > self.request_reset_time:
            self.request_count = 0
            self.request_reset_time = current_time + 60
        
        # Check if we've exceeded the rate limit
        # Using conservative limits based on free tier
        if self.request_count >= 10:  # Assuming 10 RPM limit for safety
            raise GeminiRateLimitError("Gemini API rate limit exceeded. Please try again later.")
        
        self.request_count += 1
    
    def _prepare_content(self, prompt, files=None):
        """
        Prepare content for Gemini API request
        
        Args:
            prompt (str): The text prompt
            files (list, optional): List of file paths or file objects
            
        Returns:
            str or list: Content for Gemini API
        """
        # If no files, just return the prompt text
        if not files:
            return prompt
            
        # If files are provided, prepare multimodal content
        content_parts = [prompt]
        
        # Process files if provided
        if files:
            for file_info in files:
                try:
                    if isinstance(file_info, str):
                        # Assume it's a file path
                        file_path = file_info
                    elif isinstance(file_info, dict) and file_info.get("file_url"):
                        # Get file path from ERPNext file URL
                        file_path = get_file_path(file_info.get("file_url"))
                    else:
                        continue
                    
                    # Determine file type and process accordingly
                    mime_type = self._get_mime_type(file_path)
                    
                    if "image" in mime_type:
                        # Add image to content
                        image_data = genai.upload_file(file_path)
                        content_parts.append(image_data)
                    elif mime_type == "application/pdf":
                        # For PDFs, we'll use a utility function to extract text
                        from erpnext_gemini_integration.utils.file_processor import extract_text_from_pdf
                        pdf_text = extract_text_from_pdf(file_path)
                        content_parts.append(f"Content from PDF: {pdf_text}")
                    elif "text" in mime_type or mime_type == "application/csv":
                        with open(file_path, "r") as f:
                            file_text = f.read()
                        content_parts.append(f"Content from file: {file_text}")
                    
                except Exception as e:
                    frappe.log_error(f"Error processing file for Gemini API: {str(e)}")
        
        return content_parts
    
    def _get_mime_type(self, file_path):
        """
        Get MIME type of a file
        
        Args:
            file_path (str): Path to the file
            
        Returns:
            str: MIME type of the file
        """
        import mimetypes
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or "application/octet-stream"
    
    def _prepare_function_declarations(self, functions=None):
        """
        Prepare function declarations for Gemini API
        
        Args:
            functions (list, optional): List of function names to include
            
        Returns:
            list: List of function declarations
        """
        if not self.enable_function_calling:
            return None
            
        # Get all enabled functions from the database
        filters = {"enabled": 1}
        if functions:
            filters["name"] = ["in", functions]
            
        function_docs = frappe.get_all(
            "Gemini Function",
            filters=filters,
            fields=["name", "description", "parameters"]
        )
        
        declarations = []
        for func in function_docs:
            try:
                parameters = json.loads(func.parameters)
                declarations.append({
                    "name": func.name,
                    "description": func.description,
                    "parameters": parameters
                })
            except Exception as e:
                frappe.log_error(f"Error parsing function parameters for {func.name}: {str(e)}")
        
        return declarations if declarations else None
    
    def _prepare_generation_config(self, max_tokens=None, temperature=None):
        """
        Prepare generation config for Gemini API
        
        Args:
            max_tokens (int, optional): Maximum tokens to generate
            temperature (float, optional): Temperature for generation
            
        Returns:
            dict: Generation config
        """
        return {
            "max_output_tokens": max_tokens or self.max_tokens,
            "temperature": temperature or self.temperature,
            "top_p": 0.95,
            "top_k": 40
        }
    
    def _prepare_tools(self, functions=None):
        """
        Prepare tools configuration for Gemini API
        
        Args:
            functions (list, optional): List of function names to include
            
        Returns:
            list: List of tool configurations
        """
        tools = []
        
        # Add function calling tool if enabled
        function_declarations = self._prepare_function_declarations(functions)
        if function_declarations:
            tools.append({
                "function_declarations": function_declarations
            })
        
        return tools if tools else None
    
    def generate_content(self, prompt, context=None, files=None, functions=None, max_tokens=None, temperature=None):
        """
        Generate content using Gemini API
        
        Args:
            prompt (str): The text prompt
            context (dict, optional): Context information
            files (list, optional): List of file paths or file objects
            functions (list, optional): List of function names to include
            max_tokens (int, optional): Maximum tokens to generate
            temperature (float, optional): Temperature for generation
            
        Returns:
            dict: Response from Gemini API
        """
        try:
            # Check rate limits
            self._check_rate_limits()
            
            # Prepare content
            content = self._prepare_content(prompt, files)
            
            # Prepare generation config
            generation_config = self._prepare_generation_config(max_tokens, temperature)
            
            # Prepare safety settings
            safety_settings = self.safety_settings
            
            # Prepare tools
            tools = self._prepare_tools(functions)
            
            # Add context if provided
            history = None
            if context and context.get("history"):
                history = context.get("history")
            
            # Create model instance
            model = genai.GenerativeModel(model_name=self.model)
            
            # Generate content
            for attempt in range(self.max_retries):
                try:
                    if history:
                        response = model.generate_content(
                            contents=[*history, content],
                            generation_config=generation_config,
                            safety_settings=safety_settings,
                            tools=tools
                        )
                    else:
                        response = model.generate_content(
                            content,
                            generation_config=generation_config,
                            safety_settings=safety_settings,
                            tools=tools
                        )
                    
                    # Process response
                    return self._process_response(response)
                    
                except Exception as e:
                    if "RESOURCE_EXHAUSTED" in str(e) and attempt < self.max_retries - 1:
                        # Rate limit hit, wait and retry
                        time.sleep(self.retry_delay * (attempt + 1))
                        continue
                    else:
                        raise
            
            raise GeminiAPIError("Maximum retry attempts reached")
            
        except GeminiRateLimitError as e:
            frappe.log_error(f"Gemini API rate limit exceeded: {str(e)}")
            return {
                "error": True,
                "message": str(e)
            }
        except Exception as e:
            frappe.log_error(f"Error generating content with Gemini API: {str(e)}")
            return {
                "error": True,
                "message": f"Error: {str(e)}"
            }
    
    def _process_response(self, response):
        """
        Process response from Gemini API
        
        Args:
            response: Response object from Gemini API
            
        Returns:
            dict: Processed response
        """
        try:
            # Check if response was blocked
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                return {
                    "error": True,
                    "message": f"Content blocked: {response.prompt_feedback.block_reason}"
                }
            
            # Extract text content
            text = response.text if hasattr(response, 'text') else None
            
            # Check for function calls
            function_call = None
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and candidate.content:
                    for part in candidate.content.parts:
                        if hasattr(part, 'function_call') and part.function_call:
                            function_call = {
                                "name": part.function_call.name,
                                "args": json.loads(part.function_call.args)
                            }
            
            # Process citations if grounding is enabled
            citations = []
            if self.enable_grounding and hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and candidate.content:
                    for part in candidate.content.parts:
                        if hasattr(part, 'text') and part.text:
                            # Extract citations from text
                            pass
            
            # Return processed response
            result = {
                "text": text,
                "function_call": function_call,
                "citations": citations,
                "error": False
            }
            
            return result
            
        except Exception as e:
            frappe.log_error(f"Error processing Gemini API response: {str(e)}")
            return {
                "error": True,
                "message": f"Error processing response: {str(e)}"
            }


    def execute_function_call(self, function_call, context=None):
        """
        Execute a function call
        
        Args:
            function_call (dict): Function call information
            context (dict, optional): Context information
            
        Returns:
            dict: Result of function execution
        """
        try:
            # Get function details
            function_name = function_call.get("name")
            function_args = function_call.get("args", {})
            
            # Check if function exists
            function_doc = frappe.get_doc("Gemini Function", function_name)
            if not function_doc:
                return {
                    "error": True,
                    "message": f"Function {function_name} not found"
                }
            
            # Check if function is enabled
            if not function_doc.enabled:
                return {
                    "error": True,
                    "message": f"Function {function_name} is disabled"
                }
            
            # Check if user has permission to execute function
            from erpnext_gemini_integration.modules.security import GeminiSecurity
            security = GeminiSecurity(user=self.user)
            if not security.check_function_permission(function_name):
                return {
                    "error": True,
                    "message": f"Permission denied for function {function_name}"
                }
            
            # Check if function requires confirmation
            if function_doc.require_confirmation:
                # In a real implementation, this would trigger a confirmation flow
                # For now, we'll just log it
                frappe.log_error(f"Function {function_name} requires confirmation")
                return {
                    "error": True,
                    "message": f"Function {function_name} requires user confirmation"
                }
            
            # Execute function
            result = self._execute_function_code(function_doc.implementation, function_args, context)
            
            # Log function execution
            from erpnext_gemini_integration.modules.audit import GeminiAuditLog
            audit = GeminiAuditLog(user=self.user)
            audit.log_function_call(
                function_name=function_name,
                args=function_args,
                result=result,
                context=context
            )
            
            return {
                "error": False,
                "result": result
            }
            
        except Exception as e:
            frappe.log_error(f"Error executing function call: {str(e)}")
            return {
                "error": True,
                "message": f"Error executing function: {str(e)}"
            }
    
    def _execute_function_code(self, code, args, context):
        """
        Execute function code
        
        Args:
            code (str): Python code to execute
            args (dict): Function arguments
            context (dict): Context information
            
        Returns:
            dict: Result of function execution
        """
        try:
            # Create a safe execution environment
            globals_dict = {
                "frappe": frappe,
                "_": _,
                "json": json,
                "args": args,
                "context": context or {}
            }
            
            # Execute the code
            exec(code, globals_dict)
            
            # Get the result
            result = globals_dict.get("result", None)
            
            return result
        except Exception as e:
            frappe.log_error(f"Error executing function code: {str(e)}")
            raise
    
    def process_document(self, file_path, prompt, context=None):
        """
        Process a document using Gemini API
        
        Args:
            file_path (str): Path to the document
            prompt (str): Prompt for document processing
            context (dict, optional): Context information
            
        Returns:
            dict: Response from Gemini API
        """
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                return {
                    "error": True,
                    "message": f"File not found: {file_path}"
                }
            
            # Process document based on file type
            mime_type = self._get_mime_type(file_path)
            
            if mime_type == "application/pdf":
                return self._process_pdf(file_path, prompt, context)
            elif mime_type == "application/csv" or mime_type == "text/csv":
                return self._process_csv(file_path, prompt, context)
            elif "image" in mime_type:
                return self._process_image(file_path, prompt, context)
            elif "text" in mime_type:
                return self._process_text(file_path, prompt, context)
            else:
                return {
                    "error": True,
                    "message": f"Unsupported file type: {mime_type}"
                }
                
        except Exception as e:
            frappe.log_error(f"Error processing document: {str(e)}")
            return {
                "error": True,
                "message": f"Error processing document: {str(e)}"
            }
    
    def _process_pdf(self, file_path, prompt, context=None):
        """
        Process a PDF document
        
        Args:
            file_path (str): Path to the PDF document
            prompt (str): Prompt for document processing
            context (dict, optional): Context information
            
        Returns:
            dict: Response from Gemini API
        """
        try:
            # Extract text from PDF
            from erpnext_gemini_integration.utils.file_processor import extract_text_from_pdf
            pdf_text = extract_text_from_pdf(file_path)
            
            # Create a prompt with the PDF text
            full_prompt = f"{prompt}\n\nDocument content:\n{pdf_text}"
            
            # Generate content
            return self.generate_content(full_prompt, context)
            
        except Exception as e:
            frappe.log_error(f"Error processing PDF: {str(e)}")
            return {
                "error": True,
                "message": f"Error processing PDF: {str(e)}"
            }
    
    def _process_csv(self, file_path, prompt, context=None):
        """
        Process a CSV document
        
        Args:
            file_path (str): Path to the CSV document
            prompt (str): Prompt for document processing
            context (dict, optional): Context information
            
        Returns:
            dict: Response from Gemini API
        """
        try:
            # Read CSV file
            import csv
            
            with open(file_path, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)
            
            # Convert to string representation
            header = rows[0]
            data = rows[1:20]  # Limit to first 20 rows to avoid token limits
            
            csv_text = "Header: " + ", ".join(header) + "\n\n"
            csv_text += "Data (first 20 rows):\n"
            
            for row in data:
                csv_text += ", ".join(row) + "\n"
            
            # Create a prompt with the CSV text
            full_prompt = f"{prompt}\n\nCSV content:\n{csv_text}"
            
            # Generate content
            return self.generate_content(full_prompt, context)
            
        except Exception as e:
            frappe.log_error(f"Error processing CSV: {str(e)}")
            return {
                "error": True,
                "message": f"Error processing CSV: {str(e)}"
            }
    
    def _process_image(self, file_path, prompt, context=None):
        """
        Process an image
        
        Args:
            file_path (str): Path to the image
            prompt (str): Prompt for image processing
            context (dict, optional): Context information
            
        Returns:
            dict: Response from Gemini API
        """
        try:
            # Generate content with image
            return self.generate_content(prompt, context, files=[file_path])
            
        except Exception as e:
            frappe.log_error(f"Error processing image: {str(e)}")
            return {
                "error": True,
                "message": f"Error processing image: {str(e)}"
            }
    
    def _process_text(self, file_path, prompt, context=None):
        """
        Process a text document
        
        Args:
            file_path (str): Path to the text document
            prompt (str): Prompt for document processing
            context (dict, optional): Context information
            
        Returns:
            dict: Response from Gemini API
        """
        try:
            # Read text file
            with open(file_path, 'r') as f:
                text = f.read()
            
            # Create a prompt with the text
            full_prompt = f"{prompt}\n\nDocument content:\n{text}"
            
            # Generate content
            return self.generate_content(full_prompt, context)
            
        except Exception as e:
            frappe.log_error(f"Error processing text document: {str(e)}")
            return {
                "error": True,
                "message": f"Error processing text document: {str(e)}"
            }
    
    def create_conversation(self, title=None, context=None):
        """
        Create a new conversation
        
        Args:
            title (str, optional): Title for the conversation
            context (dict, optional): Context information
            
        Returns:
            str: Conversation ID
        """
        try:
            # Generate a title if not provided
            if not title:
                title = f"Conversation {frappe.utils.now_datetime().strftime('%Y-%m-%d %H:%M')}"
            
            # Create conversation document
            conversation = frappe.get_doc({
                "doctype": "Gemini Conversation",
                "title": title,
                "user": self.user,
                "context": json.dumps(context) if context else None
            })
            
            conversation.insert()
            
            return conversation.name
            
        except Exception as e:
            frappe.log_error(f"Error creating conversation: {str(e)}")
            return None
    
    def add_message(self, conversation_id, role, content, function_call=None):
        """
        Add a message to a conversation
        
        Args:
            conversation_id (str): Conversation ID
            role (str): Message role (user or assistant)
            content (str): Message content
            function_call (dict, optional): Function call information
            
        Returns:
            str: Message ID
        """
        try:
            # Create message document
            message = frappe.get_doc({
                "doctype": "Gemini Message",
                "conversation": conversation_id,
                "role": role,
                "content": content,
                "function_call": json.dumps(function_call) if function_call else None
            })
            
            message.insert()
            
            return message.name
            
        except Exception as e:
            frappe.log_error(f"Error adding message: {str(e)}")
            return None
    
    def get_conversation_history(self, conversation_id, limit=None):
        """
        Get conversation history
        
        Args:
            conversation_id (str): Conversation ID
            limit (int, optional): Maximum number of messages to retrieve
            
        Returns:
            list: List of messages
        """
        try:
            # Get messages from database
            filters = {"conversation": conversation_id}
            fields = ["name", "role", "content", "function_call", "creation"]
            order_by = "creation asc"
            
            if limit:
                messages = frappe.get_all(
                    "Gemini Message",
                    filters=filters,
                    fields=fields,
                    order_by=order_by,
                    limit=limit
                )
            else:
                messages = frappe.get_all(
                    "Gemini Message",
                    filters=filters,
                    fields=fields,
                    order_by=order_by
                )
            
            # Process messages
            history = []
            for msg in messages:
                message = {
                    "message_id": msg.name,
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.creation
                }
                
                if msg.function_call:
                    message["function_call"] = json.loads(msg.function_call)
                
                history.append(message)
            
            return history
            
        except Exception as e:
            frappe.log_error(f"Error getting conversation history: {str(e)}")
            return []
    
    def prepare_conversation_context(self, conversation_id, limit=10):
        """
        Prepare conversation context for Gemini API
        
        Args:
            conversation_id (str): Conversation ID
            limit (int, optional): Maximum number of messages to include
            
        Returns:
            dict: Context information
        """
        try:
            # Get conversation history
            history = self.get_conversation_history(conversation_id, limit)
            
            # Get conversation context
            conversation = frappe.get_doc("Gemini Conversation", conversation_id)
            context = json.loads(conversation.context) if conversation.context else {}
            
            # Format history for Gemini API
            formatted_history = []
            for msg in history:
                role = "user" if msg["role"] == "user" else "model"
                formatted_history.append({
                    "role": role,
                    "parts": [{"text": msg["content"]}]
                })
            
            # Add history to context
            context["history"] = formatted_history
            
            return context
            
        except Exception as e:
            frappe.log_error(f"Error preparing conversation context: {str(e)}")
            return {}
    
    def log_interaction(self, prompt, response, conversation_id=None, context=None):
        """
        Log an interaction with Gemini API
        
        Args:
            prompt (str): The prompt sent to Gemini
            response (dict): The response from Gemini
            conversation_id (str, optional): The conversation ID
            context (dict, optional): Context information
            
        Returns:
            str: Message ID
        """
        try:
            # Create or get conversation
            if not conversation_id:
                conversation_id = self.create_conversation(context=context)
            
            if not conversation_id:
                return None
            
            # Add user message
            user_message_id = self.add_message(conversation_id, "user", prompt)
            
            # Add assistant message
            assistant_message_id = None
            if response and not response.get("error"):
                function_call = response.get("function_call")
                assistant_message_id = self.add_message(
                    conversation_id, 
                    "assistant", 
                    response.get("text", ""), 
                    function_call
                )
            
            # Return the assistant message ID
            return assistant_message_id
            
        except Exception as e:
            frappe.log_error(f"Error logging interaction: {str(e)}")
            return None
