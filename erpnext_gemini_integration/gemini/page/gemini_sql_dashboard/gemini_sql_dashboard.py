import frappe

@frappe.whitelist()
def get_dashboard_settings():
    """Get dashboard settings and permissions"""
    return {
        "can_execute": frappe.has_permission("Gemini SQL Dashboard", "read"),
        "max_results": 1000  # Maximum number of rows to return
    }

def get_page_info():
    return {
        "page_name": "gemini-sql-dashboard",
        "title": "Gemini SQL Dashboard"
    } 