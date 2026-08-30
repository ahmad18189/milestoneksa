import json
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Tuple

import frappe
from frappe import _
from frappe.model.naming import make_autoname
from frappe.utils import cint, cstr, date_diff, flt, get_datetime, getdate, nowdate


def _date_diff_inclusive(start: Optional[str], end: Optional[str]) -> Optional[int]:
    if not start or not end:
        return None
    try:
        return cint(date_diff(getdate(end), getdate(start))) + 1
    except Exception:
        return None


def _parse_assigned_users(raw) -> List[str]:
    if not raw:
        return []
    if isinstance(raw, (list, tuple)):
        return [cstr(x) for x in raw if cstr(x)]
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return []
    if isinstance(parsed, list):
        return [cstr(x) for x in parsed if cstr(x)]
    return []


def _assignee_display_names(users: Iterable[str]) -> List[str]:
    names = []
    for user in users or []:
        names.append(frappe.utils.get_fullname(user) or cstr(user))
    return names


def _normalize_assign_to(assign_to) -> List[str]:
    if assign_to is None or assign_to == "":
        return []
    if isinstance(assign_to, str):
        try:
            parsed = frappe.parse_json(assign_to)
            assign_to = parsed
        except Exception:
            assign_to = [assign_to]
    if not isinstance(assign_to, (list, tuple)):
        assign_to = [assign_to]
    return list(dict.fromkeys([cstr(user) for user in assign_to if cstr(user)]))


def _apply_task_assignments(task_name: str, assign_to) -> None:
    from frappe.desk.form.assign_to import add as assign_add
    from frappe.desk.form.assign_to import remove as assign_remove

    wanted = set(_normalize_assign_to(assign_to))
    current = set(
        frappe.get_all(
            "ToDo",
            filters={
                "reference_type": "Task",
                "reference_name": task_name,
                "status": "Open",
            },
            pluck="allocated_to",
        )
        or []
    )
    for user in wanted - current:
        assign_add(
            {
                "assign_to": [user],
                "doctype": "Task",
                "name": task_name,
            }
        )
    for user in current - wanted:
        assign_remove("Task", task_name, user)


def _treeify(tasks: Iterable[frappe._dict]) -> List[frappe._dict]:
    task_list = list(tasks)
    by_name = {task.name: task for task in task_list}
    children: Dict[Optional[str], List[frappe._dict]] = defaultdict(list)

    for task in task_list:
        parent = task.parent_task or None
        # Promote orphans (missing parent) to roots so they remain visible.
        if parent and parent not in by_name:
            parent = None
            task.parent_task = None
        children[parent].append(task)

    for bucket in children.values():
        bucket.sort(key=lambda t: (t.idx or 0, t.lft or 0, cstr(t.subject)))

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
        return frappe.defaults.get_defaults().get("currency")
    return frappe.get_cached_value("Company", company, "default_currency")


def _progress_from_status(status: Optional[str]) -> int:
    return 100 if cstr(status) in ("Completed", "Cancelled") else 0


def _serialize_task(row: frappe._dict) -> frappe._dict:
    row.duration_days = _date_diff_inclusive(row.exp_start_date, row.exp_end_date)

    # Use custom actual dates if available, otherwise use timesheet dates
    custom_actual_duration = _date_diff_inclusive(row.custom_actual_start_date, row.custom_actual_end_date)
    timesheet_duration = _date_diff_inclusive(row.act_start_date, row.act_end_date)
    row.actual_duration_days = custom_actual_duration or timesheet_duration

    row.planned_hours = flt(row.expected_time)
    row.actual_hours = flt(row.actual_time)
    row.total_costing_amount = flt(row.total_costing_amount)
    row.is_group = cint(row.is_group)
    row.progress = flt(row.progress) if row.get("progress") is not None else _progress_from_status(row.status)
    assigned_to = _parse_assigned_users(row.get("_assign"))
    row.assigned_to = assigned_to
    row.assigned_to_names = _assignee_display_names(assigned_to)
    return row


TASK_CLIENT_FIELDS = [
    "name",
    "subject",
    "status",
    "priority",
    "task_weight",
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
    "idx",
    "lft",
    "rgt",
    "progress",
    "modified",
    "custom_actual_start_date",
    "custom_actual_end_date",
    "project",
    "_assign",
]


