import frappe
from frappe import _


@frappe.whitelist()
def delete_bulk_docs(doctype: str, items: str | list, delete_linked: bool = False):
	"""CRM Task uses integer names; normalize to strings before bulk delete."""
	from crm.api.doc import delete_bulk_docs as crm_delete_bulk_docs

	if not doctype:
		frappe.throw(_("Doctype is required"))
	if not items:
		frappe.throw(_("Items are required"))

	parsed_items = frappe.parse_json(items) if isinstance(items, str) else items
	if not isinstance(parsed_items, list):
		frappe.throw(_("Items must be a list"))

	return crm_delete_bulk_docs(doctype, [str(item) for item in parsed_items], delete_linked)
