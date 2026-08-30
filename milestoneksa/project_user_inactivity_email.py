"""Daily project-task inactivity notices with progressive Additional Salary deductions."""

from __future__ import annotations

from calendar import monthrange
from datetime import datetime

import frappe
from frappe.utils import flt, format_datetime, get_last_day, getdate, today

TEMPLATE_NAME = "Project User Inactivity Deduction - AR"
INACTIVITY_THRESHOLD_DAYS = 15
DEDUCTION_COMPONENT = "خصم عدم إدخال مهام"

EXECUTIVE_RECIPIENTS = [
	"a.abdullah@milestoneksa.com",  # CEO
	"m.eqtefan@milestoneksa.com",  # COO
	"m.alnasser@milestoneksa.com",  # CFO
]

MONITORED_USERS = [
	"a.alhaj@milestoneksa.com",
]


def get_last_task_alteration(user: str) -> dict | None:
	row = frappe.db.sql(
		"""
		SELECT v.creation, v.docname, t.subject, t.project, p.project_name
		FROM `tabVersion` v
		INNER JOIN `tabTask` t ON t.name = v.docname
		LEFT JOIN `tabProject` p ON p.name = t.project
		WHERE v.ref_doctype = 'Task' AND v.owner = %s
		ORDER BY v.creation DESC
		LIMIT 1
		""",
		user,
		as_dict=True,
	)
	return row[0] if row else None


def get_user_projects(user: str) -> list[dict]:
	"""Projects linked to the user's open tasks or recent task updates."""
	rows = frappe.db.sql(
		"""
		SELECT DISTINCT t.project, p.project_name
		FROM `tabTask` t
		LEFT JOIN `tabProject` p ON p.name = t.project
		WHERE t.project IS NOT NULL AND t.project != ''
			AND (
				t._assign LIKE %s
				OR EXISTS (
					SELECT 1 FROM `tabVersion` v
					WHERE v.ref_doctype = 'Task' AND v.docname = t.name AND v.owner = %s
				)
			)
			AND t.status NOT IN ('Completed', 'Cancelled')
		ORDER BY p.project_name, t.project
		""",
		(f"%{user}%", user),
		as_dict=True,
	)
	if rows:
		return rows

	return frappe.db.sql(
		"""
		SELECT DISTINCT t.project, p.project_name
		FROM `tabVersion` v
		INNER JOIN `tabTask` t ON t.name = v.docname
		LEFT JOIN `tabProject` p ON p.name = t.project
		WHERE v.ref_doctype = 'Task' AND v.owner = %s
			AND t.project IS NOT NULL AND t.project != ''
		ORDER BY v.creation DESC
		LIMIT 5
		""",
		user,
		as_dict=True,
	)


def format_project_list(projects: list[dict]) -> str:
	if not projects:
		return "—"
	parts = []
	for row in projects:
		name = row.project_name or row.project
		parts.append(f"{row.project} — {name}" if row.project_name else row.project)
	return " | ".join(parts)


def has_task_action_on_date(user: str, check_date=None) -> bool:
	"""True if the user created or altered any Task on the given date."""
	check_date = getdate(check_date or today())
	return bool(
		frappe.db.sql(
			"""
			SELECT 1
			FROM `tabVersion` v
			INNER JOIN `tabTask` t ON t.name = v.docname
			WHERE v.ref_doctype = 'Task'
				AND v.owner = %s
				AND DATE(v.creation) = %s
			LIMIT 1
			""",
			(user, check_date),
		)
	)


def get_employee_for_user(user: str) -> dict | None:
	return frappe.db.get_value(
		"Employee",
		{"user_id": user, "status": "Active"},
		["name", "employee_name", "user_id", "designation", "department", "company"],
		as_dict=True,
	)


def get_latest_salary_slip(employee: str) -> dict | None:
	rows = frappe.db.sql(
		"""
		SELECT name, start_date, end_date, gross_pay, net_pay, payment_days
		FROM `tabSalary Slip`
		WHERE employee = %s AND docstatus = 1
		ORDER BY end_date DESC, posting_date DESC
		LIMIT 1
		""",
		employee,
		as_dict=True,
	)
	return rows[0] if rows else None


def get_current_month_payroll_date() -> str:
	return get_last_day(getdate(today()))


