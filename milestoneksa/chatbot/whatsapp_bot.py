"""Milestone WhatsApp chatbot logic."""

from __future__ import annotations

import json
import re

import frappe
from frappe import _
from frappe.integrations.utils import make_post_request
from frappe.utils import now_datetime

from frappe_whatsapp.utils import format_number, get_whatsapp_account

CHATBOT_FLAG = "milestoneksa_chatbot_processing"

PROJECT_LIST_INTRO = (
	"مرحبًا بك في Milestone 👋\n"
	"يسعدنا اهتمامك بمشاريعنا العقارية.\n\n"
	"اضغط على الزر أدناه لاختيار المشروع الذي ترغب بمعرفة تفاصيله،"
	" وسنرسل لك نبذة مختصرة وملف PDF يحتوي على معلومات المشروع."
)

LIST_BUTTON_TEXT = "عرض المشاريع"
LIST_HEADER = "مشاريع Milestone"
LIST_SECTION_TITLE = "اختر المشروع"

CONSULTANT_QUESTION = (
	"هل ترغب أن يتواصل معك أحد مستشارينا لمساعدتك في معرفة التفاصيل واختيار الأنسب لك؟"
)

LEAD_CONFIRMATION = (
	"شكرًا لك.\n"
	"تم تسجيل طلبك، وسيتواصل معك أحد مستشارينا قريبًا لمساعدتك والإجابة عن استفساراتك."
)

WAIT_FOR_TEAM_REPLY = (
	"شكرًا لتواصلك معنا.\n"
	"طلبك مسجل لدينا، وسيقوم أحد أعضاء فريق Milestone بالتواصل معك قريبًا. "
	"إذا رغبت بمعرفة المزيد عن المشاريع أو الخدمات، اكتب: المشاريع."
)

HUMAN_HANDOFF_STATES = {"human_handoff", "human_active"}

NO_CONTACT_REPLY = (
	"شكرًا لك.\n"
	"نتمنى أن تكون المعلومات مفيدة، ويمكنك التواصل معنا في أي وقت إذا رغبت بمعرفة المزيد عن مشاريع Milestone."
)

NO_PROJECTS_MESSAGE = (
	"نعتذر، لا توجد مشاريع متاحة للعرض حاليًا.\n"
	"يمكنك ترك رسالتك، وسيقوم فريقنا بالتواصل معك قريبًا."
)

INVALID_SELECTION_MESSAGE = (
	"عذرًا، لم نتمكن من معرفة اختيارك.\n"
	"يرجى الضغط على زر عرض المشاريع واختيار المشروع من القائمة."
)

TEMPLATE_NAME = "milestone_project_intro"
TEMPLATE_LANGUAGE = "ar"

PROJECT_ROW_IDS = {
	"project_al_nathym",
	"project_al_nassem",
	"project_dahrt_laban",
	"project_nimar",
}

SHOW_PROJECTS_PAYLOADS = {"show_projects", "عرض المشاريع", "اعرض المشاريع", "أعرض المشاريع"}
CONSULTANT_YES_PAYLOADS = {"consultant_yes", "نعم", "yes", "نعم، تواصلوا معي"}
CONSULTANT_NO_PAYLOADS = {"consultant_no", "لا", "no", "لا، شكرًا"}
PROJECT_SERVICE_KEYWORDS = {
	"project",
	"projects",
	"service",
	"services",
	"real estate",
	"مشروع",
	"مشاريع",
	"خدمة",
	"خدمات",
	"عقار",
	"عقارات",
	"تفاصيل",
	"pdf",
	"ملف",
}


TEXT_ONLY_TEMPLATE_NAMES = {"milestone_project_intro_text"}
INTRO_TEMPLATE_NAME = "milestone_project_intro"


def validate_chatbot_whatsapp_template(doc, method=None):
	"""Prevent Desk edits that Meta will reject for chatbot templates."""
	if doc.template_name in TEXT_ONLY_TEMPLATE_NAMES and doc.buttons:
		frappe.throw(
			_(
				"Template '{0}' is text-only and must not have buttons. "
				"The numbered project list is already in the message body. "
				"For a quick-reply button, use template '{1}' with one button: عرض المشاريع."
			).format(doc.template_name, INTRO_TEMPLATE_NAME),
			title=_("WhatsApp Chatbot Template"),
		)

	if doc.template_name == INTRO_TEMPLATE_NAME and doc.buttons and len(doc.buttons) > 1:
		frappe.throw(
			_(
				"Template '{0}' should have only one quick-reply button: عرض المشاريع. "
				"The chatbot sends the 4-project interactive list after the customer clicks it."
			).format(INTRO_TEMPLATE_NAME),
			title=_("WhatsApp Chatbot Template"),
		)


