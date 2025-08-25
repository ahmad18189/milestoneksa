# -*- coding: utf-8 -*-
# File: milestoneksa/api/employee_assets.py

import re
import frappe
from frappe import _
from frappe.utils import escape_html

AR_RE = re.compile(r"[\u0600-\u06FF]")  # Arabic block

def _is_arabic(text: str) -> bool:
	return bool(AR_RE.search(text or ""))

@frappe.whitelist()
def get_assets_for_employee(employee: str):
	"""
	Return a list of assets where custodian == given Employee.
	Also returns tags split into Arabic / English buckets.
	Structure:
	[
		{
			"name": "AST-0001",
			"asset_name": "MacBook Pro",
			"tags_ar": ["حاسوب"],
			"tags_en": ["laptop","mac"]
		},
		...
	]
	"""
	if not employee:
		frappe.throw(_("Employee is required"))

	# Resolve the 'custodian' field dynamically (some sites customize Asset)
	asset_meta = frappe.get_meta("Asset")
	fieldnames = [df.fieldname for df in asset_meta.fields]
	custodian_field = "custodian" if "custodian" in fieldnames else None
	if not custodian_field:
		# Fallbacks commonly seen in customizations (best-effort)
		for candidate in ("employee", "employee_id", "employee_code"):
			if candidate in fieldnames:
				custodian_field = candidate
				break
	if not custodian_field:
		frappe.throw(_("Could not find a 'custodian' or compatible field on Asset."))

	# Query assets
	assets = frappe.get_all(
		"Asset",
		filters={custodian_field: employee},
		fields=["name", "asset_name"]
	)

	# Collect tags for each Asset via Tag Link
	out = []
	for a in assets:
		tags = frappe.db.get_all(
			"Tag Link",
			filters={"document_type": "Asset", "document_name": a.name},
			fields=["tag"]
		)
		tags_ar, tags_en = [], []
		for t in tags:
			txt = (t.tag or "").strip()
			if not txt:
				continue
			if _is_arabic(txt):
				tags_ar.append(txt)
			else:
				tags_en.append(txt)

		out.append({
			"name": a.name,
			"asset_name": escape_html(a.asset_name or a.name),
			"tags_ar": tags_ar,
			"tags_en": tags_en,
		})

	return out