def ensure_deduction_salary_component():
	if frappe.db.exists("Salary Component", DEDUCTION_COMPONENT):
		return DEDUCTION_COMPONENT

	doc = frappe.get_doc(
		{
			"doctype": "Salary Component",
			"salary_component": DEDUCTION_COMPONENT,
			"salary_component_abbr": "خصم مهام",
			"type": "Deduction",
			"description": "خصم تلقائي لعدم إدخال أو تحديث مهام المشروع",
		}
	)
	doc.insert(ignore_permissions=True)
	return DEDUCTION_COMPONENT


def find_inactivity_additional_salary(employee: str, payroll_date) -> dict | None:
	payroll_date = getdate(payroll_date)
	rows = frappe.db.sql(
		"""
		SELECT name, amount, docstatus, payroll_date
		FROM `tabAdditional Salary`
		WHERE employee = %s
			AND salary_component = %s
			AND docstatus < 2
			AND YEAR(payroll_date) = %s
			AND MONTH(payroll_date) = %s
		ORDER BY modified DESC
		LIMIT 1
		""",
		(employee, DEDUCTION_COMPONENT, payroll_date.year, payroll_date.month),
		as_dict=True,
	)
	return rows[0] if rows else None


def apply_inactivity_additional_salary(data: dict) -> dict:
	"""Create or update Additional Salary deduction for the current payroll month."""
	ensure_deduction_salary_component()
	employee = data["employee"]
	payroll_date = get_current_month_payroll_date()
	amount = flt(data["deduction_amount"], 2)
	days_inactive = data["days_inactive"]
	deduction_days = data["deduction_days"]

	existing = find_inactivity_additional_salary(employee.name, payroll_date)
	description = (
		f"خصم عدم إدخال مهام — {days_inactive} يوم انقطاع — {deduction_days} يوم خصم — "
		f"آخر تحديث: {format_datetime(data['report_date'], 'dd/MM/yyyy')}"
	)

	if existing:
		frappe.db.set_value(
			"Additional Salary",
			existing.name,
			{
				"amount": amount,
				"payroll_date": payroll_date,
				"disabled": 0,
			},
			update_modified=True,
		)
		frappe.db.set_value(
			"Additional Salary",
			existing.name,
			"_comments",
			description,
			update_modified=False,
		)
		action = "updated"
		docname = existing.name
	else:
		doc = frappe.get_doc(
			{
				"doctype": "Additional Salary",
				"employee": employee.name,
				"employee_name": employee.employee_name,
				"company": employee.company,
				"salary_component": DEDUCTION_COMPONENT,
				"type": "Deduction",
				"currency": "SAR",
				"amount": amount,
				"payroll_date": payroll_date,
				"overwrite_salary_structure_amount": 1,
				"is_recurring": 0,
				"disabled": 0,
			}
		)
		doc.insert(ignore_permissions=True)
		frappe.db.set_value("Additional Salary", doc.name, "_comments", description, update_modified=False)
		action = "created"
		docname = doc.name

	frappe.db.commit()
	return {
		"action": action,
		"additional_salary": docname,
		"amount": amount,
		"payroll_date": str(payroll_date),
		"docstatus": frappe.db.get_value("Additional Salary", docname, "docstatus"),
	}


def build_inactivity_report(user: str) -> dict | None:
	last = get_last_task_alteration(user)
	if not last:
		return None

	employee = get_employee_for_user(user)
	if not employee:
		return None

	report_date = getdate(today())
	last_dt = last.creation
	days_inactive = (report_date - getdate(last_dt)).days
	if days_inactive < INACTIVITY_THRESHOLD_DAYS:
		return None

	deduction_days = flt(days_inactive / 2, 2)
	slip = get_latest_salary_slip(employee.name)
	gross_pay = flt(slip.gross_pay if slip else 0)
	payment_days = flt(slip.payment_days if slip and slip.payment_days else 30) or 30
	if not payment_days and slip and slip.start_date and slip.end_date:
		payment_days = monthrange(getdate(slip.end_date).year, getdate(slip.end_date).month)[1]
	daily_rate = flt(gross_pay / payment_days, 2) if gross_pay else 0
	deduction_amount = flt(deduction_days * daily_rate, 2)

	return {
		"user": user,
		"employee": employee,
		"last_alteration": last_dt,
		"last_task_id": last.docname,
		"last_task_subject": last.subject or "",
		"days_inactive": days_inactive,
		"deduction_days": deduction_days,
		"report_date": report_date,
		"salary_slip": slip,
		"gross_pay": gross_pay,
		"payment_days": payment_days,
		"daily_rate": daily_rate,
		"deduction_amount": deduction_amount,
		"payroll_date": get_current_month_payroll_date(),
	}


