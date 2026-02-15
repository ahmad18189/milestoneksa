# -*- coding: utf-8 -*-
"""
Create Project Proposal Doctype System
Includes main doctype, child tables, templates, workflow, and dashboard
"""
import frappe
from frappe.utils import now


def _ensure_doctype(name, **kwargs):
	"""
	Idempotently create a DocType if it doesn't exist.
	Returns the DocType doc (existing or newly created).
	"""
	if frappe.db.exists("DocType", name):
		print(f"DocType '{name}' already exists, skipping...")
		return frappe.get_doc("DocType", name)

	doc = frappe.new_doc("DocType")
	doc.update({"name": name, **kwargs})
	doc.insert(ignore_permissions=True)
	print(f"✅ Created DocType: {name}")
	return doc


def create_child_table_doctypes():
	"""Create all child table DocTypes"""
	
	# 1. Project Team Member
	_ensure_doctype(
		"Project Team Member",
		module="milestoneksa",
		istable=1,
		editable_grid=1,
		track_changes=0,
		custom=0,
		allow_copy=0,
		allow_rename=0,
		engine="InnoDB",
		fields=[
			{"fieldname": "employee", "label": "Employee", "fieldtype": "Link", "options": "Employee", "reqd": 1, "in_list_view": 1},
			{"fieldname": "employee_name", "label": "Employee Name", "fieldtype": "Data", "fetch_from": "employee.employee_name", "read_only": 1, "in_list_view": 1},
			{"fieldname": "role", "label": "Role", "fieldtype": "Data", "reqd": 1, "in_list_view": 1},
			{"fieldname": "department", "label": "Department", "fieldtype": "Link", "options": "Department", "fetch_from": "employee.department"},
			{"fieldname": "responsibilities", "label": "Responsibilities", "fieldtype": "Small Text"},
			{"fieldname": "start_date", "label": "Start Date", "fieldtype": "Date"},
			{"fieldname": "end_date", "label": "End Date", "fieldtype": "Date"},
		],
		permissions=[]
	)

	# 2. Project Evaluation Report
	_ensure_doctype(
		"Project Evaluation Report",
		module="milestoneksa",
		istable=1,
		editable_grid=1,
		track_changes=0,
		custom=0,
		allow_copy=0,
		allow_rename=0,
		engine="InnoDB",
		fields=[
			{"fieldname": "evaluation_type", "label": "Evaluation Type", "fieldtype": "Select", "options": "Projects Management\nFinancial Management", "reqd": 1, "in_list_view": 1},
			{"fieldname": "evaluated_by", "label": "Evaluated By", "fieldtype": "Link", "options": "User", "reqd": 1},
			{"fieldname": "evaluation_date", "label": "Evaluation Date", "fieldtype": "Date", "default": "Today", "reqd": 1},
			{"fieldname": "feasibility_status", "label": "Feasibility Status", "fieldtype": "Select", "options": "Feasible\nNot Feasible\nConditional", "reqd": 1},
			{"fieldname": "estimated_cost", "label": "Estimated Cost (SAR)", "fieldtype": "Currency"},
			{"fieldname": "estimated_duration", "label": "Estimated Duration (Days)", "fieldtype": "Int"},
			{"fieldname": "regulatory_requirements", "label": "Regulatory Requirements", "fieldtype": "Small Text"},
			{"fieldname": "risks", "label": "Risks", "fieldtype": "Small Text"},
			{"fieldname": "recommendations", "label": "Recommendations", "fieldtype": "Text Editor"},
			{"fieldname": "roi_estimate", "label": "ROI Estimate (%)", "fieldtype": "Percent"},
			{"fieldname": "financial_risks", "label": "Financial Risks", "fieldtype": "Small Text"},
			{"fieldname": "attachment", "label": "Attachment", "fieldtype": "Attach"},
		],
		permissions=[]
	)

	# 3. Project Feasibility Item
	_ensure_doctype(
		"Project Feasibility Item",
		module="milestoneksa",
		istable=1,
		editable_grid=1,
		track_changes=0,
		custom=0,
		allow_copy=0,
		allow_rename=0,
		engine="InnoDB",
		fields=[
			{"fieldname": "item_type", "label": "Item Type", "fieldtype": "Select", "options": "BOQ Item\nLayout Item\nFinancial Projection", "reqd": 1, "in_list_view": 1},
			{"fieldname": "item_code", "label": "Item Code", "fieldtype": "Data", "in_list_view": 1},
			{"fieldname": "item_name", "label": "Item Name", "fieldtype": "Data", "reqd": 1, "in_list_view": 1},
			{"fieldname": "description", "label": "Description", "fieldtype": "Small Text"},
			{"fieldname": "quantity", "label": "Quantity", "fieldtype": "Float"},
			{"fieldname": "uom", "label": "UOM", "fieldtype": "Link", "options": "UOM"},
			{"fieldname": "unit_rate", "label": "Unit Rate (SAR)", "fieldtype": "Currency"},
			{"fieldname": "amount", "label": "Amount (SAR)", "fieldtype": "Currency", "read_only": 1},
			{"fieldname": "year", "label": "Year", "fieldtype": "Int", "depends_on": "eval:doc.item_type=='Financial Projection'"},
			{"fieldname": "cash_flow", "label": "Cash Flow (SAR)", "fieldtype": "Currency", "depends_on": "eval:doc.item_type=='Financial Projection'"},
		],
		permissions=[]
	)

	# 4. Project License
	_ensure_doctype(
		"Project License",
		module="milestoneksa",
		istable=1,
		editable_grid=1,
		track_changes=0,
		custom=0,
		allow_copy=0,
		allow_rename=0,
		engine="InnoDB",
		fields=[
			{"fieldname": "license_type", "label": "License Type", "fieldtype": "Select", "options": "Municipality\nElectricity\nWater\nCivil Defense", "reqd": 1, "in_list_view": 1},
			{"fieldname": "license_number", "label": "License Number", "fieldtype": "Data", "in_list_view": 1},
			{"fieldname": "application_date", "label": "Application Date", "fieldtype": "Date"},
			{"fieldname": "issue_date", "label": "Issue Date", "fieldtype": "Date"},
			{"fieldname": "expiry_date", "label": "Expiry Date", "fieldtype": "Date"},
			{"fieldname": "status", "label": "Status", "fieldtype": "Select", "options": "Pending\nApproved\nRejected\nExpired", "default": "Pending", "in_list_view": 1},
			{"fieldname": "attachment", "label": "License Document", "fieldtype": "Attach"},
			{"fieldname": "remarks", "label": "Remarks", "fieldtype": "Small Text"},
		],
		permissions=[]
	)

	# 5. Project Contractor Offer
	_ensure_doctype(
		"Project Contractor Offer",
		module="milestoneksa",
		istable=1,
		editable_grid=1,
		track_changes=0,
		custom=0,
		allow_copy=0,
		allow_rename=0,
		engine="InnoDB",
		fields=[
			{"fieldname": "contractor", "label": "Contractor", "fieldtype": "Link", "options": "Supplier", "reqd": 1, "in_list_view": 1},
			{"fieldname": "contractor_name", "label": "Contractor Name", "fieldtype": "Data", "fetch_from": "contractor.supplier_name", "read_only": 1, "in_list_view": 1},
			{"fieldname": "offer_date", "label": "Offer Date", "fieldtype": "Date", "default": "Today", "reqd": 1},
			{"fieldname": "total_amount", "label": "Total Amount (SAR)", "fieldtype": "Currency", "reqd": 1, "in_list_view": 1},
			{"fieldname": "validity_date", "label": "Validity Date", "fieldtype": "Date"},
			{"fieldname": "duration_days", "label": "Duration (Days)", "fieldtype": "Int"},
			{"fieldname": "payment_terms", "label": "Payment Terms", "fieldtype": "Small Text"},
			{"fieldname": "warranty_period", "label": "Warranty Period (Months)", "fieldtype": "Int"},
			{"fieldname": "status", "label": "Status", "fieldtype": "Select", "options": "Received\nUnder Review\nAccepted\nRejected", "default": "Received", "in_list_view": 1},
			{"fieldname": "attachment", "label": "Offer Document", "fieldtype": "Attach"},
			{"fieldname": "remarks", "label": "Remarks", "fieldtype": "Small Text"},
		],
		permissions=[]
	)

	# 6. Project Weekly Report
	_ensure_doctype(
		"Project Weekly Report",
		module="milestoneksa",
		istable=1,
		editable_grid=1,
		track_changes=0,
		custom=0,
		allow_copy=0,
		allow_rename=0,
		engine="InnoDB",
		fields=[
			{"fieldname": "week_start_date", "label": "Week Start Date", "fieldtype": "Date", "reqd": 1, "in_list_view": 1},
			{"fieldname": "week_end_date", "label": "Week End Date", "fieldtype": "Date", "reqd": 1},
			{"fieldname": "reported_by", "label": "Reported By", "fieldtype": "Link", "options": "User", "reqd": 1},
			{"fieldname": "report_date", "label": "Report Date", "fieldtype": "Date", "default": "Today", "reqd": 1},
			{"fieldname": "progress_percentage", "label": "Progress (%)", "fieldtype": "Percent", "reqd": 1, "in_list_view": 1},
			{"fieldname": "work_completed", "label": "Work Completed", "fieldtype": "Text Editor", "reqd": 1},
			{"fieldname": "work_planned", "label": "Work Planned for Next Week", "fieldtype": "Text Editor"},
			{"fieldname": "issues_challenges", "label": "Issues/Challenges", "fieldtype": "Text Editor"},
			{"fieldname": "photos", "label": "Progress Photos", "fieldtype": "Attach Image"},
		],
		permissions=[]
	)

	# 7. Project Monthly Financial
	_ensure_doctype(
		"Project Monthly Financial",
		module="milestoneksa",
		istable=1,
		editable_grid=1,
		track_changes=0,
		custom=0,
		allow_copy=0,
		allow_rename=0,
		engine="InnoDB",
		fields=[
			{"fieldname": "month", "label": "Month", "fieldtype": "Select", "options": "January\nFebruary\nMarch\nApril\nMay\nJune\nJuly\nAugust\nSeptember\nOctober\nNovember\nDecember", "reqd": 1, "in_list_view": 1},
			{"fieldname": "year", "label": "Year", "fieldtype": "Int", "reqd": 1, "in_list_view": 1},
			{"fieldname": "reported_by", "label": "Reported By", "fieldtype": "Link", "options": "User", "reqd": 1},
			{"fieldname": "report_date", "label": "Report Date", "fieldtype": "Date", "default": "Today", "reqd": 1},
			{"fieldname": "budgeted_amount", "label": "Budgeted Amount (SAR)", "fieldtype": "Currency"},
			{"fieldname": "actual_spent", "label": "Actual Spent (SAR)", "fieldtype": "Currency", "reqd": 1, "in_list_view": 1},
			{"fieldname": "variance", "label": "Variance (SAR)", "fieldtype": "Currency", "read_only": 1, "in_list_view": 1},
			{"fieldname": "variance_percentage", "label": "Variance (%)", "fieldtype": "Percent", "read_only": 1},
			{"fieldname": "remarks", "label": "Remarks", "fieldtype": "Text Editor"},
			{"fieldname": "attachment", "label": "Financial Report", "fieldtype": "Attach"},
		],
		permissions=[]
	)

	# 8. Project Attachment
	_ensure_doctype(
		"Project Attachment",
		module="milestoneksa",
		istable=1,
		editable_grid=1,
		track_changes=0,
		custom=0,
		allow_copy=0,
		allow_rename=0,
		engine="InnoDB",
		fields=[
			{"fieldname": "document_type", "label": "Document Type", "fieldtype": "Select", "options": "Contract\nPlan\nPhoto\nInvoice\nReceipt\nOther", "reqd": 1, "in_list_view": 1},
			{"fieldname": "document_name", "label": "Document Name", "fieldtype": "Data", "reqd": 1, "in_list_view": 1},
			{"fieldname": "attachment", "label": "Attachment", "fieldtype": "Attach", "reqd": 1},
			{"fieldname": "upload_date", "label": "Upload Date", "fieldtype": "Date", "default": "Today"},
			{"fieldname": "uploaded_by", "label": "Uploaded By", "fieldtype": "Link", "options": "User", "read_only": 1},
			{"fieldname": "description", "label": "Description", "fieldtype": "Small Text"},
		],
		permissions=[]
	)

	# 9. Project Handover Item
	_ensure_doctype(
		"Project Handover Item",
		module="milestoneksa",
		istable=1,
		editable_grid=1,
		track_changes=0,
		custom=0,
		allow_copy=0,
		allow_rename=0,
		engine="InnoDB",
		fields=[
			{"fieldname": "item_description", "label": "Item Description", "fieldtype": "Data", "reqd": 1, "in_list_view": 1},
			{"fieldname": "category", "label": "Category", "fieldtype": "Select", "options": "Quality Check\nDocumentation\nEquipment\nSystem\nOther", "reqd": 1},
			{"fieldname": "status", "label": "Status", "fieldtype": "Select", "options": "Pending\nVerified\nNot Applicable", "default": "Pending", "reqd": 1, "in_list_view": 1},
			{"fieldname": "verified_by", "label": "Verified By", "fieldtype": "Link", "options": "User"},
			{"fieldname": "verification_date", "label": "Verification Date", "fieldtype": "Date"},
			{"fieldname": "remarks", "label": "Remarks", "fieldtype": "Small Text"},
			{"fieldname": "attachment", "label": "Verification Document", "fieldtype": "Attach"},
		],
		permissions=[]
	)

	# 10. Project BOQ Template (Child table for BOQ items)
	_ensure_doctype(
		"Project BOQ Template Item",
		module="milestoneksa",
		istable=1,
		editable_grid=1,
		track_changes=0,
		custom=0,
		allow_copy=0,
		allow_rename=0,
		engine="InnoDB",
		fields=[
			{"fieldname": "item_code", "label": "Item Code", "fieldtype": "Data", "in_list_view": 1},
			{"fieldname": "item_name", "label": "Item Name", "fieldtype": "Data", "reqd": 1, "in_list_view": 1},
			{"fieldname": "description", "label": "Description", "fieldtype": "Small Text"},
			{"fieldname": "quantity", "label": "Quantity", "fieldtype": "Float", "default": 1},
			{"fieldname": "uom", "label": "UOM", "fieldtype": "Link", "options": "UOM"},
			{"fieldname": "unit_rate", "label": "Unit Rate (SAR)", "fieldtype": "Currency"},
			{"fieldname": "amount", "label": "Amount (SAR)", "fieldtype": "Currency", "read_only": 1},
		],
		permissions=[]
	)

	# 11. Project Building Area Component
	_ensure_doctype(
		"Project Building Area Component",
		module="milestoneksa",
		istable=1,
		editable_grid=1,
		track_changes=0,
		custom=0,
		allow_copy=0,
		allow_rename=0,
		engine="InnoDB",
		fields=[
			{"fieldname": "floor_name", "label": "Floor/Level Name", "fieldtype": "Data", "reqd": 1, "in_list_view": 1},
			{"fieldname": "area_sqm", "label": "Area (m²)", "fieldtype": "Float", "reqd": 1, "in_list_view": 1},
			{"fieldname": "include_in_total", "label": "Include in Total", "fieldtype": "Check", "default": "1", "in_list_view": 1},
			{"fieldname": "percentage", "label": "Percentage (%)", "fieldtype": "Percent", "read_only": 1, "in_list_view": 1},
			{"fieldname": "number_of_units", "label": "Number of Units", "fieldtype": "Int", "in_list_view": 1},
			{"fieldname": "usage_type", "label": "Usage Type", "fieldtype": "Select", "options": "Commercial\nStorage\nServices\nResidential\nAdministrative\nMixed\nOther", "in_list_view": 1},
		],
		permissions=[]
	)

	# 12. Project Building Space
	_ensure_doctype(
		"Project Building Space",
		module="milestoneksa",
		istable=1,
		editable_grid=1,
		track_changes=0,
		custom=0,
		allow_copy=0,
		allow_rename=0,
		engine="InnoDB",
		fields=[
			{"fieldname": "space_name", "label": "Space/Unit Name or Number", "fieldtype": "Data", "reqd": 1, "in_list_view": 1},
			{"fieldname": "space_area", "label": "Area (m²)", "fieldtype": "Float", "reqd": 1, "in_list_view": 1},
			{"fieldname": "length", "label": "Length (m)", "fieldtype": "Float"},
			{"fieldname": "width", "label": "Width (m)", "fieldtype": "Float"},
			{"fieldname": "height", "label": "Height (m)", "fieldtype": "Float"},
			{"fieldname": "floor_location", "label": "Floor/Location", "fieldtype": "Data", "in_list_view": 1},
			{"fieldname": "usage_type", "label": "Usage Type", "fieldtype": "Select", "options": "Commercial\nStorage\nServices\nResidential\nAdministrative\nMixed\nOther"},
		],
		permissions=[]
	)


