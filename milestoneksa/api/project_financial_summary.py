# -*- coding: utf-8 -*-
"""Financial Summary tab data for Project: costs, income, connected doctypes, active POs (contract with supplier)."""
from frappe import _
from frappe.query_builder import DocType
from frappe.query_builder.functions import Sum
from frappe.utils import flt, cint, getdate, add_to_date
from frappe.utils.data import get_first_day, get_last_day

import frappe


@frappe.whitelist()
def get_financial_summary_data(project: str) -> dict:
	"""Return costs, income, payment summary, POs, and all financial summary cards data."""
	if not project:
		frappe.throw(_("Project is required"))

	project_doc = frappe.get_doc("Project", project)
	costs = _get_costs(project, project_doc)
	income = _get_income(project, project_doc)
	connected_doctypes = _get_connected_doctypes(project)
	active_purchase_orders = _get_active_purchase_orders(project)
	all_po_totals = _get_all_project_po_totals(project)
	payment_summary = _get_payment_summary(costs, active_purchase_orders, project, project_doc, all_po_totals)
	last_month_invoiced, last_month_invoices = _get_last_month_invoiced(project)
	active_po_item_detail = _get_po_item_detail(project)
	supplier_payments_unallocated = _get_supplier_payments_unallocated_unreconciled(project)
	purchased_items_cost = get_project_purchased_items_cost(project)

	# New cards data
	gross_margin = _get_gross_margin(costs, income)
	budget_vs_actual = _get_budget_vs_actual(project_doc, costs)
	billed_vs_unbilled = _get_billed_vs_unbilled(project_doc, income)
	invoiced_this_month = _get_invoiced_this_month(project)
	outstanding_po = _get_outstanding_po(active_purchase_orders, project)
	identifier_activity_cost = _get_identifier_activity_cost_summary(project)
	sales_order_total = _get_sales_order_total(project)
	top_suppliers = _get_top_suppliers(project)
	cost_breakdown = _get_cost_breakdown(costs)
	payment_status = _get_payment_status(project)
	last_activity = _get_last_activity(project)
	alerts = _get_alerts(
		project, costs, income, payment_summary,
		len(supplier_payments_unallocated or []),
		budget_vs_actual,
	)

	return {
		"costs": costs,
		"income": income,
		"connected_doctypes": connected_doctypes,
		"active_purchase_orders": active_purchase_orders,
		"payment_summary": payment_summary,
		"last_month_invoiced": last_month_invoiced,
		"last_month_invoices": last_month_invoices,
		"active_po_item_detail": active_po_item_detail,
		"supplier_payments_unallocated_unreconciled": supplier_payments_unallocated,
		"purchased_items_cost": purchased_items_cost,
		"gross_margin": gross_margin,
		"budget_vs_actual": budget_vs_actual,
		"billed_vs_unbilled": billed_vs_unbilled,
		"invoiced_this_month": invoiced_this_month,
		"outstanding_po": outstanding_po,
		"identifier_activity_cost": identifier_activity_cost,
		"sales_order_total": sales_order_total,
		"top_suppliers": top_suppliers,
		"cost_breakdown": cost_breakdown,
		"payment_status": payment_status,
		"last_activity": last_activity,
		"alerts": alerts,
		"project_info": {
			"name": project_doc.name,
			"project_name": project_doc.project_name,
			"company": project_doc.company or "",
		},
	}