def _fmt_date(dt) -> str:
	if not dt:
		return ""
	if isinstance(dt, datetime):
		return format_datetime(dt, "dd/MM/yyyy — HH:mm")
	return format_datetime(getdate(dt), "dd/MM/yyyy")


def build_email_html(data: dict) -> str:
	emp = data["employee"]
	slip = data.get("salary_slip")
	additional_salary = data.get("additional_salary", {})
	slip_period = ""
	if slip:
		slip_period = f"{format_datetime(slip.start_date, 'MMMM yyyy')} ({format_datetime(slip.start_date, 'dd/MM/yyyy')} — {format_datetime(slip.end_date, 'dd/MM/yyyy')})"

	add_salary_row = ""
	if additional_salary:
		add_salary_row = f"""
<tr><td>سجل Additional Salary</td><td>{additional_salary.get('additional_salary', '')}</td></tr>
<tr><td>تاريخ الرواتب (Payroll Date)</td><td>{additional_salary.get('payroll_date', '')}</td></tr>
<tr><td>حالة السجل</td><td>{'مسودة' if additional_salary.get('docstatus') == 0 else 'معتمد'}</td></tr>
"""

	return f"""
<div dir="rtl" style="font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6;">
<p>إشعار نظام — {emp.company or 'شركة مرحلة المشروع للتطوير العقاري'}</p>
<p>تاريخ الإصدار: <strong>{format_datetime(data['report_date'], 'dd/MM/yyyy')}</strong></p>
<hr>
<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%; text-align: right;">
<tr style="background: #f2f2f2;"><th colspan="2">1. بيانات الموظف</th></tr>
<tr><td>الاسم</td><td>{emp.employee_name}</td></tr>
<tr><td>المستخدم</td><td>{emp.user_id}</td></tr>
<tr><td>رقم الموظف</td><td>{emp.name}</td></tr>
</table>
<br>
<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%; text-align: right;">
<tr style="background: #f2f2f2;"><th colspan="2">2. آخر إدخال مسجّل</th></tr>
<tr><td>التاريخ</td><td>{_fmt_date(data['last_alteration'])}</td></tr>
<tr><td>المهمة</td><td>{data['last_task_id']} | {data['last_task_subject']}</td></tr>
<tr><td>المدة منذ آخر إدخال</td><td><strong>{data['days_inactive']} يوم</strong></td></tr>
</table>
<br>
<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%; text-align: right;">
<tr style="background: #f2f2f2;"><th colspan="2">3. تطبيق السياسة</th></tr>
<tr><td>السياسة</td><td>عند انقطاع إدخالات مستخدم المشروع <strong>15 يوماً متتالياً</strong>، يُخصم من الراتب <strong>عدد أيام يساوي نصف فترة الانقطاع</strong>، مع <strong>استمرار العلاقة الوظيفية</strong></td></tr>
<tr><td>فترة الانقطاع</td><td>{data['days_inactive']} يوم</td></tr>
<tr><td>أيام الخصم المطبّقة</td><td><strong>{data['deduction_days']} يوم</strong></td></tr>
<tr><td>تاريخ التطبيق</td><td>{format_datetime(data['report_date'], 'dd/MM/yyyy')}</td></tr>
</table>
<br>
<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%; text-align: right;">
<tr style="background: #f2f2f2;"><th colspan="2">4. الخصم المالي — Additional Salary{f' (مرجع راتب: {slip_period})' if slip_period else ''}</th></tr>
<tr><td>الراتب الإجمالي المرجعي</td><td>{data['gross_pay']:,.2f} ر.س</td></tr>
<tr><td>الأجر اليومي ({data['gross_pay']:,.0f} ÷ {int(data['payment_days'])})</td><td>{data['daily_rate']:,.2f} ر.س</td></tr>
<tr><td><strong>مبلغ الخصم ({data['deduction_days']} يوم)</strong></td><td><strong>{data['deduction_amount']:,.2f} ر.س</strong></td></tr>
{add_salary_row}
</table>
<hr>
<p><strong>إجراء مطلوب:</strong> استئناف تحديث مهام المشاريع فوراً. يُطبّق الخصم عبر Additional Salary على قسيمة راتب الشهر الحالي.</p>
<p>— نظام المتابعة | الموارد البشرية</p>
</div>
"""


