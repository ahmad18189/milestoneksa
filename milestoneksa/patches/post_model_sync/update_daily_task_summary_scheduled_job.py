"""Force Scheduled Job Type cron for Daily Task Summary (4 PM Sun–Thu).

Frappe reads cron from hooks during migrate; if migrate was skipped, the DB can
still show the old ``0 9 * * *`` schedule."""
import frappe

METHOD = "milestoneksa.tasks.daily_task_summary.send_daily_project_task_summary"
CRON = "0 16 * * 0-4"


def execute():
	name = frappe.db.get_value("Scheduled Job Type", {"method": METHOD}, "name")
	if not name:
		return
	doc = frappe.get_doc("Scheduled Job Type", name)
	if doc.cron_format == CRON and doc.frequency == "Cron":
		return
	doc.cron_format = CRON
	doc.frequency = "Cron"
	doc.save(ignore_permissions=True)
