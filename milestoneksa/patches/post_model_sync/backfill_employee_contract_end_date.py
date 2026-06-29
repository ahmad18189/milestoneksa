"""Backfill Employee.contract_end_date from date_of_joining where contract end is empty."""
from __future__ import annotations

import frappe

from milestoneksa.api.employee import compute_contract_end_date


def execute():
	employees = frappe.get_all(
		"Employee",
		filters={
			"date_of_joining": ["is", "set"],
			"contract_end_date": ["is", "not set"],
		},
		fields=["name", "date_of_joining"],
	)

	for emp in employees:
		contract_end = compute_contract_end_date(emp.date_of_joining)
		if not contract_end:
			continue

		frappe.db.set_value(
			"Employee",
			emp.name,
			"contract_end_date",
			contract_end,
			update_modified=False,
		)

	if employees:
		frappe.db.commit()
