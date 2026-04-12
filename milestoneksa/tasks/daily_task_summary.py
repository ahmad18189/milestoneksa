# Copyright (c) 2025, ahmed and contributors
# License: MIT. See LICENSE

"""Daily Project Task Summary: send email to configured roles with tasks created/modified in last 24h."""

from datetime import datetime

import frappe
from frappe import _
from frappe.utils import add_to_date, get_url_to_form, now
from frappe.utils.user import get_users_with_role


def _get_recipient_roles():
	"""Get list of roles from Projects Settings daily summary table."""
	settings = frappe.get_single("Projects Settings")
	table = getattr(settings, "daily_summary_recipient_roles", None) or []
	return [row.role for row in table if row.role]


def _get_recipients_with_language():
	"""Return list of (user_id, email, language) for all users in configured roles. Deduplicated by email so each address receives only one email."""
	roles = _get_recipient_roles()
	if not roles:
		return []
	seen_emails = set()
	out = []
	for role in roles:
		for user in get_users_with_role(role):
			email = frappe.db.get_value("User", user, "email")
			if not email or email in seen_emails:
				continue
			seen_emails.add(email)
			lang = frappe.db.get_value("User", user, "language") or "en"
			out.append((user, email, lang))
	return out


def _get_tasks_last_24h(project_name):
	"""Return tasks for project created or modified in the last 24 hours."""
	since = add_to_date(now(), hours=-24)
	if isinstance(since, datetime):
		since = since.strftime("%Y-%m-%d %H:%M:%S")
	tasks = frappe.db.sql(
		"""
		SELECT name, subject, description, status
		FROM `tabTask`
		WHERE project = %(project)s
		  AND (creation >= %(since)s OR modified >= %(since)s)
		ORDER BY modified DESC
		""",
		{"project": project_name, "since": since},
		as_dict=True,
	)
	out = []
	for t in tasks:
		desc = (t.description or "")[:500]
		if len((t.description or "")) > 500:
			desc += "..."
		out.append({
			"name": t.name,
			"link": get_url_to_form("Task", t.name),
			"subject": t.subject or "",
			"description": desc,
			"status": t.status or "",
		})
	return out


def _get_labels(lang, no_updates=False):
	"""Pre-translated labels for the email template (ar/en). If no_updates=True, use the no-update message."""
	if no_updates:
		no_tasks_message = _(
			"No update on the current system information. Please contact the project managers.",
			lang=lang,
		)
	else:
		no_tasks_message = _("No tasks created or modified in the last 24 hours.", lang=lang)
	return {
		"title": _("Daily Task Summary", lang=lang),
		"task": _("Task", lang=lang),
		"status": _("Status", lang=lang),
		"description": _("Description", lang=lang),
		"subject": _("Subject", lang=lang),
		"no_tasks_message": no_tasks_message,
		"project_link_label": _("Open Project", lang=lang),
		"project": _("Project", lang=lang),
	}


def _get_projects_with_tasks_last_24h():
	"""
	Return list of dicts for each opted-in project that has task changes in last 24h.
	Each dict: project_name, project_display, project_link, tasks (list).
	Only includes projects that have at least one task created/modified.
	"""
	project_names = frappe.get_all(
		"Project",
		filters={"status": "Open", "send_daily_task_summary": 1},
		pluck="name",
	)
	since = add_to_date(now(), hours=-24)
	if isinstance(since, datetime):
		since = since.strftime("%Y-%m-%d %H:%M:%S")
	out = []
	for project_name in project_names:
		tasks = frappe.db.sql(
			"""
			SELECT name, subject, description, status
			FROM `tabTask`
			WHERE project = %(project)s
			  AND (creation >= %(since)s OR modified >= %(since)s)
			ORDER BY modified DESC
			""",
			{"project": project_name, "since": since},
			as_dict=True,
		)
		if not tasks:
			continue
		task_list = []
		for t in tasks:
			desc = (t.description or "")[:500]
			if len((t.description or "")) > 500:
				desc += "..."
			task_list.append({
				"name": t.name,
				"link": get_url_to_form("Task", t.name),
				"subject": t.subject or "",
				"description": desc,
				"status": t.status or "",
			})
		project_display = frappe.db.get_value("Project", project_name, "project_name") or project_name
		out.append({
			"project_name": project_name,
			"project_display": project_display,
			"project_link": get_url_to_form("Project", project_name),
			"tasks": task_list,
		})
	return out


