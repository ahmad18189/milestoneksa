"""Ensure Scheduled Job Type cron exists for attendance email reports (Sun-Thu, every 5 min)."""

import frappe

METHOD = "milestoneksa.tasks.attendance_email_reports.run_due_attendance_email_reports"
CRON = "*/5 * * * 0-4"


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
