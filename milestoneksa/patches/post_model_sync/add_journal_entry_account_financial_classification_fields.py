"""Add financial classification fields to Journal Entry Account rows."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"Journal Entry Account": [
				{
					"fieldname": "custom_project_identifier",
					"label": "Project Identifier",
					"fieldtype": "Link",
					"options": "Project Identifier",
					"insert_after": "project",
					"allow_on_submit": 1,
					"in_list_view": 1,
					"columns": 1,
				},
				{
					"fieldname": "custom_activity_type",
					"label": "Activity Type",
					"fieldtype": "Link",
					"options": "Activity Type",
					"insert_after": "custom_project_identifier",
					"allow_on_submit": 1,
					"in_list_view": 1,
					"columns": 1,
				},
			],
		},
		ignore_validate=True,
	)
	frappe.clear_cache(doctype="Journal Entry")
