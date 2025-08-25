# -*- coding: utf-8 -*-
import json
import frappe
from frappe import _
from frappe.utils import now_datetime

def _get_session_employee():
	user = frappe.session.user
	emp = frappe.db.get_value(
		"Employee",
		{"user_id": user, "status": "Active"},
		["name", "employee_name"],
		as_dict=True,
	)
	if not emp:
		frappe.throw(_("No active Employee linked to user {0}.").format(user))
	return emp

@frappe.whitelist()
def get_next_action():
	emp = _get_session_employee()
	last = frappe.get_all(
		"Employee Checkin",
		filters={"employee": emp.name},
		fields=["name", "log_type", "time"],
		order_by="time desc",
		limit=1,
	)
	next_action = "IN" if not last or last[0].log_type == "OUT" else "OUT"
	return {"employee": emp, "last": (last[0] if last else None), "next_action": next_action}

@frappe.whitelist()
def quick_checkin(log_type, latitude=None, longitude=None, geolocation=None, time=None):
	"""Record an Employee Checkin for the current user. Latitude & Longitude are REQUIRED."""
	emp = _get_session_employee()

	log_type = (log_type or "IN").upper()
	if log_type not in ("IN", "OUT"):
		frappe.throw(_("Invalid log_type: {0}").format(log_type))

	# required coords
	if latitude in (None, "") or longitude in (None, ""):
		frappe.throw(_("Latitude and longitude are required for checking in/out. Please allow location access and try again."))

	try:
		lat = float(latitude); lng = float(longitude)
	except Exception:
		frappe.throw(_("Latitude and longitude must be numeric values."))

	if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lng <= 180.0):
		frappe.throw(_("Invalid coordinates. Latitude must be between -90 and 90; Longitude between -180 and 180."))

	# build a valid GeoJSON if not provided or invalid
	def make_geojson(lat, lng):
		return json.dumps({
			"type": "FeatureCollection",
			"features": [{
				"type": "Feature",
				"properties": {},
				"geometry": {"type": "Point", "coordinates": [lng, lat]}
			}]
		})

	if geolocation and isinstance(geolocation, str):
		try:
			json.loads(geolocation)
		except Exception:
			geolocation = make_geojson(lat, lng)
	else:
		geolocation = make_geojson(lat, lng)

	doc = frappe.get_doc({
		"doctype": "Employee Checkin",
		"employee": emp.name,
		"employee_name": emp.employee_name,
		"log_type": log_type,
		"time": time or now_datetime(),
		"latitude": lat,
		"longitude": lng,
		"geolocation": geolocation,
	})
	doc.insert(ignore_permissions=False)
	frappe.db.commit()
	return {"name": doc.name, "log_type": doc.log_type, "time": doc.time}
