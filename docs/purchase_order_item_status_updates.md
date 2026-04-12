# Purchase Order Item: Received Qty & Billed Amount Updates

This document describes where **Received Qty** and **Billed Amount** on Purchase Order → Items are updated, based on Purchase Receipt (PR) and Purchase Invoice (PI). All logic lives in **ERPNext**; this project (milestoneksa) does not override it.

---

## 1. Received Qty (`received_qty`)

**Updated by:** Status Updater when **Purchase Receipt** or **Purchase Invoice (update_stock=1)** is submitted or cancelled.

### Purchase Receipt → Purchase Order Item

- **File:** `erpnext/stock/doctype/purchase_receipt/purchase_receipt.py`
- **Where:** `PurchaseReceipt.__init__` → `self.status_updater` (first entry)
- **Config:**
  - `source_dt`: Purchase Receipt Item  
  - `target_dt`: Purchase Order Item  
  - `join_field`: `purchase_order_item` (PR Item → PO Item name)  
  - `target_field`: **`received_qty`**  
  - `source_field`: **`received_qty`** (from PR Item)  
  - `second_source_dt`: Purchase Invoice Item (PI with update_stock=1 also contributes received_qty via `po_detail` → same PO Item)  
  - `target_parent_dt` / `target_parent_field`: Purchase Order, **`per_received`**

**Logic:** `StatusUpdater.update_qty()` in `erpnext/controllers/status_updater.py` runs on submit/cancel. It sums `received_qty` from all submitted Purchase Receipt Items (and, via second_source, Purchase Invoice Items with update_stock=1) linked to each Purchase Order Item (`purchase_order_item` / `po_detail`), then runs:

```sql
UPDATE `tabPurchase Order Item` SET received_qty = <sum> WHERE name = '<po_detail>'
```

and updates Purchase Order’s **per_received** from its items.

### Purchase Invoice (update_stock=1) → Purchase Order Item

- **File:** `erpnext/accounts/doctype/purchase_invoice/purchase_invoice.py`
- **Where:** `PurchaseInvoice.update_status_updater_args()` (called before submit/cancel)
- **Config:** Same target: Purchase Order Item, **`received_qty`**, with source Purchase Invoice Item **`received_qty`**, join `po_detail`, and extra_cond that PI has **update_stock = 1**.

So both PR and stock-updating PI feed into the same **received_qty** sum on each PO Item.

---

## 2. Billed Amount (`billed_amt`)

**Updated by:** Status Updater when **Purchase Invoice** is submitted or cancelled.

### Purchase Invoice → Purchase Order Item

- **File:** `erpnext/accounts/doctype/purchase_invoice/purchase_invoice.py`
- **Where:** `PurchaseInvoice.__init__` → `self.status_updater` (single entry)
- **Config:**
  - `source_dt`: Purchase Invoice Item  
  - `target_dt`: Purchase Order Item  
  - `join_field`: **`po_detail`** (PI Item → PO Item name)  
  - `target_field`: **`billed_amt`**  
  - `target_ref_field`: **`amount`** (PO Item’s total amount; used for % and over-billing checks)  
  - `source_field`: **`amount`** (PI Item amount to sum)  
  - `target_parent_dt` / `target_parent_field`: Purchase Order, **`per_billed`**

**Logic:** On PI submit/cancel, `update_prevdoc_status()` → `update_qty()`. For each PO Item (`po_detail`), it sums **`amount`** of all submitted Purchase Invoice Items pointing to that PO Item, then:

```sql
UPDATE `tabPurchase Order Item` SET billed_amt = <sum> WHERE name = '<po_detail>'
```

and updates Purchase Order’s **per_billed** from its items.

**Note:** Only PI items that reference the PO directly (`po_detail` set, typically **not** created via PR) are included in this sum. When PI is created from PR, items have `pr_detail`; then **Purchase Receipt Item** `billed_amt` is updated by `update_billed_amount_based_on_po()` (see below); PO Item `billed_amt` is still updated by the same status updater when there are PI rows with `po_detail` (e.g. PI from PO without PR).

