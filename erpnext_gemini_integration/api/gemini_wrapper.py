# -*- coding: utf-8 -*-
# Copyright (c) 2025, Your Name and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
# import os # Unused
import json
import time
# import requests # Unused
import random # Added for jitter in retry logic
from frappe import _
# Combine imports from both branches, keeping caching and get_files_path
from frappe.utils import cint, get_files_path, get_site_config
import frappe.utils.caching 
from frappe.utils.file_manager import get_file_path
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold # Keep this for potential future use or reference, though parsing changed
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
        # Use model from origin/main
        self.model = self.settings.model or "gemini-1.5-pro" 
        self.max_tokens = cint(self.settings.max_tokens) or 8192
        self.temperature = float(self.settings.temperature or 0.7)
        # Use safety settings parsing from origin/main
        self.safety_settings = self._parse_safety_settings() 
        self.enable_grounding = self.settings.enable_grounding # Keep grounding flag, though tools prep changed
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
            # Use model from origin/main in defaults
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
    
    # Use safety settings parsing from origin/main
    def _parse_safety_settings(self):
        """
        Parse safety settings from JSON string in settings
        
        Returns:
            list: List of safety setting dictionaries or None
        """
        try:
            if not self.settings.safety_settings:
                return self._get_default_safety_settings()
                
            settings = json.loads(self.settings.safety_settings)
            
            # Use a simpler format that's compatible with the current API
            safety_settings = []
            for category, threshold in settings.items():
                # Basic validation (can be enhanced)
                if isinstance(category, str) and isinstance(threshold, str):
                    safety_settings.append({
                        "category": category.upper().replace("HARM_CATEGORY_", ""), # Attempt to normalize if needed
                        "threshold": threshold.upper().replace("BLOCK_", "") # Attempt to normalize if needed
                    })
                else:
                     _logger.warning(f"Skipping invalid safety setting entry: {category}:{threshold}")

            return safety_settings if safety_settings else self._get_default_safety_settings()
            
        except Exception as e:
            frappe.log_error(f"Error parsing safety settings: {str(e)}")
            return self._get_default_safety_settings()

    # Use default safety settings logic from origin/main
    def _get_default_safety_settings(self):
        """
        Get default safety settings (use API defaults by returning None)
        
        Returns:
            None 
        """
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
    
    # Use content preparation from origin/main
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
                        _logger.warning(f"Skipping invalid file info: {file_info}")
                        continue
                    
                    # Determine file type and process accordingly
                    mime_type = self._get_mime_type(file_path)
                    
                    if "image" in mime_type:
                        # Add image to content using upload_file
                        _logger.info(f"Uploading image file: {file_path}")
                        uploaded_file = genai.upload_file(path=file_path)
                        # Short delay after upload might be needed sometimes
                        time.sleep(1) 
                        content_parts.append(uploaded_file)
                        _logger.info(f"Appended uploaded image: {uploaded_file.name}")
                    elif mime_type == "application/pdf":
                        # For PDFs, extract text (consider using genai.upload_file if API supports it directly)
                        from erpnext_gemini_integration.utils.file_processor import extract_text_from_pdf
                        pdf_text = extract_text_from_pdf(file_path)
                        content_parts.append(f"\n\n--- Content from PDF ({os.path.basename(file_path)}) ---\n{pdf_text}\n--- End PDF Content ---")
                    elif "text" in mime_type or mime_type == "application/csv":
                        # For text/csv, include content directly
                        with open(file_path, "r", encoding='utf-8', errors='ignore') as f:
                            file_text = f.read()
                        content_parts.append(f"\n\n--- Content from file ({os.path.basename(file_path)}) ---\n{file_text}\n--- End File Content ---")
                    else:
                        _logger.warning(f"Skipping unsupported file type {mime_type} for file: {file_path}")
                        
                except Exception as e:
                    # Log error but continue processing other files
                    frappe.log_error(f"Error processing file {file_info} for Gemini API: {str(e)}")
        
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
        # Ensure os is imported if using os.path.basename above
        import os 
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
    
    # Use generation config format from origin/main
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
    
    # Use tools preparation from origin/main (no grounding)
    def _prepare_tools(self, functions=None):
        """
        Prepare tools configuration for Gemini API
        
        Args:
            functions (list, optional): List of function names to include
            
        Returns:
            list: List of tool configurations or None
        """
        tools = []
        
        # Add function calling tool if enabled
        function_declarations = self._prepare_function_declarations(functions)
        if function_declarations:
            tools.append({
                "function_declarations": function_declarations
            })
        
        # Grounding retrieval removed as per origin/main merge
        
        return tools if tools else None
    
    def generate_content(self, prompt, context=None, files=None, functions=None, max_tokens=None, temperature=None):
        """
        Generate content using Gemini API
        
        Args:
            prompt (str): The text prompt
            context (dict, optional): Context information (e.g., history)
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
            
            # Prepare content (handles multimodal)
            content = self._prepare_content(prompt, files)
            
            # Prepare generation config
            generation_config = self._prepare_generation_config(max_tokens, temperature)
            
            # Prepare safety settings
            safety_settings = self.safety_settings
            
            # Prepare tools
            tools = self._prepare_tools(functions)
            
            # Prepare history if provided in context
            history = None
            if context and context.get("history"):
                # Ensure history format is compatible (list of Content objects)
                # This might need adjustment based on how history is stored/retrieved
                history = context.get("history") 
                # Example conversion if history is stored as simple dicts:
                # history = [genai.types.Content(role=msg['role'], parts=[msg['content']]) for msg in context.get("history")]
            
            # Use model instantiation from origin/main
            model = genai.GenerativeModel(model_name=self.model)
            
            # Generate content
            for attempt in range(self.max_retries):
                try:
                    _logger.debug(f"Generating content with Gemini. Attempt {attempt + 1}")
                    _logger.debug(f"Content: {content}")
                    _logger.debug(f"History: {history}")
                    _logger.debug(f"Tools: {tools}")
                    _logger.debug(f"Safety Settings: {safety_settings}")
                    _logger.debug(f"Generation Config: {generation_config}")

                    if history:
                        # Start chat if history exists
                        chat = model.start_chat(history=history)
                        response = chat.send_message(
                            content=content,
                            generation_config=generation_config,
                            safety_settings=safety_settings,
                            tools=tools
                        )
                    else:
                        # Use generate_content for single turn
                        response = model.generate_content(
                            contents=content, # Note: generate_content expects 'contents'
                            generation_config=generation_config,
                            safety_settings=safety_settings,
                            tools=tools
                        )
                    
                    _logger.debug(f"Received response from Gemini: {response}")
                    # Process response
                    return self._process_response(response)
                    
                except Exception as e:
                    _logger.error(f"Error during Gemini API call (Attempt {attempt + 1}): {str(e)}", exc_info=True)
                    if "RESOURCE_EXHAUSTED" in str(e) and attempt < self.max_retries - 1:
                        # Rate limit hit, wait with exponential backoff and retry
                        wait_time = self.retry_delay * (2 ** attempt) + (random.random() * 0.1) # Add jitter
                        _logger.warning(f"Gemini API rate limit hit. Retrying in {wait_time:.2f} seconds (Attempt {attempt + 1}/{self.max_retries}).")
                        time.sleep(wait_time)
                        continue
                    # Handle potential API changes or other errors
                    elif "FunctionDeclarations" in str(e) or "Tool" in str(e):
                         _logger.error("Potential Tool/FunctionDeclaration format issue. Check API documentation.")
                         # Fallback or specific error handling might be needed here
                         raise GeminiAPIError(f"API structure error: {str(e)}")
                    else:
                        # Re-raise other exceptions
                        raise
            
            # If loop completes without success
            raise GeminiAPIError("Maximum retry attempts reached after API errors.")
            
        except GeminiRateLimitError as e:
            frappe.log_error(f"Gemini API rate limit exceeded: {str(e)}")
            return {
                "error": True,
                "message": _("Gemini API rate limit exceeded. Please try again after a short while.")
            }
        except GeminiAPIError as e:
             frappe.log_error(f"Gemini API Error: {str(e)}")
             return {
                "error": True,
                "message": _("A specific Gemini API error occurred: {0}").format(str(e))
            }
        except Exception as e:
            frappe.log_error(f"Unexpected error generating content with Gemini API: {str(e)}", exc_info=True)
            return {
                "error": True,
                "message": _("An unexpected error occurred while communicating with the Gemini API. Please check the logs for details.")
            }
    
    # Use response processing from origin/main (function call extraction, no citations)
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
            # Accessing prompt_feedback might differ based on API version/response structure
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                _logger.warning(f"Gemini response blocked. Reason: {response.prompt_feedback.block_reason}")
                return {
                    "error": True,
                    "message": _("Content blocked by safety settings. Reason: {0}").format(response.prompt_feedback.block_reason)
                }
            
            # Extract text content safely
            text = None
            try:
                text = response.text
            except ValueError as ve:
                 _logger.warning(f"Could not extract text directly from response (might contain function call): {ve}")
                 # Attempt to extract text from parts if direct access fails
                 if hasattr(response, 'candidates') and response.candidates:
                     candidate = response.candidates[0]
                     if hasattr(candidate, 'content') and candidate.content and hasattr(candidate.content, 'parts'):
                         text_parts = [part.text for part in candidate.content.parts if hasattr(part, 'text')]
                         if text_parts:
                             text = " ".join(text_parts)
            except Exception as e:
                 _logger.error(f"Unexpected error extracting text from response: {e}")

            # Check for function calls using origin/main logic
            function_call = None
            function_name = None
            function_args = None
            try:
                if hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'content') and candidate.content and hasattr(candidate.content, 'parts'):
                        for part in candidate.content.parts:
                            if hasattr(part, 'function_call') and part.function_call:
                                fc = part.function_call
                                function_name = fc.name
                                # Args might be a Struct/dict-like object, convert to dict
                                function_args = dict(fc.args) 
                                function_call = {
                                    "name": function_name,
                                    "args": function_args
                                }
                                _logger.info(f"Detected function call: {function_name} with args: {function_args}")
                                break # Assuming only one function call per response part
            except Exception as e:
                _logger.error(f"Error extracting function call from response: {e}")

            # Citations processing removed as per origin/main merge
            citations = [] 
            
            # Return processed response
            result = {
                "text": text or "" , # Ensure text is not None
                "function_call": function_call,
                "citations": citations,
                "error": False
            }
            
            # If only a function call is returned, text might be empty. Add a placeholder.
            if function_call and not text:
                result["text"] = _("Attempting to execute function: {0}").format(function_name)

            return result
            
        except Exception as e:
            frappe.log_error(f"Error processing Gemini API response: {str(e)}", exc_info=True)
            return {
                "error": True,
                "message": _("An error occurred while processing the Gemini API response. Please check the logs for details.")
            }


    def execute_function_call(self, function_call, context=None):
        """
        Execute a function call
        
        Args:
            function_call (dict): Function call information { "name": str, "args": dict }
            context (dict, optional): Context information
            
        Returns:
            dict: Result of function execution { "error": bool, "result": any } or { "error": bool, "message": str }
        """
        try:
            # Get function details
            function_name = function_call.get("name")
            function_args = function_call.get("args", {})
            
            if not function_name:
                 return {"error": True, "message": _("Function call name missing.")}

            # Check if function exists
            try:
                function_doc = frappe.get_doc("Gemini Function", function_name)
            except frappe.DoesNotExistError:
                 _logger.error(f"Gemini Function DocType not found: {function_name}")
                 return {
                    "error": True,
                    "message": _("Function definition ") + f"\"{function_name}\"" + _(" not found.")
                }
            
            # Check if function is enabled
            if not function_doc.enabled:
                _logger.warning(f"Attempted to call disabled function: {function_name}")
                return {
                    "error": True,
                    "message": _("Function ") + f"\"{function_name}\"" + _(" is currently disabled.")
                }
            
            # Check if user has permission to execute function
            # Ensure security module exists and is importable
            try:
                from erpnext_gemini_integration.modules.security import GeminiSecurity
                security = GeminiSecurity(user=self.user)
                if not security.check_function_permission(function_name):
                    _logger.warning(f"Permission denied for user {self.user} to execute function {function_name}")
                    return {
                        "error": True,
                        "message": _("You do not have permission to execute the function ") + f"\"{function_name}\"" + _(".")
                    }
            except ImportError:
                 _logger.error("GeminiSecurity module not found. Skipping permission check.")
                 # Decide if this should be a hard failure or just a warning
                 # return {"error": True, "message": _("Security module missing, cannot verify function permissions.")}

            
            # Check if function requires confirmation
            if function_doc.require_confirmation:
                # In a real implementation, this would trigger a confirmation flow
                # For now, we'll just log it and return an error indicating confirmation needed
                _logger.info(f"Function {function_name} requires user confirmation.")
                return {
                    "error": True,
                    "needs_confirmation": True, # Add a flag for UI handling
                    "message": _("Function ") + f"\"{function_name}\"" + _(" requires user confirmation before execution.")
                }
            
            # Execute function
            result = None
            # Check if it's a pre-packaged ERPNext function first
            try:
                from erpnext_gemini_integration.modules.erpnext_functions import ERPNext_FUNCTIONS
                if function_name in ERPNext_FUNCTIONS:
                    _logger.info(f"Executing pre-packaged function: {function_name}")
                    func_to_call = ERPNext_FUNCTIONS[function_name]
                    # Ensure args is a dict before unpacking
                    result = func_to_call(**(function_args or {})) 
                elif function_doc.implementation: # Fallback to executing code from doctype (DEPRECATED)
                    _logger.warning(f"Executing function {function_name} from DocType implementation field. This approach is deprecated - consider moving implementation to erpnext_functions.py module for better maintainability and security.")
                    result = self._execute_function_code(function_doc.implementation, function_args, context)
                else:
                    _logger.error(f"Function {function_name} has no implementation defined.")
                    return {
                        "error": True,
                        "message": _("Function ") + f"\"{function_name}\"" + _(" has no implementation defined.")
                    }
            except ImportError:
                 _logger.error("erpnext_functions module not found. Cannot execute pre-packaged functions.")
                 if not function_doc.implementation:
                     return {"error": True, "message": _("Function implementation module missing and no fallback defined.")}
                 # If fallback exists, log warning and continue
                 _logger.warning("Falling back to DocType implementation due to missing erpnext_functions module.")
                 result = self._execute_function_code(function_doc.implementation, function_args, context)

            # Log function execution (ensure audit module exists)
            try:
                from erpnext_gemini_integration.modules.audit import GeminiAuditLog
                audit = GeminiAuditLog(user=self.user)
                audit.log_function_call(
                    function_name=function_name,
                    args=function_args,
                    result=result,
                    context=context
                )
            except ImportError:
                 _logger.warning("GeminiAuditLog module not found. Skipping function call audit logging.")
            
            # Return the result in the format expected by Gemini API for function results
            return {
                "error": False,
                "result": {
                     "functionResponse": {
                        "name": function_name,
                        "response": {
                            # Gemini expects the result within a 'content' field typically
                            "content": result 
                        }
                    }
                }
            }
            
        except Exception as e:
            frappe.log_error(f"Error executing function call {function_name}: {str(e)}", exc_info=True)
            # Return error in the format expected by Gemini API if possible
            return {
                "error": True,
                # "message": f"Error executing function: {str(e)}" # Keep internal message
                "result": { # Provide error structure for Gemini
                     "functionResponse": {
                        "name": function_name,
                        "response": {
                            "content": f"Error executing function: {str(e)}" 
                        }
                    }
                }
            }
    
    # This method executes code directly from a DocType field - keep the enhanced warning
    def _execute_function_code(self, code, args, context):
        """
        Execute function code defined in DocType (DEPRECATED - Use erpnext_functions.py)
        
        Args:
            code (str): Python code to execute
            args (dict): Function arguments
            context (dict): Context information
            
        Returns:
            any: Result of function execution
        """
        try:
            # Create a restricted execution environment if possible
            # For now, using basic exec with limited globals
            globals_dict = {
                "frappe": frappe,
                "_": _,
                "json": json,
                "args": args or {},
                "context": context or {},
                "result": None # Initialize result
            }
            
            # Execute the code
            exec(code, globals_dict)
            
            # Get the result
            result = globals_dict.get("result")
            
            return result
        except Exception as e:
            frappe.log_error(f"Error executing function code from DocType field: {str(e)}", exc_info=True)
            raise # Re-raise the exception to be caught by execute_function_call
    
    # process_document and helpers removed as per cleanup plan

    def log_interaction(self, prompt, response, conversation_id=None, context=None):
        """
        Log interaction with Gemini API
        
        Args:
            prompt (str): The prompt sent to the API
            response (dict): The processed response from the API
            conversation_id (str, optional): Conversation ID
            context (dict, optional): Context information
            
        Returns:
            str: Message ID of the logged interaction
        """
        try:
            # Ensure conversation exists or create one
            if not conversation_id:
                conversation_id = self.create_conversation(context=context)
                if not conversation_id:
                    raise Exception("Failed to create conversation for logging")
            
            # Log user message
            user_message = frappe.get_doc({
                "doctype": "Gemini Message",
                "conversation": conversation_id,
                "role": "user",
                "content": prompt, # Log the original prompt (or masked if needed)
                "context": json.dumps(context) if context else None
            })
            user_message.insert(ignore_permissions=True)
            
            # Log assistant message
            assistant_message = frappe.get_doc({
                "doctype": "Gemini Message",
                "conversation": conversation_id,
                "role": "assistant",
                "content": response.get("text", ""),
                "function_call": json.dumps(response.get("function_call")) if response.get("function_call") else None,
                "citations": json.dumps(response.get("citations")) if response.get("citations") else None,
                "is_error": 1 if response.get("error") else 0,
                "error_message": response.get("message") if response.get("error") else None
            })
            assistant_message.insert(ignore_permissions=True)
            
            # Return the ID of the assistant's message as the primary log entry ID
            return assistant_message.name
            
        except Exception as e:
            frappe.log_error(f"Error logging Gemini interaction: {str(e)}", exc_info=True)
            return None

    def create_conversation(self, title=None, context=None):
        """
        Create a new conversation
        
        Args:
            title (str, optional): Title for the conversation
            context (dict, optional): Context information
            
        Returns:
            str: Conversation ID or None if failed
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
            
            conversation.insert(ignore_permissions=True) # Use ignore_permissions if called from background jobs
            
            _logger.info(f"Created Gemini Conversation: {conversation.name}")
            return conversation.name
            
        except Exception as e:
            frappe.log_error(f"Error creating conversation: {str(e)}", exc_info=True)
            return None
    
    # Removed add_message, get_conversation_history, prepare_conversation_context as they seem redundant
    # The logging function now handles message creation within a conversation.
    # History preparation should happen in the calling function (e.g., chat_api.py) before calling generate_content.

# Utility function (can be moved to utils if needed)
@frappe.whitelist()
@frappe.utils.caching.regional_cache("erpnext_gemini_integration:get_enabled_functions")
def get_enabled_functions_for_client():
    """Get a list of enabled functions suitable for client-side display."""
    try:
        functions = frappe.get_all(
            "Gemini Function",
            filters={"enabled": 1},
            fields=["name", "description", "client_prompt_suggestion"]
        )
        return functions
    except Exception as e:
        frappe.log_error(f"Error fetching enabled Gemini functions: {str(e)}")
        return []

