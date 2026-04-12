# Copyright (c) 2025, ahmed and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_url, now
from frappe.utils.data import escape_html, fmt_money


def get_transition_action_for_states(doctype: str, from_state: str, to_state: str) -> str:
	"""Return the Workflow transition action label (e.g. Approve, Reject) for from_state -> to_state."""
	try:
		workflows = frappe.get_all(
			"Workflow",
			filters={"document_type": doctype},
			fields=["name"],
			limit=1,
		)
		if not workflows:
			return ""
		workflow_doc = frappe.get_doc("Workflow", workflows[0].name)
		for t in workflow_doc.transitions:
			if t.state == from_state and t.next_state == to_state:
				return t.action or ""
	except Exception as e:
		frappe.log_error(f"Error getting transition action: {e}")
	return ""


def get_employee_name_for_user(user: str) -> str:
	"""Return display name for user: User.full_name or Employee name if linked."""
	if not user:
		return ""
	name = frappe.db.get_value("User", user, "full_name")
	if name:
		return name
	emp = frappe.db.get_value("Employee", {"user_id": user}, "employee_name")
	return emp or user


class PaymentApprovalRequest(Document):
	def validate(self):
		"""Standard validation hook and workflow activity log.

		Note:
			Previously this method was forcing `workflow_state = "Pending CEO Approval"`
			for users with the COO role on new documents. That caused Frappe to raise
			a \"workflow state transition not allowed from Draft to Pending CEO Approval\"
			error, because there is no corresponding transition configured in the
			`Payment Approval Request` workflow.

			The special‑case behaviour has been removed so that all new requests
			start in the normal **Draft** workflow state and follow the configured
			transitions without errors.
		"""
		self._append_workflow_activity_log_if_changed()
	
	def _append_workflow_activity_log_if_changed(self):
		"""Append one row to workflow_activity_log when workflow_state changed (called from validate)."""
		current_state = self.workflow_state
		if not current_state:
			return
		doc_before = self.get_doc_before_save()
		previous_state = doc_before.get("workflow_state") if doc_before else None
		if previous_state is None and self.get("name"):
			previous_state = frappe.db.get_value(self.doctype, self.name, "workflow_state")
		if previous_state is None or previous_state == current_state:
			return
		action = get_transition_action_for_states(
			"Payment Approval Request", previous_state or "", current_state
		)
		if not action:
			action = _("Changed to {0}").format(current_state)
		employee_name = get_employee_name_for_user(frappe.session.user)
		self.append("workflow_activity_log", {
			"user": frappe.session.user,
			"employee_name": employee_name,
			"log_datetime": now(),
			"action": action,
			"workflow_status": current_state,
		})

	def on_update(self):
		"""Triggered on document update to detect workflow state changes"""
		if self.has_value_changed("workflow_state"):
			self.handle_workflow_state_change()

	def on_update_after_submit(self):
		"""Triggered on document update after submission (e.g. workflow action on submitted doc).
		Workflow log row is added in validate() so it is saved with the doc.
		"""
		if self.has_value_changed("workflow_state"):
			self.handle_workflow_state_change()

	def handle_workflow_state_change(self):
		"""Handle workflow state changes: create desk announcements (log row is added in validate / on_update_after_submit)."""
		current_state = self.workflow_state

		# Don't create announcements for Draft state
		if not current_state or current_state == "Draft":
			return

		# Get the role that needs to act on this state
		role = self.get_role_for_workflow_state(current_state)
		
		if role:
			# Unpublish old announcements for this Payment Approval Request
			self.unpublish_old_announcements()
			
			# Create new announcement for the current role
			self.create_desk_announcement(role, current_state)
	
	def get_role_for_workflow_state(self, state):
		"""Get the role that should act on the given workflow state"""
		try:
			# Get the workflow for Payment Approval Request
			workflow = frappe.get_all(
				"Workflow",
				filters={"document_type": "Payment Approval Request"},
				fields=["name"],
				limit=1
			)
			
			if not workflow:
				return None
			
			workflow_doc = frappe.get_doc("Workflow", workflow[0].name)
			
			# Find transitions where the current state is the starting state
			# The role that can act is in the "allowed" field
			for transition in workflow_doc.transitions:
				if transition.state == state:
					return transition.allowed
			
			return None
		except Exception as e:
			frappe.log_error(f"Error getting role for workflow state: {str(e)}")
			return None
	
	def create_desk_announcement(self, role, workflow_state):
		"""Create a desk announcement for the specified role"""
		try:
			# Build detailed message with all relevant information
			message = self.build_announcement_message(workflow_state)
			
			# Create the announcement
			announcement = frappe.get_doc({
				"doctype": "Desk Announcement",
				"title": f"Payment Approval Required: {self.name}",
				"message": message,
				"link_url": f"{get_url()}/app/payment-approval-request/{self.name}",
				"show_policy": "Until Dismissed",
				"audience": "By Role",
				"is_published": 1
			})
			
			# Add the role to the roles child table
			announcement.append("roles", {
				"role": role
			})
			
			# Insert the announcement
			announcement.insert(ignore_permissions=True)
			
			frappe.db.commit()
			
		except Exception as e:
			frappe.log_error(f"Error creating desk announcement: {str(e)}")
	
	def build_announcement_message(self, workflow_state):
		"""Build compact HTML message for the announcement. Link is on the announcement (Open Link), not in content.
		Amount is plain text (no currency symbol image) so it renders correctly in the compact modal."""
		if self.amount is not None and self.amount != "":
			currency_code = frappe.defaults.get_global_default("currency") or "SAR"
			amount_str = fmt_money(flt(self.amount), precision=2) + " " + currency_code
		else:
			amount_str = "N/A"
		description_preview = ""
		if self.description:
			description_text = frappe.utils.strip_html(self.description) or ""
			description_preview = (description_text[:200] + "...") if len(description_text) > 200 else description_text

		rows = [
			("Request ID", self.name),
			("Employee", self.employee_name or ""),
			("Department", self.department or ""),
			("Application Date", str(self.application_date) if self.application_date else ""),
			("Amount", amount_str),
		]
		if self.priority:
			rows.append(("Priority", self.priority))
		if self.project:
			rows.append(("Project", self.project))
		if description_preview:
			rows.append(("Description", description_preview))

		row_html = "".join(
			f"""
			<tr>
				<td class="par-announcement__label">{escape_html(str(label))}</td>
				<td class="par-announcement__value">{escape_html(str(value))}</td>
			</tr>"""
			for label, value in rows
		)

		message = f"""
		<div class="par-announcement">
			<div class="par-announcement__header">
				<span class="par-announcement__icon" aria-hidden="true">&#128197;</span>
				<span class="par-announcement__badge par-announcement__badge--pending">{escape_html(workflow_state)}</span>
			</div>
			<p class="par-announcement__subtitle">Action required — please review and approve or reject.</p>
			<div class="par-announcement__card">
				<table class="par-announcement__table">
					{row_html}
				</table>
			</div>
		</div>
		"""
		return message
	
	def unpublish_old_announcements(self):
		"""Unpublish all previous announcements for this Payment Approval Request"""
		try:
			# Find all desk announcements that were created for this request
			# We identify them by checking if the title contains this request's name
			announcements = frappe.get_all(
				"Desk Announcement",
				filters={
					"title": ["like", f"%{self.name}%"],
					"is_published": 1
				},
				fields=["name"]
			)
			
			# Unpublish each announcement
			for ann in announcements:
				frappe.db.set_value("Desk Announcement", ann.name, "is_published", 0)
			
			if announcements:
				frappe.db.commit()
				
		except Exception as e:
			frappe.log_error(f"Error unpublishing old announcements: {str(e)}")
