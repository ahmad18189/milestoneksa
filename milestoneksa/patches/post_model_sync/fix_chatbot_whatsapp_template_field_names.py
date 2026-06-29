import frappe

from milestoneksa.chatbot.whatsapp_bot import (
	CHATBOT_TEMPLATE_FIELD_NAMES,
	CHATBOT_TEMPLATE_FOR_DOCTYPE,
	CHATBOT_TEMPLATE_NAMES,
)


def execute():
	for template_name in CHATBOT_TEMPLATE_NAMES:
		for doc_name in frappe.get_all(
			"WhatsApp Templates",
			filters={"template_name": template_name},
			pluck="name",
		):
			frappe.db.set_value(
				"WhatsApp Templates",
				doc_name,
				{
					"field_names": CHATBOT_TEMPLATE_FIELD_NAMES,
					"for_doctype": CHATBOT_TEMPLATE_FOR_DOCTYPE,
				},
				update_modified=False,
			)
