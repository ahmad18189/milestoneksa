import frappe


def execute():
	js_path = frappe.get_app_path("milestoneksa", "public", "js", "project_task_tab.js")
	with open(js_path) as f:
		script = f.read()
	if frappe.db.exists("Client Script", "Project Task Tab"):
		frappe.db.set_value("Client Script", "Project Task Tab", "script", script, update_modified=True)
		frappe.db.commit()
		print("Updated Project Task Tab client script")
