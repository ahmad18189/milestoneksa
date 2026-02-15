
import frappe

def create_employee_custody_transaction():
	if frappe.db.exists("DocType", "Employee Custody Transaction"):
		print("Employee Custody Transaction already exists")
		return

	doc = frappe.get_doc({
		"doctype": "DocType",
		"name": "Employee Custody Transaction",
		"module": "MilestoneKSA",
		"custom": 0,
		"istable": 1,
		"fields": [
			{
				"fieldname": "transaction_date", "fieldtype": "Datetime",
				"label": "Date", "reqd": 1
			},
			{
				"fieldname": "action", "fieldtype": "Select",
				"label": "Action",
				"options": "\nCreated\nAssigned\nReturned\nDisabled"
			},
			{
				"fieldname": "employee", "fieldtype": "Link",
				"label": "Employee", "options": "Employee"
			},
			{
				"fieldname": "condition_note", "fieldtype": "Small Text",
				"label": "Condition / Notes"
			}
		],
		"permissions": [
			{"role": "HR User", "read": 1, "write": 1, "create": 1, "delete": 1},
			{"role": "HR Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
			{"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1}
		]
	})

	doc.insert(ignore_if_duplicate=True)
	frappe.db.commit()
	print("Employee Custody Transaction created successfully")


import frappe

def create_employee_custody():
	if frappe.db.exists("DocType", "Employee Custody"):
		print("Employee Custody already exists")
		return

	doc = frappe.get_doc({
		"doctype": "DocType",
		"name": "Employee Custody",
		"module": "MilestoneKSA",
		"custom": 0,
		"istable": 0,
		"autoname": "naming_series:",
		"naming_rule": "By fieldname",
		"fields": [
			{
				"fieldname": "naming_series", "fieldtype": "Select",
				"label": "Naming Series", "options": "CUST-.YYYY.-",
				"reqd": 1, "default": "CUST-.YYYY.-"
			},
			{
				"fieldname": "status", "fieldtype": "Select",
				"label": "Status",
				"options": "\nAvailable\nAssigned\nDisabled",
				"default": "Available", "reqd": 1
			},
			{
				"fieldname": "custody_name", "fieldtype": "Data",
				"label": "Custody Name", "reqd": 1
			},
			{
				"fieldname": "asset", "fieldtype": "Link",
				"label": "Asset", "options": "Asset"
			},
			{
				"fieldname": "item_code", "fieldtype": "Link",
				"label": "Item", "options": "Item"
			},
			{
				"fieldname": "serial_no", "fieldtype": "Small Text",
				"label": "Serial No"
			},
			{
				"fieldname": "condition_on_issue", "fieldtype": "Small Text",
				"label": "Initial Condition"
			},
			{
				"fieldname": "transactions", "fieldtype": "Table",
				"label": "Custody Transactions",
				"options": "Employee Custody Transaction"
			}
		],
		"permissions": [
			{"role": "HR User", "read": 1, "write": 1, "create": 1, "delete": 1},
			{"role": "HR Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
			{"role": "Employee", "read": 1},
			{"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1}
		],
		"track_changes": 1
	})

	doc.insert(ignore_if_duplicate=True)
	frappe.db.commit()
	print("Employee Custody created successfully")
