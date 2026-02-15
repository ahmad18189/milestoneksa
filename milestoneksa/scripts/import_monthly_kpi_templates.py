# Copyright (c) 2025, Milestone KSA and contributors
# License: GNU General Public License v3. See license.txt

"""
Import monthly KPI templates: KRAs (Arabic) + Appraisal Templates per employee.
Idempotent: KRAs upserted by title; templates upserted by name with goals replaced each run.

Run from bench (site milestoneksa.com):
  bench --site milestoneksa.com console
  >>> from milestoneksa.milestoneksa.scripts.import_monthly_kpi_templates import main
  >>> main()   # uses EXTRACTED_DATA
  >>> main(file_path="/path/to/kpi_data.json")   # optional: load from JSON

Or:
  bench --site milestoneksa.com execute milestoneksa.milestoneksa.scripts.import_monthly_kpi_templates.main
"""

from __future__ import unicode_literals

import json
import frappe
from frappe import _


# --- Data from KPI - الشهري.xlsx -----------------------------------------------

EXTRACTED_DATA = {
    "أحمد الحاج": [
        {"kra_title": "سرعة الاستجابة على البريد الالكتروني", "kra_description": "الالتزام بالرد السريع والمهني على جميع الايميلات الرسمية", "weightage": 10},
        {"kra_title": "التقارير الأسبوعية", "kra_description": "الالتزام بإرسال التقارير الأسبوعية في موعدها وبجودة ودقة", "weightage": 10},
        {"kra_title": "التفاعل عبر الواتساب للشركة", "kra_description": "الرد المهني والسريع على مراسلات العمل", "weightage": 10},
        {"kra_title": "التعامل الداخلي", "kra_description": "الاحترام المهني والتعاون مع الزملاء داخل الشركة", "weightage": 10},
        {"kra_title": "التعامل الخارجي", "kra_description": "تمثيل الشركة بصورة لائقة مع الجهات والعملاء", "weightage": 10},
        {"kra_title": "الانضباط الوظيفي", "kra_description": "الالتزام بمواعيد الدوام والحضور", "weightage": 10},
        {"kra_title": "رفع البيانات على النظام", "kra_description": "إدخال البيانات بشكل صحيح ودقيق", "weightage": 10},
        {"kra_title": "تحديث بيانات القسم", "kra_description": "تحديث بيانات القسم بشكل مستمر ودوري على النظام", "weightage": 10},
        {"kra_title": "حضور الاجتماعات", "kra_description": "الالتزام بحضور الاجتماعات الدورية للشركة", "weightage": 10},
        {"kra_title": "مراقية المشاريع وتسليمها", "kra_description": "المتابعة الميدانية - التزام المقاولين بالتنفيذ - تسليم المشاريع", "weightage": 10},
    ],
    "خالد بن ظفير": [
        {"kra_title": "سرعة الاستجابة على البريد الالكتروني", "kra_description": "الالتزام بالرد السريع والمهني على جميع الايميلات الرسمية", "weightage": 10},
        {"kra_title": "التقارير الأسبوعية", "kra_description": "الالتزام بإرسال التقارير الأسبوعية في موعدها وبجودة ودقة", "weightage": 10},
        {"kra_title": "التفاعل عبر الواتساب للشركة", "kra_description": "الرد المهني والسريع على مراسلات العمل", "weightage": 10},
        {"kra_title": "التعامل الداخلي", "kra_description": "الاحترام المهني والتعاون مع الزملاء داخل الشركة", "weightage": 10},
        {"kra_title": "التعامل الخارجي", "kra_description": "تمثيل الشركة بصورة لائقة مع الجهات والعملاء", "weightage": 10},
        {"kra_title": "الانضباط الوظيفي", "kra_description": "الالتزام بمواعيد الدوام والحضور", "weightage": 10},
        {"kra_title": "متابعة الأعمال المطلوبة", "kra_description": "انهاء وإنجاز الأعمال", "weightage": 10},
        {"kra_title": "سرعة الاستجابة والتواصل", "kra_description": "مدى التواصل مع الجهات الحكومية", "weightage": 10},
        {"kra_title": "حضور الاجتماعات", "kra_description": "الالتزام بحضور الاجتماعات الدورية للشركة", "weightage": 10},
        {"kra_title": "التفاعل والانجاز في الاجتماعات", "kra_description": "المشاركة الفعالة وتحقيق مخرجات واضحة", "weightage": 10},
    ],
    "محمد الناصر": [
        {"kra_title": "سرعة الاستجابة على البريد الالكتروني", "kra_description": "الالتزام بالرد السريع والمهني على جميع الايميلات الرسمية", "weightage": 10},
        {"kra_title": "التقارير الأسبوعية", "kra_description": "الالتزام بإرسال التقارير الأسبوعية في موعدها وبجودة ودقة", "weightage": 10},
        {"kra_title": "التفاعل عبر الواتساب للشركة", "kra_description": "الرد المهني والسريع على مراسلات العمل", "weightage": 10},
        {"kra_title": "التعامل الداخلي", "kra_description": "الاحترام المهني والتعاون مع الزملاء داخل الشركة", "weightage": 10},
        {"kra_title": "التعاون مع الإدارات", "kra_description": "الشئون الإدارية - المشاريع - التسويق والمبيعات", "weightage": 10},
        {"kra_title": "الانضباط الوظيفي", "kra_description": "الالتزام بمواعيد الدوام والحضور", "weightage": 10},
        {"kra_title": "رفع البيانات على النظام", "kra_description": "إدخال البيانات بشكل صحيح ودقيق", "weightage": 10},
        {"kra_title": "تحديث بيانات القسم", "kra_description": "تحديث بيانات القسم بشكل مستمر ودوري على النظام", "weightage": 10},
        {"kra_title": "حضور الاجتماعات", "kra_description": "الالتزام بحضور الاجتماعات الدورية للشركة", "weightage": 10},
        {"kra_title": "التفاعل والانجاز في الاجتماعات", "kra_description": "المشاركة الفعالة وتحقيق مخرجات واضحة", "weightage": 10},
    ],
    "أحمد عبدالرحمن": [
        {"kra_title": "سرعة الاستجابة على البريد الالكتروني", "kra_description": "الالتزام بالرد السريع والمهني على جميع الايميلات الرسمية", "weightage": 10},
        {"kra_title": "التقارير الأسبوعية", "kra_description": "الالتزام بإرسال التقارير الأسبوعية في موعدها وبجودة ودقة", "weightage": 10},
        {"kra_title": "التفاعل عبر الواتساب للشركة", "kra_description": "الرد المهني والسريع على مراسلات العمل", "weightage": 10},
        {"kra_title": "التعامل الداخلي", "kra_description": "الاحترام المهني والتعاون مع الزملاء داخل الشركة", "weightage": 10},
        {"kra_title": "التعامل الخارجي", "kra_description": "تمثيل الشركة بصورة لائقة مع الجهات والعملاء", "weightage": 10},
        {"kra_title": "الانضباط الوظيفي", "kra_description": "الالتزام بمواعيد الدوام والحضور", "weightage": 10},
        {"kra_title": "التخطيط والتطوير", "kra_description": "تطوير الأنظمة", "weightage": 10},
        {"kra_title": "أمن المعلومات", "kra_description": "تطبيق سياسات أمن المعلومات", "weightage": 10},
        {"kra_title": "حضور الاجتماعات", "kra_description": "الالتزام بحضور الاجتماعات الدورية للشركة", "weightage": 10},
        {"kra_title": "التفاعل والانجاز في الاجتماعات", "kra_description": "المشاركة الفعالة وتحقيق مخرجات واضحة", "weightage": 10},
    ],
    "نجود العصفور": [
        {"kra_title": "سرعة الاستجابة على البريد الالكتروني", "kra_description": "الالتزام بالرد السريع والمهني على جميع الايميلات الرسمية", "weightage": 10},
        {"kra_title": "التقارير الأسبوعية", "kra_description": "الالتزام بإرسال التقارير الأسبوعية في موعدها وبجودة ودقة", "weightage": 10},
        {"kra_title": "التفاعل عبر الواتساب للشركة", "kra_description": "الرد المهني والسريع على مراسلات العمل", "weightage": 10},
        {"kra_title": "التعامل الداخلي", "kra_description": "الاحترام المهني والتعاون مع الزملاء داخل الشركة", "weightage": 10},
        {"kra_title": "التعامل الخارجي", "kra_description": "تمثيل الشركة بصورة لائقة مع الجهات والعملاء", "weightage": 10},
        {"kra_title": "الانضباط الوظيفي", "kra_description": "الالتزام بمواعيد الدوام والحضور", "weightage": 10},
        {"kra_title": "الرقم الموحد", "kra_description": "الالتزام بالرد على المكالمات", "weightage": 10},
        {"kra_title": "تصوير المشاريع", "kra_description": "جودة التصوير", "weightage": 10},
        {"kra_title": "حضور الاجتماعات", "kra_description": "الالتزام بحضور الاجتماعات الدورية للشركة", "weightage": 10},
        {"kra_title": "التفاعل والانجاز في الاجتماعات", "kra_description": "المشاركة الفعالة وتحقيق مخرجات واضحة", "weightage": 10},
    ],
    "محمد اقطيفان": [
        {"kra_title": "سرعة الاستجابة على البريد الالكتروني", "kra_description": "الالتزام بالرد السريع والمهني على جميع الايميلات الرسمية", "weightage": 10},
        {"kra_title": "التقارير الأسبوعية", "kra_description": "الالتزام بإرسال التقارير الأسبوعية في موعدها وبجودة ودقة", "weightage": 10},
        {"kra_title": "التفاعل عبر الواتساب للشركة", "kra_description": "الرد المهني والسريع على مراسلات العمل", "weightage": 10},
        {"kra_title": "التعامل الداخلي", "kra_description": "الاحترام المهني والتعاون مع الزملاء داخل الشركة", "weightage": 10},
        {"kra_title": "التعامل الخارجي", "kra_description": "تمثيل الشركة بصورة لائقة مع الجهات والعملاء", "weightage": 10},
        {"kra_title": "الانضباط الوظيفي", "kra_description": "الالتزام بمواعيد الدوام والحضور", "weightage": 10},
        {"kra_title": "دعم الإدارات", "kra_description": "تلبية الطلبات الإدارية حسب الأنظمة والقوانين", "weightage": 10},
        {"kra_title": "السرية والخصوصية", "kra_description": "حماية البيانات والحفاظ على سرية المعلومات", "weightage": 10},
        {"kra_title": "حضور الاجتماعات", "kra_description": "الالتزام بحضور الاجتماعات الدورية للشركة", "weightage": 10},
        {"kra_title": "التفاعل والانجاز في الاجتماعات", "kra_description": "المشاركة الفعالة وتحقيق مخرجات واضحة", "weightage": 10},
    ],
}