@frappe.whitelist()
def get_project_purchased_items_cost(project: str) -> dict:
	"""Return VAT-inclusive purchased item cost summary and PI line details for a project."""
	if not project:
		frappe.throw(_("Project is required"))

	rows = frappe.db.sql(
		"""
		SELECT
			pi.name AS purchase_invoice,
			pi.posting_date,
			pi.supplier,
			pi.supplier_name,
			COALESCE(NULLIF(pi_item.custom_activity_type, ''), pi.custom_activity_type) AS activity_type,
			COALESCE(NULLIF(pi_item.custom_project_identifier, ''), pi.custom_project_identifier) AS project_identifier,
			pi_item.item_code,
			pi_item.item_name,
			pi_item.uom,
			pi_item.qty,
			pi_item.base_net_amount,
			CASE
				WHEN COALESCE(pi.base_net_total, 0) > 0
				THEN pi_item.base_net_amount * (pi.base_grand_total / pi.base_net_total)
				ELSE pi_item.base_net_amount
			END AS base_amount_with_vat,
			COALESCE(NULLIF(pi_item.purchase_order, ''), po_from_item.parent, po_from_pr.parent) AS purchase_order
		FROM `tabPurchase Invoice Item` pi_item
		INNER JOIN `tabPurchase Invoice` pi ON pi.name = pi_item.parent
		LEFT JOIN `tabPurchase Order Item` po_from_item ON po_from_item.name = pi_item.po_detail
		LEFT JOIN `tabPurchase Receipt Item` pr_item ON pr_item.name = pi_item.pr_detail
		LEFT JOIN `tabPurchase Order Item` po_from_pr ON po_from_pr.name = pr_item.purchase_order_item
		LEFT JOIN `tabPurchase Order` po ON po.name = COALESCE(NULLIF(pi_item.purchase_order, ''), po_from_item.parent, po_from_pr.parent)
		WHERE pi.docstatus = 1
		AND (
			pi_item.project = %(project)s
			OR (COALESCE(pi_item.project, '') = '' AND pi.project = %(project)s)
			OR (po.name IS NOT NULL AND po.project = %(project)s)
			OR po_from_item.project = %(project)s
			OR po_from_pr.project = %(project)s
		)
		ORDER BY pi.posting_date DESC, pi.name DESC, pi_item.idx ASC
		""",
		{"project": project},
		as_dict=True,
	)

	item_summary_map = {}
	identifier_activity_summary_map = {}
	purchase_summary_map = {}
	total_net = 0
	total_with_vat = 0
	details = []

	for row in rows:
		item_code = row.get("item_code") or ""
		item_name = row.get("item_name") or item_code
		uom = row.get("uom") or ""
		qty = flt(row.get("qty"), 6)
		net_amount = flt(row.get("base_net_amount"), 2)
		amount_with_vat = flt(row.get("base_amount_with_vat"), 2)
		total_net += net_amount
		total_with_vat += amount_with_vat

		item_key = (item_code, item_name, uom)
		if item_key not in item_summary_map:
			item_summary_map[item_key] = {
				"item_code": item_code,
				"item_name": item_name,
				"uom": uom,
				"activity_types": set(),
				"project_identifiers": set(),
				"qty": 0,
				"net_amount": 0,
				"amount_with_vat": 0,
			}
		if row.get("activity_type"):
			item_summary_map[item_key]["activity_types"].add(row.get("activity_type"))
		if row.get("project_identifier"):
			item_summary_map[item_key]["project_identifiers"].add(row.get("project_identifier"))
		item_summary_map[item_key]["qty"] += qty
		item_summary_map[item_key]["net_amount"] += net_amount
		item_summary_map[item_key]["amount_with_vat"] += amount_with_vat

		project_identifier = row.get("project_identifier") or _("Not Set")
		activity_type = row.get("activity_type") or _("Not Set")
		identifier_activity_key = (project_identifier, activity_type)
		if identifier_activity_key not in identifier_activity_summary_map:
			identifier_activity_summary_map[identifier_activity_key] = {
				"project_identifier": project_identifier,
				"activity_type": activity_type,
				"purchase_invoices": set(),
				"qty": 0,
				"net_amount": 0,
				"amount_with_vat": 0,
			}
		if row.get("purchase_invoice"):
			identifier_activity_summary_map[identifier_activity_key]["purchase_invoices"].add(row.get("purchase_invoice"))
		identifier_activity_summary_map[identifier_activity_key]["qty"] += qty
		identifier_activity_summary_map[identifier_activity_key]["net_amount"] += net_amount
		identifier_activity_summary_map[identifier_activity_key]["amount_with_vat"] += amount_with_vat

		pi_name = row.get("purchase_invoice") or ""
		if pi_name not in purchase_summary_map:
			purchase_summary_map[pi_name] = {
				"purchase_invoice": pi_name,
				"posting_date": str(row.get("posting_date")) if row.get("posting_date") else "",
				"supplier": row.get("supplier") or "",
				"supplier_name": row.get("supplier_name") or row.get("supplier") or "",
				"activity_types": set(),
				"project_identifiers": set(),
				"purchase_orders": set(),
				"net_amount": 0,
				"amount_with_vat": 0,
			}
		if row.get("activity_type"):
			purchase_summary_map[pi_name]["activity_types"].add(row.get("activity_type"))
		if row.get("project_identifier"):
			purchase_summary_map[pi_name]["project_identifiers"].add(row.get("project_identifier"))
		if row.get("purchase_order"):
			purchase_summary_map[pi_name]["purchase_orders"].add(row.get("purchase_order"))
		purchase_summary_map[pi_name]["net_amount"] += net_amount
		purchase_summary_map[pi_name]["amount_with_vat"] += amount_with_vat

		details.append({
			"purchase_invoice": pi_name,
			"posting_date": str(row.get("posting_date")) if row.get("posting_date") else "",
			"supplier": row.get("supplier") or "",
			"supplier_name": row.get("supplier_name") or row.get("supplier") or "",
			"activity_type": row.get("activity_type") or "",
			"project_identifier": row.get("project_identifier") or "",
			"purchase_order": row.get("purchase_order") or "",
			"item_code": item_code,
			"item_name": item_name,
			"uom": uom,
			"qty": qty,
			"net_amount": net_amount,
			"amount_with_vat": amount_with_vat,
		})

	item_summary = []
	for item in item_summary_map.values():
		item["activity_types"] = ", ".join(sorted(item["activity_types"]))
		item["project_identifiers"] = ", ".join(sorted(item["project_identifiers"]))
		item_summary.append(item)
	item_summary = sorted(
		item_summary,
		key=lambda d: flt(d.get("amount_with_vat"), 0),
		reverse=True,
	)
	identifier_activity_summary = []
	for group in identifier_activity_summary_map.values():
		group["purchase_invoices"] = sorted(group["purchase_invoices"])
		identifier_activity_summary.append(group)
	identifier_activity_summary = sorted(
		identifier_activity_summary,
		key=lambda d: flt(d.get("amount_with_vat"), 0),
		reverse=True,
	)
	purchase_summary = []
	for purchase in purchase_summary_map.values():
		purchase["activity_types"] = ", ".join(sorted(purchase["activity_types"]))
		purchase["project_identifiers"] = ", ".join(sorted(purchase["project_identifiers"]))
		purchase["purchase_orders"] = ", ".join(sorted(purchase["purchase_orders"]))
		purchase_summary.append(purchase)
	purchase_summary = sorted(
		purchase_summary,
		key=lambda d: flt(d.get("amount_with_vat"), 0),
		reverse=True,
	)

	return {
		"item_summary": item_summary,
		"identifier_activity_summary": identifier_activity_summary,
		"purchase_summary": purchase_summary,
		"details": details,
		"totals": {
			"net_amount": flt(total_net, 2),
			"amount_with_vat": flt(total_with_vat, 2),
		},
	}


