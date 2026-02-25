# milestoneksa/api/salary_ui.py
from __future__ import annotations
import json
import re
import frappe
from frappe import _
from typing import Tuple

# ---------- helpers ----------
ALTERATION_LOG_TABLE_FIELD = "mksa_alteration_log"
ALLOWED_COMPONENT_TABLES = ("earnings", "deductions", "earnings_component", "deductions_component")

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

def _to_float(value, default=0.0):
    if isinstance(value, (int, float)):
        return float(value)

    try:
        txt = str(value or "").strip()
        if not txt:
            return float(default)

        # Version currency diffs can contain HTML (e.g. img tag for currency symbol).
        txt = re.sub(r"<[^>]*>", "", txt)

        # Normalize Arabic/Persian digits and decimal/thousand separators.
        trans = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹٫٬", "01234567890123456789.,")
        txt = txt.translate(trans)
        txt = txt.replace("\u200e", "").replace("\u200f", "").replace("\u061c", "")

        # Keep only numeric/separator chars (drop currency labels/symbols).
        txt = re.sub(r"[^0-9,.\-+]", "", txt)

        # Handle locale-specific separators:
        # - 1,250.00 -> 1250.00
        # - 1.250,00 -> 1250.00
        if "," in txt and "." in txt:
            if txt.rfind(",") > txt.rfind("."):
                # decimal comma
                txt = txt.replace(".", "")
                txt = txt.replace(",", ".")
            else:
                # decimal dot
                txt = txt.replace(",", "")
        elif "," in txt:
            # If comma is likely decimal separator (1 or 2 decimal digits), convert to dot.
            parts = txt.split(",")
            if len(parts) == 2 and len(parts[1]) in (1, 2):
                txt = txt.replace(",", ".")
            else:
                txt = txt.replace(",", "")

        # Keep only the first numeric token if there is still mixed text.
        match = re.search(r"[-+]?\d*\.?\d+", txt)
        if not match:
            return float(default)

        return float(match.group(0))
    except Exception:
        return float(default)

def _resolve_component_name_from_structure(st, table_field, row_idx, row_name):
    rows = getattr(st, table_field, None) or []
    if row_name:
        for row in rows:
            if row.get("name") == row_name:
                return row.get("salary_component") or row.get("abbr") or _("Component")

    if isinstance(row_idx, int) and 0 <= row_idx < len(rows):
        row = rows[row_idx]
        return row.get("salary_component") or row.get("abbr") or _("Component")

    return _("Component")

def _append_structure_log_row(st, salary_component, old_value, new_value, altered_at=None, altered_by=None):
    if not st.meta.get_field(ALTERATION_LOG_TABLE_FIELD):
        return

    st.append(ALTERATION_LOG_TABLE_FIELD, {
        "salary_component": salary_component,
        "old_value": _to_float(old_value),
        "new_value": _to_float(new_value),
        "currency": st.get("currency"),
        "altered_at": altered_at or frappe.utils.now(),
        "altered_by": altered_by or frappe.session.user,
    })

def _sync_logs_from_versions(st):
    if not st.meta.get_field(ALTERATION_LOG_TABLE_FIELD):
        return 0

    existing_rows = st.get(ALTERATION_LOG_TABLE_FIELD) or []
    existing_by_identity = {}
    for r in existing_rows:
        identity = (
            str(r.get("altered_at") or ""),
            str(r.get("altered_by") or ""),
            str(r.get("salary_component") or ""),
        )
        existing_by_identity[identity] = r

    versions = frappe.get_all(
        "Version",
        filters={"ref_doctype": "Salary Structure", "docname": st.name},
        fields=["name", "owner", "creation", "data"],
        order_by="creation asc",
        limit=200,
    )

    added_count = 0
    for version in versions:
        try:
            data = json.loads(version.data) if version.data else {}
        except Exception:
            continue

        for item in (data.get("row_changed") or []):
            if not isinstance(item, (list, tuple)) or len(item) < 4:
                continue

            table_field, row_idx, row_name, changes = item[0], item[1], item[2], item[3]
            if table_field not in ALLOWED_COMPONENT_TABLES:
                continue

            if not isinstance(changes, (list, tuple)):
                continue

            comp_name = _resolve_component_name_from_structure(st, table_field, row_idx, row_name)
            for change in changes:
                if not isinstance(change, (list, tuple)) or len(change) < 3:
                    continue
                if change[0] != "amount":
                    continue

                old_value = _to_float(change[1])
                new_value = _to_float(change[2])
                identity = (
                    str(version.creation or ""),
                    str(version.owner or ""),
                    str(comp_name or ""),
                )

                existing_row = existing_by_identity.get(identity)
                if existing_row:
                    # Keep structure log values aligned with Version-derived values.
                    existing_old = _to_float(existing_row.get("old_value"))
                    existing_new = _to_float(existing_row.get("new_value"))
                    if abs(existing_old - old_value) > 1e-9 or abs(existing_new - new_value) > 1e-9:
                        existing_row.old_value = old_value
                        existing_row.new_value = new_value
                        existing_row.currency = existing_row.get("currency") or st.get("currency")
                        added_count += 1
                    continue

                _append_structure_log_row(
                    st,
                    salary_component=comp_name,
                    old_value=old_value,
                    new_value=new_value,
                    altered_at=version.creation,
                    altered_by=version.owner,
                )
                existing_by_identity[identity] = True
                added_count += 1

    return added_count

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

    old_amount = _to_float(target_row.get("amount") if target_row else 0)
    new_amount = _to_float(new_amount)

    if not target_row:
        target_row = draft.append(target_tbl, {
            "salary_component": component,
            "amount": new_amount,
        })
    else:
        target_row.amount = new_amount

    _append_structure_log_row(
        draft,
        salary_component=component,
        old_value=old_amount,
        new_value=new_amount,
    )

    draft.save(ignore_permissions=False)

    if int(submit_after or 0) == 1:
        try:
            draft.on_update_after_submit()
        except Exception:
            frappe.clear_messages()
            return {"structure_name": draft.name, "amended": amended, "submitted": 0}

    return {"structure_name": draft.name, "amended": amended, "submitted": int(draft.docstatus == 1)}

@frappe.whitelist()
def get_salary_alteration_history(employee: str, sync_from_version: int = 0):
    """Return salary alteration logs from Salary Structure child table only (no Version sync)."""
    frappe.only_for(("System Manager", "HR Manager", "HR User"), message=_("Not permitted"))

    row = _find_employee_structure(employee)
    if not row:
        return {"structure": None, "currency": None, "logs": []}

    st = frappe.get_doc("Salary Structure", row.name)
    if int(sync_from_version or 0) == 1:
        added = _sync_logs_from_versions(st)
        if added:
            st.save(ignore_permissions=True)

    log_rows = st.get(ALTERATION_LOG_TABLE_FIELD) or []
    logs = []
    for item in sorted(log_rows, key=lambda x: x.get("altered_at") or "", reverse=True):
        logs.append({
            "salary_component": item.get("salary_component") or "",
            "old_value": _to_float(item.get("old_value")),
            "new_value": _to_float(item.get("new_value")),
            "currency": item.get("currency") or st.get("currency"),
            "altered_at": item.get("altered_at"),
            "altered_by": item.get("altered_by"),
        })

    return {
        "structure": st.name,
        "currency": st.get("currency"),
        "logs": logs,
    }
