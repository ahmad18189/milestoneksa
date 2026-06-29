import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"Employee Contract End Review": [
				{
					"fieldname": "last_reminder_sent_on",
					"label": "Last Reminder Sent On",
					"fieldtype": "Datetime",
					"insert_after": "notification_sent_on",
					"read_only": 1,
				},
				{
					"fieldname": "auto_renew_notice_sent",
					"label": "Auto Renew Notice Sent",
					"fieldtype": "Check",
					"default": "0",
					"insert_after": "last_reminder_sent_on",
					"read_only": 1,
				},
				{
					"fieldname": "auto_renew_notice_sent_on",
					"label": "Auto Renew Notice Sent On",
					"fieldtype": "Datetime",
					"insert_after": "auto_renew_notice_sent",
					"read_only": 1,
				},
			]
		},
		ignore_validate=True,
	)
	frappe.clear_cache(doctype="Employee Contract End Review")
