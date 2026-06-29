# -*- coding: utf-8 -*-
"""KSA End of Service benefit calculations (Labour Law Articles 84 & 85)."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, flt, formatdate, getdate
from dateutil.relativedelta import relativedelta

from milestoneksa.api.salary_ui import _extract_from_structure, _find_employee_structure

SEPARATION_CONTRACT_EXPIRY = "Contract Expiry"
SEPARATION_RESIGNATION = "Resignation"
SEPARATION_EMPLOYER_TERMINATION = "Employer Termination"
AVERAGE_SLIP_MONTHS = 3


def get_last_salary_slip_name(employee: str, end_date=None) -> str | None:
	filters: dict = {"employee": employee, "docstatus": 1}
	if end_date:
		filters["end_date"] = ["<=", getdate(end_date)]

	return frappe.db.get_value("Salary Slip", filters, "name", order_by="start_date desc")


def get_last_actual_wage_from_salary_slip(employee: str, end_date=None) -> tuple[float, str | None, list[dict]]:
	"""
	Last actual wage from the latest submitted Salary Slip earnings.
	Recalculates with full payment days (same approach as HRMS Gratuity).
	"""
	slip_name = get_last_salary_slip_name(employee, end_date)
	if not slip_name:
		return 0.0, None, []

	slip = frappe.get_doc("Salary Slip", slip_name)
	if slip.total_working_days:
		slip.payment_days = slip.total_working_days
		slip.calculate_net_pay()

	excluded = _get_excluded_salary_components()
	breakdown: list[dict] = []
	total = 0.0

	for row in slip.earnings:
		component = row.salary_component
		amount = flt(row.amount)
		if component in excluded:
			continue
		breakdown.append({"component": component, "amount": amount})
		total += amount

	return flt(total, 2), slip_name, breakdown


def get_average_wage_from_salary_slips(employee: str, months: int = AVERAGE_SLIP_MONTHS, end_date=None) -> float:
	"""Average gross pay from the last N submitted salary slips."""
	filters: dict = {"employee": employee, "docstatus": 1}
	if end_date:
		filters["end_date"] = ["<=", getdate(end_date)]

	slips = frappe.get_all(
		"Salary Slip",
		filters=filters,
		fields=["gross_pay"],
		order_by="start_date desc",
		limit=months,
	)
	if not slips:
		return 0.0

	return flt(sum(flt(row.gross_pay) for row in slips) / len(slips), 2)


def get_last_actual_wage_from_structure(employee: str) -> float:
	"""Fallback when no salary slips exist."""
	row = _find_employee_structure(employee)
	if not row:
		return 0.0

	earnings, _deductions, _currency, _st = _extract_from_structure(row.name)
	excluded = _get_excluded_salary_components()
	return flt(
		sum(item.get("amount", 0) for item in earnings if item.get("salary_component") not in excluded),
		2,
	)


def get_last_actual_wage(employee: str, end_date=None) -> dict:
	"""Resolve last actual wage from salary slips, with structure fallback."""
	wage, slip_name, breakdown = get_last_actual_wage_from_salary_slip(employee, end_date)
	source = "Salary Slip"

	if wage <= 0:
		wage = get_last_actual_wage_from_structure(employee)
		source = "Salary Structure"
		slip_name = None
		breakdown = []

	avg_wage = get_average_wage_from_salary_slips(employee, end_date=end_date)

	return {
		"last_actual_wage": wage,
		"salary_slip_reference": slip_name,
		"average_monthly_wage": avg_wage,
		"wage_source": source,
		"wage_breakdown": breakdown,
	}


def _get_excluded_salary_components() -> set[str]:
	"""Exclude variable / statistical components from last actual wage."""
	excluded: set[str] = set()
	meta = frappe.get_meta("Salary Component")

	if meta.has_field("variable_based_on_taxable_salary"):
		excluded.update(
			frappe.get_all(
				"Salary Component",
				filters={"variable_based_on_taxable_salary": 1},
				pluck="name",
			)
			or []
		)

	if meta.has_field("is_statistical_component"):
		excluded.update(
			frappe.get_all(
				"Salary Component",
				filters={"is_statistical_component": 1},
				pluck="name",
			)
			or []
		)

	return excluded


def get_unpaid_leave_days_from_applications(employee: str, from_date, to_date) -> float:
	"""
	Unpaid leave days from approved Leave Applications (LWP / PPL leave types)
	within the service period.
	"""
	if not from_date or not to_date:
		return 0.0

	period_start = getdate(from_date)
	period_end = getdate(to_date)
	if period_end < period_start:
		return 0.0

	applications = frappe.db.sql(
		"""
		SELECT
			la.from_date, la.to_date, la.total_leave_days, la.half_day, la.half_day_date,
			lt.is_lwp, lt.is_ppl, lt.fraction_of_daily_salary_per_leave, la.leave_type
		FROM `tabLeave Application` la
		INNER JOIN `tabLeave Type` lt ON lt.name = la.leave_type
		WHERE la.employee = %(employee)s
			AND la.docstatus = 1
			AND la.status = 'Approved'
			AND (lt.is_lwp = 1 OR lt.is_ppl = 1)
			AND la.from_date <= %(to_date)s
			AND la.to_date >= %(from_date)s
		""",
		{"employee": employee, "from_date": period_start, "to_date": period_end},
		as_dict=True,
	)

	total_unpaid = 0.0
	for app in applications:
		overlap_start = max(getdate(app.from_date), period_start)
		overlap_end = min(getdate(app.to_date), period_end)
		if overlap_end < overlap_start:
			continue

		overlap_calendar_days = date_diff(overlap_end, overlap_start) + 1
		leave_days = flt(app.total_leave_days) or overlap_calendar_days

		if overlap_calendar_days < leave_days:
			effective_days = overlap_calendar_days
		else:
			effective_days = leave_days

		if app.half_day and overlap_calendar_days == 1:
			effective_days = min(effective_days, 0.5)

		if app.is_lwp:
			total_unpaid += effective_days
		elif app.is_ppl:
			unpaid_fraction = 1 - flt(app.fraction_of_daily_salary_per_leave or 0)
			total_unpaid += effective_days * unpaid_fraction

	return flt(total_unpaid, 2)


def get_leave_allocation_summary(employee: str, as_on_date) -> list[dict]:
	"""Active leave allocations overlapping the service period end date."""
	as_on = getdate(as_on_date)
	return frappe.get_all(
		"Leave Allocation",
		filters={
			"employee": employee,
			"docstatus": 1,
			"from_date": ["<=", as_on],
			"to_date": [">=", as_on],
		},
		fields=["name", "leave_type", "from_date", "to_date", "total_leaves_allocated", "new_leaves_allocated"],
		order_by="from_date desc",
	)


def get_paid_leave_days_taken(employee: str, from_date, to_date) -> float:
	"""Approved paid leave days (non-LWP/PPL) taken in service period."""
	if not from_date or not to_date:
		return 0.0

	rows = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(la.total_leave_days), 0) AS total_days
		FROM `tabLeave Application` la
		INNER JOIN `tabLeave Type` lt ON lt.name = la.leave_type
		WHERE la.employee = %(employee)s
			AND la.docstatus = 1
			AND la.status = 'Approved'
			AND IFNULL(lt.is_lwp, 0) = 0
			AND IFNULL(lt.is_ppl, 0) = 0
			AND la.from_date <= %(to_date)s
			AND la.to_date >= %(from_date)s
		""",
		{
			"employee": employee,
			"from_date": getdate(from_date),
			"to_date": getdate(to_date),
		},
		as_dict=True,
	)
	return flt(rows[0].total_days if rows else 0, 2)


