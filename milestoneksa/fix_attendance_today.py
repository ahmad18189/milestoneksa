import frappe
from frappe.utils import today


def fix_today_checkin_attendance(employee="HR-EMP-00005"):
	checkin = frappe.db.get_value(
		"Employee Checkin",
		{"employee": employee, "time": [">=", f"{today()} 00:00:00"]},
		["name", "time"],
		as_dict=True,
	)
	if not checkin:
		return {"fixed": False, "reason": "no_checkin_today"}

	existing = frappe.db.get_value(
		"Attendance",
		{"employee": employee, "attendance_date": today(), "docstatus": 1},
		"name",
	)
	if existing:
		frappe.db.set_value(
			"Attendance",
			existing,
			{"status": "Present", "in_time": checkin.time, "shift": "Normal"},
			update_modified=True,
		)
		att_name = existing
	else:
		emp = frappe.db.get_value(
			"Employee", employee, ["employee_name", "company", "department"], as_dict=True
		)
		doc = frappe.get_doc(
			{
				"doctype": "Attendance",
				"employee": employee,
				"employee_name": emp.employee_name,
				"company": emp.company,
				"department": emp.department,
				"attendance_date": today(),
				"status": "Present",
				"shift": "Normal",
				"in_time": checkin.time,
			}
		)
		doc.insert(ignore_permissions=True)
		doc.submit()
		att_name = doc.name

	frappe.db.set_value("Employee Checkin", checkin.name, "attendance", att_name)
	frappe.db.commit()
	return {"fixed": True, "attendance": att_name, "checkin": checkin.name, "in_time": str(checkin.time)}
