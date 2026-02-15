import json
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Tuple

import frappe
from frappe import _
from frappe.utils import cint, cstr, date_diff, flt, getdate


def _date_diff_inclusive(start: Optional[str], end: Optional[str]) -> Optional[int]:
    if not start or not end:
        return None
    try:
        return cint(date_diff(getdate(end), getdate(start))) + 1
    except Exception:
        return None


def _treeify(tasks: Iterable[frappe._dict]) -> List[frappe._dict]:
    children: Dict[Optional[str], List[frappe._dict]] = defaultdict(list)
    for task in tasks:
        parent = task.parent_task or None
        children[parent].append(task)

    for bucket in children.values():
        bucket.sort(key=lambda t: (t.lft or 0, cstr(t.subject)))

    ordered: List[frappe._dict] = []

    def walk(node: Optional[str], prefix: Optional[str] = None):
        for idx, child in enumerate(children.get(node, []), start=1):
            wbs = f"{prefix}.{idx}" if prefix else cstr(idx)
            child.wbs = wbs
            ordered.append(child)
            walk(child.name, wbs)

    walk(None, None)
    return ordered


def _get_currency_for_project(project: str) -> Optional[str]:
    company = frappe.db.get_value("Project", project, "company")
    if not company:
        return frappe.defaults.get_default("currency")
    return frappe.get_cached_value("Company", company, "default_currency")


def _serialize_task(row: frappe._dict) -> frappe._dict:
    row.duration_days = _date_diff_inclusive(row.exp_start_date, row.exp_end_date)
    
    # Use custom actual dates if available, otherwise use timesheet dates
    custom_actual_duration = _date_diff_inclusive(row.custom_actual_start_date, row.custom_actual_end_date)
    timesheet_duration = _date_diff_inclusive(row.act_start_date, row.act_end_date)
    row.actual_duration_days = custom_actual_duration or timesheet_duration
    
    row.planned_hours = flt(row.expected_time)
    row.actual_hours = flt(row.actual_time)
    row.total_costing_amount = flt(row.total_costing_amount)
    return row


def _get_task_meta_options() -> Tuple[List[str], List[str]]:
    meta = frappe.get_meta("Task")
    status_field = meta.get_field("status")
    priority_field = meta.get_field("priority")

    status_options = [opt for opt in (status_field.options or "").split("\n") if opt]
    priority_options = [opt for opt in (priority_field.options or "").split("\n") if opt]
    return status_options, priority_options


@frappe.whitelist()
def get_project_tasks(project: str):
    if not project:
        frappe.throw(_("Project is required"))

    fields = [
        "name",
        "subject",
        "status",
        "priority",
        "parent_task",
        "is_group",
        "exp_start_date",
        "exp_end_date",
        "expected_time",
        "act_start_date",
        "act_end_date",
        "actual_time",
        "total_costing_amount",
        "description",
        "lft",
        "custom_actual_start_date",
        "custom_actual_end_date",
    ]

    records = frappe.db.get_list(
        "Task",
        filters={"project": project},
        fields=fields,
        order_by="lft asc",
        as_list=False,
    )

    tasks = [_serialize_task(frappe._dict(row)) for row in records]
    ordered = _treeify(tasks)
    currency = _get_currency_for_project(project)
    status_options, priority_options = _get_task_meta_options()

    return {
        "tasks": ordered,
        "currency": currency,
        "status_options": status_options,
        "priority_options": priority_options,
    }


@frappe.whitelist()
def create_project_task(project: str, task=None):
    """Create a new task linked to the project"""
    if not project:
        frappe.throw(_("Project is required"))

    if task is None:
        task = {}
    if isinstance(task, str):
        task = frappe.parse_json(task)

    doc = frappe.new_doc("Task")
    doc.update(
        {
            "project": project,
            "subject": task.get("subject"),
            "is_group": cint(task.get("is_group")),
            "status": task.get("status") or "Open",
            "priority": task.get("priority") or "Medium",
            "exp_start_date": task.get("exp_start_date"),
            "exp_end_date": task.get("exp_end_date"),
            "expected_time": flt(task.get("planned_hours")),
            "custom_actual_start_date": task.get("custom_actual_start_date"),
            "custom_actual_end_date": task.get("custom_actual_end_date"),
            "description": task.get("description"),
            "parent_task": task.get("parent_task") if not task.get("is_group") else None,
        }
    )
    if not doc.subject:
        frappe.throw(_("Subject is required"))

    doc.insert()
    frappe.db.commit()
    return doc.name