def build_subject(data: dict) -> str:
	emp = data["employee"]
	return (
		f"[SYS-NOTIFY] تنبيه عدم إدخال — {emp.name} | "
		f"{data['days_inactive']} يوم | خصم {data['deduction_days']} يوم"
	)


def ensure_template(html: str, subject: str):
	if frappe.db.exists("Email Template", TEMPLATE_NAME):
		doc = frappe.get_doc("Email Template", TEMPLATE_NAME)
	else:
		doc = frappe.new_doc("Email Template")
		doc.name = TEMPLATE_NAME

	doc.subject = subject
	doc.use_html = 1
	doc.enabled = 1
	doc.response_html = html
	doc.response = html
	doc.save(ignore_permissions=True)


def send_inactivity_notice(data: dict, extra_recipients: list[str] | None = None) -> list[str]:
	html = build_email_html(data)
	subject = build_subject(data)
	ensure_template(html, subject)

	recipients = list({data["user"], *EXECUTIVE_RECIPIENTS, *(extra_recipients or [])})
	sent = []
	for recipient in recipients:
		if not recipient:
			continue
		frappe.sendmail(recipients=[recipient], subject=subject, message=html, now=True)
		sent.append(recipient)
	return sent


def run_daily_project_inactivity_emails() -> list[dict]:
	"""Scheduled: apply Additional Salary deduction + send daily notices."""
	results = []
	for user in MONITORED_USERS:
		try:
			data = build_inactivity_report(user)
			if not data:
				results.append({"user": user, "sent": False, "reason": "below_threshold_or_no_data"})
				continue

			deduction_result = apply_inactivity_additional_salary(data)
			data["additional_salary"] = deduction_result
			sent = send_inactivity_notice(data)
			results.append(
				{
					"user": user,
					"sent": True,
					"recipients": sent,
					"days_inactive": data["days_inactive"],
					"deduction_days": data["deduction_days"],
					"deduction_amount": data["deduction_amount"],
					"additional_salary": deduction_result,
				}
			)
		except Exception:
			frappe.log_error(title=f"Project inactivity job failed: {user}", message=frappe.get_traceback())
			results.append({"user": user, "sent": False, "reason": "error"})
	return results


def apply_deduction_for_user(user: str = "a.alhaj@milestoneksa.com"):
	"""Manual: apply/update Additional Salary only (no email)."""
	data = build_inactivity_report(user)
	if not data:
		return {"user": user, "applied": False, "reason": "below_threshold_or_no_data"}
	result = apply_inactivity_additional_salary(data)
	return {"user": user, "applied": True, **result, **get_report_fields(data)}


def get_report_fields(data: dict) -> dict:
	return {
		"days_inactive": data["days_inactive"],
		"deduction_days": data["deduction_days"],
		"deduction_amount": data["deduction_amount"],
	}


def send_test(recipient="ahamad18189@gmail.com"):
	data = build_inactivity_report("a.alhaj@milestoneksa.com")
	if not data:
		frappe.throw("User is below inactivity threshold or has no task history.")
	data["additional_salary"] = apply_inactivity_additional_salary(data)
	sent = send_inactivity_notice(data, extra_recipients=[recipient])
	return {"template": TEMPLATE_NAME, "sent_to": sent, "subject": build_subject(data), "data": data}


def send_to_executives():
	data = build_inactivity_report("a.alhaj@milestoneksa.com")
	if not data:
		frappe.throw("User is below inactivity threshold or has no task history.")
	data["additional_salary"] = apply_inactivity_additional_salary(data)
	sent = send_inactivity_notice(data)
	return {"template": TEMPLATE_NAME, "sent_to": sent, "subject": build_subject(data)}


