# milestoneksa/milestoneksa/purchase_order.py

import frappe
from frappe.utils import nowdate, getdate, flt


def normalize_payment_schedule_to_grand_total(doc, method=None, *args, **kwargs):
	"""
	Ensure Payment Schedule total equals Grand Total / Rounded Total.
	Scales payment_amount proportionally so sum matches doc.rounded_total or doc.grand_total.
	Called on before_validate so core validate_payment_schedule_amount passes on save.
	"""
	# doc_events call: handler(doc, method_name) e.g. (doc, "before_validate")
	if not doc.get("payment_schedule") or len(doc.payment_schedule) == 0:
		return
	total = sum(flt(row.payment_amount) for row in doc.payment_schedule)
	target = flt(doc.rounded_total or doc.grand_total)
	if target <= 0:
		return
	if abs(total - target) < 0.01:
		return
	# Scale proportionally; put rounding remainder on last row
	precision = 2
	if total <= 0:
		# All zero: set full amount on first row
		doc.payment_schedule[0].payment_amount = flt(target, precision)
		for i in range(1, len(doc.payment_schedule)):
			doc.payment_schedule[i].payment_amount = 0
		return
	allocated = 0
	for i, row in enumerate(doc.payment_schedule):
		if i == len(doc.payment_schedule) - 1:
			row.payment_amount = flt(target - allocated, precision)
		else:
			amt = flt(flt(row.payment_amount) / total * target, precision)
			row.payment_amount = amt
			allocated += amt
	# Set base_payment_amount so validation (total vs base_grand_total) passes
	conv = flt(doc.get("conversion_rate")) or 1
	base_target = flt(doc.base_rounded_total or doc.base_grand_total)
	if hasattr(doc.payment_schedule[0], "base_payment_amount") and base_target is not None:
		base_allocated = 0
		for i, row in enumerate(doc.payment_schedule):
			if i == len(doc.payment_schedule) - 1:
				row.base_payment_amount = flt(base_target - base_allocated, precision)
			else:
				base_amt = flt(flt(row.payment_amount) * conv, precision)
				row.base_payment_amount = base_amt
				base_allocated += base_amt


def _create_tasks(doc):
    """
    Internal helper: create Task per payment schedule row.
    Logs reasons for skipped rows as comments on the Purchase Order.
    """
    today = getdate(nowdate())

    # Resolve Project: header field or first item's project
    project = doc.project or next((item.project for item in doc.items if item.project), None)
    if not project:
        frappe.throw("Please select a Project on this Purchase Order or on at least one item.")

    created, skipped = 0, 0
    skip_messages = []
    if not doc.payment_schedule:
        return

    for row in doc.payment_schedule:
        # Skip if already linked
        if row.task:
            reason = f"Line {row.idx}: already has task {row.task}"
            skip_messages.append(reason)
            skipped += 1
            continue

        # Validate payment amount
        if (row.payment_amount or 0) <= 0:
            reason = f"Line {row.idx}: payment_amount ≤ 0 ({row.payment_amount})"
            frappe.log_error(reason, "milestoneksa")
            skip_messages.append(reason)
            skipped += 1
            continue

        # Parse due_date
        try:
            due_date = getdate(row.due_date)
        except Exception:
            reason = f"Line {row.idx}: invalid due_date '{row.due_date}'"
            frappe.log_error(reason, "milestoneksa")
            skip_messages.append(reason)
            skipped += 1
            continue

        # Determine start date from header schedule_date or transaction_date
        header_date = row.start_date or doc.get("schedule_date") or doc.transaction_date or nowdate()
        try:
            start_date = getdate(header_date)
        except Exception:
            start_date = today

        # Build Task payload (include description in subject)
        # Handle None values for description
        description = row.description or f"Payment Schedule Line {row.idx}"
        subject = f"PO {doc.name} – {description} – p(line {row.idx})"
        task_data = {
            "doctype": "Task",
            "project": project,
            "subject": f"{project} - {description}",
            "description": (
                f"Purchase Order: {doc.name}\n"
                f"Description: {description}\n"
                f"Amount: {row.payment_amount}\n"
                f"Due date: {row.due_date}"
            ),
            "status": "Open",
            "exp_start_date": start_date,
            "exp_end_date": due_date,
            "expected_time": row.get("estimated_hours") or 0
        }

        # Insert Task and link back to payment schedule row
        try:
            task = frappe.get_doc(task_data).insert(ignore_permissions=True)
            frappe.db.set_value(
                "Payment Schedule",
                row.name,
                "task",
                task.name,
                update_modified=False
            )
            created += 1
        except Exception as e:
            reason = f"Line {row.idx}: error creating task: {e}"
            skip_messages.append(reason)
            frappe.log_error(reason, "milestoneksa")
            skipped += 1

    # Final feedback
    frappe.msgprint(f"✅ {created} tasks created, {skipped} rows skipped.")

    # Log skip reasons as comments on the Purchase Order
    for msg in skip_messages:
        doc.add_comment('Comment', msg)

@frappe.whitelist()
def create_payment_tasks(doc, method=None):
	"""
	Hook: Purchase Order on_submit
	Accepts a Document instance directly from the hook.
	"""
	_create_tasks(doc)



@frappe.whitelist()
def generate_payment_tasks(name):
	"""
	Called via JS RPC to generate tasks without submit.
	Fetches the Purchase Order by name.
	"""
	doc = frappe.get_doc("Purchase Order", name)
	_create_tasks(doc)


@frappe.whitelist()
def recalc_po_from_invoices(po_name):
	"""
	Recalculate Purchase Order Item received_qty and billed_amt from linked Purchase Receipts
	and Purchase Invoices, then update PO per_received and per_billed.
	Use: bench --site site execute milestoneksa.milestoneksa.milestoneksa.purchase_order.recalc_po_from_invoices --args '["PUR-ORD-2025-00002"]'
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


@frappe.whitelist()
def recalc_po_billed_amt(po_name):
	"""
	Recalculate billed_amt and received_qty from linked PIs/PRs. Prefer recalc_po_from_invoices() which does both.
	"""
	return recalc_po_from_invoices(po_name)
