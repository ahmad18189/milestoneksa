import pathlib

import frappe


def sync():
	script_path = pathlib.Path(__file__).resolve().parent / "public" / "js" / "project_task_tab.js"
	script = script_path.read_text()
	frappe.db.set_value("Client Script", "Project Task Tab", "script", script)
	frappe.db.commit()
	return {"length": len(script), "has_dom_order": "table.element.querySelectorAll" in script}
