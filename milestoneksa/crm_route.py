from frappe.website.path_resolver import resolve_path as default_resolve_path


def resolve_path(path):
	normalized_path = path.strip("/ ")
	if normalized_path == "crm" or normalized_path.startswith("crm/"):
		return "milestone-crm"

	if (
		normalized_path == "blog"
		or normalized_path.startswith("blog/")
		or normalized_path.startswith("blog-detail/")
	):
		return "appartement"

	return default_resolve_path(path)
