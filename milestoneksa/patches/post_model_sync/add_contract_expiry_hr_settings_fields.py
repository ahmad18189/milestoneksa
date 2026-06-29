import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"HR Settings": [
				{
					"fieldname": "mksa_contract_alert_sb",
					"label": "تنبيهات انتهاء العقود",
					"fieldtype": "Section Break",
					"insert_after": "mksa_checkout_report_last_sent",
					"collapsible": 1,
				},
				{
					"fieldname": "mksa_enable_contract_expiry_alerts",
					"label": "تفعيل تنبيهات انتهاء العقود",
					"fieldtype": "Check",
					"default": "1",
					"insert_after": "mksa_contract_alert_sb",
				},
				{
					"fieldname": "mksa_contract_alert_days_before",
					"label": "عدد الأيام قبل انتهاء العقد",
					"fieldtype": "Int",
					"default": "60",
					"insert_after": "mksa_enable_contract_expiry_alerts",
				},
				{
					"fieldname": "mksa_contract_alert_roles",
					"label": "أدوار المستلمين (الإنتاج)",
					"fieldtype": "Table",
					"options": "Attendance Email Report Role",
					"insert_after": "mksa_contract_alert_days_before",
				},
				{
					"fieldname": "mksa_contract_alert_test_cb",
					"label": "اختبار الإرسال",
					"fieldtype": "Column Break",
					"insert_after": "mksa_contract_alert_roles",
				},
				{
					"fieldname": "mksa_contract_alert_test_email",
					"label": "بريد الاختبار",
					"fieldtype": "Data",
					"options": "Email",
					"default": "ahmed@milestoneksa.com",
					"insert_after": "mksa_contract_alert_test_cb",
				},
				{
					"fieldname": "mksa_send_contract_alert_test_email",
					"label": "إرسال بريد اختبار انتهاء العقد",
					"fieldtype": "Button",
					"insert_after": "mksa_contract_alert_test_email",
				},
			]
		},
		ignore_validate=True,
	)

	settings = frappe.get_single("HR Settings")
	existing_roles = {row.role for row in (settings.mksa_contract_alert_roles or [])}
	for role in ("COO", "CEO"):
		if role not in existing_roles:
			settings.append("mksa_contract_alert_roles", {"role": role})
	settings.save(ignore_permissions=True)
	frappe.clear_cache(doctype="HR Settings")
