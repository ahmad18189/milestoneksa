# File: milestoneksa/milestoneksa/page/project_dashboard/project_dashboard.py

import frappe

@frappe.whitelist()
def get_project_dashboard_data(project_name):
    """Fetch all data needed for the project dashboard."""
    # Permission check
    if not frappe.has_permission("Project", doc=project_name, throw=False):
        frappe.throw("Not permitted to view this project dashboard")

    # Fetch project info
    project = frappe.get_doc("Project", project_name)
    project_info = {
        "name": project.name,
        "status": project.status,
        "percent_complete": project.percent_complete,
        "planned_duration": project.get("expected_duration") or project.get("duration"),
        "estimated_cost": project.get("estimated_cost") or project.get("total_planned_cost"),
        "actual_cost": project.get("actual_cost") or project.get("total_costing_amount")
    }

    # Fetch tasks for this project
    tasks = frappe.get_all(
        "Task",
        filters={"project": project.name},
        fields=[
            "name", "subject", "status", "priority",
            "exp_start_date", "exp_end_date", "depends_on_tasks"
        ],
        order_by="exp_start_date asc"      # ← sorts oldest first
    )

    # Aggregate counts by status & priority
    status_counts = {}
    priority_counts = {}
    for t in tasks:
        status_counts[t.status] = status_counts.get(t.status, 0) + 1
        pr = t.priority or "Medium"
        priority_counts[pr] = priority_counts.get(pr, 0) + 1

    # Count pending items by custom Doctypes (if they exist)
    pending_counts = {}
    for dt in ["Project Decision", "Project Action", "Project Change Request"]:
        if frappe.db.exists("DocType", dt):
            pending_counts[dt] = frappe.db.count(
                dt, {"project": project.name, "status": ("!=", "Closed")}
            )

    return {
        "project": project_info,
        "tasks": tasks,
        "status_counts": status_counts,
        "priority_counts": priority_counts,
        "pending_counts": pending_counts
    }