def _serialize_task_for_client(row) -> dict:
    data = frappe._dict(row)
    _serialize_task(data)
    return {
        "name": data.name,
        "subject": data.subject,
        "status": data.status,
        "priority": data.priority,
        "task_weight": flt(data.task_weight),
        "parent_task": data.parent_task or None,
        "is_group": cint(data.is_group),
        "exp_start_date": data.exp_start_date,
        "exp_end_date": data.exp_end_date,
        "expected_time": flt(data.expected_time),
        "planned_hours": flt(data.planned_hours),
        "act_start_date": data.act_start_date,
        "act_end_date": data.act_end_date,
        "actual_time": flt(data.actual_time),
        "actual_hours": flt(data.actual_hours),
        "total_costing_amount": flt(data.total_costing_amount),
        "description": data.description,
        "idx": cint(data.idx),
        "lft": cint(data.lft),
        "rgt": cint(data.rgt) if data.get("rgt") is not None else None,
        "progress": flt(data.progress),
        "modified": cstr(data.modified) if data.get("modified") else None,
        "custom_actual_start_date": data.custom_actual_start_date,
        "custom_actual_end_date": data.custom_actual_end_date,
        "duration_days": data.duration_days,
        "actual_duration_days": data.actual_duration_days,
        "wbs": data.get("wbs"),
        "project": data.get("project"),
        "assigned_to": list(data.assigned_to or []),
        "assigned_to_names": list(data.assigned_to_names or []),
    }


def _fetch_serialized_tasks(names: Iterable[str]) -> List[dict]:
    names = [cstr(name) for name in names if cstr(name)]
    if not names:
        return []
    rows = frappe.get_all(
        "Task",
        filters={"name": ["in", names]},
        fields=TASK_CLIENT_FIELDS,
        limit_page_length=0,
    )
    by_name = {row.name: _serialize_task_for_client(row) for row in rows}
    return [by_name[name] for name in names if name in by_name]


def _build_wbs_map(project: str) -> Dict[str, str]:
    rows = frappe.get_all(
        "Task",
        filters={"project": project},
        fields=["name", "parent_task", "idx", "lft", "subject"],
        order_by="lft asc",
        limit_page_length=0,
    )
    ordered = _treeify([frappe._dict(row) for row in rows])
    return {row.name: row.wbs for row in ordered}


def _renumber_siblings(project: str, parent_task: Optional[str]) -> dict:
    filters = {"project": project}
    if parent_task:
        filters["parent_task"] = parent_task
    else:
        filters["parent_task"] = ["is", "not set"]

    siblings = frappe.get_all(
        "Task",
        filters=filters,
        fields=["name", "idx", "lft", "subject"],
        order_by="idx asc, lft asc, subject asc",
        limit_page_length=0,
    )
    ordered_names = [row.name for row in siblings]
    idx_by_name = {}
    for idx, name in enumerate(ordered_names, start=1):
        idx_by_name[name] = idx
        frappe.db.set_value("Task", name, "idx", idx, update_modified=False)
    return {
        "parent_task": parent_task,
        "ordered_names": ordered_names,
        "idx_by_name": idx_by_name,
    }


def _children_meta_for(names: Iterable[str]) -> dict:
    meta = {}
    for name in [cstr(n) for n in names if cstr(n)]:
        direct = frappe.db.count("Task", {"parent_task": name})
        meta[name] = {
            "direct_child_count": direct,
            "is_group": 1 if direct else cint(frappe.db.get_value("Task", name, "is_group")),
        }
    return meta


def _project_patch_fragment(project: Optional[str]) -> Optional[dict]:
    if not project or not frappe.db.exists("Project", project):
        return None
    percent = frappe.db.get_value("Project", project, "percent_complete")
    return {"name": project, "percent_complete": flt(percent)}


def _build_mutation_patch(
    project: Optional[str],
    *,
    task_name: Optional[str] = None,
    task_names: Optional[Iterable[str]] = None,
    affected_parent_names: Optional[Iterable[str]] = None,
    removed: Optional[Iterable[str]] = None,
    sibling_orders: Optional[List[dict]] = None,
    errors: Optional[List[str]] = None,
) -> dict:
    names = []
    if task_name:
        names.append(task_name)
    if task_names:
        names.extend(list(task_names))
    names = list(dict.fromkeys([cstr(n) for n in names if cstr(n)]))

    parent_names = list(dict.fromkeys([cstr(n) for n in (affected_parent_names or []) if cstr(n)]))
    tasks = _fetch_serialized_tasks(names)
    affected_parents = _fetch_serialized_tasks(parent_names)

    wbs_by_name = _build_wbs_map(project) if project else {}
    for row in tasks + affected_parents:
        row["wbs"] = wbs_by_name.get(row["name"])

    children_meta = _children_meta_for([row["name"] for row in tasks + affected_parents])

    patch = {
        "ok": True,
        "task": tasks[0] if len(tasks) == 1 and task_name else (tasks[0] if tasks and task_name else None),
        "tasks": tasks,
        "affected_parents": affected_parents,
        "removed": [cstr(n) for n in (removed or []) if cstr(n)],
        "sibling_order": (sibling_orders or [None])[0] if sibling_orders and len(sibling_orders) == 1 else None,
        "sibling_orders": sibling_orders or [],
        "wbs_by_name": wbs_by_name,
        "children_meta": children_meta,
        "project": _project_patch_fragment(project),
        "errors": errors or [],
    }
    return patch


