import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"HR Settings": [
				{
					"fieldname": "mksa_checkin_warning_last_sent",
					"label": "آخر إرسال لتحذير عدم الحضور",
					"fieldtype": "Date",
					"hidden": 1,
					"read_only": 1,
					"insert_after": "mksa_checkout_report_last_sent",
				}
			]
		},
		ignore_validate=True,
	)
	frappe.clear_cache(doctype="HR Settings")
