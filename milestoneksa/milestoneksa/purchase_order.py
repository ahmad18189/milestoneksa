# milestoneksa/milestoneksa/purchase_order.py

import frappe
from frappe.utils import nowdate, getdate


def _create_tasks(doc):
    """
    Internal helper: create Task per payment schedule row.
    Logs reasons for skipped rows as comments on the Purchase Order.
    """
    today = getdate(nowdate())

    # Resolve Project: header field or first item's project
    project = doc.project or next((item.project for item in doc.items if item.project), None)
    if not project:
        frappe.throw("Please select a Project on this Purchase Order or on at least one item.")

    created, skipped = 0, 0
    skip_messages = []
    if not doc.payment_schedule:
        return

    for row in doc.payment_schedule:
        # Skip if already linked
        if row.task:
            reason = f"Line {row.idx}: already has task {row.task}"
            skip_messages.append(reason)
            skipped += 1
            continue

        # Validate payment amount
        if (row.payment_amount or 0) <= 0:
            reason = f"Line {row.idx}: payment_amount ≤ 0 ({row.payment_amount})"
            frappe.log_error(reason, "milestoneksa")
            skip_messages.append(reason)
            skipped += 1
            continue

        # Parse due_date
        try:
            due_date = getdate(row.due_date)
        except Exception:
            reason = f"Line {row.idx}: invalid due_date '{row.due_date}'"
            frappe.log_error(reason, "milestoneksa")
            skip_messages.append(reason)
            skipped += 1
            continue

        # Determine start date from header schedule_date or transaction_date
        header_date = row.start_date or doc.get("schedule_date") or doc.transaction_date or nowdate()
        try:
            start_date = getdate(header_date)
        except Exception:
            start_date = today

        # Build Task payload (include description in subject)
        subject = f"PO {doc.name} – {row.description} – p(line {row.idx})"
        task_data = {
            "doctype": "Task",
            "project": project,
            "subject": project+" - "+row.description,
            "description": (
                f"Purchase Order: {doc.name}\n"
                f"Description: {row.description}\n"
                f"Amount: {row.payment_amount}\n"
                f"Due date: {row.due_date}"
            ),
            "status": "Open",
            "exp_start_date": start_date,
            "exp_end_date": due_date,
            "expected_time": row.get("estimated_hours") or 0
        }

        # Insert Task and link back to payment schedule row
        try:
            task = frappe.get_doc(task_data).insert(ignore_permissions=True)
            frappe.db.set_value(
                "Payment Schedule",
                row.name,
                "task",
                task.name,
                update_modified=False
            )
            created += 1
        except Exception as e:
            reason = f"Line {row.idx}: error creating task: {e}"
            skip_messages.append(reason)
            frappe.log_error(reason, "milestoneksa")
            skipped += 1

    # Final feedback
    frappe.msgprint(f"✅ {created} tasks created, {skipped} rows skipped.")

    # Log skip reasons as comments on the Purchase Order
    for msg in skip_messages:
        doc.add_comment('Comment', msg)

@frappe.whitelist()
def create_payment_tasks(doc, method=None):
    """
    Hook: Purchase Order on_submit
    Accepts a Document instance directly from the hook.
    """
    _create_tasks(doc)

@frappe.whitelist()
def generate_payment_tasks(name):
    """
    Called via JS RPC to generate tasks without submit.
    Fetches the Purchase Order by name.
    """
    doc = frappe.get_doc("Purchase Order", name)
    _create_tasks(doc)
