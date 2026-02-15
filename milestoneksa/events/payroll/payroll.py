import frappe
from frappe.utils import nowdate, getdate


def create_ssa_on_submit(doc, method=None):
	"""Create a Salary Structure Assignment (SSA) when a Salary Structure is submitted."""
	# Validate required inputs
	if not getattr(doc, "custom_employee", None):
		frappe.throw("Please set the custom Employee field (custom_employee) before submitting the Salary Structure.")
	if not doc.company:
		frappe.throw("Salary Structure must have a Company.")

	# Resolve effective date: prefer structure's from_date else today
	eff_date = getdate(getattr(doc, "from_date", None) or nowdate())


	# Create & submit SSA
	ssa = frappe.get_doc({
		"doctype": "Salary Structure Assignment",
		"employee": doc.custom_employee,
		"salary_structure": doc.name,
		"company": doc.company,
		"from_date": eff_date,
	})
	ssa.insert(ignore_permissions=True)
	ssa.submit()

	frappe.msgprint(f"Created Salary Structure Assignment: <b>{ssa.name}</b> for <b>{doc.custom_employee}</b> (effective {eff_date}).")
