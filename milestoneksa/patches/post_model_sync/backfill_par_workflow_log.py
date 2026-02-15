"""
Backfill Payment Approval Request workflow_activity_log from Version doctype.
Runs only for PAR documents that have no workflow_activity_log rows (one-time backfill).
"""
from __future__ import annotations

import json
from typing import List

import frappe


def _get_transition_action(doctype: str, from_state: str, to_state: str) -> str:
	"""Return the Workflow transition action label for from_state -> to_state."""
	try:
		workflows = frappe.get_all(
			"Workflow",
			filters={"document_type": doctype},
			fields=["name"],
			limit=1,
		)
		if not workflows:
			return ""
		workflow_doc = frappe.get_doc("Workflow", workflows[0].name)
		for t in workflow_doc.transitions:
			if t.state == from_state and t.next_state == to_state:
				return t.action or ""
	except Exception as e:
		frappe.log_error(f"Error getting transition action: {e}")
	return ""


def _get_employee_name_for_user(user: str) -> str:
	"""Return display name for user: User.full_name or Employee name if linked."""
	if not user:
		return ""
	name = frappe.db.get_value("User", user, "full_name")
	if name:
		return name
	emp = frappe.db.get_value("Employee", {"user_id": user}, "employee_name")
	return emp or user


def execute():
	doctype = "Payment Approval Request"
	par_names = frappe.get_all(doctype, pluck="name")
	for name in par_names:
		# Only backfill if no log rows yet (idempotent)
		existing = frappe.db.count(
			"Payment Approval Request Workflow Log",
			filters={"parent": name, "parenttype": doctype},
		)
		if existing > 0:
			continue
		rows = _get_workflow_log_rows_from_version(doctype, name)
		if not rows:
			continue
		doc = frappe.get_doc(doctype, name)
		for r in rows:
			doc.append("workflow_activity_log", r)
		doc.flags.ignore_version = True
		doc.flags.ignore_permissions = True
		doc.flags.ignore_validate_update_after_submit = True
		doc.save()
		frappe.db.commit()


def _get_workflow_log_rows_from_version(doctype: str, docname: str) -> List[dict]:
	"""Build workflow_activity_log rows from Version records (workflow_state changes only)."""
	versions = frappe.get_all(
		"Version",
		filters={"ref_doctype": doctype, "docname": docname},
		fields=["name", "owner", "creation", "data"],
		order_by="creation asc",
	)
	rows = []
	for v in versions:
		if not v.get("data"):
			continue
		try:
			data = json.loads(v["data"])
		except (TypeError, json.JSONDecodeError):
			continue
		changed = data.get("changed") or []
		old_state = None
		new_state = None
		for entry in changed:
			if not isinstance(entry, (list, tuple)) or len(entry) < 3:
				continue
			if entry[0] == "workflow_state":
				old_state = entry[1]
				new_state = entry[2]
				break
		if new_state is None:
			continue
		action = _get_transition_action(doctype, old_state or "", new_state)
		if not action:
			action = f"Changed to {new_state}"
		owner = v.get("owner") or ""
		rows.append({
			"user": owner,
			"employee_name": _get_employee_name_for_user(owner),
			"log_datetime": v.get("creation"),
			"action": action,
			"workflow_status": new_state,
		})
	return rows
