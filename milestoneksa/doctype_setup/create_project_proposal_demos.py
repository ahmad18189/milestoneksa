# -*- coding: utf-8 -*-
"""
Create 2 Arabic Demo Project Proposals with full scenarios and all details
"""
import frappe
from frappe.utils import nowdate, add_days, add_months, getdate
from datetime import datetime


def create_demo_proposals():
	"""Create 2 complete Arabic demo project proposals"""
	
	print("=" * 60)
	print("Creating Arabic Demo Project Proposals...")
	print("=" * 60)
	
	# Get or create required data
	company = frappe.db.get_value("Company", {"name": ["!=", ""]}, "name") or frappe.db.get_value("Company", {}, "name")
	if not company:
		print("❌ No company found. Please create a company first.")
		return
	
	# Get employees
	employees = frappe.get_all("Employee", limit=5)
	if len(employees) < 2:
		print("❌ Need at least 2 employees. Please create employees first.")
		return
	
	# Get departments
	departments = frappe.get_all("Department", limit=3)
	
	# Create Demo 1: Real Estate Project
	print("\n📋 Creating Demo 1: Real Estate Project (مشروع عقاري)...")
	create_demo_1_real_estate(company, employees, departments)
	
	# Create Demo 2: Construction Project
	print("\n📋 Creating Demo 2: Construction Project (مشروع إنشائي)...")
	create_demo_2_construction(company, employees, departments)
	
	frappe.db.commit()
	print("\n" + "=" * 60)
	print("✅ Demo Project Proposals created successfully!")
	print("=" * 60)


