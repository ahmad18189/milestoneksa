# Copyright (c) 2026, Milestoneksa and contributors
# License: MIT
"""Idempotent seed for CEO Executive KPI Dashboard workspace and settings."""

from __future__ import annotations

import json

import frappe
from frappe.utils import cint

BLOCK_NAME = "Executive KPI Dashboard"
# Name/label must match title: Desk sidebar routes via slug(title), and
# frappe.workspaces is keyed by slug(name). Mismatch causes "Page … not found".
WORKSPACE_TITLE = "Executive KPI Dashboard"
WORKSPACE_NAME = WORKSPACE_TITLE
OLD_WORKSPACE_NAMES = (
	"executive-kpi-dashboard",
	"لوحة المؤشرات التنفيذية",
)

BLOCK_HTML = """
<div id="executive-dashboard-root" class="executive-dashboard" dir="rtl" lang="ar">
	<div class="ed-loading">جاري تحميل لوحة المؤشرات التنفيذية…</div>
</div>
""".strip()

# Runs inside Frappe create_shadow_element IIFE with root_element = shadowRoot.
# App JS may load before/after desk boot replaces window.frappe — use durable export.
BLOCK_SCRIPT = """
(function () {
	function getApi() {
		return (
			window.__mk_executive_dashboard ||
			(window.frappe &&
				frappe.milestoneksa &&
				frappe.milestoneksa.executive_dashboard) ||
			null
		);
	}
	function tryMount(attempt) {
		var root = root_element.querySelector("#executive-dashboard-root");
		if (!root) return;
		var api = getApi();
		if (api && api.mount) {
			api.mount(root);
			return;
		}
		if ((attempt || 0) < 80) {
			setTimeout(function () {
				tryMount((attempt || 0) + 1);
			}, 200);
		} else if (root) {
			root.innerHTML =
				'<div class="ed-error">تعذر تهيئة لوحة المؤشرات. حدّث الصفحة.</div>';
		}
	}
	tryMount(0);
})();
""".strip()


def execute():
	_ensure_ceo_role()
	_seed_settings()
	_upsert_custom_block()
	_upsert_workspace()


def _ensure_ceo_role():
	if not frappe.db.exists("Role", "CEO"):
		doc = frappe.get_doc({"doctype": "Role", "role_name": "CEO", "desk_access": 1})
		doc.insert(ignore_permissions=True)


def _seed_settings():
	if not frappe.db.exists("DocType", "Executive Dashboard Settings"):
		return

	doc = frappe.get_single("Executive Dashboard Settings")

	# Fill missing defaults only; never wipe configured cash accounts on re-run
	if not doc.default_company:
		companies = frappe.get_all("Company", pluck="name", limit=1)
		if companies:
			doc.default_company = companies[0]
	if not doc.dashboard_currency and doc.default_company:
		doc.dashboard_currency = frappe.db.get_value(
			"Company", doc.default_company, "default_currency"
		)
	if not doc.default_date_range:
		doc.default_date_range = "Current Month"
	if not doc.active_project_statuses:
		doc.active_project_statuses = "All"
	if doc.forecast_days in (None, ""):
		doc.forecast_days = 90
	if doc.max_alerts_displayed in (None, ""):
		doc.max_alerts_displayed = 10
	if doc.enabled in (None, ""):
		doc.enabled = 1

	# Seed helper once: when cash table empty and Singles never saved
	had_cash_rows = bool(doc.cash_accounts)
	settings_exist = frappe.db.exists(
		"Singles", {"doctype": "Executive Dashboard Settings", "field": "enabled"}
	)
	if not had_cash_rows and not settings_exist and doc.default_company:
		types = []
		if cint(doc.include_bank_accounts if doc.include_bank_accounts is not None else 1):
			types.append("Bank")
		if cint(doc.include_cash_on_hand if doc.include_cash_on_hand is not None else 1):
			types.append("Cash")
		if types:
			accounts = frappe.get_all(
				"Account",
				filters={
					"company": doc.default_company,
					"is_group": 0,
					"account_type": ["in", types],
				},
				fields=["name", "company"],
				limit=20,
			)
			for acct in accounts:
				doc.append(
					"cash_accounts",
					{
						"account": acct.name,
						"company": acct.company,
						"include_in_cash": 1,
						"restricted": 0,
					},
				)

	doc.save(ignore_permissions=True)


def _upsert_custom_block():
	# Prefer CSS from public asset via app_include; also embed in block style when present
	style = ""
	try:
		from pathlib import Path

		css_path = Path(__file__).resolve().parents[2] / "public" / "css" / "executive_dashboard.css"
		if css_path.exists():
			style = css_path.read_text(encoding="utf-8")
	except Exception:
		style = ""

	if frappe.db.exists("Custom HTML Block", BLOCK_NAME):
		doc = frappe.get_doc("Custom HTML Block", BLOCK_NAME)
		doc.html = BLOCK_HTML
		doc.script = BLOCK_SCRIPT
		if style:
			doc.style = style
		doc.private = 0
		doc.save(ignore_permissions=True)
	else:
		doc = frappe.get_doc(
			{
				"doctype": "Custom HTML Block",
				"name": BLOCK_NAME,
				"html": BLOCK_HTML,
				"script": BLOCK_SCRIPT,
				"style": style,
				"private": 0,
			}
		)
		doc.insert(ignore_permissions=True)


def _upsert_workspace():
	content = [
		{
			"id": "ed-header",
			"type": "header",
			"data": {
				"text": (
					'<div class="ed-ws-title-row">'
					f'<span class="h4"><b>{WORKSPACE_TITLE}</b></span>'
					'<a class="btn btn-default btn-sm ed-ws-settings-btn" '
					'href="/app/executive-dashboard-settings" '
					"onclick=\"frappe.set_route('Form','Executive Dashboard Settings'); return false;\">"
					"Settings</a>"
					"</div>"
				),
				"col": 12,
			},
		},
		{
			"id": "ed-block",
			"type": "custom_block",
			"data": {"custom_block_name": BLOCK_NAME, "col": 12},
		},
	]

	# Drop legacy workspace names so sidebar slug resolves to the current title
	for old_name in OLD_WORKSPACE_NAMES:
		if old_name != WORKSPACE_NAME and frappe.db.exists("Workspace", old_name):
			frappe.delete_doc("Workspace", old_name, force=1, ignore_permissions=True)

	if frappe.db.exists("Workspace", WORKSPACE_NAME):
		doc = frappe.get_doc("Workspace", WORKSPACE_NAME)
	else:
		doc = frappe.new_doc("Workspace")

	doc.title = WORKSPACE_TITLE
	doc.label = WORKSPACE_TITLE  # autoname field:label → name == title
	doc.module = "Milestoneksa"
	doc.public = 1
	doc.content = json.dumps(content, ensure_ascii=False)
	doc.icon = "project"
	doc.indicator_color = "green"
	doc.is_hidden = 0

	doc.set("roles", [])
	doc.append("roles", {"role": "CEO"})

	doc.set("shortcuts", [])
	doc.append(
		"shortcuts",
		{
			"label": "Dashboard Settings",
			"link_to": "Executive Dashboard Settings",
			"type": "DocType",
			"color": "Blue",
		},
	)

	doc.set("custom_blocks", [])
	doc.append(
		"custom_blocks",
		{"custom_block_name": BLOCK_NAME, "label": BLOCK_NAME},
	)

	if doc.is_new():
		doc.insert(ignore_permissions=True)
	else:
		doc.save(ignore_permissions=True)