---

## 3. Status Updater entry point

- **File:** `erpnext/controllers/status_updater.py`
- **Methods:**  
  - `update_prevdoc_status()` → `update_qty()` then `validate_qty()`  
  - `_update_children()` runs the SQL that sets **received_qty** or **billed_amt** on `tabPurchase Order Item`  
  - `_update_percent_field_in_targets()` updates **per_received** / **per_billed** on the Purchase Order

Submit/cancel flows call `self.update_prevdoc_status()` from the controller (e.g. `PurchaseReceipt.on_submit` / `on_cancel`, `PurchaseInvoice.on_submit` / `on_cancel`).

---

## 4. Related: Purchase Receipt Item `billed_amt`

When a Purchase Invoice is submitted/cancelled, **Purchase Receipt Item** `billed_amt` is also updated so PR shows how much is billed:

- **File:** `erpnext/accounts/doctype/purchase_invoice/purchase_invoice.py`  
  - `update_billing_status_in_pr()` → for each PI item with `pr_detail`, sets that PR Item’s **billed_amt**; then calls **`update_billed_amount_based_on_po()`** (from `erpnext/stock/doctype/purchase_receipt/purchase_receipt.py`).
- **File:** `erpnext/stock/doctype/purchase_receipt/purchase_receipt.py`  
  - **`update_billed_amount_based_on_po(po_details, ...)`**  
    - Gets **billed amount against PO** via **`get_billed_amount_against_po(po_details)`** (sum of PI Item `amount` where `po_detail` in po_details, docstatus=1, no pr_detail, update_stock=0).  
    - Updates **Purchase Receipt Item** `billed_amt` for PR items linked to those PO items; it does **not** write to Purchase Order Item (PO Item `billed_amt` is updated only by the PI status updater above).

---

## 5. Summary table

| Field on PO Item | Updated by doctype | Config / logic location | Join |
|------------------|--------------------|-------------------------|------|
| **received_qty** | Purchase Receipt   | `purchase_receipt.py` __init__ → status_updater | PR Item.`purchase_order_item` = PO Item.name |
| **received_qty** | Purchase Invoice (update_stock=1) | `purchase_invoice.py` update_status_updater_args() | PI Item.`po_detail` = PO Item.name |
| **billed_amt**   | Purchase Invoice   | `purchase_invoice.py` __init__ → status_updater | PI Item.`po_detail` = PO Item.name |

All actual writes to **Purchase Order Item** happen in **`erpnext/controllers/status_updater.py`** in **`_update_children()`** via the SQL that sets `received_qty` or `billed_amt` on `tabPurchase Order Item`.

---

## 6. Customizing for this project (milestoneksa)

To change how **Received Qty** or **Billed Amount** are set for PO Items in this project you can:

1. **Doc hooks**  
   - In `hooks.py`, add `doc_events` for **Purchase Receipt** and/or **Purchase Invoice** (`on_submit`, `on_cancel`).  
   - In the handler, after the default flow (or in place of it), recompute and set `received_qty` / `billed_amt` on the linked **Purchase Order Item** rows (e.g. with `frappe.db.set_value` or a custom status-update function).  
   - Be careful not to double-apply if you still call the standard status updater.

2. **Override Status Updater**  
   - Subclass `PurchaseReceipt` and/or `PurchaseInvoice` in this app and override `update_prevdoc_status()` (or the method that builds `status_updater`) to use different rules or extra logic before/after calling `super()`.

3. **Patch after submit**  
   - Use a `doc_events` hook that runs after submit/cancel and only corrects or recalculates PO Item `received_qty` / `billed_amt` when your project-specific conditions are met.

All of the above should use the same link fields: **`purchase_order_item`** (from PR Item) and **`po_detail`** (from PI Item) to identify the **Purchase Order Item** row to update.
