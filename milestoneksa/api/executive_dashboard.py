# Copyright (c) 2026, Milestoneksa and contributors
# License: MIT
"""CEO Executive KPI Dashboard API."""

from __future__ import annotations

import hashlib

import frappe
from frappe import _
from frappe.utils import (
	add_days,
	cint,
	flt,
	get_datetime,
	get_first_day,
	get_last_day,
	get_quarter_start,
	getdate,
	now_datetime,
	today,
)

UNAVAILABLE = "غير متوفر في النظام"
UNSPECIFIED = "غير محدد"
# Include upstream approval queue so CEO sees the payment pipeline (not only CEO state)
CEO_PENDING_STATES = (
	"Pending CEO Approval",
	"Pending CFO Approval",
	"Pending COO Approval",
)
PAR_DOCTYPE = "Payment Approval Request"


def _settings():
	return frappe.get_single("Executive Dashboard Settings")


def _flag(val) -> bool:
	return bool(cint(val))


def _assert_access(settings=None):
	settings = settings or _settings()
	roles = set(frappe.get_roles())
	if "CEO" in roles:
		return
	if "System Manager" in roles and _flag(settings.allow_system_manager_access):
		return
	frappe.throw(_("Not permitted to access the Executive Dashboard."), frappe.PermissionError)


def _permitted_companies() -> list[str]:
	user = frappe.session.user
	if user == "Administrator" or "System Manager" in frappe.get_roles():
		return frappe.get_all("Company", pluck="name")
	perms = frappe.get_all(
		"User Permission",
		filters={"user": user, "allow": "Company"},
		pluck="for_value",
	)
	if perms:
		return perms
	default = frappe.db.get_value("User", user, "company") or frappe.defaults.get_user_default(
		"Company"
	)
	if default:
		return [default]
	return frappe.get_all("Company", pluck="name")


def _resolve_company(company: str | None, settings) -> str:
	permitted = _permitted_companies()
	if not permitted:
		frappe.throw(_("No permitted company found for this user."))
	chosen = company or settings.default_company or permitted[0]
	if chosen not in permitted:
		frappe.throw(_("You are not permitted to view data for company {0}.").format(chosen))
	return chosen


def _resolve_dates(from_date=None, to_date=None, settings=None):
	settings = settings or _settings()
	if from_date and to_date:
		return getdate(from_date), getdate(to_date)

	today_d = getdate(today())
	rng = settings.default_date_range or "Current Month"

	if rng == "Current Month":
		return get_first_day(today_d), get_last_day(today_d)
	if rng == "Current Quarter":
		start = get_quarter_start(today_d)
		return start, get_last_day(add_days(start, 80))
	if rng == "Current Fiscal Year":
		fy = frappe.db.get_value(
			"Fiscal Year",
			{"year_start_date": ["<=", today_d], "year_end_date": [">=", today_d]},
			["year_start_date", "year_end_date"],
			as_dict=True,
		)
		if fy:
			return getdate(fy.year_start_date), getdate(fy.year_end_date)
		return getdate(f"{today_d.year}-01-01"), today_d
	if rng == "Last 30 Days":
		return add_days(today_d, -30), today_d
	if rng == "Last 90 Days":
		return add_days(today_d, -90), today_d
	return get_first_day(today_d), get_last_day(today_d)


def _sales_amount_field(basis: str) -> str:
	return {
		"Net Total": "net_total",
		"Grand Total": "grand_total",
		"Base Net Total": "base_net_total",
		"Base Grand Total": "base_grand_total",
	}.get(basis or "Grand Total", "grand_total")


def _freshness(max_hours, source_updated_at=None) -> dict:
	calculated_at = now_datetime()
	is_stale = False
	stale_reason = None
	threshold = int(max_hours or 24)
	if source_updated_at:
		try:
			src = get_datetime(source_updated_at)
			age_h = (calculated_at - src).total_seconds() / 3600.0
			if age_h > threshold:
				is_stale = True
				stale_reason = _("Source data older than {0} hours").format(threshold)
		except Exception:
			pass
	return {
		"calculated_at": str(calculated_at),
		"source_updated_at": str(source_updated_at) if source_updated_at else None,
		"is_stale": is_stale,
		"freshness_threshold_hours": threshold,
		"stale_reason": stale_reason,
	}


def _kpi(value, *, available=True, label="", meta=None):
	return {
		"value": value if available else None,
		"available": available,
		"label": label,
		"message": None if available else UNAVAILABLE,
		"meta": meta or {},
	}


