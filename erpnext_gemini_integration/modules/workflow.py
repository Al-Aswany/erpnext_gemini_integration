# -*- coding: utf-8 -*-
# Copyright (c) 2025, Your Name and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe import _
from frappe.utils import now_datetime, add_days, add_months
from datetime import datetime, timedelta

class GeminiWorkflow:
    """
    Workflow automation for Gemini Assistant
    
    This class handles:
    - Scheduled analysis of business data
    - Automated report generation
    - Periodic data processing tasks
    """
    
    def __init__(self, user=None):
        """
        Initialize the workflow module
        
        Args:
            user (str, optional): The user. Defaults to current user.
        """
        self.user = user or frappe.session.user

    def log_workflow_execution(self, workflow_type, status, results=None, error=None):
        """
        Log workflow execution for auditing purposes
        
        Args:
            workflow_type (str): Type of workflow (hourly, daily, etc.)
            status (str): Status of execution (success, failed)
            results (dict, optional): Results of workflow execution
            error (str, optional): Error message if workflow failed
            
        Returns:
            str: ID of the log entry
        """
        try:
            # Create workflow log
            workflow_log = frappe.new_doc("Gemini Workflow Log")
            workflow_log.user = self.user
            workflow_log.timestamp = now_datetime()
            workflow_log.workflow_type = workflow_type
            workflow_log.status = status
            
            # Set results or error
            if results:
                workflow_log.results = json.dumps(results)
                
            if error:
                workflow_log.error = error
                
            workflow_log.insert(ignore_permissions=True)
            
            return workflow_log.name
            
        except Exception as e:
            frappe.log_error(f"Error logging workflow execution: {str(e)}")
            return None

def run_hourly_analysis():
    """
    Run hourly analysis of business data
    
    This function is called by a scheduled job every hour to analyze:
    - Recent transactions
    - System performance
    - User activity
    
    Returns:
        dict: Results of analysis
    """
    try:
        workflow = GeminiWorkflow(user="Administrator")
        frappe.logger().info("Starting hourly Gemini analysis")
        
        # Initialize results
        results = {
            "timestamp": str(now_datetime()),
            "metrics": {},
            "insights": [],
            "actions": []
        }
        
        # Analyze recent transactions
        try:
            # Get transactions from last hour
            last_hour = add_days(now_datetime(), 0)
            last_hour = last_hour.replace(minute=0, second=0, microsecond=0)
            
            # Sales transactions
            sales_count = frappe.db.count("Sales Invoice", {"creation": [">=", last_hour]})
            results["metrics"]["sales_count"] = sales_count
            
            # Purchase transactions
            purchase_count = frappe.db.count("Purchase Invoice", {"creation": [">=", last_hour]})
            results["metrics"]["purchase_count"] = purchase_count
            
            # Stock transactions
            stock_count = frappe.db.count("Stock Entry", {"creation": [">=", last_hour]})
            results["metrics"]["stock_count"] = stock_count
            
            # Add insight if transaction volume is unusual
            if sales_count > 100:
                results["insights"].append("Unusually high sales volume detected in the last hour")
                
        except Exception as e:
            frappe.log_error(f"Error analyzing transactions in hourly analysis: {str(e)}")
            results["insights"].append("Error analyzing transactions")
        
        # Analyze system performance
        try:
            # Get error logs from last hour
            error_count = frappe.db.count("Error Log", {"creation": [">=", last_hour]})
            results["metrics"]["error_count"] = error_count
            
            # Add insight if error count is high
            if error_count > 10:
                results["insights"].append("Unusually high number of system errors detected")
                results["actions"].append("Investigate system errors in the Error Log")
                
        except Exception as e:
            frappe.log_error(f"Error analyzing system performance in hourly analysis: {str(e)}")
            results["insights"].append("Error analyzing system performance")
        
        # Analyze user activity
        try:
            # Get active users in last hour
            active_users = frappe.db.sql("""
                SELECT COUNT(DISTINCT user) 
                FROM `tabActivity Log` 
                WHERE creation >= %s
            """, last_hour)[0][0]
            
            results["metrics"]["active_users"] = active_users
            
        except Exception as e:
            frappe.log_error(f"Error analyzing user activity in hourly analysis: {str(e)}")
            results["insights"].append("Error analyzing user activity")
        
        # Log successful execution
        workflow.log_workflow_execution("hourly", "success", results)
        
        frappe.logger().info(f"Completed hourly Gemini analysis: {json.dumps(results)}")
        return results
        
    except Exception as e:
        # Log failed execution
        error_message = f"Error in hourly Gemini analysis: {str(e)}"
        frappe.log_error(error_message)
        
        if 'workflow' in locals():
            workflow.log_workflow_execution("hourly", "failed", error=error_message)
            
        return {"error": error_message}

