"""Automatic attendance for Ahmed Abdelrahman (HR-EMP-00004)."""

from __future__ import annotations

import calendar
import random
from datetime import date, datetime, time, timedelta

import frappe
from frappe.utils import get_datetime, getdate, nowdate

EMPLOYEE = "HR-EMP-00004"
SHIFT = "Normal"
DEVICE_ID = "Auto Attendance"
REFERENCE_CHECKIN = "EMP-CKIN-06-2026-000076"
DEFAULT_LATITUDE = 41.1089371
DEFAULT_LONGITUDE = 28.7635965
DEFAULT_GEOLOCATION = (
	'{"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}, '
	'"geometry": {"type": "Point", "coordinates": [28.7635965, 41.1089371]}}]}'
)


def checkin_location() -> dict:
	return {
		"latitude": DEFAULT_LATITUDE,
		"longitude": DEFAULT_LONGITUDE,
		"geolocation": DEFAULT_GEOLOCATION,
	}


def is_saudi_workday(d: date) -> bool:
	# Saudi work week: Sunday–Thursday (Fri/Sat off).
	return d.weekday() in (6, 0, 1, 2, 3)


def _seeded_random_time(d: date, kind: str, start_h: int, start_m: int, end_h: int, end_m: int) -> datetime:
	rng = random.Random(f"{EMPLOYEE}:{d.isoformat()}:{kind}")
	start = datetime.combine(d, time(start_h, start_m))
	end = datetime.combine(d, time(end_h, end_m))
	delta = int((end - start).total_seconds())
	return start + timedelta(seconds=rng.randint(0, max(delta, 0)))


def _live_random_time(d: date, start_h: int, start_m: int, end_h: int, end_m: int) -> datetime:
	start = datetime.combine(d, time(start_h, start_m))
	end = datetime.combine(d, time(end_h, end_m))
	delta = int((end - start).total_seconds())
	return start + timedelta(seconds=random.randint(0, max(delta, 0)))


def random_checkin_time(d: date, *, seeded: bool = False) -> datetime:
	if seeded:
		return _seeded_random_time(d, "in", 8, 0, 9, 0)
	return _live_random_time(d, 8, 0, 9, 0)


def random_checkout_time(d: date, in_time: datetime, *, seeded: bool = False) -> datetime:
	if seeded:
		out_time = _seeded_random_time(d, "out", 17, 0, 19, 0)
	else:
		out_time = _live_random_time(d, 17, 0, 19, 0)
	if out_time <= in_time:
		out_time = in_time + timedelta(hours=8)
	return out_time


def _employee_details() -> dict:
	return frappe.db.get_value(
		"Employee",
		EMPLOYEE,
		["employee_name", "company", "department"],
		as_dict=True,
	)


def _day_checkins(attendance_date: date) -> list[dict]:
	return frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": EMPLOYEE,
			"time": ["between", [f"{attendance_date} 00:00:00", f"{attendance_date} 23:59:59"]],
		},
		fields=["name", "time", "log_type", "attendance"],
		order_by="time asc",
	)


def _attendance_name(attendance_date: date) -> str | None:
	return frappe.db.get_value(
		"Attendance",
		{"employee": EMPLOYEE, "attendance_date": attendance_date, "docstatus": ["<", 2]},
		"name",
	)


