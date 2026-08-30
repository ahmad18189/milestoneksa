# Copyright (c) 2026, Milestoneksa and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, cstr, flt, fmt_money, get_datetime, get_url, now_datetime, strip_html
from frappe.utils.verified_command import get_signed_params, verify_request

APPLY_METHOD = "/api/method/milestoneksa.api.rfq_ceo_review.apply_rfq_ceo_email_action"
CONFIRM_METHOD = "/api/method/milestoneksa.api.rfq_ceo_review.confirm_rfq_ceo_email_action"


def _assert_rfq_exists(rfq: str):
	if not rfq or not frappe.db.exists("Request for Quotation", rfq):
		frappe.throw(_("Request for Quotation {0} not found").format(rfq))


def _get_rfq_doc(rfq: str, for_update: bool = False):
	_assert_rfq_exists(rfq)
	return frappe.get_doc("Request for Quotation", rfq, for_update=for_update)


def _user_has_ceo_role(user: str) -> bool:
	return "CEO" in frappe.get_roles(user) or "System Manager" in frappe.get_roles(user)


def _can_decide(rfq_doc) -> bool:
	user = frappe.session.user
	if user == "Administrator" or "System Manager" in frappe.get_roles(user):
		return True
	return rfq_doc.get("custom_ceo_reviewer") == user


def _plain_money(row) -> str:
	raw = strip_html(cstr(row.get("formatted_grand_total") or ""))
	if raw:
		return raw
	currency = row.get("currency") or ""
	return f"{currency} {flt(row.get('grand_total')):.2f}".strip()


def _get_received_quotations(rfq: str) -> list[dict]:
	rows = frappe.db.sql(
		"""
		select
			sq.name,
			sq.supplier,
			sq.supplier_name,
			sq.transaction_date,
			sq.status,
			sq.docstatus,
			sq.grand_total,
			sq.currency,
			sq.valid_till
		from `tabSupplier Quotation` sq
		where sq.docstatus = 1
			and exists (
				select 1
				from `tabSupplier Quotation Item` sqi
				where sqi.parent = sq.name
					and sqi.request_for_quotation = %(rfq)s
			)
		order by sq.grand_total asc, sq.transaction_date asc, sq.name asc
		""",
		{"rfq": rfq},
		as_dict=True,
	)

	lowest = None
	for row in rows:
		total = flt(row.grand_total)
		if lowest is None or total < lowest:
			lowest = total

	for row in rows:
		row.is_lowest = bool(lowest is not None and flt(row.grand_total) == flt(lowest))
		row.formatted_grand_total = fmt_money(row.grand_total, currency=row.currency)
	return rows