def get_report_summary(user="a.alhaj@milestoneksa.com"):
	data = build_inactivity_report(user)
	if not data:
		last = get_last_task_alteration(user)
		days = (getdate(today()) - getdate(last.creation)).days if last else None
		return {"user": user, "days_inactive": days, "below_threshold": True}
	existing = find_inactivity_additional_salary(data["employee"].name, data["payroll_date"])
	return {
		"user": user,
		"days_inactive": data["days_inactive"],
		"deduction_days": data["deduction_days"],
		"deduction_amount": data["deduction_amount"],
		"payroll_date": str(data["payroll_date"]),
		"last_alteration": str(data["last_alteration"]),
		"last_task": f"{data['last_task_id']} | {data['last_task_subject']}",
		"existing_additional_salary": existing,
	}


FORMAL_WARNING_TEMPLATE = "Project User Formal Warning - AR"


def build_formal_warning_context(
	user: str = "a.alhaj@milestoneksa.com",
	*,
	daily_check: bool = False,
	check_date=None,
) -> dict:
	last = get_last_task_alteration(user)
	employee = get_employee_for_user(user)
	if not employee:
		frappe.throw(f"No active employee linked to user {user}")

	report_date = getdate(check_date or today())
	last_dt = last.creation if last else None
	days_inactive = (report_date - getdate(last_dt)).days if last_dt else None
	projects = get_user_projects(user)
	emp_suffix = employee.name.split("-")[-1]
	reference_no = (
		f"HR-WARN-{report_date.strftime('%Y%m%d')}-{emp_suffix}"
		if daily_check
		else f"HR-WARN-{report_date.strftime('%Y%m')}-{emp_suffix}"
	)

	return {
		"user": user,
		"employee": employee,
		"last_alteration": last_dt,
		"last_task_id": last.docname if last else "",
		"last_task_subject": (last.subject or "") if last else "",
		"last_project": (last.project or "") if last else "",
		"last_project_name": (last.project_name or last.project or "") if last else "",
		"projects": projects,
		"project_list_text": format_project_list(projects),
		"days_inactive": days_inactive,
		"report_date": report_date,
		"daily_check": daily_check,
		"no_action_today": daily_check and not has_task_action_on_date(user, report_date),
		"reference_no": reference_no,
	}


def build_formal_warning_subject(data: dict) -> str:
	emp = data["employee"]
	if data.get("daily_check"):
		return (
			f"إنذار نظامي — عدم تحديث مهام اليوم ({format_datetime(data['report_date'], 'dd/MM/yyyy')}) — "
			f"{emp.employee_name} ({emp.name})"
		)
	return f"إنذار نظامي — عدم تحديث مهام المشروع — {emp.employee_name} ({emp.name})"


