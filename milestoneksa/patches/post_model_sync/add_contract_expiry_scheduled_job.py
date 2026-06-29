"""Ensure Scheduled Job Type cron exists for contract expiry alerts (daily 8 AM Sun-Thu)."""

import frappe

METHOD = "milestoneksa.tasks.contract_expiry_alerts.run_contract_expiry_alerts"
CRON = "0 8 * * 0-4"


def execute():
	if not frappe.db.exists("Scheduled Job Type", {"method": METHOD}):
		doc = frappe.get_doc(
			{
				"doctype": "Scheduled Job Type",
				"method": METHOD,
				"frequency": "Cron",
				"cron_format": CRON,
				"stopped": 0,
			}
		)
		doc.insert(ignore_permissions=True)
		return

	name = frappe.db.get_value("Scheduled Job Type", {"method": METHOD}, "name")
	doc = frappe.get_doc("Scheduled Job Type", name)
	if doc.cron_format == CRON and doc.frequency == "Cron":
		return
	doc.cron_format = CRON
	doc.frequency = "Cron"
	doc.save(ignore_permissions=True)