def create_demo_1_real_estate(company, employees, departments):
	"""Create Demo 1: Real Estate Development Project"""
	
	proposal = frappe.new_doc("Project Proposal")
	
	# Basic Information
	proposal.project_name = "مشروع تطوير مجمع سكني تجاري - حي النخيل"
	proposal.project_code = "RE-2025-001"
	proposal.project_type = "Real Estate"
	proposal.proposal_date = add_days(nowdate(), -30)
	proposal.location = "حي النخيل، الرياض، المملكة العربية السعودية"
	proposal.property_location = "قطعة أرض رقم 1234، مخطط النخيل، مساحة 5000 متر مربع"
	
	# Proposer
	proposal.employee = employees[0].name
	proposal.employee_name = frappe.db.get_value("Employee", employees[0].name, "employee_name")
	if departments:
		proposal.department = departments[0].name
	
	proposal.investment_type = "تطوير مجمع سكني تجاري متكامل"
	proposal.expected_value = "عائد استثماري متوقع 25% سنوياً، قيمة المشروع الإجمالية 15 مليون ريال"
	
	# Description
	proposal.project_description = """
	<strong>وصف المشروع:</strong><br>
	تطوير مجمع سكني تجاري متكامل في حي النخيل بمدينة الرياض يتكون من:<br>
	<ul>
		<li>3 أبراج سكنية (60 شقة سكنية)</li>
		<li>مجمع تجاري (20 محل تجاري)</li>
		<li>مواقف سيارات تحت الأرض (150 موقف)</li>
		<li>مرافق خدمية (صالة ألعاب، مسجد، حديقة)</li>
	</ul>
	
	<strong>الهدف من المشروع:</strong><br>
	تلبية الطلب المتزايد على الوحدات السكنية والتجارية في المنطقة، وتحقيق عائد استثماري جيد.
	"""
	
	# Naming Series
	proposal.naming_series = "PROJ-.YYYY.-.####"
	
	# Team Members
	proposal.append("team_members", {
		"employee": employees[0].name,
		"role": "مدير المشروع",
		"responsibilities": "الإشراف العام على المشروع، التنسيق بين الأقسام، متابعة الجدول الزمني"
	})
	if len(employees) > 1:
		proposal.append("team_members", {
			"employee": employees[1].name,
			"role": "مهندس معماري",
			"responsibilities": "التصميم المعماري، المخططات، التنسيق مع الاستشاريين"
		})
	if len(employees) > 2:
		proposal.append("team_members", {
			"employee": employees[2].name,
			"role": "مهندس مالي",
			"responsibilities": "الدراسات المالية، الميزانيات، التحليل المالي"
		})
	
	# Evaluation Reports
	proposal.append("evaluation_reports", {
		"evaluation_type": "Projects Management",
		"evaluated_by": frappe.session.user,
		"evaluation_date": add_days(nowdate(), -25),
		"feasibility_status": "Feasible",
		"estimated_cost": 15000000,
		"estimated_duration": 540,
		"regulatory_requirements": "رخصة بناء من أمانة الرياض، رخصة دفاع مدني، رخصة كهرباء، رخصة مياه",
		"risks": "تقلبات أسعار المواد، تأخير في الحصول على التراخيص، تغيرات في السوق العقاري",
		"recommendations": "المشروع قابل للتنفيذ مع مراعاة الحصول على التراخيص في الوقت المحدد وتأمين التمويل اللازم"
	})
	
	proposal.append("evaluation_reports", {
		"evaluation_type": "Financial Management",
		"evaluated_by": frappe.session.user,
		"evaluation_date": add_days(nowdate(), -20),
		"feasibility_status": "Feasible",
		"estimated_cost": 15000000,
		"roi_estimate": 25,
		"financial_risks": "تقلبات أسعار الفائدة، تغيرات في السوق العقاري، صعوبة الحصول على التمويل",
		"recommendations": "المشروع مجدي مالياً مع عائد استثماري جيد. يُنصح بتأمين التمويل قبل البدء"
	})
	
	proposal.projects_mgmt_feasible = 1
	proposal.financial_mgmt_feasible = 1
	proposal.initial_estimated_cost = 15000000
	proposal.initial_estimated_duration = 540
	
	# Feasibility Items (BOQ)
	proposal.append("feasibility_items", {
		"item_type": "BOQ Item",
		"item_code": "RE-001",
		"item_name": "أعمال الحفر والردم",
		"description": "حفر أساسات الأبراج والمجمع التجاري",
		"quantity": 5000,
		"uom": get_or_create_uom("Nos"),  # Use existing UOM
		"unit_rate": 25,
		"amount": 125000
	})
	
	proposal.append("feasibility_items", {
		"item_type": "BOQ Item",
		"item_code": "RE-002",
		"item_name": "الخرسانة المسلحة",
		"description": "خرسانة مسلحة للأبراج والمجمع",
		"quantity": 8000,
		"uom": get_or_create_uom("Nos"),
		"unit_rate": 350,
		"amount": 2800000
	})
	
	proposal.append("feasibility_items", {
		"item_type": "BOQ Item",
		"item_code": "RE-003",
		"item_name": "الحديد التسليحي",
		"description": "حديد تسليح للمباني",
		"quantity": 1200,
		"uom": get_or_create_uom("Nos"),
		"unit_rate": 3500,
		"amount": 4200000
	})
	
	proposal.append("feasibility_items", {
		"item_type": "Financial Projection",
		"item_name": "التدفق النقدي السنة الأولى",
		"year": 1,
		"cash_flow": -8000000
	})
	
	proposal.append("feasibility_items", {
		"item_type": "Financial Projection",
		"item_name": "التدفق النقدي السنة الثانية",
		"year": 2,
		"cash_flow": -5000000
	})
	
	proposal.append("feasibility_items", {
		"item_type": "Financial Projection",
		"item_name": "التدفق النقدي السنة الثالثة",
		"year": 3,
		"cash_flow": 12000000
	})
	
	proposal.total_boq_amount = 7125000
	proposal.estimated_total_cost = 15000000
	proposal.estimated_roi = 25
	proposal.break_even_point = "الشهر 24 من بداية البيع"
	proposal.cash_flow_year_1 = -8000000
	proposal.cash_flow_year_2 = -5000000
	proposal.cash_flow_year_3 = 12000000
	
	proposal.layout_description = """
	<strong>المخطط المعماري:</strong><br>
	<ul>
		<li>3 أبراج سكنية (20 طابق لكل برج)</li>
		<li>مجمع تجاري من طابقين</li>
		<li>مواقف تحت الأرض (3 طوابق)</li>
		<li>مساحات خضراء وحدائق</li>
	</ul>
	"""
	
	# Licenses
	proposal.append("licenses", {
		"license_type": "Municipality",
		"license_number": "BLD-2025-1234",
		"application_date": add_days(nowdate(), -15),
		"status": "Approved",
		"issue_date": add_days(nowdate(), -5),
		"remarks": "رخصة بناء من أمانة منطقة الرياض"
	})
	
	proposal.append("licenses", {
		"license_type": "Civil Defense",
		"license_number": "CD-2025-5678",
		"application_date": add_days(nowdate(), -12),
		"status": "Pending",
		"remarks": "في انتظار الموافقة"
	})
	
	proposal.append("licenses", {
		"license_type": "Electricity",
		"license_number": "ELEC-2025-9012",
		"application_date": add_days(nowdate(), -10),
		"status": "Approved",
		"issue_date": add_days(nowdate(), -3),
		"remarks": "رخصة كهرباء من الشركة السعودية للكهرباء"
	})
	
	# Contractor Offers
	proposal.append("contractor_offers", {
		"contractor": get_or_create_supplier("شركة البناء المتقدمة"),
		"offer_date": add_days(nowdate(), -8),
		"total_amount": 14800000,
		"validity_date": add_days(nowdate(), 30),
		"duration_days": 540,
		"payment_terms": "30% مقدماً، 40% حسب الإنجاز، 30% عند التسليم",
		"warranty_period": 24,
		"status": "Under Review",
		"remarks": "عرض تنافسي مع ضمان جودة عالية"
	})
	
	proposal.append("contractor_offers", {
		"contractor": get_or_create_supplier("مؤسسة الإنشاءات الحديثة"),
		"offer_date": add_days(nowdate(), -7),
		"total_amount": 15200000,
		"validity_date": add_days(nowdate(), 30),
		"duration_days": 600,
		"payment_terms": "25% مقدماً، 50% حسب الإنجاز، 25% عند التسليم",
		"warranty_period": 36,
		"status": "Received",
		"remarks": "عرض أعلى سعراً لكن بضمان أطول"
	})
	
	proposal.selected_contractor = get_or_create_supplier("شركة البناء المتقدمة")
	proposal.contract_amount = 14800000
	
	# Execution
	proposal.start_date = add_days(nowdate(), 10)
	proposal.expected_completion_date = add_days(nowdate(), 550)
	proposal.progress_percentage = 15
	
	# Weekly Reports
	proposal.append("weekly_reports", {
		"week_start_date": add_days(nowdate(), -14),
		"week_end_date": add_days(nowdate(), -7),
		"reported_by": frappe.session.user,
		"report_date": add_days(nowdate(), -6),
		"progress_percentage": 10,
		"work_completed": "إكمال أعمال الحفر والردم، بدء صب الأساسات",
		"work_planned": "متابعة صب الأساسات، بدء أعمال الحديد التسليحي",
		"issues_challenges": "تأخير بسيط في الحصول على رخصة الدفاع المدني"
	})
	
	proposal.append("weekly_reports", {
		"week_start_date": add_days(nowdate(), -7),
		"week_end_date": nowdate(),
		"reported_by": frappe.session.user,
		"report_date": nowdate(),
		"progress_percentage": 15,
		"work_completed": "إكمال صب الأساسات، بدء أعمال الحديد التسليحي للطابق الأول",
		"work_planned": "متابعة أعمال الحديد، بدء صب الخرسانة للطابق الأول",
		"issues_challenges": "لا توجد مشاكل"
	})
	
	# Monthly Financial
	proposal.append("monthly_financial_reports", {
		"month": "January",
		"year": 2025,
		"reported_by": frappe.session.user,
		"report_date": nowdate(),
		"budgeted_amount": 2000000,
		"actual_spent": 1850000,
		"variance": -150000,
		"variance_percentage": -7.5,
		"remarks": "الإنفاق أقل من المخطط بسبب تأخير بسيط في البدء"
	})
	
	# Attachments - skip for demo (attachment field is required)
	# Users can add attachments manually in the UI
	# proposal.append("supporting_documents", {...})
	
	# Handover Items
	proposal.append("handover_items", {
		"item_description": "فحص جودة الأعمال الإنشائية",
		"category": "Quality Check",
		"status": "Pending"
	})
	
	proposal.append("handover_items", {
		"item_description": "استكمال جميع التراخيص",
		"category": "Documentation",
		"status": "Pending"
	})
	
	proposal.append("handover_items", {
		"item_description": "تسليم المخططات النهائية",
		"category": "Documentation",
		"status": "Pending"
	})
	
	# Status - keep as draft for demo
	proposal.status = "Draft"
	# Don't set workflow_state manually - let workflow handle it
	
	proposal.insert(ignore_permissions=True)
	# Don't submit - keep as draft for demo purposes
	print(f"✅ Created: {proposal.name} - {proposal.project_name}")