@frappe.whitelist()
def crm_is_whatsapp_enabled():
	"""CRM compatibility: this frappe_whatsapp version uses WhatsApp Account, not WhatsApp Settings."""
	if not frappe.db.exists("DocType", "WhatsApp Account"):
		return False

	return bool(
		frappe.db.exists(
			"WhatsApp Account",
			{
				"status": "Active",
				"is_default_outgoing": 1,
			},
		)
		or frappe.db.exists("WhatsApp Account", {"status": "Active"})
	)


@frappe.whitelist()
def crm_is_whatsapp_installed():
	"""CRM compatibility for frappe_whatsapp installations without WhatsApp Settings."""
	return bool(
		frappe.db.exists("DocType", "WhatsApp Account")
		and frappe.db.exists("DocType", "WhatsApp Message")
	)


def link_whatsapp_message_to_crm(doc, method=None):
	"""Attach WhatsApp Message to the matching CRM Lead so CRM history is visible."""
	if doc.doctype != "WhatsApp Message":
		return

	if doc.reference_doctype and doc.reference_name:
		if doc.type == "Outgoing" and not getattr(frappe.flags, CHATBOT_FLAG, False):
			phone = normalize_phone(doc.get("to"))
			_mark_human_handoff(phone, doc.reference_name)
		return

	phone = normalize_phone(doc.get("from") if doc.type == "Incoming" else doc.get("to"))
	if not phone:
		return

	lead = _resolve_crm_lead_for_phone(phone)
	if lead:
		doc.reference_doctype = "CRM Lead"
		doc.reference_name = lead

	if doc.type == "Outgoing" and not getattr(frappe.flags, CHATBOT_FLAG, False):
		_mark_human_handoff(phone, doc.reference_name)


def handle_whatsapp_message(doc, method=None):
	"""Entry point for incoming WhatsApp Message after_insert hook."""
	if getattr(frappe.flags, CHATBOT_FLAG, False):
		return

	if doc.doctype != "WhatsApp Message" or doc.type != "Incoming":
		return

	try:
		frappe.flags.milestoneksa_chatbot_processing = True
		_ensure_message_linked_to_crm(doc)
		_process_incoming_message(doc)
	except Exception:
		frappe.log_error(title="WhatsApp Chatbot Error")
	finally:
		frappe.flags.milestoneksa_chatbot_processing = False


def _process_incoming_message(doc):
	phone = normalize_phone(doc.get("from"))
	if not phone:
		return

	payload = _extract_incoming_payload(doc)
	session = get_or_create_session(phone, profile_name=doc.get("profile_name"))
	session.last_message_at = now_datetime()
	session.last_incoming_message = payload
	session.last_interactive_payload = payload
	session.save(ignore_permissions=True)

	# Consultant yes/no must be handled before crm_lead, closed, or handoff checks.
	# Otherwise an existing lead can cause the bot to ignore the user's acceptance.
	if session.state == "awaiting_consultant" and session.selected_project:
		if _is_consultant_yes(payload):
			_handle_consultant_yes(phone, session)
			return

		if _is_consultant_no(payload):
			_handle_consultant_no(phone, session)
			return

		send_consultant_question(phone)
		return

	# When sales owns the conversation, the bot stays quiet unless the customer
	# clearly asks to see projects again or selects a project.
	if session.state in HUMAN_HANDOFF_STATES:
		if _is_consultant_yes(payload):
			send_text(phone, LEAD_CONFIRMATION)
			return

		if payload in PROJECT_ROW_IDS or _is_fallback_project_number(payload):
			project = _resolve_project_from_payload(payload)
			if project:
				_handle_project_selection(phone, session, project, ask_consultant=True)
			return

		if payload in SHOW_PROJECTS_PAYLOADS or _is_project_or_service_request(payload):
			send_project_list(phone, session=session)
			return

		return

	# Closed sessions can be restarted when the customer asks for projects/services.
	if session.state == "closed":
		if payload in PROJECT_ROW_IDS or _is_fallback_project_number(payload):
			project = _resolve_project_from_payload(payload)
			if project:
				_handle_project_selection(phone, session, project, ask_consultant=True)
			return

		if payload in SHOW_PROJECTS_PAYLOADS or _is_project_or_service_request(payload):
			send_project_list(phone, session=session)
			return

		return

	if payload in PROJECT_ROW_IDS or _is_fallback_project_number(payload):
		project = _resolve_project_from_payload(payload)
		if project:
			_handle_project_selection(phone, session, project, ask_consultant=True)
			return

	if payload in SHOW_PROJECTS_PAYLOADS or _is_project_or_service_request(payload):
		send_project_list(phone, session=session)
		return

	if _is_consultant_yes(payload) and session.selected_project:
		_handle_consultant_yes(phone, session)
		return

	if _is_consultant_no(payload):
		_handle_consultant_no(phone, session)
		return

	if _is_greeting_or_text(doc, payload):
		send_project_list(phone, session=session)
		return

	send_text(phone, INVALID_SELECTION_MESSAGE)
	send_project_list(phone, session=session)

