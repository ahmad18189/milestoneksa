# -*- coding: utf-8 -*-
import frappe
from frappe import _
from frappe.utils import now_datetime

from frappe.model.document import Document


class DeskAnnouncement(Document):
	pass

def _is_within_window(doc):
	"""Check publish window & Published flag."""
	if not doc.is_published:
		return False
	now = now_datetime()
	if doc.publish_from and now < doc.publish_from:
		return False
	if doc.publish_upto and now > doc.publish_upto:
		return False
	return True

def _user_matches_audience(doc, user):
	"""Check if the given user matches doc.audience rules."""
	if doc.audience == "All":
		return True

	roles_needed = {r.role for r in (doc.get("roles") or [])}
	users_needed = {u.user for u in (doc.get("users") or [])}

	if doc.audience == "By Role":
		user_roles = set(frappe.get_roles(user))
		return bool(roles_needed & user_roles)

	if doc.audience == "By User":
		return user in users_needed

	# "Roles & Users" -> match if either
	if doc.audience == "Roles & Users":
		user_roles = set(frappe.get_roles(user))
		return (user in users_needed) or bool(roles_needed & user_roles)

	return False

def _has_receipt(doc, user, include_seen=False):
	"""True if user has a receipt that should suppress showing."""
	for r in (doc.get("receipts") or []):
		if r.user == user:
			if r.status == "dismissed":
				return True
			if include_seen and r.status == "seen":
				return True
	return False

@frappe.whitelist()
def get_pending_announcements():
	"""Return a list of Desk Announcements to show to current user."""
	user = frappe.session.user
	if not user or user == "Guest":
		return []

	rows = frappe.get_all(
		"Desk Announcement",
		filters={"is_published": 1},
		fields=["name", "title", "link_url", "show_policy", "audience", "publish_from", "publish_upto"],
		order_by="modified desc",
		limit=50,
	)

	out = []
	for row in rows:
		doc = frappe.get_doc("Desk Announcement", row.name)

		if not _is_within_window(doc):
			continue
		if not _user_matches_audience(doc, user):
			continue

		# Suppress if:
		# - Until Dismissed: user has 'dismissed'
		# - Once: user has 'seen' or 'dismissed'
		if doc.show_policy == "Until Dismissed":
			if _has_receipt(doc, user, include_seen=False):
				continue
		else:  # "Once"
			if _has_receipt(doc, user, include_seen=True):
				continue

		out.append({
			"name": doc.name,
			"title": doc.title,
			"message": doc.message,
			"link_url": doc.link_url,
			"show_policy": doc.show_policy
		})

	return out

@frappe.whitelist()
def acknowledge(announcement: str, action: str):
	"""
	action in {"dismiss","seen"}.
	- "dismiss": record that user ticked 'Don't show again'
	- "seen":    used only for 'Once' policy to record a single display
	"""
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Not permitted"))

	doc = frappe.get_doc("Desk Announcement", announcement)

	if action not in {"dismiss", "seen"}:
		frappe.throw(_("Invalid action"))

	# De-dup receipts
	for r in (doc.get("receipts") or []):
		if r.user == user and r.status == ("dismissed" if action == "dismiss" else "seen"):
			return {"ok": True}

	doc.append("receipts", {
		"user": user,
		"status": "dismissed" if action == "dismiss" else "seen",
		"timestamp": now_datetime()
	})
	doc.flags.ignore_permissions = True
	doc.save(ignore_version=True)
	frappe.db.commit()
	return {"ok": True}