def _get_identifier_activity_cost_summary(project: str) -> dict:
	"""Combined PI + JE cost grouped by Project Identifier and Activity Type."""
	if not project:
		return {"rows": [], "totals": {}}

	group_map = {}
	totals = {
		"purchase_invoice_cost": 0,
		"journal_entry_cost": 0,
		"total_cost": 0,
	}

	def get_group(project_identifier, activity_type):
		project_identifier = project_identifier or _("Not Set")
		activity_type = activity_type or _("Not Set")
		key = (project_identifier, activity_type)
		if key not in group_map:
			group_map[key] = {
				"project_identifier": project_identifier,
				"activity_type": activity_type,
				"purchase_invoices": set(),
				"journal_entries": set(),
				"purchase_invoice_details": [],
				"journal_entry_details": [],
				"purchase_invoice_cost": 0,
				"journal_entry_cost": 0,
				"total_cost": 0,
			}
		return group_map[key]

	pi_rows = frappe.db.sql(
		"""
		SELECT
			pi.name AS purchase_invoice,
			pi.posting_date,
			pi.supplier,
			pi.supplier_name,
			COALESCE(NULLIF(pi_item.custom_activity_type, ''), pi.custom_activity_type) AS activity_type,
			COALESCE(NULLIF(pi_item.custom_project_identifier, ''), pi.custom_project_identifier) AS project_identifier,
			pi_item.item_code,
			pi_item.item_name,
			pi_item.qty,
			pi_item.base_net_amount,
			CASE
				WHEN COALESCE(pi.base_net_total, 0) > 0
				THEN pi_item.base_net_amount * (pi.base_grand_total / pi.base_net_total)
				ELSE pi_item.base_net_amount
			END AS amount_with_vat
		FROM `tabPurchase Invoice Item` pi_item
		INNER JOIN `tabPurchase Invoice` pi ON pi.name = pi_item.parent
		LEFT JOIN `tabPurchase Order Item` po_from_item ON po_from_item.name = pi_item.po_detail
		LEFT JOIN `tabPurchase Receipt Item` pr_item ON pr_item.name = pi_item.pr_detail
		LEFT JOIN `tabPurchase Order Item` po_from_pr ON po_from_pr.name = pr_item.purchase_order_item
		LEFT JOIN `tabPurchase Order` po ON po.name = COALESCE(NULLIF(pi_item.purchase_order, ''), po_from_item.parent, po_from_pr.parent)
		WHERE pi.docstatus = 1
		AND (
			pi_item.project = %(project)s
			OR (COALESCE(pi_item.project, '') = '' AND pi.project = %(project)s)
			OR (po.name IS NOT NULL AND po.project = %(project)s)
			OR po_from_item.project = %(project)s
			OR po_from_pr.project = %(project)s
		)
		""",
		{"project": project},
		as_dict=True,
	)
	for row in pi_rows or []:
		amount = flt(row.get("amount_with_vat"), 2)
		group = get_group(row.get("project_identifier"), row.get("activity_type"))
		if row.get("purchase_invoice"):
			group["purchase_invoices"].add(row.get("purchase_invoice"))
		group["purchase_invoice_details"].append({
			"purchase_invoice": row.get("purchase_invoice") or "",
			"posting_date": str(row.get("posting_date")) if row.get("posting_date") else "",
			"supplier": row.get("supplier") or "",
			"supplier_name": row.get("supplier_name") or row.get("supplier") or "",
			"item_code": row.get("item_code") or "",
			"item_name": row.get("item_name") or row.get("item_code") or "",
			"qty": flt(row.get("qty"), 6),
			"net_amount": flt(row.get("base_net_amount"), 2),
			"amount_with_vat": amount,
		})
		group["purchase_invoice_cost"] += amount
		group["total_cost"] += amount
		totals["purchase_invoice_cost"] += amount
		totals["total_cost"] += amount

	activity_field = (
		"jea.custom_activity_type"
		if frappe.db.has_column("Journal Entry Account", "custom_activity_type")
		else "''"
	)
	identifier_field = (
		"jea.custom_project_identifier"
		if frappe.db.has_column("Journal Entry Account", "custom_project_identifier")
		else "''"
	)
	je_rows = frappe.db.sql(
		f"""
		SELECT
			je.name AS journal_entry,
			je.posting_date,
			je.voucher_type,
			je.user_remark,
			jea.account,
			{activity_field} AS activity_type,
			{identifier_field} AS project_identifier,
			jea.debit AS amount
		FROM `tabJournal Entry Account` jea
		INNER JOIN `tabJournal Entry` je ON je.name = jea.parent
		WHERE je.docstatus = 1
			AND jea.project = %(project)s
			AND COALESCE(jea.debit, 0) > 0
		""",
		{"project": project},
		as_dict=True,
	)
	for row in je_rows or []:
		amount = flt(row.get("amount"), 2)
		group = get_group(row.get("project_identifier"), row.get("activity_type"))
		if row.get("journal_entry"):
			group["journal_entries"].add(row.get("journal_entry"))
		group["journal_entry_details"].append({
			"journal_entry": row.get("journal_entry") or "",
			"posting_date": str(row.get("posting_date")) if row.get("posting_date") else "",
			"voucher_type": row.get("voucher_type") or "",
			"account": row.get("account") or "",
			"user_remark": row.get("user_remark") or "",
			"amount": amount,
		})
		group["journal_entry_cost"] += amount
		group["total_cost"] += amount
		totals["journal_entry_cost"] += amount
		totals["total_cost"] += amount

	rows = []
	for row in group_map.values():
		row["purchase_invoices"] = sorted(row["purchase_invoices"])
		row["journal_entries"] = sorted(row["journal_entries"])
		row["purchase_invoice_cost"] = flt(row["purchase_invoice_cost"], 2)
		row["journal_entry_cost"] = flt(row["journal_entry_cost"], 2)
		row["total_cost"] = flt(row["total_cost"], 2)
		row["purchase_invoice_details"] = sorted(
			row["purchase_invoice_details"],
			key=lambda d: (d.get("posting_date") or "", d.get("purchase_invoice") or ""),
			reverse=True,
		)
		row["journal_entry_details"] = sorted(
			row["journal_entry_details"],
			key=lambda d: (d.get("posting_date") or "", d.get("journal_entry") or ""),
			reverse=True,
		)
		rows.append(row)
	rows = sorted(rows, key=lambda d: flt(d.get("total_cost"), 0), reverse=True)

	return {
		"rows": rows,
		"totals": {
			"purchase_invoice_cost": flt(totals["purchase_invoice_cost"], 2),
			"journal_entry_cost": flt(totals["journal_entry_cost"], 2),
			"total_cost": flt(totals["total_cost"], 2),
		},
	}


def _get_all_project_po_totals(project: str) -> list:
	"""All POs linked to project with grand_total, invoiced (tax included), remaining. No filter by remaining > 0."""
	po_names = frappe.db.sql(
		"""
		SELECT DISTINCT po.name
		FROM `tabPurchase Order` po
		LEFT JOIN `tabPurchase Order Item` poi ON poi.parent = po.name
		WHERE po.docstatus = 1
		AND (po.project = %s OR poi.project = %s)
		""",
		(project, project),
		as_list=True,
	)
	po_names = [r[0] for r in po_names] if po_names else []
	out = []
	for name in po_names:
		grand_total = _get_po_project_share_grand_total(name, project)
		invoiced_amount = _get_po_invoiced_amount_with_tax(name, project)
		remaining = grand_total - invoiced_amount
		out.append({"grand_total": grand_total, "invoiced_amount": invoiced_amount, "remaining": remaining})
	return out


