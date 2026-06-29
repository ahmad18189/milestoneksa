# -*- coding: utf-8 -*-
# Copyright (c) 2026, ahmed and contributors

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_years, get_datetime, get_url, getdate, now_datetime, today
from frappe.utils.verified_command import get_signed_params, verify_request

from milestoneksa.payroll.ksa_end_of_service import (
	SEPARATION_CONTRACT_EXPIRY,
	compute_final_eos,
)

ALLOWED_ACTION_ROLES = ("COO", "CEO", "HR Manager", "System Manager")
ACTION_EXTEND = "extend"
ACTION_END = "end"
ACTION_LABELS = {
	ACTION_EXTEND: _("Extend Contract"),
	ACTION_END: _("End Contract"),
}
APPLY_METHOD = (
	"/api/method/milestoneksa.milestoneksa.doctype.employee_contract_end_review"
	".employee_contract_end_review.apply_contract_action"
)
CONFIRM_METHOD = (
	"/api/method/milestoneksa.milestoneksa.doctype.employee_contract_end_review"
	".employee_contract_end_review.confirm_contract_action"
)


class EmployeeContractEndReview(Document):
	def before_insert(self):
		existing = get_existing_review(self.employee, self.contract_end_date)
		if existing:
			frappe.throw(
				_("Employee Contract End Review already exists: {0}").format(
					frappe.bold(existing)
				)
			)

	def validate(self):
		self._sync_from_employee()
		self._compute_days_to_expiry()

	def _sync_from_employee(self):
		if not self.employee:
			return
		emp = frappe.get_doc("Employee", self.employee)
		if not self.contract_end_date:
			self.contract_end_date = emp.contract_end_date
		if not self.date_of_joining:
			self.date_of_joining = emp.date_of_joining

	def _compute_days_to_expiry(self):
		if self.contract_end_date:
			self.days_to_expiry = (getdate(self.contract_end_date) - getdate(today())).days
		else:
			self.days_to_expiry = 0


def contract_review_exists(employee: str, contract_end_date) -> str | None:
	"""Return review name if any non-cancelled review exists for this employee + contract end."""
	if not contract_end_date:
		return None

	return frappe.db.get_value(
		"Employee Contract End Review",
		{
			"employee": employee,
			"contract_end_date": getdate(contract_end_date),
			"status": ["!=", "Cancelled"],
		},
		"name",
		order_by="creation desc",
	)


def pending_review_for_employee(employee: str) -> str | None:
	"""Return the active pending review for an employee, if any."""
	return frappe.db.get_value(
		"Employee Contract End Review",
		{"employee": employee, "status": "Pending Review"},
		"name",
		order_by="creation desc",
	)


def get_existing_review(employee: str, contract_end_date=None) -> str | None:
	"""
	Find an existing review to reuse — same contract cycle first, then any pending review.
	Avoids duplicate reviews and keeps email actions on the original document.
	"""
	if contract_end_date:
		existing = contract_review_exists(employee, contract_end_date)
		if existing:
			return existing

	return pending_review_for_employee(employee)


def pending_review_exists(employee: str, contract_end_date) -> str | None:
	"""Return review name if a Pending Review already exists for this employee + contract end."""
	if not contract_end_date:
		return pending_review_for_employee(employee)

	return frappe.db.get_value(
		"Employee Contract End Review",
		{
			"employee": employee,
			"contract_end_date": getdate(contract_end_date),
			"status": "Pending Review",
		},
		"name",
	)