def _extract_incoming_payload(doc) -> str:
	message = (doc.get("message") or "").strip()
	content_type = doc.get("content_type")

	if content_type in ("button", "interactive"):
		return message

	if content_type == "text":
		return message

	return message


def _is_greeting_or_text(doc, payload: str) -> bool:
	if doc.get("content_type") == "text" and payload:
		return True
	return bool(payload)


def _is_project_or_service_request(payload: str) -> bool:
	normalized = payload.strip().lower()
	if not normalized:
		return False
	return any(keyword in normalized for keyword in PROJECT_SERVICE_KEYWORDS)


def _is_fallback_project_number(payload: str) -> bool:
	return payload.strip() in {"1", "2", "3", "4"}


def _resolve_project_from_payload(payload: str):
	projects = get_active_projects()
	if not projects:
		return None

	if payload in PROJECT_ROW_IDS:
		return frappe.db.get_value(
			"WhatsApp Chatbot Project",
			{"list_row_id": payload, "enabled": 1},
			["name", "project_name_ar", "project_name_en", "description_ar", "description_en", "pdf_file"],
			as_dict=True,
		)

	if payload.strip() in {"1", "2", "3", "4"}:
		index = int(payload.strip()) - 1
		if 0 <= index < len(projects):
			return projects[index]

	return None


def _handle_project_selection(phone: str, session, project: dict, ask_consultant: bool = True):
	session.selected_project = project.name
	session.state = "project_selected"
	session.save(ignore_permissions=True)

	display_name = f"{project.project_name_ar} / {project.project_name_en}"
	description = (project.description_ar or project.description_en or "").strip()

	if description:
		send_text(
			phone,
			f"شكرًا لاختيارك مشروع {display_name}.\n\n"
			f"إليك نبذة مختصرة عن المشروع:\n{description}\n\n"
			f"سنرسل لك الآن ملف PDF يحتوي على تفاصيل أكثر عن المشروع.",
		)
	else:
		send_text(
			phone,
			f"شكرًا لاختيارك مشروع {display_name}.\n\n"
			f"سنرسل لك الآن ملف PDF يحتوي على تفاصيل المشروع،"
			f" ويمكن لأحد مستشارينا مساعدتك في معرفة المزيد إذا رغبت بذلك.",
		)

	if project.pdf_file:
		send_document(
			phone,
			project.pdf_file,
			caption=f"تفاصيل مشروع {project.project_name_ar}",
		)
	else:
		send_text(
			phone,
			f"شكرًا لاختيارك مشروع {display_name}.\n"
			f"ملف التفاصيل غير متاح حاليًا، لكن يمكننا تسجيل طلبك ليتواصل معك أحد مستشارينا ويزودك بالمعلومات المطلوبة.",
		)

	if not ask_consultant:
		session.state = "closed"
		session.save(ignore_permissions=True)
		return

	session.state = "awaiting_consultant"
	session.save(ignore_permissions=True)
	send_consultant_question(phone)