def _get_payment_summary(costs: dict, active_purchase_orders: list, project: str = None, project_doc=None, all_po_totals: list = None) -> dict:
	"""Payment summary aligned with Active Purchase Orders: sum of Invoiced, sum of Remaining, sum of Grand Total for all POs."""
	if all_po_totals:
		total_paid_to_date = sum(flt(p.get("invoiced_amount", 0)) for p in all_po_totals)
		total_remaining_po = sum(flt(p.get("remaining", 0)) for p in all_po_totals)
		project_total_cost = sum(flt(p.get("grand_total", 0)) for p in all_po_totals)
	else:
		total_paid_to_date = flt(costs.get("total", 0))
		if project:
			from milestoneksa.milestoneksa.project import calculate_total_pending_po_cost
			total_remaining_po = flt(calculate_total_pending_po_cost(project))
		else:
			total_remaining_po = sum(flt(po.get("remaining", 0)) for po in (active_purchase_orders or []))
		project_total_cost = total_paid_to_date + total_remaining_po
	return {
		"total_paid_to_date": total_paid_to_date,
		"total_remaining_po": total_remaining_po,
		"project_total_cost": project_total_cost,
	}


def _get_last_month_invoiced(project: str) -> tuple:
	"""Invoiced in previous calendar month: PI and Journal Entry (debit), plus list of PIs for drill-down."""
	today = getdate()
	prev_month = add_to_date(today, months=-1)
	month_start = get_first_day(prev_month)
	month_end = get_last_day(prev_month)

	# Purchase Invoices linked to project (header or item) with posting_date in previous month
	pi = DocType("Purchase Invoice")
	pi_item = DocType("Purchase Invoice Item")
	# PIs with project on header
	pi_header = (
		frappe.qb.from_(pi)
		.select(pi.name, pi.posting_date, pi.supplier, pi.base_grand_total)
		.where(
			(pi.project == project)
			& (pi.docstatus == 1)
			& (pi.posting_date >= month_start)
			& (pi.posting_date <= month_end)
		)
		.run(as_dict=True)
	)
	# PIs with project on item only (exclude already in pi_header)
	header_names = [p.name for p in pi_header]
	pi_from_items = (
		frappe.qb.from_(pi_item)
		.inner_join(pi)
		.on(pi_item.parent == pi.name)
		.select(pi.name, pi.posting_date, pi.supplier, pi.base_grand_total)
		.where(
			(pi_item.project == project)
			& (pi.docstatus == 1)
			& (pi.posting_date >= month_start)
			& (pi.posting_date <= month_end)
		)
		.run(as_dict=True)
	)
	# Deduplicate by name (keep first occurrence)
	seen = set(header_names)
	pi_list = list(pi_header)
	for p in pi_from_items:
		if p.name not in seen:
			seen.add(p.name)
			pi_list.append(p)
	pi_list.sort(key=lambda x: (x.get("posting_date") or "", x.get("name") or ""))
	purchase_invoice_total = sum(flt(p.get("base_grand_total", 0)) for p in pi_list)
	last_month_invoices = [
		{
			"name": p.get("name"),
			"posting_date": str(p.get("posting_date")) if p.get("posting_date") else "",
			"supplier": p.get("supplier") or "",
			"base_grand_total": flt(p.get("base_grand_total", 0)),
		}
		for p in pi_list
	]

	# Journal Entry costs in last month (GL Entry debit, voucher_type = Journal Entry, project)
	gle = DocType("GL Entry")
	je_debit = (
		frappe.qb.from_(gle)
		.select(Sum(gle.debit))
		.where(
			(gle.project == project)
			& (gle.voucher_type == "Journal Entry")
			& (gle.is_cancelled == 0)
			& (gle.posting_date >= month_start)
			& (gle.posting_date <= month_end)
		)
		.run(as_list=True)
	)
	journal_entry_total = flt(je_debit[0][0]) if je_debit and je_debit[0][0] else 0

	total = purchase_invoice_total + journal_entry_total
	last_month_invoiced = {
		"purchase_invoice": purchase_invoice_total,
		"journal_entry": journal_entry_total,
		"total": total,
	}
	return last_month_invoiced, last_month_invoices


def _get_po_invoiced_amount_with_tax(po_name: str, project: str = None) -> float:
	"""Sum of PI item share of base_grand_total (tax included) for PIs linked to this PO (po_detail or pr_detail).
	When project is set, only count PO items that belong to this project (item.project = project or item project blank and header project = project)."""
	if not po_name:
		return 0
	# PO item names for this PO; when project given, only items belonging to that project
	if project:
		# COALESCE on po.project so NULL header project still matches when comparing to project
		po_item_subquery = """
			SELECT poi.name FROM `tabPurchase Order Item` poi
			INNER JOIN `tabPurchase Order` po ON po.name = poi.parent
			WHERE poi.parent = %(po_name)s
			  AND (poi.project = %(project)s OR (COALESCE(poi.project, '') = '' AND COALESCE(po.project, '') = %(project)s))
		"""
		sub_params = {"po_name": po_name, "project": project}
		po_item_names = frappe.db.sql(po_item_subquery, sub_params, as_list=True)
		po_item_names = [r[0] for r in po_item_names] if po_item_names else []
		# Fallback: PO linked by header only (items have no project) -> use all PO items for this PO
		if not po_item_names:
			po_header_project = frappe.db.get_value("Purchase Order", po_name, "project")
			if (po_header_project or "") == project:
				po_item_names = frappe.db.sql(
					"SELECT name FROM `tabPurchase Order Item` WHERE parent = %s", (po_name,), as_list=True
				)
				po_item_names = [r[0] for r in po_item_names] if po_item_names else []
			if not po_item_names:
				return 0
		placeholders = ", ".join(["%s"] * len(po_item_names))
		invoiced = frappe.db.sql(
			f"""
			SELECT COALESCE(SUM(
				CASE WHEN pi.base_net_total > 0 THEN pi_item.base_net_amount / pi.base_net_total * pi.base_grand_total
				ELSE pi_item.base_net_amount END
			), 0)
			FROM `tabPurchase Invoice Item` pi_item
			INNER JOIN `tabPurchase Invoice` pi ON pi.name = pi_item.parent
			LEFT JOIN `tabPurchase Receipt Item` pri ON pri.name = pi_item.pr_detail
			WHERE pi.docstatus = 1
			  AND (
				pi_item.po_detail IN ({placeholders})
				OR pri.purchase_order_item IN ({placeholders})
			  )
			""",
			po_item_names + po_item_names,
			as_list=True,
		)
	else:
		invoiced = frappe.db.sql(
			"""
			SELECT COALESCE(SUM(
				CASE WHEN pi.base_net_total > 0 THEN pi_item.base_net_amount / pi.base_net_total * pi.base_grand_total
				ELSE pi_item.base_net_amount END
			), 0)
			FROM `tabPurchase Invoice Item` pi_item
			INNER JOIN `tabPurchase Invoice` pi ON pi.name = pi_item.parent
			LEFT JOIN `tabPurchase Receipt Item` pri ON pri.name = pi_item.pr_detail
			WHERE pi.docstatus = 1
			  AND (
				pi_item.po_detail IN (SELECT name FROM `tabPurchase Order Item` WHERE parent = %s)
				OR pri.purchase_order_item IN (SELECT name FROM `tabPurchase Order Item` WHERE parent = %s)
			  )
			""",
			(po_name, po_name),
			as_list=True,
		)
	return flt(invoiced[0][0]) if invoiced and invoiced[0][0] else 0


