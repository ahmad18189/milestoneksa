app_name = "milestoneksa"
app_title = "Milestoneksa"
app_publisher = "ahmed"
app_description = "milestoneksa customizations"
app_email = "ahmed@milestoneksa.com"
app_license = "mit"
website_include_css = "/assets/milestoneksa/css/login.css"
doc_events = {
    "Purchase Order": {
        "on_submit": "milestoneksa.milestoneksa.purchase_order.create_payment_tasks"
    }
}
doctype_js = {
	"Employee": "public/js/employee_assets.js",
}
fixtures = [
    {
        "dt": "Custom Field",
        "filters": [
            ["module", "=", "Milestoneksa"]
        ]
    }
]
app_include_css = [
    "https://cdn.jsdelivr.net/npm/frappe-gantt@1.0.3/dist/frappe-gantt.css",
]
app_include_js = [
    "/assets/milestoneksa/js/purchase_order.js",
    "assets/milestoneksa/js/setup_quick_checkin.js",
    "assets/milestoneksa/js/test_time_dialog.js",
    "assets/milestoneksa/js/test_fields_dialog.js",
    #"/assets/milestoneksa/js/fix_task_gantt_scroll.js",
    #"/assets/milestoneksa/js/task_gantt_config.js",
    "https://cdn.jsdelivr.net/npm/frappe-gantt@1.0.3/dist/frappe-gantt.umd.min.js",
]
page_css = {
    "project_dashboard": "milestoneksa/css/project_dashboard.css"
}

doc_events = {
	"Employee": {
		"validate": "milestoneksa.api.employee.validate_employee",
	},
 	"Salary Structure": {
		"on_submit": "milestoneksa.events.payroll.payroll.create_ssa_on_submit",
	}
}
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

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

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

# ignore_links_on_delete = ["Communication", "ToDo"]

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