def build_formal_warning_html(data: dict) -> str:
	emp = data["employee"]
	days_text = f"<strong>{data['days_inactive']} يوم</strong>" if data["days_inactive"] is not None else "غير محدد"
	project_list = data.get("project_list_text") or "—"
	last_project_text = data.get("last_project_name") or data.get("last_project") or "—"
	if data.get("last_project") and data.get("last_project_name"):
		last_project_text = f"{data['last_project']} — {data['last_project_name']}"

	project_rows = f"""
<tr><td>المشروع / المشاريع</td><td><strong>{project_list}</strong></td></tr>
"""
	last_task_row = ""
	if data.get("last_task_id"):
		last_task_row = f"""
<tr><td>آخر مهمة تم تعديلها</td><td>{data['last_task_id']} — {data['last_task_subject']}</td></tr>
<tr><td>مشروع آخر مهمة</td><td>{last_project_text}</td></tr>
<tr><td>تاريخ آخر تعديل مسجّل</td><td>{_fmt_date(data['last_alteration'])}</td></tr>
<tr><td>المدة منذ آخر تعديل</td><td>{days_text}</td></tr>
"""
	else:
		last_task_row = "<tr><td colspan='2'>لا يوجد أي تعديل مسجّل على مهام المشروع في النظام.</td></tr>"

	daily_row = ""
	daily_intro = ""
	if data.get("daily_check"):
		daily_row = f"""
<tr><td>تاريخ المتابعة</td><td>{format_datetime(data['report_date'], 'dd/MM/yyyy')}</td></tr>
<tr><td>حالة اليوم (حتى 4:00 مساءً)</td><td><strong>لم يُسجّل أي إدخال أو تعديل على مهام المشروع</strong></td></tr>
"""
		daily_intro = f"""
<p>
نفيدكم بأنه حتى الساعة <strong>4:00 مساءً</strong> من تاريخ <strong>{format_datetime(data['report_date'], 'dd/MM/yyyy')}</strong>،
تبيّن <strong>عدم قيامكم بأي إدخال أو تعديل على مهام المشروع</strong>
(<strong>{project_list}</strong>) في نظام إدارة المشاريع،
مما يُعد إخلالاً بواجباتكم الوظيفية وإجراءات العمل المعتمدة في الشركة.
</p>
"""
	else:
		daily_intro = f"""
<p>
نفيدكم بأنه وفق متابعة النظام الإلكتروني لمهام المشاريع
(<strong>{project_list}</strong>)، تبيّن <strong>عدم قيامكم بتحديث أو تعديل مهام المشروع
المسندة إليكم</strong> في نظام إدارة المشاريع بالشكل المطلوب، مما يُعد إخلالاً بواجباتكم الوظيفية
وإجراءات العمل المعتمدة في الشركة.
</p>
"""

	return f"""
<div dir="rtl" style="font-family: 'Traditional Arabic', 'Arial', sans-serif; font-size: 15px; line-height: 1.9; color: #111;">
<p style="text-align: center;"><strong>{emp.company or 'شركة مرحلة المشروع للتطوير العقاري'}</strong></p>
<p style="text-align: center;">إدارة الموارد البشرية</p>
<hr>
<p><strong>الرقم المرجعي:</strong> {data['reference_no']}</p>
<p><strong>التاريخ:</strong> {format_datetime(data['report_date'], 'dd/MM/yyyy')}</p>
<p><strong>الموضوع:</strong> إنذار نظامي — إخلال بواجب تحديث مهام المشروع في النظام</p>
<hr>
<p>السيد/ <strong>{emp.employee_name}</strong> المحترم،</p>
<p>المسمى الوظيفي: <strong>{emp.designation or '—'}</strong></p>
<p>الإدارة: <strong>{emp.department or '—'}</strong></p>
<p>رقم الموظف: <strong>{emp.name}</strong></p>
<p>البريد الإلكتروني: <strong>{emp.user_id}</strong></p>
<br>
<p>تحية طيبة وبعد،</p>
{daily_intro}
<p>
يُعد إدخال وتحديث المهام اليومية في النظام من المتطلبات الأساسية لضمان متابعة سير العمل،
وإعداد التقارير، وتوثيق الإنجاز، ولا يُقبل الاكتفاء بالإنجاز الفعلي دون تسجيله في النظام.
</p>
<br>
<table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%; text-align: right;">
<tr style="background: #f5f5f5;"><th colspan="2">البيانات المسجّلة في النظام</th></tr>
{project_rows}
{daily_row}
{last_task_row}
<tr><td>تاريخ إصدار الإنذار</td><td>{format_datetime(data['report_date'], 'dd/MM/yyyy')}</td></tr>
</table>
<br>
<p><strong>بناءً على ما سبق، نُخطركم رسمياً بما يلي:</strong></p>
<ol style="padding-right: 20px;">
<li>يُعد هذا الإشعار <strong>إنذاراً نظامياً</strong> وفق سياسات الشركة ولوائح العمل المعمول بها.</li>
<li>يُطلب منكم <strong>استئناف تحديث مهام المشاريع فوراً</strong> والالتزام بالإدخال اليومي في النظام.</li>
<li>في حال <strong>عدم تحديث مهام المشروع في يوم العمل نفسه (حتى الساعة 4:00 مساءً)</strong>،
يُصدر هذا الإنذار تلقائياً في كل يوم عمل دون إدخال أو تعديل مسجّل.</li>
<li>في حال استمرار الانقطاع لمدة <strong>{INACTIVITY_THRESHOLD_DAYS} يوماً متتالياً</strong>، تُطبَّق السياسة المالية المعتمدة
(خصم يعادل نصف أيام الانقطاع من الراتب عبر Additional Salary) مع الاحتفاظ بالعلاقة الوظيفية.</li>
<li>تكرار المخالفة قد يعرّضكم لإجراءات تأديبية إضافية وفق نظام العمل واللوائح الداخلية.</li>
</ol>
<br>
<p><strong>المطلوب منكم خلال 24 ساعة:</strong></p>
<ul style="padding-right: 20px;">
<li>مراجعة جميع المهام المفتوحة والمسندة إليكم.</li>
<li>تحديث حالة كل مهمة ونسبة الإنجاز والملاحظات في النظام.</li>
<li>إخطار مدير المشاريع المباشر عند وجود أي عائق يمنع التحديث.</li>
</ul>
<br>
<p>نسخة إلى:</p>
<ul style="padding-right: 20px;">
<li>الرئيس التنفيذي — a.abdullah@milestoneksa.com</li>
<li>مدير العمليات — m.eqtefan@milestoneksa.com</li>
<li>المدير المالي — m.alnasser@milestoneksa.com</li>
</ul>
<br>
<p>وتفضلوا بقبول فائق الاحترام والتقدير،</p>
<p><strong>إدارة الموارد البشرية</strong><br>{emp.company or 'شركة مرحلة المشروع للتطوير العقاري'}</p>
<p style="font-size: 12px; color: #666;">— إشعار آلي من نظام متابعة مهام المشاريع — لا يُعد هذا الإنذار إنهاءً للخدمة —</p>
</div>
"""