def _send_multi_project_summary():
	"""
	Send one email per recipient with tasks from all opted-in projects (last 24h).
	When no tasks were updated in the past 24 hours, still send an email with the message
	"No update on the current system information. Please contact the project managers."
	Returns total number of emails sent.
	"""
	recipients = _get_recipients_with_language()
	if not recipients:
		return 0
	projects_with_tasks = _get_projects_with_tasks_last_24h()
	no_updates = not projects_with_tasks
	sent = 0
	for user_id, email, lang in recipients:
		labels = _get_labels(lang, no_updates=no_updates)
		if no_updates:
			# One placeholder section so template shows no_tasks_message
			projects_payload = [{
				"project_name": "",
				"project_display": _("System", lang=lang),
				"project_link": "#",
				"tasks": [],
			}]
		else:
			projects_payload = projects_with_tasks
		subject = _("Daily Task Summary", lang=lang)
		args = {
			"projects": projects_payload,
			"labels": labels,
			"no_updates": no_updates,
		}
		try:
			frappe.sendmail(
				recipients=[email],
				subject=subject,
				template="project_daily_task_summary",
				args=args,
				header=[labels["title"], "blue"],
			)
			sent += 1
		except Exception as e:
			frappe.log_error(
				title=f"Daily Task Summary (multi-project) email failed -> {email}",
				message=str(e),
			)
	return sent


def _send_for_project(project_name):
	"""
	Send daily task summary emails for one project to all configured recipients.
	Returns (sent_count, error_message or None).
	"""
	if not project_name or not frappe.db.exists("Project", project_name):
		return 0, _("Invalid project.")
	recipients = _get_recipients_with_language()
	if not recipients:
		return 0, _("No recipient roles configured in Projects Settings.")
	tasks = _get_tasks_last_24h(project_name)
	project_link = get_url_to_form("Project", project_name)
	project_display = frappe.db.get_value("Project", project_name, "project_name") or project_name
	sent = 0
	for user_id, email, lang in recipients:
		labels = _get_labels(lang)
		subject = _("Daily task summary: {0}", lang=lang).format(project_display)
		args = {
			"project_name": project_display,
			"project_link": project_link,
			"tasks": tasks,
			"labels": labels,
		}
		try:
			frappe.sendmail(
				recipients=[email],
				subject=subject,
				template="project_daily_task_summary",
				args=args,
				header=[labels["title"], "blue"],
			)
			sent += 1
		except Exception as e:
			frappe.log_error(
				title=f"Daily Task Summary email failed for {project_name} -> {email}",
				message=str(e),
			)
	return sent, None


def send_daily_project_task_summary():
	"""Scheduled job: send one email per recipient with tasks from all opted-in projects (last 24h)."""
	try:
		_send_multi_project_summary()
	except Exception as e:
		frappe.log_error(
			title="Daily Task Summary (scheduler) failed",
			message=str(e),
		)


def send_test_email(to_email: str):
	"""Send a test daily task summary to the given email (e.g. for testing)."""
	if not to_email:
		return "No email provided."
	projects_with_tasks = _get_projects_with_tasks_last_24h()
	labels = _get_labels("en")
	if not projects_with_tasks:
		# One placeholder section so template renders
		projects_with_tasks = [{
			"project_name": "",
			"project_display": _("(No projects with task changes in the last 24 hours)"),
			"project_link": "#",
			"tasks": [],
		}]
	subject = _("Daily Task Summary (test)")
	args = {"projects": projects_with_tasks, "labels": labels}
	frappe.sendmail(
		recipients=[to_email],
		subject=subject,
		template="project_daily_task_summary",
		args=args,
		header=[_("Daily Task Summary"), "blue"],
	)
	return f"Test email sent to {to_email}"


@frappe.whitelist()
def send_daily_task_summary_for_project(project: str):
	"""Send daily task summary for the given project now (used by custom button)."""
	if not project:
		return {"sent": 0, "message": _("Project is required.")}
	if not frappe.db.exists("Project", project):
		return {"sent": 0, "message": _("Invalid project.")}
	doc = frappe.get_doc("Project", project)
	frappe.has_permission("Project", "read", doc=doc, throw=True)
	sent, err = _send_for_project(project)
	if err:
		return {"sent": 0, "message": err}
	return {
		"sent": sent,
		"message": _("Daily task summary sent to {0} recipient(s).").format(sent),
	}
