import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"HR Settings": [
				{
					"fieldname": "mksa_attendance_email_sb",
					"label": "تقارير الحضور بالبريد",
					"fieldtype": "Section Break",
					"insert_after": "allow_geolocation_tracking",
					"collapsible": 1,
				},
				{
					"fieldname": "mksa_enable_attendance_email_reports",
					"label": "تفعيل تقارير الحضور بالبريد",
					"fieldtype": "Check",
					"default": "1",
					"insert_after": "mksa_attendance_email_sb",
				},
				{
					"fieldname": "mksa_attendance_email_roles",
					"label": "أدوار المستلمين",
					"fieldtype": "Table",
					"options": "Attendance Email Report Role",
					"insert_after": "mksa_enable_attendance_email_reports",
				},
				{
					"fieldname": "mksa_attendance_ignored_roles",
					"label": "أدوار مستثناة من التقارير",
					"fieldtype": "Table",
					"options": "Attendance Email Report Role",
					"insert_after": "mksa_attendance_email_roles",
					"description": "أي موظف مرتبط بمستخدم لديه أحد هذه الأدوار لن يظهر في تقارير الحضور.",
				},
				{
					"fieldname": "mksa_checkin_report_time",
					"label": "وقت تقرير تسجيل الدخول",
					"fieldtype": "Time",
					"default": "11:00:00",
					"insert_after": "mksa_attendance_ignored_roles",
				},
				{
					"fieldname": "mksa_checkout_report_time",
					"label": "وقت تقرير تسجيل الخروج",
					"fieldtype": "Time",
					"default": "18:00:00",
					"insert_after": "mksa_checkin_report_time",
				},
				{
					"fieldname": "mksa_attendance_email_test_cb",
					"label": "اختبار الإرسال",
					"fieldtype": "Column Break",
					"insert_after": "mksa_checkout_report_time",
				},
				{
					"fieldname": "mksa_attendance_test_email",
					"label": "بريد الاختبار",
					"fieldtype": "Data",
					"options": "Email",
					"insert_after": "mksa_attendance_email_test_cb",
				},
				{
					"fieldname": "mksa_attendance_test_report_type",
					"label": "نوع التقرير",
					"fieldtype": "Select",
					"options": "Check-in\nCheck-out",
					"default": "Check-in",
					"insert_after": "mksa_attendance_test_email",
				},
				{
					"fieldname": "mksa_send_attendance_test_email",
					"label": "إرسال بريد اختبار",
					"fieldtype": "Button",
					"insert_after": "mksa_attendance_test_report_type",
				},
				{
					"fieldname": "mksa_checkin_report_last_sent",
					"label": "آخر إرسال لتقرير الدخول",
					"fieldtype": "Date",
					"hidden": 1,
					"read_only": 1,
					"insert_after": "mksa_send_attendance_test_email",
				},
				{
					"fieldname": "mksa_checkout_report_last_sent",
					"label": "آخر إرسال لتقرير الخروج",
					"fieldtype": "Date",
					"hidden": 1,
					"read_only": 1,
					"insert_after": "mksa_checkin_report_last_sent",
				},
			]
		},
		ignore_validate=True,
	)
	frappe.clear_cache(doctype="HR Settings")