# --- Meta inspection for Appraisal Template ------------------------------------

def _appraisal_template_goal_fieldnames():
    """Detect goals child table field, KRA link, weight, description from meta."""
    meta = frappe.get_meta("Appraisal Template")
    goals_field = "goals"
    for f in meta.fields:
        if f.fieldtype == "Table" and (f.options or "").lower().find("appraisal") >= 0:
            goals_field = f.fieldname
            break

    goal_meta = frappe.get_meta("Appraisal Template Goal")
    kra_field = None
    weight_field = None
    desc_field = None
    for fn in ("kra", "key_result_area"):
        if goal_meta.has_field(fn):
            kra_field = fn
            break
    if not kra_field:
        kra_field = "key_result_area"
    for fn in ("weightage", "per_weightage", "weight"):
        if goal_meta.has_field(fn):
            weight_field = fn
            break
    if not weight_field:
        weight_field = "per_weightage"
    for fn in ("description", "goal_description"):
        if goal_meta.has_field(fn):
            desc_field = fn
            break
    return goals_field, kra_field, weight_field, desc_field


def _kra_title_and_description_fields():
    """Return (title_field, description_field) for KRA doctype."""
    meta = frappe.get_meta("KRA")
    title_field = "title" if meta.has_field("title") else "name"
    desc_field = "description" if meta.has_field("description") else None
    return title_field, desc_field


