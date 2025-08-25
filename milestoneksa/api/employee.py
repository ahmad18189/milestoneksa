# -*- coding: utf-8 -*-
# File: milestoneksa/api/employee.py

import frappe
from frappe import _
from frappe.utils import getdate, flt


def validate_employee(doc, method=None):
	"""
	Main validator for Employee:
	- Recompute custom_total_cost from Residence Costs child table.
	- Validate residence start/end dates on the parent.
	- Validate Sponsorship Transfer rows (required fields, order, overlap).
	"""
	compute_residence_total(doc)
	validate_residence_dates(doc)
	validate_sponsorship_dates(doc)


def compute_residence_total(doc):
	"""Recalculate total from child rows and set custom_total_cost."""
	total = 0.0
	for row in (doc.custom_residence_costs or []):
		total += flt(getattr(row, "amount", 0), 2)
	doc.custom_total_cost = total


def validate_residence_dates(doc):
	"""Validate Employee custom residence start/end dates on the parent doc."""
	start = getattr(doc, "custom_residence_start_date", None)
	end = getattr(doc, "custom_residence_end_date", None)

	# If either is set, both must be set
	if bool(start) ^ bool(end):
		frappe.throw(_("Residence period is incomplete. Please set both Start and End dates."))

	if start and end:
		s = getdate(start)
		e = getdate(end)
		if e < s:
			frappe.throw(
				_("Residence End Date cannot be before Start Date (Start: {0}, End: {1}).")
				.format(s.strftime("%Y-%m-%d"), e.strftime("%Y-%m-%d"))
			)


def validate_sponsorship_dates(doc):
	"""
	Validate child 'Sponsorship Transfer' rows:
	- Required dates per row
	- End >= Start per row
	- No overlapping periods across rows (inclusive check)
	"""
	rows = list(doc.get("custom_sponsorship_transfer") or [])
	if not rows:
		return

	# Per-row required & range checks
	for r in rows:
		if not r.sponsorship_start_date or not r.sponsorship_end_date:
			frappe.throw(_("Row #{0}: Sponsorship Start and End dates are required.").format(r.idx))

		s = getdate(r.sponsorship_start_date)
		e = getdate(r.sponsorship_end_date)
		if e < s:
			frappe.throw(
				_("Row #{0}: Sponsorship End Date cannot be before Start Date (Start: {1}, End: {2}).")
				.format(r.idx, s.strftime("%Y-%m-%d"), e.strftime("%Y-%m-%d"))
			)

	# Overlap detection (sort by start date, then ensure each starts after the previous ends)
	sortable = [
		(getdate(r.sponsorship_start_date), getdate(r.sponsorship_end_date), r)
		for r in rows
	]
	sortable.sort(key=lambda x: (x[0], x[1]))

	prev_end = None
	prev_row = None
	for s, e, r in sortable:
		if prev_end and s <= prev_end:
			# Overlap found (inclusive): current start is on/before previous end
			frappe.throw(
				_("Sponsorship periods overlap between Row #{0} (ends {1}) and Row #{2} (starts {3}). "
				  "Please adjust the dates.")
				.format(
					prev_row.idx,
					prev_end.strftime("%Y-%m-%d"),
					r.idx,
					s.strftime("%Y-%m-%d")
				)
			)
		prev_end = e
		prev_row = r

	# OPTIONAL: require residence period be covered by at least one sponsorship period
	# Uncomment if desired.
	# res_start = getattr(doc, "custom_residence_start_date", None)
	# res_end = getattr(doc, "custom_residence_end_date", None)
	# if res_start and res_end:
	# 	rs, re = getdate(res_start), getdate(res_end)
	# 	covered = any((s <= rs and re <= e) for s, e, _ in sortable)
	# 	if not covered:
	# 		frappe.throw(
	# 			_("Residence period ({0} → {1}) is not fully covered by any single Sponsorship Transfer period.")
	# 			.format(rs.strftime("%Y-%m-%d"), re.strftime("%Y-%m-%d"))
	# 		)
