# -*- coding: utf-8 -*-
# Copyright (c) 2025, Your Name and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import os
import json
from frappe import _
from frappe.utils import cint, get_site_config

def extract_text_from_pdf(file_path):
    """
    Extract text from a PDF file
    
    Args:
        file_path (str): Path to the PDF file
        
    Returns:
        str: Extracted text
    """
    try:
        # Try to import PyPDF2
        import PyPDF2
        
        text = ""
        with open(file_path, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n\n"
        
        return text
    except ImportError:
        # If PyPDF2 is not available, try to use pdfplumber
        try:
            import pdfplumber
            
            text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() + "\n\n"
            
            return text
        except ImportError:
            # If neither library is available, log error and return empty string
            frappe.log_error("PDF text extraction libraries (PyPDF2 or pdfplumber) not installed")
            return "PDF text extraction failed. Required libraries not installed."
    except Exception as e:
        frappe.log_error(f"Error extracting text from PDF: {str(e)}")
        return f"PDF text extraction failed: {str(e)}"

def extract_data_from_csv(file_path):
    """
    Extract data from a CSV file
    
    Args:
        file_path (str): Path to the CSV file
        
    Returns:
        list: List of dictionaries representing CSV rows
    """
    try:
        import csv
        
        data = []
        with open(file_path, 'r', newline='', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                data.append(dict(row))
        
        return data
    except Exception as e:
        frappe.log_error(f"Error extracting data from CSV: {str(e)}")
        return []

def get_doctype_fields(doctype):
    """
    Get fields for a DocType
    
    Args:
        doctype (str): DocType name
        
    Returns:
        list: List of field information
    """
    try:
        meta = frappe.get_meta(doctype)
        fields = []
        
        for field in meta.fields:
            fields.append({
                "fieldname": field.fieldname,
                "label": field.label,
                "fieldtype": field.fieldtype,
                "options": field.options,
                "reqd": field.reqd,
                "hidden": field.hidden,
                "description": field.description
            })
        
        return fields
    except Exception as e:
        frappe.log_error(f"Error getting DocType fields: {str(e)}")
        return []

def detect_active_doctype():
    """
    Detect the active DocType based on the current page
    
    Returns:
        dict: Information about the active DocType and document
    """
    try:
        # This is a placeholder. In a real implementation, this would
        # use JavaScript to detect the current page and doctype.
        # For now, we'll return None.
        return None
    except Exception as e:
        frappe.log_error(f"Error detecting active DocType: {str(e)}")
        return None

def get_document_context(doctype, docname):
    """
    Get context information for a document
    
    Args:
        doctype (str): DocType name
        docname (str): Document name
        
    Returns:
        dict: Document context information
    """
    try:
        # Check permissions
        if not frappe.has_permission(doctype, "read", docname):
            return {
                "error": True,
                "message": f"No permission to read {doctype} {docname}"
            }
        
        # Get document
        doc = frappe.get_doc(doctype, docname)
        
        # Get fields that the user has permission to read
        fields = {}
        meta = frappe.get_meta(doctype)
        
        for field in meta.fields:
            if field.fieldtype not in ["Section Break", "Column Break", "Tab Break"]:
                # Check field level permissions if applicable
                if hasattr(doc, field.fieldname):
                    fields[field.fieldname] = {
                        "label": field.label,
                        "value": doc.get(field.fieldname),
                        "type": field.fieldtype
                    }
        
        # Get linked documents
        links = {}
        for link_field in meta.get_link_fields():
            if hasattr(doc, link_field.fieldname) and doc.get(link_field.fieldname):
                links[link_field.fieldname] = {
                    "doctype": link_field.options,
                    "name": doc.get(link_field.fieldname)
                }
        
        # Get child tables
        child_tables = {}
        for child_table in meta.get_table_fields():
            if hasattr(doc, child_table.fieldname):
                child_docs = doc.get(child_table.fieldname)
                child_tables[child_table.fieldname] = {
                    "label": child_table.label,
                    "count": len(child_docs),
                    "doctype": child_table.options
                }
        
        return {
            "doctype": doctype,
            "name": docname,
            "fields": fields,
            "links": links,
            "child_tables": child_tables
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting document context: {str(e)}")
        return {
            "error": True,
            "message": f"Error: {str(e)}"
        }