def preview_formal_warning(user: str = "a.alhaj@milestoneksa.com", daily_check: bool = False) -> dict:
	"""Return subject + HTML draft without sending."""
	data = build_formal_warning_context(user, daily_check=daily_check)
	return {
		"user": user,
		"recipients_on_send": [user, *EXECUTIVE_RECIPIENTS],
		"cc_on_send": EXECUTIVE_RECIPIENTS,
		"subject": build_formal_warning_subject(data),
		"html": build_formal_warning_html(data),
		"context": {
			"employee": data["employee"].name,
			"employee_name": data["employee"].employee_name,
			"days_inactive": data["days_inactive"],
			"daily_check": data.get("daily_check"),
			"no_action_today": data.get("no_action_today"),
			"last_alteration": str(data["last_alteration"]) if data["last_alteration"] else None,
			"last_task": f"{data['last_task_id']} | {data['last_task_subject']}" if data.get("last_task_id") else None,
			"projects": data.get("project_list_text"),
			"reference_no": data["reference_no"],
		},
	}


def send_formal_warning(
	user: str = "a.alhaj@milestoneksa.com",
	extra_recipients: list[str] | None = None,
	*,
	daily_check: bool = False,
	check_date=None,
) -> dict:
	"""Send formal system warning (إنذار نظامي) to user with executives on CC."""
	data = build_formal_warning_context(user, daily_check=daily_check, check_date=check_date)
	html = build_formal_warning_html(data)
	subject = build_formal_warning_subject(data)

	if frappe.db.exists("Email Template", FORMAL_WARNING_TEMPLATE):
		doc = frappe.get_doc("Email Template", FORMAL_WARNING_TEMPLATE)
	else:
		doc = frappe.new_doc("Email Template")
		doc.name = FORMAL_WARNING_TEMPLATE
	doc.subject = subject
	doc.use_html = 1
	doc.enabled = 1
	doc.response_html = html
	doc.response = html
	doc.save(ignore_permissions=True)

	cc = list({*EXECUTIVE_RECIPIENTS, *(extra_recipients or [])})
	frappe.sendmail(
		recipients=[user],
		cc=cc,
		subject=subject,
		message=html,
		now=True,
	)

	return {
		"sent_to": user,
		"cc": cc,
		"subject": subject,
		"reference_no": data["reference_no"],
	}


def run_daily_formal_task_warnings() -> list[dict]:
	"""4 PM Sun–Thu: send إنذار نظامي if no task action was recorded today."""
	check_date = getdate(today())
	results = []

	for user in MONITORED_USERS:
		try:
			if has_task_action_on_date(user, check_date):
				results.append({"user": user, "sent": False, "reason": "action_today", "date": str(check_date)})
				continue

			result = send_formal_warning(user, daily_check=True, check_date=check_date)
			results.append({"user": user, "sent": True, "date": str(check_date), **result})
		except Exception:
			frappe.log_error(title=f"Daily formal task warning failed: {user}", message=frappe.get_traceback())
			results.append({"user": user, "sent": False, "reason": "error", "date": str(check_date)})

	return results
