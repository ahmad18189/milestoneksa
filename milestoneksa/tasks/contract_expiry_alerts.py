# -*- coding: utf-8 -*-
# Copyright (c) 2026, ahmed and contributors

"""Contract expiry alert emails and scheduled job."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_days, add_years, formatdate, get_url, getdate, now_datetime, today, validate_email_address
from frappe.utils.user import get_users_with_role

from milestoneksa.milestoneksa.doctype.employee_contract_end_review.employee_contract_end_review import (
	create_pending_review,
	get_contract_action_links,
	get_existing_review,
	get_or_create_review,
)

DEFAULT_TEST_EMAIL = "ahmed@milestoneksa.com"
DEFAULT_TEST_EMPLOYEE = "HR-EMP-00004"

LABELS = {
	"title": "تنبيه انتهاء العقود / Contract Expiry Alert",
	"alert_date": "تاريخ التنبيه",
	"summary": "ملخص",
	"employee_label": "موظف/موظفين",
	"expiring_in": "العقود تنتهي خلال",
	"days": "يوماً",
	"employee": "الموظف",
	"department": "القسم",
	"designation": "المسمى الوظيفي",
	"contract_end": "نهاية العقد",
	"days_left": "الأيام المتبقية",
	"actions": "الإجراءات",
	"extend_btn": "تمديد العقد",
	"end_btn": "إنهاء العقد",
	"view_all": "عرض جميع التنبيهات المعلقة",
	"footer": "هذا البريد مرسل تلقائياً من نظام الموارد البشرية.",
	"no_records": "—",
	"reminder_title": "تذكير / Reminder",
	"reminder_body": "لا يزال إجراء مراجعة انتهاء العقد معلقاً. يرجى اختيار تمديد العقد أو إنهائه.",
	"auto_renew_notice_title": "أيام التنبيه بالتجديد التلقائي بعد إنشاء المراجعة",
	"auto_renew_notice_body": "إذا لم يُتخذ إجراء خلال {0} يوماً من إنشاء مراجعة انتهاء العقد، سيُجدَّد عقد الموظف تلقائياً لسنة واحدة ما لم يتم اختيار إنهاء العقد.",
}

AUTO_RENEW_LABELS = {
	"title": "تنبيه التجديد التلقائي للعقد / Contract Auto-Renewal Notice",
	"alert_date": "تاريخ التنبيه",
	"notice_title": "تنبيه: سيتم تجديد العقد تلقائياً لسنة أخرى",
	"notice_body": "لم يُتخذ أي إجراء على مراجعة انتهاء العقد منذ إنشائها. وفقاً لسياسة الشركة، سيتم تجديد عقد الموظف لسنة إضافية ما لم يتم اختيار إنهاء العقد.",
	"employee": "الموظف",
	"department": "القسم",
	"contract_end": "نهاية العقد الحالية",
	"days_left": "الأيام المتبقية",
	"review_created": "تاريخ إنشاء المراجعة",
	"new_contract_end": "نهاية العقد بعد التجديد (سنة واحدة)",
	"extend_btn": "تمديد العقد الآن",
	"end_btn": "إنهاء العقد",
	"view_review": "عرض مراجعة انتهاء العقد",
	"footer": "هذا البريد مرسل تلقائياً من نظام الموارد البشرية.",
	"no_records": "—",
}

STATUS_LABELS = {
	"title": "تحديث حالة مراجعة انتهاء العقد / Contract Review Status Update",
	"alert_date": "تاريخ التحديث",
	"employee": "الموظف",
	"department": "القسم",
	"previous_status": "الحالة السابقة",
	"new_status": "الحالة الجديدة",
	"new_contract_end": "نهاية العقد الجديدة",
	"final_eos": "مكافأة نهاية الخدمة النهائية",
	"acted_by": "تم بواسطة",
	"view_review": "عرض مراجعة انتهاء العقد",
	"footer": "هذا البريد مرسل تلقائياً من نظام الموارد البشرية.",
	"no_records": "—",
}


def _settings():
	return frappe.get_single("HR Settings")


def _alerts_enabled() -> bool:
	return bool(getattr(_settings(), "mksa_enable_contract_expiry_alerts", 1))


def _days_before() -> int:
	return int(getattr(_settings(), "mksa_contract_alert_days_before", 60) or 60)


def _auto_renew_notice_days() -> int:
	return int(getattr(_settings(), "mksa_contract_auto_renew_notice_days", 10) or 10)


def _get_recipient_roles() -> list[str]:
	rows = getattr(_settings(), "mksa_contract_alert_roles", None) or []
	roles = [row.role for row in rows if row.role]
	return roles or ["COO", "CEO"]


def _get_production_recipients() -> list[tuple[str, str]]:
	"""Return (user_id, email) for configured alert roles."""
	seen_emails: set[str] = set()
	out: list[tuple[str, str]] = []
	for role in _get_recipient_roles():
		for user in get_users_with_role(role):
			if frappe.db.get_value("User", user, "enabled") == 0:
				continue
			email = frappe.db.get_value("User", user, "email")
			if not email or email in seen_emails:
				continue
			seen_emails.add(email)
			out.append((user, email))
	return out


def _user_for_email(email: str) -> str:
	user = frappe.db.get_value("User", {"email": email}, "name")
	if user and frappe.db.get_value("User", user, "enabled"):
		return user
	return frappe.db.get_value("User", {"name": "Administrator"}, "name") or "Administrator"


def _resolve_employee(employee: str | None) -> str:
	if employee:
		if frappe.db.exists("Employee", employee):
			return employee
		match = frappe.db.get_value(
			"Employee",
			{"employee_name": ["like", f"%{employee}%"]},
			"name",
		)
		if match:
			return match
		frappe.throw(_("Employee not found: {0}").format(employee))
	return DEFAULT_TEST_EMPLOYEE


def _review_link(review_name: str) -> str:
	return f"{get_url()}/app/employee-contract-end-review/{review_name}"


def _list_link() -> str:
	return f"{get_url()}/app/employee-contract-end-review?status=Pending+Review"


def _build_employee_row(review, user: str) -> dict:
	designation = review.designation
	if designation and frappe.db.exists("Designation", designation):
		designation = frappe.db.get_value("Designation", designation, "designation_name") or designation

	links = get_contract_action_links(review, user)
	return {
		"employee_name": review.employee_name,
		"department": review.department,
		"designation": designation,
		"contract_end_date": formatdate(review.contract_end_date),
		"days_to_expiry": review.days_to_expiry,
		"review_name": review.name,
		**links,
	}


def build_email_args(reviews, user: str, days_before: int | None = None, is_reminder: bool = False) -> dict:
	days_before = days_before or _days_before()
	auto_renew_notice_days = _auto_renew_notice_days()
	employees = [_build_employee_row(r, user) for r in reviews]
	return {
		"labels": LABELS,
		"alert_date": formatdate(today()),
		"days_before": days_before,
		"auto_renew_notice_days": auto_renew_notice_days,
		"auto_renew_notice_body": LABELS["auto_renew_notice_body"].format(auto_renew_notice_days),
		"count": len(employees),
		"employees": employees,
		"list_link": _list_link(),
		"is_reminder": is_reminder,
	}


def build_auto_renew_notice_args(review, user: str) -> dict:
	links = get_contract_action_links(review, user)
	new_end = add_years(getdate(review.contract_end_date), 1)
	return {
		"labels": AUTO_RENEW_LABELS,
		"alert_date": formatdate(today()),
		"employee_name": review.employee_name,
		"department": review.department,
		"contract_end_date": formatdate(review.contract_end_date),
		"days_to_expiry": review.days_to_expiry,
		"review_created_on": formatdate(review.creation),
		"new_contract_end_date": formatdate(new_end),
		"review_link": links["review_link"],
		"extend_link": links["extend_link"],
		"end_link": links["end_link"],
	}


def build_status_change_args(review, previous_status: str) -> dict:
	acted_by = review.extended_by or review.ended_by
	if acted_by:
		acted_by = frappe.db.get_value("User", acted_by, "full_name") or acted_by

	status_messages = {
		"Extended": _(
			"Contract for {0} has been extended to {1}."
		).format(review.employee_name, formatdate(review.new_contract_end_date)),
		"End Contract": _(
			"Contract for {0} has been ended. Final EOS: {1} SAR."
		).format(review.employee_name, review.final_eos_amount or 0),
		"Cancelled": _("Contract end review for {0} has been cancelled.").format(review.employee_name),
	}

	return {
		"labels": STATUS_LABELS,
		"alert_date": formatdate(today()),
		"employee_name": review.employee_name,
		"department": review.department,
		"previous_status": previous_status,
		"new_status": review.status,
		"status_label": _("Status changed: {0} → {1}").format(previous_status, review.status),
		"status_message": status_messages.get(review.status, ""),
		"new_contract_end_date": formatdate(review.new_contract_end_date) if review.new_contract_end_date else None,
		"final_eos_amount": review.final_eos_amount,
		"acted_by": acted_by,
		"review_link": _review_link(review.name),
	}


def _send_template_email(
	recipients: list[tuple[str, str]],
	subject: str,
	template: str,
	build_args,
	*,
	header_color: str = "blue",
	cc: list[str] | None = None,
) -> int:
	sent = 0
	for user, email in recipients:
		try:
			args = build_args(user) if callable(build_args) else build_args
			frappe.sendmail(
				recipients=[email],
				cc=cc,
				subject=subject,
				template=template,
				args=args,
				header=[args.get("labels", LABELS).get("title", subject), header_color],
			)
			sent += 1
		except Exception:
			frappe.log_error(title=f"Contract alert email failed ({template})", message=frappe.get_traceback())
	return sent


def _send_reminder_emails(
	recipients: list[tuple[str, str]],
	reviews,
	days_before: int,
	is_reminder: bool,
	cc: list[str] | None = None,
) -> int:
	if not reviews:
		return 0

	def build_args(user: str):
		return build_email_args(reviews, user, days_before, is_reminder=is_reminder)

	subject_key = "Contract Expiry Reminder" if is_reminder else "Contract Expiry Alert"
	subject = _("{0} — {1} employee(s)").format(_(subject_key), len(reviews))
	return _send_template_email(recipients, subject, "contract_expiry_alert", build_args, cc=cc)


def _mark_reminders_sent(review_names: list[str]):
	now = now_datetime()
	for name in review_names:
		frappe.db.set_value(
			"Employee Contract End Review",
			name,
			{
				"notification_sent": 1,
				"notification_sent_on": now,
				"last_reminder_sent_on": now,
			},
			update_modified=False,
		)


def _find_employees_due_for_alert(days_before: int) -> list[dict]:
	"""
	Active employees in the alert window: contract end is today or later,
	and days remaining <= days_before (includes passed alert dates with no review yet).
	"""
	return frappe.db.sql(
		"""
		SELECT name, employee_name, contract_end_date, date_of_joining,
			DATEDIFF(contract_end_date, %(today)s) AS days_to_expiry
		FROM `tabEmployee`
		WHERE status = 'Active'
			AND contract_end_date IS NOT NULL
			AND contract_end_date >= %(today)s
			AND DATEDIFF(contract_end_date, %(today)s) <= %(days_before)s
		ORDER BY contract_end_date ASC
		""",
		{"today": today(), "days_before": days_before},
		as_dict=True,
	)


def sync_pending_reviews_for_due_contracts(days_before: int | None = None) -> dict:
	"""
	For each active employee within the alert window (days_left <= days_before):
	- If any Employee Contract End Review already exists for that cycle → skip (reuse existing)
	- If the employee already has a pending review → skip (email actions stay on that document)
	- Otherwise → create a new Pending Review (including missed/passed alert dates)
	"""
	days_before = days_before or _days_before()
	employees = _find_employees_due_for_alert(days_before)

	created: list[str] = []
	skipped: list[dict] = []

	for emp in employees:
		existing = get_existing_review(emp.name, emp.contract_end_date)
		if existing:
			review = frappe.get_doc("Employee Contract End Review", existing)
			skipped.append(
				{
					"employee": emp.name,
					"employee_name": emp.employee_name,
					"contract_end_date": str(emp.contract_end_date),
					"review": existing,
					"review_status": review.status,
				}
			)
			continue

		doc = create_pending_review(emp.name, emp.contract_end_date)
		created.append(doc.name)

	return {
		"days_before": days_before,
		"window": f"0 to {days_before} days before contract end",
		"checked": len(employees),
		"created": created,
		"skipped": skipped,
		"employees_in_window": [
			{
				"employee": e.name,
				"employee_name": e.employee_name,
				"contract_end_date": str(e.contract_end_date),
				"days_to_expiry": e.days_to_expiry,
			}
			for e in employees
		],
	}


def _get_all_pending_reviews() -> list[str]:
	return frappe.get_all(
		"Employee Contract End Review",
		filters={"status": "Pending Review"},
		fields=["name"],
		order_by="contract_end_date asc",
		pluck="name",
	)


def _get_pending_reviews_due_auto_renew_notice(notice_days: int) -> list[str]:
	cutoff = add_days(today(), -notice_days)
	return frappe.db.sql(
		"""
		SELECT name
		FROM `tabEmployee Contract End Review`
		WHERE status = 'Pending Review'
			AND IFNULL(auto_renew_notice_sent, 0) = 0
			AND DATE(creation) <= %(cutoff)s
		ORDER BY creation ASC
		""",
		{"cutoff": cutoff},
		pluck=True,
	)


def _send_auto_renew_notice_emails(recipients: list[tuple[str, str]], reviews) -> int:
	sent_reviews = 0
	for review in reviews:
		def build_args(user: str, current_review=review):
			return build_auto_renew_notice_args(current_review, user)

		subject = _("Contract Auto-Renewal Notice — {0}").format(review.employee_name)
		sent = _send_template_email(
			recipients,
			subject,
			"contract_expiry_auto_renew_notice",
			build_args,
			header_color="orange",
		)
		if sent:
			sent_reviews += 1
			frappe.db.set_value(
				"Employee Contract End Review",
				review.name,
				{
					"auto_renew_notice_sent": 1,
					"auto_renew_notice_sent_on": now_datetime(),
				},
				update_modified=False,
			)
	return sent_reviews


def send_status_change_notification(review, previous_status: str):
	"""Email configured roles when a review status changes."""
	if not _alerts_enabled():
		return

	if isinstance(review, str):
		review = frappe.get_doc("Employee Contract End Review", review)

	recipients = _get_production_recipients()
	if not recipients:
		return

	args = build_status_change_args(review, previous_status)
	subject = _("Contract Review Status Update — {0} ({1})").format(
		review.employee_name,
		review.status,
	)
	_send_template_email(
		recipients,
		subject,
		"contract_expiry_status_changed",
		args,
		header_color="green",
	)


def on_contract_review_update(doc, method=None):
	"""Doc event: notify roles when review status changes."""
	if doc.is_new() or frappe.flags.in_contract_review_status_email:
		return

	before = doc.get_doc_before_save()
	if not before or before.status == doc.status:
		return

	frappe.flags.in_contract_review_status_email = True
	try:
		send_status_change_notification(doc, before.status)
	finally:
		frappe.flags.in_contract_review_status_email = False


def run_contract_expiry_alerts(cc: list[str] | str | None = None):
	"""Production scheduler: sync reviews, resend pending reminders, auto-renew notices."""
	if not _alerts_enabled():
		return

	if isinstance(cc, str):
		cc = [cc]

	days_before = _days_before()
	notice_days = _auto_renew_notice_days()
	sync_pending_reviews_for_due_contracts(days_before)

	recipients = _get_production_recipients()
	if not recipients:
		frappe.log_error(
			title="Contract expiry alert: no recipients",
			message="No enabled users with configured alert roles and email addresses.",
		)
		return

	pending_names = _get_all_pending_reviews()
	if pending_names:
		reviews = [frappe.get_doc("Employee Contract End Review", name) for name in pending_names]
		is_reminder = any(review.notification_sent for review in reviews)
		sent = _send_reminder_emails(recipients, reviews, days_before, is_reminder=is_reminder, cc=cc)
		if sent:
			_mark_reminders_sent(pending_names)

	auto_renew_names = _get_pending_reviews_due_auto_renew_notice(notice_days)
	if auto_renew_names:
		auto_renew_reviews = [
			frappe.get_doc("Employee Contract End Review", name) for name in auto_renew_names
		]
		_send_auto_renew_notice_emails(recipients, auto_renew_reviews)

	frappe.db.commit()


def send_contract_expiry_alerts_now(
	days_before: int | None = None,
	cc: str | None = None,
	roles: list[str] | str | None = None,
) -> dict:
	"""
	Bench execute: set days_before (optional), sync, and send production alert emails.
	cc: optional copy recipient, e.g. ahmed@milestoneksa.com
	roles: optional list of roles, e.g. ["CEO", "CFO"]
	"""
	if not _alerts_enabled():
		return {"enabled": False}

	settings = _settings()
	if days_before is not None:
		settings.mksa_contract_alert_days_before = int(days_before)

	if roles:
		if isinstance(roles, str):
			import json
			roles = json.loads(roles) if roles.strip().startswith("[") else [r.strip() for r in roles.split(",")]
		settings.mksa_contract_alert_roles = []
		for role in roles:
			settings.append("mksa_contract_alert_roles", {"role": role})

	if days_before is not None or roles:
		settings.save(ignore_permissions=True)
		frappe.db.commit()

	cc_list = [cc.strip()] if cc else None
	run_contract_expiry_alerts(cc=cc_list)

	pending = _get_all_pending_reviews()
	return {
		"days_before": _days_before(),
		"roles": [row.role for row in (settings.mksa_contract_alert_roles or [])],
		"cc": cc_list,
		"pending_reviews": pending,
		"recipients": [email for _user, email in _get_production_recipients()],
	}


def backfill_reviews_for_employees(employees: list[str] | str | None = None) -> dict:
	"""
	Bench execute: create missing Pending Reviews for specific active employees.
	Skips if an Employee Contract End Review already exists for the employee/contract cycle.
	"""
	if isinstance(employees, str):
		import json
		employees = json.loads(employees)

	if not employees:
		frappe.throw(_("Provide employees list, e.g. ['HR-EMP-00005', 'HR-EMP-00011']"))

	created: list[str] = []
	skipped: list[dict] = []
	errors: list[dict] = []

	for employee_id in employees:
		if not frappe.db.exists("Employee", employee_id):
			errors.append({"employee": employee_id, "error": "Employee not found"})
			continue

		emp = frappe.get_doc("Employee", employee_id)
		if emp.status != "Active":
			errors.append(
				{"employee": employee_id, "employee_name": emp.employee_name, "error": f"Status is {emp.status}"}
			)
			continue

		if not emp.contract_end_date:
			errors.append(
				{"employee": employee_id, "employee_name": emp.employee_name, "error": "No contract end date"}
			)
			continue

		existing = get_existing_review(employee_id, emp.contract_end_date)
		if existing:
			review = frappe.get_doc("Employee Contract End Review", existing)
			skipped.append(
				{
					"employee": employee_id,
					"employee_name": emp.employee_name,
					"contract_end_date": str(emp.contract_end_date),
					"review": existing,
					"review_status": review.status,
				}
			)
			continue

		doc = create_pending_review(employee_id, emp.contract_end_date)
		created.append(doc.name)

	frappe.db.commit()
	return {
		"days_before_setting": _days_before(),
		"created": created,
		"skipped": skipped,
		"errors": errors,
	}


def run_sync_pending_reviews_only(days_before: int | None = None):
	"""Bench execute: only create missing pending reviews (no email)."""
	if not _alerts_enabled():
		return {"enabled": False}

	result = sync_pending_reviews_for_due_contracts(days_before)
	frappe.db.commit()
	return result


def test_contract_expiry_alert_for_employee(employee: str | None = None):
	"""
	Bench execute test: create review for employee and email ahmed@milestoneksa.com only.
	Never sends to COO/CEO. Does not mark notification_sent.
	"""
	employee_id = _resolve_employee(employee)
	review = get_or_create_review(employee_id)
	review.reload()

	test_email = DEFAULT_TEST_EMAIL
	settings_email = getattr(_settings(), "mksa_contract_alert_test_email", None)
	if settings_email:
		test_email = settings_email.strip()

	validate_email_address(test_email, throw=True)

	test_user = _user_for_email(test_email)
	args = build_email_args([review], test_user)
	subject = _("(Test) Contract Expiry Alert — {0}").format(review.employee_name)
	sent = 0
	try:
		frappe.sendmail(
			recipients=[test_email],
			subject=subject,
			template="contract_expiry_alert",
			args=args,
			header=[LABELS["title"], "blue"],
		)
		sent = 1
	except Exception:
		frappe.log_error(title="Contract expiry test email failed", message=frappe.get_traceback())

	return {
		"employee": employee_id,
		"employee_name": review.employee_name,
		"review_name": review.name,
		"recipient": test_email,
		"sent": sent,
		"contract_end_date": str(review.contract_end_date),
		"days_to_expiry": review.days_to_expiry,
	}


@frappe.whitelist()
def send_test_contract_expiry_email():
	"""HR Settings test button — sends only to mksa_contract_alert_test_email."""
	frappe.only_for(("HR Manager", "System Manager"))
	result = test_contract_expiry_alert_for_employee()
	return {
		"sent": result["sent"],
		"message": _("تم إرسال بريد الاختبار إلى {0}").format(result["recipient"]),
	}
