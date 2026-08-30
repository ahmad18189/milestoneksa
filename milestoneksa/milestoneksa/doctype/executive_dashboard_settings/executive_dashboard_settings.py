# Copyright (c) 2026, Milestoneksa and contributors
# License: MIT

import frappe
from frappe.model.document import Document


class ExecutiveDashboardSettings(Document):
	def validate(self):
		company = self.default_company
		for row in list(self.cash_accounts or []) + list(self.excluded_cash_accounts or []):
			if not row.account:
				continue
			acct_company = frappe.db.get_value("Account", row.account, "company")
			if company and acct_company and acct_company != company:
				frappe.throw(
					frappe._("Account {0} belongs to company {1}, not {2}").format(
						row.account, acct_company, company
					)
				)
			if not row.company and acct_company:
				row.company = acct_company

		seen = set()
		for row in self.target_projects or []:
			if not row.project:
				continue
			if row.project in seen:
				frappe.throw(frappe._("Duplicate target project: {0}").format(row.project))
			seen.add(row.project)
			proj = frappe.db.get_value(
				"Project", row.project, ["project_name", "status", "company"], as_dict=True
			)
			if not proj:
				continue
			if company and proj.company and proj.company != company:
				frappe.throw(
					frappe._("Project {0} belongs to company {1}, not {2}").format(
						row.project, proj.company, company
					)
				)
			row.project_name = proj.project_name or row.project
			row.status = proj.status
