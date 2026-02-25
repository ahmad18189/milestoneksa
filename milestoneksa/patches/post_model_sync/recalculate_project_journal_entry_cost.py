"""One-time patch: recalculate total_cost_from_journal_entry for all projects."""
import frappe


def execute():
	from milestoneksa.milestoneksa.project import recalculate_all_projects_journal_entry_cost

	result = recalculate_all_projects_journal_entry_cost()
	frappe.msgprint(f"Updated {result['updated']} of {result['total']} projects.")