def _get_task_meta_options() -> Tuple[List[str], List[str]]:
    meta = frappe.get_meta("Task")
    status_field = meta.get_field("status")
    priority_field = meta.get_field("priority")

    status_options = [opt for opt in (status_field.options or "").split("\n") if opt]
    priority_options = [opt for opt in (priority_field.options or "").split("\n") if opt]
    return status_options, priority_options


def _expand_parent_planned_bounds(task_doc):
    """Expand ancestor planned dates before child validation runs."""
    if not task_doc.parent_task or not (task_doc.exp_start_date or task_doc.exp_end_date):
        return

    child_start = getdate(task_doc.exp_start_date) if task_doc.exp_start_date else None
    child_end = getdate(task_doc.exp_end_date) if task_doc.exp_end_date else None
    parent_name = task_doc.parent_task

    while parent_name:
        parent = frappe.db.get_value(
            "Task",
            parent_name,
            ["name", "parent_task", "exp_start_date", "exp_end_date"],
            as_dict=True,
        )
        if not parent:
            break

        updates = {}
        if child_start and (not parent.exp_start_date or child_start < getdate(parent.exp_start_date)):
            updates["exp_start_date"] = child_start
        if child_end and (not parent.exp_end_date or child_end > getdate(parent.exp_end_date)):
            updates["exp_end_date"] = child_end

        if updates:
            frappe.db.set_value("Task", parent.name, updates, update_modified=True)

        parent_name = parent.parent_task


def _update_project_percent_complete(project: str):
    if not project:
        return
    project_doc = frappe.get_doc("Project", project)
    project_doc.update_percent_complete()
    project_doc.save(ignore_permissions=True)


@frappe.whitelist()
def get_project_tasks(project: str):
    if not project:
        frappe.throw(_("Project is required"))

    records = frappe.db.get_list(
        "Task",
        filters={"project": project},
        fields=TASK_CLIENT_FIELDS,
        order_by="lft asc",
        as_list=False,
    )

    tasks = [_serialize_task(frappe._dict(row)) for row in records]
    ordered = [_serialize_task_for_client(row) for row in _treeify(tasks)]
    currency = _get_currency_for_project(project)
    status_options, priority_options = _get_task_meta_options()

    return {
        "tasks": ordered,
        "currency": currency,
        "status_options": status_options,
        "priority_options": priority_options,
    }


def _get_task_descendants(task_name: str) -> List[frappe._dict]:
    if not task_name:
        return []

    project = frappe.db.get_value("Task", task_name, "project")
    filters = {"parent_task": ["is", "set"]}
    if project:
        filters["project"] = project

    all_children = frappe.get_all(
        "Task",
        filters=filters,
        fields=["name", "subject", "status", "parent_task", "is_group", "idx", "lft", "project"],
        order_by="idx asc, lft asc, subject asc",
        limit_page_length=0,
    )
    children_by_parent: Dict[str, List[frappe._dict]] = defaultdict(list)
    for child in all_children:
        children_by_parent[child.parent_task].append(child)

    descendants: List[frappe._dict] = []

    def walk(parent: str, level: int = 1):
        for child in children_by_parent.get(parent, []):
            child.level = level
            descendants.append(child)
            walk(child.name, level + 1)

    walk(task_name)
    return descendants


@frappe.whitelist()
def get_task_completion_children(task_name: str):
    if not task_name:
        frappe.throw(_("Task is required"))

    task = frappe.get_doc("Task", task_name)
    children = _get_task_descendants(task_name)
    return {
        "task": {
            "name": task.name,
            "subject": task.subject,
            "status": task.status,
            "project": task.project,
        },
        "children": [
            {
                "name": child.name,
                "subject": child.subject,
                "status": child.status,
                "parent_task": child.parent_task,
                "is_group": cint(child.is_group),
                "level": cint(child.level),
            }
            for child in children
        ],
    }


