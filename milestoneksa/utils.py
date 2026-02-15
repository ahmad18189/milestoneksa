import frappe
from frappe.utils import format_value as _format_value

def format_value(value, df=None, format=None, currency=None):
    # if SAR, inject the new symbol
    if df and df.fieldtype=="Currency" and currency=="SAR":
        df.symbol = "⃀"  # new Riyal symbol
    return _format_value(value, df, format, currency)


def use_monthly_series_on_manual_save(doc, method=None):
	"""
	Workaround for Sales Invoice saves hanging/failing due to `tabSeries ... FOR UPDATE` lock waits.

	If a user is saving a Sales Invoice from Desk (savedocs), and the selected series is:
	  ACC-SINV-.YYYY.-
	switch it to a monthly key:
	  ACC-SINV-.YYYY.-.MM.-

	This moves the counter to a different `tabSeries` row (reduces contention).
	"""
	try:
		if not doc or getattr(doc, "doctype", None) != "Sales Invoice":
			return

		# Only affect manual desk saves
		form = getattr(frappe.local, "form_dict", None) or {}
		if form.get("cmd") != "frappe.desk.form.save.savedocs":
			return

		# Only for new invoices (naming happens on insert)
		if getattr(doc, "name", None):
			return

		current = (getattr(doc, "naming_series", None) or "").strip()
		if current != "ACC-SINV-.YYYY.-":
			return

		doc.naming_series = "ACC-SINV-.YYYY.-.MM.-"
	except Exception:
		# best-effort: never block save because of the workaround itself
		return