def _project_statuses(settings) -> list[str]:
	"""Return project statuses to include. Empty / All → every Project status in use."""
	raw = (settings.active_project_statuses or "").strip()
	if not raw or raw.lower() in {"all", "*", "الكل"}:
		statuses = frappe.get_all("Project", pluck="status", distinct=True)
		return [s for s in statuses if s] or ["Open", "Completed"]
	return [s.strip() for s in raw.replace("\n", ",").split(",") if s.strip()]


def _target_project_names(settings) -> list[str]:
	"""Explicit target projects from settings; empty → use status filter instead."""
	names = []
	for row in settings.target_projects or []:
		if not row.project:
			continue
		if hasattr(row, "include_in_dashboard") and not _flag(row.include_in_dashboard):
			continue
		names.append(row.project)
	return names


def _get_cash_accounts(settings, company: str) -> list[str]:
	"""Only explicitly configured cash accounts — never silent Bank/Cash fallback."""
	excluded = {row.account for row in (settings.excluded_cash_accounts or []) if row.account}
	included = []
	for row in settings.cash_accounts or []:
		if not row.account or not _flag(row.include_in_cash):
			continue
		if row.account in excluded:
			continue
		if _flag(row.restricted) and not _flag(settings.include_restricted_cash):
			continue
		acct_company = frappe.db.get_value("Account", row.account, "company")
		if acct_company and acct_company != company:
			continue
		included.append(row.account)
	return included


def _account_balance(account: str, company: str) -> float:
	val = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(debit) - SUM(credit), 0)
		FROM `tabGL Entry`
		WHERE account=%s AND company=%s AND is_cancelled=0
		""",
		(account, company),
	)
	return flt(val[0][0]) if val else 0.0


def _get_collections(settings, company, from_date, to_date) -> float:
	src = settings.collections_source or "Allocated Payment References"
	if src == "Allocated Payment References":
		val = frappe.db.sql(
			"""
			SELECT COALESCE(SUM(per.allocated_amount), 0)
			FROM `tabPayment Entry Reference` per
			INNER JOIN `tabPayment Entry` pe ON pe.name = per.parent
			WHERE pe.docstatus=1 AND pe.company=%s
			  AND pe.posting_date BETWEEN %s AND %s
			  AND per.reference_doctype='Sales Invoice'
			""",
			(company, from_date, to_date),
		)
		return flt(val[0][0]) if val else 0.0
	if src == "Invoice Paid Amount":
		val = frappe.db.sql(
			"""
			SELECT COALESCE(SUM(grand_total - outstanding_amount), 0)
			FROM `tabSales Invoice`
			WHERE docstatus=1 AND company=%s AND posting_date BETWEEN %s AND %s
			""",
			(company, from_date, to_date),
		)
		return flt(val[0][0]) if val else 0.0
	val = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(paid_amount), 0)
		FROM `tabPayment Entry`
		WHERE docstatus=1 AND company=%s AND posting_date BETWEEN %s AND %s
		  AND payment_type='Receive'
		""",
		(company, from_date, to_date),
	)
	return flt(val[0][0]) if val else 0.0


