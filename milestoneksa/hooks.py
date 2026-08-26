app_name = "milestoneksa"
app_title = "Milestoneksa"
app_publisher = "ahmed"
app_description = "milestoneksa customizations"
app_email = "ahmed@milestoneksa.com"
app_license = "mit"
website_include_css = "/assets/milestoneksa/css/login.css"
website_path_resolver = "milestoneksa.crm_route.resolve_path"

website_route_rules = [
	{"from_route": "/crm", "to_route": "milestone-crm"},
	{"from_route": "/crm/<path:app_path>", "to_route": "milestone-crm"},
]

fixtures = [
    {
        "dt": "Custom Field",
        "filters": [["module", "=", "Milestoneksa"]],
    },
    {
        "dt": "Client Script",
        "filters": [["module", "=", "Milestoneksa"]],
    },
    {
        "dt": "Server Script",
        "filters": [["module", "=", "Milestoneksa"]],
    },
]

app_include_css = [
    "https://cdn.jsdelivr.net/npm/frappe-gantt@1.0.3/dist/frappe-gantt.css",
    "/assets/milestoneksa/css/quick_checkin.css",
    "/assets/milestoneksa/css/font.css",
    "/assets/milestoneksa/css/announcement_popup.css?v=3",
    "/assets/milestoneksa/css/project_task_tab.css?v=50",
    "/assets/milestoneksa/css/lib/tabulator.min.css",
]

app_include_js = [
    "/assets/milestoneksa/js/purchase_order.js",
    #"assets/milestoneksa/js/report_pdf_button.js",
    "assets/milestoneksa/js/setup_quick_checkin.js",
    "assets/milestoneksa/js/test_time_dialog.js",
    "assets/milestoneksa/js/test_fields_dialog.js",
    "assets/milestoneksa/js/announcement_popup.js",
    #"/assets/milestoneksa/js/fix_task_gantt_scroll.js",
    #"/assets/milestoneksa/js/task_gantt_config.js",
    "https://cdn.jsdelivr.net/npm/frappe-gantt@1.0.3/dist/frappe-gantt.umd.min.js",
    "/assets/milestoneksa/js/lib/tabulator.min.js",
]

page_css = {
    "project_dashboard": "milestoneksa/css/project_dashboard.css"
}

doctype_js = {
	"Employee": [
		"public/js/employee_assets.js",
		"public/js/employee_salary_ui.js",
		"public/js/employee_custody_ui.js",
		"public/js/employee_contract_end_date.js",
	],
	"HR Settings": [
		"public/js/hr_settings_attendance_emails.js",
		"public/js/hr_settings_contract_alerts.js",
	],
	"Task": ["public/js/task_completion_acknowledgment.js"],
	"Project": ["public/js/project_task_tab.js", "public/js/project_dashboard_tab.js", "public/js/project_financial_summary_tab.js", "public/js/project_building_info.js"],
	"Project Proposal": ["public/js/project_proposal_dashboard.js", "public/js/project_building_info.js"]
}

doc_events = {
	"Purchase Order": {
#		"before_validate": "milestoneksa.milestoneksa.purchase_order.normalize_payment_schedule_to_grand_total",
#		"on_submit": "milestoneksa.milestoneksa.purchase_order.create_payment_tasks"
	},
	"Employee": {
		"validate": "milestoneksa.api.employee.validate_employee",
	},
 	"Salary Structure": {
		"on_submit": "milestoneksa.events.payroll.payroll.create_ssa_on_submit",
	},
	"GL Entry": {
		"after_insert": "milestoneksa.milestoneksa.project.on_gl_entry_change",
		"on_update": "milestoneksa.milestoneksa.project.on_gl_entry_change",
		"on_trash": "milestoneksa.milestoneksa.project.on_gl_entry_change",
	},
	"Purchase Invoice": {
		"on_submit": "milestoneksa.milestoneksa.project.recalculate_project_purchase_cost_on_pi_change",
		"on_cancel": "milestoneksa.milestoneksa.project.recalculate_project_purchase_cost_on_pi_change",
	},
	"WhatsApp Message": {
		"before_validate": [
			"milestoneksa.chatbot.whatsapp_bot.link_whatsapp_message_to_crm",
			"milestoneksa.chatbot.whatsapp_bot.prepare_chatbot_template_body_param",
		],
		"after_insert": "milestoneksa.chatbot.whatsapp_bot.handle_whatsapp_message",
	},
	"WhatsApp Templates": {
		"before_validate": "milestoneksa.chatbot.whatsapp_bot.validate_chatbot_whatsapp_template",
	},
	"Lead": {
		"after_insert": "milestoneksa.crm_lead_sync.sync_erpnext_lead_to_crm",
		"on_update": "milestoneksa.crm_lead_sync.sync_erpnext_lead_to_crm",
	},
	"CRM Lead": {
		"after_insert": "milestoneksa.crm_lead_sync.sync_crm_lead_to_erpnext",
		"on_update": "milestoneksa.crm_lead_sync.sync_crm_lead_to_erpnext",
	},
	"Employee Contract End Review": {
		"on_update": "milestoneksa.tasks.contract_expiry_alerts.on_contract_review_update",
	},
}