def create_template_doctypes():
	"""Create template DocTypes for reusable structures"""
	
	# 1. Project Team Member Template
	_ensure_doctype(
		"Project Team Member Template",
		module="milestoneksa",
		istable=0,
		editable_grid=0,
		track_changes=1,
		custom=0,
		allow_copy=1,
		allow_rename=1,
		engine="InnoDB",
		autoname="field:template_name",
		fields=[
			{"fieldname": "template_name", "label": "Template Name", "fieldtype": "Data", "reqd": 1, "unique": 1},
			{"fieldname": "project_type", "label": "Project Type", "fieldtype": "Select", "options": "Real Estate\nConstruction\nOperational"},
			{"fieldname": "description", "label": "Description", "fieldtype": "Small Text"},
			{"fieldname": "section_team", "label": "Team Members", "fieldtype": "Section Break"},
			{"fieldname": "team_members", "label": "Team Members", "fieldtype": "Table", "options": "Project Team Member"},
		],
		permissions=[
			{"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
			{"role": "Projects Manager", "read": 1, "write": 1, "create": 1},
		]
	)

	# 2. BOQ Template
	_ensure_doctype(
		"BOQ Template",
		module="milestoneksa",
		istable=0,
		editable_grid=0,
		track_changes=1,
		custom=0,
		allow_copy=1,
		allow_rename=1,
		engine="InnoDB",
		autoname="field:template_name",
		fields=[
			{"fieldname": "template_name", "label": "Template Name", "fieldtype": "Data", "reqd": 1, "unique": 1},
			{"fieldname": "project_type", "label": "Project Type", "fieldtype": "Select", "options": "Real Estate\nConstruction\nOperational"},
			{"fieldname": "description", "label": "Description", "fieldtype": "Small Text"},
			{"fieldname": "section_boq", "label": "BOQ Items", "fieldtype": "Section Break"},
			{"fieldname": "boq_items", "label": "BOQ Items", "fieldtype": "Table", "options": "Project BOQ Template Item"},
			{"fieldname": "total_amount", "label": "Total Amount (SAR)", "fieldtype": "Currency", "read_only": 1},
		],
		permissions=[
			{"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
			{"role": "Projects Manager", "read": 1, "write": 1, "create": 1},
		]
	)


def create_main_doctype():
	"""Create the main Project Proposal DocType with all tabs and fields"""
	
	fields = []
	
	# ========== PROPOSAL TAB ==========
	# Basic Information Section
	fields.extend([
		{"fieldname": "tab_proposal", "label": "Proposal", "fieldtype": "Tab Break"},
		{"fieldname": "section_basic_info", "label": "Basic Information", "fieldtype": "Section Break"},
		{"fieldname": "project_name", "label": "Project Name", "fieldtype": "Data", "reqd": 1, "in_list_view": 1},
		{"fieldname": "project_code", "label": "Project Code", "fieldtype": "Data", "unique": 1},
		{"fieldname": "project_type", "label": "Project Type", "fieldtype": "Select", "options": "Real Estate\nConstruction\nOperational", "reqd": 1, "in_list_view": 1},
		{"fieldname": "column_break_1", "fieldtype": "Column Break"},
		{"fieldname": "proposal_date", "label": "Proposal Date", "fieldtype": "Date", "default": "Today", "reqd": 1},
		{"fieldname": "location", "label": "Location/Address", "fieldtype": "Small Text", "reqd": 1},
		{"fieldname": "property_location", "label": "Property Location (if applicable)", "fieldtype": "Small Text"},
		
		# Proposer Information
		{"fieldname": "section_proposer", "label": "Proposer Information", "fieldtype": "Section Break"},
		{"fieldname": "employee", "label": "Employee (Proposer)", "fieldtype": "Link", "options": "Employee", "reqd": 1, "in_list_view": 1},
		{"fieldname": "employee_name", "label": "Employee Name", "fieldtype": "Data", "fetch_from": "employee.employee_name", "read_only": 1},
		{"fieldname": "department", "label": "Department", "fieldtype": "Link", "options": "Department", "fetch_from": "employee.department", "read_only": 1},
		{"fieldname": "column_break_2", "fieldtype": "Column Break"},
		{"fieldname": "investment_type", "label": "Type of Investment", "fieldtype": "Small Text"},
		{"fieldname": "expected_value", "label": "Expected Value/Feasibility", "fieldtype": "Small Text"},
		
		# Project Description
		{"fieldname": "section_description", "label": "Project Description", "fieldtype": "Section Break"},
		{"fieldname": "project_description", "label": "Project Description", "fieldtype": "Text Editor", "reqd": 1},
		{"fieldname": "supporting_documents", "label": "Supporting Documents", "fieldtype": "Table", "options": "Project Attachment"},
		
		# Initial Approvals
		{"fieldname": "section_approvals", "label": "Initial Approvals", "fieldtype": "Section Break"},
		{"fieldname": "deputy_ceo_approval", "label": "Deputy CEO Initial Approval", "fieldtype": "Select", "options": "Pending\nApproved\nRejected", "default": "Pending", "read_only": 1},
		{"fieldname": "deputy_ceo_approver", "label": "Deputy CEO", "fieldtype": "Link", "options": "User", "read_only": 1},
		{"fieldname": "deputy_ceo_approval_date", "label": "Deputy CEO Approval Date", "fieldtype": "Date", "read_only": 1},
		{"fieldname": "column_break_3", "fieldtype": "Column Break"},
		{"fieldname": "ceo_approval", "label": "CEO Final Approval", "fieldtype": "Select", "options": "Pending\nApproved\nRejected", "default": "Pending", "read_only": 1},
		{"fieldname": "ceo_approver", "label": "CEO", "fieldtype": "Link", "options": "User", "read_only": 1},
		{"fieldname": "ceo_approval_date", "label": "CEO Approval Date", "fieldtype": "Date", "read_only": 1},
	])
	
	# ========== EVALUATION TAB ==========
	fields.extend([
		{"fieldname": "tab_evaluation", "label": "Evaluation", "fieldtype": "Tab Break"},
		{"fieldname": "section_evaluation", "label": "Initial Evaluation", "fieldtype": "Section Break"},
		{"fieldname": "evaluation_reports", "label": "Evaluation Reports", "fieldtype": "Table", "options": "Project Evaluation Report"},
		
		# Summary Fields
		{"fieldname": "section_eval_summary", "label": "Evaluation Summary", "fieldtype": "Section Break"},
		{"fieldname": "projects_mgmt_feasible", "label": "Projects Management: Feasible", "fieldtype": "Check", "read_only": 1},
		{"fieldname": "financial_mgmt_feasible", "label": "Financial Management: Feasible", "fieldtype": "Check", "read_only": 1},
		{"fieldname": "column_break_4", "fieldtype": "Column Break"},
		{"fieldname": "initial_estimated_cost", "label": "Initial Estimated Cost (SAR)", "fieldtype": "Currency", "read_only": 1},
		{"fieldname": "initial_estimated_duration", "label": "Initial Estimated Duration (Days)", "fieldtype": "Int", "read_only": 1},
	])
	
	# ========== FEASIBILITY TAB ==========
	fields.extend([
		{"fieldname": "tab_feasibility", "label": "Feasibility Study", "fieldtype": "Tab Break"},
		{"fieldname": "section_boq", "label": "Bill of Quantities (BOQ)", "fieldtype": "Section Break"},
		{"fieldname": "boq_template", "label": "BOQ Template", "fieldtype": "Link", "options": "BOQ Template"},
		{"fieldname": "feasibility_items", "label": "Feasibility Items", "fieldtype": "Table", "options": "Project Feasibility Item"},
		{"fieldname": "total_boq_amount", "label": "Total BOQ Amount (SAR)", "fieldtype": "Currency", "read_only": 1},
		
		# Layout/Concept
		{"fieldname": "section_layout", "label": "Layout / Concept", "fieldtype": "Section Break"},
		{"fieldname": "layout_description", "label": "Layout Description", "fieldtype": "Text Editor"},
		{"fieldname": "layout_attachment", "label": "Layout/Concept Document", "fieldtype": "Attach"},
		
		# Financial Analysis
		{"fieldname": "section_financial", "label": "Financial Analysis", "fieldtype": "Section Break"},
		{"fieldname": "estimated_total_cost", "label": "Estimated Total Cost (SAR)", "fieldtype": "Currency", "reqd": 1},
		{"fieldname": "estimated_roi", "label": "Estimated ROI (%)", "fieldtype": "Percent"},
		{"fieldname": "break_even_point", "label": "Break Even Point", "fieldtype": "Data"},
		{"fieldname": "column_break_5", "fieldtype": "Column Break"},
		{"fieldname": "cash_flow_year_1", "label": "Cash Flow Year 1 (SAR)", "fieldtype": "Currency"},
		{"fieldname": "cash_flow_year_2", "label": "Cash Flow Year 2 (SAR)", "fieldtype": "Currency"},
		{"fieldname": "cash_flow_year_3", "label": "Cash Flow Year 3 (SAR)", "fieldtype": "Currency"},
		{"fieldname": "financial_analysis_attachment", "label": "Financial Analysis Document", "fieldtype": "Attach"},
	])
	
	# ========== EXECUTION TAB ==========
	fields.extend([
		{"fieldname": "tab_execution", "label": "Execution", "fieldtype": "Tab Break"},
		{"fieldname": "section_technical", "label": "Technical Requirements", "fieldtype": "Section Break"},
		{"fieldname": "technical_requirements", "label": "Technical Requirements", "fieldtype": "Text Editor"},
		
		# Licenses
		{"fieldname": "section_licenses", "label": "Licenses & Permits", "fieldtype": "Section Break"},
		{"fieldname": "licenses", "label": "Licenses", "fieldtype": "Table", "options": "Project License"},
		
		# Contractors
		{"fieldname": "section_contractors", "label": "Contractor Offers", "fieldtype": "Section Break"},
		{"fieldname": "contractor_offers", "label": "Contractor Offers", "fieldtype": "Table", "options": "Project Contractor Offer"},
		{"fieldname": "selected_contractor", "label": "Selected Contractor", "fieldtype": "Link", "options": "Supplier"},
		{"fieldname": "contract_amount", "label": "Contract Amount (SAR)", "fieldtype": "Currency", "read_only": 1},
		
		# Execution Tracking
		{"fieldname": "section_tracking", "label": "Execution Tracking", "fieldtype": "Section Break"},
		{"fieldname": "start_date", "label": "Start Date", "fieldtype": "Date"},
		{"fieldname": "expected_completion_date", "label": "Expected Completion Date", "fieldtype": "Date"},
		{"fieldname": "actual_completion_date", "label": "Actual Completion Date", "fieldtype": "Date", "read_only": 1},
		{"fieldname": "column_break_6", "fieldtype": "Column Break"},
		{"fieldname": "progress_percentage", "label": "Progress (%)", "fieldtype": "Percent", "read_only": 1},
		{"fieldname": "weekly_reports", "label": "Weekly Reports", "fieldtype": "Table", "options": "Project Weekly Report"},
		{"fieldname": "monthly_financial_reports", "label": "Monthly Financial Reports", "fieldtype": "Table", "options": "Project Monthly Financial"},
	])
	
	# ========== HANDOVER TAB ==========
	fields.extend([
		{"fieldname": "tab_handover", "label": "Handover", "fieldtype": "Tab Break"},
		{"fieldname": "section_handover", "label": "Final Handover", "fieldtype": "Section Break"},
		{"fieldname": "handover_date", "label": "Handover Date", "fieldtype": "Date"},
		{"fieldname": "handed_over_to", "label": "Handed Over To", "fieldtype": "Link", "options": "Department", "description": "Marketing & Sales Department"},
		{"fieldname": "column_break_7", "fieldtype": "Column Break"},
		{"fieldname": "handover_status", "label": "Handover Status", "fieldtype": "Select", "options": "Pending\nIn Progress\nCompleted", "default": "Pending"},
		{"fieldname": "handover_items", "label": "Handover Checklist", "fieldtype": "Table", "options": "Project Handover Item"},
		{"fieldname": "handover_remarks", "label": "Handover Remarks", "fieldtype": "Text Editor"},
	])
	
	# ========== DASHBOARD TAB ==========
	fields.extend([
		{"fieldname": "tab_dashboard", "label": "Management Dashboard", "fieldtype": "Tab Break"},
		{"fieldname": "section_dashboard", "label": "Project Dashboard", "fieldtype": "Section Break"},
		{"fieldname": "dashboard_html", "label": "Dashboard", "fieldtype": "HTML", "options": "HTML"},
	])
	
	# ========== BUILDING INFORMATION TAB ==========
	fields.extend([
		{"fieldname": "tab_building_info", "label": "Building Information", "fieldtype": "Tab Break"},
		
		# Basic Building Information Section
		{"fieldname": "section_basic_building", "label": "Basic Building Information", "fieldtype": "Section Break"},
		{"fieldname": "total_land_area", "label": "Total Land Area (m²)", "fieldtype": "Float"},
		{"fieldname": "number_of_floors", "label": "Number of Floors/Levels", "fieldtype": "Int"},
		{"fieldname": "column_break_building_1", "fieldtype": "Column Break"},
		{"fieldname": "building_type", "label": "Building Type", "fieldtype": "Select", "options": "Commercial\nResidential\nAdministrative\nMixed\nOther"},
		{"fieldname": "building_height", "label": "Building Height (m)", "fieldtype": "Float"},
		{"fieldname": "building_dimensions", "label": "Building Dimensions", "fieldtype": "Small Text", "description": "Length x Width x Height"},
		
		# Areas and Building Components Section
		{"fieldname": "section_areas", "label": "Areas and Building Components", "fieldtype": "Section Break"},
		{"fieldname": "building_areas", "label": "Areas Table", "fieldtype": "Table", "options": "Project Building Area Component"},
		{"fieldname": "total_building_area", "label": "Total Building Area (m²)", "fieldtype": "Float", "read_only": 1},
		{"fieldname": "column_break_areas", "fieldtype": "Column Break"},
		{"fieldname": "total_units", "label": "Total Number of Units", "fieldtype": "Int", "read_only": 1},
		
		# Spaces and Units Section
		{"fieldname": "section_spaces", "label": "Spaces and Units", "fieldtype": "Section Break"},
		{"fieldname": "building_spaces", "label": "Spaces Table", "fieldtype": "Table", "options": "Project Building Space"},
		{"fieldname": "total_spaces_count", "label": "Total Spaces Count", "fieldtype": "Int", "read_only": 1},
		{"fieldname": "total_spaces_area", "label": "Total Spaces Area (m²)", "fieldtype": "Float", "read_only": 1},
		{"fieldname": "total_spaces_percentage", "label": "Total Spaces Area % of Land", "fieldtype": "Percent", "read_only": 1},
		
		# Technical Details Section
		{"fieldname": "section_technical_details", "label": "Technical Details", "fieldtype": "Section Break"},
		{"fieldname": "number_of_bathrooms", "label": "Number of Bathrooms", "fieldtype": "Int"},
		{"fieldname": "number_of_stairs", "label": "Number of Stairs/Staircases", "fieldtype": "Int"},
		{"fieldname": "structural_details", "label": "Structural Details", "fieldtype": "Text Editor"},
		{"fieldname": "column_break_technical", "fieldtype": "Column Break"},
		{"fieldname": "electrical_requirements", "label": "Electrical Requirements", "fieldtype": "Small Text"},
		{"fieldname": "plumbing_requirements", "label": "Plumbing Requirements", "fieldtype": "Small Text"},
		{"fieldname": "hvac_requirements", "label": "HVAC Requirements", "fieldtype": "Small Text"},
		{"fieldname": "other_technical_details", "label": "Other Technical Details", "fieldtype": "Text Editor"},
		
		# Images and Drawings Section
		{"fieldname": "section_images", "label": "Images and Drawings", "fieldtype": "Section Break"},
		{"fieldname": "floor_plan_image", "label": "Floor Plan Image", "fieldtype": "Attach Image"},
		{"fieldname": "floor_plan_image_display", "label": "Floor Plan Preview", "fieldtype": "Image", "options": "floor_plan_image", "read_only": 1},
		{"fieldname": "cross_section_image", "label": "Cross Section Image", "fieldtype": "Attach Image"},
		{"fieldname": "cross_section_image_display", "label": "Cross Section Preview", "fieldtype": "Image", "options": "cross_section_image", "read_only": 1},
		{"fieldname": "elevation_image", "label": "Elevation Image", "fieldtype": "Attach Image"},
		{"fieldname": "elevation_image_display", "label": "Elevation Preview", "fieldtype": "Image", "options": "elevation_image", "read_only": 1},
		{"fieldname": "column_break_images_1", "fieldtype": "Column Break"},
		{"fieldname": "site_plan_image", "label": "Site Plan Image", "fieldtype": "Attach Image"},
		{"fieldname": "site_plan_image_display", "label": "Site Plan Preview", "fieldtype": "Image", "options": "site_plan_image", "read_only": 1},
		{"fieldname": "other_drawings", "label": "Other Drawings/Documents", "fieldtype": "Attach"},
		{"fieldname": "images_description", "label": "Images Description/Notes", "fieldtype": "Small Text"},
	])
	
	# ========== COMMON FIELDS ==========
	fields.extend([
		# Status and Workflow
		{"fieldname": "section_status", "label": "Status", "fieldtype": "Section Break", "collapsible": 1},
		{"fieldname": "workflow_state", "label": "Workflow State", "fieldtype": "Link", "options": "Workflow State", "hidden": 1},
		{"fieldname": "status", "label": "Status", "fieldtype": "Select", "options": "Draft\nPending Deputy CEO Approval\nPending CEO Approval\nUnder Initial Evaluation\nFeasibility Study Phase\nApproved\nIn Execution\nCompleted\nRejected", "default": "Draft", "read_only": 1, "in_list_view": 1},
		
		# Team
		{"fieldname": "section_team", "label": "Project Team", "fieldtype": "Section Break", "collapsible": 1},
		{"fieldname": "team_template", "label": "Team Template", "fieldtype": "Link", "options": "Project Team Member Template"},
		{"fieldname": "team_members", "label": "Team Members", "fieldtype": "Table", "options": "Project Team Member"},
		
		# Naming Series
		{"fieldname": "naming_series", "label": "Naming Series", "fieldtype": "Select", "options": "PROJ-.YYYY.-.####", "default": "PROJ-.YYYY.-.####", "reqd": 1},
	])
	
	# Create the main doctype
	_ensure_doctype(
		"Project Proposal",
		module="milestoneksa",
		istable=0,
		editable_grid=0,
		track_changes=1,
		track_seen=1,
		custom=0,
		is_submittable=1,
		autoname="naming_series:",
		naming_rule="By fieldname",
		naming_series="PROJ-.YYYY.-.####",
		title_field="project_name",
		subject_field="project_name",
		allow_rename=1,
		engine="InnoDB",
		fields=fields,
		permissions=[
			{"role": "Employee", "read": 1, "write": 1, "create": 1},
			{"role": "Deputy CEO", "read": 1, "write": 1, "submit": 1},
			{"role": "CEO", "read": 1, "write": 1, "submit": 1},
			{"role": "Projects Manager", "read": 1, "write": 1},
			{"role": "Financial Manager", "read": 1, "write": 1},
			{"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1, "submit": 1, "cancel": 1, "amend": 1},
		]
	)


def create_workflow():
	"""Create workflow for Project Proposal"""
	
	workflow_name = "Project Proposal Workflow"
	
	if frappe.db.exists("Workflow", workflow_name):
		print(f"Workflow '{workflow_name}' already exists, skipping...")
		return
	
	# Create workflow states first
	states = [
		{"state": "Draft", "doc_status": 0},
		{"state": "Pending Deputy CEO Approval", "doc_status": 0},
		{"state": "Pending CEO Approval", "doc_status": 0},
		{"state": "Under Initial Evaluation", "doc_status": 0},
		{"state": "Feasibility Study Phase", "doc_status": 0},
		{"state": "Approved", "doc_status": 1},
		{"state": "In Execution", "doc_status": 1},
		{"state": "Completed", "doc_status": 1},
		{"state": "Rejected", "doc_status": 0},
	]
	
	for state_data in states:
		if not frappe.db.exists("Workflow State", state_data["state"]):
			frappe.get_doc({
				"doctype": "Workflow State",
				"workflow_state_name": state_data["state"]
			}).insert(ignore_permissions=True)
	
	# Create workflow actions
	actions = [
		"Submit for Initial Approval",
		"Approve Initial",
		"Reject",
		"Approve Final",
		"Send for Evaluation",
		"Complete Evaluation",
		"Start Feasibility Study",
		"Complete Feasibility Study",
		"Approve Project",
		"Start Execution",
		"Complete Project",
	]
	
	for action_name in actions:
		if not frappe.db.exists("Workflow Action Master", action_name):
			frappe.get_doc({
				"doctype": "Workflow Action Master",
				"workflow_action_name": action_name
			}).insert(ignore_permissions=True)
	
	# Create the workflow
	workflow = frappe.new_doc("Workflow")
	workflow.workflow_name = workflow_name
	workflow.document_type = "Project Proposal"
	workflow.workflow_state_field = "workflow_state"
	workflow.is_active = 1
	workflow.send_email_alert = 1
	
	# Add states with allow_edit roles
	# Note: allow_edit accepts only one role, so we use Projects Manager for evaluation/feasibility states
	state_edit_roles = {
		"Draft": "Employee",
		"Pending Deputy CEO Approval": "Deputy CEO",
		"Pending CEO Approval": "CEO",
		"Under Initial Evaluation": "Projects Manager",
		"Feasibility Study Phase": "Projects Manager",
		"Approved": "Projects Manager",
		"In Execution": "Projects Manager",
		"Completed": "Projects Manager",
		"Rejected": "System Manager"
	}
	
	for state_data in states:
		state_name = state_data["state"]
		workflow.append("states", {
			"state": state_name,
			"doc_status": state_data["doc_status"],
			"allow_edit": state_edit_roles.get(state_name, "System Manager")
		})
	
	# Add transitions
	# Note: All projects require CEO approval. Projects > 2M SAR have special emphasis per policy,
	# but follow the same workflow path. Special handling can be added via notifications or custom logic.
	transitions = [
		{"state": "Draft", "action": "Submit for Initial Approval", "next_state": "Pending Deputy CEO Approval", "allowed": "Employee"},
		{"state": "Pending Deputy CEO Approval", "action": "Approve Initial", "next_state": "Pending CEO Approval", "allowed": "Deputy CEO"},
		{"state": "Pending Deputy CEO Approval", "action": "Reject", "next_state": "Rejected", "allowed": "Deputy CEO"},
		{"state": "Pending CEO Approval", "action": "Approve Final", "next_state": "Under Initial Evaluation", "allowed": "CEO"},
		{"state": "Pending CEO Approval", "action": "Reject", "next_state": "Rejected", "allowed": "CEO"},
		{"state": "Under Initial Evaluation", "action": "Complete Evaluation", "next_state": "Feasibility Study Phase", "allowed": "Projects Manager"},
		{"state": "Feasibility Study Phase", "action": "Complete Feasibility Study", "next_state": "Approved", "allowed": "Projects Manager"},
		{"state": "Approved", "action": "Start Execution", "next_state": "In Execution", "allowed": "Projects Manager"},
		{"state": "In Execution", "action": "Complete Project", "next_state": "Completed", "allowed": "Projects Manager"},
	]
	
	for trans in transitions:
		workflow.append("transitions", {
			"state": trans["state"],
			"action": trans["action"],
			"next_state": trans["next_state"],
			"allowed": trans["allowed"],
			"condition": trans.get("condition")
		})
	
	workflow.insert(ignore_permissions=True)
	print(f"✅ Created Workflow: {workflow_name}")


def create_required_roles():
	"""Create required roles if they don't exist"""
	required_roles = [
		"Deputy CEO",
		"CEO",
		"Projects Manager",
		"Financial Manager"
	]
	
	for role_name in required_roles:
		if not frappe.db.exists("Role", role_name):
			role = frappe.new_doc("Role")
			role.role_name = role_name
			role.insert(ignore_permissions=True)
			print(f"✅ Created Role: {role_name}")
		else:
			print(f"Role '{role_name}' already exists")


def update_project_proposal_with_building_info():
	"""Update existing Project Proposal DocType with Building Information tab fields"""
	if not frappe.db.exists("DocType", "Project Proposal"):
		print("Project Proposal DocType does not exist, skipping update...")
		return
	
	doc = frappe.get_doc("DocType", "Project Proposal")
	meta = frappe.get_meta("Project Proposal")
	
	# Check if Building Information tab already exists
	tab_exists = meta.has_field("tab_building_info")
	
	# Check if Image display fields exist
	image_display_fields = [
		"floor_plan_image_display",
		"cross_section_image_display",
		"elevation_image_display",
		"site_plan_image_display"
	]
	missing_image_fields = [f for f in image_display_fields if not meta.has_field(f)]
	
	if tab_exists and not missing_image_fields:
		print("Building Information tab with Image display fields already exists in Project Proposal, skipping update...")
		return
	
	if tab_exists:
		print("Building Information tab exists, adding missing Image display fields...")
		# Only add the Image display fields
		building_fields = [
			{"fieldname": "floor_plan_image_display", "label": "Floor Plan Preview", "fieldtype": "Image", "options": "floor_plan_image", "read_only": 1, "insert_after": "floor_plan_image"},
			{"fieldname": "cross_section_image_display", "label": "Cross Section Preview", "fieldtype": "Image", "options": "cross_section_image", "read_only": 1, "insert_after": "cross_section_image"},
			{"fieldname": "elevation_image_display", "label": "Elevation Preview", "fieldtype": "Image", "options": "elevation_image", "read_only": 1, "insert_after": "elevation_image"},
			{"fieldname": "site_plan_image_display", "label": "Site Plan Preview", "fieldtype": "Image", "options": "site_plan_image", "read_only": 1, "insert_after": "site_plan_image"},
		]
		# Filter to only add missing fields
		building_fields = [f for f in building_fields if f["fieldname"] in missing_image_fields]
		insert_after = "floor_plan_image"  # Will be set per field
	else:
		# Original full list - Get the field list for Building Information tab
		building_fields = [
		{"fieldname": "tab_building_info", "label": "Building Information", "fieldtype": "Tab Break"},
		{"fieldname": "section_basic_building", "label": "Basic Building Information", "fieldtype": "Section Break"},
		{"fieldname": "total_land_area", "label": "Total Land Area (m²)", "fieldtype": "Float"},
		{"fieldname": "number_of_floors", "label": "Number of Floors/Levels", "fieldtype": "Int"},
		{"fieldname": "column_break_building_1", "fieldtype": "Column Break"},
		{"fieldname": "building_type", "label": "Building Type", "fieldtype": "Select", "options": "Commercial\nResidential\nAdministrative\nMixed\nOther"},
		{"fieldname": "building_height", "label": "Building Height (m)", "fieldtype": "Float"},
		{"fieldname": "building_dimensions", "label": "Building Dimensions", "fieldtype": "Small Text", "description": "Length x Width x Height"},
		{"fieldname": "section_areas", "label": "Areas and Building Components", "fieldtype": "Section Break"},
		{"fieldname": "building_areas", "label": "Areas Table", "fieldtype": "Table", "options": "Project Building Area Component"},
		{"fieldname": "total_building_area", "label": "Total Building Area (m²)", "fieldtype": "Float", "read_only": 1},
		{"fieldname": "total_building_area_percentage", "label": "Total Building Area % of Land", "fieldtype": "Percent", "read_only": 1},
		{"fieldname": "column_break_areas", "fieldtype": "Column Break"},
		{"fieldname": "total_units", "label": "Total Number of Units", "fieldtype": "Int", "read_only": 1},
		{"fieldname": "section_spaces", "label": "Spaces and Units", "fieldtype": "Section Break"},
		{"fieldname": "building_spaces", "label": "Spaces Table", "fieldtype": "Table", "options": "Project Building Space"},
		{"fieldname": "total_spaces_count", "label": "Total Spaces Count", "fieldtype": "Int", "read_only": 1},
		{"fieldname": "total_spaces_area", "label": "Total Spaces Area (m²)", "fieldtype": "Float", "read_only": 1},
		{"fieldname": "total_spaces_percentage", "label": "Total Spaces Area % of Land", "fieldtype": "Percent", "read_only": 1},
		{"fieldname": "section_technical_details", "label": "Technical Details", "fieldtype": "Section Break"},
		{"fieldname": "number_of_bathrooms", "label": "Number of Bathrooms", "fieldtype": "Int"},
		{"fieldname": "number_of_stairs", "label": "Number of Stairs/Staircases", "fieldtype": "Int"},
		{"fieldname": "structural_details", "label": "Structural Details", "fieldtype": "Text Editor"},
		{"fieldname": "column_break_technical", "fieldtype": "Column Break"},
		{"fieldname": "electrical_requirements", "label": "Electrical Requirements", "fieldtype": "Small Text"},
		{"fieldname": "plumbing_requirements", "label": "Plumbing Requirements", "fieldtype": "Small Text"},
		{"fieldname": "hvac_requirements", "label": "HVAC Requirements", "fieldtype": "Small Text"},
		{"fieldname": "other_technical_details", "label": "Other Technical Details", "fieldtype": "Text Editor"},
		{"fieldname": "section_images", "label": "Images and Drawings", "fieldtype": "Section Break"},
		{"fieldname": "floor_plan_image", "label": "Floor Plan Image", "fieldtype": "Attach Image"},
		{"fieldname": "floor_plan_image_display", "label": "Floor Plan Preview", "fieldtype": "Image", "options": "floor_plan_image", "read_only": 1},
		{"fieldname": "cross_section_image", "label": "Cross Section Image", "fieldtype": "Attach Image"},
		{"fieldname": "cross_section_image_display", "label": "Cross Section Preview", "fieldtype": "Image", "options": "cross_section_image", "read_only": 1},
		{"fieldname": "elevation_image", "label": "Elevation Image", "fieldtype": "Attach Image"},
		{"fieldname": "elevation_image_display", "label": "Elevation Preview", "fieldtype": "Image", "options": "elevation_image", "read_only": 1},
		{"fieldname": "column_break_images_1", "fieldtype": "Column Break"},
		{"fieldname": "site_plan_image", "label": "Site Plan Image", "fieldtype": "Attach Image"},
		{"fieldname": "site_plan_image_display", "label": "Site Plan Preview", "fieldtype": "Image", "options": "site_plan_image", "read_only": 1},
		{"fieldname": "other_drawings", "label": "Other Drawings/Documents", "fieldtype": "Attach"},
		{"fieldname": "images_description", "label": "Images Description/Notes", "fieldtype": "Small Text"},
	]
	
	# Find insertion point (after dashboard_html field)
	insert_after = "dashboard_html"
	if not meta.has_field(insert_after):
		# Try to find the last tab break
		for field in reversed(doc.fields):
			if field.fieldtype == "Tab Break":
				insert_after = field.fieldname
				break
	
	# Add fields to DocType
	first_field_idx = None
	for idx, field_data in enumerate(building_fields):
		fieldname = field_data["fieldname"]
		if not meta.has_field(fieldname):
			field_doc = frappe.new_doc("DocField")
			field_doc.update(field_data)
			field_doc.parent = "Project Proposal"
			field_doc.parenttype = "DocType"
			field_doc.parentfield = "fields"
			# Set insert_after
			if "insert_after" in field_data:
				field_doc.insert_after = field_data["insert_after"]
			elif idx == 0:
				field_doc.insert_after = insert_after
			if first_field_idx is None:
				first_field_idx = len(doc.fields)
			doc.append("fields", field_doc)
		else:
			print(f"Field '{fieldname}' already exists, skipping...")
	
	if first_field_idx is not None:
		# Reorder fields to ensure proper insertion
		doc.save(ignore_permissions=True)
		frappe.db.commit()
		print("✅ Updated Project Proposal DocType with Building Information tab")
	else:
		print("All Building Information fields already exist in Project Proposal")


def add_building_info_to_erpnext_project():
	"""Add Building Information custom fields to ERPNext Project DocType"""
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
	
	# Find the last field in Project DocType to insert after
	# Using 'message' as it's typically the last field in Project DocType
	try:
		project_meta = frappe.get_meta("Project")
		if project_meta.has_field("message"):
			insert_after = "message"
		else:
			# Fallback: find last field
			last_field = None
			for field in reversed(project_meta.fields):
				if field.fieldtype not in ["Section Break", "Column Break", "Tab Break"]:
					last_field = field.fieldname
					break
			insert_after = last_field if last_field else "append"
	except:
		insert_after = "append"
	
	custom_fields = {
		'Project': [
			# Tab Break
			dict(fieldname='tab_building_info_custom', label='Building Information',
				 fieldtype='Tab Break', insert_after=insert_after),
			
			# Basic Building Information Section
			dict(fieldname='section_basic_building_custom', label='Basic Building Information',
				 fieldtype='Section Break', insert_after='tab_building_info_custom'),
			dict(fieldname='total_land_area_custom', label='Total Land Area (m²)',
				 fieldtype='Float', insert_after='section_basic_building_custom'),
			dict(fieldname='number_of_floors_custom', label='Number of Floors/Levels',
				 fieldtype='Int', insert_after='total_land_area_custom'),
			dict(fieldname='column_break_building_1_custom', fieldtype='Column Break',
				 insert_after='number_of_floors_custom'),
			dict(fieldname='building_type_custom', label='Building Type',
				 fieldtype='Select', options='Commercial\nResidential\nAdministrative\nMixed\nOther',
				 insert_after='column_break_building_1_custom'),
			dict(fieldname='building_height_custom', label='Building Height (m)',
				 fieldtype='Float', insert_after='building_type_custom'),
			dict(fieldname='building_dimensions_custom', label='Building Dimensions',
				 fieldtype='Small Text', description='Length x Width x Height',
				 insert_after='building_height_custom'),
			
			# Areas and Building Components Section
			dict(fieldname='section_areas_custom', label='Areas and Building Components',
				 fieldtype='Section Break', insert_after='building_dimensions_custom'),
			dict(fieldname='building_areas_custom', label='Areas Table',
				 fieldtype='Table', options='Project Building Area Component',
				 insert_after='section_areas_custom'),
			dict(fieldname='total_building_area_custom', label='Total Building Area (m²)',
				 fieldtype='Float', read_only=1, insert_after='building_areas_custom'),
			dict(fieldname='total_building_area_percentage_custom', label='Total Building Area % of Land',
				 fieldtype='Percent', read_only=1, insert_after='total_building_area_custom'),
			dict(fieldname='column_break_areas_custom', fieldtype='Column Break',
				 insert_after='total_building_area_percentage_custom'),
			dict(fieldname='total_units_custom', label='Total Number of Units',
				 fieldtype='Int', read_only=1, insert_after='column_break_areas_custom'),
			
			# Spaces and Units Section
			dict(fieldname='section_spaces_custom', label='Spaces and Units',
				 fieldtype='Section Break', insert_after='total_units_custom'),
			dict(fieldname='building_spaces_custom', label='Spaces Table',
				 fieldtype='Table', options='Project Building Space',
				 insert_after='section_spaces_custom'),
			dict(fieldname='total_spaces_count_custom', label='Total Spaces Count',
				 fieldtype='Int', read_only=1, insert_after='building_spaces_custom'),
			dict(fieldname='total_spaces_area_custom', label='Total Spaces Area (m²)',
				 fieldtype='Float', read_only=1, insert_after='total_spaces_count_custom'),
			dict(fieldname='total_spaces_percentage_custom', label='Total Spaces Area % of Land',
				 fieldtype='Percent', read_only=1, insert_after='total_spaces_area_custom'),
			
			# Technical Details Section
			dict(fieldname='section_technical_details_custom', label='Technical Details',
				 fieldtype='Section Break', insert_after='total_spaces_count_custom'),
			dict(fieldname='number_of_bathrooms_custom', label='Number of Bathrooms',
				 fieldtype='Int', insert_after='section_technical_details_custom'),
			dict(fieldname='number_of_stairs_custom', label='Number of Stairs/Staircases',
				 fieldtype='Int', insert_after='number_of_bathrooms_custom'),
			dict(fieldname='structural_details_custom', label='Structural Details',
				 fieldtype='Text Editor', insert_after='number_of_stairs_custom'),
			dict(fieldname='column_break_technical_custom', fieldtype='Column Break',
				 insert_after='structural_details_custom'),
			dict(fieldname='electrical_requirements_custom', label='Electrical Requirements',
				 fieldtype='Small Text', insert_after='column_break_technical_custom'),
			dict(fieldname='plumbing_requirements_custom', label='Plumbing Requirements',
				 fieldtype='Small Text', insert_after='electrical_requirements_custom'),
			dict(fieldname='hvac_requirements_custom', label='HVAC Requirements',
				 fieldtype='Small Text', insert_after='plumbing_requirements_custom'),
			dict(fieldname='other_technical_details_custom', label='Other Technical Details',
				 fieldtype='Text Editor', insert_after='hvac_requirements_custom'),
			
			# Images and Drawings Section
			dict(fieldname='section_images_custom', label='Images and Drawings',
				 fieldtype='Section Break', insert_after='other_technical_details_custom'),
			dict(fieldname='floor_plan_image_custom', label='Floor Plan Image',
				 fieldtype='Attach Image', insert_after='section_images_custom'),
			dict(fieldname='floor_plan_image_display_custom', label='Floor Plan Preview',
				 fieldtype='Image', options='floor_plan_image_custom', read_only=1,
				 insert_after='floor_plan_image_custom'),
			dict(fieldname='cross_section_image_custom', label='Cross Section Image',
				 fieldtype='Attach Image', insert_after='floor_plan_image_display_custom'),
			dict(fieldname='cross_section_image_display_custom', label='Cross Section Preview',
				 fieldtype='Image', options='cross_section_image_custom', read_only=1,
				 insert_after='cross_section_image_custom'),
			dict(fieldname='elevation_image_custom', label='Elevation Image',
				 fieldtype='Attach Image', insert_after='cross_section_image_display_custom'),
			dict(fieldname='elevation_image_display_custom', label='Elevation Preview',
				 fieldtype='Image', options='elevation_image_custom', read_only=1,
				 insert_after='elevation_image_custom'),
			dict(fieldname='column_break_images_1_custom', fieldtype='Column Break',
				 insert_after='elevation_image_display_custom'),
			dict(fieldname='site_plan_image_custom', label='Site Plan Image',
				 fieldtype='Attach Image', insert_after='column_break_images_1_custom'),
			dict(fieldname='site_plan_image_display_custom', label='Site Plan Preview',
				 fieldtype='Image', options='site_plan_image_custom', read_only=1,
				 insert_after='site_plan_image_custom'),
			dict(fieldname='other_drawings_custom', label='Other Drawings/Documents',
				 fieldtype='Attach', insert_after='site_plan_image_display_custom'),
			dict(fieldname='images_description_custom', label='Images Description/Notes',
				 fieldtype='Small Text', insert_after='other_drawings_custom'),
		]
	}
	
	create_custom_fields(custom_fields, update=True)
	print("✅ Created Building Information custom fields for ERPNext Project DocType")


def execute():
	"""Main execution function"""
	print("=" * 60)
	print("Creating Project Proposal Doctype System...")
	print("=" * 60)
	
	try:
		# Create required roles first
		print("\n👥 Creating required roles...")
		create_required_roles()
		# Create child tables first
		print("\n📋 Creating child table DocTypes...")
		create_child_table_doctypes()
		
		# Create template doctypes
		print("\n📝 Creating template DocTypes...")
		create_template_doctypes()
		
		# Create main doctype
		print("\n📄 Creating main Project Proposal DocType...")
		create_main_doctype()
		
		# Update existing Project Proposal with Building Information tab
		print("\n🏗️ Updating Project Proposal with Building Information tab...")
		update_project_proposal_with_building_info()
		
		# Create workflow
		print("\n🔄 Creating workflow...")
		create_workflow()
		
		# Add Building Information custom fields to ERPNext Project
		print("\n🏗️ Adding Building Information to ERPNext Project...")
		add_building_info_to_erpnext_project()
		
		# Clear cache
		frappe.clear_cache()
		frappe.db.commit()
		
		print("\n" + "=" * 60)
		print("✅ Project Proposal Doctype System created successfully!")
		print("=" * 60)
		print("\nComponents created:")
		print("✅ Main DocType: Project Proposal")
		print("✅ 12 Child Table DocTypes (including Building Area Component and Building Space)")
		print("✅ 2 Template DocTypes")
		print("✅ Workflow with 9 states")
		print("✅ Building Information tab for Project Proposal")
		print("✅ Building Information custom fields for ERPNext Project")
		print("✅ Building Information calculation JavaScript")
		print("✅ Dashboard JavaScript file")
		print("✅ Arabic translations")
		print("\nNext steps:")
		print("1. Run: bench --site milestoneksa.com migrate")
		print("2. Test the doctype and workflow")
		print("3. Verify dashboard rendering")
		
	except Exception as e:
		frappe.db.rollback()
		print(f"\n❌ Error: {str(e)}")
		import traceback
		traceback.print_exc()
		raise