def _build_comparison_html(rfq_doc, quotations: list[dict] | None = None) -> str:
	quotations = quotations if quotations is not None else _get_received_quotations(rfq_doc.name)
	winning = rfq_doc.get("custom_winning_supplier_quotation")
	status = rfq_doc.get("custom_ceo_review_status") or "Not Sent"

	banner = ""
	if status == "Approved" and winning:
		winner = next((q for q in quotations if q.name == winning), None)
		supplier_name = (
			(winner.supplier_name if winner else None)
			or rfq_doc.get("custom_winning_supplier")
			or ""
		)
		# formatted_grand_total may include trusted currency HTML (e.g. SAR symbol img)
		amount_html = (winner.formatted_grand_total if winner else "") or ""
		decided_on = rfq_doc.get("custom_ceo_decided_on") or ""
		banner = f"""
		<div class="rfq-ceo-winner-banner">
			<strong>{frappe.utils.escape_html(_("Winning Supplier Quotation"))}:</strong>
			<a href="/app/supplier-quotation/{frappe.utils.escape_html(winning)}">{frappe.utils.escape_html(winning)}</a>
			— {frappe.utils.escape_html(supplier_name)}
			{(' — ' + amount_html) if amount_html else ''}
			{(' — ' + frappe.utils.escape_html(str(decided_on))) if decided_on else ''}
		</div>
		"""
	elif status == "Rejected":
		banner = f"""
		<div class="rfq-ceo-rejected-banner">
			{frappe.utils.escape_html(_("CEO rejected this comparison. You can send it again after reviewing the quotations."))}
		</div>
		"""
	elif status == "Pending CEO Review":
		reviewer = rfq_doc.get("custom_ceo_reviewer") or ""
		banner = f"""
		<div class="rfq-ceo-pending-banner">
			{frappe.utils.escape_html(_("Pending CEO review"))}
			{(' — ' + frappe.utils.escape_html(reviewer)) if reviewer else ''}
		</div>
		"""

	if not quotations:
		return banner + f"<p class='text-muted'>{frappe.utils.escape_html(_('No submitted supplier quotations linked to this RFQ yet.'))}</p>"

	rows_html = []
	for q in quotations:
		classes = ["rfq-ceo-row"]
		if q.name == winning:
			classes.append("rfq-ceo-row--winner")
		elif q.is_lowest:
			classes.append("rfq-ceo-row--lowest")
		badge = ""
		if q.name == winning:
			badge = f'<span class="rfq-ceo-badge rfq-ceo-badge--winner">{frappe.utils.escape_html(_("Winner"))}</span>'
		elif q.is_lowest:
			badge = f'<span class="rfq-ceo-badge rfq-ceo-badge--lowest">{frappe.utils.escape_html(_("Lowest"))}</span>'

		rows_html.append(
			f"""
			<tr class="{' '.join(classes)}" data-sq="{frappe.utils.escape_html(q.name)}">
				<td><a href="/app/supplier-quotation/{frappe.utils.escape_html(q.name)}">{frappe.utils.escape_html(q.name)}</a> {badge}</td>
				<td>{frappe.utils.escape_html(q.supplier_name or q.supplier or '-')}</td>
				<td>{frappe.utils.escape_html(str(q.transaction_date or '-'))}</td>
				<td class="text-right">{q.formatted_grand_total or '-'}</td>
				<td>{frappe.utils.escape_html(_(q.status) if q.status else '-')}</td>
			</tr>
			"""
		)

	return f"""
	{banner}
	<div class="rfq-ceo-comparison-table table-responsive">
		<table class="table table-bordered table-sm mb-0">
			<thead>
				<tr>
					<th>{frappe.utils.escape_html(_("Supplier Quotation"))}</th>
					<th>{frappe.utils.escape_html(_("Supplier"))}</th>
					<th>{frappe.utils.escape_html(_("Date"))}</th>
					<th class="text-right">{frappe.utils.escape_html(_("Grand Total"))}</th>
					<th>{frappe.utils.escape_html(_("Status"))}</th>
				</tr>
			</thead>
			<tbody>
				{''.join(rows_html)}
			</tbody>
		</table>
	</div>
	"""


def _create_ceo_announcement(rfq_doc, ceo_user: str, remarks: str | None = None):
	message = f"""
	<p>{_("Please review the received supplier quotations for RFQ")} <strong>{frappe.utils.escape_html(rfq_doc.name)}</strong>.</p>
	<p>{_("Open the RFQ, compare the quotations, recommend one, then Approve or Reject.")}</p>
	"""
	if remarks:
		message += f"<p><strong>{_('Remarks')}:</strong> {frappe.utils.escape_html(remarks)}</p>"

	announcement = frappe.get_doc(
		{
			"doctype": "Desk Announcement",
			"title": _("RFQ Comparison Review Required: {0}").format(rfq_doc.name),
			"message": message,
			"link_url": f"{get_url()}/app/request-for-quotation/{rfq_doc.name}",
			"show_policy": "Until Dismissed",
			"audience": "By User",
			"is_published": 1,
		}
	)
	announcement.append("users", {"user": ceo_user})
	announcement.insert(ignore_permissions=True)
	return announcement.name


def _assign_to_ceo(rfq: str, ceo_user: str, remarks: str | None = None):
	from frappe.desk.form.assign_to import add as assign_add

	description = _("Please review supplier quotation comparison for RFQ {0}").format(rfq)
	if remarks:
		description += f"\n\n{remarks}"

	assign_add(
		{
			"assign_to": [ceo_user],
			"doctype": "Request for Quotation",
			"name": rfq,
			"description": description,
		},
		ignore_permissions=True,
	)