def create_demo_2_construction(company, employees, departments):
	"""Create Demo 2: Construction Project"""
	
	proposal = frappe.new_doc("Project Proposal")
	
	# Basic Information
	proposal.project_name = "مشروع بناء مجمع إداري - طريق الملك فهد"
	proposal.project_code = "CON-2025-002"
	proposal.project_type = "Construction"
	proposal.proposal_date = add_days(nowdate(), -45)
	proposal.location = "طريق الملك فهد، الرياض، المملكة العربية السعودية"
	proposal.property_location = "قطعة أرض رقم 5678، مخطط الإدارة، مساحة 3000 متر مربع"
	
	# Proposer
	proposal.employee = employees[1].name if len(employees) > 1 else employees[0].name
	proposal.employee_name = frappe.db.get_value("Employee", proposal.employee, "employee_name")
	if len(departments) > 1:
		proposal.department = departments[1].name
	elif departments:
		proposal.department = departments[0].name
	
	proposal.investment_type = "بناء مجمع إداري للإيجار"
	proposal.expected_value = "عائد استثماري متوقع 18% سنوياً، قيمة المشروع 8 مليون ريال"
	
	# Description
	proposal.project_description = """
	<strong>وصف المشروع:</strong><br>
	بناء مجمع إداري متكامل في طريق الملك فهد يتكون من:<br>
	<ul>
		<li>مبنى إداري (10 طوابق)</li>
		<li>60 مكتب إداري</li>
		<li>قاعات اجتماعات</li>
		<li>مواقف سيارات (100 موقف)</li>
		<li>مرافق خدمية (كافيتريا، صالة استقبال)</li>
	</ul>
	
	<strong>الهدف من المشروع:</strong><br>
	تلبية الطلب على المكاتب الإدارية في المنطقة، وتحقيق عائد إيجاري مستقر.
	"""
	
	# Naming Series
	proposal.naming_series = "PROJ-.YYYY.-.####"
	
	# Team Members
	proposal.append("team_members", {
		"employee": proposal.employee,
		"role": "مدير المشروع",
		"responsibilities": "الإشراف العام، التنسيق، المتابعة"
	})
	if len(employees) > 2:
		proposal.append("team_members", {
			"employee": employees[2].name,
			"role": "مهندس موقع",
			"responsibilities": "الإشراف الميداني، متابعة الجودة"
		})
	if len(employees) > 3:
		proposal.append("team_members", {
			"employee": employees[3].name,
			"role": "مهندس كميات",
			"responsibilities": "حساب الكميات، متابعة التكاليف"
		})
	
	# Evaluation Reports
	proposal.append("evaluation_reports", {
		"evaluation_type": "Projects Management",
		"evaluated_by": frappe.session.user,
		"evaluation_date": add_days(nowdate(), -40),
		"feasibility_status": "Feasible",
		"estimated_cost": 8000000,
		"estimated_duration": 360,
		"regulatory_requirements": "رخصة بناء، رخصة دفاع مدني، رخصة كهرباء",
		"risks": "تقلبات أسعار المواد، تأخير في الحصول على التراخيص",
		"recommendations": "المشروع قابل للتنفيذ، يُنصح بالبدء فور الحصول على التراخيص"
	})
	
	proposal.append("evaluation_reports", {
		"evaluation_type": "Financial Management",
		"evaluated_by": frappe.session.user,
		"evaluation_date": add_days(nowdate(), -35),
		"feasibility_status": "Feasible",
		"estimated_cost": 8000000,
		"roi_estimate": 18,
		"financial_risks": "تقلبات أسعار الفائدة، تغيرات في السوق",
		"recommendations": "المشروع مجدي مالياً مع عائد استثماري جيد"
	})
	
	proposal.projects_mgmt_feasible = 1
	proposal.financial_mgmt_feasible = 1
	proposal.initial_estimated_cost = 8000000
	proposal.initial_estimated_duration = 360
	
	# Feasibility Items
	proposal.append("feasibility_items", {
		"item_type": "BOQ Item",
		"item_code": "CON-001",
		"item_name": "أعمال الحفر والردم",
		"description": "حفر أساسات المبنى",
		"quantity": 3000,
		"uom": get_or_create_uom("Nos"),
		"unit_rate": 25,
		"amount": 75000
	})
	
	proposal.append("feasibility_items", {
		"item_type": "BOQ Item",
		"item_code": "CON-002",
		"item_name": "الخرسانة المسلحة",
		"description": "خرسانة مسلحة للمبنى",
		"quantity": 5000,
		"uom": get_or_create_uom("Nos"),
		"unit_rate": 350,
		"amount": 1750000
	})
	
	proposal.append("feasibility_items", {
		"item_type": "BOQ Item",
		"item_code": "CON-003",
		"item_name": "الحديد التسليحي",
		"description": "حديد تسليح",
		"quantity": 800,
		"uom": get_or_create_uom("Nos"),
		"unit_rate": 3500,
		"amount": 2800000
	})
	
	proposal.append("feasibility_items", {
		"item_type": "BOQ Item",
		"item_code": "CON-004",
		"item_name": "أعمال التشطيبات",
		"description": "تشطيبات داخلية وخارجية",
		"quantity": 1,
		"uom": get_or_create_uom("Nos"),
		"unit_rate": 2000000,
		"amount": 2000000
	})
	
	proposal.append("feasibility_items", {
		"item_type": "Financial Projection",
		"item_name": "التدفق النقدي السنة الأولى",
		"year": 1,
		"cash_flow": -5000000
	})
	
	proposal.append("feasibility_items", {
		"item_type": "Financial Projection",
		"item_name": "التدفق النقدي السنة الثانية",
		"year": 2,
		"cash_flow": -2000000
	})
	
	proposal.append("feasibility_items", {
		"item_type": "Financial Projection",
		"item_name": "التدفق النقدي السنة الثالثة",
		"year": 3,
		"cash_flow": 6000000
	})
	
	proposal.total_boq_amount = 6625000
	proposal.estimated_total_cost = 8000000
	proposal.estimated_roi = 18
	proposal.break_even_point = "الشهر 30 من بداية الإيجار"
	proposal.cash_flow_year_1 = -5000000
	proposal.cash_flow_year_2 = -2000000
	proposal.cash_flow_year_3 = 6000000
	
	proposal.layout_description = """
	<strong>المخطط المعماري:</strong><br>
	<ul>
		<li>مبنى إداري (10 طوابق)</li>
		<li>6 مكاتب لكل طابق</li>
		<li>قاعات اجتماعات في كل طابق</li>
		<li>مواقف سيارات (طابقين تحت الأرض)</li>
	</ul>
	"""
	
	# Licenses
	proposal.append("licenses", {
		"license_type": "Municipality",
		"license_number": "BLD-2025-5678",
		"application_date": add_days(nowdate(), -30),
		"status": "Approved",
		"issue_date": add_days(nowdate(), -10),
		"remarks": "رخصة بناء من أمانة منطقة الرياض"
	})
	
	proposal.append("licenses", {
		"license_type": "Civil Defense",
		"license_number": "CD-2025-9012",
		"application_date": add_days(nowdate(), -28),
		"status": "Approved",
		"issue_date": add_days(nowdate(), -8),
		"remarks": "رخصة دفاع مدني"
	})
	
	proposal.append("licenses", {
		"license_type": "Electricity",
		"license_number": "ELEC-2025-3456",
		"application_date": add_days(nowdate(), -25),
		"status": "Approved",
		"issue_date": add_days(nowdate(), -5),
		"remarks": "رخصة كهرباء"
	})
	
	proposal.append("licenses", {
		"license_type": "Water",
		"license_number": "WTR-2025-7890",
		"application_date": add_days(nowdate(), -22),
		"status": "Approved",
		"issue_date": add_days(nowdate(), -3),
		"remarks": "رخصة مياه"
	})
	
	# Contractor Offers
	proposal.append("contractor_offers", {
		"contractor": get_or_create_supplier("شركة الإنشاءات الكبرى"),
		"offer_date": add_days(nowdate(), -15),
		"total_amount": 7900000,
		"validity_date": add_days(nowdate(), 45),
		"duration_days": 360,
		"payment_terms": "30% مقدماً، 50% حسب الإنجاز، 20% عند التسليم",
		"warranty_period": 24,
		"status": "Accepted",
		"remarks": "عرض مقبول - أفضل سعر وجودة"
	})
	
	proposal.append("contractor_offers", {
		"contractor": get_or_create_supplier("مؤسسة البناء الحديث"),
		"offer_date": add_days(nowdate(), -14),
		"total_amount": 8200000,
		"validity_date": add_days(nowdate(), 45),
		"duration_days": 390,
		"payment_terms": "25% مقدماً، 55% حسب الإنجاز، 20% عند التسليم",
		"warranty_period": 36,
		"status": "Rejected",
		"remarks": "عرض أعلى سعراً"
	})
	
	proposal.selected_contractor = get_or_create_supplier("شركة الإنشاءات الكبرى")
	proposal.contract_amount = 7900000
	
	# Execution
	proposal.start_date = add_days(nowdate(), -5)
	proposal.expected_completion_date = add_days(nowdate(), 355)
	proposal.progress_percentage = 5
	
	# Weekly Reports
	proposal.append("weekly_reports", {
		"week_start_date": add_days(nowdate(), -7),
		"week_end_date": nowdate(),
		"reported_by": frappe.session.user,
		"report_date": nowdate(),
		"progress_percentage": 5,
		"work_completed": "بدء أعمال الحفر والردم، تجهيز الموقع",
		"work_planned": "متابعة الحفر، بدء صب الأساسات",
		"issues_challenges": "لا توجد مشاكل"
	})
	
	# Monthly Financial
	proposal.append("monthly_financial_reports", {
		"month": "January",
		"year": 2025,
		"reported_by": frappe.session.user,
		"report_date": nowdate(),
		"budgeted_amount": 1000000,
		"actual_spent": 950000,
		"variance": -50000,
		"variance_percentage": -5,
		"remarks": "الإنفاق ضمن المخطط"
	})
	
	# Attachments - skip for demo (attachment field is required)
	# Users can add attachments manually in the UI
	# proposal.append("supporting_documents", {...})
	
	# Handover Items
	proposal.append("handover_items", {
		"item_description": "فحص جودة الأعمال الإنشائية",
		"category": "Quality Check",
		"status": "Pending"
	})
	
	proposal.append("handover_items", {
		"item_description": "فحص أنظمة الكهرباء",
		"category": "System",
		"status": "Pending"
	})
	
	proposal.append("handover_items", {
		"item_description": "فحص أنظمة المياه",
		"category": "System",
		"status": "Pending"
	})
	
	proposal.append("handover_items", {
		"item_description": "تسليم المخططات النهائية",
		"category": "Documentation",
		"status": "Pending"
	})
	
	proposal.append("handover_items", {
		"item_description": "تسليم شهادات الضمان",
		"category": "Documentation",
		"status": "Pending"
	})
	
	# Status - keep as draft for demo
	proposal.status = "Draft"
	# Don't set workflow_state manually - let workflow handle it
	
	proposal.insert(ignore_permissions=True)
	# Don't submit - keep as draft for demo purposes
	print(f"✅ Created: {proposal.name} - {proposal.project_name}")