def _get_po_project_share_grand_total(po_name: str, project: str) -> float:
	"""Project's share of PO grand_total (by proportion of item base_net_amount belonging to project)."""
	if not po_name or not project:
		return 0
	# Use COALESCE on PO project so NULL = %s doesn't exclude header-linked items
	row = frappe.db.sql(
		"""
		SELECT
			po.grand_total,
			po.project AS po_project,
			(SELECT SUM(poi.base_net_amount) FROM `tabPurchase Order Item` poi
			 WHERE poi.parent = %s AND (poi.project = %s OR (COALESCE(poi.project, '') = '' AND COALESCE((SELECT project FROM `tabPurchase Order` WHERE name = poi.parent), '') = %s))) AS project_net,
			(SELECT SUM(poi.base_net_amount) FROM `tabPurchase Order Item` poi WHERE poi.parent = %s) AS total_net
		FROM `tabPurchase Order` po
		WHERE po.name = %s
		""",
		(po_name, project, project, po_name, po_name),
		as_list=True,
	)
	if not row or not row[0][0]:
		return 0
	grand_total = flt(row[0][0])
	po_project = row[0][1]  # may be None
	project_net = flt(row[0][2])
	total_net = flt(row[0][3])
	if total_net and total_net > 0 and project_net:
		return flt(project_net / total_net * grand_total)
	# Fallback: PO linked by header (po.project = project) but no item-level project match (e.g. all items blank) -> treat full PO as project's share
	if grand_total and total_net and total_net > 0 and (not project_net or project_net == 0) and (po_project == project or (po_project or "") == project):
		return grand_total
	return 0


def _get_po_item_detail(project: str) -> list:
	"""Per-PO item-level detail: items with qty, received_qty, base_net_amount, billed_amt, remaining_amt."""
	po_names = frappe.db.sql(
		"""
		SELECT DISTINCT po.name
		FROM `tabPurchase Order` po
		LEFT JOIN `tabPurchase Order Item` poi ON poi.parent = po.name
		WHERE po.docstatus = 1
		AND (po.project = %s OR poi.project = %s)
		""",
		(project, project),
		as_list=True,
	)
	po_names = [r[0] for r in po_names] if po_names else []
	out = []
	for po_name in po_names:
		po_doc = frappe.db.get_value(
			"Purchase Order",
			po_name,
			["grand_total", "supplier", "status"],
			as_dict=True,
		)
		if not po_doc:
			continue
		# Include all items for this PO (PO is already linked by header or item project)
		items = frappe.db.get_all(
			"Purchase Order Item",
			filters={"parent": po_name},
			fields=["item_code", "item_name", "qty", "received_qty", "base_net_amount", "billed_amt"],
			order_by="idx",
		)
		item_rows = []
		for row in items:
			billed = flt(row.get("billed_amt", 0))
			ordered_val = flt(row.get("base_net_amount", 0))
			remaining_amt = ordered_val - billed
			item_rows.append({
				"item_code": row.get("item_code") or "",
				"item_name": row.get("item_name") or "",
				"qty": flt(row.get("qty", 0)),
				"received_qty": flt(row.get("received_qty", 0)),
				"base_net_amount": ordered_val,
				"billed_amt": billed,
				"remaining_amt": remaining_amt,
			})
		grand_total = _get_po_project_share_grand_total(po_name, project)
		invoiced_amount = _get_po_invoiced_amount_with_tax(po_name, project)
		remaining = grand_total - invoiced_amount
		invoices = _get_purchase_invoices_for_po(po_name)
		out.append({
			"po_name": po_name,
			"supplier": po_doc.get("supplier") or "",
			"grand_total": grand_total,
			"invoiced_amount": invoiced_amount,
			"remaining": remaining,
			"status": po_doc.get("status") or "",
			"items": item_rows,
			"invoices": invoices,
		})
	return out


def _get_purchase_invoices_for_po(po_name: str) -> list:
	"""Purchase Invoices linked to this PO (via pi_item.po_detail). Returns name, posting_date, supplier, grand_total, paid_amount, outstanding_amount."""
	po_item_names = frappe.db.sql_list(
		"""SELECT name FROM `tabPurchase Order Item` WHERE parent = %s""",
		(po_name,),
	)
	if not po_item_names:
		return []
	pi_names = frappe.db.sql_list(
		"""
		SELECT DISTINCT pi_item.parent
		FROM `tabPurchase Invoice Item` pi_item
		INNER JOIN `tabPurchase Invoice` pi ON pi.name = pi_item.parent AND pi.docstatus = 1
		WHERE pi_item.po_detail IN (%s)
		""" % (", ".join(["%s"] * len(po_item_names))),
		tuple(po_item_names),
	)
	if not pi_names:
		return []
	# Get PI header fields: grand_total (or rounded_total), outstanding_amount, paid_amount
	invoices = frappe.db.sql(
		"""
		SELECT name, posting_date, supplier, supplier_name,
			COALESCE(rounded_total, grand_total) AS grand_total,
			COALESCE(outstanding_amount, 0) AS outstanding_amount,
			COALESCE(paid_amount, 0) AS paid_amount
		FROM `tabPurchase Invoice`
		WHERE name IN (%s) AND docstatus = 1
		ORDER BY posting_date DESC, name DESC
		""" % (", ".join(["%s"] * len(pi_names))),
		tuple(pi_names),
		as_dict=True,
	)
	out = []
	for r in invoices:
		grand_total = flt(r.get("grand_total"), 0)
		outstanding = flt(r.get("outstanding_amount"), 0)
		paid = flt(r.get("paid_amount"), 0)
		if paid == 0 and grand_total and outstanding is not None:
			paid = grand_total - outstanding
		out.append({
			"name": r.get("name") or "",
			"posting_date": str(r.get("posting_date")) if r.get("posting_date") else "",
			"supplier": r.get("supplier") or "",
			"supplier_name": r.get("supplier_name") or r.get("supplier") or "",
			"grand_total": grand_total,
			"paid_amount": paid,
			"outstanding_amount": outstanding,
		})
	return out