def _complete_parent_task_and_descendants(task_name: str, commit: bool = True):
    task = frappe.get_doc("Task", task_name)
    children = _get_task_descendants(task_name)
    if not children:
        frappe.throw(_("This task has no child tasks requiring acknowledgement."))

    completed_values = {
        "status": "Completed",
        "progress": 100,
        "completed_by": frappe.session.user,
        "completed_on": nowdate(),
        "modified": get_datetime(),
        "modified_by": frappe.session.user,
    }

    completed_task_names = [child.name for child in children] + [task.name]
    for completed_task_name in completed_task_names:
        frappe.db.set_value(
            "Task",
            completed_task_name,
            completed_values,
            update_modified=False,
        )

    for child in sorted(children, key=lambda row: cint(row.level), reverse=True):
        if child.parent_task:
            recalculate_parent_task(child.parent_task, propagate=0, commit=0)
    if task.parent_task:
        recalculate_parent_task(task.parent_task, propagate=1, commit=0)
    if task.project:
        _update_project_percent_complete(task.project)

    if commit:
        frappe.db.commit()

    return {
        "name": task.name,
        "status": "Completed",
        "children_count": len(children),
        "completed_task_count": len(completed_task_names),
    }


@frappe.whitelist()
def complete_parent_task_with_acknowledgement(task_name: str):
    if not task_name:
        frappe.throw(_("Task is required"))
    return _complete_parent_task_and_descendants(task_name, commit=True)


def _next_sibling_idx(project: str, parent_task: Optional[str]) -> int:
    filters = {"project": project}
    if parent_task:
        filters["parent_task"] = parent_task
    else:
        filters["parent_task"] = ["is", "not set"]

    max_idx = frappe.db.get_all("Task", filters=filters, fields=["max(idx) as idx"])
    return cint(max_idx[0].idx if max_idx else 0) + 1


def _ensure_parent_task(parent_task: Optional[str], project: str, child_name: Optional[str] = None):
    if not parent_task:
        return

    parent = frappe.get_doc("Task", parent_task)
    if parent.project != project:
        frappe.throw(_("Parent Task must belong to the same Project"))
    if child_name and parent.name == child_name:
        frappe.throw(_("A task cannot be its own parent"))

    if not cint(parent.is_group):
        parent.is_group = 1
        parent.save(ignore_permissions=True)


@frappe.whitelist()
def create_project_task(project: str, task=None):
    """Create a new task linked to the project"""
    if not project:
        frappe.throw(_("Project is required"))

    if task is None:
        task = {}
    if isinstance(task, str):
        task = frappe.parse_json(task)

    parent_task = task.get("parent_task") or None
    _ensure_parent_task(parent_task, project)

    doc = frappe.new_doc("Task")
    doc.update(
        {
            "project": project,
            "subject": task.get("subject"),
            "is_group": cint(task.get("is_group")),
            "status": task.get("status") or "Open",
            "priority": task.get("priority") or "Medium",
            "task_weight": flt(task.get("task_weight")),
            "exp_start_date": task.get("exp_start_date"),
            "exp_end_date": task.get("exp_end_date"),
            "expected_time": flt(task.get("planned_hours")),
            "custom_actual_start_date": task.get("custom_actual_start_date") or task.get("exp_start_date"),
            "custom_actual_end_date": task.get("custom_actual_end_date") or task.get("exp_end_date"),
            "description": task.get("description"),
            "parent_task": parent_task,
            "idx": _next_sibling_idx(project, parent_task),
        }
    )
    if not doc.subject:
        frappe.throw(_("Subject is required"))

    doc.insert()

    assign_to = task.get("assign_to")
    if assign_to is None:
        assign_to = task.get("assigned_to")
    if assign_to is not None:
        _apply_task_assignments(doc.name, assign_to)

    sibling_order = _renumber_siblings(project, parent_task)
    affected_parents = []
    if parent_task:
        recalculate_parent_task(parent_task, propagate=1, commit=0)
        # Collect ancestor chain
        cursor = parent_task
        while cursor:
            affected_parents.append(cursor)
            cursor = frappe.db.get_value("Task", cursor, "parent_task")

    _update_project_percent_complete(project)
    frappe.db.commit()

    return _build_mutation_patch(
        project,
        task_name=doc.name,
        affected_parent_names=affected_parents,
        sibling_orders=[sibling_order],
    )


