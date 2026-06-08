import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"HR Settings": [
				{
					"fieldname": "mksa_attendance_ignored_roles",
					"label": "أدوار مستثناة من التقارير",
					"fieldtype": "Table",
					"options": "Attendance Email Report Role",
					"insert_after": "mksa_attendance_email_roles",
					"description": "أي موظف مرتبط بمستخدم لديه أحد هذه الأدوار لن يظهر في تقارير الحضور.",
				}
			]
		},
		ignore_validate=True,
	)
	frappe.clear_cache(doctype="HR Settings")