def _get_supplier_payments_unallocated_unreconciled(project: str) -> list:
	"""Payment Entries to suppliers for the project: only those with empty Payment References (unallocated). If references exist, treated as reconciled and excluded."""
	pe_list = frappe.db.sql(
		"""
		SELECT
			pe.name,
			pe.posting_date,
			pe.party,
			pe.party_name,
			pe.paid_amount,
			pe.base_paid_amount,
			pe.total_allocated_amount,
			pe.unallocated_amount,
			pe.clearance_date
		FROM `tabPayment Entry` pe
		WHERE pe.party_type = 'Supplier'
			AND pe.docstatus = 1
			AND pe.project = %(project)s
			AND NOT EXISTS (
				SELECT 1 FROM `tabPayment Entry Reference` per
				WHERE per.parent = pe.name
			)
		ORDER BY pe.posting_date DESC, pe.name DESC
		""",
		{"project": project},
		as_dict=True,
	)
	out = []
	for r in pe_list:
		out.append({
			"name": r.get("name"),
			"posting_date": str(r.get("posting_date")) if r.get("posting_date") else "",
			"party": r.get("party") or "",
			"party_name": r.get("party_name") or "",
			"paid_amount": flt(r.get("paid_amount", 0)),
			"base_paid_amount": flt(r.get("base_paid_amount", 0)),
			"total_allocated_amount": flt(r.get("total_allocated_amount", 0)),
			"unallocated_amount": flt(r.get("unallocated_amount", 0)),
			"clearance_date": str(r.get("clearance_date")) if r.get("clearance_date") else "",
			"reconciled": 1 if r.get("clearance_date") else 0,
		})
	return out


def _get_costs(project: str, project_doc) -> dict:
	"""Costs: PI, Journal Entry/GL, Timesheet, Expense Claim, Consumed Material."""
	from milestoneksa.milestoneksa.project import (
		calculate_total_cost_from_journal_entry,
		calculate_total_purchase_cost_from_pi,
	)

	# Purchase Invoice: same logic as Project total_purchase_cost (item or header project)
	purchase_invoice = flt(calculate_total_purchase_cost_from_pi(project))

	journal_entry_gl = calculate_total_cost_from_journal_entry(project)
	timesheet = flt(project_doc.total_costing_amount)
	expense_claim = flt(project_doc.get("total_expense_claim", 0))
	consumed_material = flt(project_doc.get("total_consumed_material_cost", 0))

	total = (
		purchase_invoice
		+ journal_entry_gl
		+ timesheet
		+ expense_claim
		+ consumed_material
	)

	return {
		"purchase_invoice": purchase_invoice,
		"journal_entry_gl": journal_entry_gl,
		"timesheet": timesheet,
		"expense_claim": expense_claim,
		"consumed_material": consumed_material,
		"total": total,
	}


def _get_income(project: str, project_doc) -> dict:
	"""Income: Sales Invoice, Journal Entry/GL (credits)."""
	# Sales Invoice: sum base_net_amount from SI Item where project = X (project's share)
	si_item = DocType("Sales Invoice Item")
	si = DocType("Sales Invoice")
	si_total = (
		frappe.qb.from_(si_item)
		.inner_join(si)
		.on(si_item.parent == si.name)
		.select(Sum(si_item.base_net_amount))
		.where((si_item.project == project) & (si.docstatus == 1))
		.run(as_list=True)
	)
	sales_invoice = flt(si_total[0][0]) if si_total and si_total[0][0] else 0
	# SI with project on header only (no project on items)
	si_header = frappe.db.sql(
		"""
		SELECT SUM(base_net_total) FROM `tabSales Invoice`
		WHERE project = %s AND docstatus = 1
		AND name NOT IN (SELECT DISTINCT parent FROM `tabSales Invoice Item` WHERE project = %s)
		""",
		(project, project),
		as_list=True,
	)
	sales_invoice += flt(si_header[0][0]) if si_header and si_header[0][0] else 0

	# Income: only from Sales Invoices (no Journal Entry)
	total = sales_invoice

	return {
		"sales_invoice": sales_invoice,
		"total": total,
	}


def _get_connected_doctypes(project: str) -> list:
	"""Count of linked doctypes for the project."""
	doctypes_config = [
		("Sales Order", "project"),
		("Sales Invoice", "project"),
		("Purchase Order", "project"),
		("Purchase Invoice", "project"),
		("Timesheet", "project"),
		("Expense Claim", "project"),
		("Stock Entry", "project"),
		("Task", "project"),
	]
	out = []
	for doctype, field in doctypes_config:
		try:
			count = frappe.db.count(doctype, {field: project})
		except Exception:
			count = 0
		out.append({"doctype": doctype, "count": count})

	# Journal Entry: count distinct JE where at least one account row has project
	try:
		je_count = frappe.db.sql(
			"""
			SELECT COUNT(DISTINCT parent) FROM `tabJournal Entry Account`
			WHERE project = %s
			""",
			(project,),
			as_list=True,
		)
		je_count = cint(je_count[0][0]) if je_count and je_count[0][0] else 0
	except Exception:
		je_count = 0
	out.append({"doctype": "Journal Entry", "count": je_count})

	return out


def _get_active_purchase_orders(project: str) -> list:
	"""Active POs (contract with supplier): grand_total, invoiced_amount, remaining."""
	po = DocType("Purchase Order")
	po_item = DocType("Purchase Order Item")
	# POs where header project = X or any item has project = X
	po_names = frappe.db.sql(
		"""
		SELECT DISTINCT po.name
		FROM `tabPurchase Order` po
		LEFT JOIN `tabPurchase Order Item` poi ON poi.parent = po.name
		WHERE po.docstatus = 1
		AND (po.project = %s OR poi.project = %s)
		""",
		(project, project),
		as_list=True,
	)
	po_names = [r[0] for r in po_names] if po_names else []
	out = []
	for name in po_names:
		doc = frappe.db.get_value(
			"Purchase Order",
			name,
			["grand_total", "supplier", "status"],
			as_dict=True,
		)
		if not doc:
			continue
		grand_total = _get_po_project_share_grand_total(name, project)
		invoiced_amount = _get_po_invoiced_amount_with_tax(name, project)
		remaining = grand_total - invoiced_amount
		# Only include POs with remaining > 0 in the Active Purchase Orders list
		if flt(remaining) <= 0:
			continue
		out.append({
			"name": name,
			"supplier": doc.supplier or "",
			"grand_total": grand_total,
			"invoiced_amount": invoiced_amount,
			"remaining": remaining,
			"status": doc.status or "",
		})
	return out


