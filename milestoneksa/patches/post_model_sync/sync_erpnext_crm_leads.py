import frappe

from milestoneksa.crm_lead_sync import ensure_link_custom_fields, sync_all_leads


def execute():
	if "crm" not in frappe.get_installed_apps():
		return

	ensure_link_custom_fields()
	sync_all_leads()
