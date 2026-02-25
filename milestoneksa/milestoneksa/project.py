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
		# Overwrite total_purchase_cost with our PI sum (item + header project); standard uses item-only and can be wrong
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


def calculate_total_purchase_cost_from_pi(project: str | None = None):
	"""Total Purchase Cost (via Purchase Invoice): total of purchase invoices linked to this project.
	Include: item or header project = X, or PI item from a PO that has project = X."""
	if not project:
		return 0
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


def _should_update_project_from_gl_entry(doc) -> bool:
	"""Return True if this GL Entry affects a project's Journal Entry cost."""
	return (
		doc.get("voucher_type") == "Journal Entry"
		and doc.get("project")
	)


def _enqueue_project_journal_entry_cost_update(project: str) -> None:
	"""Enqueue update of project's total_cost_from_journal_entry (non-blocking)."""
	if not project:
		return
	frappe.enqueue(
		"milestoneksa.milestoneksa.project._update_project_journal_entry_cost",
		project=project,
		queue="short",
	)


def _update_project_journal_entry_cost(project: str) -> None:
	"""Update a single project's total_cost_from_journal_entry and gross margin."""
	try:
		cost = calculate_total_cost_from_journal_entry(project)
		pending = calculate_total_pending_po_cost(project)
		doc = frappe.get_doc("Project", project)
		doc.total_cost_from_journal_entry = cost
		doc.total_pending_po_cost = pending
		doc.calculate_gross_margin()
		frappe.db.set_value(
			"Project",
			project,
			{
				"total_cost_from_journal_entry": cost,
				"total_pending_po_cost": pending,
				"gross_margin": doc.gross_margin,
				"per_gross_margin": doc.per_gross_margin,
			},
			update_modified=False,
		)
		frappe.db.commit()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Project Journal Entry Cost Update")


@frappe.whitelist()
def recalculate_all_projects_journal_entry_cost() -> dict:
	"""Recalculate total_cost_from_journal_entry for all projects. Run via bench execute."""
	projects = frappe.get_all("Project", pluck="name")
	updated = 0
	for name in projects:
		try:
			cost = calculate_total_cost_from_journal_entry(name)
			pending = calculate_total_pending_po_cost(name)
			doc = frappe.get_doc("Project", name)
			doc.total_cost_from_journal_entry = cost
			doc.total_pending_po_cost = pending
			doc.calculate_gross_margin()
			frappe.db.set_value(
				"Project",
				name,
				{
					"total_cost_from_journal_entry": cost,
					"total_pending_po_cost": pending,
					"gross_margin": doc.gross_margin,
					"per_gross_margin": doc.per_gross_margin,
				},
				update_modified=False,
			)
			updated += 1
		except Exception as e:
			frappe.log_error(frappe.get_traceback(), f"Project {name} JE cost update")
	frappe.db.commit()
	return {"updated": updated, "total": len(projects)}


def on_gl_entry_change(doc, method: str | None = None) -> None:
	"""Hook: when GL Entry is created/updated/deleted and affects a project, enqueue project update."""
	projects_to_update = set()
	if method == "on_update" and doc.get("voucher_type") == "Journal Entry":
		# Project may have changed; update both old and new
		old = doc.get_doc_before_save()
		if old and old.get("project"):
			projects_to_update.add(old.project)
	if _should_update_project_from_gl_entry(doc):
		projects_to_update.add(doc.project)
	for project in projects_to_update:
		_enqueue_project_journal_entry_cost_update(project)


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
	doc.total_purchase_cost = total_from_pi
	doc.calculate_gross_margin()
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


@frappe.whitelist()
def get_purchase_invoices_for_project(project: str):
	"""List Purchase Invoices linked to project (header or item) and total. For checking Milestone-102 etc."""
	if not project:
		return {"invoices": [], "total": 0}
	# All PI items that count toward this project (item has project, or item blank and header has project)
	rows = frappe.db.sql(
		"""
		SELECT pi.name, pi.posting_date, pi.supplier, pi.base_net_total, pi.base_grand_total,
		       SUM(pi_item.base_net_amount) AS items_sum
		FROM `tabPurchase Invoice` pi
		INNER JOIN `tabPurchase Invoice Item` pi_item ON pi_item.parent = pi.name
		WHERE pi.docstatus = 1
		AND (pi_item.project = %(project)s OR (COALESCE(pi_item.project,'') = '' AND pi.project = %(project)s))
		GROUP BY pi.name, pi.posting_date, pi.supplier, pi.base_net_total, pi.base_grand_total
		ORDER BY pi.posting_date
		""",
		{"project": project},
		as_dict=True,
	)
	total = sum(flt(r.get("items_sum")) for r in rows)
	return {"invoices": rows, "total": total}
