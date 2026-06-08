from pathlib import Path

import frappe
from crm.www.crm import get_context as get_crm_context


CRM_WHATSAPP_CSS = "/assets/milestoneksa/css/crm_whatsapp.css?v=20260608"
CRM_WHATSAPP_JS = "/assets/milestoneksa/js/crm_whatsapp.js?v=20260608"


def get_context(context):
	context.no_cache = 1
	context.no_breadcrumbs = 1

	crm_html_path = Path(frappe.get_app_path("crm", "www", "crm.html"))
	crm_html = crm_html_path.read_text(encoding="utf-8")
	crm_html = frappe.render_template(crm_html, get_crm_context())

	if CRM_WHATSAPP_CSS not in crm_html:
		crm_html = crm_html.replace(
			"</head>",
			f'  <link rel="stylesheet" href="{CRM_WHATSAPP_CSS}">\n</head>',
		)

	if CRM_WHATSAPP_JS not in crm_html:
		crm_html = crm_html.replace(
			"</body>",
			f'  <script defer src="{CRM_WHATSAPP_JS}"></script>\n</body>',
		)

	context.crm_html = crm_html
