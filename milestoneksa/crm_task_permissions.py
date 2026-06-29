"""Restrict CRM Task visibility to own tasks unless privileged role."""

from __future__ import annotations

import frappe

PRIVILEGED_ROLES = frozenset(
	{
		"System Manager",
		"HR User",
		"HR Manager",
		"CEO",
		"COO",
	}
)


def can_view_all_crm_tasks(user: str | None = None) -> bool:
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	return bool(PRIVILEGED_ROLES.intersection(frappe.get_roles(user)))


def _is_own_task(doc, user: str) -> bool:
	if not doc:
		return False
	assigned_to = doc.get("assigned_to") if isinstance(doc, dict) else getattr(doc, "assigned_to", None)
	owner = doc.get("owner") if isinstance(doc, dict) else getattr(doc, "owner", None)
	return assigned_to == user or owner == user


def get_permission_query_conditions(user: str, doctype: str | None = None) -> str:
	if not user:
		user = frappe.session.user
	if can_view_all_crm_tasks(user):
		return ""

	escaped_user = frappe.db.escape(user)
	return f"(`tabCRM Task`.`assigned_to` = {escaped_user} OR `tabCRM Task`.`owner` = {escaped_user})"


def has_crm_task_permission(doc, ptype: str = "read", user: str | None = None) -> bool:
	user = user or frappe.session.user
	if can_view_all_crm_tasks(user):
		return True
	return _is_own_task(doc, user)


def ensure_crm_task_docperms():
	"""Sales User if_owner blocks tasks assigned to user but owned by someone else."""
	perm_name = frappe.db.get_value(
		"Custom DocPerm",
		{"parent": "CRM Task", "role": "Sales User"},
		"name",
	)
	if not perm_name:
		return

	if frappe.db.get_value("Custom DocPerm", perm_name, "if_owner"):
		frappe.db.set_value("Custom DocPerm", perm_name, "if_owner", 0, update_modified=False)


def test_permissions():
	results = {}
	total = frappe.db.count("CRM Task")
	for user in ("a.alhaj@milestoneksa.com", "a.abdullah@milestoneksa.com", "m.eqtefan@milestoneksa.com"):
		frappe.set_user(user)
		from frappe.permissions import get_role_permissions

		meta = frappe.get_meta("CRM Task")
		role_perms = get_role_permissions(meta, user=user)
		results[user] = {
			"privileged": can_view_all_crm_tasks(user),
			"condition": get_permission_query_conditions(user),
			"can_read": bool(role_perms.get("read")),
			"list_count": len(frappe.get_list("CRM Task", fields=["name"], limit_page_length=500)),
			"total_in_db": total,
		}
	frappe.set_user("Administrator")
	return results