def compute_years_of_service(
	date_of_joining,
	end_date,
	unpaid_leave_days: float = 0,
) -> float:
	"""
	Service years from joining to end date (KSA: calendar years + pro-rated months/days).
	Unpaid leave (LWP/PPL) reduces the effective end date.
	"""
	if not date_of_joining or not end_date:
		return 0.0

	start = getdate(date_of_joining)
	end = getdate(end_date)
	if end < start:
		return 0.0

	if unpaid_leave_days:
		end = add_days(end, -int(unpaid_leave_days))
		if end < start:
			return 0.0

	delta = relativedelta(end, start)
	years = delta.years + (delta.months / 12.0) + (delta.days / 365.0)
	return flt(years, 4)


def get_total_service_days(date_of_joining, end_date, unpaid_leave_days: float = 0) -> int:
	"""Total calendar days of service after unpaid leave deduction."""
	if not date_of_joining or not end_date:
		return 0

	start = getdate(date_of_joining)
	end = getdate(end_date)
	if end < start:
		return 0

	total_days = date_diff(end, start)
	return max(total_days - int(unpaid_leave_days or 0), 0)


def compute_article_84_amount(wage: float, years: float) -> float:
	"""
	Article 84: half-month wage per year for first 5 years,
	one full month wage per year thereafter. Partial years prorated.
	"""
	wage = flt(wage, 2)
	years = flt(years, 4)
	if wage <= 0 or years <= 0:
		return 0.0

	if years <= 5:
		return flt(years * 0.5 * wage, 2)

	first_five = 5 * 0.5 * wage
	remaining = (years - 5) * 1.0 * wage
	return flt(first_five + remaining, 2)


