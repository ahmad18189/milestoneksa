import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

SYNC_FLAG = "in_lead_sync"

ERP_TO_CRM_STATUS = {
	"Lead": "New",
	"Open": "New",
	"Replied": "Contacted",
	"Opportunity": "Qualified",
	"Quotation": "Qualified",
	"Interested": "Nurture",
	"Converted": "Converted",
	"Lost Quotation": "Unqualified",
	"Do Not Contact": "Junk",
}

CRM_TO_ERP_STATUS = {
	"New": "Lead",
	"Contacted": "Replied",
	"Nurture": "Interested",
	"Qualified": "Opportunity",
	"Converted": "Converted",
	"Unqualified": "Lost Quotation",
	"Junk": "Do Not Contact",
}

SHARED_FIELDS = (
	"salutation",
	"first_name",
	"middle_name",
	"last_name",
	"lead_name",
	"job_title",
	"gender",
	"website",
	"mobile_no",
	"phone",
	"territory",
	"industry",
	"no_of_employees",
	"annual_revenue",
	"lead_owner",
	"naming_series",
	"source",
)


def ensure_link_custom_fields():
	create_custom_fields(
		{
			"Lead": [
				{
					"fieldname": "crm_lead",
					"fieldtype": "Link",
					"label": "CRM Lead",
					"options": "CRM Lead",
					"insert_after": "lead_name",
					"read_only": 1,
					"no_copy": 1,
				}
			],
			"CRM Lead": [
				{
					"fieldname": "erpnext_lead",
					"fieldtype": "Link",
					"label": "ERPNext Lead",
					"options": "Lead",
					"insert_after": "lead_name",
					"read_only": 1,
					"no_copy": 1,
				}
			],
		},
		ignore_validate=True,
	)


def _is_syncing():
	return bool(getattr(frappe.flags, SYNC_FLAG, False))


def _set_syncing(value=True):
	setattr(frappe.flags, SYNC_FLAG, value)


def _map_status_to_crm(status):
	if not status:
		return "New"
	if frappe.db.exists("CRM Lead Status", status):
		return status
	return ERP_TO_CRM_STATUS.get(status, "New")


def _map_status_to_erp(status):
	if not status:
		return "Lead"
	return CRM_TO_ERP_STATUS.get(status, "Lead")


def _normalize_source(source, target_doctype):
	if not source:
		return None
	source_doctype = "CRM Lead Source" if target_doctype == "CRM Lead" else "Lead Source"
	return source if frappe.db.exists(source_doctype, source) else None


def _sanitize_link_fields(data, doctype):
	meta = frappe.get_meta(doctype)
	for field in meta.fields:
		if field.fieldtype != "Link" or not data.get(field.fieldname):
			continue
		if not frappe.db.exists(field.options, data[field.fieldname]):
			data.pop(field.fieldname, None)
	return data


def _lead_data_from_erpnext(doc):
	data = {field: doc.get(field) for field in SHARED_FIELDS if doc.get(field) is not None}
	data["email"] = doc.get("email_id")
	data["organization"] = doc.get("company_name")
	data["status"] = _map_status_to_crm(doc.get("status"))
	data["source"] = _normalize_source(doc.get("source"), "CRM Lead")
	data["erpnext_lead"] = doc.name
	return _sanitize_link_fields(
		{key: value for key, value in data.items() if value not in ("", None)},
		"CRM Lead",
	)


def _lead_data_from_crm(doc):
	data = {field: doc.get(field) for field in SHARED_FIELDS if doc.get(field) is not None}
	data["email_id"] = doc.get("email")
	data["company_name"] = doc.get("organization")
	data["status"] = _map_status_to_erp(doc.get("status"))
	data["source"] = _normalize_source(doc.get("source"), "Lead")
	data["crm_lead"] = doc.name
	return _sanitize_link_fields(
		{key: value for key, value in data.items() if value not in ("", None)},
		"Lead",
	)


def _find_crm_lead(doc):
	if doc.get("crm_lead") and frappe.db.exists("CRM Lead", doc.crm_lead):
		return doc.crm_lead

	for fieldname, value in (("name", doc.name), ("mobile_no", doc.mobile_no), ("email", doc.email_id)):
		if not value:
			continue
		crm_field = "name" if fieldname == "name" else fieldname if fieldname != "email_id" else "email"
		match = frappe.db.get_value("CRM Lead", {crm_field: value}, "name")
		if match:
			return match

	return None


