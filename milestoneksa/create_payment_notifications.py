import frappe

def execute():
    workflow_notifications = [
        ("Pending Manager Approval", "Manager"),
        ("Pending CFO Approval", "CFO"),
        ("Pending COO Approval", "COO"),
        ("Pending CEO Approval", "CEO")
    ]

    email_template = """
<p>Dear {{ role }},</p>

<p>You have a new Payment Approval Request from <strong>{{ doc.employee_name }}</strong>.</p>

<table style="border-collapse: collapse; width: 100%;">
<tr><td><strong>Employee:</strong></td><td>{{ doc.employee_name }}</td></tr>
<tr><td><strong>Department:</strong></td><td>{{ doc.department }}</td></tr>
<tr><td><strong>Date:</strong></td><td>{{ doc.application_date }}</td></tr>
<tr><td><strong>Amount:</strong></td><td>{{ doc.amount }}</td></tr>
<tr><td><strong>Description:</strong></td><td>{{ doc.description }}</td></tr>
</table>

<p>
<a href="{{ frappe.utils.get_url() }}/app/payment-approval-request/{{ doc.name }}" style="padding: 10px 15px; background-color: #2563eb; color: white; text-decoration: none;">
Open Request
</a>
</p>
"""

    for state, role in workflow_notifications:
        name = f"Payment Approval Notification - {role}"
        if frappe.db.exists("Notification", name):
            frappe.msgprint(f"Notification '{name}' already exists.")
            continue

        notification = frappe.get_doc({
            "doctype": "Notification",
            "name": name,
            "subject": f"Approval Required: {{ doc.name }} is in {state}",
            "document_type": "Payment Approval Request",
            "event": "Value Change",
            "value_changed": "workflow_state",
            "condition": f'doc.workflow_state == "{state}"',
            "message": email_template,
            "channel": "Email",
            "enabled": 1,
            "recipients": [{
                "receiver_by_role": role
            }]
        })

        notification.insert(ignore_permissions=True)
        frappe.msgprint(f"✅ Notification for '{role}' created.")

    frappe.db.commit()
    frappe.msgprint("✅ All workflow notifications created successfully.")
