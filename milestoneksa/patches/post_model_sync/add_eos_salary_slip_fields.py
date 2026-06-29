"""Add salary slip reference and leave summary fields to Employee Contract End Review."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"Employee Contract End Review": [
				{
					"fieldname": "salary_slip_reference",
					"label": "Salary Slip Reference",
					"fieldtype": "Link",
					"options": "Salary Slip",
					"read_only": 1,
					"insert_after": "last_actual_wage",
				},
				{
					"fieldname": "average_monthly_wage",
					"label": "Average Monthly Wage",
					"fieldtype": "Currency",
					"read_only": 1,
					"insert_after": "salary_slip_reference",
				},
				{
					"fieldname": "wage_source",
					"label": "Wage Source",
					"fieldtype": "Data",
					"read_only": 1,
					"insert_after": "average_monthly_wage",
				},
				{
					"fieldname": "paid_leave_days_taken",
					"label": "Paid Leave Days Taken",
					"fieldtype": "Float",
					"read_only": 1,
					"insert_after": "unpaid_leave_days",
				},
			]
		},
		ignore_validate=True,
	)
	frappe.clear_cache(doctype="Employee Contract End Review")
