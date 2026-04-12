# -*- coding: utf-8 -*-
"""
Management payment & cost report: PI payments, Payment Approval Requests, cost concepts, per m².

Run:
  bench --site milestoneksa.com execute milestoneksa.payment_distribution_report.run

Optional args (via execute):
  bench --site milestoneksa.com execute milestoneksa.payment_distribution_report.run \\
    --kwargs '{"projects": ["Milestone-101", "Milestone-106"]}'
"""
from __future__ import annotations

from collections import defaultdict

import frappe
from frappe.utils import flt

# Cost concept buckets (order: first match wins)
_CONCEPT_RULES: list[tuple[str, tuple[str, ...]]] = [
	(
		"governmental_fees",
		(
			"رخص",
			"بلدية",
			"حكوم",
			"رسوم",
			"ترخيص",
			"فحص",
			"هيئة",
			"استمارة",
			"zatca",
			"ضريبة",
			"government",
			"municipal",
			"license",
			"permit",
		),
	),
	(
		"consulting_engineering",
		(
			"استشارات",
			"هندس",
			"مكتب",
			"تصميم",
			"اشراف",
			"consult",
			"engineering office",
			"survey",
		),
	),
	(
		"labor",
		(
			"عامل",
			"عمال",
			"اجور",
			"اجرة",
			"labor",
			"wage",
			"manpower",
			"workers",
		),
	),
	(
		"material",
		(
			"مواد",
			"حديد",
			"اسمنت",
			"سباكة",
			"كهرباء",
			"بلاط",
			"دهان",
			"صرف",
			"acces",
			"steel",
			"cement",
			"material",
			"cable",
			"pipe",
			"equipment",
		),
	),
	(
		"building_contracting",
		(
			"مقاول",
			"بناء",
			"انشاء",
			"خرسانة",
			"ردم",
			"structural",
			"contracting",
			"construction",
			"مباني",
		),
	),
]


def _classify_text(text: str | None) -> str:
	if not text:
		return "other"
	low = text.lower()
	for concept, keys in _CONCEPT_RULES:
		for k in keys:
			if k.lower() in low:
				return concept
	return "other"


def _classify_item_group(group: str | None) -> str:
	if not group:
		return "other"
	g = group.lower()
	if any(x in g for x in ("service", "خدمات", "استش")):
		return "consulting_engineering"
	if any(x in g for x in ("raw", "material", "مواد", "stock")):
		return "material"
	return "other"


def project_pi_names(project: str) -> list[str]:
	return frappe.db.sql(
		"""
		SELECT DISTINCT pi.name
		FROM `tabPurchase Invoice` pi
		INNER JOIN `tabPurchase Invoice Item` pi_item ON pi_item.parent = pi.name
		LEFT JOIN `tabPurchase Order` po ON po.name = pi_item.purchase_order
		WHERE pi.docstatus = 1
		AND (
			pi_item.project = %(p)s
			OR (IFNULL(pi_item.project, '') = '' AND pi.project = %(p)s)
			OR (IFNULL(pi_item.purchase_order, '') != '' AND po.project = %(p)s)
		)
		""",
		{"p": project},
		pluck="name",
	)


def pi_lines_by_concept(project: str) -> dict[str, float]:
	"""Sum PI item base_net_amount by cost concept (item name + item group + supplier hint)."""
	rows = frappe.db.sql(
		"""
		SELECT
			pi_item.item_code,
			pi_item.item_name,
			pi_item.base_net_amount,
			IFNULL(it.item_group, '') AS item_group,
			IFNULL(s.supplier_name, '') AS supplier_name
		FROM `tabPurchase Invoice` pi
		INNER JOIN `tabPurchase Invoice Item` pi_item ON pi_item.parent = pi.name
		LEFT JOIN `tabPurchase Order` po ON po.name = pi_item.purchase_order
		LEFT JOIN `tabItem` it ON it.name = pi_item.item_code
		LEFT JOIN `tabSupplier` s ON s.name = pi.supplier
		WHERE pi.docstatus = 1
		AND (
			pi_item.project = %(p)s
			OR (IFNULL(pi_item.project, '') = '' AND pi.project = %(p)s)
			OR (IFNULL(pi_item.purchase_order, '') != '' AND po.project = %(p)s)
		)
		""",
		{"p": project},
		as_dict=True,
	)
	out: dict[str, float] = defaultdict(float)
	for r in rows:
		amt = flt(r.base_net_amount)
		text = " ".join(
			filter(
				None,
				[
					r.item_name,
					r.item_code,
					r.item_group,
					r.supplier_name,
				],
			)
		)
		c1 = _classify_text(text)
		if c1 == "other":
			c1 = _classify_item_group(r.item_group)
		if c1 == "other":
			c1 = _classify_text(r.supplier_name)
		out[c1] += amt
	return dict(out)


