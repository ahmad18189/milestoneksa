# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

# Map last transaction action -> parent status
ACTION_TO_STATUS = {
	"Created": "Available",
	"Assigned": "Assigned",
	"Returned": "Available",
	"Disabled": "Disabled",
}

class EmployeeCustody(Document):
	def before_insert(self):
		# Ensure we start with a Created row
		if not self.transactions:
			row = self.append("transactions", {})
			row.action = "Created"
			row.transaction_date = frappe.utils.now_datetime()

	def validate(self):
		# 1) Enforce row-level requirements
		self._validate_transaction_rows()

		# 2) Drive parent status from the last transaction
		self._sync_status_from_last_action()

		# 3) Guard: same Asset cannot be Assigned in two different custodies
		self._prevent_asset_double_assignment()

	def _last_action(self):
		if not self.transactions:
			return None
		return self.transactions[-1].action

	def _sync_status_from_last_action(self):
		last = self._last_action()
		new_status = ACTION_TO_STATUS.get(last)
		# If something odd, default to Available
		self.status = new_status or "Available"
		if last == "Assigned":
			self.current_employee = self.transactions[-1].employee
		else:
			self.current_employee = None


	def _validate_transaction_rows(self):
		for i, row in enumerate(self.transactions, start=1):
			act = (row.action or "").strip()
			if not act:
				frappe.throw(_("Row {0}: Action is required").format(i))

			# Ensure transaction_date exists
			if not row.transaction_date:
				frappe.throw(_("Row {0}: Date is required").format(i))

			# Per-action requirements
			if act == "Assigned":
				if not row.employee:
					frappe.throw(_("Row {0}: Employee is required for 'Assigned'").format(i))

	def _prevent_asset_double_assignment(self):
		# Only check when this custody is currently Assigned and has an Asset
		if self.status != "Assigned" or not self.asset:
			return

		conflict = frappe.db.sql("""
			select name
			from `tabEmployee Custody`
			where name != %s
			  and asset = %s
			  and status = 'Assigned'
			limit 1
		""", (self.name or "New Custody", self.asset))

		if conflict:
			frappe.throw(_("Asset {0} is already assigned in custody {1}").format(self.asset, conflict[0][0]))

	# Convenience actions (optional, for buttons)
	@frappe.whitelist()
	def add_assigned(self, employee: str, transaction_date: str, note: str = None):
		row = self.append("transactions", {})
		row.action = "Assigned"
		row.employee = employee
		row.transaction_date = transaction_date
		row.condition_note = note
		self.save()
		frappe.msgprint(_("Added 'Assigned'"), alert=True)

	@frappe.whitelist()
	def add_returned(self, transaction_date: str, note: str = None):
		row = self.append("transactions", {})
		row.action = "Returned"
		row.transaction_date = transaction_date
		row.condition_note = note
		self.save()
		frappe.msgprint(_("Added 'Returned'"), alert=True)

	@frappe.whitelist()
	def add_disabled(self, transaction_date: str, note: str = None):
		row = self.append("transactions", {})
		row.action = "Disabled"
		row.transaction_date = transaction_date
		row.condition_note = note
		self.save()
		frappe.msgprint(_("Added 'Disabled'"), alert=True)


# Keep these at bottom of file


@frappe.whitelist()
def assign_available_to_employee(custody: str, employee: str, transaction_datetime: str, note: str = None):
	"""Assign a selected AVAILABLE custody to an employee (invoked from Employee UI)."""
	doc = frappe.get_doc("Employee Custody", custody)
	doc.add_assigned(employee=employee, transaction_date=transaction_datetime, note=note)
	return {"ok": True, "custody": doc.name}

@frappe.whitelist()
def return_assigned_custody(custody: str, transaction_datetime: str, note: str = None):
	"""Return an ASSIGNED custody (invoked from Employee UI)."""
	doc = frappe.get_doc("Employee Custody", custody)
	doc.add_returned(transaction_date=transaction_datetime, note=note)
	return {"ok": True, "custody": doc.name}

@frappe.whitelist()
def list_assigned_for_employee(employee: str):
	"""
	Return currently assigned custodies for an employee.
	last_activity_date is computed from the child table's max(transaction_date).
	"""
	if not employee:
		return []

	rows = frappe.db.sql("""
		SELECT
			ec.name,
			ec.custody_name,
			ec.asset,
			ec.item_code,
			ec.serial_no,
			(
				SELECT MAX(ect.transaction_date)
				FROM `tabEmployee Custody Transaction` ect
				WHERE ect.parent = ec.name
			) AS last_activity_date
		FROM `tabEmployee Custody` ec
		WHERE ec.status = 'Assigned'
		  AND ec.current_employee = %s
		ORDER BY last_activity_date DESC, ec.modified DESC
	""", (employee,), as_dict=True)

	return rows