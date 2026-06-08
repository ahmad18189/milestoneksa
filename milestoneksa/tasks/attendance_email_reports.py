# Copyright (c) 2026, ahmed and contributors
# License: MIT

"""Daily Arabic attendance summary emails (check-in / check-out) for HR Settings roles."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace

import frappe
from frappe import _
from frappe.utils import (
	format_datetime,
	get_datetime,
	get_time,
	getdate,
	now_datetime,
	today,
	validate_email_address,
)
from frappe.utils.user import get_users_with_role

from hrms.hr.doctype.employee_checkin.employee_checkin import calculate_working_hours

REPORT_CHECKIN = "Check-in"
REPORT_CHECKOUT = "Check-out"
SEND_WINDOW_MINUTES = 5

AR_LABELS_CHECKIN = {
	"title": "تقرير تسجيل الدخول",
	"report_date": "تاريخ التقرير",
	"summary": "ملخص",
	"checked_in_title": "الموظفون الذين سجلوا الدخول",
	"not_checked_in_title": "الموظفون الذين لم يسجلوا الدخول",
	"employee": "الموظف",
	"department": "القسم",
	"checkin_time": "وقت الدخول",
	"count": "العدد",
	"no_records": "لا يوجد",
	"footer": "هذا البريد مرسل تلقائياً من نظام الموارد البشرية.",
}

AR_LABELS_CHECKOUT = {
	"title": "تقرير تسجيل الخروج",
	"report_date": "تاريخ التقرير",
	"summary": "ملخص",
	"checked_out_title": "الموظفون الذين سجلوا الخروج",
	"not_checked_out_title": "سجلوا الدخول ولم يسجلوا الخروج",
	"no_checkin_checkout_title": "لم يسجلوا دخولاً أو خروجاً",
	"employee": "الموظف",
	"department": "القسم",
	"checkout_time": "وقت الخروج",
	"total_hours": "إجمالي الساعات",
	"count": "العدد",
	"no_records": "لا يوجد",
	"footer": "هذا البريد مرسل تلقائياً من نظام الموارد البشرية.",
}


@dataclass
class EmployeeRow:
	name: str
	employee_name: str
	department: str | None
	default_shift: str | None
	user_id: str | None


def _settings():
	return frappe.get_single("HR Settings")


def _reports_enabled() -> bool:
	return bool(getattr(_settings(), "mksa_enable_attendance_email_reports", 1))


def _get_recipient_roles() -> list[str]:
	table = getattr(_settings(), "mksa_attendance_email_roles", None) or []
	return [row.role for row in table if row.role]


def _get_ignored_employee_roles() -> list[str]:
	table = getattr(_settings(), "mksa_attendance_ignored_roles", None) or []
	return [row.role for row in table if row.role]


def _get_users_with_ignored_roles() -> set[str]:
	ignored_users: set[str] = set()
	for role in _get_ignored_employee_roles():
		ignored_users.update(get_users_with_role(role))
	return ignored_users


def _get_recipients() -> list[tuple[str, str]]:
	roles = _get_recipient_roles()
	if not roles:
		return []
	seen: set[str] = set()
	out: list[tuple[str, str]] = []
	for role in roles:
		for user in get_users_with_role(role):
			if frappe.db.get_value("User", user, "enabled") == 0:
				continue
			email = frappe.db.get_value("User", user, "email")
			if not email or email in seen:
				continue
			seen.add(email)
			out.append((user, email))
	return out


def _get_active_employees() -> list[EmployeeRow]:
	rows = frappe.get_all(
		"Employee",
		filters={"status": "Active"},
		fields=["name", "employee_name", "department", "default_shift", "user_id"],
		order_by="employee_name asc",
	)
	ignored_users = _get_users_with_ignored_roles()
	return [EmployeeRow(**r) for r in rows if not r.user_id or r.user_id not in ignored_users]


def _report_date_str() -> str:
	return format_datetime(now_datetime(), "dd-MM-yyyy")


def _format_time(dt) -> str:
	if not dt:
		return ""
	return format_datetime(get_datetime(dt), "HH:mm")


def _today_checkins() -> list[dict]:
	report_day = today()
	return frappe.db.sql(
		"""
		SELECT name, employee, employee_name, log_type, time, shift
		FROM `tabEmployee Checkin`
		WHERE DATE(`time`) = %(report_day)s
		ORDER BY employee, `time`
		""",
		{"report_day": report_day},
		as_dict=True,
	)


def _today_attendance_map() -> dict[str, dict]:
	report_day = today()
	rows = frappe.get_all(
		"Attendance",
		filters={
			"attendance_date": report_day,
			"docstatus": 1,
		},
		fields=["employee", "working_hours", "in_time", "out_time", "shift"],
	)
	return {r.employee: r for r in rows}


def _group_checkins_by_employee(checkins: list[dict]) -> dict[str, list[dict]]:
	grouped: dict[str, list[dict]] = defaultdict(list)
	for row in checkins:
		grouped[row.employee].append(row)
	return grouped


def _get_shift_calc_settings(employee: str, default_shift: str | None, logs: list[dict]):
	shift = default_shift
	if not shift and logs:
		shift = logs[0].get("shift")
	if shift and frappe.db.exists("Shift Type", shift):
		st = frappe.get_cached_doc("Shift Type", shift)
		return (
			st.determine_check_in_and_check_out
			or "Alternating entries as IN and OUT during the same shift",
			st.working_hours_calculation_based_on or "First Check-in and Last Check-out",
		)
	return (
		"Alternating entries as IN and OUT during the same shift",
		"First Check-in and Last Check-out",
	)


def _logs_to_namespace(logs: list[dict]) -> list[SimpleNamespace]:
	return [SimpleNamespace(time=get_datetime(r["time"]), log_type=r.get("log_type")) for r in logs]


def _has_checkin_today(logs: list[dict]) -> bool:
	if not logs:
		return False
	if any((r.get("log_type") or "").upper() == "IN" for r in logs):
		return True
	return True  # any log counts as check-in presence


def _has_checkout_today(logs: list[dict], check_in_out_type: str) -> bool:
	if not logs:
		return False
	if any((r.get("log_type") or "").upper() == "OUT" for r in logs):
		return True
	if check_in_out_type == "Alternating entries as IN and OUT during the same shift":
		return len(logs) >= 2
	return False


def _first_checkin_time(logs: list[dict]):
	for row in logs:
		if (row.get("log_type") or "").upper() == "IN":
			return row.get("time")
	return logs[0].get("time") if logs else None


def _checkout_time_from_logs(logs: list[dict], check_in_out_type: str, working_hours_calc_type: str):
	ns_logs = _logs_to_namespace(logs)
	_, _in_time, out_time = calculate_working_hours(
		ns_logs, check_in_out_type, working_hours_calc_type
	)
	return out_time or (logs[-1].get("time") if len(logs) >= 2 else None)


def _working_hours_for_employee(
	employee: EmployeeRow, logs: list[dict], attendance_row: dict | None
) -> float:
	if attendance_row and attendance_row.get("working_hours"):
		return float(attendance_row["working_hours"])

	check_in_out_type, working_hours_calc_type = _get_shift_calc_settings(
		employee.name, employee.default_shift, logs
	)
	if not logs:
		return 0.0
	ns_logs = _logs_to_namespace(logs)
	total_hours, _, _ = calculate_working_hours(
		ns_logs, check_in_out_type, working_hours_calc_type
	)
	return float(total_hours or 0)


def build_checkin_report_data() -> dict:
	employees = _get_active_employees()
	checkins = _today_checkins()
	by_emp = _group_checkins_by_employee(checkins)

	checked_in = []
	not_checked_in = []

	for emp in employees:
		logs = by_emp.get(emp.name, [])
		if logs:
			checked_in.append(
				{
					"employee_name": emp.employee_name or emp.name,
					"department": emp.department or "",
					"checkin_time": _format_time(_first_checkin_time(logs)),
				}
			)
		else:
			not_checked_in.append(
				{
					"employee_name": emp.employee_name or emp.name,
					"department": emp.department or "",
				}
			)

	labels = dict(AR_LABELS_CHECKIN)
	return {
		"labels": labels,
		"report_date": _report_date_str(),
		"checked_in": checked_in,
		"not_checked_in": not_checked_in,
		"counts": {
			"checked_in": len(checked_in),
			"not_checked_in": len(not_checked_in),
			"total": len(employees),
		},
	}


def build_checkout_report_data() -> dict:
	employees = _get_active_employees()
	checkins = _today_checkins()
	by_emp = _group_checkins_by_employee(checkins)
	attendance_map = _today_attendance_map()

	checked_out = []
	not_checked_out = []
	no_checkin_checkout = []

	for emp in employees:
		logs = by_emp.get(emp.name, [])
		att = attendance_map.get(emp.name)
		check_in_out_type, working_hours_calc_type = _get_shift_calc_settings(
			emp.name, emp.default_shift, logs
		)

		if not logs and not att:
			no_checkin_checkout.append(
				{
					"employee_name": emp.employee_name or emp.name,
					"department": emp.department or "",
				}
			)
			continue

		has_in = _has_checkin_today(logs) or bool(att and att.get("in_time"))
		has_out = _has_checkout_today(logs, check_in_out_type) or bool(att and att.get("out_time"))

		if has_out:
			checkout_dt = None
			if att and att.get("out_time"):
				checkout_dt = att.get("out_time")
			else:
				checkout_dt = _checkout_time_from_logs(
					logs, check_in_out_type, working_hours_calc_type
				)
			hours = _working_hours_for_employee(emp, logs, att)
			checked_out.append(
				{
					"employee_name": emp.employee_name or emp.name,
					"department": emp.department or "",
					"checkout_time": _format_time(checkout_dt),
					"total_hours": f"{hours:.2f}",
				}
			)
		elif has_in:
			not_checked_out.append(
				{
					"employee_name": emp.employee_name or emp.name,
					"department": emp.department or "",
				}
			)
		else:
			no_checkin_checkout.append(
				{
					"employee_name": emp.employee_name or emp.name,
					"department": emp.department or "",
				}
			)

	labels = dict(AR_LABELS_CHECKOUT)
	return {
		"labels": labels,
		"report_date": _report_date_str(),
		"checked_out": checked_out,
		"not_checked_out": not_checked_out,
		"no_checkin_checkout": no_checkin_checkout,
		"counts": {
			"checked_out": len(checked_out),
			"not_checked_out": len(not_checked_out),
			"no_checkin_checkout": len(no_checkin_checkout),
			"total": len(employees),
		},
	}


def _send_report_email(
	recipients: list[str],
	subject: str,
	template: str,
	args: dict,
	header: list | None = None,
) -> int:
	sent = 0
	for email in recipients:
		try:
			frappe.sendmail(
				recipients=[email],
				subject=subject,
				template=template,
				args=args,
				header=header or [args["labels"]["title"], "blue"],
			)
			sent += 1
		except Exception:
			frappe.log_error(
				title=f"Attendance email failed -> {email}",
				message=frappe.get_traceback(),
			)
	return sent


def send_checkin_summary(update_last_sent: bool = True) -> int:
	if not _reports_enabled():
		return 0
	recipients = _get_recipients()
	if not recipients:
		return 0
	args = build_checkin_report_data()
	subject = f"{AR_LABELS_CHECKIN['title']} - {args['report_date']}"
	emails = [email for _, email in recipients]
	sent = _send_report_email(
		emails,
		subject,
		"attendance_checkin_summary",
		args,
	)
	if sent and update_last_sent:
		_mark_last_sent("mksa_checkin_report_last_sent")
	return sent


def send_checkout_summary(update_last_sent: bool = True) -> int:
	if not _reports_enabled():
		return 0
	recipients = _get_recipients()
	if not recipients:
		return 0
	args = build_checkout_report_data()
	subject = f"{AR_LABELS_CHECKOUT['title']} - {args['report_date']}"
	emails = [email for _, email in recipients]
	sent = _send_report_email(
		emails,
		subject,
		"attendance_checkout_summary",
		args,
	)
	if sent and update_last_sent:
		_mark_last_sent("mksa_checkout_report_last_sent")
	return sent


def _mark_last_sent(fieldname: str):
	frappe.db.set_value("HR Settings", "HR Settings", fieldname, today())
	frappe.db.commit()


def _time_in_send_window(configured_time, now_dt: datetime | None = None) -> bool:
	if not configured_time:
		return False
	now_dt = now_dt or now_datetime()
	target = get_time(str(configured_time))
	current = now_dt.time().replace(microsecond=0)
	current_mins = current.hour * 60 + current.minute
	target_mins = target.hour * 60 + target.minute
	return target_mins <= current_mins < target_mins + SEND_WINDOW_MINUTES


def _already_sent_today(fieldname: str) -> bool:
	last_sent = getattr(_settings(), fieldname, None)
	return getdate(last_sent) == getdate(today()) if last_sent else False


def run_due_attendance_email_reports():
	"""Scheduled: send check-in/check-out reports when configured time is due (Sun-Thu cron)."""
	if not _reports_enabled():
		return
	settings = _settings()
	try:
		if (
			settings.mksa_checkin_report_time
			and _time_in_send_window(settings.mksa_checkin_report_time)
			and not _already_sent_today("mksa_checkin_report_last_sent")
		):
			send_checkin_summary(update_last_sent=True)
		if (
			settings.mksa_checkout_report_time
			and _time_in_send_window(settings.mksa_checkout_report_time)
			and not _already_sent_today("mksa_checkout_report_last_sent")
		):
			send_checkout_summary(update_last_sent=True)
	except Exception:
		frappe.log_error(
			title="Attendance email scheduler failed",
			message=frappe.get_traceback(),
		)


@frappe.whitelist()
def send_test_attendance_email(test_email: str | None = None, report_type: str | None = None):
	"""Send a test attendance email from HR Settings."""
	frappe.only_for(("HR Manager", "System Manager"))

	settings = _settings()
	email = (test_email or settings.mksa_attendance_test_email or "").strip()
	report_type = report_type or settings.mksa_attendance_test_report_type

	if not email:
		frappe.throw(_("يرجى إدخال بريد الاختبار."))
	validate_email_address(email, throw=True)

	if report_type == REPORT_CHECKIN:
		args = build_checkin_report_data()
		subject = f"{AR_LABELS_CHECKIN['title']} (اختبار) - {args['report_date']}"
		template = "attendance_checkin_summary"
	elif report_type == REPORT_CHECKOUT:
		args = build_checkout_report_data()
		subject = f"{AR_LABELS_CHECKOUT['title']} (اختبار) - {args['report_date']}"
		template = "attendance_checkout_summary"
	else:
		frappe.throw(_("يرجى اختيار نوع التقرير: تسجيل الدخول أو تسجيل الخروج."))

	sent = _send_report_email([email], subject, template, args)
	if not sent:
		frappe.throw(_("فشل إرسال بريد الاختبار. راجع سجل الأخطاء."))

	return {
		"sent": sent,
		"message": _("تم إرسال بريد الاختبار إلى {0}").format(email),
	}