def _build_company_summary(settings, company, from_date, to_date) -> dict:
	target_names = _target_project_names(settings)
	filters = {"company": company}
	if target_names:
		filters["name"] = ["in", target_names]
	else:
		filters["status"] = ["in", _project_statuses(settings)]
	projects = frappe.get_all(
		"Project",
		filters=filters,
		fields=[
			"name",
			"estimated_costing",
			"total_sales_amount",
			"per_gross_margin",
			"total_purchase_cost",
			"total_cost_from_journal_entry",
			"total_costing_amount",
			"modified",
		],
	)
	src_mod = max((p.modified for p in projects), default=None)

	p_source = settings.portfolio_value_source or "Project Estimated Cost"
	portfolio_available = True
	portfolio_value = 0.0
	invested_total = sum(_project_invested_cost(p) for p in projects)

	if p_source == "Project Estimated Cost":
		portfolio_value = sum(flt(p.estimated_costing) for p in projects)
		# Site often leaves estimated_costing empty — fall back to invested cost
		if not portfolio_value and invested_total:
			portfolio_value = invested_total
	elif p_source == "Project Purchase + Journal Cost":
		portfolio_value = invested_total
	elif p_source == "Project Expected Sales":
		portfolio_value = sum(flt(p.total_sales_amount) for p in projects)
	elif p_source == "Submitted Sales Invoices":
		amt_field = _sales_amount_field(settings.sales_amount_basis)
		portfolio_value = flt(
			frappe.db.sql(
				f"""
				SELECT COALESCE(SUM(`{amt_field}`), 0) FROM `tabSales Invoice`
				WHERE docstatus=1 AND company=%s AND posting_date BETWEEN %s AND %s
				""",
				(company, from_date, to_date),
			)[0][0]
		)
	elif p_source == "Custom Field":
		field = (settings.portfolio_custom_field or "").strip()
		if not field or not frappe.db.has_column("tabProject", field):
			portfolio_available = False
		else:
			vals = frappe.get_all(
				"Project",
				filters={"company": company, "status": ["in", statuses]},
				fields=[field],
			)
			portfolio_value = sum(flt(v.get(field)) for v in vals)
	else:
		portfolio_available = False

	cash_accounts = _get_cash_accounts(settings, company)
	cash_available = bool(cash_accounts)
	cash_value = sum(_account_balance(a, company) for a in cash_accounts) if cash_accounts else None
	cash_kpi = _kpi(
		cash_value,
		available=cash_available,
		label="النقد المتاح",
		meta={"accounts_configured": len(cash_accounts)},
	)
	if not cash_available:
		cash_kpi["message"] = "يرجى تكوين حسابات النقد في إعدادات لوحة المؤشرات التنفيذية"

	amt_field = _sales_amount_field(settings.sales_amount_basis)
	is_return_clause = "" if _flag(settings.include_sales_returns) else " AND IFNULL(is_return,0)=0 "
	sales_value = flt(
		frappe.db.sql(
			f"""
			SELECT COALESCE(SUM(`{amt_field}`), 0) FROM `tabSales Invoice`
			WHERE docstatus=1 AND company=%s AND posting_date BETWEEN %s AND %s
			{is_return_clause}
			""",
			(company, from_date, to_date),
		)[0][0]
	)
	collections_value = _get_collections(settings, company, from_date, to_date)

	margins = [flt(p.per_gross_margin) for p in projects if flt(p.total_sales_amount) > 0]
	margin_available = bool(margins)
	margin_value = (sum(margins) / len(margins)) if margins else None

	return {
		"freshness": _freshness(settings.project_data_max_age_hours, src_mod),
		"kpis": {
			"portfolio_value": _kpi(portfolio_value, available=portfolio_available, label="قيمة المحفظة"),
			"available_cash": cash_kpi,
			"sales": _kpi(sales_value, available=True, label="المبيعات"),
			"collections": _kpi(collections_value, available=True, label="التحصيل"),
			"expected_margin": _kpi(margin_value, available=margin_available, label="هامش الربح المتوقع"),
		},
		"targets": {
			"monthly_sales_target": flt(settings.monthly_sales_target) or None,
			"monthly_collection_target": flt(settings.monthly_collection_target) or None,
			"minimum_cash_target": flt(settings.minimum_cash_target) or None,
			"expected_margin_target": flt(settings.expected_margin_target) or None,
		},
	}


def _project_progress(project_name: str, percent_complete: float, settings) -> float:
	src = settings.project_progress_source or "Project Percent Complete"
	if src == "Project Percent Complete":
		return flt(percent_complete)
	if src == "Task Completion":
		total = frappe.db.count("Task", {"project": project_name})
		if not total:
			return flt(percent_complete)
		done = frappe.db.count("Task", {"project": project_name, "status": "Completed"})
		return flt(done) * 100.0 / total
	if src == "Task Progress":
		rows = frappe.get_all("Task", filters={"project": project_name}, fields=["progress"])
		if not rows:
			return flt(percent_complete)
		return sum(flt(r.progress) for r in rows) / len(rows)
	return flt(percent_complete)


def _project_invested_cost(project_row) -> float:
	"""PI + Journal costs — populated on this site; timesheet costing is often empty."""
	return flt(project_row.get("total_purchase_cost")) + flt(
		project_row.get("total_cost_from_journal_entry")
	)


