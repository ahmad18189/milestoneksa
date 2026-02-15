# milestoneksa/api/salary_ui.py
from __future__ import annotations
import frappe
from frappe import _
from typing import Tuple

# ---------- helpers ----------

def _find_employee_structure(employee: str):
    """
    Find a Salary Structure tied to this employee (no SSA). We only query fields
    that actually exist on your site to avoid 1054 Unknown column errors.
    Tries, in order:
      - employee (if present)
      - custom_employee (if present)
      - custom_employee_name (if present)
      - name == Employee.employee_name (fallback)
    """
    emp = frappe.get_doc("Employee", employee)
    emp_name = emp.employee_name

    meta = frappe.get_meta("Salary Structure")

    filters_to_try = []

    if meta.get_field("custom_employee"):
        filters_to_try.append({"custom_employee": employee, "docstatus": ["!=", 2]})


    # Fallback: structure named exactly as employee_name (always safe)
    filters_to_try.append({"name": emp_name, "docstatus": ["!=", 2]})

    for f in filters_to_try:
        rows = frappe.get_all(
            "Salary Structure",
            filters=f,
            fields=["name", "currency", "is_active", "docstatus", "modified"],
            order_by="is_active desc, modified desc",
            limit=1,
        )
        if rows:
            return rows[0]

    return None

def _extract_from_structure(structure_name: str) -> Tuple[list, list, str, object]:
    """Return (earnings, deductions, currency, structure_doc) from Salary Structure."""
    st = frappe.get_doc("Salary Structure", structure_name)
    meta = frappe.get_meta("Salary Structure")

    def pick_rows(candidates):
        for fn in candidates:
            if meta.get_field(fn):
                return getattr(st, fn) or []
        return []

    earn_rows = pick_rows(("earnings", "earnings_component"))
    ded_rows  = pick_rows(("deductions", "deductions_component"))

    def norm(ch, typ):
        return {
            "name": ch.name,
            "salary_component": ch.get("salary_component") or ch.get("abbr") or "Component",
            "amount": float(ch.get("amount") or 0),
            "type": typ,
        }

    earnings   = [norm(ch, "Earning") for ch in earn_rows]
    deductions = [norm(ch, "Deduction") for ch in ded_rows]
    currency   = st.currency or frappe.db.get_default("Currency") or "USD"
    return earnings, deductions, currency, st

def _ensure_draft(doc):
    """If submitted, create amended draft; else return doc."""
    # if doc.docstatus == 0:
    #     return doc, False
    # amended = frappe.copy_doc(doc)
    # amended.amended_from = doc.name
    # amended.docstatus = 0
    # amended.name = None
    # amended.insert(ignore_permissions=True)
    return doc, True

def _find_child_by_component(parent_doc, table_names, component):
    meta = parent_doc.meta
    for tn in table_names:
        if meta.get_field(tn):
            for ch in (getattr(parent_doc, tn) or []):
                if (ch.get("salary_component") or ch.get("abbr")) == component:
                    return ch, tn
    return None, None

# ---------- API: Phase 1 (snapshot in custom HTML) ----------

@frappe.whitelist()
def get_structure_snapshot(employee: str):
    """Return two tables (Earnings & Deductions) from the Salary Structure ONLY."""
    frappe.only_for(("System Manager", "HR Manager", "HR User"), message=_("Not permitted"))

    row = _find_employee_structure(employee)
    if not row:
        return {}

    earnings, deductions, currency, st = _extract_from_structure(row.name)
    return {
        "structure_name": row.name,
        "currency": currency,
        "docstatus": row.docstatus,
        "earnings": earnings,
        "deductions": deductions,
        "total_earnings": sum(x["amount"] for x in earnings),
        "total_deductions": sum(x["amount"] for x in deductions),
    }

# ---------- API: Phase 2 (alter a component on the Structure) ----------

@frappe.whitelist()
def get_structure_components(employee: str):
    """List components for selector (from Structure only)."""
    frappe.only_for(("System Manager", "HR Manager", "HR User"), message=_("Not permitted"))

    row = _find_employee_structure(employee)
    if not row:
        return {"structure": None, "components": []}

    earnings, deductions, currency, st = _extract_from_structure(row.name)
    comps = (
        [{"salary_component": x["salary_component"], "current_amount": x["amount"], "type": "Earning"} for x in earnings] +
        [{"salary_component": x["salary_component"], "current_amount": x["amount"], "type": "Deduction"} for x in deductions]
    )

    # de-dup by name
    seen, uniq = set(), []
    for it in comps:
        if it["salary_component"] not in seen:
            seen.add(it["salary_component"])
            uniq.append(it)

    return {
        "structure": row.name,
        "currency": currency,
        "docstatus": row.docstatus,
        "components": uniq,
    }

@frappe.whitelist()
def alter_structure_component(employee: str, component: str, new_amount: float, submit_after: int = 0):
    """Change a component amount in the Salary Structure (creates amended draft if submitted)."""
    frappe.only_for(("System Manager", "HR Manager"), message=_("Not permitted"))

    row = _find_employee_structure(employee)
    if not row:
        frappe.throw(_("No Salary Structure found for this employee."))

    st = frappe.get_doc("Salary Structure", row.name)
    draft, amended = _ensure_draft(st)

    earn_row, earn_tbl = _find_child_by_component(draft, ("earnings", "earnings_component"), component)
    ded_row,  ded_tbl  = _find_child_by_component(draft, ("deductions", "deductions_component"), component)
    target_row, target_tbl = (earn_row, earn_tbl) if earn_row else (ded_row, ded_tbl)

    if not target_tbl:
        # Default to earnings if we can't find it; flip to deductions if earnings table missing
        target_tbl = "earnings" if draft.meta.get_field("earnings") else ("deductions" if draft.meta.get_field("deductions") else None)
        if not target_tbl:
            frappe.throw(_("Could not find child tables on Salary Structure."))

    if not target_row:
        target_row = draft.append(target_tbl, {
            "salary_component": component,
            "amount": float(new_amount) or 0.0,
        })
    else:
        target_row.amount = float(new_amount) or 0.0

    draft.save(ignore_permissions=False)

    if int(submit_after or 0) == 1:
        try:
            draft.on_update_after_submit()
        except Exception:
            frappe.clear_messages()
            return {"structure_name": draft.name, "amended": amended, "submitted": 0}

    return {"structure_name": draft.name, "amended": amended, "submitted": int(draft.docstatus == 1)}