@frappe.whitelist()
def update_project_task(task_name: str, updates=None):
    """Update a task with the given updates dict"""
    if not task_name:
        frappe.throw(_("Task is required"))

    if updates is None:
        updates = {}
    if isinstance(updates, str):
        updates = frappe.parse_json(updates)

    completion_acknowledged = cint(updates.pop("completion_acknowledged", 0))
    assign_to = updates.pop("assign_to", None)
    if assign_to is None and "assigned_to" in updates:
        assign_to = updates.pop("assigned_to")

    allowed_fields = {
        "subject",
        "is_group",
        "status",
        "priority",
        "task_weight",
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
    old_parent_task = doc.parent_task or None
    acknowledged_parent_completion = False
    if cstr(updates.get("status")) == "Completed" and doc.status != "Completed":
        child_count = frappe.db.count("Task", {"parent_task": doc.name})
        if child_count and not completion_acknowledged:
            frappe.throw(
                _("Please acknowledge the child tasks before completing this parent task."),
                title=_("Parent Task Completion Requires Acknowledgement"),
            )
        acknowledged_parent_completion = bool(child_count and completion_acknowledged)
        if acknowledged_parent_completion:
            updates.pop("status", None)

    dirty = False

    for key, value in updates.items():
        if key not in allowed_fields:
            continue

        if key in ("planned_hours", "expected_time"):
            key = "expected_time"
            value = flt(value)
        elif key == "task_weight":
            value = flt(value)
        elif key == "is_group":
            value = cint(value)
        elif key == "status":
            doc.progress = _progress_from_status(value)
            dirty = True
        elif key == "parent_task":
            value = value or None
            _ensure_parent_task(value, doc.project, doc.name)
        elif key in ("exp_start_date", "exp_end_date", "custom_actual_start_date", "custom_actual_end_date"):
            if not value:
                value = None
            else:
                try:
                    value = getdate(value)
                except Exception:
                    frappe.throw(_("Invalid date for {0}").format(key))

        if key in ("exp_start_date", "exp_end_date", "custom_actual_start_date", "custom_actual_end_date"):
            old_value = doc.get(key)
            old_cmp = getdate(old_value) if old_value else None
            new_cmp = getdate(value) if value else None
            if old_cmp != new_cmp:
                doc.set(key, value)
                dirty = True
            continue

        if doc.get(key) != value:
            doc.set(key, value)
            dirty = True

    if doc.exp_start_date and not doc.custom_actual_start_date:
        doc.custom_actual_start_date = doc.exp_start_date
        dirty = True

    if doc.exp_end_date and not doc.custom_actual_end_date:
        doc.custom_actual_end_date = doc.exp_end_date
        dirty = True

    if doc.exp_start_date and doc.exp_end_date and getdate(doc.exp_start_date) > getdate(doc.exp_end_date):
        if "exp_start_date" in updates and "exp_end_date" not in updates:
            doc.exp_end_date = doc.exp_start_date
        elif "exp_end_date" in updates and "exp_start_date" not in updates:
            doc.exp_start_date = doc.exp_end_date
        dirty = True

    if dirty:
        # Expand parents in DB first so ERPNext child-vs-parent date validation passes.
        _expand_parent_planned_bounds(doc)
        doc.save()


    if assign_to is not None:
        _apply_task_assignments(doc.name, assign_to)

    if acknowledged_parent_completion:
        completion_result = _complete_parent_task_and_descendants(doc.name, commit=False)
        dirty = True
    else:
        completion_result = None

    if dirty:
        # Recalculate old and new parent chains
        parents_to_recalc = []
        if old_parent_task:
            parents_to_recalc.append(old_parent_task)
        if doc.parent_task and doc.parent_task not in parents_to_recalc:
            parents_to_recalc.append(doc.parent_task)

        sibling_orders = []
        if old_parent_task != (doc.parent_task or None):
            sibling_orders.append(_renumber_siblings(doc.project, old_parent_task or None))
            sibling_orders.append(_renumber_siblings(doc.project, doc.parent_task or None))

        if not acknowledged_parent_completion:
            for parent_name in parents_to_recalc:
                recalculate_parent_task(parent_name, propagate=1, commit=0)

        affected_parents = []
        for parent_name in parents_to_recalc:
            cursor = parent_name
            while cursor:
                if cursor not in affected_parents:
                    affected_parents.append(cursor)
                cursor = frappe.db.get_value("Task", cursor, "parent_task")

        _update_project_percent_complete(doc.project)
        frappe.db.commit()

        task_names = [doc.name]
        if completion_result:
            # Include completed descendants for silent client merge
            descendants = _get_task_descendants(doc.name)
            task_names.extend([row.name for row in descendants])
            task_names = list(dict.fromkeys(task_names))

        return _build_mutation_patch(
            doc.project,
            task_name=doc.name,
            task_names=task_names,
            affected_parent_names=affected_parents,
            sibling_orders=sibling_orders,
        )

    return _build_mutation_patch(doc.project, task_name=doc.name)


@frappe.whitelist()
def reorder_project_task(task_name: str, direction: str):
    """Move a task up/down within its current parent group for the Project Tasks table."""
    if not task_name:
        frappe.throw(_("Task is required"))
    if direction not in ("up", "down"):
        frappe.throw(_("Direction must be up or down"))

    task = frappe.get_doc("Task", task_name)
    parent_task = task.parent_task or None
    filters = {"project": task.project}
    if parent_task:
        filters["parent_task"] = parent_task
    else:
        filters["parent_task"] = ["is", "not set"]

    siblings = frappe.get_all(
        "Task",
        filters=filters,
        fields=["name", "idx", "lft", "subject"],
        order_by="idx asc, lft asc, subject asc",
        limit_page_length=0,
    )
    names = [row.name for row in siblings]
    try:
        index = names.index(task.name)
    except ValueError:
        frappe.throw(_("Task was not found in its sibling group"))

    swap_with = index - 1 if direction == "up" else index + 1
    if swap_with < 0 or swap_with >= len(siblings):
        return {"moved": False}

    names[index], names[swap_with] = names[swap_with], names[index]
    for idx, name in enumerate(names, start=1):
        frappe.db.set_value("Task", name, "idx", idx, update_modified=False)

    frappe.db.commit()
    return {"moved": True, "task": task.name, "direction": direction}


@frappe.whitelist()
def reorder_project_task_siblings(project: str, parent_task: Optional[str], task_names):
    """Persist a drag/drop order for tasks within the same parent group."""
    if not project:
        frappe.throw(_("Project is required"))

    if isinstance(task_names, str):
        task_names = frappe.parse_json(task_names)
    if not isinstance(task_names, list) or not task_names:
        frappe.throw(_("Task order is required"))
    task_names = [cstr(name) for name in task_names if cstr(name)]
    if len(task_names) != len(set(task_names)):
        frappe.throw(_("Task order contains duplicate tasks"))

    parent_task = parent_task or None
    if parent_task:
        _ensure_parent_task(parent_task, project)

    filters = {"project": project}
    if parent_task:
        filters["parent_task"] = parent_task
    else:
        filters["parent_task"] = ["is", "not set"]

    sibling_rows = frappe.get_all(
        "Task",
        filters=filters,
        fields=["name", "project", "parent_task"],
        order_by="idx asc, lft asc, subject asc",
        limit_page_length=0,
    )
    sibling_names = [row.name for row in sibling_rows]
    sibling_set = set(sibling_names)
    if not set(task_names).issubset(sibling_set):
        frappe.throw(_("Some tasks in the order were not found"))
    if set(task_names) != sibling_set:
        frappe.throw(_("Task order must include all tasks in the same parent group"))

    for row in sibling_rows:
        if row.project != project:
            frappe.throw(_("All tasks must belong to the same Project"))
        if (row.parent_task or None) != parent_task:
            frappe.throw(_("Tasks can only be reordered inside the same parent group"))

    for idx, name in enumerate(task_names, start=1):
        frappe.db.set_value("Task", name, "idx", idx, update_modified=False)

    sibling_order = {
        "parent_task": parent_task,
        "ordered_names": task_names,
        "idx_by_name": {name: idx for idx, name in enumerate(task_names, start=1)},
    }
    frappe.db.commit()
    patch = _build_mutation_patch(
        project,
        task_names=task_names,
        sibling_orders=[sibling_order],
    )
    patch["updated"] = len(task_names)
    patch["parent_task"] = parent_task
    return patch


@frappe.whitelist()
def recalculate_parent_task(parent_task_name: str, propagate: int = 0, commit: int = 1):
    """Recalculate parent task metrics based on children tasks"""
    if not parent_task_name:
        return
    
    parent = frappe.get_doc("Task", parent_task_name)
    
    # Get all child tasks
    children = frappe.get_all(
        "Task",
        filters={"parent_task": parent_task_name},
        fields=[
            "exp_start_date", "exp_end_date", "expected_time", "actual_time", "status", "progress",
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
    
    # Parent status follows its direct children. When every child is completed,
    # the parent becomes completed; if a completed parent gets reopened children,
    # it is moved back to an active status.
    child_statuses = [cstr(c.status) for c in children]
    all_completed = all(status == "Completed" for status in child_statuses)
    if all_completed:
        parent.status = "Completed"
    elif any(status == "Working" for status in child_statuses):
        parent.status = "Working"
    elif parent.status == "Completed":
        parent.status = "Open"

    child_progress_values = [
        flt(c.progress) if c.progress is not None else _progress_from_status(c.status)
        for c in children
    ]
    parent.progress = flt(sum(child_progress_values) / len(child_progress_values), 2)
    
    _expand_parent_planned_bounds(parent)
    parent.save()

    if cint(propagate) and parent.parent_task:
        recalculate_parent_task(parent.parent_task, propagate=1, commit=0)

    if cint(commit):
        frappe.db.commit()

    return {
        "parent": parent.name,
        "children_count": len(children),
        "total_planned_hours": parent.expected_time,
        "status": parent.status,
        "progress": parent.progress,
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
    
    parent_task_names = []
    seen_parent_tasks = set()
    for task in all_tasks:
        if task.parent_task and task.parent_task not in seen_parent_tasks:
            parent_task_names.append(task.parent_task)
            seen_parent_tasks.add(task.parent_task)
    
    updated_count = 0
    for parent_name in parent_task_names:
        try:
            recalculate_parent_task(parent_name)
            updated_count += 1
        except Exception as e:
            frappe.log_error(f"Failed to recalculate parent {parent_name}: {str(e)}")

    _update_project_percent_complete(project)
    
    return {
        "updated_count": updated_count,
        "total_parents": len(parent_task_names)
    }


def copy_project_tasks_to_project(source_project: str, target_project: str, target_parent_subject: str):
    """Copy all tasks from one project to another and attach copied roots to a target parent."""
    if not source_project or not target_project or not target_parent_subject:
        frappe.throw(_("Source project, target project, and target parent subject are required"))

    target_parent = frappe.db.get_value(
        "Task",
        {"project": target_project, "subject": ["like", f"%{target_parent_subject}%"]},
        ["name", "is_group"],
        as_dict=True,
    )
    if not target_parent:
        frappe.throw(_("Target parent task not found"))

    if not cint(target_parent.is_group):
        parent_doc = frappe.get_doc("Task", target_parent.name)
        parent_doc.is_group = 1
        parent_doc.save(ignore_permissions=True)

    source_rows = frappe.get_all(
        "Task",
        filters={"project": source_project},
        fields=["name", "parent_task", "lft", "idx"],
        order_by="lft asc",
        limit_page_length=10000,
    )

    copy_fields = [
        "subject",
        "is_group",
        "status",
        "priority",
        "exp_start_date",
        "exp_end_date",
        "expected_time",
        "description",
        "custom_actual_start_date",
        "custom_actual_end_date",
    ]

    mapping = {}
    root_count = 0

    def next_task_name():
        for _i in range(1000):
            name = make_autoname("TASK-.YYYY.-.#####")
            if not frappe.db.exists("Task", name):
                return name
        frappe.throw(_("Unable to generate a unique Task name"))

    for source_row in source_rows:
        source_doc = frappe.get_doc("Task", source_row.name)
        parent_task = mapping.get(source_doc.parent_task) if source_doc.parent_task else target_parent.name
        if not parent_task:
            parent_task = target_parent.name

        new_doc = frappe.new_doc("Task")
        for fieldname in copy_fields:
            if source_doc.meta.has_field(fieldname):
                new_doc.set(fieldname, source_doc.get(fieldname))

        new_doc.project = target_project
        new_doc.parent_task = parent_task
        new_doc.idx = source_doc.idx or 0
        new_doc.insert(ignore_permissions=True, set_name=next_task_name())

        mapping[source_doc.name] = new_doc.name
        if not source_doc.parent_task:
            root_count += 1

    frappe.db.commit()
    recalculate_all_project_parents(target_project)
    frappe.db.commit()

    return {
        "source_project": source_project,
        "target_project": target_project,
        "target_parent": target_parent.name,
        "source_tasks": len(source_rows),
        "copied_tasks": len(mapping),
        "copied_root_tasks": root_count,
        "first_5_mappings": list(mapping.items())[:5],
    }


@frappe.whitelist()
def delete_project_tasks(task_names, force: int = 1, delete_connected: int = 0):
    """
    Delete exactly the requested tasks by default.

    Connected tasks includes:
    If delete_connected is explicitly enabled, connected tasks include descendants
    and tasks that depend on any requested task.
    """

    if not task_names:
        frappe.throw(_("Task names are required"))

    if isinstance(task_names, str):
        task_names = frappe.parse_json(task_names)

    if not isinstance(task_names, list):
        task_names = [task_names]

    force = cint(force)
    delete_connected = cint(delete_connected)

    # Clean input
    roots = [t for t in task_names if t]
    if not roots:
        frappe.throw(_("Task names are required"))

    def _expand_descendants(names: set[str]) -> set[str]:
        """Return names + all descendants (nested set)."""
        # Get lft/rgt for current set
        rows = frappe.get_all("Task", filters={"name": ["in", list(names)]}, fields=["name", "lft", "rgt"])
        if not rows:
            return set()

        descendants: set[str] = set()
        for r in rows:
            if r.lft is None or r.rgt is None:
                continue
            # All nodes inside the interval are descendants including self
            interval = frappe.get_all(
                "Task",
                filters={"lft": [">=", r.lft], "rgt": ["<=", r.rgt]},
                fields=["name"],
                limit_page_length=0,
            )
            descendants.update(d.name for d in interval if d.name)
        return descendants

    def _expand_reverse_dependencies(names: set[str]) -> set[str]:
        """Tasks that depend on given tasks (reverse of Task.depends_on)."""
        # tabTask Depends On: parent = the Task which has the dependency row; task = referenced Task
        if not names:
            return set()
        parents = frappe.get_all(
            "Task Depends On",
            filters={"task": ["in", list(names)]},
            fields=["parent"],
            limit_page_length=0,
        )
        return set(p.parent for p in parents if p.parent)

    to_delete: set[str] = set(roots)

    if delete_connected:
        # Expand until stable: descendants + reverse dependencies (+ their descendants)
        prev_size = -1
        while prev_size != len(to_delete):
            prev_size = len(to_delete)
            # descendants
            to_delete |= _expand_descendants(to_delete)
            # reverse dependency parents
            dep_parents = _expand_reverse_dependencies(to_delete)
            if dep_parents:
                to_delete |= dep_parents
                to_delete |= _expand_descendants(dep_parents)

    # Capture project + parents before deletion for silent client patch
    pre_rows = frappe.get_all(
        "Task",
        filters={"name": ["in", list(to_delete)]},
        fields=["name", "lft", "parent_task", "project"],
        limit_page_length=0,
    )
    lft_map = {r.name: (r.lft or 0) for r in pre_rows}
    parent_map = {r.name: (r.parent_task or None) for r in pre_rows}
    project = next((r.project for r in pre_rows if r.project), None)
    ordered = sorted(list(to_delete), key=lambda n: (lft_map.get(n, 0), n), reverse=True)

    deleted: list[str] = []
    errors: list[str] = []
    surviving_parents = set()

    for name in ordered:
        parent_name = parent_map.get(name)
        try:
            frappe.delete_doc("Task", name, force=force, ignore_permissions=True)
            deleted.append(name)
            if parent_name:
                surviving_parents.add(parent_name)
        except frappe.DoesNotExistError:
            continue
        except Exception as e:
            msg = f"Failed to delete task {name}: {str(e)}"
            errors.append(msg)
            frappe.log_error(msg, "Delete Task Error")

    # Clean dependency rows that pointed at deleted tasks so parent save does not fail
    if deleted:
        frappe.db.delete("Task Depends On", {"task": ["in", deleted]})

    # Do not recalc parents that were also deleted
    surviving_parents = {p for p in surviving_parents if p not in set(deleted) and frappe.db.exists("Task", p)}

    for parent_name in list(surviving_parents):
        try:
            recalculate_parent_task(parent_name, propagate=1, commit=0)
        except Exception as e:
            # Parent save can fail if unrelated link rows are dirty; still return the delete patch.
            errors.append(f"Failed to recalculate parent {parent_name}: {str(e)}")
            frappe.log_error(str(e), "Delete Task Parent Recalc")

    expanded_parents = []
    for parent_name in surviving_parents:
        cursor = parent_name
        while cursor:
            if cursor not in expanded_parents and frappe.db.exists("Task", cursor):
                expanded_parents.append(cursor)
            cursor = frappe.db.get_value("Task", cursor, "parent_task") if frappe.db.exists("Task", cursor) else None

    if project:
        try:
            _update_project_percent_complete(project)
        except Exception:
            pass

    frappe.db.commit()

    patch = _build_mutation_patch(
        project,
        removed=deleted,
        affected_parent_names=expanded_parents,
        errors=errors,
    )
    patch.update(
        {
            "requested": roots,
            "delete_connected": bool(delete_connected),
            "force": bool(force),
            "deleted_count": len(deleted),
            "deleted_tasks": deleted,
        }
    )
    return patch