def payment_allocations_by_pi(project: str) -> tuple[list[dict], float]:
	pis = project_pi_names(project)
	if not pis:
		return [], 0.0
	ph = ",".join(["%s"] * len(pis))
	rows = frappe.db.sql(
		f"""
		SELECT pe.name AS pe_name, pe.posting_date, pe.mode_of_payment,
			pe.party_name, per.reference_name AS pi_name, per.allocated_amount
		FROM `tabPayment Entry` pe
		INNER JOIN `tabPayment Entry Reference` per ON per.parent = pe.name
		WHERE pe.docstatus = 1 AND pe.party_type = 'Supplier'
		AND per.reference_doctype = 'Purchase Invoice'
		AND per.reference_name IN ({ph})
		ORDER BY pe.posting_date, pe.name
		""",
		tuple(pis),
		as_dict=True,
	)
	total = sum(flt(r.allocated_amount) for r in rows)
	return rows, total


def allocate_paid_to_concepts(
	pi_concept_net: dict[str, float], paid_total: float
) -> dict[str, float]:
	"""Spread paid_total across concepts in proportion to PI net by concept."""
	t_net = sum(pi_concept_net.values())
	if not t_net or not paid_total:
		return {k: 0.0 for k in pi_concept_net}
	scale = paid_total / t_net
	return {k: flt(v * scale) for k, v in pi_concept_net.items()}


def get_project_area_m2(project: str) -> tuple[float, str]:
	"""Returns (area_m2, label). Prefers total building area, then land."""
	doc = frappe.db.get_value(
		"Project",
		project,
		["total_building_area_custom", "total_land_area_custom"],
		as_dict=True,
	)
	if not doc:
		return 0.0, "no area on project"
	bld = flt(doc.get("total_building_area_custom"))
	land = flt(doc.get("total_land_area_custom"))
	if bld > 0:
		return bld, "total_building_area_custom (m²)"
	if land > 0:
		return land, "total_land_area_custom (m²)"
	return 0.0, "no building/land area set"


def get_payment_approval_requests(project: str) -> list[dict]:
	if not frappe.db.exists("DocType", "Payment Approval Request"):
		return []
	return frappe.get_all(
		"Payment Approval Request",
		filters={"project": project, "docstatus": 1},
		fields=[
			"name",
			"employee_name",
			"application_date",
			"amount",
			"description",
			"final_remarks",
			"priority",
			"creation",
		],
		order_by="application_date desc, creation desc",
	)


