from frappe.utils import format_value as _format_value

def format_value(value, df=None, format=None, currency=None):
    # if SAR, inject the new symbol
    if df and df.fieldtype=="Currency" and currency=="SAR":
        df.symbol = "⃀"  # new Riyal symbol
    return _format_value(value, df, format, currency)