def _get_rfq_ceo_action_url(
	action: str,
	rfq_doc,
	user: str,
	recommended_quotation: str | None = None,
) -> str:
	params = {
		"action": action,
		"rfq": rfq_doc.name,
		"current_status": rfq_doc.get("custom_ceo_review_status") or "Pending CEO Review",
		"user": user,
		"last_modified": cstr(rfq_doc.modified),
		"recommended_quotation": recommended_quotation or "",
	}
	return get_url(APPLY_METHOD + "?" + get_signed_params(params))


def _get_confirm_rfq_ceo_action_url(
	action: str,
	rfq: str,
	user: str,
	recommended_quotation: str | None = None,
) -> str:
	params = {
		"action": action,
		"rfq": rfq,
		"user": user,
		"recommended_quotation": recommended_quotation or "",
	}
	return get_url(CONFIRM_METHOD + "?" + get_signed_params(params))


def _build_email_comparison_table(rfq_doc, quotations: list[dict], ceo_user: str) -> str:
	rows = []
	th = "border:1px solid #d1d8dd;padding:8px 10px;background:#f5f7fa;text-align:left;font-size:13px;"
	td = "border:1px solid #d1d8dd;padding:8px 10px;font-size:13px;"
	approve_btn = (
		"display:inline-block;padding:7px 12px;background:#28a745;color:#ffffff;"
		"text-decoration:none;border-radius:4px;font-size:12px;font-weight:600;"
	)

	for q in quotations:
		badge = ""
		if q.get("is_lowest"):
			badge = (
				' <span style="background:#2490ef;color:#fff;padding:2px 6px;'
				'border-radius:10px;font-size:10px;font-weight:700;">'
				f'{frappe.utils.escape_html(_("Lowest"))}</span>'
			)
		approve_link = _get_rfq_ceo_action_url("Approved", rfq_doc, ceo_user, q.name)
		rows.append(
			f"""
			<tr>
				<td style="{td}">
					<a href="{get_url()}/app/supplier-quotation/{frappe.utils.escape_html(q.name)}">
						{frappe.utils.escape_html(q.name)}
					</a>{badge}
				</td>
				<td style="{td}">{frappe.utils.escape_html(q.supplier_name or q.supplier or "-")}</td>
				<td style="{td}">{frappe.utils.escape_html(cstr(q.transaction_date or "-"))}</td>
				<td style="{td} text-align:right;">{frappe.utils.escape_html(_plain_money(q))}</td>
				<td style="{td}">{frappe.utils.escape_html(_(q.status) if q.status else "-")}</td>
				<td style="{td} text-align:center;">
					<a href="{approve_link}" style="{approve_btn}">{frappe.utils.escape_html(_("Approve"))}</a>
				</td>
			</tr>
			"""
		)

	reject_link = _get_rfq_ceo_action_url("Rejected", rfq_doc, ceo_user)
	reject_btn = (
		"display:inline-block;padding:10px 16px;background:#dc3545;color:#ffffff;"
		"text-decoration:none;border-radius:4px;font-size:13px;font-weight:600;"
	)
	open_link = f"{get_url()}/app/request-for-quotation/{rfq_doc.name}"
	open_btn = (
		"display:inline-block;padding:10px 16px;background:#2563eb;color:#ffffff;"
		"text-decoration:none;border-radius:4px;font-size:13px;font-weight:600;margin-right:8px;"
	)

	return f"""
	<table style="border-collapse:collapse;width:100%;max-width:900px;margin:16px 0;">
		<thead>
			<tr>
				<th style="{th}">{frappe.utils.escape_html(_("Supplier Quotation"))}</th>
				<th style="{th}">{frappe.utils.escape_html(_("Supplier"))}</th>
				<th style="{th}">{frappe.utils.escape_html(_("Date"))}</th>
				<th style="{th} text-align:right;">{frappe.utils.escape_html(_("Grand Total"))}</th>
				<th style="{th}">{frappe.utils.escape_html(_("Status"))}</th>
				<th style="{th}">{frappe.utils.escape_html(_("Action"))}</th>
			</tr>
		</thead>
		<tbody>
			{''.join(rows)}
		</tbody>
	</table>
	<p style="margin:18px 0 8px 0;">
		<a href="{open_link}" style="{open_btn}">{frappe.utils.escape_html(_("Open RFQ Comparison"))}</a>
		<a href="{reject_link}" style="{reject_btn}">{frappe.utils.escape_html(_("Reject Comparison"))}</a>
	</p>
	<p style="color:#6c7680;font-size:12px;margin-top:16px;">
		{frappe.utils.escape_html(_("Click Approve on a quotation, then confirm on the acknowledgement page. Reject declines all quotations for this comparison."))}
	</p>
	"""


