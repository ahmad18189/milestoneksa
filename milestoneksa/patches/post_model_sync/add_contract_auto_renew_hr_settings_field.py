import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"HR Settings": [
				{
					"fieldname": "mksa_contract_auto_renew_notice_days",
					"label": "أيام التنبيه بالتجديد التلقائي بعد إنشاء المراجعة",
					"fieldtype": "Int",
					"default": "10",
					"insert_after": "mksa_contract_alert_days_before",
					"description": "بعد هذه المدة من إنشاء مراجعة انتهاء العقد، يُرسل بريد إضافي بأن العقد سيُجدَّد لسنة أخرى إذا لم يُتخذ إجراء.",
				},
			]
		},
		ignore_validate=True,
	)
	frappe.clear_cache(doctype="HR Settings")

	settings = frappe.get_single("HR Settings")
	if not getattr(settings, "mksa_contract_auto_renew_notice_days", None):
		settings.mksa_contract_auto_renew_notice_days = 10
		settings.save(ignore_permissions=True)
		frappe.db.commit()
