from frappe.website.path_resolver import resolve_path as default_resolve_path


def resolve_path(path):
	normalized_path = path.strip("/ ")
	if normalized_path == "crm" or normalized_path.startswith("crm/"):
		return "milestone-crm"

	return default_resolve_path(path)