# --- KRA upsert ---------------------------------------------------------------

def _upsert_kra(kra_title: str, kra_description: str = "", title_fld: str = "title", desc_fld: str | None = "description") -> str:
    """Create or update KRA by Arabic title. Returns KRA name."""
    name = frappe.db.exists("KRA", {title_fld: kra_title})
    if name:
        doc = frappe.get_doc("KRA", name)
        if desc_fld and (doc.get(desc_fld) or "") != (kra_description or ""):
            doc.set(desc_fld, kra_description or "")
            doc.flags.ignore_permissions = True
            doc.save()
        return name
    doc = frappe.new_doc("KRA")
    doc.set(title_fld, kra_title)
    if desc_fld:
        doc.set(desc_fld, kra_description or "")
    doc.flags.ignore_permissions = True
    doc.insert()
    return doc.name


# --- Appraisal Template upsert -----------------------------------------------

def _upsert_appraisal_template(
    employee_name: str,
    kpi_rows: list,
    goals_fld: str,
    kra_fld: str,
    weight_fld: str,
    desc_fld: str | None,
    kra_name_by_title: dict,
    employee_id: str | None = None,
) -> str:
    """Create or update Appraisal Template for employee; replace goals each run. Returns template name."""
    template_title = "تقييم شهري - " + employee_name
    existing = frappe.db.exists("Appraisal Template", {"template_title": template_title})
    if existing:
        doc = frappe.get_doc("Appraisal Template", existing)
    else:
        doc = frappe.new_doc("Appraisal Template")
        doc.template_title = template_title

    # Best-effort: link template to Employee if field exists and employee_id provided
    if employee_id and doc.meta.has_field("custom_employee"):
        doc.set("custom_employee", employee_id)

    # Clear and re-add goals (use pre-resolved KRA names)
    doc.set(goals_fld, [])
    for row in kpi_rows:
        kra_name = kra_name_by_title.get(row["kra_title"])
        if not kra_name:
            continue
        goal = doc.append(goals_fld, {})
        goal.set(kra_fld, kra_name)
        goal.set(weight_fld, row.get("weightage", 10))
        if desc_fld and row.get("kra_description"):
            goal.set(desc_fld, row["kra_description"])

    doc.flags.ignore_permissions = True
    doc.save()
    return doc.name


