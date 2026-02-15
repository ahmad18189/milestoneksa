# -*- coding: utf-8 -*-
import frappe
from frappe.utils import now

def _ensure_doctype(name, **kwargs):
	"""
	Idempotently create a DocType if it doesn't exist.
	Returns the DocType doc (existing or newly created).
	"""
	if frappe.db.exists("DocType", name):
		return frappe.get_doc("DocType", name)

	doc = frappe.new_doc("DocType")
	doc.update({"name": name, **kwargs})
	doc.insert(ignore_permissions=True)
	return doc

def _reload(dtname):
	try:
		# expects files to exist only if you also keep JSONs; safe to ignore if not present
		mapper = {
			"Desk Announcement Role": ("MilestoneKSA", "doctype", "desk_announcement_role"),
			"Desk Announcement User": ("MilestoneKSA", "doctype", "desk_announcement_user"),
			"Desk Announcement Receipt": ("MilestoneKSA", "doctype", "desk_announcement_receipt"),
			"Desk Announcement": ("MilestoneKSA", "doctype", "desk_announcement"),
		}
		if dtname in mapper:
			app, doctype_folder, fname = mapper[dtname]
			frappe.reload_doc(app, doctype_folder, fname)
	except Exception:
		pass

def create_desk_announcement_doctypes():
	# --- Child tables first ---
	_ensure_doctype(
		"Desk Announcement Role",
		module="MilestoneKSA",
		istable=1,
		editable_grid=1,
		track_changes=0,
		custom=0,
		allow_copy=0,
		allow_rename=0,
		engine="InnoDB",
		fields=[
			{
				"fieldname": "role",
				"label": "Role",
				"fieldtype": "Link",
				"options": "Role",
				"reqd": 1
			}
		],
		permissions=[]
	)

	_ensure_doctype(
		"Desk Announcement User",
		module="MilestoneKSA",
		istable=1,
		editable_grid=1,
		track_changes=0,
		custom=0,
		allow_copy=0,
		allow_rename=0,
		engine="InnoDB",
		fields=[
			{
				"fieldname": "user",
				"label": "User",
				"fieldtype": "Link",
				"options": "User",
				"reqd": 1
			}
		],
		permissions=[]
	)

	_ensure_doctype(
		"Desk Announcement Receipt",
		module="MilestoneKSA",
		istable=1,
		editable_grid=0,
		track_changes=0,
		custom=0,
		allow_copy=0,
		allow_rename=0,
		engine="InnoDB",
		fields=[
			{
				"fieldname": "user",
				"label": "User",
				"fieldtype": "Link",
				"options": "User",
				"reqd": 1
			},
			{
				"fieldname": "status",
				"label": "Status",
				"fieldtype": "Select",
				"options": "seen\ndismissed",
				"reqd": 1
			},
			{
				"fieldname": "timestamp",
				"label": "Timestamp",
				"fieldtype": "Datetime",
				"reqd": 1,
				"default": "Now"
			}
		],
		permissions=[]
	)

	# --- Parent doctype ---
	_ensure_doctype(
		"Desk Announcement",
		module="MilestoneKSA",
		istable=0,
		editable_grid=0,
		quick_entry=0,
		track_changes=1,
		custom=0,
		allow_copy=0,
		allow_rename=0,
		engine="InnoDB",
		autoname="ANN-.#####",
		fields=[
			# Content
			{
				"fieldname": "title",
				"label": "Title",
				"fieldtype": "Data",
				"reqd": 1
			},
			{
				"fieldname": "message",
				"label": "Message (Rich Text)",
				"fieldtype": "Text Editor",
				"reqd": 1
			},
			{
				"fieldname": "link_url",
				"label": "Link (optional)",
				"fieldtype": "Data",
				"options": "URL"
			},
			{
				"fieldname": "show_policy",
				"label": "Show Policy",
				"fieldtype": "Select",
				"options": "Until Dismissed\nOnce",
				"default": "Until Dismissed",
				"reqd": 1
			},

			# Audience
			{
				"fieldname": "section_audience",
				"label": "Audience",
				"fieldtype": "Section Break"
			},
			{
				"fieldname": "audience",
				"label": "Audience Type",
				"fieldtype": "Select",
				"options": "All\nBy Role\nBy User\nRoles & Users",
				"default": "All",
				"reqd": 1
			},
			{
				"fieldname": "roles",
				"label": "Target Roles",
				"fieldtype": "Table",
				"options": "Desk Announcement Role",
				"depends_on": "eval:in_list(['By Role','Roles & Users'], doc.audience)"
			},
			{
				"fieldname": "users",
				"label": "Target Users",
				"fieldtype": "Table",
				"options": "Desk Announcement User",
				"depends_on": "eval:in_list(['By User','Roles & Users'], doc.audience)"
			},

			# Publishing
			{
				"fieldname": "section_publish",
				"label": "Publishing",
				"fieldtype": "Section Break"
			},
			{
				"fieldname": "is_published",
				"label": "Published",
				"fieldtype": "Check",
				"default": "1"
			},
			{
				"fieldname": "publish_from",
				"label": "Publish From",
				"fieldtype": "Datetime"
			},
			{
				"fieldname": "publish_upto",
				"label": "Publish Upto",
				"fieldtype": "Datetime"
			},

			# Receipts
			{
				"fieldname": "section_receipts",
				"label": "Receipts",
				"fieldtype": "Section Break",
				"collapsible": 1
			},
			{
				"fieldname": "receipts",
				"label": "Receipts",
				"fieldtype": "Table",
				"options": "Desk Announcement Receipt",
				"read_only": 1
			}
		],
		# Only basic CRUD for System Manager; no submit/cancel/amend perms defined.
		permissions=[
			{
				"role": "System Manager",
				"permlevel": 0,
				"read": 1,
				"write": 1,
				"create": 1,
				"delete": 1
			}
		]
	)

	# Optional best-effort reloads (harmless if JSON files are not present)
	for dt in [
		"Desk Announcement Role",
		"Desk Announcement User",
		"Desk Announcement Receipt",
		"Desk Announcement",
	]:
		_reload(dt)

	frappe.clear_cache()
	frappe.db.commit()
	return {"ok": True, "at": now()}
