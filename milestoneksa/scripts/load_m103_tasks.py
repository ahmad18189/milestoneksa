import frappe
from frappe.utils import getdate
from datetime import datetime


def _parse_date(s: str):
	# accepts "03-Nov-2025"
	return getdate(datetime.strptime(s, "%d-%b-%Y"))


def execute(project: str = "Milestone-103"):
	"""
	Load Milestone-103 task hierarchy (idempotent).
	Creates missing tasks, updates existing tasks (dates/is_group/parent).
	"""

	if not frappe.db.exists("Project", project):
		frappe.throw(f"Project {project} not found")

	rows = [
		{"subject": "Project (M-103 Dahrat Laban)", "parent_subject": None, "is_group": 1, "exp_start_date": "03-Nov-2025", "exp_end_date": "27-Jul-2026"},
		{"subject": "Project Proposal (مقترح المشروع)", "parent_subject": "Project (M-103 Dahrat Laban)", "is_group": 0, "exp_start_date": "03-Nov-2025", "exp_end_date": "03-Nov-2025"},
		{"subject": "Proposal Approval (اعتماد مقترح المشروع)", "parent_subject": "Project (M-103 Dahrat Laban)", "is_group": 0, "exp_start_date": "03-Dec-2025", "exp_end_date": "03-Dec-2025"},
		{"subject": "License Receipt (استلام الرخصة)", "parent_subject": "Project (M-103 Dahrat Laban)", "is_group": 0, "exp_start_date": "05-Jan-2026", "exp_end_date": "05-Jan-2026"},
		{"subject": "Start Execution (البدء في التنفيذ)", "parent_subject": "Project (M-103 Dahrat Laban)", "is_group": 0, "exp_start_date": "05-Jan-2026", "exp_end_date": "05-Jan-2026"},
		{"subject": "Finish Foundations + Insulation (انهاء الاساسات والعزل)", "parent_subject": "Project (M-103 Dahrat Laban)", "is_group": 0, "exp_start_date": "23-Feb-2026", "exp_end_date": "23-Feb-2026"},
		{"subject": "Finish Structure + Start Finishing (انهاء العظم - بداية التشطيب)", "parent_subject": "Project (M-103 Dahrat Laban)", "is_group": 0, "exp_start_date": "06-Apr-2026", "exp_end_date": "06-Apr-2026"},
		{"subject": "Finish Licenses + Start Marketing (انهاء الرخص - بدأ التسويق)", "parent_subject": "Project (M-103 Dahrat Laban)", "is_group": 0, "exp_start_date": "01-Jun-2026", "exp_end_date": "01-Jun-2026"},
		{"subject": "Project Benefits & Marketing (تحقيق منافع المشروع والتسويق)", "parent_subject": "Project (M-103 Dahrat Laban)", "is_group": 0, "exp_start_date": "26-Jun-2026", "exp_end_date": "26-Jun-2026"},
		{"subject": "Customer Satisfaction Survey (استبيان رضاء العملاء والمستأجرين)", "parent_subject": "Project (M-103 Dahrat Laban)", "is_group": 0, "exp_start_date": "27-Jul-2026", "exp_end_date": "27-Jul-2026"},
		{"subject": "Construction Work (أعمال المنشأ)", "parent_subject": "Project (M-103 Dahrat Laban)", "is_group": 1, "exp_start_date": "05-Jan-2026", "exp_end_date": "27-Jul-2026"},
		{"subject": "Sub-Structure Procurement (مشتريات الأعمال التحتية)", "parent_subject": "Construction Work (أعمال المنشأ)", "is_group": 0, "exp_start_date": "05-Jan-2026", "exp_end_date": "20-Jan-2026"},
		{"subject": "Sub-Structure Works (أعمال التحتية)", "parent_subject": "Construction Work (أعمال المنشأ)", "is_group": 0, "exp_start_date": "21-Jan-2026", "exp_end_date": "23-Feb-2026"},
		{"subject": "Super Structure Procurement (مشتريات الهيكل)", "parent_subject": "Construction Work (أعمال المنشأ)", "is_group": 0, "exp_start_date": "24-Feb-2026", "exp_end_date": "10-Mar-2026"},
		{"subject": "Super Structure Works (أعمال الهيكل العلوي)", "parent_subject": "Construction Work (أعمال المنشأ)", "is_group": 0, "exp_start_date": "11-Mar-2026", "exp_end_date": "06-Apr-2026"},
		{"subject": "MEP Procurement (مشتريات الالكتروميكانيك)", "parent_subject": "Construction Work (أعمال المنشأ)", "is_group": 0, "exp_start_date": "07-Apr-2026", "exp_end_date": "20-Apr-2026"},
		{"subject": "Finishing Procurement (مشتريات التشطيب)", "parent_subject": "Construction Work (أعمال المنشأ)", "is_group": 0, "exp_start_date": "07-Apr-2026", "exp_end_date": "25-Apr-2026"},
		{"subject": "MEP Works (تنفيذ اعمال الالكتروميكانيك)", "parent_subject": "Construction Work (أعمال المنشأ)", "is_group": 0, "exp_start_date": "21-Apr-2026", "exp_end_date": "15-May-2026"},
		{"subject": "Finishing Works (تنفيذ التشطيب)", "parent_subject": "Construction Work (أعمال المنشأ)", "is_group": 0, "exp_start_date": "26-Apr-2026", "exp_end_date": "01-Jun-2026"},
		{"subject": "Project Deliveries (تسليمات المشروع)", "parent_subject": "Construction Work (أعمال المنشأ)", "is_group": 0, "exp_start_date": "15-May-2026", "exp_end_date": "26-Jun-2026"},
		{"subject": "Procurement Closer (اغلاق المشتريات والفواتير)", "parent_subject": "Construction Work (أعمال المنشأ)", "is_group": 0, "exp_start_date": "02-Jun-2026", "exp_end_date": "26-Jun-2026"},
		{"subject": "Project Closer (اغلاق المشروع + الدروس المستفادة)", "parent_subject": "Construction Work (أعمال المنشأ)", "is_group": 0, "exp_start_date": "27-Jun-2026", "exp_end_date": "27-Jul-2026"},
	]

	existing = frappe.get_all(
		"Task",
		filters={"project": project},
		fields=["name", "subject", "parent_task", "is_group", "exp_start_date", "exp_end_date"],
		limit_page_length=0,
	)

	by_subject = {}
	for t in existing:
		by_subject.setdefault(t.subject, []).append(t)

	subject_to_taskname = {}
	created, updated, unchanged = [], [], []

	pending = list(rows)
	progress = True

	while pending and progress:
		progress = False
		next_pending = []

		for r in pending:
			subject = r["subject"]
			parent_subject = r.get("parent_subject")

			parent_name = None
			if parent_subject:
				parent_name = subject_to_taskname.get(parent_subject)
				if not parent_name:
					cands = by_subject.get(parent_subject) or []
					if cands:
						parent_name = cands[0].name
						subject_to_taskname[parent_subject] = parent_name
				if not parent_name:
					next_pending.append(r)
					continue

			exp_start = _parse_date(r["exp_start_date"])
			exp_end = _parse_date(r["exp_end_date"])
			is_group = int(r.get("is_group") or 0)

			cands = by_subject.get(subject) or []
			chosen = None
			for c in cands:
				if (c.parent_task or None) == (parent_name or None):
					chosen = c
					break
			if not chosen and cands:
				chosen = cands[0]

			if chosen:
				doc = frappe.get_doc("Task", chosen.name)
				changed = False

				if doc.project != project:
					doc.project = project
					changed = True
				if (doc.parent_task or None) != (parent_name or None):
					doc.parent_task = parent_name
					changed = True
				if int(doc.is_group or 0) != is_group:
					doc.is_group = is_group
					changed = True
				if doc.exp_start_date != exp_start:
					doc.exp_start_date = exp_start
					changed = True
				if doc.exp_end_date != exp_end:
					doc.exp_end_date = exp_end
					changed = True

				if changed:
					doc.save(ignore_permissions=True)
					updated.append(doc.name)
				else:
					unchanged.append(doc.name)

				subject_to_taskname[subject] = doc.name
				progress = True
				continue

			# Create new
			doc = frappe.new_doc("Task")
			doc.update(
				{
					"project": project,
					"subject": subject,
					"is_group": is_group,
					"parent_task": parent_name,
					"status": "Open",
					"exp_start_date": exp_start,
					"exp_end_date": exp_end,
				}
			)
			doc.insert(ignore_permissions=True)
			created.append(doc.name)
			subject_to_taskname[subject] = doc.name

			by_subject.setdefault(subject, []).append(
				frappe._dict(
					name=doc.name,
					subject=doc.subject,
					parent_task=doc.parent_task,
					is_group=doc.is_group,
					exp_start_date=doc.exp_start_date,
					exp_end_date=doc.exp_end_date,
				)
			)
			progress = True

		pending = next_pending

	if pending:
		frappe.throw(f"Could not resolve parents for {len(pending)} tasks: {[p['subject'] for p in pending]}")

	frappe.db.commit()

	return {
		"project": project,
		"created": created,
		"updated": updated,
		"unchanged": unchanged,
	}