def run_daily_analysis():
    """
    Run daily analysis of business data
    
    This function is called by a scheduled job every day to analyze:
    - Daily business performance
    - Trends and patterns
    - Key metrics for decision making
    
    Returns:
        dict: Results of analysis
    """
    try:
        workflow = GeminiWorkflow(user="Administrator")
        frappe.logger().info("Starting daily Gemini analysis")
        
        # Initialize results
        results = {
            "timestamp": str(now_datetime()),
            "metrics": {},
            "insights": [],
            "actions": [],
            "trends": {}
        }
        
        # Get date range
        today = now_datetime().date()
        yesterday = add_days(today, -1)
        last_week = add_days(today, -7)
        last_month = add_months(today, -1)
        
        # Analyze daily sales
        try:
            # Get sales data
            yesterday_sales = frappe.db.sql("""
                SELECT SUM(grand_total) 
                FROM `tabSales Invoice` 
                WHERE DATE(posting_date) = %s
                AND docstatus = 1
            """, yesterday)[0][0] or 0
            
            last_week_sales = frappe.db.sql("""
                SELECT SUM(grand_total) 
                FROM `tabSales Invoice` 
                WHERE posting_date BETWEEN %s AND %s
                AND docstatus = 1
            """, [last_week, yesterday])[0][0] or 0
            
            # Calculate averages
            avg_daily_sales = last_week_sales / 7 if last_week_sales else 0
            
            # Store metrics
            results["metrics"]["yesterday_sales"] = yesterday_sales
            results["metrics"]["avg_daily_sales"] = avg_daily_sales
            
            # Calculate trends
            sales_trend = ((yesterday_sales - avg_daily_sales) / avg_daily_sales * 100) if avg_daily_sales else 0
            results["trends"]["sales"] = sales_trend
            
            # Add insights
            if sales_trend > 20:
                results["insights"].append(f"Sales increased by {sales_trend:.1f}% compared to daily average")
            elif sales_trend < -20:
                results["insights"].append(f"Sales decreased by {abs(sales_trend):.1f}% compared to daily average")
                results["actions"].append("Review sales performance and identify potential issues")
                
        except Exception as e:
            frappe.log_error(f"Error analyzing daily sales in daily analysis: {str(e)}")
            results["insights"].append("Error analyzing daily sales")
        
        # Analyze inventory levels
        try:
            # Get low stock items
            low_stock_items = frappe.db.sql("""
                SELECT COUNT(*) 
                FROM `tabBin` 
                WHERE actual_qty <= reorder_level 
                AND reorder_level > 0
            """)[0][0] or 0
            
            results["metrics"]["low_stock_items"] = low_stock_items
            
            if low_stock_items > 0:
                results["insights"].append(f"{low_stock_items} items are below reorder level")
                results["actions"].append("Review stock levels and create purchase orders")
                
        except Exception as e:
            frappe.log_error(f"Error analyzing inventory in daily analysis: {str(e)}")
            results["insights"].append("Error analyzing inventory levels")
        
        # Analyze accounts receivable
        try:
            # Get overdue invoices
            overdue_invoices = frappe.db.sql("""
                SELECT COUNT(*), SUM(outstanding_amount) 
                FROM `tabSales Invoice` 
                WHERE docstatus = 1 
                AND due_date < %s 
                AND outstanding_amount > 0
            """, today, as_dict=True)[0]
            
            overdue_count = overdue_invoices.get("COUNT(*)", 0)
            overdue_amount = overdue_invoices.get("SUM(outstanding_amount)", 0)
            
            results["metrics"]["overdue_invoices"] = overdue_count
            results["metrics"]["overdue_amount"] = overdue_amount
            
            if overdue_count > 10 or overdue_amount > 10000:
                results["insights"].append(f"{overdue_count} overdue invoices with total amount {overdue_amount}")
                results["actions"].append("Follow up on overdue payments")
                
        except Exception as e:
            frappe.log_error(f"Error analyzing accounts receivable in daily analysis: {str(e)}")
            results["insights"].append("Error analyzing accounts receivable")
        
        # Log successful execution
        workflow.log_workflow_execution("daily", "success", results)
        
        frappe.logger().info(f"Completed daily Gemini analysis: {json.dumps(results)}")
        return results
        
    except Exception as e:
        # Log failed execution
        error_message = f"Error in daily Gemini analysis: {str(e)}"
        frappe.log_error(error_message)
        
        if 'workflow' in locals():
            workflow.log_workflow_execution("daily", "failed", error=error_message)
            
        return {"error": error_message}