def _email_ceo(
	rfq_doc,
	ceo_user: str,
	remarks: str | None = None,
	quotations: list[dict] | None = None,
	recipients: list[str] | None = None,
):
	to_list = [r for r in (recipients or [ceo_user]) if r]
	if not to_list:
		return

	quotations = quotations if quotations is not None else _get_received_quotations(rfq_doc.name)
	subject = _("RFQ Comparison Review Required: {0}").format(rfq_doc.name)
	message = f"""
	<p>{_("Hello")},</p>
	<p>{_("You have been asked to review supplier quotations for Request for Quotation")}
	<b>{frappe.utils.escape_html(rfq_doc.name)}</b>.</p>
	<p>{_("Compare the quotations below. Approve one quotation, or reject the comparison.")}</p>
	"""
	if remarks:
		message += f"<p><b>{_('Remarks')}:</b> {frappe.utils.escape_html(remarks)}</p>"
	message += _build_email_comparison_table(rfq_doc, quotations, ceo_user)

	frappe.sendmail(
		recipients=to_list,
		subject=subject,
		message=message,
		reference_doctype="Request for Quotation",
		reference_name=rfq_doc.name,
		now=True,
	)


def _email_rfq_creator_on_approve(rfq_doc, selected, remarks: str | None = None):
	"""Notify the RFQ owner when CEO approves a supplier quotation."""
	owner = rfq_doc.owner
	if not owner or owner == "Guest":
		return

	email = frappe.db.get_value("User", owner, "email") or (
		owner if "@" in owner else None
	)
	if not email:
		return

	link = f"{get_url()}/app/request-for-quotation/{rfq_doc.name}"
	sq_name = selected.name if selected else ""
	supplier_name = (selected.supplier_name or selected.supplier or "") if selected else ""
	amount = _plain_money(selected) if selected else ""
	decided_by = frappe.session.user

	subject = _("RFQ {0}: CEO approved supplier quotation").format(rfq_doc.name)
	message = f"""
	<p>{_("Hello")},</p>
	<p>{_("The CEO has approved a supplier quotation for Request for Quotation")}
	<b>{frappe.utils.escape_html(rfq_doc.name)}</b>.</p>
	<ul>
		<li><b>{_("Winning Supplier Quotation")}:</b>
			<a href="{get_url()}/app/supplier-quotation/{frappe.utils.escape_html(sq_name)}">
				{frappe.utils.escape_html(sq_name)}
			</a>
		</li>
		<li><b>{_("Winning Supplier")}:</b> {frappe.utils.escape_html(supplier_name)}</li>
		<li><b>{_("Grand Total")}:</b> {frappe.utils.escape_html(amount)}</li>
		<li><b>{_("Decided By")}:</b> {frappe.utils.escape_html(decided_by)}</li>
	</ul>
	"""
	if remarks:
		message += f"<p><b>{_('Remarks')}:</b> {frappe.utils.escape_html(remarks)}</p>"
	message += f'<p><a href="{link}">{_("Open RFQ Comparison")}</a></p>'

	frappe.sendmail(
		recipients=[email],
		subject=subject,
		message=message,
		reference_doctype="Request for Quotation",
		reference_name=rfq_doc.name,
		now=True,
	)


