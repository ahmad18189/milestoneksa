import frappe
from frappe.utils import flt

def execute(filters=None):
    filters = filters or {}
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")

    conditions = ""
    if from_date and to_date:
        conditions = f"AND posting_date BETWEEN '{from_date}' AND '{to_date}'"

    revenue = frappe.db.sql(f"""
        SELECT SUM(base_grand_total) FROM `tabSales Invoice`
        WHERE docstatus = 1 {conditions}
    """)[0][0] or 0

    expenses = frappe.db.sql(f"""
        SELECT SUM(base_grand_total) FROM `tabPurchase Invoice`
        WHERE docstatus = 1 {conditions}
    """)[0][0] or 0

    net_profit = flt(revenue) - flt(expenses)

    # ✅ Column format for KPI Card
    columns = ["Net Profit:Currency:150"]
    data = [[net_profit]]

    return columns, data
