"""One-time patch: add Financial Summary tab fields to Project form field_order in Property Setter."""
import json
import frappe


def execute():
	ps = frappe.db.get_value(
		"Property Setter",
		{"doc_type": "Project", "property": "field_order"},
		["name", "value"],
		as_dict=True,
	)
	if not ps:
		return
	order = json.loads(ps["value"])
	changed = False
	# Insert Financial Summary tab + content right after Dashboard
	try:
		dashboard_idx = order.index("custom_dashboard_html") + 1
	except ValueError:
		dashboard_idx = len(order)
	for field in ("custom_financial_summary_tab", "custom_financial_summary_html"):
		if field not in order:
			order.insert(dashboard_idx, field)
			dashboard_idx += 1
			changed = True
	# Insert costing fields after total_purchase_cost
	try:
		po_cost_idx = order.index("total_purchase_cost") + 1
	except ValueError:
		po_cost_idx = len(order)
	for field in ("total_cost_from_journal_entry", "total_pending_po_cost"):
		if field not in order:
			order.insert(po_cost_idx, field)
			po_cost_idx += 1
			changed = True
	if changed:
		frappe.db.set_value("Property Setter", ps["name"], "value", json.dumps(order))
		frappe.db.commit()