def get_article_85_factor(years: float, separation_reason: str) -> float:
	"""Resignation scaling per Article 85; full benefit for expiry/termination."""
	if separation_reason in (SEPARATION_CONTRACT_EXPIRY, SEPARATION_EMPLOYER_TERMINATION):
		return 1.0

	if separation_reason != SEPARATION_RESIGNATION:
		return 1.0

	if years < 2:
		return 0.0
	if years < 5:
		return 1.0 / 3.0
	if years < 10:
		return 2.0 / 3.0
	return 1.0


def build_eos_notes(
	wage_data: dict,
	years: float,
	total_service_days: int,
	unpaid_leave_days: float,
	paid_leave_days: float,
	allocations: list[dict],
	article_84: float,
	factor: float,
	final_amount: float,
	separation_reason: str,
	from_date,
	to_date,
) -> str:
	lines = [
		f"Service Period: {formatdate(from_date)} → {formatdate(to_date)}",
		f"Wage Source: {wage_data.get('wage_source')}",
	]

	if wage_data.get("salary_slip_reference"):
		lines.append(f"Last Salary Slip: {wage_data['salary_slip_reference']}")
	if wage_data.get("average_monthly_wage"):
		lines.append(f"Average Monthly Wage (last {AVERAGE_SLIP_MONTHS} slips): {wage_data['average_monthly_wage']:,.2f} SAR")

	for row in wage_data.get("wage_breakdown") or []:
		lines.append(f"  - {row['component']}: {flt(row['amount']):,.2f} SAR")

	lines.extend(
		[
			f"Last Actual Wage: {wage_data.get('last_actual_wage', 0):,.2f} SAR",
			f"Unpaid Leave Days (LWP/PPL applications): {unpaid_leave_days}",
			f"Paid Leave Days Taken: {paid_leave_days}",
			f"Total Service Days: {total_service_days}",
			f"Years of Service (after unpaid leave): {years:.4f}",
			f"Separation Reason: {separation_reason}",
			f"Article 84 Full Amount: {article_84:,.2f} SAR",
			f"Article 85 Factor: {factor:.4f}",
			f"Final EOS Amount: {final_amount:,.2f} SAR",
		]
	)

	if allocations:
		lines.append("Active Leave Allocations:")
		for alloc in allocations[:10]:
			lines.append(
				f"  - {alloc.leave_type}: {alloc.total_leaves_allocated} "
				f"({formatdate(alloc.from_date)} → {formatdate(alloc.to_date)})"
			)

	return "\n".join(lines)


def compute_final_eos(
	employee: str,
	end_date,
	separation_reason: str = SEPARATION_CONTRACT_EXPIRY,
	unpaid_leave_days: float | None = None,
) -> dict:
	"""Compute full EOS breakdown using salary slips and leave records."""
	emp = frappe.get_doc("Employee", employee)
	doj = emp.date_of_joining

	wage_data = get_last_actual_wage(employee, end_date)
	computed_unpaid = get_unpaid_leave_days_from_applications(employee, doj, end_date)
	unpaid_days = computed_unpaid if unpaid_leave_days is None else flt(unpaid_leave_days)
	paid_leave_days = get_paid_leave_days_taken(employee, doj, end_date)
	allocations = get_leave_allocation_summary(employee, end_date)

	wage = flt(wage_data["last_actual_wage"], 2)
	total_service_days = get_total_service_days(doj, end_date, unpaid_days)
	years = compute_years_of_service(doj, end_date, unpaid_days)
	article_84 = compute_article_84_amount(wage, years)
	factor = get_article_85_factor(years, separation_reason)
	final_amount = flt(article_84 * factor, 2)

	notes = build_eos_notes(
		wage_data,
		years,
		total_service_days,
		unpaid_days,
		paid_leave_days,
		allocations,
		article_84,
		factor,
		final_amount,
		separation_reason,
		doj,
		end_date,
	)

	return {
		"last_actual_wage": wage,
		"salary_slip_reference": wage_data.get("salary_slip_reference"),
		"average_monthly_wage": wage_data.get("average_monthly_wage"),
		"wage_source": wage_data.get("wage_source"),
		"unpaid_leave_days": unpaid_days,
		"unpaid_leave_days_computed": computed_unpaid,
		"paid_leave_days_taken": paid_leave_days,
		"total_service_days": total_service_days,
		"years_of_service": years,
		"article_84_full_amount": article_84,
		"article_85_factor": factor,
		"final_eos_amount": final_amount,
		"eos_calculation_notes": notes,
	}