scheduler_events = {
	"cron": {
		# Daily task summary: 4 PM (server time), Sun–Thu only (exclude Fri & Sat)
		"0 16 * * 0-4": ["milestoneksa.tasks.daily_task_summary.send_daily_project_task_summary"],
		# Attendance check-in/check-out emails: every 5 min Sun–Thu; times from HR Settings
		"*/5 * * * 0-4": [
			"milestoneksa.tasks.attendance_email_reports.run_due_attendance_email_reports"
		],
		"0 8 * * 0-4": [
			"milestoneksa.tasks.contract_expiry_alerts.run_contract_expiry_alerts"
		],
		# Project task inactivity: daily notice when user has not altered tasks for 15+ days
		"0 9 * * 0-4": [
			"milestoneksa.project_user_inactivity_email.run_daily_project_inactivity_emails",
			"milestoneksa.tasks.auto_attendance_ahmed_abdelrahman.run_daily_auto_checkin",
		],
		# Ahmed Abdelrahman auto check-out (random 5–7 PM), Sun–Thu only
		"0 19 * * 0-4": [
			"milestoneksa.tasks.auto_attendance_ahmed_abdelrahman.run_daily_auto_checkout",
		],
	},
}

boot_session = "milestoneksa.boot.boot_session"

# Email
# ------------------
# Override email sending to use API instead of SMTP (bypasses DigitalOcean SMTP port blocking)
override_email_send = "milestoneksa.email_api.send_email_via_api"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "milestoneksa",
# 		"logo": "/assets/milestoneksa/logo.png",
# 		"title": "Milestoneksa",
# 		"route": "/milestoneksa",
# 		"has_permission": "milestoneksa.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/milestoneksa/css/milestoneksa.css"
# app_include_js = "/assets/milestoneksa/js/milestoneksa.js"

# include js, css files in header of web template
# web_include_css = "/assets/milestoneksa/css/milestoneksa.css"
# web_include_js = "/assets/milestoneksa/js/milestoneksa.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "milestoneksa/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "milestoneksa/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "milestoneksa.utils.jinja_methods",
# 	"filters": "milestoneksa.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "milestoneksa.install.before_install"
# after_install = "milestoneksa.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "milestoneksa.uninstall.before_uninstall"
# after_uninstall = "milestoneksa.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "milestoneksa.utils.before_app_install"
# after_app_install = "milestoneksa.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "milestoneksa.utils.before_app_uninstall"
# after_app_uninstall = "milestoneksa.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "milestoneksa.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
	"CRM Task": "milestoneksa.crm_task_permissions.get_permission_query_conditions",
}

has_permission = {
	"CRM Task": "milestoneksa.crm_task_permissions.has_crm_task_permission",
}

after_migrate = ["milestoneksa.crm_task_permissions.ensure_crm_task_docperms"]

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
	"Project": "milestoneksa.milestoneksa.project.Project"
}

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"milestoneksa.tasks.all"
# 	],
# 	"daily": [
# 		"milestoneksa.tasks.daily"
# 	],
# 	"hourly": [
# 		"milestoneksa.tasks.hourly"
# 	],
# 	"weekly": [
# 		"milestoneksa.tasks.weekly"
# 	],
# 	"monthly": [
# 		"milestoneksa.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "milestoneksa.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "milestoneksa.event.get_events"
# }
override_whitelisted_methods = {
	"crm.api.whatsapp.is_whatsapp_enabled": "milestoneksa.chatbot.whatsapp_bot.crm_is_whatsapp_enabled",
	"crm.api.whatsapp.is_whatsapp_installed": "milestoneksa.chatbot.whatsapp_bot.crm_is_whatsapp_installed",
	"crm.api.whatsapp.get_whatsapp_messages": "milestoneksa.chatbot.whatsapp_bot.crm_get_whatsapp_messages",
	"crm.api.doc.delete_bulk_docs": "milestoneksa.api.crm_compat.delete_bulk_docs",
}

# CRM v1.74 expects Frappe v16 APIs; patch before CRM imports them.
import frappe.config as _frappe_config_module  # noqa: E402, F401
import frappe.desk.form.assign_to as _assign_to_module  # noqa: E402, F401
import frappe.model.delete_doc as _delete_doc_module  # noqa: E402

from milestoneksa.compat.delete_doc_shim import patch_frappe_for_crm  # noqa: E402

patch_frappe_for_crm()
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "milestoneksa.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

ignore_links_on_delete = ["CRM Notification"]

# Request Events
# ----------------
# before_request = ["milestoneksa.utils.before_request"]
# after_request = ["milestoneksa.utils.after_request"]

# Job Events
# ----------
# before_job = ["milestoneksa.utils.before_job"]
# after_job = ["milestoneksa.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"milestoneksa.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

