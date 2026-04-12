# -*- coding: utf-8 -*-
"""Recalculate Purchase Order Item received_qty and billed_amt from linked PRs and PIs."""
from frappe import _
import frappe
from frappe.utils import flt


@frappe.whitelist()
def recalc_po_from_invoices(po_name):
	"""
	Recalculate Purchase Order Item received_qty and billed_amt from linked Purchase Receipts
	and Purchase Invoices, then update PO per_received and per_billed.
	Use: bench --site YOUR_SITE execute milestoneksa.api.purchase_order_recalc.recalc_po_from_invoices --args '["PUR-ORD-2025-00002"]'
	"""
	if not po_name or not frappe.db.exists("Purchase Order", po_name):
		return {"updated": 0, "message": "Invalid or missing Purchase Order."}
	po_items = frappe.db.get_all(
		"Purchase Order Item",
		filters={"parent": po_name},
		fields=["name", "amount", "qty"],
		order_by="idx",
	)
	if not po_items:
		return {"updated": 0, "message": "No items on this PO."}
	updated = 0
	for row in po_items:
		detail_id = row["name"]
		# received_qty: from PR Item + from PI Item (when PI update_stock=1), same as ERPNext status updater
		received = frappe.db.sql(
			"""
			SELECT IFNULL((
				SELECT SUM(pri.received_qty)
				FROM `tabPurchase Receipt Item` pri
				INNER JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent AND pr.docstatus = 1
				WHERE pri.purchase_order_item = %(detail_id)s
			), 0) + IFNULL((
				SELECT SUM(pi_item.received_qty)
				FROM `tabPurchase Invoice Item` pi_item
				INNER JOIN `tabPurchase Invoice` pi ON pi.name = pi_item.parent AND pi.docstatus = 1 AND pi.update_stock = 1
				WHERE pi_item.po_detail = %(detail_id)s
			), 0)
			""",
			{"detail_id": detail_id},
			as_list=True,
		)
		rec_qty = flt(received[0][0], 6) if received and received[0][0] is not None else 0
		frappe.db.set_value("Purchase Order Item", detail_id, "received_qty", rec_qty, update_modified=False)
		# billed_amt: from PI Item (po_detail or via pr_detail -> PR Item -> purchase_order_item)
		billed = frappe.db.sql(
			"""
			SELECT IFNULL(SUM(pi_item.amount), 0)
			FROM `tabPurchase Invoice Item` pi_item
			INNER JOIN `tabPurchase Invoice` pi ON pi.name = pi_item.parent
			LEFT JOIN `tabPurchase Receipt Item` pri ON pri.name = pi_item.pr_detail
			WHERE pi.docstatus = 1
			  AND (pi_item.po_detail = %(detail_id)s OR pri.purchase_order_item = %(detail_id)s)
			""",
			{"detail_id": detail_id},
			as_list=True,
		)
		billed_val = flt(billed[0][0]) if billed and billed[0][0] else 0
		frappe.db.set_value("Purchase Order Item", detail_id, "billed_amt", billed_val, update_modified=False)
		updated += 1
	# per_received: same as Purchase Order set_received_qty_for_drop_ship_items (min(received_qty, qty) / total qty)
	per_received_row = frappe.db.sql(
		"""
		SELECT ROUND(
			IFNULL(SUM(LEAST(IFNULL(received_qty, 0), IFNULL(qty, 0))), 0)
			/ NULLIF(SUM(IFNULL(qty, 0)), 0) * 100, 6
		)
		FROM `tabPurchase Order Item`
		WHERE parent = %s AND parenttype = 'Purchase Order'
		HAVING SUM(IFNULL(qty, 0)) > 0
		""",
		(po_name,),
		as_list=True,
	)
	if per_received_row and per_received_row[0][0] is not None:
		frappe.db.set_value("Purchase Order", po_name, "per_received", flt(per_received_row[0][0]), update_modified=False)
	# per_billed: same as status_updater
	per_billed = frappe.db.sql(
		"""
		SELECT ROUND(
			IFNULL(SUM(CASE WHEN ABS(amount) > ABS(IFNULL(billed_amt,0)) THEN ABS(IFNULL(billed_amt,0)) ELSE ABS(amount) END), 0)
			/ NULLIF(SUM(ABS(amount)), 0) * 100, 6
		)
		FROM `tabPurchase Order Item`
		WHERE parent = %s AND parenttype = 'Purchase Order'
		HAVING SUM(ABS(amount)) > 0
		""",
		(po_name,),
		as_list=True,
	)
	if per_billed and per_billed[0][0] is not None:
		frappe.db.set_value("Purchase Order", po_name, "per_billed", flt(per_billed[0][0]), update_modified=False)
	# Refresh PO status
	po_doc = frappe.get_doc("Purchase Order", po_name)
	if hasattr(po_doc, "set_status"):
		po_doc.set_status(update=True)
	frappe.db.commit()
	return {"updated": updated, "message": f"Updated {updated} PO item(s): received_qty, billed_amt, per_received, per_billed for {po_name}."}