def print_management_report(project: str, title: str) -> None:
	line = "=" * 78
	print(f"\n{line}\n{title}\n{line}")

	area_m2, area_label = get_project_area_m2(project)
	print(f"\n--- Project area ---\n  {area_label}: {area_m2:,.2f}" if area_m2 else "\n--- Project area ---\n  (Set total_building_area_custom or total_land_area_custom on Project for per-m² metrics)")

	# PAR
	pars = get_payment_approval_requests(project)
	print(f"\n--- Payment Approval Request (submitted, linked to project) — {len(pars)} ---")
	par_total = 0.0
	for p in pars:
		amt = flt(p.amount)
		par_total += amt
		concept = _classify_text((p.description or "") + " " + (p.final_remarks or ""))
		print(
			f"  {p.name} | {p.application_date} | {amt:,.2f} | {p.priority or ''} | [{concept}]"
		)
		desc = (p.description or "")[:120].replace("\n", " ")
		print(f"      Why: {desc}")
		if p.final_remarks:
			print(f"      Final remarks: {(p.final_remarks or '')[:120]}")
	print(f"  Subtotal PAR amounts (requested/approved workflow): {par_total:,.2f}")

	# PI lines by concept
	pi_by_c = pi_lines_by_concept(project)
	pi_net_total = sum(pi_by_c.values())
	print(f"\n--- Purchase Invoice lines by cost concept (base net) — total {pi_net_total:,.2f} ---")
	_concept_labels = {
		"governmental_fees": "Governmental / licenses / fees",
		"consulting_engineering": "Consulting & engineering",
		"labor": "Labor & manpower",
		"material": "Materials & supplies",
		"building_contracting": "Building / contracting works",
		"other": "Other / unclassified",
	}
	for key in sorted(pi_by_c.keys(), key=lambda x: -pi_by_c[x]):
		v = pi_by_c[key]
		pct = (v / pi_net_total * 100) if pi_net_total else 0
		label = _concept_labels.get(key, key)
		print(f"  {label:42} {v:>14,.2f}  ({pct:5.1f}%)")

	rows, paid_total = payment_allocations_by_pi(project)
	print(f"\n--- Supplier payments allocated to project PIs ---\n  Total paid: {paid_total:,.2f}")

	paid_by_c = allocate_paid_to_concepts(pi_by_c, paid_total)
	print("\n--- Estimated paid by cost concept (paid × PI concept mix) ---")
	for key in sorted(paid_by_c.keys(), key=lambda x: -paid_by_c[x]):
		v = paid_by_c[key]
		pct = (v / paid_total * 100) if paid_total else 0
		label = _concept_labels.get(key, key)
		print(f"  {label:42} {v:>14,.2f}  ({pct:5.1f}%)")

	if area_m2 and paid_total:
		print("\n--- Cost per m² (paid / area) ---")
		print(f"  Overall paid per m²: {paid_total / area_m2:,.2f}")
		for key in sorted(paid_by_c.keys(), key=lambda x: -paid_by_c[x]):
			if paid_by_c[key] <= 0:
				continue
			label = _concept_labels.get(key, key)
			print(f"  {label:42} {paid_by_c[key] / area_m2:>14,.2f} / m²")

	# Supplier rollup
	by_sup = defaultdict(float)
	by_mop = defaultdict(float)
	for r in rows:
		a = flt(r.allocated_amount)
		by_sup[r.party_name or ""] += a
		by_mop[r.mode_of_payment or "(not set)"] += a
	print("\n--- Who we paid (supplier) ---")
	for k, v in sorted(by_sup.items(), key=lambda x: -x[1]):
		pct = (v / paid_total * 100) if paid_total else 0
		print(f"  {k[:50]:50} {v:>14,.2f}  ({pct:5.1f}%)")
	print("\n--- How (mode of payment) ---")
	for k, v in sorted(by_mop.items(), key=lambda x: -x[1]):
		pct = (v / paid_total * 100) if paid_total else 0
		print(f"  {str(k)[:45]:45} {v:>14,.2f}  ({pct:5.1f}%)")

	# Management narrative
	print("\n--- Management summary ---")
	print(
		"  • PI cost concepts use keyword rules on item name, item group, and supplier name.\n"
		"  • 'Estimated paid by concept' spreads actual supplier payments in proportion to\n"
		"    those PI line mixes (good when payments match invoices).\n"
		"  • Payment Approval Request rows show internal approval requests; amounts may\n"
		"    overlap or precede supplier invoices — use PAR for 'why' narrative, PI+PE for cash out.\n"
		"  • Set total_building_area_custom (or land area) on the Project for per-m² KPIs."
	)


def run(projects: list[str] | None = None):
	frappe.connect()
	projects = projects or ["Milestone-101", "Milestone-106"]
	titles = {
		"Milestone-101": "Milestone-101 — Al Nathym النظيم",
		"Milestone-106": "Milestone-106 — Al Aqeeq",
	}
	for p in projects:
		print_management_report(p, titles.get(p, p))
	print(
		"\nDone.\n"
		"Note: PAR totals are not added to PI paid totals (different doc flows).\n"
	)


if __name__ == "__main__":
	run()