def get_or_create_supplier(supplier_name):
	"""Get or create a supplier"""
	supplier = frappe.db.get_value("Supplier", {"supplier_name": supplier_name}, "name")
	if not supplier:
		supplier_doc = frappe.new_doc("Supplier")
		supplier_doc.supplier_name = supplier_name
		supplier_doc.supplier_group = "All Supplier Groups"
		supplier_doc.insert(ignore_permissions=True)
		supplier = supplier_doc.name
		print(f"  ✅ Created Supplier: {supplier_name}")
	return supplier


def get_or_create_uom(uom_name):
	"""Get or create a UOM, or use default if not found"""
	# Try common UOM names first
	common_uoms = ["Nos", "Unit", "Box", "Kg", "Ton", "Meter", "Square Meter", "Cubic Meter"]
	
	# Check if requested UOM exists
	uom = frappe.db.get_value("UOM", {"uom_name": uom_name}, "name")
	if uom:
		return uom
	
	# Try common UOMs
	for common_uom in common_uoms:
		uom = frappe.db.get_value("UOM", {"uom_name": common_uom}, "name")
		if uom:
			return uom
	
	# Get any existing UOM
	existing_uom = frappe.db.get_value("UOM", {}, "name")
	if existing_uom:
		return existing_uom
	
	# Create default UOM if none exists
	uom_doc = frappe.new_doc("UOM")
	uom_doc.uom_name = "Nos"
	uom_doc.insert(ignore_permissions=True)
	return uom_doc.name


def execute():
	"""Main execution function"""
	create_demo_proposals()