@frappe.whitelist(allow_guest=True)
def apply_rfq_ceo_email_action(
	action,
	rfq,
	current_status,
	user=None,
	last_modified=None,
	recommended_quotation=None,
):
	"""Step 1: verify signed email link and show acknowledgement page."""
	if not verify_request():
		return

	rfq_doc = _get_rfq_doc(rfq)
	status = rfq_doc.get("custom_ceo_review_status") or "Not Sent"
	if status != current_status or status != "Pending CEO Review":
		_return_rfq_ceo_link_expired_page(rfq_doc)
		return

	if user and not (
		user == rfq_doc.get("custom_ceo_reviewer")
		or user == "Administrator"
		or "System Manager" in frappe.get_roles(user)
		or "CEO" in frappe.get_roles(user)
	):
		frappe.respond_as_web_page(
			_("Not Permitted"),
			_("You are not authorized to perform this action."),
			indicator_color="red",
		)
		return

	action = cstr_decision(action)
	quotations = _get_received_quotations(rfq)
	by_name = {q.name: q for q in quotations}
	selected = by_name.get(recommended_quotation) if recommended_quotation else None

	if action == "Approved" and not selected:
		frappe.respond_as_web_page(
			_("Invalid Quotation"),
			_("The selected supplier quotation is not linked to this RFQ."),
			indicator_color="red",
		)
		return

	action_link = _get_confirm_rfq_ceo_action_url(action, rfq, user, recommended_quotation)
	alert_doc_change = bool(
		last_modified and get_datetime(rfq_doc.modified) != get_datetime(last_modified)
	)

	if action == "Approved":
		action_label = _("Approve Quotation")
		details = _("Approve supplier quotation {0} ({1}) for RFQ {2}.").format(
			frappe.bold(selected.name),
			frappe.bold(selected.supplier_name or selected.supplier or ""),
			frappe.bold(rfq_doc.name),
		)
	else:
		action_label = _("Reject Comparison")
		details = _("Reject the supplier quotation comparison for RFQ {0}.").format(
			frappe.bold(rfq_doc.name)
		)

	frappe.respond_as_web_page(
		title=None,
		html=None,
		indicator_color="blue",
		template="confirm_rfq_ceo_action",
		context={
			"action_label": action_label,
			"details": details,
			"rfq": rfq_doc.name,
			"rfq_link": f"{get_url()}/app/request-for-quotation/{rfq_doc.name}",
			"action_link": action_link,
			"alert_doc_change": alert_doc_change,
			"quotation_name": selected.name if selected else "",
			"supplier_name": (selected.supplier_name or selected.supplier) if selected else "",
			"grand_total": _plain_money(selected) if selected else "",
		},
	)


@frappe.whitelist(allow_guest=True)
def confirm_rfq_ceo_email_action(action, rfq, user=None, recommended_quotation=None):
	"""Step 2: record CEO decision after acknowledgement."""
	if not verify_request():
		return

	logged_in_user = frappe.session.user
	if logged_in_user == "Guest" and user:
		frappe.set_user(user)

	try:
		result = record_rfq_ceo_decision(
			rfq=rfq,
			recommended_quotation=recommended_quotation or None,
			decision=action,
			remarks=_("Decision recorded from email"),
			ignore_permissions=1,
		)
		status = result.get("status")
		winner = result.get("winning_supplier_quotation")
		if action == "Approved":
			message = _("Supplier quotation {0} was approved for RFQ {1}.").format(
				frappe.bold(winner or recommended_quotation),
				frappe.bold(rfq),
			)
		else:
			message = _("Supplier quotation comparison for RFQ {0} was rejected.").format(
				frappe.bold(rfq)
			)

		rfq_link = f"{get_url()}/app/request-for-quotation/{rfq}"
		frappe.respond_as_web_page(
			_("Success"),
			f'{message}<p><a href="{rfq_link}">{_("Open RFQ")}</a></p><p>{_("Status")}: {frappe.bold(status)}</p>',
			indicator_color="green",
		)
	except Exception as e:
		frappe.db.rollback()
		frappe.respond_as_web_page(
			_("Action Failed"),
			cstr(e),
			indicator_color="red",
		)
	finally:
		if logged_in_user == "Guest":
			frappe.set_user(logged_in_user)