def _get_gross_margin(costs: dict, income: dict) -> dict:
	"""Gross margin: profit and margin % from income - costs."""
	total_income = flt(income.get("total", 0))
	total_cost = flt(costs.get("total", 0))
	profit = total_income - total_cost
	margin_pct = (profit / total_income * 100) if total_income else 0
	return {"profit": profit, "margin_pct": margin_pct, "total_income": total_income, "total_cost": total_cost}


def _get_budget_vs_actual(project_doc, costs: dict) -> dict:
	"""Budget vs actual: estimated_costing vs total cost, variance."""
	estimated = flt(project_doc.get("estimated_costing", 0))
	actual = flt(costs.get("total", 0))
	variance = actual - estimated
	variance_pct = (variance / estimated * 100) if estimated else 0
	return {
		"estimated": estimated,
		"actual": actual,
		"variance": variance,
		"variance_pct": variance_pct,
		"over_budget": variance > 0,
	}


def _get_billed_vs_unbilled(project_doc, income: dict) -> dict:
	"""Billed (Sales Invoice) vs total Sales Order value, unbilled amount."""
	total_billed = flt(income.get("total", 0))
	total_sales_amount = flt(project_doc.get("total_sales_amount", 0))
	unbilled = total_sales_amount - total_billed
	return {
		"total_billed": total_billed,
		"total_sales_amount": total_sales_amount,
		"unbilled": unbilled,
	}


def _get_invoiced_this_month(project: str) -> float:
	"""Current calendar month: sum of PI (and JE debit) linked to project."""
	today = getdate()
	month_start = get_first_day(today)
	month_end = get_last_day(today)
	# PIs linked to project (header or item or via PO) in current month
	pi_sum = frappe.db.sql(
		"""
		SELECT SUM(pi_item.base_net_amount)
		FROM `tabPurchase Invoice Item` pi_item
		INNER JOIN `tabPurchase Invoice` pi ON pi_item.parent = pi.name
		LEFT JOIN `tabPurchase Order` po ON po.name = pi_item.purchase_order AND COALESCE(pi_item.purchase_order,'') != ''
		WHERE pi.docstatus = 1
		AND (pi.posting_date >= %s AND pi.posting_date <= %s)
		AND (
			pi_item.project = %s OR (COALESCE(pi_item.project,'') = '' AND pi.project = %s)
			OR (COALESCE(pi_item.purchase_order,'') != '' AND po.project = %s)
		)
		""",
		(month_start, month_end, project, project, project),
		as_list=True,
	)
	pi_total = flt(pi_sum[0][0]) if pi_sum and pi_sum[0][0] else 0
	gle = DocType("GL Entry")
	je_sum = (
		frappe.qb.from_(gle)
		.select(Sum(gle.debit))
		.where(
			(gle.project == project)
			& (gle.voucher_type == "Journal Entry")
			& (gle.is_cancelled == 0)
			& (gle.posting_date >= month_start)
			& (gle.posting_date <= month_end)
		)
		.run(as_list=True)
	)
	je_total = flt(je_sum[0][0]) if je_sum and je_sum[0][0] else 0
	return pi_total + je_total


def _get_outstanding_po(active_purchase_orders: list, project: str) -> dict:
	"""Outstanding: total remaining to pay from POs and from Purchase Invoices, with detail lists for dropdowns."""
	total_remaining = sum(flt(po.get("remaining", 0)) for po in (active_purchase_orders or []))
	total_invoiced = sum(flt(po.get("invoiced_amount", 0)) for po in (active_purchase_orders or []))
	total_remaining_pi = _get_outstanding_pi(project)
	remaining_po_details = [
		{"po_name": po.get("name"), "supplier": po.get("supplier") or "", "remaining": flt(po.get("remaining", 0))}
		for po in (active_purchase_orders or [])
	]
	remaining_pi_details = _get_outstanding_pi_details(project)
	return {
		"total_remaining": total_remaining,
		"total_invoiced": total_invoiced,
		"total_remaining_pi": total_remaining_pi,
		"remaining_po_details": remaining_po_details,
		"remaining_pi_details": remaining_pi_details,
	}