def _create_checkin(attendance_date: date, checkin_time: datetime, log_type: str) -> str:
	emp = _employee_details()
	location = checkin_location()
	doc = frappe.get_doc(
		{
			"doctype": "Employee Checkin",
			"employee": EMPLOYEE,
			"employee_name": emp.employee_name,
			"time": checkin_time,
			"log_type": log_type,
			"device_id": DEVICE_ID,
			"skip_auto_attendance": 1,
			**location,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def _link_checkins(checkin_names: list[str], attendance_name: str) -> None:
	for name in checkin_names:
		frappe.db.set_value("Employee Checkin", name, "attendance", attendance_name)


def _upsert_attendance(
	attendance_date: date,
	in_time: datetime | None,
	out_time: datetime | None,
	existing_name: str | None = None,
	*,
	include_checkout: bool = True,
) -> str:
	emp = _employee_details()
	values = {
		"status": "Present",
		"shift": SHIFT,
		"in_time": in_time,
	}
	if include_checkout:
		values["out_time"] = out_time

	if existing_name:
		frappe.db.set_value("Attendance", existing_name, values, update_modified=True)
		return existing_name

	doc = frappe.get_doc(
		{
			"doctype": "Attendance",
			"employee": EMPLOYEE,
			"employee_name": emp.employee_name,
			"company": emp.company,
			"department": emp.department,
			"attendance_date": attendance_date,
			**values,
		}
	)
	doc.insert(ignore_permissions=True)
	doc.submit()
	return doc.name


def ensure_day_attendance(
	attendance_date: date,
	*,
	include_checkout: bool = True,
	seeded: bool = False,
	create_if_missing: bool = True,
) -> dict:
	d = getdate(attendance_date)
	if not is_saudi_workday(d):
		return {"date": str(d), "skipped": True, "reason": "weekend"}

	checkins = _day_checkins(d)
	in_logs = [c for c in checkins if c.log_type == "IN"]
	out_logs = [c for c in checkins if c.log_type == "OUT"]
	att_name = _attendance_name(d)
	created_checkins: list[str] = []

	if not att_name and not in_logs and not create_if_missing:
		return {"date": str(d), "skipped": True, "reason": "no_record"}

	in_time = get_datetime(in_logs[0].time) if in_logs else None
	out_time = get_datetime(out_logs[-1].time) if out_logs else None

	if not in_time and att_name:
		att_in = frappe.db.get_value("Attendance", att_name, "in_time")
		if att_in:
			in_time = get_datetime(att_in)

	if include_checkout and not out_time and att_name:
		att_out = frappe.db.get_value("Attendance", att_name, "out_time")
		if att_out:
			out_time = get_datetime(att_out)

	if not in_time:
		in_time = random_checkin_time(d, seeded=seeded)
		created_checkins.append(_create_checkin(d, in_time, "IN"))

	if include_checkout and not out_time and in_time:
		out_time = random_checkout_time(d, in_time, seeded=seeded)
		created_checkins.append(_create_checkin(d, out_time, "OUT"))

	att_name = _upsert_attendance(
		d, in_time, out_time if include_checkout else None, att_name, include_checkout=include_checkout
	)
	if created_checkins:
		_link_checkins(created_checkins, att_name)

	return {
		"date": str(d),
		"attendance": att_name,
		"in_time": str(in_time) if in_time else None,
		"out_time": str(out_time) if include_checkout and out_time else None,
		"created_checkins": created_checkins,
	}


def run_daily_auto_checkin() -> dict:
	today = getdate(nowdate())
	if not is_saudi_workday(today):
		return {"skipped": True, "reason": "weekend", "date": str(today)}

	if any(c.log_type == "IN" for c in _day_checkins(today)):
		return {"skipped": True, "reason": "checkin_exists", "date": str(today)}

	result = ensure_day_attendance(today, include_checkout=False, seeded=False, create_if_missing=True)
	frappe.db.commit()
	return result


def run_daily_auto_checkout() -> dict:
	today = getdate(nowdate())
	if not is_saudi_workday(today):
		return {"skipped": True, "reason": "weekend", "date": str(today)}

	checkins = _day_checkins(today)
	if not any(c.log_type == "IN" for c in checkins):
		return {"skipped": True, "reason": "no_checkin", "date": str(today)}
	if any(c.log_type == "OUT" for c in checkins):
		return {"skipped": True, "reason": "checkout_exists", "date": str(today)}

	result = ensure_day_attendance(today, include_checkout=True, seeded=False, create_if_missing=True)
	frappe.db.commit()
	return result


def fix_employee_month_attendance(year: int | None = None, month: int | None = None) -> list[dict]:
	today = getdate(nowdate())
	year = year or today.year
	month = month or today.month
	results = []

	for day in range(1, calendar.monthrange(year, month)[1] + 1):
		d = date(year, month, day)
		if d > today:
			continue
		if not is_saudi_workday(d):
			continue
		results.append(
			ensure_day_attendance(
				d,
				include_checkout=d < today,
				seeded=True,
				create_if_missing=True,
			)
		)

	frappe.db.commit()
	return results


def sync_employee_checkin_locations() -> dict:
	"""Align all Ahmed check-in coordinates with REFERENCE_CHECKIN."""
	location = checkin_location()
	names = frappe.get_all("Employee Checkin", filters={"employee": EMPLOYEE}, pluck="name")
	updated = 0

	for name in names:
		frappe.db.set_value(
			"Employee Checkin",
			name,
			location,
			update_modified=False,
		)
		updated += 1

	frappe.db.commit()
	return {
		"employee": EMPLOYEE,
		"reference_checkin": REFERENCE_CHECKIN,
		"updated": updated,
		**location,
	}


def ensure_scheduled_jobs():
	"""Register cron jobs after deploy (sync_jobs is normally run on migrate)."""
	from frappe.core.doctype.scheduled_job_type.scheduled_job_type import sync_jobs

	sync_jobs()