def _handle_consultant_yes(phone: str, session):
	if not session.selected_project:
		send_project_list(phone, session=session)
		return

	project = frappe.get_doc("WhatsApp Chatbot Project", session.selected_project)
	display_name = f"{project.project_name_ar} / {project.project_name_en}"
	lead_name = create_or_update_lead(phone, display_name, profile_name=None)

	session.crm_lead = lead_name
	session.state = "human_handoff"
	session.save(ignore_permissions=True)
	send_text(phone, LEAD_CONFIRMATION)


def _handle_consultant_no(phone: str, session):
	session.state = "closed"
	session.save(ignore_permissions=True)
	send_text(phone, NO_CONTACT_REPLY)


def _is_consultant_yes(payload: str) -> bool:
	normalized = payload.strip().lower()
	return normalized in {p.lower() for p in CONSULTANT_YES_PAYLOADS}


def _is_consultant_no(payload: str) -> bool:
	normalized = payload.strip().lower()
	return normalized in {p.lower() for p in CONSULTANT_NO_PAYLOADS}


def normalize_phone(phone: str | None) -> str:
	if not phone:
		return ""
	phone = re.sub(r"[^\d+]", "", phone.strip())
	return format_number(phone)


def get_or_create_session(phone: str, profile_name: str | None = None, started_by: str = "Customer"):
	phone = normalize_phone(phone)
	if frappe.db.exists("WhatsApp Bot Session", phone):
		return frappe.get_doc("WhatsApp Bot Session", phone)

	session = frappe.get_doc(
		{
			"doctype": "WhatsApp Bot Session",
			"phone": phone,
			"started_by": started_by,
			"state": None,
			"last_message_at": now_datetime(),
		}
	)
	session.insert(ignore_permissions=True)
	return session


def _mark_human_handoff(phone: str | None, lead: str | None = None):
	"""Put the conversation in human-owned mode after a sales/team reply."""
	phone = normalize_phone(phone)
	if not phone:
		return

	session = get_or_create_session(phone)
	if lead and not session.crm_lead:
		session.crm_lead = lead
	session.state = "human_handoff"
	session.last_message_at = now_datetime()
	session.save(ignore_permissions=True)


def get_active_projects():
	return frappe.get_all(
		"WhatsApp Chatbot Project",
		filters={"enabled": 1},
		fields=[
			"name",
			"project_name_ar",
			"project_name_en",
			"description_ar",
			"description_en",
			"pdf_file",
			"list_row_id",
			"sort_order",
		],
		order_by="sort_order asc, project_name_ar asc",
	)


def send_project_list(phone: str, session=None):
	projects = get_active_projects()
	if not projects:
		send_text(phone, NO_PROJECTS_MESSAGE)
		return {"success": False, "reason": "no_active_projects"}

	if session:
		session.state = "menu_sent"
		session.save(ignore_permissions=True)

	if _send_interactive_project_list(phone, projects):
		return {"success": True, "mode": "interactive_list"}

	send_fallback_project_menu(phone)
	return {"success": True, "mode": "fallback_text"}


def send_fallback_project_menu(phone: str):
	projects = get_active_projects()
	if not projects:
		send_text(phone, NO_PROJECTS_MESSAGE)
		return

	lines = [PROJECT_LIST_INTRO, "", "يمكنك اختيار المشروع المناسب لك من القائمة التالية:", ""]
	for idx, project in enumerate(projects, start=1):
		lines.append(f"{idx} - {project.project_name_ar} / {project.project_name_en}")

	lines.append("")
	lines.append("أرسل رقم المشروع فقط.")
	send_text(phone, "\n".join(lines))


def _send_interactive_project_list(phone: str, projects: list[dict]) -> bool:
	rows = []
	for project in projects:
		rows.append(
			{
				"id": project.list_row_id,
				"title": f"{project.project_name_ar} / {project.project_name_en}"[:24],
				"description": f"تفاصيل مشروع {project.project_name_ar}"[:72],
			}
		)

	data = {
		"messaging_product": "whatsapp",
		"to": normalize_phone(phone),
		"type": "interactive",
		"interactive": {
			"type": "list",
			"header": {"type": "text", "text": LIST_HEADER},
			"body": {"text": PROJECT_LIST_INTRO},
			"action": {
				"button": LIST_BUTTON_TEXT,
				"sections": [
					{
						"title": LIST_SECTION_TITLE,
						"rows": rows[:10],
					}
				],
			},
		},
	}

	try:
		response = _post_to_meta(data)
		log_outgoing_message(
			phone=phone,
			message=PROJECT_LIST_INTRO,
			content_type="interactive",
			message_id=response.get("messages", [{}])[0].get("id"),
			buttons=json.dumps(rows, ensure_ascii=False),
			status="Success",
		)
		return True
	except Exception:
		frappe.log_error(title="WhatsApp Chatbot List Send Failed")
		return False