def create_pending_review(employee: str, contract_end_date) -> Document:
	"""Create a new Pending Review for the employee contract cycle."""
	emp = frappe.get_doc("Employee", employee)
	contract_end = getdate(contract_end_date or emp.contract_end_date)
	if not contract_end:
		frappe.throw(_("Employee {0} has no Contract End Date.").format(emp.employee_name))

	existing = get_existing_review(employee, contract_end)
	if existing:
		return frappe.get_doc("Employee Contract End Review", existing)

	doc = frappe.get_doc(
		{
			"doctype": "Employee Contract End Review",
			"employee": employee,
			"contract_end_date": contract_end,
			"date_of_joining": emp.date_of_joining,
			"status": "Pending Review",
			"separation_reason": SEPARATION_CONTRACT_EXPIRY,
			"alert_date": today(),
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


def get_or_create_review(employee: str, contract_end_date=None) -> Document:
	"""Return existing review for this contract cycle or create a new pending one."""
	emp = frappe.get_doc("Employee", employee)
	contract_end = contract_end_date or emp.contract_end_date
	if not contract_end:
		frappe.throw(_("Employee {0} has no Contract End Date.").format(emp.employee_name))

	existing = get_existing_review(employee, contract_end)
	if existing:
		return frappe.get_doc("Employee Contract End Review", existing)

	return create_pending_review(employee, contract_end)


def get_contract_action_links(review, user: str) -> dict:
	"""Signed email action URLs (Workflow Actions pattern)."""
	if isinstance(review, str):
		review = frappe.get_doc("Employee Contract End Review", review)
	return {
		"extend_link": get_contract_action_url(ACTION_EXTEND, review, user),
		"end_link": get_contract_action_url(ACTION_END, review, user),
		"review_link": f"{get_url()}/app/employee-contract-end-review/{review.name}",
	}


def get_contract_action_url(action: str, doc, user: str) -> str:
	params = {
		"action": action,
		"name": doc.name,
		"current_status": doc.status,
		"user": user,
		"last_modified": doc.modified,
	}
	return get_url(APPLY_METHOD + "?" + get_signed_params(params))


def get_confirm_contract_action_url(action: str, name: str, user: str) -> str:
	params = {
		"action": action,
		"name": name,
		"user": user,
	}
	return get_url(CONFIRM_METHOD + "?" + get_signed_params(params))


def _user_can_act(user: str) -> bool:
	if not user or user == "Guest":
		return False
	return bool(set(frappe.get_roles(user)) & set(ALLOWED_ACTION_ROLES))


@frappe.whitelist(allow_guest=True)
def apply_contract_action(action, name, current_status, user=None, last_modified=None):
	"""Step 1: verify signed link and show confirmation page."""
	if not verify_request():
		return

	doc = frappe.get_doc("Employee Contract End Review", name)
	if doc.status != current_status:
		return_link_expired_page(doc)
		return

	if user and not _user_can_act(user):
		frappe.respond_as_web_page(
			_("Not Permitted"),
			_("You are not authorized to perform this action."),
			indicator_color="red",
		)
		return

	action_link = get_confirm_contract_action_url(action, name, user)
	alert_doc_change = bool(
		last_modified and get_datetime(doc.modified) != get_datetime(last_modified)
	)
	return_confirmation_page(doc, action, action_link, alert_doc_change=alert_doc_change)


@frappe.whitelist(allow_guest=True)
def confirm_contract_action(action, name, user=None):
	"""Step 2: execute extend/end after confirmation."""
	if not verify_request():
		return

	logged_in_user = frappe.session.user
	if logged_in_user == "Guest" and user:
		if not _user_can_act(user):
			frappe.respond_as_web_page(
				_("Not Permitted"),
				_("You are not authorized to perform this action."),
				indicator_color="red",
			)
			return
		frappe.set_user(user)

	try:
		if action == ACTION_EXTEND:
			result = _execute_extend_contract(name, frappe.session.user)
		elif action == ACTION_END:
			result = _execute_end_contract(name, frappe.session.user)
		else:
			frappe.throw(_("Unknown action: {0}").format(action))

		frappe.db.commit()
		return_success_page(name, action, result)
	finally:
		if logged_in_user == "Guest":
			frappe.set_user(logged_in_user)


def return_confirmation_page(doc, action, action_link, alert_doc_change=False):
	frappe.respond_as_web_page(
		title=None,
		html=None,
		indicator_color="blue",
		template="confirm_contract_action",
		context={
			"action_label": ACTION_LABELS.get(action, action),
			"employee_name": doc.employee_name,
			"review_link": f"{get_url()}/app/employee-contract-end-review/{doc.name}",
			"action_link": action_link,
			"alert_doc_change": alert_doc_change,
		},
	)


def return_link_expired_page(doc):
	frappe.respond_as_web_page(
		_("Link Expired"),
		_("Review {0} is already set to status {1}.").format(
			frappe.bold(doc.name),
			frappe.bold(doc.status),
		),
		indicator_color="orange",
	)


def return_success_page(name, action, result):
	doc = frappe.get_doc("Employee Contract End Review", name)
	if action == ACTION_EXTEND:
		message = _("Contract for {0} extended to {1}.").format(
			frappe.bold(doc.employee_name),
			frappe.bold(result.get("new_contract_end_date")),
		)
	else:
		message = _("Contract ended for {0}. Final EOS: {1} SAR.").format(
			frappe.bold(doc.employee_name),
			frappe.bold(result.get("final_eos_amount")),
		)

	frappe.respond_as_web_page(_("Success"), message, indicator_color="green")


def _execute_extend_contract(name: str, acting_user: str) -> dict:
	doc = frappe.get_doc("Employee Contract End Review", name)
	if doc.status != "Pending Review":
		frappe.throw(_("Only Pending Review records can be extended."))

	emp = frappe.get_doc("Employee", doc.employee)
	previous_end = getdate(doc.contract_end_date or emp.contract_end_date)
	new_end = add_years(previous_end, 1)

	doc.previous_contract_end_date = previous_end
	doc.new_contract_end_date = new_end
	doc.extended_on = now_datetime()
	doc.extended_by = acting_user
	doc.status = "Extended"
	doc.save(ignore_permissions=True)

	emp.contract_end_date = new_end
	emp.flags.ignore_validate = True
	emp.save(ignore_permissions=True)

	return {
		"status": doc.status,
		"new_contract_end_date": str(new_end),
	}


def _execute_end_contract(name: str, acting_user: str) -> dict:
	doc = frappe.get_doc("Employee Contract End Review", name)
	if doc.status != "Pending Review":
		frappe.throw(_("Only Pending Review records can be ended."))

	separation_reason = doc.separation_reason or SEPARATION_CONTRACT_EXPIRY
	eos = compute_final_eos(
		doc.employee,
		doc.contract_end_date,
		separation_reason=separation_reason,
		unpaid_leave_days=None,
	)

	doc.last_actual_wage = eos["last_actual_wage"]
	doc.salary_slip_reference = eos.get("salary_slip_reference")
	doc.average_monthly_wage = eos.get("average_monthly_wage")
	doc.wage_source = eos.get("wage_source")
	doc.unpaid_leave_days = eos["unpaid_leave_days"]
	doc.paid_leave_days_taken = eos.get("paid_leave_days_taken")
	doc.years_of_service = eos["years_of_service"]
	doc.article_84_full_amount = eos["article_84_full_amount"]
	doc.article_85_factor = eos["article_85_factor"]
	doc.final_eos_amount = eos["final_eos_amount"]
	doc.eos_calculation_notes = eos["eos_calculation_notes"]
	doc.ended_on = now_datetime()
	doc.ended_by = acting_user
	doc.status = "End Contract"
	doc.save(ignore_permissions=True)

	return {
		"status": doc.status,
		"final_eos_amount": doc.final_eos_amount,
	}


@frappe.whitelist()
def extend_contract(name: str):
	"""Desk form action: extend contract by 1 year."""
	frappe.only_for(ALLOWED_ACTION_ROLES)
	result = _execute_extend_contract(name, frappe.session.user)
	frappe.db.commit()
	return {
		**result,
		"message": _("Contract extended to {0}.").format(result["new_contract_end_date"]),
	}


@frappe.whitelist()
def end_contract(name: str):
	"""Desk form action: end contract and compute EOS."""
	frappe.only_for(ALLOWED_ACTION_ROLES)
	result = _execute_end_contract(name, frappe.session.user)
	frappe.db.commit()
	return {
		**result,
		"message": _("Contract end processed. Final EOS: {0} SAR.").format(result["final_eos_amount"]),
	}