def _return_rfq_ceo_link_expired_page(rfq_doc):
	status = rfq_doc.get("custom_ceo_review_status") or "Not Sent"
	frappe.respond_as_web_page(
		_("Link Expired"),
		_("RFQ {0} CEO review status is already {1}.").format(
			frappe.bold(rfq_doc.name),
			frappe.bold(status),
		),
		indicator_color="orange",
	)


@frappe.whitelist()
def get_ceo_users():
	"""Return enabled users that have the CEO role."""
	users = frappe.get_all(
		"Has Role",
		filters={"role": "CEO", "parenttype": "User"},
		pluck="parent",
	)
	if not users:
		return []
	rows = frappe.get_all(
		"User",
		filters={"name": ["in", users], "enabled": 1, "user_type": "System User"},
		fields=["name", "full_name"],
		order_by="full_name asc",
	)
	return [{"value": row.name, "label": row.full_name or row.name} for row in rows]


@frappe.whitelist()
def get_rfq_supplier_quotations(rfq: str):
	rfq_doc = _get_rfq_doc(rfq)
	rfq_doc.check_permission("read")
	quotations = _get_received_quotations(rfq)
	return {
		"quotations": quotations,
		"html": _build_comparison_html(rfq_doc, quotations),
		"status": rfq_doc.get("custom_ceo_review_status") or "Not Sent",
		"reviewer": rfq_doc.get("custom_ceo_reviewer"),
		"winning_supplier_quotation": rfq_doc.get("custom_winning_supplier_quotation"),
		"can_send": rfq_doc.docstatus == 1 and bool(quotations),
		"can_decide": bool(
			rfq_doc.docstatus == 1
			and (rfq_doc.get("custom_ceo_review_status") == "Pending CEO Review")
			and _can_decide(rfq_doc)
			and quotations
		),
		"ceo_users": get_ceo_users(),
	}


@frappe.whitelist()
def send_rfq_comparison_to_ceo(rfq: str, ceo_user: str, remarks: str | None = None):
	rfq_doc = _get_rfq_doc(rfq)
	rfq_doc.check_permission("write")

	if rfq_doc.docstatus != 1:
		frappe.throw(_("Submit the Request for Quotation before sending it to the CEO."))

	if not ceo_user or not frappe.db.exists("User", ceo_user):
		frappe.throw(_("Please select a valid CEO user."))

	if not frappe.db.get_value("User", ceo_user, "enabled"):
		frappe.throw(_("Selected user is disabled."))

	if not _user_has_ceo_role(ceo_user):
		frappe.throw(_("Selected user must have the CEO role."))

	quotations = _get_received_quotations(rfq)
	if not quotations:
		frappe.throw(_("There are no submitted supplier quotations linked to this RFQ."))

	now = now_datetime()
	frappe.db.set_value(
		"Request for Quotation",
		rfq,
		{
			"custom_ceo_review_status": "Pending CEO Review",
			"custom_ceo_reviewer": ceo_user,
			"custom_ceo_sent_on": now,
			"custom_winning_supplier_quotation": None,
			"custom_winning_supplier": None,
			"custom_ceo_decided_on": None,
		},
		update_modified=True,
	)

	_assign_to_ceo(rfq, ceo_user, remarks)
	_create_ceo_announcement(rfq_doc, ceo_user, remarks)
	try:
		rfq_doc.reload()
		_email_ceo(rfq_doc, ceo_user, remarks, quotations=quotations)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "RFQ CEO Review Email Failed")

	frappe.db.commit()
	return get_rfq_supplier_quotations(rfq)


