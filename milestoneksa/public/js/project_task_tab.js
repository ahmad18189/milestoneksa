frappe.ui.form.on("Project", {
	// ==========================================================
	// Project Task Tab Debug Marker
	// ==========================================================
	// If you do NOT see these logs in browser console, this file is NOT being executed
	// (likely because a "Client Script" is overriding the behavior).
	// ==========================================================
	__mks_task_tab_version: "2026-01-18T00:00Z-task-tab-delete+select",

	refresh(frm) {
		try {
			console.log(
				"[MKS][TASK TAB] refresh",
				{
					project: frm?.doc?.name,
					is_new: frm?.is_new?.(),
					version: frm?.events?.__mks_task_tab_version,
				}
			);
		} catch (e) {
			// noop
		}
		// Add custom button in form toolbar
		if (!frm.is_new()) {
			frm.add_custom_button(__("Sync Tasks"), () => {
				frm.events.render_project_task_tab(frm);
				frappe.show_alert({
					message: __("Task table synced"),
					indicator: "green"
				});
			});
		}
		
		frm.events.render_project_task_tab(frm);
	},

	after_save(frm) {
		try {
			console.log(
				"[MKS][TASK TAB] after_save",
				{ project: frm?.doc?.name, version: frm?.events?.__mks_task_tab_version }
			);
		} catch (e) {
			// noop
		}
		frm.events.render_project_task_tab(frm);
	},

	render_project_task_tab(frm) {
		console.log("[MKS][TASK TAB] Starting render", {
			project: frm?.doc?.name,
			version: frm?.events?.__mks_task_tab_version,
			fields_available: Object.keys(frm.fields_dict || {}),
		});
		
		const field = frm.fields_dict.custom_project_tasks_html;
		if (!field) {
			console.warn("[MKS][TASK TAB] HTML field 'custom_project_tasks_html' not found!", {
				version: frm?.events?.__mks_task_tab_version,
			});
			frappe.msgprint({
				title: __("Debug Info"),
				message: __("Custom field 'custom_project_tasks_html' not found. Please reload the page."),
				indicator: "orange"
			});
			return;
		}
		
		console.log("[MKS][TASK TAB] Field found, rendering table...", {
			version: frm?.events?.__mks_task_tab_version,
		});

		const wrapper = field.$wrapper;
		wrapper.empty().addClass("project-task-tab-wrapper").css({
			"padding": "15px",
			"background": "#ffffff",
			"min-height": "400px"
		});

		if (frm.is_new()) {
			wrapper.append(
				$("<div class='text-muted small mt-2'>")
					.text(__("Save the project to manage tasks from this tab."))
			);
			return;
		}

		// Track selected tasks explicitly (prevents accidental delete when DOM state is wrong)
		frm.__selected_task_names = new Set();

		const header = $(`
			<style>
				.project-tasks-header {
					background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
					padding: 20px;
					border-radius: 8px;
					color: white;
					margin: 0 0 20px 0;
					box-shadow: 0 2px 8px rgba(0,0,0,0.1);
				}
				
				.project-tasks-header .h6 {
					color: white;
					font-size: 18px;
					font-weight: 600;
					margin-bottom: 5px;
				}
				
				.project-tasks-header small {
					color: rgba(255,255,255,0.9);
					font-size: 12px;
				}
				
				.project-tasks-header .btn {
					border: 1px solid rgba(255,255,255,0.3);
					background: rgba(255,255,255,0.15);
					color: white;
					backdrop-filter: blur(10px);
				}
				
				.project-tasks-header .btn:hover {
					background: rgba(255,255,255,0.25);
					border-color: rgba(255,255,255,0.5);
					transform: translateY(-2px);
					box-shadow: 0 4px 12px rgba(0,0,0,0.2);
				}
				
				.project-tasks-header .btn-primary {
					background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
					border: 1px solid white;
				}
				
				.project-tasks-header .btn-primary:hover {
					background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
					box-shadow: 0 4px 12px rgba(255,255,255,0.3);
				}
			</style>
			<div class="d-flex justify-content-between align-items-center mb-3 project-tasks-header">
				<div>
					<div class="h6 mb-0">📋 ${__("Project Tasks")}
						<span class="badge bg-dark ms-2" style="font-size: 10px; opacity: 0.85;">
							MKS <span data-role="mks-task-tab-version">unknown</span>
						</span>
					</div>
					<small>${__("Click cells with 📝 to edit inline. Parent tasks (blue) auto-update from children.")}</small>
				</div>
				<div>
					<button class="btn btn-sm btn-danger me-2" data-role="delete-selected" title="${__("Delete Selected Tasks")}">
						<svg class="icon icon-sm"><use href="#icon-delete"></use></svg> ${__("Delete Selected")}
					</button>
					<button class="btn btn-sm btn-light me-1" data-role="expand-all" title="${__("Expand All")}">
						▼ ${__("Expand")}
					</button>
					<button class="btn btn-sm btn-light me-2" data-role="collapse-all" title="${__("Collapse All")}">
						▶ ${__("Collapse")}
					</button>
					<button class="btn btn-sm btn-success" data-role="recalc-parents">
						<svg class="icon icon-sm"><use href="#icon-refresh"></use></svg> ${__("Recalc Parents")}
					</button>
					<button class="btn btn-sm btn-primary" data-role="add-task">
						<svg class="icon icon-sm"><use href="#icon-add"></use></svg> ${__("Add Task")}
					</button>
					<button class="btn btn-sm btn-secondary" data-role="refresh-tasks">
						<svg class="icon icon-sm"><use href="#icon-refresh"></use></svg> ${__("Refresh")}
					</button>
				</div>
			</div>
		`);

		const tableWrapper = $(`
			<style>
				/* Enhanced table wrapper */
				.project-task-tab-wrapper {
					font-family: 'Cairo', sans-serif !important;
				}
				
				.project-task-tab-wrapper * {
					font-family: 'Cairo', sans-serif !important;
				}

				/* Table styling */
				.project-task-table-wrapper {
					border-radius: 8px;
					overflow: visible;
					box-shadow: 0 1px 3px rgba(0,0,0,0.08);
					margin: 0;
					width: 100%;
				}
				
				.table-responsive {
					border-radius: 8px;
					border: 1px solid #dee2e6;
					overflow-x: auto;
					overflow-y: auto;
				}
				
				.project-task-table-wrapper .table {
					margin-bottom: 0;
					font-size: 13px;
					width: 100%;
					table-layout: auto;
				}
				
				/* Header styling */
				.project-task-table-wrapper .table thead th {
					background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
					border-bottom: 2px solid #dee2e6;
					font-weight: 600;
					font-size: 12px;
					text-transform: uppercase;
					letter-spacing: 0.3px;
					color: #495057;
					padding: 12px 8px;
					white-space: nowrap;
					position: sticky;
					top: 0;
					z-index: 10;
				}
				
				/* Editable cells */
				.editable-cell { 
					cursor: pointer; 
					background-color: #f8f9fa;
					transition: all 0.2s ease;
					position: relative;
					border-left: 2px solid transparent;
				}
				
				.editable-cell:hover { 
					background-color: #fff3cd;
					border-left-color: #ffc107;
					box-shadow: inset 0 0 0 1px #ffc107;
				}
				
				.editable-cell::after {
					content: '✎';
					position: absolute;
					right: 4px;
					top: 50%;
					transform: translateY(-50%);
					opacity: 0;
					font-size: 10px;
					color: #6c757d;
					transition: opacity 0.2s;
				}
				
				.editable-cell:hover::after {
					opacity: 0.6;
				}
				
				/* Parent task rows */
				.table-primary { 
					background: linear-gradient(90deg, #e7f3ff 0%, #d4e9ff 100%) !important;
					font-weight: 600;
					border-left: 4px solid #0d6efd !important;
				}
				
				.table-primary:hover {
					background: linear-gradient(90deg, #d4e9ff 0%, #c5e2ff 100%) !important;
				}
				
				/* Row hover effects */
				.project-task-table-wrapper .table tbody tr {
					transition: all 0.15s ease;
				}
				
				.project-task-table-wrapper .table tbody tr:hover {
					background-color: #f8f9fa;
					transform: scale(1.001);
					box-shadow: 0 2px 4px rgba(0,0,0,0.06);
				}
				
				/* Task subject link */
				.task-subject a {
					color: #0d6efd;
					text-decoration: none;
					transition: color 0.2s;
				}
				
				.task-subject a:hover {
					color: #0a58ca;
					text-decoration: underline;
				}
				
				.table-primary .task-subject a {
					color: #084298;
					font-weight: 600;
				}
				
				/* WBS badge */
				.project-task-table-wrapper td:nth-child(3) {
					font-family: 'Cairo', sans-serif !important;
					font-weight: 600;
					color: #6c757d;
					font-size: 11px;
				}

				/* Task subject cell should match Cairo */
				.project-task-table-wrapper .task-subject,
				.project-task-table-wrapper .task-subject a {
					font-family: 'Cairo', sans-serif !important;
					font-weight: 600;
				}
				
				/* Status badges */
				.project-task-table-wrapper td[data-field="status"] {
					font-weight: 500;
				}
				
				/* Actual date columns - green highlight */
				.project-task-table-wrapper td[data-field="custom_actual_start_date"],
				.project-task-table-wrapper td[data-field="custom_actual_end_date"] {
					background-color: #f0f9ff !important;
					border-left: 2px solid #17a2b8;
				}
				
				.project-task-table-wrapper td[data-field="custom_actual_start_date"]:hover,
				.project-task-table-wrapper td[data-field="custom_actual_end_date"]:hover {
					background-color: #d1f2eb !important;
					border-left-color: #20c997;
				}
				
				/* Action buttons */
				.project-task-table-wrapper .btn-link {
					color: #6c757d;
					transition: all 0.2s;
				}
				
				.project-task-table-wrapper .btn-link:hover {
					color: #0d6efd;
					transform: scale(1.2);
				}
				
				/* Collapse triangle */
				.collapse-triangle {
					display: inline-block;
					width: 16px;
					height: 16px;
					line-height: 16px;
					text-align: center;
					cursor: pointer;
					user-select: none;
					transition: transform 0.3s ease;
					color: #0d6efd;
					font-weight: bold;
					margin-right: 8px;
					border-radius: 3px;
					background: rgba(13, 110, 253, 0.1);
				}
				
				.collapse-triangle:hover {
					background: rgba(13, 110, 253, 0.2);
					transform: scale(1.2);
				}
				
				.collapse-triangle.collapsed {
					transform: rotate(-90deg);
				}
				
				.collapse-triangle.collapsed:hover {
					transform: rotate(-90deg) scale(1.2);
				}
				
				/* Child task rows */
				.child-task.hidden-by-collapse {
					display: none !important;
				}
				
				/* Loading and empty states */
				[data-role="loading"], [data-role="empty"] {
					padding: 40px;
					text-align: center;
				}
				
				/* Input fields in edit mode */
				.editable-cell .form-control-sm {
					border: 2px solid #0d6efd;
					box-shadow: 0 0 0 0.2rem rgba(13,110,253,.25);
				}
				
				/* Button styling */
				.project-task-tab-wrapper .btn {
					transition: all 0.2s ease;
				}
				
				.project-task-tab-wrapper .btn:hover {
					transform: translateY(-1px);
					box-shadow: 0 2px 4px rgba(0,0,0,0.15);
				}
				
				/* Responsive table scroll */
				.project-task-table-wrapper .table-responsive {
					max-height: 70vh;
					overflow-x: auto;
					overflow-y: auto;
				}
				
				.project-task-table-wrapper .table-responsive::-webkit-scrollbar {
					width: 10px;
					height: 10px;
				}
				
				.project-task-table-wrapper .table-responsive::-webkit-scrollbar-track {
					background: #f1f1f1;
					border-radius: 5px;
				}
				
				.project-task-table-wrapper .table-responsive::-webkit-scrollbar-thumb {
					background: linear-gradient(180deg, #888 0%, #666 100%);
					border-radius: 5px;
					border: 2px solid #f1f1f1;
				}
				
				.project-task-table-wrapper .table-responsive::-webkit-scrollbar-thumb:hover {
					background: linear-gradient(180deg, #555 0%, #333 100%);
				}
				
				/* Ensure content isn't cut off */
				.project-task-tab-wrapper {
					overflow: visible !important;
				}
				
				.project-task-table-wrapper .table td,
				.project-task-table-wrapper .table th {
					padding: 10px 8px;
					vertical-align: middle;
				}
				
				/* Checkbox styling */
				.task-checkbox {
					cursor: pointer;
					width: 18px;
					height: 18px;
					vertical-align: middle;
				}
				
				.task-row-selected {
					background-color: #fff3cd !important;
				}
				
				.task-row-selected:hover {
					background-color: #ffe69c !important;
				}
				
				/* Minimum column widths */
				.project-task-table-wrapper th:nth-child(1) { min-width: 40px; }
				.project-task-table-wrapper th:nth-child(2) { min-width: 220px; }
				.project-task-table-wrapper th:nth-child(3) { min-width: 60px; }
				.project-task-table-wrapper th:nth-child(4) { min-width: 120px; }
				.project-task-table-wrapper th:nth-child(5) { min-width: 100px; }
				.project-task-table-wrapper th:nth-child(6) { min-width: 130px; }
				.project-task-table-wrapper th:nth-child(7) { min-width: 130px; }
				.project-task-table-wrapper th:nth-child(10) { min-width: 130px; }
				.project-task-table-wrapper th:nth-child(11) { min-width: 130px; }
			</style>
			<div class="table-responsive project-task-table-wrapper">
				<table class="table table-bordered table-sm align-middle mb-0">
					<thead class="table-light">
						<tr>
							<th style="min-width: 40px; text-align: center;">
								<input type="checkbox" class="task-checkbox" data-role="select-all" title="${__("Select All")}">
							</th>
							<th style="min-width: 220px;">
								<svg class="icon icon-sm text-primary"><use href="#icon-task"></use></svg>
								${__("Task Name")}
							</th>
							<th><span class="badge bg-secondary">WBS</span></th>
							<th>📊 ${__("Status")} 📝</th>
							<th>⭐ ${__("Priority")} 📝</th>
							<th>📅 ${__("Planned Start")} 📝</th>
							<th>🏁 ${__("Planned Finish")} 📝</th>
							<th>⏱️ ${__("Duration")}</th>
							<th>🕐 ${__("Planned Hours")} 📝</th>
							<th style="background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%); font-weight: 700;">
								✅ ${__("Actual Start")} 📝
							</th>
							<th style="background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%); font-weight: 700;">
								✅ ${__("Actual End")} 📝
							</th>
							<th>📏 ${__("Actual Duration")}</th>
							<th>⏰ ${__("Actual Hours")}</th>
							<th>💰 ${__("Actual Cost")}</th>
							<th class="text-center" style="min-width: 90px;">⚙️ ${__("Actions")}</th>
						</tr>
					</thead>
					<tbody></tbody>
				</table>
			</div>
		`);

		const emptyState = $(`
			<div class="alert alert-light border mt-3 mb-0 d-none text-center" data-role="empty" style="padding: 60px; border-radius: 8px; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);">
				<svg class="icon icon-xl text-muted mb-3" style="width: 64px; height: 64px;"><use href="#icon-task"></use></svg>
				<h5 class="text-muted">${__("No Tasks Yet")}</h5>
				<p class="text-muted mb-0">${__("Use the Add Task button above to create your first task for this project.")}</p>
			</div>
		`);

		const loadingState = $(`
			<div class="text-center mt-5 mb-5" data-role="loading">
				<div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;">
					<span class="visually-hidden">${__("Loading...")}</span>
				</div>
				<div class="mt-3 text-muted">${__("Loading tasks...")}</div>
			</div>
		`);

		wrapper.append(header, tableWrapper, emptyState, loadingState);
		
		// Set visible version label (template string cannot safely interpolate frm)
		try {
			const v = frm?.events?.__mks_task_tab_version || "unknown";
			header.find('[data-role="mks-task-tab-version"]').text(v);
		} catch (e) {
			// noop
		}
		console.log("[MKS][TASK TAB] Header + Table injected into DOM", {
			version: frm?.events?.__mks_task_tab_version,
			has_delete_selected_btn: header.find("[data-role='delete-selected']").length,
			has_select_all: wrapper.find("[data-role='select-all']").length,
		});

		header.find("[data-role='add-task']").on("click", () => {
			frm.events.open_project_task_dialog(frm);
		});

		header.find("[data-role='refresh-tasks']").on("click", () => {
			frm.events.load_project_tasks(frm);
		});
		
		header.find("[data-role='recalc-parents']").on("click", () => {
			frm.events.recalculate_all_parents(frm);
		});
		
		header.find("[data-role='expand-all']").on("click", () => {
			frm.events.expand_all_tasks(frm);
		});
		
		header.find("[data-role='collapse-all']").on("click", () => {
			frm.events.collapse_all_tasks(frm);
		});
		
		header.find("[data-role='delete-selected']").on("click", () => {
			console.log("[MKS][TASK TAB] delete-selected clicked", {
				version: frm?.events?.__mks_task_tab_version,
			});
			frm.events.delete_selected_tasks(frm);
		});
		
		// Select all checkbox handler
		wrapper.on("change", "[data-role='select-all']", function() {
			const isChecked = $(this).prop("checked");
			console.log("[MKS][TASK TAB] select-all changed", {
				checked: isChecked,
				version: frm?.events?.__mks_task_tab_version,
			});
			// Update all row checkboxes and selection Set
			wrapper.find(".task-row-checkbox").prop("checked", isChecked).trigger("change");
		});

		frm.events.load_project_tasks(frm);
	},
	
	expand_all_tasks(frm) {
		const taskMap = frm.__task_hierarchy || {};
		Object.values(taskMap).forEach(task => {
			if (task.children && task.children.length > 0) {
				task.expanded = true;
				const row = $(`tr[data-task="${task.name}"]`);
				const triangle = row.find(".collapse-triangle");
				triangle.removeClass("collapsed");
				row.removeClass("collapsed");
			}
		});
		$("tr.child-task").removeClass("hidden-by-collapse").fadeIn(200);
		frappe.show_alert({ message: __("All tasks expanded"), indicator: "blue" }, 2);
	},
	
	collapse_all_tasks(frm) {
		const taskMap = frm.__task_hierarchy || {};
		Object.values(taskMap).forEach(task => {
			if (task.children && task.children.length > 0) {
				task.expanded = false;
				const row = $(`tr[data-task="${task.name}"]`);
				const triangle = row.find(".collapse-triangle");
				triangle.addClass("collapsed");
				row.addClass("collapsed");
			}
		});
		$("tr.child-task").addClass("hidden-by-collapse").fadeOut(200);
		frappe.show_alert({ message: __("All tasks collapsed"), indicator: "blue" }, 2);
	},
	
	recalculate_all_parents(frm) {
		frappe.call({
			method: "milestoneksa.api.project_tasks.recalculate_all_project_parents",
			args: { project: frm.doc.name },
			freeze: true,
			freeze_message: __("Recalculating parent tasks..."),
			callback: (r) => {
				if (r.message) {
					frappe.show_alert({
						message: __(`Updated ${r.message.updated_count} parent tasks`),
						indicator: "green"
					});
				}
				frm.events.load_project_tasks(frm);
			},
		});
	},

	load_project_tasks(frm) {
		const field = frm.fields_dict.custom_project_tasks_html;
		if (!field) {
			return;
		}

		const wrapper = field.$wrapper;
		
		// Reset selection state on every reload/render
		frm.__selected_task_names = new Set();
		wrapper.find("[data-role='select-all']").prop("checked", false).prop("indeterminate", false);

		const tableBody = wrapper.find("tbody");
		const emptyState = wrapper.find("[data-role='empty']");
		const loadingState = wrapper.find("[data-role='loading']");

		tableBody.empty();
		emptyState.addClass("d-none");
		loadingState.removeClass("d-none");

		console.log("[MKS][TASK TAB] Fetching tasks for project", {
			project: frm?.doc?.name,
			version: frm?.events?.__mks_task_tab_version,
		});
		
		frappe.call({
			method: "milestoneksa.api.project_tasks.get_project_tasks",
			args: { project: frm.doc.name },
			callback: (r) => {
				loadingState.addClass("d-none");
				console.log("[MKS][TASK TAB] get_project_tasks response", {
					version: frm?.events?.__mks_task_tab_version,
					has_message: !!r?.message,
					task_count: r?.message?.tasks?.length,
				});

				if (!r || !r.message) {
					console.warn("[MKS][TASK TAB] No data returned", {
						version: frm?.events?.__mks_task_tab_version,
					});
					emptyState.removeClass("d-none");
					return;
				}

				const { tasks = [], currency, status_options = [], priority_options = [] } = r.message;

				frm.__project_task_meta = {
					currency,
					status_options,
					priority_options,
				};

				if (!tasks.length) {
					emptyState.removeClass("d-none");
					return;
				}

				frm.__project_tasks_data = tasks;
				frm.events.render_task_hierarchy(frm, tasks, tableBody);
				frm.events.update_select_all_checkbox(frm);
			},
			error: (err) => {
				console.error("Project Task Tab: API Error:", err);
				loadingState.addClass("d-none");
				emptyState
					.removeClass("d-none")
					.text(__("Unable to load tasks. Check console for errors."));
				frappe.msgprint({
					title: __("Error Loading Tasks"),
					message: __("Unable to load tasks. Please check browser console for details."),
					indicator: "red"
				});
			},
		});
	},

	render_task_hierarchy(frm, tasks, tableBody) {
		// Build parent-child map
		const taskMap = {};
		const rootTasks = [];
		
		tasks.forEach(t => {
			taskMap[t.name] = { ...t, children: [], expanded: true };
		});
		
		tasks.forEach(t => {
			if (t.parent_task && taskMap[t.parent_task]) {
				taskMap[t.parent_task].children.push(taskMap[t.name]);
			} else {
				rootTasks.push(taskMap[t.name]);
			}
		});
		
		// Store task map in form for collapse/expand
		frm.__task_hierarchy = taskMap;
		
		// Render recursively
		function renderTask(task, level = 0, parentExpanded = true) {
			const row = frm.events.render_project_task_row(frm, task, level);
			tableBody.append(row);
			
			// Only show if parent is expanded
			if (!parentExpanded) {
				row.hide();
			}
			
			// Render children
			if (task.children && task.children.length > 0) {
				task.children.forEach(child => {
					renderTask(child, level + 1, parentExpanded && task.expanded);
				});
			}
		}
		
		rootTasks.forEach(task => renderTask(task, 0, true));
	},

	render_project_task_row(frm, task, level = 0) {
		const currency = frm.__project_task_meta?.currency;
		const meta = frm.__project_task_meta || {};
		const hasChildren = task.children && task.children.length > 0;
		const indent = level * 20;

		const toUserDate = (value) => (value ? frappe.datetime.str_to_user(value) : "-");
		const toDays = (value) => (isNaN(value) || value === null ? "-" : `${value} ${__("days")}`);
		const toHours = (value) =>
			value === null || value === undefined ? "-" : frappe.format(value, { fieldtype: "Float", precision: 2 });
		const toCurrency = (value) =>
			value === null || value === undefined
				? "-"
				: frappe.format(value, { fieldtype: "Currency", options: currency });

		const row = $(`
			<tr data-task="${frappe.utils.escape_html(task.name)}" 
			    data-parent="${frappe.utils.escape_html(task.parent_task || '')}"
			    data-level="${level}"
			    class="${hasChildren ? 'table-primary parent-task' : 'child-task'}">
				<td style="text-align: center; padding-left: 8px;">
					<input type="checkbox" class="task-checkbox task-row-checkbox" data-task="${frappe.utils.escape_html(task.name)}">
				</td>
				<td class="task-subject" style="padding-left: ${indent + 10}px;"></td>
				<td>${frappe.utils.escape_html(task.wbs || "")}</td>
				<td class="editable-cell" data-field="status">${frappe.utils.escape_html(task.status || "")}</td>
				<td class="editable-cell" data-field="priority">${frappe.utils.escape_html(task.priority || "")}</td>
				<td class="editable-cell" data-field="exp_start_date">${toUserDate(task.exp_start_date)}</td>
				<td class="editable-cell" data-field="exp_end_date">${toUserDate(task.exp_end_date)}</td>
				<td>${toDays(task.duration_days)}</td>
				<td class="editable-cell" data-field="planned_hours">${toHours(task.planned_hours)}</td>
				<td class="editable-cell" data-field="custom_actual_start_date" style="background-color: #f0f9ff;">${toUserDate(task.custom_actual_start_date)}</td>
				<td class="editable-cell" data-field="custom_actual_end_date" style="background-color: #f0f9ff;">${toUserDate(task.custom_actual_end_date)}</td>
				<td>${toDays(task.actual_duration_days)}</td>
				<td>${toHours(task.actual_hours)}</td>
				<td>${toCurrency(task.total_costing_amount)}</td>
				<td class="text-center">
					<button class="btn btn-link btn-sm p-0 me-1" data-role="add-child" title="${__("Add Child Task")}">
						<svg class="icon icon-sm"><use href="#icon-add"></use></svg>
					</button>
					<button class="btn btn-link btn-sm p-0 me-1" data-role="edit-task" title="${__("Edit")}">
						<svg class="icon icon-sm"><use href="#icon-edit"></use></svg>
					</button>
					<button class="btn btn-link btn-sm p-0 text-danger" data-role="delete-task" title="${__("Delete Task")}">
						<svg class="icon icon-sm"><use href="#icon-delete"></use></svg>
					</button>
				</td>
			</tr>
		`);

		// Subject cell with link and hierarchy indicator
		const subjectCell = row.find(".task-subject");
		
		if (hasChildren) {
			// Collapsible triangle for parent tasks
			const triangle = $(`
				<span class="collapse-triangle me-2" style="cursor: pointer; user-select: none; font-size: 14px; display: inline-block; transition: transform 0.2s;">
					▼
				</span>
			`);
			
			triangle.on("click", (e) => {
				e.stopPropagation();
				frm.events.toggle_task_children(frm, task.name);
			});
			
			subjectCell.append(triangle);
		} else {
			// Add spacing for alignment
			subjectCell.append($('<span class="me-2" style="width: 14px; display: inline-block;"></span>'));
		}
		
		const link = $(`<a class='${hasChildren ? "fw-bold" : ""}'>`)
			.text(task.subject || task.name)
			.on("click", () => frappe.set_route("Form", "Task", task.name));
		subjectCell.append(link);

		// Make cells editable on click
		row.find(".editable-cell").on("click", function() {
			frm.events.make_cell_editable(frm, $(this), task, meta);
		});

		// Add child task button
		row.find("[data-role='add-child']").on("click", () => {
			frm.events.open_project_task_dialog(frm, null, task.name);
		});

		// Edit task button
		row.find("[data-role='edit-task']").on("click", () => {
			frm.events.open_project_task_dialog(frm, task);
		});
		
		// Delete task button
		row.find("[data-role='delete-task']").on("click", () => {
			frm.events.delete_single_task(frm, task);
		});
		
		// Checkbox change handler
		row.find(".task-row-checkbox").on("change", function() {
			const isChecked = $(this).prop("checked");
			const taskName = $(this).data("task");
			
			if (!frm.__selected_task_names) {
				frm.__selected_task_names = new Set();
			}
			
			if (isChecked) {
				frm.__selected_task_names.add(taskName);
			} else {
				frm.__selected_task_names.delete(taskName);
			}
			
			if (isChecked) {
				row.addClass("task-row-selected");
			} else {
				row.removeClass("task-row-selected");
			}
			frm.events.update_select_all_checkbox(frm);
		});

		return row;
	},

	toggle_task_children(frm, taskName) {
		const taskMap = frm.__task_hierarchy || {};
		const task = taskMap[taskName];
		
		if (!task || !task.children || task.children.length === 0) {
			return;
		}
		
		// Toggle expanded state
		task.expanded = !task.expanded;
		
		// Find the row and triangle
		const row = $(`tr[data-task="${taskName}"]`);
		const triangle = row.find(".collapse-triangle");
		
		// Toggle triangle class and rotation
		if (task.expanded) {
			triangle.removeClass("collapsed");
			row.removeClass("collapsed");
		} else {
			triangle.addClass("collapsed");
			row.addClass("collapsed");
		}
		
		// Toggle all descendant rows with animation
		function toggleDescendants(parentTask, show) {
			parentTask.children.forEach(child => {
				const childRow = $(`tr[data-task="${child.name}"]`);
				
				if (show && task.expanded) {
					childRow.removeClass("hidden-by-collapse").fadeIn(200);
					// If this child is also expanded and has children, show them too
					if (child.expanded && child.children && child.children.length > 0) {
						toggleDescendants(child, true);
					}
				} else {
					childRow.addClass("hidden-by-collapse").fadeOut(200);
					// Hide all descendants regardless
					if (child.children && child.children.length > 0) {
						toggleDescendants(child, false);
					}
				}
			});
		}
		
		toggleDescendants(task, task.expanded);
		
		// Show feedback
		const childCount = task.children.length;
		const action = task.expanded ? "expanded" : "collapsed";
		frappe.show_alert({
			message: `${action === "expanded" ? "▼" : "▶"} ${childCount} child task${childCount > 1 ? "s" : ""} ${action}`,
			indicator: "blue"
		}, 2);
	},

	make_cell_editable(frm, cell, task, meta) {
		// Prevent multiple edit sessions
		if (cell.data("editing")) return;
		cell.data("editing", true);
		
		const field = cell.data("field");
		const currentValue = task[field];
		const originalHtml = cell.html();
		
		cell.empty().css("padding", "2px");
		
		let input;
		if (field === "status") {
			input = $(`<select class="form-control form-control-sm" style="width: 100%;"></select>`);
			(meta.status_options || []).forEach(opt => {
				input.append($("<option>").val(opt).text(opt).prop("selected", opt === currentValue));
			});
		} else if (field === "priority") {
			input = $(`<select class="form-control form-control-sm" style="width: 100%;"></select>`);
			(meta.priority_options || []).forEach(opt => {
				input.append($("<option>").val(opt).text(opt).prop("selected", opt === currentValue));
			});
		} else if (field === "exp_start_date" || field === "exp_end_date" || field === "custom_actual_start_date" || field === "custom_actual_end_date") {
			input = $(`<input type="date" class="form-control form-control-sm" style="width: 100%;">`);
			if (currentValue) {
				input.val(frappe.datetime.str_to_user(currentValue, "yyyy-mm-dd"));
			}
		} else if (field === "planned_hours") {
			input = $(`<input type="number" step="0.5" class="form-control form-control-sm" style="width: 100%;">`);
			input.val(currentValue || "");
		}
		
		cell.append(input);
		
		// Focus after a brief delay to ensure rendering
		setTimeout(() => {
			input.focus();
			if (input.is("select")) {
				input.click(); // Open dropdown
			}
		}, 50);
		
		let saved = false;
		
		const saveValue = () => {
			if (saved) return;
			saved = true;
			
			const newValue = input.val();
			
			// Restore cell appearance
			cell.data("editing", false);
			cell.css("padding", "");
			
			if (newValue && newValue !== currentValue) {
				const updates = {};
				updates[field] = newValue;
				cell.html(`<span class="text-muted"><i>Saving...</i></span>`);
				frm.events.quick_update_task(frm, task.name, updates);
			} else {
				// Just restore original
				cell.html(originalHtml);
			}
		};
		
		const cancelEdit = () => {
			if (saved) return;
			saved = true;
			cell.data("editing", false);
			cell.css("padding", "");
			cell.html(originalHtml);
		};
		
		// For select, save on change
		if (input.is("select")) {
			input.on("change", () => {
				saveValue();
			});
			input.on("blur", () => {
				setTimeout(cancelEdit, 100);
			});
		} else {
			// For inputs, save on blur or enter
			input.on("blur", () => {
				setTimeout(saveValue, 100);
			});
			input.on("keydown", (e) => {
				if (e.which === 13) { // Enter
					e.preventDefault();
					saveValue();
				} else if (e.which === 27) { // Escape
					e.preventDefault();
					cancelEdit();
				}
			});
		}
		
		// Prevent click from bubbling
		input.on("click", (e) => {
			e.stopPropagation();
		});
	},

	quick_update_task(frm, taskName, updates) {
		frappe.call({
			method: "milestoneksa.api.project_tasks.update_project_task",
			args: {
				task_name: taskName,
				updates: updates,
			},
			freeze: false,
			callback: () => {
				frappe.show_alert({ message: __("Task updated"), indicator: "green" });
				frm.events.load_project_tasks(frm);
			},
		});
	},

	open_project_task_dialog(frm, task = null, parentTask = null) {
		const isEdit = Boolean(task);
		const meta = frm.__project_task_meta || {};
		const statusOptions = meta.status_options || ["Open", "Working", "Pending Review", "Overdue", "Completed", "Cancelled"];
		const priorityOptions = meta.priority_options || ["Low", "Medium", "High", "Urgent"];

		const dialog = new frappe.ui.Dialog({
			title: isEdit ? __("Update Task") : (parentTask ? __("Add Child Task") : __("Add Task")),
			fields: [
				{ fieldname: "subject", label: __("Subject"), fieldtype: "Data", reqd: 1 },
				{ 
					fieldname: "is_group", 
					label: __("Is Group (Parent Task)"), 
					fieldtype: "Check",
					default: 0,
					description: __("Check this if this task will have child tasks")
				},
				{
					fieldname: "status",
					label: __("Status"),
					fieldtype: "Select",
					options: statusOptions.join("\n"),
					default: "Open",
				},
				{
					fieldname: "priority",
					label: __("Priority"),
					fieldtype: "Select",
					options: priorityOptions.join("\n"),
					default: "Medium",
				},
				{ fieldname: "col_break_1", fieldtype: "Column Break" },
				{ fieldname: "exp_start_date", label: __("Planned Start"), fieldtype: "Date" },
				{ fieldname: "exp_end_date", label: __("Planned Finish"), fieldtype: "Date" },
				{ fieldname: "planned_hours", label: __("Planned Hours"), fieldtype: "Float" },
				{ fieldname: "section_actual", label: __("Actual Dates"), fieldtype: "Section Break" },
				{ fieldname: "custom_actual_start_date", label: __("Actual Start Date"), fieldtype: "Date" },
				{ fieldname: "col_break_2", fieldtype: "Column Break" },
				{ fieldname: "custom_actual_end_date", label: __("Actual End Date"), fieldtype: "Date" },
				{ fieldname: "section_more", label: __("More Details"), fieldtype: "Section Break", collapsible: 1 },
				{
					fieldname: "parent_task",
					label: __("Parent Task"),
					fieldtype: "Link",
					options: "Task",
					description: __("Optional: link this task beneath another task."),
					default: parentTask || "",
					read_only: parentTask ? 1 : 0,
					depends_on: "eval:!doc.is_group",
				},
				{ fieldname: "description", label: __("Description"), fieldtype: "Small Text" },
			],
			primary_action_label: isEdit ? __("Update") : __("Create"),
			primary_action(values) {
				if (!values.subject) {
					frappe.msgprint(__("Subject is required."));
					return;
				}

				if (isEdit) {
					frm.events.submit_task_update(frm, task.name, values, dialog);
				} else {
					frm.events.submit_task_create(frm, values, dialog);
				}
			},
		});

		if (isEdit) {
			dialog.set_values({
				subject: task.subject,
				is_group: task.is_group || 0,
				status: task.status,
				priority: task.priority,
				exp_start_date: task.exp_start_date,
				exp_end_date: task.exp_end_date,
				planned_hours: task.planned_hours,
				custom_actual_start_date: task.custom_actual_start_date,
				custom_actual_end_date: task.custom_actual_end_date,
				parent_task: task.parent_task,
				description: task.description,
			});
			
			// Add delete button when editing
			dialog.add_custom_action(__("Delete"), () => {
				frm.events.delete_single_task(frm, task, dialog);
			}, "btn-danger");
		}

		dialog.show();
	},

	submit_task_create(frm, values, dialog) {
		frappe.call({
			method: "milestoneksa.api.project_tasks.create_project_task",
			args: {
				project: frm.doc.name,
				task: values,
			},
			freeze: true,
			freeze_message: __("Creating task..."),
			callback: () => {
				dialog.hide();
				frappe.show_alert({ message: __("Task created"), indicator: "green" });
				frm.events.load_project_tasks(frm);
			},
		});
	},

	submit_task_update(frm, taskName, values, dialog) {
		frappe.call({
			method: "milestoneksa.api.project_tasks.update_project_task",
			args: {
				task_name: taskName,
				updates: values,
			},
			freeze: true,
			freeze_message: __("Updating task..."),
			callback: () => {
				dialog.hide();
				frappe.show_alert({ message: __("Task updated"), indicator: "green" });
				frm.events.load_project_tasks(frm);
			},
		});
	},
	
	delete_selected_tasks(frm) {
		const field = frm.fields_dict.custom_project_tasks_html;
		if (!field) return;
		
		const wrapper = field.$wrapper;
		
		// SAFETY: never delete unless user explicitly selected rows
		const selected = Array.from(frm.__selected_task_names || []);
		if (!selected.length) {
			frappe.msgprint({
				title: __("No Tasks Selected"),
				message: __("Please select at least one task to delete."),
				indicator: "orange"
			});
			return;
		}
		const taskNames = selected;
		const taskCount = taskNames.length;
		
		frappe.confirm(
			__(
				"Are you sure you want to FORCE delete {0} selected task(s) AND all connected tasks (children + dependent tasks)? This action cannot be undone.",
				[taskCount]
			),
			() => {
				// User confirmed
				frappe.call({
					method: "milestoneksa.api.project_tasks.delete_project_tasks",
					args: {
						task_names: taskNames,
						force: 1,
						delete_connected: 1,
					},
					freeze: true,
					freeze_message: __("Deleting tasks..."),
					callback: (r) => {
						const deleted_count = r?.message?.deleted_count ?? taskCount;
						frappe.show_alert({
							message: __("{0} task(s) deleted successfully (including connected tasks)", [deleted_count]),
							indicator: "green"
						});
						frm.events.load_project_tasks(frm);
					},
					error: (err) => {
						console.error("Error deleting tasks:", err);
						frappe.msgprint({
							title: __("Error"),
							message: __("Failed to delete tasks. Please check console for details."),
							indicator: "red"
						});
					}
				});
			},
			() => {
				// User cancelled - do nothing
			}
		);
	},
	
	delete_single_task(frm, task, dialog = null) {
		if (!task || !task.name) {
			return;
		}
		
		const taskName = task.name;
		const taskSubject = task.subject || taskName;
		
		frappe.confirm(
			__(
				"Are you sure you want to FORCE delete the task '{0}' AND all connected tasks (children + dependent tasks)? This action cannot be undone.",
				[taskSubject]
			),
			() => {
				// User confirmed
				if (dialog) {
					dialog.hide();
				}
				
				frappe.call({
					method: "milestoneksa.api.project_tasks.delete_project_tasks",
					args: {
						task_names: [taskName],
						force: 1,
						delete_connected: 1,
					},
					freeze: true,
					freeze_message: __("Deleting task..."),
					callback: (r) => {
						const deleted_count = r?.message?.deleted_count ?? 1;
						frappe.show_alert({
							message: __("Deleted {0} task(s) (including connected tasks)", [deleted_count]),
							indicator: "green"
						});
						frm.events.load_project_tasks(frm);
					},
					error: (err) => {
						console.error("Error deleting task:", err);
						frappe.msgprint({
							title: __("Error"),
							message: __("Failed to delete task. Please check console for details."),
							indicator: "red"
						});
					}
				});
			},
			() => {
				// User cancelled - do nothing
			}
		);
	},
	
	update_select_all_checkbox(frm) {
		const field = frm.fields_dict.custom_project_tasks_html;
		if (!field) return;
		
		const wrapper = field.$wrapper;
		const allCheckboxes = wrapper.find(".task-row-checkbox");
		const checkedCheckboxes = wrapper.find(".task-row-checkbox:checked");
		const selectAllCheckbox = wrapper.find("[data-role='select-all']");
		
		// Keep Set in sync with DOM state (extra safety)
		frm.__selected_task_names = new Set(
			checkedCheckboxes.map(function() { return $(this).data("task"); }).get()
		);
		
		if (allCheckboxes.length === 0) {
			selectAllCheckbox.prop("checked", false);
			return;
		}
		
		// Update select all checkbox state
		if (checkedCheckboxes.length === 0) {
			selectAllCheckbox.prop("indeterminate", false);
			selectAllCheckbox.prop("checked", false);
		} else if (checkedCheckboxes.length === allCheckboxes.length) {
			selectAllCheckbox.prop("indeterminate", false);
			selectAllCheckbox.prop("checked", true);
		} else {
			selectAllCheckbox.prop("indeterminate", true);
		}
	},
});

