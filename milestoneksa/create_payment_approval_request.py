import frappe

def execute():
    create_roles_if_missing()
    create_payment_approval_request_doctype()
    frappe.db.commit()

def create_roles_if_missing():
    required_roles = ["Manager", "CFO", "COO", "CEO"]
    for role_name in required_roles:
        if not frappe.db.exists("Role", role_name):
            role = frappe.get_doc({
                "doctype": "Role",
                "role_name": role_name
            })
            role.insert()
            frappe.msgprint(f"✅ Created Role: {role_name}")

def create_payment_approval_request_doctype():
    if frappe.db.exists("DocType", "Payment Approval Request"):
        frappe.msgprint("DocType already exists.")
        return

    doc = frappe.new_doc("DocType")
    doc.name = "Payment Approval Request"
    doc.module = "milestoneksa"
    doc.custom = 0
    doc.is_submittable = 1  # <-- Fix applied here
    doc.is_table = 0
    doc.track_changes = 1
    doc.track_views = 1
    doc.autoname = "field:employee"

    # Fields
    fields = [
        {"fieldname": "employee", "label": "Employee", "fieldtype": "Link", "options": "Employee", "reqd": 1},
        {"fieldname": "employee_name", "label": "Employee Name", "fieldtype": "Data", "fetch_from": "employee.employee_name", "read_only": 1},
        {"fieldname": "department", "label": "Department", "fieldtype": "Link", "options": "Department", "fetch_from": "employee.department", "read_only": 1},
        {"fieldname": "application_date", "label": "Application Date", "fieldtype": "Date", "default": "Today"},
        {"fieldname": "description", "label": "Description", "fieldtype": "Small Text", "reqd": 1},
        {"fieldname": "attachment", "label": "Attachment", "fieldtype": "Attach", "reqd": 1},
        {"fieldname": "amount", "label": "Amount", "fieldtype": "Currency"},
        {"fieldname": "direct_manager", "label": "Direct Manager", "fieldtype": "Link", "options": "User", "read_only": 1},
        {"fieldname": "final_remarks", "label": "Final Remarks", "fieldtype": "Small Text"}
    ]
    for f in fields:
        doc.append("fields", f)

    # Permissions
    permissions = [
        {"role": "Employee", "read": 1, "write": 1, "create": 1},
        {"role": "Manager", "read": 1, "write": 1},
        {"role": "CFO", "read": 1, "write": 1},
        {"role": "COO", "read": 1, "write": 1},
        {"role": "CEO", "read": 1, "write": 1},
        {"role": "System Manager", "read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1, "amend": 1}
    ]
    for p in permissions:
        doc.append("permissions", p)

    doc.save()
    frappe.msgprint("✅ Created DocType: Payment Approval Request")
