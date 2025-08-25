import frappe
from frappe.utils import flt, get_first_day, nowdate

def execute(filters=None):
    filters = filters or {}
    
    # Automatically get start of year if not provided
    from_date = filters.get("from_date") or get_first_day(nowdate(), 0)
    to_date = filters.get("to_date") or nowdate()

    date_condition = f"AND posting_date BETWEEN '{from_date}' AND '{to_date}'"

    # Get all non-group Bank accounts
    bank_accounts = frappe.get_all("Account", filters={"account_type": "Bank", "is_group": 0}, pluck="name")

    if not bank_accounts:
        return ["Cash in Bank:Currency:150"], [[0]]

    accounts_list = "', '".join(bank_accounts)

    # Sum Debit - Credit for bank accounts
    result = frappe.db.sql(f"""
        SELECT SUM(debit) - SUM(credit)
        FROM `tabGL Entry`
        WHERE docstatus = 1 AND account IN ('{accounts_list}')
        {date_condition}
    """)[0][0] or 0

    return ["Cash in Bank:Currency:150"], [[flt(result)]]
