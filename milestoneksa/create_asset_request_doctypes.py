import frappe

def execute():
	# --- Child DocType ---
	if not frappe.db.exists("DocType", "Asset Request Item"):
		frappe.get_doc({
			"doctype": "DocType",
			"name": "Asset Request Item",
			"module": "milestoneksa",
			"custom": 0,
			"istable": 1,
			"editable_grid": 1,
			"engine": "InnoDB",
			"fields": [
				{"fieldname": "item_code", "fieldtype": "Link", "label": "Item", "options": "Item", "reqd": 1, "in_list_view": 1},
				{"fieldname": "item_name", "fieldtype": "Data", "label": "Item Name", "read_only": 1, "in_list_view": 1},
				{"fieldname": "asset_category", "fieldtype": "Link", "label": "Asset Category", "options": "Asset Category"},
				{"fieldname": "uom", "fieldtype": "Link", "label": "UOM", "options": "UOM"},
				{"fieldname": "qty", "fieldtype": "Float", "label": "Qty", "default": 1, "reqd": 1, "in_list_view": 1},
				{"fieldname": "warehouse", "fieldtype": "Link", "label": "Warehouse", "options": "Warehouse"},
				{"fieldname": "existing_asset", "fieldtype": "Link", "label": "Existing Asset (for Replacement/Loan/Return)", "options": "Asset"},
				{"fieldname": "serial_no", "fieldtype": "Small Text", "label": "Serial No(s)"},
				{"fieldname": "remarks", "fieldtype": "Small Text", "label": "Remarks"}
			],
			"permissions": []
		}).insert()
		print("Created DocType: Asset Request Item")

	# --- Parent DocType ---
	if not frappe.db.exists("DocType", "Asset Request"):
		frappe.get_doc({
			"doctype": "DocType",
			"name": "Asset Request",
			"module": "milestoneksa",
			"custom": 0,
			"istable": 0,
			"editable_grid": 0,
			"track_changes": 1,
			"track_seen": 1,
			"is_submittable": 1,
			"autoname": "naming_series:",
			"naming_rule": "By fieldname",
			"naming_series": "ASR-.YYYY.-.####",
			"title_field": "employee",
			"subject_field": "employee",
			"allow_rename": 1,
			"engine": "InnoDB",
			"fields": [
				{"fieldname": "company", "fieldtype": "Link", "label": "Company", "options": "Company", "reqd": 1},
				{"fieldname": "employee", "fieldtype": "Link", "label": "Employee", "options": "Employee", "reqd": 1},
				{"fieldname": "department", "fieldtype": "Link", "label": "Department", "options": "Department"},
				{"fieldname": "branch", "fieldtype": "Link", "label": "Branch", "options": "Branch"},
				{"fieldname": "request_type", "fieldtype": "Select", "label": "Request Type", "options": "New\nReplacement\nTemporary Loan\nReturn", "default": "New"},
				{"fieldname": "priority", "fieldtype": "Select", "label": "Priority", "options": "Low\nNormal\nHigh\nUrgent", "default": "Normal"},
				{"fieldname": "needed_by", "fieldtype": "Date", "label": "Needed By"},
				{"fieldname": "justification", "fieldtype": "Small Text", "label": "Justification / Purpose"},
				{"fieldname": "items", "fieldtype": "Table", "label": "Items", "options": "Asset Request Item", "reqd": 1},
				{"fieldname": "total_qty", "fieldtype": "Float", "label": "Total Qty", "read_only": 1, "in_list_view": 1},
				{"fieldname": "status", "fieldtype": "Select", "label": "Status", "read_only": 1,
				 "options": "Draft\nSubmitted\nApproved\nRejected\nIssued", "default": "Draft"},
				{"fieldname": "naming_series", "fieldtype": "Select", "label": "Naming Series",
				 "options": "ASR-.YYYY.-.####", "default": "ASR-.YYYY.-.####"},
				{"fieldname": "expense_approver", "fieldtype": "Link", "label": "Expense Approver (Resolved)",
				 "options": "User", "hidden": 1}
			],
			"permissions": [
				{"role": "Employee", "read": 1, "write": 1, "create": 1},
				{"role": "Expense Approver", "read": 1, "submit": 1},
				{"role": "Asset Manager", "read": 1, "write": 1},
				{"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1, "submit": 1}
			]
		}).insert()
		print("Created DocType: Asset Request")
