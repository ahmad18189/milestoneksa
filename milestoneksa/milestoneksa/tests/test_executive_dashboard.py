# Copyright (c) 2026, Milestoneksa and contributors
# License: MIT

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from milestoneksa.api import executive_dashboard as ed


class TestExecutiveDashboard(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		if not frappe.db.exists("DocType", "Executive Dashboard Settings"):
			self.skipTest("Executive Dashboard Settings not migrated")

		self.settings = frappe.get_single("Executive Dashboard Settings")
		self.settings.enabled = 1
		self.settings.allow_system_manager_access = 1
		self.settings.active_project_statuses = "Open"
		self.settings.show_unavailable_kpis = 1
		self.settings.show_company_summary = 1
		self.settings.show_project_status = 1
		self.settings.show_liquidity_and_sales = 1
		self.settings.show_risks_and_decisions = 1
		if not self.settings.default_company:
			companies = frappe.get_all("Company", pluck="name", limit=1)
			if companies:
				self.settings.default_company = companies[0]
		self.settings.set("cash_accounts", [])
		self.settings.set("excluded_cash_accounts", [])
		self.settings.save(ignore_permissions=True)

	def test_acl_rejects_non_ceo_without_sm_flag(self):
		self.settings.allow_system_manager_access = 0
		self.settings.save(ignore_permissions=True)
		with patch.object(ed.frappe, "get_roles", return_value=["Employee"]):
			with self.assertRaises(frappe.PermissionError):
				ed._assert_access(self.settings)

	def test_acl_allows_ceo(self):
		with patch.object(ed.frappe, "get_roles", return_value=["CEO"]):
			ed._assert_access(self.settings)

	def test_acl_sm_only_when_enabled(self):
		self.settings.allow_system_manager_access = 0
		self.settings.save(ignore_permissions=True)
		with patch.object(ed.frappe, "get_roles", return_value=["System Manager"]):
			with self.assertRaises(frappe.PermissionError):
				ed._assert_access(self.settings)

		self.settings.allow_system_manager_access = 1
		self.settings.save(ignore_permissions=True)
		with patch.object(ed.frappe, "get_roles", return_value=["System Manager"]):
			ed._assert_access(self.settings)

	def test_company_filter_rejects_foreign(self):
		company = self.settings.default_company
		if not company:
			self.skipTest("No company")
		with patch.object(ed, "_permitted_companies", return_value=[company]), patch.object(
			ed.frappe, "get_roles", return_value=["CEO"]
		):
			with self.assertRaises(frappe.ValidationError):
				ed.get_executive_dashboard(company="__FOREIGN_COMPANY__")

	def test_cash_empty_config_unavailable(self):
		accounts = ed._get_cash_accounts(self.settings, self.settings.default_company or "X")
		self.assertEqual(accounts, [])

		if not self.settings.default_company:
			self.skipTest("No company")
		with patch.object(ed.frappe, "get_roles", return_value=["CEO"]), patch.object(
			ed, "_permitted_companies", return_value=[self.settings.default_company]
		):
			data = ed.get_executive_dashboard(company=self.settings.default_company)
			cash = data["company_summary"]["kpis"]["available_cash"]
			self.assertFalse(cash["available"])
			self.assertTrue(cash.get("message"))

	def test_unavailable_unit_kpis(self):
		if not self.settings.default_company:
			self.skipTest("No company")
		with patch.object(ed.frappe, "get_roles", return_value=["CEO"]), patch.object(
			ed, "_permitted_companies", return_value=[self.settings.default_company]
		):
			data = ed.get_executive_dashboard(company=self.settings.default_company)
			units = (data.get("liquidity") or {}).get("unavailable_kpis") or {}
			sold = units.get("units_sold") or {}
			self.assertFalse(sold.get("available"))
			self.assertEqual(sold.get("message"), ed.UNAVAILABLE)

	def test_rag_thresholds(self):
		self.settings.yellow_project_delay_days = 1
		self.settings.red_project_delay_days = 14
		self.settings.yellow_cost_variance_percent = 5
		self.settings.red_cost_variance_percent = 10
		self.assertEqual(ed._rag_for_project(0, 0, self.settings), "green")
		self.assertEqual(ed._rag_for_project(5, 0, self.settings), "yellow")
		self.assertEqual(ed._rag_for_project(20, 0, self.settings), "red")
		self.assertEqual(ed._rag_for_project(0, 12, self.settings), "red")

	def test_planned_progress_not_fabricated(self):
		if not self.settings.default_company:
			self.skipTest("No company")
		with patch.object(ed.frappe, "get_roles", return_value=["CEO"]), patch.object(
			ed, "_permitted_companies", return_value=[self.settings.default_company]
		):
			data = ed.get_executive_dashboard(company=self.settings.default_company)
			for p in (data.get("projects") or {}).get("projects") or []:
				self.assertFalse(p.get("progress_planned_available"))
				self.assertIsNone(p.get("progress_planned"))
