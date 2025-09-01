import json
import frappe
from frappe.utils.pdf import get_pdf
from frappe.www.printview import get_letter_head
from frappe.desk.query_report import run as run_query_report

def _normalize_filters(report_name: str, f: dict) -> dict:
	"""Accept synonyms coming from Payroll Entry and map to common report filters."""
	f = dict(f or {})
	if not f.get('from_date') and f.get('start_date'):
		f['from_date'] = f['start_date']
	if not f.get('to_date') and f.get('end_date'):
		f['to_date'] = f['end_date']
	return f

def _post_filter_rows_by_employees(columns, rows, employee_list):
	if not employee_list:
		return rows

	# find a column key representing "employee"
	emp_keys = []
	for col in columns:
		label = (col.get('label') if isinstance(col, dict) else getattr(col, 'label', None)) or ''
		fieldname = (col.get('fieldname') if isinstance(col, dict) else getattr(col, 'fieldname', None)) or ''
		if label.strip().lower() == 'employee' or fieldname.strip().lower() == 'employee':
			emp_keys.append(fieldname or label)

	if not emp_keys:
		emp_keys = ['employee', 'Employee']

	employee_set = set(employee_list)
	filtered = []
	for r in rows:
		val = None
		for key in emp_keys:
			if key in r:
				val = r.get(key)
				break
		# if we couldn't detect a key, keep the row
		if not emp_keys:
			filtered.append(r)
		else:
			if val in employee_set:
				filtered.append(r)
	return filtered

def _resolve_default_currency(filters: dict, company: str | None) -> str:
	"""Decide which currency to use without calling blocked Jinja helpers."""
	# 1) explicit filter wins
	if filters.get('currency'):
		return filters['currency']
	# 2) company default currency
	if company:
		try:
			company_currency = frappe.get_cached_value("Company", company, "default_currency")
			if company_currency:
				return company_currency
		except Exception:
			pass
	# 3) system default
	return frappe.db.get_default("currency") or "SAR"

@frappe.whitelist()
def download_salary_report_pdf(report_name: str, filters: str | dict = "{}"):
	"""
	Render a query report with custom HTML/CSS and stream a PDF.
	Accepts filters from Payroll Entry (company, start/end, payroll_frequency, employee_list).
	"""
	if isinstance(filters, str):
		filters = json.loads(filters or "{}")

	filters = _normalize_filters(report_name, filters)

	# run report
	result = run_query_report(report_name, filters)
	columns = result.get("columns", [])
	rows = result.get("result", [])

	# narrow to provided employee list (if report lacks that filter)
	employee_list = filters.get('employee_list') or []
	if isinstance(employee_list, list) and employee_list:
		rows = _post_filter_rows_by_employees(columns, rows, employee_list)

	company = (filters or {}).get("company")
	letter_head_html = get_letter_head({"company": company}, False) or "" if company else ""

	default_currency = _resolve_default_currency(filters, company)

	# render html
	context = {
		"report_name": report_name,
		"filters": filters,
		"columns": columns,
		"rows": rows,
		"letter_head": letter_head_html,
		"default_currency": default_currency,  # << pass to template
	}
	html = frappe.render_template(
		"milestoneksa/templates/print_formats/salary_slip_report_cairo.html",
		context
	)

	# pdf
	pdf_bytes = get_pdf(html, options={
		"page-size": "A4",
		"margin-top": "12mm",
		"margin-right": "10mm",
		"margin-bottom": "12mm",
		"margin-left": "10mm",
	})

	frappe.local.response.filename = f"{report_name.replace(' ', '_')}.pdf"
	frappe.local.response.filecontent = pdf_bytes
	frappe.local.response.type = "pdf"
