# -*- coding: utf-8 -*-
# Copyright (c) 2025, Al-Aswany and contributors
# For license information, please see license.txt

import frappe
import os
import json
import base64
import tempfile
import mimetypes
from frappe import _
from frappe.utils import now_datetime, cint
from ..gemini.exceptions import GeminiFileProcessingError

class FileProcessor:
    """
    File processor for handling documents and attachments in Gemini integration.
    
    This class provides methods for processing various file types (PDFs, CSVs, images)
    and preparing them for analysis by the Gemini API.
    """
    
    def __init__(self):
        """Initialize the file processor."""
        self.settings = frappe.get_single("Gemini Assistant Settings")
        self.supported_file_types = {
            'image': ['jpg', 'jpeg', 'png', 'gif', 'webp'],
            'document': ['pdf', 'txt', 'csv', 'json', 'xlsx', 'docx'],
            'code': ['py', 'js', 'html', 'css', 'json', 'xml']
        }
        self.temp_files = []
    
    def process_file(self, file_path=None, file_url=None, file_content=None, file_type=None):
        """
        Process a file for analysis by Gemini.
        
        Args:
            file_path (str, optional): Local file path
            file_url (str, optional): File URL
            file_content (bytes, optional): Raw file content
            file_type (str, optional): File type hint
            
        Returns:
            dict: Processed file data
        """
        try:
            # Check if file processing is enabled
            if not self.settings.enable_file_processing:
                return {"error": "File processing is disabled", "success": False}
            
            # Get file content
            content, detected_type = self._get_file_content(file_path, file_url, file_content, file_type)
            
            if not content:
                return {"error": "Could not retrieve file content", "success": False}
            
            # Process based on file type
            if detected_type in self.supported_file_types['image']:
                return self._process_image(content, detected_type)
            elif detected_type in self.supported_file_types['document']:
                return self._process_document(content, detected_type)
            elif detected_type in self.supported_file_types['code']:
                return self._process_code(content, detected_type)
            else:
                return {"error": f"Unsupported file type: {detected_type}", "success": False}
                
        except Exception as e:
            frappe.log_error(f"Error processing file: {str(e)}")
            raise GeminiFileProcessingError(f"Error processing file: {str(e)}")
        finally:
            # Clean up temporary files
            self._cleanup_temp_files()
    
    def process_attachment(self, doctype, docname, file_field=None, attachment_name=None):
        """
        Process an attachment from a document.
        
        Args:
            doctype (str): DocType of the document
            docname (str): Name of the document
            file_field (str, optional): Field name containing the file
            attachment_name (str, optional): Name of the attachment
            
        Returns:
            dict: Processed attachment data
        """
        try:
            # Check if file processing is enabled
            if not self.settings.enable_file_processing:
                return {"error": "File processing is disabled", "success": False}
            
            # Get attachment
            if file_field:
                # Get file from document field
                doc = frappe.get_doc(doctype, docname)
                if not hasattr(doc, file_field) or not doc.get(file_field):
                    return {"error": f"No file found in field {file_field}", "success": False}
                
                file_url = doc.get(file_field)
            elif attachment_name:
                # Get specific attachment
                attachments = frappe.get_all(
                    "File",
                    filters={
                        "attached_to_doctype": doctype,
                        "attached_to_name": docname,
                        "file_name": attachment_name
                    },
                    fields=["file_url"]
                )
                
                if not attachments:
                    return {"error": f"Attachment {attachment_name} not found", "success": False}
                
                file_url = attachments[0].file_url
            else:
                # Get the latest attachment
                attachments = frappe.get_all(
                    "File",
                    filters={
                        "attached_to_doctype": doctype,
                        "attached_to_name": docname
                    },
                    fields=["file_url"],
                    order_by="creation desc",
                    limit=1
                )
                
                if not attachments:
                    return {"error": "No attachments found", "success": False}
                
                file_url = attachments[0].file_url
            
            # Process the file
            return self.process_file(file_url=file_url)
            
        except Exception as e:
            frappe.log_error(f"Error processing attachment: {str(e)}")
            raise GeminiFileProcessingError(f"Error processing attachment: {str(e)}")
    
    def extract_text_from_document(self, file_path=None, file_url=None, file_content=None):
        """
        Extract text content from a document file.
        
        Args:
            file_path (str, optional): Local file path
            file_url (str, optional): File URL
            file_content (bytes, optional): Raw file content
            
        Returns:
            str: Extracted text content
        """
        try:
            # Get file content
            content, detected_type = self._get_file_content(file_path, file_url, file_content)
            
            if not content:
                return ""
            
            # Process based on file type
            if detected_type == 'pdf':
                return self._extract_text_from_pdf(content)
            elif detected_type == 'txt':
                return content.decode('utf-8', errors='ignore')
            elif detected_type == 'csv':
                return self._extract_text_from_csv(content)
            elif detected_type == 'json':
                return self._extract_text_from_json(content)
            elif detected_type in ['xlsx', 'docx']:
                return self._extract_text_from_office(content, detected_type)
            else:
                return ""
                
        except Exception as e:
            frappe.log_error(f"Error extracting text from document: {str(e)}")
            return ""
    
    def _get_file_content(self, file_path=None, file_url=None, file_content=None, file_type=None):
        """
        Get file content from various sources.
        
        Args:
            file_path (str, optional): Local file path
            file_url (str, optional): File URL
            file_content (bytes, optional): Raw file content
            file_type (str, optional): File type hint
            
        Returns:
            tuple: (file_content, file_type)
        """
        content = None
        detected_type = file_type
        
        # Get content from file path
        if file_path and os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                content = f.read()
            
            if not detected_type:
                detected_type = file_path.split('.')[-1].lower()
        
        # Get content from file URL
        elif file_url:
            if file_url.startswith('/'):
                # Local file URL
                site_path = frappe.get_site_path()
                full_path = os.path.join(site_path, file_url.lstrip('/'))
                
                if os.path.exists(full_path):
                    with open(full_path, 'rb') as f:
                        content = f.read()
            else:
                # Remote URL
                import requests
                response = requests.get(file_url)
                content = response.content
            
            if not detected_type:
                detected_type = file_url.split('.')[-1].lower()
        
        # Use provided content
        elif file_content:
            content = file_content
            
            if not detected_type:
                # Try to detect type from content
                import magic
                mime = magic.Magic(mime=True)
                mime_type = mime.from_buffer(content)
                
                # Convert MIME type to extension
                extension = mimetypes.guess_extension(mime_type)
                if extension:
                    detected_type = extension.lstrip('.').lower()
        
        return content, detected_type
    
    def _process_image(self, content, file_type):
        """
        Process an image file.
        
        Args:
            content (bytes): Image file content
            file_type (str): Image file type
            
        Returns:
            dict: Processed image data
        """
        try:
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_type}')
            temp_file.write(content)
            temp_file.close()
            
            # Add to temp files list for cleanup
            self.temp_files.append(temp_file.name)
            
            # Get image dimensions
            from PIL import Image
            img = Image.open(temp_file.name)
            width, height = img.size
            
            # Log the processing
            self._log_file_processing('image', file_type, len(content))
            
            return {
                "file_path": temp_file.name,
                "file_type": file_type,
                "mime_type": f"image/{file_type}",
                "width": width,
                "height": height,
                "size": len(content),
                "success": True
            }
            
        except Exception as e:
            frappe.log_error(f"Error processing image: {str(e)}")
            return {"error": f"Error processing image: {str(e)}", "success": False}
    
    def _process_document(self, content, file_type):
        """
        Process a document file.
        
        Args:
            content (bytes): Document file content
            file_type (str): Document file type
            
        Returns:
            dict: Processed document data
        """
        try:
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_type}')
            temp_file.write(content)
            temp_file.close()
            
            # Add to temp files list for cleanup
            self.temp_files.append(temp_file.name)
            
            # Extract text based on file type
            text = ""
            if file_type == 'pdf':
                text = self._extract_text_from_pdf(content)
            elif file_type == 'txt':
                text = content.decode('utf-8', errors='ignore')
            elif file_type == 'csv':
                text = self._extract_text_from_csv(content)
            elif file_type == 'json':
                text = self._extract_text_from_json(content)
            elif file_type in ['xlsx', 'docx']:
                text = self._extract_text_from_office(content, file_type)
            
            # Log the processing
            self._log_file_processing('document', file_type, len(content))
            
            return {
                "file_path": temp_file.name,
                "file_type": file_type,
                "mime_type": mimetypes.guess_type(f"file.{file_type}")[0],
                "text_content": text,
                "size": len(content),
                "success": True
            }
            
        except Exception as e:
            frappe.log_error(f"Error processing document: {str(e)}")
            return {"error": f"Error processing document: {str(e)}", "success": False}
    
    def _process_code(self, content, file_type):
        """
        Process a code file.
        
        Args:
            content (bytes): Code file content
            file_type (str): Code file type
            
        Returns:
            dict: Processed code data
        """
        try:
            # Decode content
            text = content.decode('utf-8', errors='ignore')
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_type}')
            temp_file.write(content)
            temp_file.close()
            
            # Add to temp files list for cleanup
            self.temp_files.append(temp_file.name)
            
            # Log the processing
            self._log_file_processing('code', file_type, len(content))
            
            return {
                "file_path": temp_file.name,
                "file_type": file_type,
                "mime_type": mimetypes.guess_type(f"file.{file_type}")[0],
                "text_content": text,
                "size": len(content),
                "success": True
            }
            
        except Exception as e:
            frappe.log_error(f"Error processing code: {str(e)}")
            return {"error": f"Error processing code: {str(e)}", "success": False}
    
    def _extract_text_from_pdf(self, content):
        """
        Extract text from a PDF file.
        
        Args:
            content (bytes): PDF file content
            
        Returns:
            str: Extracted text
        """
        try:
            import PyPDF2
            from io import BytesIO
            
            # Create PDF reader
            pdf_file = BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            # Extract text from all pages
            text = ""
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n\n"
            
            return text
            
        except Exception as e:
            frappe.log_error(f"Error extracting text from PDF: {str(e)}")
            return ""
    
    def _extract_text_from_csv(self, content):
        """
        Extract text from a CSV file.
        
        Args:
            content (bytes): CSV file content
            
        Returns:
            str: Extracted text
        """
        try:
            import csv
            from io import StringIO
            
            # Decode content
            text = content.decode('utf-8', errors='ignore')
            
            # Parse CSV
            csv_file = StringIO(text)
            csv_reader = csv.reader(csv_file)
            
            # Convert to formatted text
            formatted_text = ""
            for row in csv_reader:
                formatted_text += " | ".join(row) + "\n"
            
            return formatted_text
            
        except Exception as e:
            frappe.log_error(f"Error extracting text from CSV: {str(e)}")
            return ""
    
    def _extract_text_from_json(self, content):
        """
        Extract text from a JSON file.
        
        Args:
            content (bytes): JSON file content
            
        Returns:
            str: Extracted text
        """
        try:
            # Decode content
            text = content.decode('utf-8', errors='ignore')
            
            # Check content size to prevent memory exhaustion
            if len(text) > 10 * 1024 * 1024:  # 10MB limit
                frappe.log_error("JSON file too large for processing")
                return "Error: JSON file exceeds size limit"
            
            # Parse JSON with proper error handling
            try:
                data = json.loads(text)
            except json.JSONDecodeError as json_error:
                frappe.log_error(f"Invalid JSON format: {str(json_error)}")
                return f"Error: Invalid JSON format - {str(json_error)}"
            except ValueError as value_error:
                frappe.log_error(f"JSON value error: {str(value_error)}")
                return f"Error: JSON processing error - {str(value_error)}"
            
            # Format as pretty JSON with size limit
            try:
                formatted_text = json.dumps(data, indent=2)
                if len(formatted_text) > 5 * 1024 * 1024:  # 5MB limit for output
                    return json.dumps(data, separators=(',', ':'))[:1024*1024] + "\n... (truncated due to size)"
                return formatted_text
            except (TypeError, ValueError) as format_error:
                frappe.log_error(f"JSON formatting error: {str(format_error)}")
                return f"Error: Could not format JSON - {str(format_error)}"
            
        except Exception as e:
            frappe.log_error(f"Error extracting text from JSON: {str(e)}")
            return f"Error: Failed to process JSON file - {str(e)}"
    
    def _extract_text_from_office(self, content, file_type):
        """
        Extract text from Office documents (XLSX, DOCX).
        
        Args:
            content (bytes): Office document content
            file_type (str): Office document type
            
        Returns:
            str: Extracted text
        """
        try:
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_type}')
            temp_file.write(content)
            temp_file.close()
            
            # Add to temp files list for cleanup
            self.temp_files.append(temp_file.name)
            
            if file_type == 'xlsx':
                import pandas as pd
                
                # Read Excel file
                df = pd.read_excel(temp_file.name)
                
                # Convert to string
                return df.to_string()
                
            elif file_type == 'docx':
                import docx
                
                # Read Word document
                doc = docx.Document(temp_file.name)
                
                # Extract text
                text = ""
                for para in doc.paragraphs:
                    text += para.text + "\n"
                
                return text
            
            return ""
            
        except Exception as e:
            frappe.log_error(f"Error extracting text from Office document: {str(e)}")
            return ""
    
    def _cleanup_temp_files(self):
        """Clean up temporary files."""
        for file_path in self.temp_files:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            except Exception as e:
                frappe.log_error(f"Error cleaning up temporary file {file_path}: {str(e)}")
        
        # Clear the list
        self.temp_files = []
    
    def _log_file_processing(self, file_category, file_type, file_size):
        """
        Log file processing to the audit log.
        
        Args:
            file_category (str): Category of file (image, document, code)
            file_type (str): File type
            file_size (int): File size in bytes
        """
        try:
            audit_log = frappe.get_doc({
                "doctype": "Gemini Audit Log",
                "timestamp": now_datetime(),
                "user": frappe.session.user,
                "action_type": "Function Call",
                "details": json.dumps({
                    "function": "file_processor",
                    "file_category": file_category,
                    "file_type": file_type,
                    "file_size": file_size,
                    "timestamp": str(now_datetime())
                }),
                "status": "Success",
                "ip_address": frappe.local.request_ip if hasattr(frappe.local, "request_ip") else "127.0.0.1"
            })
            
            audit_log.insert(ignore_permissions=True)
            frappe.db.commit()
            
        except Exception as e:
            frappe.log_error(f"Error logging file processing: {str(e)}")