@frappe.whitelist()
def update_project_task(task_name: str, updates=None):
    """Update a task with the given updates dict"""
    if not task_name:
        frappe.throw(_("Task is required"))

    if updates is None:
        updates = {}
    if isinstance(updates, str):
        updates = frappe.parse_json(updates)

    allowed_fields = {
        "subject",
        "is_group",
        "status",
        "priority",
        "exp_start_date",
        "exp_end_date",
        "planned_hours",
        "expected_time",
        "parent_task",
        "description",
        "custom_actual_start_date",
        "custom_actual_end_date",
    }

    doc = frappe.get_doc("Task", task_name)
    dirty = False

    for key, value in updates.items():
        if key not in allowed_fields:
            continue

        if key in ("planned_hours", "expected_time"):
            key = "expected_time"
            value = flt(value)
        elif key == "is_group":
            value = cint(value)
        elif key in ("exp_start_date", "exp_end_date", "custom_actual_start_date", "custom_actual_end_date") and not value:
            value = None

        if doc.get(key) != value:
            doc.set(key, value)
            dirty = True

    if dirty:
        doc.save()
        frappe.db.commit()
        
        # Recalculate parent metrics if this task has a parent
        if doc.parent_task:
            recalculate_parent_task(doc.parent_task)

    return doc.name


@frappe.whitelist()
def recalculate_parent_task(parent_task_name: str):
    """Recalculate parent task metrics based on children tasks"""
    if not parent_task_name:
        return
    
    parent = frappe.get_doc("Task", parent_task_name)
    
    # Get all child tasks
    children = frappe.get_all(
        "Task",
        filters={"parent_task": parent_task_name},
        fields=[
            "exp_start_date", "exp_end_date", "expected_time", "actual_time", "status",
            "custom_actual_start_date", "custom_actual_end_date"
        ]
    )
    
    if not children:
        return
    
    # Calculate aggregated PLANNED metrics
    start_dates = [c.exp_start_date for c in children if c.exp_start_date]
    end_dates = [c.exp_end_date for c in children if c.exp_end_date]
    
    parent.exp_start_date = min(start_dates) if start_dates else None
    parent.exp_end_date = max(end_dates) if end_dates else None
    parent.expected_time = sum(flt(c.expected_time) for c in children)
    
    # Calculate aggregated ACTUAL metrics
    actual_start_dates = [c.custom_actual_start_date for c in children if c.custom_actual_start_date]
    actual_end_dates = [c.custom_actual_end_date for c in children if c.custom_actual_end_date]
    
    parent.custom_actual_start_date = min(actual_start_dates) if actual_start_dates else None
    parent.custom_actual_end_date = max(actual_end_dates) if actual_end_dates else None
    
    # Sum actual hours from children (only if they have actual time logged)
    # Note: actual_time comes from Timesheet, we keep that as is
    # But if you want to aggregate, you can uncomment:
    # total_actual = sum(flt(c.actual_time) for c in children if c.actual_time)
    # if total_actual > 0:
    #     parent.actual_time = total_actual
    
    # Check if all children are completed
    all_completed = all(c.status == "Completed" for c in children if c.status)
    if all_completed and len(children) > 0:
        parent.status = "Completed"
    elif any(c.status == "Working" for c in children):
        parent.status = "Working"
    
    parent.save()
    frappe.db.commit()
    
    return {
        "parent": parent.name,
        "children_count": len(children),
        "total_planned_hours": parent.expected_time
    }


@frappe.whitelist()
def recalculate_all_project_parents(project: str):
    """Recalculate all parent tasks in a project"""
    if not project:
        frappe.throw(_("Project is required"))
    
    # Get all parent tasks (tasks that have children)
    all_tasks = frappe.get_all(
        "Task",
        filters={"project": project},
        fields=["name", "parent_task"],
        order_by="lft desc"  # Process deepest children first
    )
    
    parent_task_names = set()
    for task in all_tasks:
        if task.parent_task:
            parent_task_names.add(task.parent_task)
    
    updated_count = 0
    for parent_name in parent_task_names:
        try:
            recalculate_parent_task(parent_name)
            updated_count += 1
        except Exception as e:
            frappe.log_error(f"Failed to recalculate parent {parent_name}: {str(e)}")
    
    return {
        "updated_count": updated_count,
        "total_parents": len(parent_task_names)
    }

