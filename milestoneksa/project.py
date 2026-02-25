# milestoneksa/milestoneksa/project.py
# Project doctype override - extended costing from Journal Entry and Pending PO

from frappe.query_builder import DocType
from frappe.query_builder.functions import Sum
from frappe.utils import flt

import frappe

from erpnext.projects.doctype.project.project import Project as ERPNextProject


class Project(ERPNextProject):
	"""Override Project to add costing from Journal Entry and Pending PO."""

	def update_costing(self):
		super().update_costing()
		# Overwrite total_purchase_cost with our PI sum (item + header project); standard uses item-only and returns wrong value
		self.update_purchase_costing()
		self.update_journal_entry_costing()
		self.update_pending_po_costing()
		self.calculate_gross_margin()

	def update_purchase_costing(self):
		"""Recalculate total_purchase_cost from all submitted Purchase Invoices (project on item or header)."""
		self.total_purchase_cost = calculate_total_purchase_cost_from_pi(self.name)

	def update_journal_entry_costing(self):
		self.total_cost_from_journal_entry = calculate_total_cost_from_journal_entry(self.name)

	def update_pending_po_costing(self):
		self.total_pending_po_cost = calculate_total_pending_po_cost(self.name)

	def calculate_gross_margin(self):
		expense_amount = (
			flt(self.total_costing_amount)
			+ flt(self.total_purchase_cost)
			+ flt(self.get("total_consumed_material_cost", 0))
			+ flt(self.get("total_cost_from_journal_entry", 0))
		)
		self.gross_margin = flt(self.total_billed_amount) - expense_amount
		if self.total_billed_amount:
			self.per_gross_margin = (self.gross_margin / flt(self.total_billed_amount)) * 100


def calculate_total_purchase_cost_from_pi(project: str | None = None):
	"""Sum base_net_amount from Purchase Invoice Item where project matches (item, header, or PO) and parent PI is submitted."""
	if not project:
		return 0
	# Include: item.project = X, OR (item has no project and pi.project = X), OR (item has purchase_order and that PO has project = X)
	result = frappe.db.sql(
		"""
		SELECT SUM(pi_item.base_net_amount)
		FROM `tabPurchase Invoice Item` pi_item
		INNER JOIN `tabPurchase Invoice` pi ON pi_item.parent = pi.name
		LEFT JOIN `tabPurchase Order` po ON po.name = pi_item.purchase_order AND po.name IS NOT NULL AND po.name != ''
		WHERE pi.docstatus = 1
		AND (
			pi_item.project = %(project)s
			OR (COALESCE(pi_item.project, '') = '' AND pi.project = %(project)s)
			OR (COALESCE(pi_item.purchase_order, '') != '' AND po.project = %(project)s)
		)
		""",
		{"project": project},
	)
	return flt(result[0][0]) if result and result[0][0] else 0


def recalculate_project_purchase_cost_on_pi_change(doc, method=None):
	"""After PI submit/cancel, recalculate total_purchase_cost for all projects linked to this PI (header, items, or via PO)."""
	projects = set()
	if doc.get("project"):
		projects.add(doc.project)
	for d in doc.get("items") or []:
		if d.get("project"):
			projects.add(d.project)
		if d.get("purchase_order"):
			po_project = frappe.db.get_value("Purchase Order", d.purchase_order, "project")
			if po_project:
				projects.add(po_project)
	for project in projects:
		try:
			total = calculate_total_purchase_cost_from_pi(project)
			frappe.db.set_value("Project", project, "total_purchase_cost", total)
			# Recalculate gross margin (depends on total_purchase_cost)
			proj_doc = frappe.get_cached_doc("Project", project)
			if proj_doc:
				proj_doc.total_purchase_cost = total
				proj_doc.calculate_gross_margin()
				frappe.db.set_value(
					"Project", project,
					{"gross_margin": proj_doc.gross_margin, "per_gross_margin": proj_doc.per_gross_margin},
				)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Recalc Project Purchase Cost")


def calculate_total_cost_from_journal_entry(project: str | None = None):
	"""Sum debit amounts from GL Entry where voucher_type = Journal Entry and project matches."""
	if not project:
		return 0
	gle = DocType("GL Entry")
	result = (
		frappe.qb.from_(gle)
		.select(Sum(gle.debit))
		.where(
			(gle.project == project)
			& (gle.voucher_type == "Journal Entry")
			& (gle.is_cancelled == 0)
		)
		.run(as_list=True)
	)
	return flt(result[0][0]) if result and result[0][0] else 0


def calculate_total_pending_po_cost(project: str | None = None):
	"""
	Sum value (base_net_amount) of PO items linked to project that are not yet
	fully received or fully invoiced. Uses proportional value for partial qty.
	"""
	if not project:
		return 0
	po_item = DocType("Purchase Order Item")
	po = DocType("Purchase Order")
	result = (
		frappe.qb.from_(po_item)
		.inner_join(po)
		.on(po_item.parent == po.name)
		.select(
			po_item.base_net_amount,
			po_item.qty,
			po_item.received_qty,
			po_item.billed_amt,
		)
		.where(
			(po_item.project == project)
			& (po.docstatus == 1)
		)
		.run(as_dict=True)
	)
	total = 0
	for row in result or []:
		qty = flt(row.qty)
		if qty <= 0:
			continue
		received_qty = flt(row.received_qty)
		base_net_amount = flt(row.base_net_amount)
		billed_amt = flt(row.billed_amt)
		# Unreceived portion value
		unreceived_value = base_net_amount * (qty - received_qty) / qty
		# Uninvoiced portion value
		uninvoiced_value = base_net_amount - billed_amt
		# Take max to avoid double-counting (unreceived implies uninvoiced typically)
		pending = max(unreceived_value, uninvoiced_value)
		if pending > 0:
			total += pending
	return total


@frappe.whitelist()
def recalculate_project_costing(project: str):
	"""Recalculate Total Purchase Cost and other costing fields from submitted PIs and related data. Call from Project form."""
	if not project:
		frappe.throw(frappe._("Project is required"))
	total_from_pi = calculate_total_purchase_cost_from_pi(project)
	doc = frappe.get_doc("Project", project)
	doc.update_costing()
	# Always set Total Purchase Cost from our PI sum (item + header + via PO)
	doc.total_purchase_cost = total_from_pi
	doc.calculate_gross_margin()
	# Write to DB explicitly so form reload shows correct value
	frappe.db.set_value(
		"Project",
		project,
		{
			"total_purchase_cost": total_from_pi,
			"gross_margin": doc.gross_margin,
			"per_gross_margin": doc.per_gross_margin,
		},
		update_modified=False,
	)
	doc.db_update()
	frappe.db.commit()
	return {
		"total_purchase_cost": flt(total_from_pi),
		"message": frappe._("Costing recalculated. Total Purchase Cost: {0}").format(total_from_pi),
	}