def _project_actual_cost(project_name: str, project_row, settings, company) -> float:
	src = settings.project_cost_source or "Project Actual Cost"
	invested = _project_invested_cost(project_row)
	if src in ("Project Actual Cost", "Project Purchase + Journal Cost"):
		# Prefer timesheet/billing costing when present; otherwise invested cost
		base = flt(project_row.get("total_costing_amount"))
		if src == "Project Purchase + Journal Cost":
			return invested
		return base if base > 0 else invested
	if src == "Purchase Invoices":
		if invested and flt(project_row.get("total_purchase_cost")):
			return flt(project_row.get("total_purchase_cost"))
		val = frappe.db.sql(
			"""
			SELECT COALESCE(SUM(grand_total), 0) FROM `tabPurchase Invoice`
			WHERE docstatus=1 AND company=%s AND project=%s
			""",
			(company, project_name),
		)
		return flt(val[0][0]) if val else 0.0
	if src == "General Ledger":
		val = frappe.db.sql(
			"""
			SELECT COALESCE(SUM(debit) - SUM(credit), 0)
			FROM `tabGL Entry`
			WHERE company=%s AND project=%s AND is_cancelled=0
			""",
			(company, project_name),
		)
		return flt(val[0][0]) if val else 0.0
	if src == "Existing Financial Summary API":
		try:
			from milestoneksa.api.project_financial_summary import get_financial_summary_data

			data = get_financial_summary_data(project_name) or {}
			costs = data.get("costs") or {}
			total = flt(costs.get("total"))
			return total if total else invested
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Executive Dashboard Financial Summary")
			return invested
	return invested if invested else flt(project_row.get("total_costing_amount"))


def _rag_for_project(delay_days, cost_variance_pct, settings) -> str:
	red_d = int(settings.red_project_delay_days or 14)
	yel_d = int(settings.yellow_project_delay_days or 1)
	red_c = flt(settings.red_cost_variance_percent or 10)
	yel_c = flt(settings.yellow_cost_variance_percent or 5)

	severity = "green"
	if delay_days is not None:
		if delay_days >= red_d:
			severity = "red"
		elif delay_days >= yel_d:
			severity = "yellow"
	if cost_variance_pct is not None:
		if cost_variance_pct >= red_c:
			severity = "red"
		elif cost_variance_pct >= yel_c and severity != "red":
			severity = "yellow"
	return severity


def _project_paid_amount(project_name: str, company: str) -> float:
	"""Cash paid against project: Payment Entry (Pay) on project + PE linked via PI."""
	direct = flt(
		frappe.db.sql(
			"""
			SELECT COALESCE(SUM(paid_amount), 0)
			FROM `tabPayment Entry`
			WHERE docstatus=1 AND company=%s AND payment_type='Pay' AND project=%s
			""",
			(company, project_name),
		)[0][0]
	)
	# Allocations to Purchase Invoices of this project when PE.project is empty
	via_pi = flt(
		frappe.db.sql(
			"""
			SELECT COALESCE(SUM(per.allocated_amount), 0)
			FROM `tabPayment Entry Reference` per
			INNER JOIN `tabPayment Entry` pe ON pe.name = per.parent
			INNER JOIN `tabPurchase Invoice` pi ON pi.name = per.reference_name
			WHERE pe.docstatus=1 AND pe.company=%s AND pe.payment_type='Pay'
			  AND per.reference_doctype='Purchase Invoice'
			  AND pi.project=%s
			  AND IFNULL(pe.project, '') = ''
			""",
			(company, project_name),
		)[0][0]
	)
	return direct + via_pi


