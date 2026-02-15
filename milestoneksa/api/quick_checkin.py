# -*- coding: utf-8 -*-
import frappe
from frappe import _
from datetime import datetime, date, timedelta, time as pytime
from frappe.utils import get_datetime, getdate

# -------------------------------------------------------------------
# Public API used by your page (unchanged signature)
# -------------------------------------------------------------------

@frappe.whitelist()
def get_next_action(filters=None):
    """Return next action (IN/OUT), employee context and last log.

    Rule:
    - If the most recent log is OUT -> next is IN.
    - If the most recent log is IN:
        - same calendar day as 'now' -> next is OUT
        - previous day (or older)     -> next is IN   (user forgot to check out)
    """
    user = frappe.session.user
    employee = frappe.db.get_value(
        "Employee",
        {"user_id": user},
        ["name", "employee_name"],
        as_dict=True,
    )
    if not employee:
        frappe.throw(_("No Employee linked to user {0}").format(user))

    last = frappe.db.get_all(
        "Employee Checkin",
        fields=["name", "log_type", "time"],
        filters={"employee": employee.name},
        order_by="time desc",
        limit=1,
    )

    next_action = "IN"  # default

    if last:
        last_log = last[0]
        from frappe.utils import now_datetime, getdate
        today = getdate(now_datetime())
        last_day = getdate(last_log.time)

        if last_log.log_type == "IN":
            # Only ask to check OUT if that IN is from *today*
            next_action = "OUT" if last_day == today else "IN"
        else:
            # Last was OUT -> always IN next
            next_action = "IN"

    return {
        "employee": employee,
        "last": last[0] if last else None,
        "next_action": next_action,
    }



@frappe.whitelist()
def quick_checkin(log_type, latitude=None, longitude=None, geolocation=None, ts=None):
    """
    Create Employee Checkin and resolve shift at creation.
    Args:
        log_type: "IN" or "OUT"
        latitude, longitude: optional floats
        geolocation: optional GeoJSON FeatureCollection (string)
        ts: optional timestamp string (YYYY-MM-DD HH:mm:ss). Defaults to now.
    """
    user = frappe.session.user
    emp = frappe.db.get_value("Employee", {"user_id": user}, ["name", "employee_name", "default_shift"], as_dict=True)
    if not emp:
        frappe.throw(_("No Employee linked to user {0}").format(user))

    when = get_datetime(ts) if ts else get_datetime(frappe.utils.now())

    # Create the checkin document
    doc = frappe.new_doc("Employee Checkin")
    doc.employee = emp.name
    doc.employee_name = emp.employee_name
    doc.log_type = "IN" if str(log_type).upper() == "IN" else "OUT"
    doc.time = when

    # optional location
    if latitude is not None:
        try: doc.latitude = float(latitude)
        except Exception: pass
    if longitude is not None:
        try: doc.longitude = float(longitude)
        except Exception: pass
    if geolocation:
        doc.geolocation = geolocation

    # Resolve and set shift fields BEFORE insert
    shift_info = resolve_shift_for(emp.name, when, emp.default_shift)
    if shift_info:
        doc.shift = shift_info.get("shift")
        doc.shift_start = shift_info.get("shift_start")
        doc.shift_end = shift_info.get("shift_end")

    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "name": doc.name,
        "shift": getattr(doc, "shift", None),
        "shift_start": getattr(doc, "shift_start", None),
        "shift_end": getattr(doc, "shift_end", None),
    }

# -------------------------------------------------------------------
# Shift resolution helpers (no HRMS internals needed)
# -------------------------------------------------------------------

def resolve_shift_for(employee: str, when: datetime, default_shift: str | None = None):
    """
    Resolve the applicable shift for an employee at a given datetime.

    Priority:
    1) Active Shift Assignment covering the date
    2) Employee.default_shift (if set)
    3) None (no shift)

    Returns dict {shift, shift_start, shift_end} or None
    """
    the_day = getdate(when)

    # 1) Look for Shift Assignment covering the date
    assignment = frappe.db.get_all(
        "Shift Assignment",
        fields=["name", "shift_type", "start_date", "end_date"],
        filters={
            "employee": employee,
            "docstatus": ["<", 2],
            "start_date": ["<=", the_day],
            # end_date may be null (open ended)
        },
        order_by="start_date desc, creation desc",
        limit=50,
    )

    chosen_shift_type = None
    for a in assignment:
        # include if end_date is null or the_day <= end_date
        if not a.get("end_date") or the_day <= a.get("end_date"):
            chosen_shift_type = a.get("shift_type")
            break

    # 2) Fall back to Employee.default_shift (Link to Shift Type)
    if not chosen_shift_type and default_shift:
        chosen_shift_type = default_shift

    if not chosen_shift_type:
        return None

    st = frappe.db.get_value(
        "Shift Type",
        chosen_shift_type,
        ["name", "start_time", "end_time"],
        as_dict=True,
    )
    if not st or not st.start_time or not st.end_time:
        return {"shift": chosen_shift_type, "shift_start": None, "shift_end": None}

    shift_start_dt, shift_end_dt = compose_shift_datetimes(the_day, st.start_time, st.end_time)

    return {
        "shift": st.name,
        "shift_start": shift_start_dt,
        "shift_end": shift_end_dt,
    }


def compose_shift_datetimes(the_day: date, start_time: str | datetime | pytime, end_time: str | datetime | pytime):
    """
    Combine a date with start/end times to datetimes.
    Handles overnight shifts (end < start) by rolling end +1 day.
    """
    def to_pytime(val):
        if isinstance(val, pytime):
            return val
        if isinstance(val, datetime):
            return pytime(val.hour, val.minute, val.second, val.microsecond)
        # val is "HH:MM:SS"
        h, m, s = [int(x) for x in str(val).split(":")]
        return pytime(h, m, s)

    st = to_pytime(start_time)
    et = to_pytime(end_time)

    start_dt = datetime.combine(the_day, st)
    end_dt = datetime.combine(the_day, et)
    if end_dt <= start_dt:
        end_dt += timedelta(days=1)  # overnight

    return start_dt, end_dt
