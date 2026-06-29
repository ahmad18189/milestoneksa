from pathlib import Path

import frappe
from crm.www.crm import get_context as get_crm_context


CRM_WHATSAPP_CSS = "/assets/milestoneksa/css/crm_whatsapp.css?v=20260622-1"
CRM_WHATSAPP_JS = "/assets/milestoneksa/js/crm_whatsapp.js?v=20260622-1"
CRM_KANBAN_CSS = "/assets/milestoneksa/css/crm_kanban.css?v=20260622-1"
CRM_KANBAN_JS = "/assets/milestoneksa/js/crm_kanban.js?v=20260622-1"


def get_context(context):
	context.no_cache = 1
	context.no_breadcrumbs = 1

	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/crm"
		raise frappe.Redirect

	crm_html_path = Path(frappe.get_app_path("crm", "www", "crm.html"))
	crm_html = crm_html_path.read_text(encoding="utf-8")
	crm_html = frappe.render_template(crm_html, get_crm_context())

	for asset in (CRM_WHATSAPP_CSS, CRM_KANBAN_CSS):
		if asset not in crm_html:
			crm_html = crm_html.replace("</head>", f'  <link rel="stylesheet" href="{asset}">\n</head>')

	for asset in (CRM_WHATSAPP_JS, CRM_KANBAN_JS):
		if asset not in crm_html:
			crm_html = crm_html.replace("</body>", f'  <script defer src="{asset}"></script>\n</body>')

	context.crm_html = crm_html
