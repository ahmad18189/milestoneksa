# Copyright (c) 2025, Milestone KSA and contributors
# License: MIT

import frappe
from frappe import _
from frappe.utils import flt, getdate, get_first_day, get_last_day, nowdate

from erpnext.accounts.report.financial_statements import get_cost_centers_with_children
from erpnext.accounts.utils import get_account_currency


def execute(filters=None):
	if not filters:
		return get_columns(filters), []

	if not filters.get("account"):
		return get_columns(filters), []

	# Normalize and validate dates (with fallbacks when missing from request)
	filters["from_date"] = getdate(filters.get("from_date")) or get_first_day(nowdate())
	filters["to_date"] = getdate(filters.get("to_date")) or get_last_day(nowdate())

	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date"))

	# Validate account is Bank or Cash
	account_type = frappe.get_cached_value("Account", filters.account, "account_type")
	if account_type not in ("Bank", "Cash"):
		frappe.throw(_("Account must be of type Bank or Cash"))

	# Get company from account if not provided
	if not filters.get("company"):
		filters["company"] = frappe.get_cached_value("Account", filters.account, "company")

	columns = get_columns(filters)
	result = get_report_data(filters)

	return columns, result


def get_report_data(filters):
	account_currency = get_account_currency(filters.account)

	# Build common conditions for project and cost_center
	extra_conditions = []
	if filters.get("project"):
		if isinstance(filters.project, str):
			filters.project = frappe.parse_json(filters.project) if filters.project.startswith("[") else [filters.project]
		extra_conditions.append("project in %(project)s")

	if filters.get("cost_center"):
		if isinstance(filters.cost_center, str):
			filters.cost_center = frappe.parse_json(filters.cost_center) if filters.cost_center.startswith("[") else [filters.cost_center]
		filters.cost_center = get_cost_centers_with_children(filters.cost_center)
		extra_conditions.append("cost_center in %(cost_center)s")

	extra_sql = (" and " + " and ".join(extra_conditions)) if extra_conditions else ""

	# Opening balance (balance before from_date)
	opening_balance = frappe.db.sql(
		f"""
		select sum(debit) - sum(credit) as balance
		from `tabGL Entry`
		where company = %(company)s and account = %(account)s and posting_date < %(from_date)s and is_cancelled = 0
		{extra_sql}
		""",
		filters,
		as_dict=1,
	)
	opening_balance = flt(opening_balance[0]["balance"] if opening_balance else 0)

	# Period entries
	conditions = ["account = %(account)s", "posting_date >= %(from_date)s", "posting_date <= %(to_date)s", "is_cancelled = 0"] + extra_conditions
	conditions_sql = " and ".join(conditions)

	gl_entries = frappe.db.sql(
		f"""
		select posting_date, debit, credit, remarks, project, voucher_no, voucher_type
		from `tabGL Entry`
		where company = %(company)s and {conditions_sql}
		order by posting_date, creation
		""",
		filters,
		as_dict=1,
	)

	debit_entries = [e for e in gl_entries if flt(e.debit) > 0]
	credit_entries = [e for e in gl_entries if flt(e.credit) > 0]

	total_debit = sum(flt(e.debit) for e in debit_entries)
	total_credit = sum(flt(e.credit) for e in credit_entries)
	# Difference: always show as positive - in debit column when net inflow, credit column when net outflow
	diff_amount = abs(total_debit - total_credit)

	def make_row(section="", posting_date=None, debit=None, credit=None, remarks=None, project=None, voucher_no=None, voucher_type=None):
		row = {"section": section, "posting_date": posting_date, "debit": debit, "credit": credit, "remarks": remarks, "project": project, "voucher_no": voucher_no, "voucher_type": voucher_type, "account_currency": account_currency}
		return row

	result = []

	# Section In (إيرادات نقدية) - includes opening balance before from_date
	result.append(make_row(section=_("In Cash")))
	# Opening balance (balance before from_date)
	if opening_balance != 0:
		if opening_balance > 0:
			result.append(make_row(section=_("Opening Balance"), debit=opening_balance, remarks=_("Balance before {0}").format(filters.from_date)))
		else:
			result.append(make_row(section=_("Opening Balance"), credit=abs(opening_balance), remarks=_("Balance before {0}").format(filters.from_date)))
	for e in debit_entries:
		result.append(make_row(posting_date=e.posting_date, debit=e.debit, credit=0, remarks=e.remarks or "", project=e.project or "", voucher_no=e.voucher_no or "", voucher_type=e.voucher_type or ""))
	result.append(make_row(section=_("Total"), debit=total_debit))
	# Grand Total = Total + Opening Balance
	grand_total_in = total_debit + opening_balance
	if grand_total_in >= 0:
		result.append(make_row(section=_("Grand Total"), debit=grand_total_in))
	else:
		result.append(make_row(section=_("Grand Total"), credit=abs(grand_total_in)))

	# Separator rows between In Cash and Out Cash
	result.append(make_row())
	result.append(make_row())

	# Section Out (مدفوعات نقدية)
	result.append(make_row(section=_("Out Cash")))
	for e in credit_entries:
		result.append(make_row(posting_date=e.posting_date, debit=0, credit=e.credit, remarks=e.remarks or "", project=e.project or "", voucher_no=e.voucher_no or "", voucher_type=e.voucher_type or ""))
	result.append(make_row(section=_("Total"), credit=total_credit))
	# Difference: positive amount - debit when net inflow (more in than out), credit when net outflow
	if diff_amount > 0:
		if total_debit > total_credit:
			result.append(make_row(section=_("Difference"), debit=diff_amount))
		else:
			result.append(make_row(section=_("Difference"), credit=diff_amount))

	return result


def get_columns(filters):
	account_currency = None
	if filters and filters.get("account"):
		account_currency = get_account_currency(filters.account)
	if not account_currency:
		account_currency = frappe.get_cached_value("Company", filters.get("company") or frappe.defaults.get_user_default("Company"), "default_currency") if filters else "SAR"

	return [
		{"label": _("Section"), "fieldname": "section", "fieldtype": "Data", "width": 120},
		{"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
		{"label": _("Debit"), "fieldname": "debit", "fieldtype": "Currency", "options": "account_currency", "width": 130},
		{"label": _("Credit"), "fieldname": "credit", "fieldtype": "Currency", "options": "account_currency", "width": 130},
		{"label": _("Remarks"), "fieldname": "remarks", "fieldtype": "Data", "width": 200},
		{"label": _("Project"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 120},
		{"label": _("Voucher No"), "fieldname": "voucher_no", "fieldtype": "Data", "width": 120},
		{"label": _("Voucher Type"), "fieldname": "voucher_type", "fieldtype": "Link", "options": "DocType", "width": 120},
	]