def _find_erpnext_lead(doc):
	if doc.get("erpnext_lead") and frappe.db.exists("Lead", doc.erpnext_lead):
		return doc.erpnext_lead

	for fieldname, value in (("name", doc.name), ("mobile_no", doc.mobile_no), ("email_id", doc.email)):
		if not value:
			continue
		erp_field = "name" if fieldname == "name" else fieldname if fieldname != "email" else "email_id"
		match = frappe.db.get_value("Lead", {erp_field: value}, "name")
		if match:
			return match

	return None


def _update_link_fields(erpnext_lead, crm_lead):
	if frappe.db.get_value("Lead", erpnext_lead, "crm_lead") != crm_lead:
		frappe.db.set_value("Lead", erpnext_lead, "crm_lead", crm_lead, update_modified=False)
	if frappe.db.get_value("CRM Lead", crm_lead, "erpnext_lead") != erpnext_lead:
		frappe.db.set_value("CRM Lead", crm_lead, "erpnext_lead", erpnext_lead, update_modified=False)


def _apply_updates(doctype, name, data):
	doc = frappe.get_doc(doctype, name)
	changed = False
	for field, value in data.items():
		if field in ("crm_lead", "erpnext_lead"):
			continue
		if doc.get(field) != value:
			doc.set(field, value)
			changed = True
	if changed:
		doc.flags.ignore_permissions = True
		doc.flags.ignore_mandatory = True
		doc.save()


def sync_erpnext_lead_to_crm(doc, method=None):
	if _is_syncing() or doc.doctype != "Lead":
		return

	_set_syncing(True)
	try:
		crm_lead = _find_crm_lead(doc)
		data = _lead_data_from_erpnext(doc)

		if crm_lead:
			_apply_updates("CRM Lead", crm_lead, data)
		else:
			crm_doc = frappe.new_doc("CRM Lead")
			crm_doc.update(data)
			if frappe.db.exists("CRM Lead", doc.name):
				crm_doc.name = None
			else:
				crm_doc.name = doc.name
			crm_doc.flags.ignore_permissions = True
			crm_doc.flags.ignore_mandatory = True
			crm_doc.insert()
			crm_lead = crm_doc.name

		_update_link_fields(doc.name, crm_lead)
	finally:
		_set_syncing(False)


def sync_crm_lead_to_erpnext(doc, method=None):
	if _is_syncing() or doc.doctype != "CRM Lead":
		return

	_set_syncing(True)
	try:
		erpnext_lead = _find_erpnext_lead(doc)
		data = _lead_data_from_crm(doc)

		if erpnext_lead:
			_apply_updates("Lead", erpnext_lead, data)
		else:
			erp_doc = frappe.new_doc("Lead")
			erp_doc.update(data)
			if frappe.db.exists("Lead", doc.name):
				erp_doc.name = None
			else:
				erp_doc.name = doc.name
			erp_doc.flags.ignore_permissions = True
			erp_doc.flags.ignore_mandatory = True
			erp_doc.insert()
			erpnext_lead = erp_doc.name

		_update_link_fields(erpnext_lead, doc.name)
	finally:
		_set_syncing(False)


@frappe.whitelist()
def sync_all_leads():
	frappe.only_for("System Manager")
	ensure_link_custom_fields()

	created = {"crm": 0, "erpnext": 0}
	for name in frappe.get_all("Lead", pluck="name"):
		before = frappe.db.count("CRM Lead")
		sync_erpnext_lead_to_crm(frappe.get_doc("Lead", name))
		if frappe.db.count("CRM Lead") > before:
			created["crm"] += 1

	for name in frappe.get_all("CRM Lead", pluck="name"):
		before = frappe.db.count("Lead")
		sync_crm_lead_to_erpnext(frappe.get_doc("CRM Lead", name))
		if frappe.db.count("Lead") > before:
			created["erpnext"] += 1

	return {
		"crm_leads": frappe.db.count("CRM Lead"),
		"erpnext_leads": frappe.db.count("Lead"),
		"created_crm_leads": created["crm"],
		"created_erpnext_leads": created["erpnext"],
	}