def send_text(phone: str, message: str):
	doc = frappe.get_doc(
		{
			"doctype": "WhatsApp Message",
			"type": "Outgoing",
			"to": normalize_phone(phone),
			"message": message,
			"content_type": "text",
			"message_type": "Manual",
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


def send_document(phone: str, pdf_file: str, caption: str = ""):
	doc = frappe.get_doc(
		{
			"doctype": "WhatsApp Message",
			"type": "Outgoing",
			"to": normalize_phone(phone),
			"message": caption,
			"content_type": "document",
			"message_type": "Manual",
			"attach": pdf_file,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


def send_consultant_question(phone: str):
	buttons = [
		{"id": "consultant_yes", "title": "نعم، تواصلوا معي"},
		{"id": "consultant_no", "title": "لا، شكرًا"},
	]

	doc = frappe.get_doc(
		{
			"doctype": "WhatsApp Message",
			"type": "Outgoing",
			"to": normalize_phone(phone),
			"message": CONSULTANT_QUESTION,
			"content_type": "interactive",
			"message_type": "Manual",
			"buttons": json.dumps(buttons, ensure_ascii=False),
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


def send_template_intro(phone: str, customer_name: str | None = None):
	customer_name = customer_name or "عميلنا الكريم"
	phone = normalize_phone(phone)

	data = {
		"messaging_product": "whatsapp",
		"to": phone,
		"type": "template",
		"template": {
			"name": TEMPLATE_NAME,
			"language": {"code": TEMPLATE_LANGUAGE},
			"components": [
				{
					"type": "body",
					"parameters": [{"type": "text", "text": customer_name}],
				},
				{
					"type": "button",
					"sub_type": "quick_reply",
					"index": "0",
					"parameters": [{"type": "payload", "payload": "show_projects"}],
				},
			],
		},
	}

	try:
		response = _post_to_meta(data)
		log_outgoing_message(
			phone=phone,
			message=json.dumps(data["template"], ensure_ascii=False),
			content_type="text",
			message_id=response.get("messages", [{}])[0].get("id"),
			message_type="Template",
			use_template=1,
			template=TEMPLATE_NAME,
			template_parameters=json.dumps([customer_name], ensure_ascii=False),
			status="Success",
		)
		return {"success": True, "message_id": response.get("messages", [{}])[0].get("id")}
	except Exception as exc:
		frappe.log_error(title="WhatsApp Chatbot Template Send Failed")
		return {"success": False, "error": str(exc)}


def log_outgoing_message(
	phone: str,
	message: str,
	content_type: str = "text",
	message_id: str | None = None,
	buttons: str | None = None,
	status: str | None = None,
	message_type: str = "Manual",
	use_template: int = 0,
	template: str | None = None,
	template_parameters: str | None = None,
):
	"""Persist an already-sent Meta message without re-triggering send hooks."""
	account = get_whatsapp_account(account_type="outgoing")
	lead = _resolve_crm_lead_for_phone(phone)
	doc = frappe.get_doc(
		{
			"doctype": "WhatsApp Message",
			"type": "Outgoing",
			"to": normalize_phone(phone),
			"message": message,
			"content_type": content_type,
			"message_type": message_type,
			"use_template": use_template,
			"template": template,
			"template_parameters": template_parameters,
			"buttons": buttons or "{}",
			"message_id": message_id,
			"status": status,
			"whatsapp_account": account.name if account else None,
			"reference_doctype": "CRM Lead" if lead else None,
			"reference_name": lead,
		}
	)
	doc.db_insert()
	return doc


def _post_to_meta(data: dict) -> dict:
	account = get_whatsapp_account(account_type="outgoing")
	if not account:
		frappe.throw(_("Please set a default outgoing WhatsApp Account"))

	token = account.get_password("token")
	headers = {
		"authorization": f"Bearer {token}",
		"content-type": "application/json",
	}

	response = make_post_request(
		f"{account.url}/{account.version}/{account.phone_id}/messages",
		headers=headers,
		data=json.dumps(data),
	)
	return response


def _ensure_whatsapp_lead_source():
	if not frappe.db.exists("DocType", "CRM Lead Source"):
		return None

	if frappe.db.exists("CRM Lead Source", "WhatsApp"):
		return "WhatsApp"

	doc = frappe.get_doc({"doctype": "CRM Lead Source", "source_name": "WhatsApp"})
	doc.insert(ignore_permissions=True)
	return "WhatsApp"


def _find_lead_by_phone(phone: str):
	phone = normalize_phone(phone)
	candidates = _phone_candidates(phone)

	if phone.startswith("966") and len(phone) > 3:
		local = phone[3:]
		if local.startswith("0"):
			local = local[1:]
		candidates.update({local, f"0{local}", f"+966{local}", f"966{local}"})

	for candidate in candidates:
		lead = frappe.db.get_value("CRM Lead", {"mobile_no": candidate}, "name")
		if lead:
			return lead

	return None


def _phone_candidates(phone: str | None) -> set[str]:
	phone = normalize_phone(phone)
	if not phone:
		return set()

	candidates = {phone, f"+{phone}"}
	if phone.startswith("00"):
		candidates.add(phone[2:])
		candidates.add(f"+{phone[2:]}")

	return candidates


def _resolve_crm_lead_for_phone(phone: str | None) -> str | None:
	phone = normalize_phone(phone)
	if not phone:
		return None

	session_lead = frappe.db.get_value("WhatsApp Bot Session", phone, "crm_lead")
	if session_lead:
		return session_lead

	lead = _find_lead_by_phone(phone)
	if lead:
		return lead

	candidates = _phone_candidates(phone)
	for fieldname in ("mobile_no", "phone"):
		for candidate in candidates:
			lead = frappe.db.get_value("CRM Lead", {fieldname: candidate}, "name")
			if lead:
				return lead

	# Last-resort normalized match for leads saved in a different phone format.
	for row in frappe.get_all("CRM Lead", fields=["name", "mobile_no", "phone"]):
		if normalize_phone(row.mobile_no) == phone or normalize_phone(row.phone) == phone:
			return row.name

	return None


def _ensure_message_linked_to_crm(doc) -> str | None:
	if doc.reference_doctype and doc.reference_name:
		return doc.reference_name

	phone = normalize_phone(doc.get("from") if doc.type == "Incoming" else doc.get("to"))
	lead = _resolve_crm_lead_for_phone(phone)
	if not lead:
		return None

	frappe.db.set_value(
		"WhatsApp Message",
		doc.name,
		{
			"reference_doctype": "CRM Lead",
			"reference_name": lead,
		},
		update_modified=False,
	)
	doc.reference_doctype = "CRM Lead"
	doc.reference_name = lead
	return lead


def create_or_update_lead(phone: str, selected_project: str, profile_name: str | None = None) -> str:
	phone = normalize_phone(phone)
	existing = _find_lead_by_phone(phone)
	source = _ensure_whatsapp_lead_source()

	if existing:
		lead = frappe.get_doc("CRM Lead", existing)
	else:
		status = frappe.db.get_value("CRM Lead Status", {"name": "New"}, "name") or "New"
		lead = frappe.get_doc(
			{
				"doctype": "CRM Lead",
				"first_name": profile_name or "WhatsApp Customer",
				"mobile_no": f"+{phone}" if not phone.startswith("+") else phone,
				"status": status,
			}
		)
		if source:
			lead.source = source
		lead.insert(ignore_permissions=True)

	_add_lead_comment(
		lead.name,
		f"Customer requested consultant contact from WhatsApp chatbot.\nSelected project: {selected_project}",
	)
	return lead.name


def _add_lead_comment(lead_name: str, content: str):
	frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": "Comment",
			"reference_doctype": "CRM Lead",
			"reference_name": lead_name,
			"content": content,
		}
	).insert(ignore_permissions=True)


def seed_chatbot_projects():
	"""Create the 4 chatbot project records. PDF files must be added manually in Desk."""
	seed_data = [
		{
			"enabled": 1,
			"project_name_ar": "النظيم",
			"project_name_en": "Al Nathym",
			"sort_order": 1,
			"list_row_id": "project_al_nathym",
			"description_ar": "مشروع عقاري في حي النظيم بالرياض.",
		},
		{
			"enabled": 1,
			"project_name_ar": "النسيم",
			"project_name_en": "Al Nassem",
			"sort_order": 2,
			"list_row_id": "project_al_nassem",
			"description_ar": "مشروع عقاري في حي النسيم بالرياض.",
		},
		{
			"enabled": 1,
			"project_name_ar": "مشروع لبن",
			"project_name_en": "Dahrt Laban",
			"sort_order": 3,
			"list_row_id": "project_dahrt_laban",
			"description_ar": "مشروع عقاري في ظهرة لبن بالرياض.",
		},
		{
			"enabled": 1,
			"project_name_ar": "القدية",
			"project_name_en": "Nimar",
			"sort_order": 4,
			"list_row_id": "project_nimar",
			"description_ar": "مشروع عقاري في نمار / القدية.",
		},
	]

	created = []
	for row in seed_data:
		if frappe.db.exists("WhatsApp Chatbot Project", row["list_row_id"]):
			continue

		doc = frappe.get_doc({"doctype": "WhatsApp Chatbot Project", **row})
		doc.flags.ignore_mandatory = True
		doc.insert(ignore_permissions=True)
		created.append(doc.name)

	return {"created": created, "message": "Attach PDF files manually in Desk for each project."}


def _get_default_whatsapp_account():
	return frappe.db.get_value(
		"WhatsApp Account",
		{"status": "Active", "is_default_outgoing": 1},
		"name",
	) or frappe.db.get_value("WhatsApp Account", {"status": "Active"}, "name")


def _create_whatsapp_template(template_def: dict) -> dict:
	"""Create a WhatsApp Templates record and push it to Meta via frappe_whatsapp."""
	template_name = template_def["template_name"]
	language_code = template_def.get("language_code", "ar")
	doc_name = f"{template_name}-{language_code}"

	if frappe.db.exists("WhatsApp Templates", doc_name):
		return {
			"template_name": template_name,
			"status": "skipped",
			"name": doc_name,
			"message": "Template already exists in Frappe.",
		}

	whatsapp_account = _get_default_whatsapp_account()
	if not whatsapp_account:
		return {
			"template_name": template_name,
			"status": "failed",
			"error": "No active WhatsApp Account found.",
		}

	doc = frappe.get_doc(
		{
			"doctype": "WhatsApp Templates",
			"template_name": template_name,
			"template": template_def["template"],
			"category": template_def["category"],
			"language": template_def.get("language", "ar"),
			"language_code": language_code,
			"sample_values": template_def.get("sample_values", ""),
			"whatsapp_account": whatsapp_account,
		}
	)

	for button in template_def.get("buttons", []):
		doc.append("buttons", button)

	try:
		doc.insert(ignore_permissions=True)
		return {
			"template_name": template_name,
			"status": "created",
			"name": doc.name,
			"meta_id": doc.id,
			"meta_status": doc.status,
			"message": "Template created in Frappe and submitted to Meta for approval.",
		}
	except Exception as exc:
		frappe.log_error(title=f"WhatsApp Template Seed Failed: {template_name}")
		return {
			"template_name": template_name,
			"status": "failed",
			"error": str(exc),
			"message": (
				"Could not push template to Meta. Create it manually in Meta WhatsApp Manager, "
				"then use WhatsApp Templates → Sync from Meta in Frappe."
			),
		}


def seed_chatbot_templates():
	"""Create WhatsApp marketing templates for company-started conversations."""
	templates = [
		{
			"template_name": "milestone_project_intro",
			"category": "MARKETING",
			"language": "ar",
			"language_code": "ar",
			"sample_values": "عميلنا الكريم",
			"template": (
				"مرحبًا {{1}}، يسعدنا تواصلك مع Milestone.\n\n"
				"لدينا عدة مشاريع عقارية قد تناسب اهتمامك.\n"
				"اضغط على الزر أدناه لاستعراض المشاريع المتاحة ومعرفة التفاصيل."
			),
			"buttons": [
				{
					"button_type": "Quick Reply",
					"button_label": "عرض المشاريع",
					"sequence": 1,
				}
			],
		},
		{
			"template_name": "milestone_project_intro_text",
			"category": "MARKETING",
			"language": "ar",
			"language_code": "ar",
			"sample_values": "عميلنا الكريم",
			"template": (
				"مرحبًا {{1}}، يسعدنا تواصلك مع Milestone.\n\n"
				"لدينا عدة مشاريع عقارية قد تناسب اهتمامك.\n"
				"يمكنك اختيار المشروع المناسب لك من القائمة التالية:\n\n"
				"1 - النظيم / Al Nathym\n"
				"2 - النسيم / Al Nassem\n"
				"3 - مشروع لبن / Dahrt Laban\n"
				"4 - القدية / Nimar\n\n"
				"أرسل رقم المشروع فقط."
			),
		},
	]

	results = []
	for template_def in templates:
		results.append(_create_whatsapp_template(template_def))

	return {
		"results": results,
		"message": (
			"Templates are submitted to Meta for approval. "
			"Until approved, company-started messages will fail. "
			"Use milestone_project_intro_text if quick-reply buttons are not supported."
		),
	}


@frappe.whitelist()
def test_send_customer_started_menu(phone: str):
	phone = normalize_phone(phone)
	try:
		session = get_or_create_session(phone, started_by="Customer")
		session.state = "menu_sent"
		session.started_by = "Customer"
		session.save(ignore_permissions=True)
		result = send_project_list(phone, session=session)
		return {"success": True, "phone": phone, "result": result}
	except Exception as exc:
		frappe.log_error(title="WhatsApp Chatbot Test Menu Failed")
		return {"success": False, "phone": phone, "error": str(exc)}


@frappe.whitelist()
def test_send_company_started_template(phone: str, customer_name: str | None = None):
	phone = normalize_phone(phone)
	try:
		session = get_or_create_session(phone, started_by="Company")
		session.state = "template_sent"
		session.started_by = "Company"
		session.template_sent = 1
		session.save(ignore_permissions=True)

		result = send_template_intro(phone, customer_name=customer_name)
		result.update({"phone": phone, "session": session.name})
		return result
	except Exception as exc:
		frappe.log_error(title="WhatsApp Chatbot Test Template Failed")
		return {"success": False, "phone": phone, "error": str(exc)}


@frappe.whitelist()
def test_send_project_list(phone: str):
	phone = normalize_phone(phone)
	try:
		result = send_project_list(phone)
		return {"success": True, "phone": phone, "result": result}
	except Exception as exc:
		frappe.log_error(title="WhatsApp Chatbot Test Project List Failed")
		return {"success": False, "phone": phone, "error": str(exc)}


@frappe.whitelist()
def test_create_or_update_lead(phone: str, selected_project: str):
	phone = normalize_phone(phone)
	lead_name = create_or_update_lead(phone, selected_project)
	return {"success": True, "crm_lead": lead_name, "phone": phone}


@frappe.whitelist()
def test_seed_chatbot_projects():
	return seed_chatbot_projects()


@frappe.whitelist()
def test_seed_chatbot_templates():
	return seed_chatbot_templates()


@frappe.whitelist()
def backfill_whatsapp_messages_for_lead(phone: str, lead: str | None = None):
	"""Link existing WhatsApp messages for a phone to a CRM Lead."""
	phone = normalize_phone(phone)
	lead = lead or _resolve_crm_lead_for_phone(phone)
	if not lead:
		frappe.throw(_("No CRM Lead found for phone {0}").format(phone))

	candidates = list(_phone_candidates(phone))
	updated = 0
	messages = frappe.get_all(
		"WhatsApp Message",
		filters=[
			["reference_name", "is", "not set"],
			["name", "is", "set"],
		],
		fields=["name", "to", "from"],
	)

	for message in messages:
		to_phone = normalize_phone(message.to)
		from_phone = normalize_phone(message.get("from"))
		if to_phone not in candidates and from_phone not in candidates:
			continue

		frappe.db.set_value(
			"WhatsApp Message",
			message.name,
			{
				"reference_doctype": "CRM Lead",
				"reference_name": lead,
			},
			update_modified=False,
		)
		updated += 1

	if frappe.db.exists("WhatsApp Bot Session", phone):
		frappe.db.set_value(
			"WhatsApp Bot Session",
			phone,
			"crm_lead",
			lead,
			update_modified=False,
		)

	return {"phone": phone, "crm_lead": lead, "updated": updated}

