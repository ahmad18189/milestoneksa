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
	"""Return costs, income, connected doctypes, active POs, payment summary, last-month invoiced, and PO item detail."""
	if not project:
		frappe.throw(_("Project is required"))

	project_doc = frappe.get_doc("Project", project)
	costs = _get_costs(project, project_doc)
	income = _get_income(project, project_doc)
	connected_doctypes = _get_connected_doctypes(project)
	active_purchase_orders = _get_active_purchase_orders(project)
	payment_summary = _get_payment_summary(costs, active_purchase_orders)
	last_month_invoiced, last_month_invoices = _get_last_month_invoiced(project)
	active_po_item_detail = _get_po_item_detail(project)
	supplier_payments_unallocated_unreconciled = _get_supplier_payments_unallocated_unreconciled(project)

	return {
		"costs": costs,
		"income": income,
		"connected_doctypes": connected_doctypes,
		"active_purchase_orders": active_purchase_orders,
		"payment_summary": payment_summary,
		"last_month_invoiced": last_month_invoiced,
		"last_month_invoices": last_month_invoices,
		"active_po_item_detail": active_po_item_detail,
		"supplier_payments_unallocated_unreconciled": supplier_payments_unallocated_unreconciled,
		"project_info": {
			"name": project_doc.name,
			"project_name": project_doc.project_name,
			"company": project_doc.company or "",
		},
	}


def _get_payment_summary(costs: dict, active_purchase_orders: list) -> dict:
	"""Payment summary for advisor: total paid, total remaining (PO), project total."""
	total_paid_to_date = flt(costs.get("total", 0))
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
		invoiced_amount = sum(flt(r.get("billed_amt", 0)) for r in item_rows)
		grand_total = flt(po_doc.get("grand_total", 0))
		remaining = grand_total - invoiced_amount
		out.append({
			"po_name": po_name,
			"supplier": po_doc.get("supplier") or "",
			"grand_total": grand_total,
			"invoiced_amount": invoiced_amount,
			"remaining": remaining,
			"status": po_doc.get("status") or "",
			"items": item_rows,
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
		invoiced = frappe.db.sql(
			"""
			SELECT COALESCE(SUM(billed_amt), 0) FROM `tabPurchase Order Item`
			WHERE parent = %s
			""",
			(name,),
			as_list=True,
		)
		invoiced_amount = flt(invoiced[0][0]) if invoiced and invoiced[0][0] else 0
		grand_total = flt(doc.grand_total)
		remaining = grand_total - invoiced_amount
		out.append({
			"name": name,
			"supplier": doc.supplier or "",
			"grand_total": grand_total,
			"invoiced_amount": invoiced_amount,
			"remaining": remaining,
			"status": doc.status or "",
		})
	return out