# --- Main import logic -------------------------------------------------------

def run(file_path: str | None = None):
    """Load data from file_path (JSON dict like EXTRACTED_DATA) or use EXTRACTED_DATA. Returns summary dict."""
    if file_path:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = EXTRACTED_DATA

    goals_fld, kra_fld, weight_fld, desc_fld = _appraisal_template_goal_fieldnames()
    title_fld, kra_desc_fld = _kra_title_and_description_fields()

    # 1) Collect unique KRAs by title only (no duplicate KRAs); first-seen description wins
    seen_titles = {}
    for rows in data.values():
        for r in rows:
            t = r["kra_title"]
            if t not in seen_titles:
                seen_titles[t] = r.get("kra_description", "")
    kras_created = 0
    kras_updated = 0
    kra_name_by_title = {}
    for kra_title, kra_desc in seen_titles.items():
        existed = frappe.db.exists("KRA", {title_fld: kra_title})
        name = _upsert_kra(kra_title, kra_desc, title_fld, kra_desc_fld)
        kra_name_by_title[kra_title] = name
        if existed:
            kras_updated += 1
        else:
            kras_created += 1

    # 2) Per-employee: upsert template by employee name key (replace goals)
    templates_created = 0
    templates_updated = 0
    for employee_key, rows in data.items():
        display_name = employee_key
        template_title = "تقييم شهري - " + display_name
        existed = frappe.db.exists("Appraisal Template", {"template_title": template_title})
        employee_id = frappe.db.get_value("Employee", {"employee_name": employee_key}, "name") or frappe.db.get_value(
            "Employee", {"name": employee_key}, "name"
        )
        _upsert_appraisal_template(
            display_name,
            rows,
            goals_fld,
            kra_fld,
            weight_fld,
            desc_fld,
            kra_name_by_title,
            employee_id=employee_id,
        )
        if existed:
            templates_updated += 1
        else:
            templates_created += 1

    return {
        "kras_created": kras_created,
        "kras_updated": kras_updated,
        "templates_created": templates_created,
        "templates_updated": templates_updated,
    }


def main(file_path: str | None = None):
    """Entry point for bench execute. Optionally pass path to JSON file with same structure as EXTRACTED_DATA."""
    summary = run(file_path=file_path)
    frappe.db.commit()

    print("\n--- Import monthly KPI templates — summary ---")
    print("KRAs created:     ", summary["kras_created"])
    print("KRAs updated:     ", summary["kras_updated"])
    print("Templates created:", summary["templates_created"])
    print("Templates updated:", summary["templates_updated"])
    print("--- Done ---\n")


if __name__ == "__main__":
    import sys
    file_path = sys.argv[1] if len(sys.argv) > 1 else None
    main(file_path=file_path)