def _project_po_commitment(project_name: str, company: str) -> dict:
	"""Submitted Purchase Orders: committed total and unbilled remaining."""
	rows = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(grand_total), 0) AS committed,
		       COALESCE(SUM(grand_total * (100 - IFNULL(per_billed, 0)) / 100), 0) AS remaining
		FROM `tabPurchase Order`
		WHERE docstatus=1 AND company=%s AND project=%s
		""",
		(company, project_name),
		as_dict=True,
	)
	if not rows:
		return {"committed": 0.0, "remaining": 0.0}
	return {"committed": flt(rows[0].committed), "remaining": flt(rows[0].remaining)}


def _project_missing_fields(project_row, budget: float, paid: float, actual: float) -> list[dict]:
	"""Fields accounting should fill so executive KPIs are complete."""
	missing = []
	if not budget:
		missing.append(
			{
				"field": "estimated_costing",
				"label": "تقدير الميزانية (Estimated Costing)",
				"reason": "مطلوب لحساب المتبقي والانحراف عن التقدير",
			}
		)
	if not project_row.get("expected_end_date") and project_row.get("status") == "Open":
		missing.append(
			{
				"field": "expected_end_date",
				"label": "تاريخ الانتهاء المتوقع",
				"reason": "مطلوب لحساب التأخير",
			}
		)
	if budget and paid <= 0 and actual <= 0:
		missing.append(
			{
				"field": "payments_or_costs",
				"label": "مدفوعات / تكاليف مرتبطة بالمشروع",
				"reason": "لا توجد دفعات أو تكاليف مرحلة على المشروع",
			}
		)
	return missing


def _build_projects(settings, company) -> dict:
	target_names = _target_project_names(settings)
	filters = {"company": company}
	if target_names:
		filters["name"] = ["in", target_names]
	else:
		filters["status"] = ["in", _project_statuses(settings)]
	projects = frappe.get_all(
		"Project",
		filters=filters,
		fields=[
			"name",
			"project_name",
			"status",
			"percent_complete",
			"estimated_costing",
			"total_costing_amount",
			"total_purchase_cost",
			"total_cost_from_journal_entry",
			"total_sales_amount",
			"expected_end_date",
			"actual_end_date",
			"modified",
		],
		order_by="project_name asc",
	)
	src_mod = max((p.modified for p in projects), default=None)
	today_d = getdate(today())
	rows = []
	missing_budget_names = []
	for p in projects:
		progress = _project_progress(p.name, p.percent_complete, settings)
		budget = flt(p.estimated_costing)
		budget_available = budget > 0
		actual = _project_actual_cost(p.name, p, settings, company)
		paid = _project_paid_amount(p.name, company)
		po = _project_po_commitment(p.name, company)
		remaining_budget = (budget - paid) if budget_available else None
		# If no PE paid but we have actual cost, treat actual as spent-to-date for remaining
		spent_for_remain = paid if paid > 0 else actual
		remaining_vs_estimate = (budget - spent_for_remain) if budget_available else None
		cost_var = ((actual - budget) / budget * 100.0) if budget_available else None

		delay_days = None
		if p.expected_end_date:
			exp = getdate(p.expected_end_date)
			if p.actual_end_date:
				delay_days = (getdate(p.actual_end_date) - exp).days
			elif today_d > exp:
				delay_days = (today_d - exp).days
			else:
				delay_days = 0

		missing = _project_missing_fields(p, budget, paid, actual)
		if not budget_available:
			missing_budget_names.append(p.project_name or p.name)

		rag = _rag_for_project(delay_days, cost_var, settings)
		rows.append(
			{
				"name": p.name,
				"project_name": p.project_name or p.name,
				"status": p.status,
				"progress_actual": progress,
				"progress_planned": None,
				"progress_planned_available": False,
				"delay_days": delay_days,
				"budget": budget,
				"budget_available": budget_available,
				"paid": paid,
				"remaining_budget": remaining_budget,
				"remaining_vs_estimate": remaining_vs_estimate,
				"actual_cost": actual,
				"po_committed": po["committed"],
				"po_remaining": po["remaining"],
				"cost_variance_percent": cost_var,
				"sales": flt(p.total_sales_amount),
				"missing_fields": missing,
				"rag": rag,
			}
		)

	return {
		"freshness": _freshness(settings.project_data_max_age_hours, src_mod),
		"projects": rows,
		"data_gaps": {
			"projects_missing_budget": missing_budget_names,
			"missing_budget_count": len(missing_budget_names),
			"note": (
				"حقل تقدير الميزانية (estimated_costing) غير مُعبّأ في المشاريع أدناه. "
				"يُرجى من المحاسبة إدخال تقدير التكلفة لكل مشروع لاحتساب المتبقي والانحراف."
				if missing_budget_names
				else None
			),
		},
	}


def _build_liquidity(settings, company, from_date, to_date) -> dict:
	yel_days = int(settings.yellow_collection_overdue_days or 7)
	red_days = int(settings.red_collection_overdue_days or 30)
	today_d = getdate(today())

	overdue = frappe.db.sql(
		"""
		SELECT name, customer, outstanding_amount, due_date, modified
		FROM `tabSales Invoice`
		WHERE docstatus=1 AND company=%s AND outstanding_amount>0
		  AND due_date < %s
		ORDER BY due_date asc
		LIMIT 50
		""",
		(company, today_d),
		as_dict=True,
	)
	overdue_total = sum(flt(r.outstanding_amount) for r in overdue)
	src_mod = max((r.modified for r in overdue), default=None)

	due_in_period = flt(
		frappe.db.sql(
			"""
			SELECT COALESCE(SUM(outstanding_amount),0) FROM `tabSales Invoice`
			WHERE docstatus=1 AND company=%s AND due_date BETWEEN %s AND %s
			""",
			(company, from_date, to_date),
		)[0][0]
	)
	collections = _get_collections(settings, company, from_date, to_date)

	forecast_days = int(settings.forecast_days or 90)
	forecast_end = add_days(today_d, forecast_days)
	inflows = flt(
		frappe.db.sql(
			"""
			SELECT COALESCE(SUM(outstanding_amount),0) FROM `tabSales Invoice`
			WHERE docstatus=1 AND company=%s AND outstanding_amount>0
			  AND due_date BETWEEN %s AND %s
			""",
			(company, today_d, forecast_end),
		)[0][0]
	)
	outflows_pi = flt(
		frappe.db.sql(
			"""
			SELECT COALESCE(SUM(outstanding_amount),0) FROM `tabPurchase Invoice`
			WHERE docstatus=1 AND company=%s AND outstanding_amount>0
			  AND due_date BETWEEN %s AND %s
			""",
			(company, today_d, forecast_end),
		)[0][0]
	)
	par_pending = 0.0
	if frappe.db.exists("DocType", PAR_DOCTYPE):
		par_pending = flt(
			frappe.db.sql(
				f"""
				SELECT COALESCE(SUM(amount),0) FROM `tab{PAR_DOCTYPE}`
				WHERE workflow_state IN %s
				""",
				(CEO_PENDING_STATES,),
			)[0][0]
		)

	cash_accounts = _get_cash_accounts(settings, company)
	cash = sum(_account_balance(a, company) for a in cash_accounts) if cash_accounts else 0.0
	net_forecast = inflows - outflows_pi
	funding_gap = max(0.0, (outflows_pi - inflows) - cash) if cash_accounts else None

	return {
		"freshness": _freshness(settings.collection_data_max_age_hours, src_mod),
		"unavailable_kpis": _property_unit_kpis(company),
		"collections_vs_due": {
			"collections": collections,
			"due_outstanding": due_in_period,
		},
		"overdue_receivables": {
			"total": overdue_total,
			"count": len(overdue),
			"yellow_days": yel_days,
			"red_days": red_days,
			"samples": [
				{
					"name": r.name,
					"customer": r.customer,
					"outstanding": flt(r.outstanding_amount),
					"due_date": str(r.due_date),
					"overdue_days": (today_d - getdate(r.due_date)).days,
				}
				for r in overdue[:10]
			],
		},
		"cash_forecast": {
			"available": True,
			"is_estimate": True,
			"label": "التدفق المتوقع (تقدير)",
			"forecast_days": forecast_days,
			"expected_inflows": inflows,
			"expected_outflows_pi": outflows_pi,
			"pending_ceo_approvals_amount": par_pending,
			"net_estimate": net_forecast,
			"note": "تقدير تقريبي من فواتير المبيعات والمشتريات المستحقة؛ مبالغ اعتمادات الصرف معروضة منفصلة.",
		},
		"funding_gap": _kpi(
			funding_gap,
			available=bool(cash_accounts),
			label="فجوة التمويل",
			meta={"is_estimate": True},
		),
		"available_cash": _kpi(
			cash if cash_accounts else None,
			available=bool(cash_accounts),
			label="النقد المتاح",
		),
	}


def _property_unit_kpis(company: str) -> dict:
	"""Map Property Units statuses into executive inventory KPIs when the DocType exists."""
	sold = _kpi(None, available=False, label="الوحدات المباعة")
	remaining = _kpi(None, available=False, label="الوحدات المتبقية")
	reservations = _kpi(None, available=False, label="الحجوزات")
	cancellations = _kpi(None, available=False, label="الإلغاءات")

	if not frappe.db.exists("DocType", "Property Units"):
		return {
			"units_sold": sold,
			"units_remaining": remaining,
			"reservations": reservations,
			"cancellations": cancellations,
		}

	project_names = frappe.get_all("Project", filters={"company": company}, pluck="name")
	if project_names:
		rows = frappe.db.sql(
			"""
			SELECT status, COUNT(*) AS cnt
			FROM `tabProperty Units`
			WHERE project IN %s
			GROUP BY status
			""",
			(project_names,),
			as_dict=True,
		)
	else:
		rows = []

	# Many units point at legacy/missing projects — fall back to all units on single-company sites
	if not rows:
		rows = frappe.db.sql(
			"""
			SELECT status, COUNT(*) AS cnt
			FROM `tabProperty Units`
			GROUP BY status
			""",
			as_dict=True,
		)

	counts = {r.status: int(r.cnt) for r in rows}

	def _sum_matching(*needles):
		total = 0
		for status, cnt in counts.items():
			s = (status or "").lower()
			if any(n.lower() in s for n in needles):
				total += cnt
		return total

	# Statuses: Available / متوفرة, Reserved / محجوزة, Not Available / غير متوفرة
	available_cnt = _sum_matching("Available", "متوفرة")
	not_available_cnt = _sum_matching("Not Available", "غير متوفرة")
	available_cnt = max(0, available_cnt - not_available_cnt)
	reserved_cnt = _sum_matching("Reserved", "محجوزة")
	remaining = _kpi(available_cnt, available=True, label="الوحدات المتبقية")
	reservations = _kpi(reserved_cnt, available=True, label="الحجوزات")
	sold["message"] = "لا توجد حالة «مباع» في وحدات العقارات"
	cancellations["message"] = "لا توجد حالة «ملغى» في وحدات العقارات"

	return {
		"units_sold": sold,
		"units_remaining": remaining,
		"reservations": reservations,
		"cancellations": cancellations,
	}


def _alert_id(*parts) -> str:
	raw = "|".join(str(p) for p in parts)
	return hashlib.sha1(raw.encode()).hexdigest()[:16]


def _build_alerts(settings, company, projects_payload, liquidity_payload) -> dict:
	alerts = []
	today_d = getdate(today())

	for p in projects_payload.get("projects") or []:
		# Missing budget / estimate — ask accounting to fill Project.estimated_costing
		if not p.get("budget_available"):
			alerts.append(
				{
					"id": _alert_id("missing-budget", p["name"]),
					"severity": "yellow",
					"problem": _("نقص بيانات: تقدير الميزانية غير مُدخل للمشروع {0}").format(
						p["project_name"]
					),
					"impact_time_days": None,
					"impact_cost": None,
					"impact_liquidity": None,
					"recommended_action": _(
						"يُرجى من المحاسبة إدخال Estimated Costing في بطاقة المشروع لاحتساب المتبقي والانحراف"
					),
					"owner": _("المحاسبة"),
					"deadline": UNSPECIFIED,
					"ref_doctype": "Project",
					"ref_name": p["name"],
					"data_timestamp": str(now_datetime()),
				}
			)

		if p.get("rag") == "red":
			alerts.append(
				{
					"id": _alert_id("project-delay", p["name"]),
					"severity": "red",
					"problem": _("تأخر أو تجاوز تكلفة في المشروع {0}").format(p["project_name"]),
					"impact_time_days": p.get("delay_days"),
					"impact_cost": (
						flt(p.get("actual_cost")) - flt(p.get("budget")) if p.get("budget") else None
					),
					"impact_liquidity": None,
					"recommended_action": _("مراجعة الجدول والتكلفة واتخاذ قرار فوري"),
					"owner": UNSPECIFIED,
					"deadline": UNSPECIFIED,
					"ref_doctype": "Project",
					"ref_name": p["name"],
					"data_timestamp": str(now_datetime()),
				}
			)
		elif p.get("rag") == "yellow":
			alerts.append(
				{
					"id": _alert_id("project-warn", p["name"]),
					"severity": "yellow",
					"problem": _("انحراف يحتاج تصحيحاً في المشروع {0}").format(p["project_name"]),
					"impact_time_days": p.get("delay_days"),
					"impact_cost": None,
					"impact_liquidity": None,
					"recommended_action": _("تعيين مسؤول وخطة تصحيح مع موعد"),
					"owner": UNSPECIFIED,
					"deadline": UNSPECIFIED,
					"ref_doctype": "Project",
					"ref_name": p["name"],
					"data_timestamp": str(now_datetime()),
				}
			)

	for s in (liquidity_payload.get("overdue_receivables") or {}).get("samples") or []:
		days = int(s.get("overdue_days") or 0)
		if days < int(settings.yellow_collection_overdue_days or 7):
			continue
		sev = "red" if days >= int(settings.red_collection_overdue_days or 30) else "yellow"
		alerts.append(
			{
				"id": _alert_id("si-overdue", s["name"]),
				"severity": sev,
				"problem": _("تحصيل متأخر: {0}").format(s["name"]),
				"impact_time_days": days,
				"impact_cost": None,
				"impact_liquidity": flt(s.get("outstanding")),
				"recommended_action": _("متابعة العميل وتحصيل المستحق"),
				"owner": UNSPECIFIED,
				"deadline": s.get("due_date") or UNSPECIFIED,
				"ref_doctype": "Sales Invoice",
				"ref_name": s["name"],
				"data_timestamp": str(now_datetime()),
			}
		)

	cash_kpi = liquidity_payload.get("available_cash") or {}
	if cash_kpi.get("available") and cash_kpi.get("value") is not None:
		cash = flt(cash_kpi["value"])
		red_min = flt(settings.red_minimum_cash_balance)
		yel_min = flt(settings.yellow_minimum_cash_balance)
		if red_min and cash <= red_min:
			alerts.append(
				{
					"id": _alert_id("cash-red", company),
					"severity": "red",
					"problem": _("النقد المتاح أقل من الحد الحرج"),
					"impact_time_days": None,
					"impact_cost": None,
					"impact_liquidity": cash,
					"recommended_action": _("مراجعة السيولة وتأمين تمويل"),
					"owner": UNSPECIFIED,
					"deadline": UNSPECIFIED,
					"ref_doctype": "Company",
					"ref_name": company,
					"data_timestamp": str(now_datetime()),
				}
			)
		elif yel_min and cash <= yel_min:
			alerts.append(
				{
					"id": _alert_id("cash-yellow", company),
					"severity": "yellow",
					"problem": _("النقد المتاح أقل من حد التحذير"),
					"impact_time_days": None,
					"impact_cost": None,
					"impact_liquidity": cash,
					"recommended_action": _("مراقبة التدفق النقدي عن قرب"),
					"owner": UNSPECIFIED,
					"deadline": UNSPECIFIED,
					"ref_doctype": "Company",
					"ref_name": company,
					"data_timestamp": str(now_datetime()),
				}
			)

	if frappe.db.exists("DocType", PAR_DOCTYPE):
		warn_d = int(settings.ceo_approval_warning_days or 2)
		crit_d = int(settings.ceo_approval_critical_days or 5)
		fields = ["name", "amount", "modified", "creation"]
		meta = frappe.get_meta(PAR_DOCTYPE)
		if meta.has_field("employee_name"):
			fields.append("employee_name")
		pars = frappe.get_all(
			PAR_DOCTYPE,
			filters={"workflow_state": ["in", list(CEO_PENDING_STATES)]},
			fields=fields,
			order_by="modified asc",
		)
		for par in pars:
			age = (today_d - getdate(par.creation)).days
			sev = "red" if age >= crit_d else "yellow"
			alerts.append(
				{
					"id": _alert_id("par-ceo", par.name),
					"severity": sev,
					"problem": _("طلب صرف بانتظار اعتماد الرئيس التنفيذي: {0}").format(par.name),
					"impact_time_days": age,
					"impact_cost": None,
					"impact_liquidity": flt(par.amount),
					"recommended_action": _("مراجعة واعتماد أو رفض الطلب"),
					"owner": getattr(par, "employee_name", None) or UNSPECIFIED,
					"deadline": UNSPECIFIED,
					"ref_doctype": PAR_DOCTYPE,
					"ref_name": par.name,
					"data_timestamp": str(par.modified),
				}
			)

	sev_rank = {"red": 0, "yellow": 1}

	def sort_key(a):
		return (
			sev_rank.get(a["severity"], 9),
			-(flt(a.get("impact_liquidity")) + flt(a.get("impact_cost"))),
			-(flt(a.get("impact_time_days"))),
		)

	alerts.sort(key=sort_key)
	max_n = int(settings.max_alerts_displayed or 10)
	return {
		"freshness": _freshness(settings.alert_data_max_age_hours),
		"alerts": alerts[:max_n],
		"total": len(alerts),
	}


@frappe.whitelist()
def get_executive_dashboard(company=None, from_date=None, to_date=None):
	"""Return CEO executive dashboard payload for the four zones."""
	settings = _settings()
	_assert_access(settings)

	if not _flag(settings.enabled):
		frappe.throw(_("Executive Dashboard is disabled in settings."))

	company = _resolve_company(company, settings)
	from_date, to_date = _resolve_dates(from_date, to_date, settings)
	currency = settings.dashboard_currency or frappe.get_cached_value(
		"Company", company, "default_currency"
	)

	payload = {
		"company": company,
		"currency": currency,
		"from_date": str(from_date),
		"to_date": str(to_date),
		"settings": {
			"forecast_days": int(settings.forecast_days or 90),
			"show_company_summary": _flag(settings.show_company_summary),
			"show_project_status": _flag(settings.show_project_status),
			"show_liquidity_and_sales": _flag(settings.show_liquidity_and_sales),
			"show_risks_and_decisions": _flag(settings.show_risks_and_decisions),
			"show_unavailable_kpis": _flag(settings.show_unavailable_kpis),
		},
	}

	projects_section = (
		_build_projects(settings, company) if _flag(settings.show_project_status) else None
	)
	liquidity_section = (
		_build_liquidity(settings, company, from_date, to_date)
		if _flag(settings.show_liquidity_and_sales)
		else None
	)

	if _flag(settings.show_company_summary):
		payload["company_summary"] = _build_company_summary(settings, company, from_date, to_date)
	if projects_section is not None:
		payload["projects"] = projects_section
	if liquidity_section is not None:
		payload["liquidity"] = liquidity_section
	if _flag(settings.show_risks_and_decisions):
		payload["alerts"] = _build_alerts(
			settings,
			company,
			projects_section or {"projects": []},
			liquidity_section or {},
		)

	return payload
