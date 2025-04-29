# -*- coding: utf-8 -*-
# Copyright (c) 2025, Manus AI Agent and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, nowdate, add_days
import json

def check_stock_levels(item_code):
    """Fetches the actual stock quantity for a given item code."""
    try:
        if not item_code:
            return {"error": _("Item code is required.")}

        # Check if item exists
        if not frappe.db.exists("Item", item_code):
            return {"error": _("Item code ") + f"\"{item_code}\"" + _(" not found.")}

        # Get stock quantity
        # Note: This gets the total quantity across all warehouses.
        # For specific warehouse stock, the query needs modification.
        actual_qty = frappe.db.get_value("Item", item_code, "actual_qty")

        if actual_qty is None:
            actual_qty = 0 # Item might exist but have no stock ledger entry yet

        return {
            "item_code": item_code,
            "actual_quantity": actual_qty,
            "message": _("Stock level for item ") + f"\"{item_code}\"" + _(" is ") + f"{actual_qty}"
        }

    except Exception as e:
        frappe.log_error(f"Error in check_stock_levels for {item_code}: {str(e)}")
        return {"error": _("Failed to retrieve stock level for ") + f"\"{item_code}\""}

def generate_sales_report(start_date_str=None, end_date_str=None):
    """Generates a summary sales report based on submitted Sales Orders within a date range."""
    try:
        # Default date range: last 30 days
        end_date = getdate(end_date_str) if end_date_str else getdate(nowdate())
        start_date = getdate(start_date_str) if start_date_str else add_days(end_date, -30)

        # Query submitted Sales Orders within the date range
        sales_orders = frappe.get_all(
            "Sales Order",
            filters={
                "docstatus": 1, # Submitted
                "transaction_date": ["between", [start_date, end_date]]
            },
            fields=["name", "customer", "grand_total", "transaction_date"]
        )

        if not sales_orders:
            return {"message": _("No submitted Sales Orders found between ") + f"{start_date} " + _("and") + f" {end_date}."}

        total_sales = sum(so.grand_total for so in sales_orders)
        order_count = len(sales_orders)

        # Prepare summary
        summary = {
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "total_orders": order_count,
            "total_sales_amount": total_sales,
            "message": _("Found ") + f"{order_count} " + _("submitted Sales Orders totaling ") + f"{total_sales:.2f} " + _("between ") + f"{start_date} " + _("and") + f" {end_date}."
        }

        # Optionally include top customers or other insights if needed

        return summary

    except Exception as e:
        frappe.log_error(f"Error in generate_sales_report: {str(e)}")
        return {"error": _("Failed to generate sales report.")}

def list_overdue_invoices(customer=None):
    """Lists submitted Sales Invoices that are overdue."""
    try:
        filters = {
            "docstatus": 1, # Submitted
            "status": ["not in", ["Paid", "Cancelled"]],
            "due_date": ["<", nowdate()]
        }

        if customer:
            if not frappe.db.exists("Customer", customer):
                 return {"error": _("Customer ") + f"\"{customer}\"" + _(" not found.")}
            filters["customer"] = customer

        overdue_invoices = frappe.get_all(
            "Sales Invoice",
            filters=filters,
            fields=["name", "customer", "due_date", "outstanding_amount"],
            order_by="due_date asc"
        )

        if not overdue_invoices:
            msg = _("No overdue invoices found.")
            if customer:
                msg = _("No overdue invoices found for customer ") + f"\"{customer}\"" + _(".")
            return {"message": msg}

        count = len(overdue_invoices)
        total_outstanding = sum(inv.outstanding_amount for inv in overdue_invoices)

        # Prepare summary
        summary = {
            "count": count,
            "total_outstanding": total_outstanding,
            "invoices": overdue_invoices,
            "message": _("Found ") + f"{count} " + _("overdue invoices totaling ") + f"{total_outstanding:.2f} " + _("outstanding.")
        }
        if customer:
             summary["message"] = _("Found ") + f"{count} " + _("overdue invoices for customer ") + f"\"{customer}\"" + _(" totaling ") + f"{total_outstanding:.2f} " + _("outstanding.")

        return summary

    except Exception as e:
        frappe.log_error(f"Error in list_overdue_invoices: {str(e)}")
        return {"error": _("Failed to list overdue invoices.")}

# Mapping function names to actual functions
ERPNext_FUNCTIONS = {
    "check_stock_levels": check_stock_levels,
    "generate_sales_report": generate_sales_report,
    "list_overdue_invoices": list_overdue_invoices
}

