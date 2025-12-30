import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    create_custom_fields(
        {
            "Project": [
                {
                    "fieldname": "custom_project_tasks_tab",
                    "label": "Project Tasks",
                    "fieldtype": "Tab Break",
                    "insert_after": "message",
                },
                {
                    "fieldname": "custom_project_tasks_html",
                    "label": "Tasks Overview",
                    "fieldtype": "HTML",
                    "options": "<div class='project-task-tab'></div>",
                    "insert_after": "custom_project_tasks_tab",
                    "read_only": 1,
                },
            ]
        },
        ignore_validate=True,
    )
    frappe.clear_cache(doctype="Project")