def _get_outstanding_pi(project: str) -> float:
	"""Total outstanding (unpaid) amount for Purchase Invoices linked to this project."""
	if not project:
		return 0.0
	result = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(pi.outstanding_amount), 0) AS total
		FROM (
			SELECT DISTINCT pi.name, pi.outstanding_amount
			FROM `tabPurchase Invoice` pi
			INNER JOIN `tabPurchase Invoice Item` pi_item ON pi_item.parent = pi.name
			LEFT JOIN `tabPurchase Order` po ON po.name = pi_item.purchase_order AND COALESCE(pi_item.purchase_order, '') != ''
			WHERE pi.docstatus = 1
			AND (
				pi_item.project = %(project)s
				OR (COALESCE(pi_item.project, '') = '' AND pi.project = %(project)s)
				OR (COALESCE(pi_item.purchase_order, '') != '' AND po.project = %(project)s)
			)
		) pi
		""",
		{"project": project},
		as_dict=True,
	)
	return flt(result[0].get("total"), 0) if result else 0.0


def _get_outstanding_pi_details(project: str) -> list:
	"""List of Purchase Invoices linked to project with outstanding_amount > 0 (for dropdown details)."""
	if not project:
		return []
	rows = frappe.db.sql(
		"""
		SELECT pi.name, pi.posting_date, pi.supplier, pi.supplier_name, pi.outstanding_amount
		FROM `tabPurchase Invoice` pi
		INNER JOIN `tabPurchase Invoice Item` pi_item ON pi_item.parent = pi.name
		LEFT JOIN `tabPurchase Order` po ON po.name = pi_item.purchase_order AND COALESCE(pi_item.purchase_order, '') != ''
		WHERE pi.docstatus = 1
		AND COALESCE(pi.outstanding_amount, 0) > 0
		AND (
			pi_item.project = %(project)s
			OR (COALESCE(pi_item.project, '') = '' AND pi.project = %(project)s)
			OR (COALESCE(pi_item.purchase_order, '') != '' AND po.project = %(project)s)
		)
		GROUP BY pi.name, pi.posting_date, pi.supplier, pi.supplier_name, pi.outstanding_amount
		ORDER BY pi.posting_date DESC, pi.name DESC
		""",
		{"project": project},
		as_dict=True,
	)
	return [
		{
			"name": r.get("name") or "",
			"posting_date": str(r.get("posting_date")) if r.get("posting_date") else "",
			"supplier": r.get("supplier") or "",
			"supplier_name": r.get("supplier_name") or r.get("supplier") or "",
			"outstanding_amount": flt(r.get("outstanding_amount"), 0),
		}
		for r in (rows or [])
	]


def _get_sales_order_total(project: str) -> float:
	"""Total value of Sales Orders linked to project (base_net_total)."""
	r = frappe.db.sql(
		"""SELECT COALESCE(SUM(base_net_total), 0) FROM `tabSales Order` WHERE project = %s AND docstatus = 1""",
		(project,),
		as_list=True,
	)
	return flt(r[0][0]) if r and r[0][0] else 0


def _get_top_suppliers(project: str, limit: int = 10) -> list:
	"""Top suppliers by PI amount for this project (VAT-inclusive: item share of base_grand_total)."""
	rows = frappe.db.sql(
		"""
		SELECT
			pi.supplier,
			pi.supplier_name,
			SUM(
				CASE
					WHEN COALESCE(pi.base_net_total, 0) > 0
					THEN pi_item.base_net_amount * (pi.base_grand_total / pi.base_net_total)
					ELSE pi_item.base_net_amount
				END
			) AS total
		FROM `tabPurchase Invoice Item` pi_item
		INNER JOIN `tabPurchase Invoice` pi ON pi_item.parent = pi.name
		LEFT JOIN `tabPurchase Order` po ON po.name = pi_item.purchase_order AND COALESCE(pi_item.purchase_order, '') != ''
		WHERE pi.docstatus = 1
		AND (
			pi_item.project = %(project)s
			OR (COALESCE(pi_item.project, '') = '' AND pi.project = %(project)s)
			OR (COALESCE(pi_item.purchase_order, '') != '' AND po.project = %(project)s)
		)
		GROUP BY pi.supplier, pi.supplier_name
		ORDER BY total DESC
		LIMIT %(limit)s
		""",
		{"project": project, "limit": limit},
		as_dict=True,
	)
	return [{"supplier": r.get("supplier") or "", "supplier_name": r.get("supplier_name") or r.get("supplier") or "", "total": flt(r.get("total", 0))} for r in rows]


def _get_cost_breakdown(costs: dict) -> list:
	"""Cost breakdown for chart: label and value (exclude zero)."""
	if not costs:
		return []
	out = []
	for key, label in [
		("purchase_invoice", _("Purchase Invoice")),
		("journal_entry_gl", _("Journal Entry / GL")),
		("timesheet", _("Timesheet")),
		("expense_claim", _("Expense Claim")),
		("consumed_material", _("Consumed Material")),
	]:
		val = flt(costs.get(key, 0))
		if val:
			out.append({"label": label, "value": val})
	return out


def _get_payment_status(project: str) -> dict:
	"""Count of Purchase Invoices by status: Paid, Partly Paid, Unpaid."""
	# PIs linked to project (header or item or via PO)
	pi_list = frappe.db.sql(
		"""
		SELECT DISTINCT pi.name, pi.status
		FROM `tabPurchase Invoice` pi
		INNER JOIN `tabPurchase Invoice Item` pi_item ON pi_item.parent = pi.name
		LEFT JOIN `tabPurchase Order` po ON po.name = pi_item.purchase_order AND COALESCE(pi_item.purchase_order,'') != ''
		WHERE pi.docstatus = 1
		AND (
			pi_item.project = %(project)s OR (COALESCE(pi_item.project,'') = '' AND pi.project = %(project)s)
			OR (COALESCE(pi_item.purchase_order,'') != '' AND po.project = %(project)s)
		)
		""",
		{"project": project},
		as_dict=True,
	)
	paid = partly_paid = unpaid = 0
	for r in pi_list or []:
		s = (r.get("status") or "").lower()
		if "paid" in s and "partly" not in s:
			paid += 1
		elif "partly" in s:
			partly_paid += 1
		else:
			unpaid += 1
	return {"paid": paid, "partly_paid": partly_paid, "unpaid": unpaid, "total": len(pi_list or [])}


def _get_last_activity(project: str) -> dict:
	"""Last PI and last Payment Entry date for this project."""
	pi_date = frappe.db.sql(
		"""
		SELECT MAX(pi.posting_date)
		FROM `tabPurchase Invoice` pi
		INNER JOIN `tabPurchase Invoice Item` pi_item ON pi_item.parent = pi.name
		LEFT JOIN `tabPurchase Order` po ON po.name = pi_item.purchase_order AND COALESCE(pi_item.purchase_order,'') != ''
		WHERE pi.docstatus = 1
		AND (
			pi_item.project = %s OR (COALESCE(pi_item.project,'') = '' AND pi.project = %s)
			OR (COALESCE(pi_item.purchase_order,'') != '' AND po.project = %s)
		)
		""",
		(project, project, project),
		as_list=True,
	)
	pe_date = frappe.db.sql(
		"""SELECT MAX(posting_date) FROM `tabPayment Entry` WHERE docstatus = 1 AND project = %s""",
		(project,),
		as_list=True,
	)
	return {
		"last_pi_date": str(pi_date[0][0]) if pi_date and pi_date[0][0] else "",
		"last_pe_date": str(pe_date[0][0]) if pe_date and pe_date[0][0] else "",
	}


def _get_alerts(
	project: str,
	costs: dict,
	income: dict,
	payment_summary: dict,
	unallocated_count: int,
	budget_vs_actual: dict,
) -> list:
	"""List of alert messages (over budget, no income, unallocated payments, etc.)."""
	alerts = []
	if budget_vs_actual.get("over_budget") and budget_vs_actual.get("estimated"):
		alerts.append(_("Project is over budget (actual cost exceeds estimated)."))
	if flt(income.get("total", 0)) == 0 and flt(costs.get("total", 0)) > 0:
		alerts.append(_("No income recorded yet; costs are present."))
	if unallocated_count and unallocated_count > 0:
		alerts.append(_("There are unallocated supplier payments. Allocate or reconcile them."))
	if flt(payment_summary.get("total_remaining_po", 0)) > 0:
		# Informational
		pass
	return alerts