@frappe.whitelist()
def record_rfq_ceo_decision(
	rfq: str,
	recommended_quotation: str | None = None,
	decision: str = "Approved",
	remarks: str | None = None,
	ignore_permissions: int | bool = 0,
):
	rfq_doc = _get_rfq_doc(rfq)
	# CEO reviewer may only have read access on RFQ; gate by reviewer check below.
	# Email acknowledgement path may set the CEO user who lacks RFQ write/read —
	# signed-link auth already verified in confirm_rfq_ceo_email_action.
	if not cint(ignore_permissions):
		rfq_doc.check_permission("read")

	if rfq_doc.docstatus != 1:
		frappe.throw(_("RFQ must be submitted."))

	if (rfq_doc.get("custom_ceo_review_status") or "") != "Pending CEO Review":
		frappe.throw(_("This RFQ is not pending CEO review."))

	if not _can_decide(rfq_doc):
		frappe.throw(_("Only the selected CEO reviewer can record this decision."))

	decision = cstr_decision(decision)
	quotations = _get_received_quotations(rfq)
	by_name = {q.name: q for q in quotations}

	if decision == "Approved":
		if not recommended_quotation or recommended_quotation not in by_name:
			frappe.throw(_("Please select a recommended supplier quotation."))
		selected = by_name[recommended_quotation]
	else:
		# Reject still accepts an optional recommendation for audit trail
		selected = by_name.get(recommended_quotation) if recommended_quotation else None
		if recommended_quotation and not selected:
			frappe.throw(_("Selected quotation is not linked to this RFQ."))

	now = now_datetime()
	user = frappe.session.user
	ceo_user = rfq_doc.get("custom_ceo_reviewer") or user

	# Persist via DB to avoid RFQ re-validation issues (e.g. translated quote_status values).
	idx = cint(frappe.db.sql(
		"""
		select ifnull(max(idx), 0)
		from `tabRFQ CEO Decision`
		where parent=%s and parenttype='Request for Quotation' and parentfield='custom_ceo_decisions'
		""",
		rfq,
	)[0][0]) + 1

	child = frappe.get_doc(
		{
			"doctype": "RFQ CEO Decision",
			"parent": rfq,
			"parenttype": "Request for Quotation",
			"parentfield": "custom_ceo_decisions",
			"idx": idx,
			"supplier_quotation": selected.name if selected else None,
			"supplier": selected.supplier if selected else None,
			"supplier_name": selected.supplier_name if selected else None,
			"grand_total": selected.grand_total if selected else None,
			"currency": selected.currency if selected else None,
			"recommended_quotation": recommended_quotation or None,
			"decision": decision,
			"ceo_user": ceo_user,
			"decided_by": user,
			"decided_on": now,
			"remarks": remarks,
		}
	)
	child.db_insert()

	updates = {
		"custom_ceo_decided_on": now,
	}
	if decision == "Approved":
		updates.update(
			{
				"custom_ceo_review_status": "Approved",
				"custom_winning_supplier_quotation": selected.name,
				"custom_winning_supplier": selected.supplier,
			}
		)
	else:
		updates.update(
			{
				"custom_ceo_review_status": "Rejected",
				"custom_winning_supplier_quotation": None,
				"custom_winning_supplier": None,
			}
		)

	frappe.db.set_value("Request for Quotation", rfq, updates, update_modified=True)

	# Close open ToDos for the reviewer
	try:
		from frappe.desk.form.assign_to import close as assign_close

		if ceo_user:
			assign_close("Request for Quotation", rfq, ceo_user, ignore_permissions=True)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "RFQ CEO Review Close ToDo Failed")

	if decision == "Approved":
		try:
			# Reload status fields used in the notification
			rfq_doc.custom_ceo_review_status = "Approved"
			rfq_doc.custom_winning_supplier_quotation = selected.name
			rfq_doc.custom_winning_supplier = selected.supplier
			_email_rfq_creator_on_approve(rfq_doc, selected, remarks)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "RFQ CEO Approve Creator Email Failed")

	frappe.db.commit()
	return get_rfq_supplier_quotations(rfq)


def cstr_decision(decision: str) -> str:
	value = (decision or "").strip()
	if value not in ("Approved", "Rejected"):
		frappe.throw(_("Decision must be Approved or Rejected"))
	return value
