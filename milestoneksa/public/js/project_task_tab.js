frappe.ui.form.on("Project", {
	__mks_task_tab_version: "2026-06-14T12:00Z-task-tab-tabulator-v32",

	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("Sync Tasks"), () => {
				frm.events.render_project_task_tab(frm);
				frappe.show_alert({ message: __("Task table synced"), indicator: "green" });
			}, __("Project Tasks"));
			frm.add_custom_button(__("Send Daily Task Summary"), () => {
				frappe.call({
					method: "milestoneksa.tasks.daily_task_summary.send_daily_task_summary_for_project",
					args: { project: frm.doc.name },
					callback(r) {
						if (r?.message) {
							frappe.show_alert({
								message: r.message.message || __("Daily task summary sent."),
								indicator: "green",
							});
						}
					},
					error(err) {
						frappe.msgprint({
							title: __("Error"),
							message: err.message || err.exc,
							indicator: "red",
						});
					},
				});
			}, __("Project Tasks"));
		}
		frm.events.render_project_task_tab(frm);
	},

	after_save(frm) {
		frm.events.render_project_task_tab(frm);
	},

	ensure_project_task_tab_styles() {
		const styleId = "mks-task-tab-styles-v32";
		if (document.getElementById(styleId)) return;
		const link = document.createElement("link");
		link.id = styleId;
		link.rel = "stylesheet";
		link.href = `/assets/milestoneksa/css/project_task_tab.css?v=50`;
		document.head.appendChild(link);
	},

	get_project_task_wrapper(frm) {
		const activeWrapper = frm.__project_task_active_wrapper;
		if (activeWrapper?.length && document.body.contains(activeWrapper.get(0))) {
			return activeWrapper;
		}
		return frm.fields_dict.custom_project_tasks_html?.$wrapper;
	},

	render_project_task_tab(frm, targetWrapper = null, options = {}) {
		frm.events.ensure_project_task_tab_styles();
		frm.events.destroy_project_task_tabulator(frm);

		const field = frm.fields_dict.custom_project_tasks_html;
		if (!field) {
			frappe.msgprint({
				title: __("Setup Required"),
				message: __("Custom field 'custom_project_tasks_html' not found. Please reload the page."),
				indicator: "orange",
			});
			return;
		}

		const renderTarget = targetWrapper || frm.__project_task_render_target;
		const wrapper = renderTarget || field.$wrapper;
		const isFullscreen = Boolean(options.fullscreen || frm.__project_task_render_fullscreen);
		const currentLang = (
			frappe.boot?.lang ||
			frappe.lang ||
			document.documentElement.getAttribute("lang") ||
			""
		).toLowerCase();
		const isRtl = document.documentElement.dir === "rtl" || /^ar\b/.test(currentLang);
		frm.__project_task_render_target = null;
		frm.__project_task_render_fullscreen = false;
		frm.__project_task_active_wrapper = wrapper;
		wrapper
			.empty()
			.addClass("project-task-tab-wrapper")
			.toggleClass("project-task-tab-wrapper--fullscreen", isFullscreen)
			.toggleClass("project-task-tab-wrapper--rtl", isRtl)
			.attr("dir", isRtl ? "rtl" : "ltr");

		if (frm.is_new()) {
			wrapper.append(
				$("<div class='text-muted small mt-2'>").text(
					__("Save the project to manage tasks from this tab.")
				)
			);
			return;
		}

		frm.__selected_task_names = new Set();

		const icon = (name) =>
			`<svg class="icon icon-sm"><use href="#icon-${name}"></use></svg>`;

		const header = $(`
			<div class="project-tasks-toolbar">
				<div class="project-tasks-toolbar__title-row">
					<div class="toolbar-title">${__("Project Tasks")}</div>
					<p class="text-muted small mb-0">
						${__("Click highlighted cells to edit inline. Parent tasks auto-update from children.")}
					</p>
				</div>
				<div class="project-tasks-toolbar__actions">
					<button class="btn btn-default btn-sm" data-role="delete-selected" disabled>
						${icon("delete")} ${__("Delete Selected")}
					</button>
					<button class="btn btn-default btn-sm" data-role="expand-all">${__("Expand All")}</button>
					<button class="btn btn-default btn-sm" data-role="collapse-all">${__("Collapse All")}</button>
					<button class="btn btn-default btn-sm" data-role="recalc-parents">
						${icon("refresh")} ${__("Recalc Parents")}
					</button>
					<button class="btn btn-default btn-sm" data-role="manage-columns">
						${icon("setting-gear")} ${__("Columns")}
					</button>
					${
						isFullscreen
							? ""
							: `<button class="btn btn-default btn-sm" data-role="open-fullscreen">
								${icon("maximize")} ${__("Full Screen")}
							</button>`
					}
					<button class="btn btn-primary btn-sm" data-role="add-task">
						${icon("add")} ${__("Add Task")}
					</button>
					<button class="btn btn-default btn-sm" data-role="refresh-tasks">
						${icon("refresh")} ${__("Refresh")}
					</button>
				</div>
				<div class="project-tasks-toolbar__filters">
					<label class="project-task-filter-check">
						<input type="checkbox" data-role="hide-completed">
						<span>${__("Hide Completed")}</span>
					</label>
					<label class="project-task-filter-select">
						<span>${__("Status")}</span>
						<select class="form-control form-control-sm" data-role="status-filter">
							<option value="">${__("All Statuses")}</option>
						</select>
					</label>
					<span class="text-muted small" data-role="filter-count"></span>
				</div>
			</div>
		`);

		const tableWrapper = $(`
			<div class="project-task-table-scroll">
				<div class="project-task-tabulator" data-role="task-tabulator"></div>
			</div>
		`);

		const emptyState = $(`
			<div class="d-none" data-role="empty">
				${icon("task").replace("icon-sm", "icon-xl text-muted mb-3")}
				<h5 class="text-muted">${__("No Tasks Yet")}</h5>
				<p class="text-muted mb-0">${__("Use Add Task to create your first task for this project.")}</p>
			</div>
		`);

		const loadingState = $(`
			<div class="text-center py-5" data-role="loading">
				<div class="spinner-border text-primary" role="status"></div>
				<div class="mt-3 text-muted">${__("Loading tasks...")}</div>
			</div>
		`);

		wrapper.append(header, tableWrapper, emptyState, loadingState);

		header.find("[data-role='add-task']").on("click", () => frm.events.open_project_task_dialog(frm));
		header.find("[data-role='refresh-tasks']").on("click", () => frm.events.load_project_tasks(frm));
		header.find("[data-role='recalc-parents']").on("click", () => frm.events.recalculate_all_parents(frm));
		header.find("[data-role='manage-columns']").on("click", () => frm.events.open_project_task_column_dialog(frm));
		header.find("[data-role='open-fullscreen']").on("click", () => frm.events.open_project_task_fullscreen(frm));
		header.find("[data-role='expand-all']").on("click", () => frm.events.expand_all_tasks(frm));
		header.find("[data-role='collapse-all']").on("click", () => frm.events.collapse_all_tasks(frm));
		header.find("[data-role='delete-selected']").on("click", () => frm.events.delete_selected_tasks(frm));
		header.find("[data-role='hide-completed']").on("change", function () {
			frm.events.set_project_task_filter(frm, { hide_completed: $(this).prop("checked") });
		});
		header.find("[data-role='status-filter']").on("change", function () {
			frm.events.set_project_task_filter(frm, { status: $(this).val() || "" });
		});
		frm.events.update_project_task_filter_controls(frm, wrapper);

		frm.__project_task_load_target = wrapper;
		frm.events.load_project_tasks(frm);
	},

	open_project_task_fullscreen(frm) {
		const dialog = new frappe.ui.Dialog({
			title: __("Project Tasks"),
			fields: [{ fieldname: "task_table", fieldtype: "HTML" }],
		});

		dialog.show();
		dialog.$wrapper.addClass("project-task-fullscreen-modal");
		dialog.$wrapper.find(".modal-dialog").css({
			height: "calc(100vh - 24px)",
			margin: "12px auto",
			"max-width": "calc(100vw - 24px)",
			width: "calc(100vw - 24px)",
		});
		dialog.$wrapper.find(".modal-content").css("height", "100%");
		dialog.$wrapper.find(".modal-body").css({
			display: "flex",
			"flex-direction": "column",
			overflow: "hidden",
			padding: "12px",
		});

		const modalWrapper = dialog.fields_dict.task_table.$wrapper;
		modalWrapper.css({
			display: "flex",
			flex: "1 1 auto",
			"flex-direction": "column",
			"min-height": 0,
		});
		dialog.$wrapper
			.find(".form-layout, .form-page, .form-section, .section-body, .form-column, .form-column > form, .frappe-control, .control-input-wrapper, .control-value")
			.css({
				display: "flex",
				flex: "1 1 auto",
				"flex-direction": "column",
				"min-height": 0,
				width: "100%",
			});
		frm.__project_task_fullscreen_dialog = dialog;
		frm.__project_task_fullscreen_wrapper = modalWrapper;
		frm.__project_task_active_wrapper = modalWrapper;

		dialog.$wrapper.on("hidden.bs.modal", () => {
			frm.events.destroy_project_task_tabulator(frm);
			if (frm.__project_task_active_wrapper?.get(0) === modalWrapper.get(0)) {
				frm.__project_task_active_wrapper = frm.fields_dict.custom_project_tasks_html?.$wrapper;
			}
			if (frm.__project_task_fullscreen_wrapper?.get(0) === modalWrapper.get(0)) {
				frm.__project_task_fullscreen_wrapper = null;
			}
			frm.events.render_project_task_tab(frm);
		});

		setTimeout(() => {
			frm.__project_task_render_target = modalWrapper;
			frm.__project_task_render_fullscreen = true;
			frm.__project_task_active_wrapper = modalWrapper;
			frm.events.render_project_task_tab(frm);
			modalWrapper.find(".project-task-table-scroll").css({
				flex: "1 1 auto",
				height: "calc(100vh - 230px)",
				"max-height": "calc(100vh - 230px)",
				"min-height": 0,
				"overflow-x": "auto",
				"overflow-y": "auto",
			});
			frm.events.ensure_fullscreen_tasks_loaded(frm, modalWrapper, 0);
		}, 100);
	},

	ensure_fullscreen_tasks_loaded(frm, modalWrapper, attempt = 0) {
		if (!modalWrapper?.length || !document.body.contains(modalWrapper.get(0))) return;
		const loadingVisible = modalWrapper.find("[data-role='loading']").is(":visible");
		const hasRows = (frm.__project_task_tabulator?.getDataCount?.() || 0) > 0;
		if (!loadingVisible || hasRows) return;

		frm.__project_task_load_target = modalWrapper;
		frm.__project_task_active_wrapper = modalWrapper;
		frm.events.load_project_tasks(frm);

		if (attempt < 2) {
			setTimeout(() => frm.events.ensure_fullscreen_tasks_loaded(frm, modalWrapper, attempt + 1), 1200);
		}
	},

	get_project_task_columns() {
		return [
			{ id: "select", label: __("Select"), locked: true, minWidth: 36 },
			{ id: "move", label: __("Move"), locked: true, minWidth: 44 },
			{ id: "subject", label: __("Task Name"), locked: true, minWidth: 420 },
			{ id: "wbs", label: __("WBS"), minWidth: 52 },
			{ id: "status", label: __("Status"), minWidth: 86, editable: true },
			{ id: "priority", label: __("Priority"), minWidth: 84, editable: true },
			{ id: "exp_start_date", label: __("Plan Start"), minWidth: 96, editable: true },
			{ id: "exp_end_date", label: __("Plan End"), minWidth: 96, editable: true },
			{ id: "duration_days", label: __("Duration"), minWidth: 76, defaultVisible: false },
			{ id: "planned_hours", label: __("Plan Hrs"), minWidth: 82, editable: true, defaultVisible: false },
			{ id: "custom_actual_start_date", label: __("Actual Start"), minWidth: 98, editable: true },
			{ id: "custom_actual_end_date", label: __("Actual End"), minWidth: 98, editable: true },
			{ id: "actual_duration_days", label: __("Act. Dur."), minWidth: 82, defaultVisible: false },
			{ id: "actual_hours", label: __("Act. Hrs"), minWidth: 82, defaultVisible: false },
			{ id: "total_costing_amount", label: __("Cost"), minWidth: 92, defaultVisible: false },
			{ id: "actions", label: __("Actions"), locked: true, minWidth: 110 },
		];
	},

	destroy_project_task_tabulator(frm) {
		if (frm.__project_task_tabulator) {
			try {
				frm.events.save_task_expanded_state(frm);
				frm.__project_task_tabulator.destroy();
			} catch (e) {
				// ignore teardown errors during rerender
			}
			frm.__project_task_tabulator = null;
		}
	},

	filter_project_tasks_for_display(frm, tasks) {
		const filters = frm.events.get_project_task_filters(frm);
		const visible = new Set();
		const byName = {};
		(tasks || []).forEach((task) => {
			byName[task.name] = task;
		});

		const matches = (task) => {
			if (filters.hide_completed && frm.events.is_completed_task_status(task.status)) return false;
			if (filters.status && task.status !== filters.status) return false;
			return true;
		};

		(tasks || []).forEach((task) => {
			if (!matches(task)) return;
			let current = task;
			while (current?.name && !visible.has(current.name)) {
				visible.add(current.name);
				current = current.parent_task ? byName[current.parent_task] : null;
			}
		});

		return (tasks || []).filter((task) => visible.has(task.name));
	},

	build_project_task_tree_data(frm, tasks) {
		const filtered = frm.events.filter_project_tasks_for_display(frm, tasks);
		const nodesByName = {};
		filtered.forEach((task) => {
			nodesByName[task.name] = { ...task, _children: [] };
		});

		const roots = [];
		filtered.forEach((task) => {
			const node = nodesByName[task.name];
			if (task.parent_task && nodesByName[task.parent_task]) {
				nodesByName[task.parent_task]._children.push(node);
			} else {
				roots.push(node);
			}
		});

		const sortSiblings = (nodeList) => {
			nodeList.sort((a, b) => {
				const idxDiff = (Number(a.idx) || 0) - (Number(b.idx) || 0);
				if (idxDiff) return idxDiff;
				const lftDiff = (Number(a.lft) || 0) - (Number(b.lft) || 0);
				if (lftDiff) return lftDiff;
				return (a.subject || "").localeCompare(b.subject || "");
			});
			nodeList.forEach((node) => sortSiblings(node._children || []));
		};
		sortSiblings(roots);

		const prune = (nodeList) =>
			nodeList.map((node) => {
				const next = { ...node };
				if (next._children?.length) {
					next._children = prune(next._children);
				} else {
					delete next._children;
				}
				return next;
			});

		frm.__task_hierarchy = {};
		const indexHierarchy = (nodeList, parentTask = null) => {
			nodeList.forEach((node) => {
				const children = node._children || [];
				frm.__task_hierarchy[node.name] = {
					...node,
					parent_task: parentTask,
					children: children.map((child) => ({ ...child })),
				};
				if (children.length) indexHierarchy(children, node.name);
			});
		};
		indexHierarchy(roots);

		return prune(roots);
	},

	get_task_meta_options(frm) {
		const meta = frm.__project_task_meta || {};
		return {
			status_options: meta.status_options || [
				"Open",
				"Working",
				"Pending Review",
				"Overdue",
				"Completed",
				"Cancelled",
			],
			priority_options: meta.priority_options || ["Low", "Medium", "High", "Urgent"],
			currency: meta.currency,
		};
	},

	format_task_date(value) {
		return value ? frappe.datetime.str_to_user(value) : "-";
	},

	format_task_badge(value, cls) {
		const text = frappe.utils.escape_html(value ? __(value) : "-");
		return `<span class="task-badge ${cls}">${text}</span>`;
	},

	format_task_date_pill(value, cls) {
		const text = frappe.utils.escape_html(value ? frappe.datetime.str_to_user(value) : "-");
		return `<span class="task-date-pill ${cls}">${text}</span>`;
	},

	normalize_project_task_date_value(value) {
		if (!value) return null;
		if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return value;
		return frappe.datetime.user_to_str(value) || value;
	},

	get_project_task_native_date_editor() {
		return (cell, onRendered, success, cancel) => {
			const input = document.createElement("input");
			input.type = "date";
			input.className = "task-tabulator-native-date-editor";
			input.value = cell.getValue() || frappe.datetime.nowdate();

			let finished = false;
			const commit = () => {
				if (finished) return;
				finished = true;
				const value = input.value || "";
				success(value || null);
			};

			onRendered(() => {
				input.focus();
				input.select();
				setTimeout(() => {
					if (input.showPicker) {
						input.showPicker();
					}
				}, 0);
			});

			input.addEventListener("change", commit);
			input.addEventListener("keydown", (event) => {
				if (event.key === "Enter" || event.key === "Tab") {
					commit();
				} else if (event.key === "Escape") {
					finished = true;
					cancel();
				}
			});
			input.addEventListener("blur", () => setTimeout(commit, 100));

			return input;
		};
	},

	get_project_task_tabulator_columns(frm) {
		const { status_options, priority_options, currency } = frm.events.get_task_meta_options(frm);
		const esc = frappe.utils.escape_html;
		const dateEditor = frm.events.get_project_task_native_date_editor();

		return [
			{
				title: "",
				field: "__select__",
				formatter: "rowSelection",
				titleFormatter: "rowSelection",
				hozAlign: "center",
				headerHozAlign: "center",
				width: 58,
				minWidth: 58,
				headerSort: false,
				resizable: false,
				frozen: true,
			},
			{
				title: "",
				field: "__move__",
				formatter: "handle",
				rowHandle: true,
				hozAlign: "center",
				headerHozAlign: "center",
				width: 46,
				minWidth: 46,
				headerSort: false,
				resizable: false,
				frozen: true,
			},
			{
				title: __("Task Name"),
				field: "subject",
				minWidth: 390,
				widthGrow: 3,
				headerSort: true,
				frozen: true,
				formatter(cell) {
					const task = cell.getData();
					const subject = esc(task.subject || task.name || "");
					let parent = cell.getRow().getTreeParent();
					let treeDepth = 0;
					while (parent) {
						treeDepth += 1;
						parent = parent.getTreeParent();
					}
					const color = frm.events.get_task_level_color(treeDepth);
					const isGroup = Boolean(task._children?.length || task.is_group);
					return `<a class="task-tabulator-subject-link" data-task-link="${esc(task.name)}" style="color:${color};font-weight:${isGroup ? 700 : 400};">${subject}</a>`;
				},
			},
			{
				title: __("WBS"),
				field: "wbs",
				width: 70,
				headerSort: true,
			},
			{
				title: __("Status"),
				field: "status",
				width: 110,
				headerSort: true,
				editor: "list",
				editorParams: { values: status_options },
				formatter: (cell) =>
					frm.events.format_task_badge(
						cell.getValue(),
						frm.events.get_task_status_class(cell.getValue())
					),
			},
			{
				title: __("Priority"),
				field: "priority",
				width: 100,
				headerSort: true,
				editor: "list",
				editorParams: { values: priority_options },
				formatter: (cell) =>
					frm.events.format_task_badge(
						cell.getValue(),
						frm.events.get_task_priority_class(cell.getValue())
					),
			},
			{
				title: __("Plan Start"),
				field: "exp_start_date",
				width: 110,
				headerSort: true,
				editor: dateEditor,
				formatter: (cell) => frm.events.format_task_date(cell.getValue()),
			},
			{
				title: __("Plan End"),
				field: "exp_end_date",
				width: 110,
				headerSort: true,
				editor: dateEditor,
				formatter: (cell) => frm.events.format_task_date(cell.getValue()),
			},
			{
				title: __("Duration"),
				field: "duration_days",
				width: 90,
				headerSort: true,
				formatter: (cell) => {
					const value = cell.getValue();
					return value == null || isNaN(value) ? "-" : `${value} ${__("days")}`;
				},
			},
			{
				title: __("Plan Hrs"),
				field: "planned_hours",
				width: 90,
				headerSort: true,
				editor: "number",
				formatter: (cell) =>
					cell.getValue() == null
						? "-"
						: frappe.format(cell.getValue(), { fieldtype: "Float", precision: 2 }),
			},
			{
				title: __("Actual Start"),
				field: "custom_actual_start_date",
				width: 110,
				headerSort: true,
				editor: dateEditor,
				formatter: (cell) =>
					frm.events.format_task_date_pill(
						cell.getValue(),
						frm.events.get_task_actual_date_class(
							cell.getValue(),
							cell.getData(),
							"custom_actual_start_date"
						)
					),
			},
			{
				title: __("Actual End"),
				field: "custom_actual_end_date",
				width: 110,
				headerSort: true,
				editor: dateEditor,
				formatter: (cell) =>
					frm.events.format_task_date_pill(
						cell.getValue(),
						frm.events.get_task_actual_date_class(
							cell.getValue(),
							cell.getData(),
							"custom_actual_end_date"
						)
					),
			},
			{
				title: __("Act. Dur."),
				field: "actual_duration_days",
				width: 90,
				headerSort: true,
				formatter: (cell) => {
					const value = cell.getValue();
					return value == null || isNaN(value) ? "-" : `${value} ${__("days")}`;
				},
			},
			{
				title: __("Act. Hrs"),
				field: "actual_hours",
				width: 90,
				headerSort: true,
				formatter: (cell) =>
					cell.getValue() == null
						? "-"
						: frappe.format(cell.getValue(), { fieldtype: "Float", precision: 2 }),
			},
			{
				title: __("Cost"),
				field: "total_costing_amount",
				width: 100,
				headerSort: true,
				formatter: (cell) =>
					cell.getValue() == null
						? "-"
						: frappe.format(cell.getValue(), { fieldtype: "Currency", options: currency }),
			},
			{
				title: __("Actions"),
				field: "__actions__",
				width: 110,
				minWidth: 110,
				headerSort: false,
				hozAlign: "center",
				formatter() {
					return `
						<span class="task-actions-group">
							<button type="button" class="btn btn-link btn-sm p-0" data-action="add-child" title="${esc(__("Add Child Task"))}">
								<svg class="icon icon-sm"><use href="#icon-add"></use></svg>
							</button>
							<button type="button" class="btn btn-link btn-sm p-0" data-action="edit-task" title="${esc(__("Edit"))}">
								<svg class="icon icon-sm"><use href="#icon-edit"></use></svg>
							</button>
							<button type="button" class="btn btn-link btn-sm p-0 text-danger" data-action="delete-task" title="${esc(__("Delete"))}">
								<svg class="icon icon-sm"><use href="#icon-delete"></use></svg>
							</button>
						</span>
					`;
				},
			},
		];
	},

	bind_project_task_tabulator_events(frm) {
		const table = frm.__project_task_tabulator;
		if (!table) return;

		frm.events.install_project_task_drag_guard(frm);
		table.on("rowSelectionChanged", () => frm.events.sync_tabulator_selection(frm));
		table.on("rowMoved", (row) => frm.events.handle_project_task_row_moved(frm, row));
		table.on("rowMoveCancelled", () => frm.events.handle_project_task_row_move_cancelled(frm));
		table.on("cellEdited", (cell) => frm.events.handle_project_task_cell_edited(frm, cell));
		table.on("dataTreeRowExpanded", () => {
			if (!frm.__applying_task_expanded_state) frm.events.save_task_expanded_state(frm);
		});
		table.on("dataTreeRowCollapsed", () => {
			if (!frm.__applying_task_expanded_state) frm.events.save_task_expanded_state(frm);
		});
		table.on("cellClick", (e, cell) => {
			const actionBtn = e.target.closest("[data-action]");
			if (actionBtn) {
				e.stopPropagation();
				const task = cell.getRow().getData();
				const action = actionBtn.dataset.action;
				if (action === "add-child") frm.events.open_project_task_dialog(frm, null, task.name);
				if (action === "edit-task") frm.events.open_project_task_dialog(frm, task);
				if (action === "delete-task") frm.events.delete_single_task(frm, task);
				return;
			}

			const link = e.target.closest("[data-task-link]");
			if (link) {
				e.preventDefault();
				e.stopPropagation();
				frappe.set_route("Form", "Task", link.dataset.taskLink);
			}
		});
	},

	install_project_task_drag_guard(frm) {
		const table = frm.__project_task_tabulator;
		const moveRow = table?.modules?.moveRow;
		if (!moveRow || moveRow.__mks_same_parent_guard) return;

		const originalStartMove = moveRow.startMove;
		const originalMoveHover = moveRow.moveHover;
		const originalEndMove = moveRow.endMove;
		const getComponentParent = (component) => component?.getTreeParent?.()?.getData?.()?.name || "";
		const getInternalParent = (internalRow) => getComponentParent(internalRow?.getComponent?.());
		const removePointerRecovery = () => {
			if (!moveRow.__mks_recover_after_pointer_up) return;
			document.removeEventListener("mouseup", moveRow.__mks_recover_after_pointer_up, true);
			document.removeEventListener("pointerup", moveRow.__mks_recover_after_pointer_up, true);
			document.removeEventListener("touchend", moveRow.__mks_recover_after_pointer_up, true);
			moveRow.__mks_recover_after_pointer_up = null;
		};
		const clearStuckMoveTimeout = () => {
			if (!moveRow.__mks_stuck_move_timeout) return;
			clearTimeout(moveRow.__mks_stuck_move_timeout);
			moveRow.__mks_stuck_move_timeout = null;
		};
		const cleanupMoveArtifacts = () => {
			if (moveRow.hoverElement?.parentNode) moveRow.hoverElement.parentNode.removeChild(moveRow.hoverElement);
			if (moveRow.placeholderElement?.parentNode) moveRow.placeholderElement.parentNode.removeChild(moveRow.placeholderElement);
			table.element.classList.remove("tabulator-block-select", "tabulator-movingrow-sending");
			document.body.removeEventListener("mousemove", moveRow.moveHover);
			document.body.removeEventListener("mouseup", moveRow.endMove);
			moveRow.moving = false;
			moveRow.toRow = false;
			moveRow.toRowAfter = false;
			removePointerRecovery();
			clearStuckMoveTimeout();
		};
		const recoverStuckMove = () => {
			const previousTasks = moveRow.__mks_previous_tasks || frm.__project_task_drag_previous_tasks;
			if (!previousTasks) return;

			const movingComponent = moveRow.__mks_moving_component;
			const isStuck = Boolean(moveRow.moving);
			const isDisconnected =
				movingComponent && !document.body.contains(movingComponent.getElement());
			if (!isStuck && !isDisconnected) return;

			cleanupMoveArtifacts();
			frappe.msgprint({
				title: __("Invalid Move"),
				message: __("Tasks can only be dragged within the same parent group."),
				indicator: "orange",
			});
			frm.events.restore_project_task_tabulator_order(frm, previousTasks);
			frm.__project_task_drag_previous_tasks = null;
			moveRow.__mks_previous_tasks = null;
			moveRow.__mks_moving_component = null;
			moveRow.__mks_moving_parent = null;
			moveRow.__mks_invalid_parent_drop = false;
		};

		moveRow.startMove = function (...args) {
			const movingComponent = args[1]?.getComponent?.();
			this.__mks_previous_tasks = (frm.__project_tasks_data || []).map((task) => ({ ...task }));
			frm.__project_task_drag_previous_tasks = this.__mks_previous_tasks;
			this.__mks_moving_component = movingComponent;
			this.__mks_moving_parent = getComponentParent(movingComponent);
			this.__mks_invalid_parent_drop = false;
			this.__mks_stuck_move_timeout = setTimeout(recoverStuckMove, 2500);
			return originalStartMove.apply(this, args);
		};

		moveRow.moveHover = function (...args) {
			const result = originalMoveHover.apply(moveRow, args);
			if (moveRow.moving && moveRow.toRow) {
				const movingParent = moveRow.__mks_moving_parent ?? getInternalParent(moveRow.moving);
				const targetParent = getInternalParent(moveRow.toRow);
				if (movingParent !== targetParent) {
					moveRow.__mks_invalid_parent_drop = true;
					moveRow.toRow = false;
					moveRow.toRowAfter = false;
				}
			}
			return result;
		};

		moveRow.endMove = function (...args) {
			const invalidParentDrop = Boolean(moveRow.__mks_invalid_parent_drop);
			const previousTasks = moveRow.__mks_previous_tasks;
			const movingComponent = moveRow.__mks_moving_component;
			const hadValidTarget = Boolean(moveRow.toRow) && !invalidParentDrop;
			const result = originalEndMove.apply(moveRow, args);
			removePointerRecovery();
			clearStuckMoveTimeout();
			const disconnectedMove = movingComponent && !document.body.contains(movingComponent.getElement());
			if ((invalidParentDrop || disconnectedMove) && frm.__project_task_drag_previous_tasks) {
				frappe.msgprint({
					title: __("Invalid Move"),
					message: __("Tasks can only be dragged within the same parent group."),
					indicator: "orange",
				});
				frm.events.restore_project_task_tabulator_order(frm, previousTasks);
				frm.__project_task_drag_previous_tasks = null;
			} else if (hadValidTarget && movingComponent) {
				frm.__project_task_drag_previous_tasks = null;
				setTimeout(() => {
					frm.events.handle_project_task_row_moved(frm, movingComponent, previousTasks);
				}, 50);
			} else if (!invalidParentDrop) {
				frm.__project_task_drag_previous_tasks = null;
			}
			moveRow.__mks_previous_tasks = null;
			moveRow.__mks_moving_component = null;
			moveRow.__mks_moving_parent = null;
			moveRow.__mks_invalid_parent_drop = false;
			return result;
		};

		moveRow.__mks_same_parent_guard = true;
	},

	handle_project_task_row_move_cancelled(frm) {
		const previousTasks = frm.__project_task_drag_previous_tasks;
		if (!previousTasks) return;

		frappe.msgprint({
			title: __("Invalid Move"),
			message: __("Tasks can only be dragged within the same parent group."),
			indicator: "orange",
		});
		frm.events.restore_project_task_tabulator_order(frm, previousTasks);
		frm.__project_task_drag_previous_tasks = null;
	},

	handle_project_task_cell_edited(frm, cell) {
		const field = cell.getField();
		const editableFields = [
			"status",
			"priority",
			"exp_start_date",
			"exp_end_date",
			"planned_hours",
			"custom_actual_start_date",
			"custom_actual_end_date",
		];
		if (!editableFields.includes(field)) return;

		let value = cell.getValue();
		if (
			["exp_start_date", "exp_end_date", "custom_actual_start_date", "custom_actual_end_date"].includes(
				field
			) &&
			value
		) {
			value = frm.events.normalize_project_task_date_value(value);
		}

		const taskName = cell.getRow().getData().name;
		const oldValue = cell.getOldValue();
		const updates = { [field]: value || null };

		if (["exp_start_date", "exp_end_date"].includes(field)) {
			const rowData = cell.getRow().getData();
			const nextStart = field === "exp_start_date" ? updates.exp_start_date : rowData.exp_start_date;
			const nextEnd = field === "exp_end_date" ? updates.exp_end_date : rowData.exp_end_date;
			if (nextStart && nextEnd && nextStart > nextEnd) {
				if (field === "exp_start_date") updates.exp_end_date = nextStart;
				else updates.exp_start_date = nextEnd;
			}
		}

		if (field === "status" && value === "Completed") {
			frm.events.confirm_parent_task_completion(frm, taskName, updates, (acknowledgedUpdates) => {
				frm.events.quick_update_task(frm, taskName, acknowledgedUpdates, { reload: true });
			});
			cell.setValue(oldValue, true);
			return;
		}

		frm.events.quick_update_task(frm, taskName, updates, { reload: true });
	},

	get_project_task_sibling_order_from_dom(frm, parentTask) {
		const table = frm.__project_task_tabulator;
		if (!table) return [];

		const siblingSet = new Set(
			(frm.__project_tasks_data || [])
				.filter((task) => (task.parent_task || "") === (parentTask || ""))
				.map((task) => task.name)
		);

		return [...table.element.querySelectorAll(".tabulator-tableholder .tabulator-row [data-task-link]")]
			.map((el) => el.dataset.taskLink)
			.filter((name) => name && siblingSet.has(name));
	},

	handle_project_task_row_moved(frm, row, previousTasks = null) {
		if (frm.__project_task_reorder_pending) return;

		const table = frm.__project_task_tabulator;
		previousTasks = previousTasks || (frm.__project_tasks_data || []).map((task) => ({ ...task }));
		const data = row.getData();
		const originalTask = previousTasks.find((task) => task.name === data.name);
		const parentTask = originalTask ? originalTask.parent_task || "" : data.parent_task || "";

		if (table?.getSorters?.().length) {
			frappe.show_alert({
				message: __("Clear column sorting before dragging tasks to change WBS order."),
				indicator: "orange",
			});
			frm.events.restore_project_task_tabulator_order(frm, previousTasks);
			return;
		}

		if (!originalTask) {
			frappe.show_alert({
				message: __("Unable to validate this task move. Please refresh and try again."),
				indicator: "orange",
			});
			frm.events.restore_project_task_tabulator_order(frm, previousTasks);
			return;
		}

		const siblingNames = (frm.__project_tasks_data || [])
			.filter((task) => (task.parent_task || "") === parentTask)
			.map((task) => task.name);
		const originalOrder = [...siblingNames].sort((a, b) => {
			const taskA = previousTasks.find((task) => task.name === a);
			const taskB = previousTasks.find((task) => task.name === b);
			const idxDiff = (Number(taskA?.idx) || 0) - (Number(taskB?.idx) || 0);
			if (idxDiff) return idxDiff;
			return (Number(taskA?.lft) || 0) - (Number(taskB?.lft) || 0);
		});

		const movedNames = frm.events.get_project_task_sibling_order_from_dom(frm, parentTask);
		const orderedNames = [
			...movedNames,
			...siblingNames.filter((name) => !movedNames.includes(name)),
		];
		if (!movedNames.length || orderedNames.join("|") === originalOrder.join("|")) return;
		if (
			orderedNames.length !== siblingNames.length ||
			orderedNames.some((name) => !siblingNames.includes(name))
		) {
			frappe.msgprint({
				title: __("Invalid Move"),
				message: __("Tasks can only be dragged within the same parent group."),
				indicator: "orange",
			});
			frm.events.restore_project_task_tabulator_order(frm, previousTasks);
			return;
		}

		frm.events.sync_project_task_tabulator_wbs(frm);
		frm.events.apply_project_task_sibling_order(frm, parentTask, orderedNames);
		frm.events.reorder_project_task_siblings(frm, parentTask, orderedNames, previousTasks);
	},

	apply_project_task_sibling_order(frm, parentTask, orderedNames) {
		const orderByName = {};
		orderedNames.forEach((name, index) => {
			orderByName[name] = index + 1;
		});

		(frm.__project_tasks_data || []).forEach((task) => {
			if ((task.parent_task || "") !== (parentTask || "")) return;
			if (!orderByName[task.name]) return;
			task.idx = orderByName[task.name];
		});
	},

	restore_project_task_tabulator_order(frm, tasks = null) {
		const table = frm.__project_task_tabulator;
		if (!table) return;

		if (tasks) {
			frm.__project_tasks_data = tasks;
		}

		table.setData(frm.events.build_project_task_tree_data(frm, frm.__project_tasks_data || []));
		setTimeout(() => {
			frm.events.apply_saved_task_expanded_state(frm);
			frm.events.apply_project_task_tabulator_column_visibility(frm);
			frm.events.sync_tabulator_selection(frm);
		}, 0);
	},

	sync_project_task_tabulator_wbs(frm) {
		const table = frm.__project_task_tabulator;
		if (!table) return;

		const tasksByName = {};
		(frm.__project_tasks_data || []).forEach((task) => {
			tasksByName[task.name] = task;
		});

		const walkRows = (rows, prefix = "") => {
			rows.forEach((row, index) => {
				const data = row.getData();
				const wbs = prefix ? `${prefix}.${index + 1}` : String(index + 1);
				data.idx = index + 1;
				data.wbs = wbs;
				if (tasksByName[data.name]) {
					tasksByName[data.name].idx = data.idx;
					tasksByName[data.name].wbs = wbs;
				}
				row.update({ idx: data.idx, wbs });
				walkRows(row.getTreeChildren(), wbs);
			});
		};

		walkRows(table.getRows().filter((currentRow) => !currentRow.getTreeParent()));
	},

	render_project_task_tabulator(frm, tasks, targetWrapper = null) {
		const wrapper = targetWrapper || frm.events.get_project_task_wrapper(frm);
		const tableEl = wrapper?.find('[data-role="task-tabulator"]')[0];
		if (!tableEl) return;

		if (typeof Tabulator === "undefined") {
			frappe.msgprint({
				title: __("Tabulator Missing"),
				message: __("Tabulator library is not loaded. Please refresh the page."),
				indicator: "orange",
			});
			return;
		}

		frm.events.destroy_project_task_tabulator(frm);
		const treeData = frm.events.build_project_task_tree_data(frm, tasks || []);
		const expandedState = frm.__task_expanded_state || {};

		frm.__project_task_tabulator = new Tabulator(tableEl, {
			data: treeData,
			index: "name",
			layout: "fitDataStretch",
			height: "100%",
			dataTree: true,
			dataTreeChildField: "_children",
			dataTreeElementColumn: "subject",
			dataTreeStartExpanded(row, level) {
				const name = row.getData().name;
				if (name in expandedState) return expandedState[name];
				return true;
			},
			movableRows: true,
			selectable: true,
			reactiveData: false,
			resizableColumnFit: true,
			rowFormatter(row) {
				const rowElement = row.getElement();
				let parent = row.getTreeParent();
				let treeDepth = 0;
				while (parent) {
					treeDepth += 1;
					parent = parent.getTreeParent();
				}

				rowElement.classList.remove(
					"task-level-0",
					"task-level-1",
					"task-level-2",
					"task-level-3",
					"task-level-4",
					"task-level-5",
					"task-level-6",
					"parent-task-row"
				);
				rowElement.classList.add(`task-level-${Math.min(treeDepth, 6)}`);
				if (row.getData()._children?.length || row.getData().is_group) {
					rowElement.classList.add("parent-task-row");
				}
			},
			columns: frm.events.get_project_task_tabulator_columns(frm),
		});

		frm.events.bind_project_task_tabulator_events(frm);
		frm.events.apply_saved_task_expanded_state(frm);
		frm.events.apply_project_task_tabulator_column_visibility(frm);
		frm.events.sync_tabulator_selection(frm);
		frm.events.update_project_task_filter_count(frm);
	},

	apply_saved_task_expanded_state(frm) {
		const table = frm.__project_task_tabulator;
		const state = frm.__task_expanded_state || {};
		if (!table || !Object.keys(state).length) return;

		frm.__applying_task_expanded_state = true;
		const applyRows = (rows) => {
			rows.forEach((row) => {
				const children = row.getTreeChildren();
				if (!children.length) return;

				applyRows(children);
				const taskName = row.getData().name;
				if (state[taskName] === false) {
					row.treeCollapse();
				} else {
					row.treeExpand();
				}
			});
		};

		applyRows(table.getRows().filter((row) => !row.getTreeParent()));
		frm.__applying_task_expanded_state = false;
	},

	apply_project_task_tabulator_filters(frm) {
		if (!frm.__project_tasks_data?.length) return;
		const wrapper = frm.events.get_project_task_wrapper(frm);
		const emptyState = wrapper?.find("[data-role='empty']");
		const filtered = frm.events.filter_project_tasks_for_display(frm, frm.__project_tasks_data);
		if (!filtered.length) {
			frm.events.destroy_project_task_tabulator(frm);
			emptyState?.removeClass("d-none").find("h5").text(__("No Tasks Match Filters"));
			emptyState?.find("p").text(
				__("Change the status filter or uncheck Hide Completed to see more tasks.")
			);
			frm.events.update_project_task_filter_count(frm);
			return;
		}
		emptyState?.addClass("d-none");
		frm.events.render_project_task_tabulator(frm, frm.__project_tasks_data, wrapper);
	},

	apply_project_task_tabulator_column_visibility(frm) {
		const table = frm.__project_task_tabulator;
		if (!table) return;

		const fieldMap = {
			select: "__select__",
			move: "__move__",
			subject: "subject",
			wbs: "wbs",
			status: "status",
			priority: "priority",
			exp_start_date: "exp_start_date",
			exp_end_date: "exp_end_date",
			duration_days: "duration_days",
			planned_hours: "planned_hours",
			custom_actual_start_date: "custom_actual_start_date",
			custom_actual_end_date: "custom_actual_end_date",
			actual_duration_days: "actual_duration_days",
			actual_hours: "actual_hours",
			total_costing_amount: "total_costing_amount",
			actions: "__actions__",
		};

		const preferences = frm.events.get_project_task_column_preferences();
		preferences.forEach((pref) => {
			const field = fieldMap[pref.id];
			if (!field) return;
			const column = table.getColumn(field);
			if (!column) return;
			if (pref.visible === false) column.hide();
			else column.show();
		});
	},

	sync_tabulator_selection(frm) {
		const wrapper = frm.events.get_project_task_wrapper(frm);
		const table = frm.__project_task_tabulator;
		if (!wrapper?.length || !table) return;

		const selectedRows = table.getSelectedData() || [];
		frm.__selected_task_names = new Set(selectedRows.map((row) => row.name));
		wrapper.find("[data-role='delete-selected']").prop("disabled", selectedRows.length === 0);
	},

	get_project_task_filter_key(frm) {
		return `mks_project_task_filters_${frm.doc.name || "new"}`;
	},

	get_project_task_filters(frm) {
		if (frm.__project_task_filters) return frm.__project_task_filters;
		const defaults = { hide_completed: false, status: "" };
		try {
			frm.__project_task_filters = {
				...defaults,
				...JSON.parse(localStorage.getItem(frm.events.get_project_task_filter_key(frm)) || "{}"),
			};
		} catch (e) {
			frm.__project_task_filters = defaults;
		}
		return frm.__project_task_filters;
	},

	save_project_task_filters(frm) {
		localStorage.setItem(
			frm.events.get_project_task_filter_key(frm),
			JSON.stringify(frm.events.get_project_task_filters(frm))
		);
	},

	is_completed_task_status(status) {
		return ["completed", "complete", "closed"].includes(String(status || "").trim().toLowerCase());
	},

	set_project_task_filter(frm, updates) {
		frm.__project_task_filters = {
			...frm.events.get_project_task_filters(frm),
			...updates,
		};
		frm.events.save_project_task_filters(frm);
		frm.events.update_project_task_filter_controls(frm);
		frm.events.apply_project_task_tabulator_filters(frm);
	},

	update_project_task_filter_controls(frm, targetWrapper = null) {
		const wrapper = targetWrapper || frm.events.get_project_task_wrapper(frm);
		if (!wrapper?.length) return;

		const filters = frm.events.get_project_task_filters(frm);
		const select = wrapper.find("[data-role='status-filter']");
		const currentValue = filters.status || "";
		const options = frm.__project_task_meta?.status_options || [];

		select.empty().append($("<option>").val("").text(__("All Statuses")));
		options.forEach((status) => {
			select.append($("<option>").val(status).text(__(status)));
		});
		if (currentValue && !options.includes(currentValue)) {
			select.append($("<option>").val(currentValue).text(__(currentValue)));
		}

		wrapper.find("[data-role='hide-completed']").prop("checked", Boolean(filters.hide_completed));
		select.val(currentValue);
	},

	apply_project_task_filters(frm) {
		frm.events.apply_project_task_tabulator_filters(frm);
	},

	update_project_task_filter_count(frm) {
		const wrapper = frm.events.get_project_task_wrapper(frm);
		if (!wrapper?.length) return;

		const total = frm.__project_tasks_data?.length || 0;
		const shown = frm.__project_task_tabulator?.getDataCount?.() || 0;
		const filters = frm.events.get_project_task_filters(frm);
		const hasFilter = Boolean(filters.hide_completed || filters.status);

		wrapper.find("[data-role='filter-count']").text(
			hasFilter ? __("{0} of {1} shown", [shown, total]) : ""
		);
	},

	save_task_expanded_state(frm) {
		if (frm.__applying_task_expanded_state) return;
		const state = {};
		const table = frm.__project_task_tabulator;
		if (table) {
			const visitRows = (rows) => rows.forEach((row) => {
				if (row.getTreeChildren().length) {
					state[row.getData().name] = row.isTreeExpanded();
					visitRows(row.getTreeChildren());
				}
			});
			visitRows(table.getRows().filter((row) => !row.getTreeParent()));
		}
		frm.__task_expanded_state = state;
	},

	get_task_level_color(level) {
		const colors = [
			"var(--primary, #2490ef)",
			"var(--green-700, #13795b)",
			"var(--orange-700, #b25e09)",
			"var(--purple-700, #6f42c1)",
			"var(--cyan-700, #087990)",
			"var(--text-color, #1f272e)",
			"var(--text-color, #1f272e)",
		];
		return colors[Math.min(level, colors.length - 1)];
	},

	get_task_status_class(status) {
		const value = String(status || "").toLowerCase();
		if (["completed", "closed"].includes(value)) return "task-badge--green";
		if (["overdue"].includes(value)) return "task-badge--red";
		if (["working", "in progress"].includes(value)) return "task-badge--blue";
		if (["pending review"].includes(value)) return "task-badge--purple";
		if (["cancelled", "canceled"].includes(value)) return "task-badge--gray";
		return "task-badge--amber";
	},

	get_task_priority_class(priority) {
		const value = String(priority || "").toLowerCase();
		if (["urgent"].includes(value)) return "task-badge--red";
		if (["high"].includes(value)) return "task-badge--orange";
		if (["medium"].includes(value)) return "task-badge--blue";
		if (["low"].includes(value)) return "task-badge--green";
		return "task-badge--gray";
	},

	get_task_actual_date_class(value, task, dateField) {
		if (value) return "task-date-pill--set";
		const status = String(task.status || "").toLowerCase();
		if (status === "completed" && dateField === "custom_actual_end_date") return "task-date-pill--missing-danger";
		if (
			dateField === "custom_actual_start_date" &&
			task.exp_start_date &&
			frappe.datetime.get_diff(frappe.datetime.nowdate(), task.exp_start_date) > 0
		) {
			return "task-date-pill--missing-warning";
		}
		if (
			dateField === "custom_actual_end_date" &&
			task.exp_end_date &&
			frappe.datetime.get_diff(frappe.datetime.nowdate(), task.exp_end_date) > 0
		) {
			return "task-date-pill--missing-danger";
		}
		return "task-date-pill--missing";
	},

	get_project_task_column_preferences() {
		const columns = cur_frm.events.get_project_task_columns();
		const defaults = columns.map((column, index) => ({
			id: column.id,
			visible: column.locked || column.defaultVisible !== false,
			order: index + 1,
		}));
		const storageKey = "mks_project_task_columns_v2";

		try {
			const saved = JSON.parse(localStorage.getItem(storageKey) || "[]");
			const byId = {};
			saved.forEach((item) => {
				byId[item.id] = item;
			});
			return defaults.map((item) => ({
				...item,
				...(byId[item.id] || {}),
				visible: columns.find((c) => c.id === item.id)?.locked
					? true
					: byId[item.id]?.visible !== false,
			}));
		} catch (e) {
			return defaults;
		}
	},

	save_project_task_column_preferences(preferences) {
		localStorage.setItem("mks_project_task_columns_v2", JSON.stringify(preferences));
	},

	reset_project_task_column_preferences() {
		localStorage.removeItem("mks_project_task_columns_v2");
	},

	open_project_task_column_dialog(frm) {
		const columns = frm.events.get_project_task_columns().filter((column) => column.id !== "actions");
		const preferences = frm.events.get_project_task_column_preferences();
		const byId = {};
		preferences.forEach((item) => {
			byId[item.id] = item;
		});

		const columnRows = columns
			.map((column, index) => {
				const pref = byId[column.id] || {};
				const visible = pref.visible !== false;
				const order = pref.order || index + 1;
				const disabled = column.locked ? "disabled" : "";
				const lockedLabel = column.locked ? `<span class="text-muted small">${__("Locked")}</span>` : "";
				return `
					<tr data-column-id="${frappe.utils.escape_html(column.id)}">
						<td class="text-center">
							<input type="checkbox" data-role="column-visible" ${visible ? "checked" : ""} ${disabled}>
						</td>
						<td>
							<div class="column-name">${column.label}</div>
							${lockedLabel}
						</td>
						<td>
							<input type="number" class="form-control form-control-sm" data-role="column-order"
								value="${order}" min="1" step="1">
						</td>
					</tr>
				`;
			})
			.join("");

		const dialog = new frappe.ui.Dialog({
			title: __("Manage Task Columns"),
			fields: [
				{
					fieldname: "columns_html",
					fieldtype: "HTML",
					options: `
						<div class="mks-task-column-manager">
							<div class="text-muted small mb-2">
								${__("Keep only important columns visible for a smaller, clearer task table.")}
							</div>
							<div class="table-responsive">
								<table class="table table-bordered table-sm mb-0">
									<thead>
										<tr>
											<th class="text-center">${__("Show")}</th>
											<th>${__("Column")}</th>
											<th>${__("Order")}</th>
										</tr>
									</thead>
									<tbody>${columnRows}</tbody>
								</table>
							</div>
						</div>
					`,
				},
			],
			primary_action_label: __("Apply"),
			primary_action() {
				const nextPreferences = [];
				dialog.$wrapper.find("[data-column-id]").each(function (index) {
					const row = $(this);
					const id = row.data("column-id");
					const column = columns.find((item) => item.id === id);
					nextPreferences.push({
						id,
						visible: column?.locked
							? true
							: row.find("[data-role='column-visible']").prop("checked"),
						order: parseInt(row.find("[data-role='column-order']").val(), 10) || index + 1,
					});
				});
				nextPreferences.push({ id: "actions", visible: true, order: 999 });
				frm.events.save_project_task_column_preferences(nextPreferences);
				dialog.hide();
				frm.events.apply_project_task_tabulator_column_visibility(frm);
			},
		});

		dialog.add_custom_action(__("Reset to Default"), () => {
			frm.events.reset_project_task_column_preferences();
			dialog.hide();
			frm.events.apply_project_task_tabulator_column_visibility(frm);
			frappe.show_alert({ message: __("Column layout reset"), indicator: "green" });
		}, "btn-default");

		dialog.show();
	},

	expand_all_tasks(frm) {
		const table = frm.__project_task_tabulator;
		if (!table) return;
		const expandRows = (rows) => {
			rows.forEach((row) => {
				if (row.getTreeChildren().length) {
					row.treeExpand();
					expandRows(row.getTreeChildren());
				}
			});
		};
		expandRows(table.getRows().filter((row) => !row.getTreeParent()));
		frm.events.save_task_expanded_state(frm);
		frappe.show_alert({ message: __("All tasks expanded"), indicator: "blue" }, 2);
	},

	collapse_all_tasks(frm) {
		const table = frm.__project_task_tabulator;
		if (!table) return;
		const collapseRows = (rows) => {
			rows.forEach((row) => {
				if (row.getTreeChildren().length) {
					collapseRows(row.getTreeChildren());
					row.treeCollapse();
				}
			});
		};
		collapseRows(table.getRows().filter((row) => !row.getTreeParent()));
		frm.events.save_task_expanded_state(frm);
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
						indicator: "green",
					});
				}
				frm.events.load_project_tasks(frm);
			},
		});
	},

	load_project_tasks(frm) {
		const wrapper = frm.__project_task_load_target || frm.events.get_project_task_wrapper(frm);
		frm.__project_task_load_target = null;
		if (!wrapper?.length) return;
		frm.__project_task_active_wrapper = wrapper;

		frm.events.save_task_expanded_state(frm);
		frm.events.destroy_project_task_tabulator(frm);

		frm.__selected_task_names = new Set();
		wrapper.find("[data-role='delete-selected']").prop("disabled", true);

		const emptyState = wrapper.find("[data-role='empty']");
		const loadingState = wrapper.find("[data-role='loading']");

		emptyState.addClass("d-none");
		loadingState.removeClass("d-none");

		frappe.call({
			method: "milestoneksa.api.project_tasks.get_project_tasks",
			args: { project: frm.doc.name },
			callback: (r) => {
				loadingState.addClass("d-none");

				if (!r?.message) {
					emptyState.removeClass("d-none");
					return;
				}

				const { tasks = [], currency, status_options = [], priority_options = [] } = r.message;
				frm.__project_task_meta = { currency, status_options, priority_options };

				if (!tasks.length) {
					emptyState.removeClass("d-none");
					return;
				}

				frm.__project_tasks_data = tasks;
				frm.events.update_project_task_filter_controls(frm, wrapper);
				frm.events.apply_project_task_tabulator_filters(frm);
			},
			error: () => {
				loadingState.addClass("d-none");
				emptyState.removeClass("d-none");
				frappe.msgprint({
					title: __("Error Loading Tasks"),
					message: __("Unable to load tasks. Please try again."),
					indicator: "red",
				});
			},
		});
	},

	get_task_completion_children_from_hierarchy(frm, taskName) {
		const task = (frm.__task_hierarchy || {})[taskName];
		const children = [];
		const walk = (node, level = 1) => {
			(node.children || []).forEach((child) => {
				children.push({
					name: child.name,
					subject: child.subject || child.name,
					status: child.status || "",
					level,
				});
				walk(child, level + 1);
			});
		};
		if (task) walk(task);
		return children;
	},

	show_parent_completion_acknowledgement(frm, taskName, taskSubject, children, onConfirm) {
		if (!children.length) {
			onConfirm();
			return;
		}

		const escapeHtml = frappe.utils.escape_html;
		const rows = children
			.map((child) => {
				const indent = Math.max((child.level || 1) - 1, 0) * 18;
				return `
					<tr>
						<td style="padding-inline-start:${indent}px;">${escapeHtml(child.subject || child.name)}</td>
						<td class="text-muted small">${escapeHtml(child.name)}</td>
						<td>${escapeHtml(__(child.status || ""))}</td>
					</tr>
				`;
			})
			.join("");

		const dialog = new frappe.ui.Dialog({
			title: __("Complete Parent Task"),
			fields: [
				{
					fieldtype: "HTML",
					fieldname: "child_tasks_html",
					options: `
						<p class="text-muted">
							${__("You are completing a parent task. Please review its child tasks before continuing.")}
						</p>
						<div class="mb-2"><strong>${escapeHtml(taskSubject || taskName)}</strong></div>
						<div class="table-responsive" style="max-height: 320px; overflow: auto;">
							<table class="table table-bordered table-sm">
								<thead>
									<tr>
										<th>${__("Child Task")}</th>
										<th>${__("Task ID")}</th>
										<th>${__("Status")}</th>
									</tr>
								</thead>
								<tbody>${rows}</tbody>
							</table>
						</div>
					`,
				},
				{
					fieldtype: "Check",
					fieldname: "acknowledged",
					label: __("I acknowledge that this parent task has child tasks and still want to mark it Completed."),
					reqd: 1,
				},
			],
			primary_action_label: __("Acknowledge and Complete"),
			primary_action(values) {
				if (!values.acknowledged) {
					frappe.msgprint(__("Please acknowledge the child tasks before completing this parent task."));
					return;
				}
				dialog.hide();
				onConfirm();
			},
		});
		dialog.show();
	},

	confirm_parent_task_completion(frm, taskName, updates, onConfirm) {
		if (updates.completion_acknowledged || updates.status !== "Completed") {
			onConfirm(updates);
			return;
		}

		const task = (frm.__task_hierarchy || {})[taskName] || {};
		const children = frm.events.get_task_completion_children_from_hierarchy(frm, taskName);
		if (!children.length) {
			onConfirm(updates);
			return;
		}

		frm.events.show_parent_completion_acknowledgement(
			frm,
			taskName,
			task.subject || taskName,
			children,
			() => onConfirm({ ...updates, completion_acknowledged: 1 })
		);
	},

	quick_update_task(frm, taskName, updates, options = {}) {
		if (updates.status === "Completed" && !updates.completion_acknowledged) {
			frm.events.confirm_parent_task_completion(frm, taskName, updates, (acknowledgedUpdates) => {
				frm.events.quick_update_task(frm, taskName, acknowledgedUpdates, options);
			});
			return;
		}

		frappe.call({
			method: "milestoneksa.api.project_tasks.update_project_task",
			args: { task_name: taskName, updates },
			freeze: false,
			callback: () => {
				frappe.show_alert({ message: __("Task updated"), indicator: "green" });
				if (options.reload !== false) frm.events.load_project_tasks(frm);
			},
		});
	},

	reorder_project_task_siblings(frm, parentTask, orderedNames, previousTasks = null) {
		frm.__project_task_reorder_pending = true;
		frm.events.save_task_expanded_state(frm);
		frappe.call({
			method: "milestoneksa.api.project_tasks.reorder_project_task_siblings",
			args: {
				project: frm.doc.name,
				parent_task: parentTask || "",
				task_names: orderedNames,
			},
			freeze: false,
			callback: (r) => {
				frm.__project_task_reorder_pending = false;
				if (r?.exc) {
					frappe.msgprint({
						title: __("Unable to Reorder"),
						message: __("Tasks can only be dragged within the same parent group."),
						indicator: "orange",
					});
					frm.events.restore_project_task_tabulator_order(frm, previousTasks);
					return;
				}
				frappe.show_alert({
					message: __("Task order saved"),
					indicator: "green",
				});
			},
			error: () => {
				frm.__project_task_reorder_pending = false;
				frappe.msgprint({
					title: __("Unable to Reorder"),
					message: __("Tasks can only be dragged within the same parent group."),
					indicator: "orange",
				});
				frm.events.restore_project_task_tabulator_order(frm, previousTasks);
			},
		});
	},

	open_project_task_dialog(frm, task = null, parentTask = null) {
		const isEdit = Boolean(task);
		const meta = frm.__project_task_meta || {};
		const statusOptions = meta.status_options || ["Open", "Working", "Pending Review", "Overdue", "Completed", "Cancelled"];
		const priorityOptions = meta.priority_options || ["Low", "Medium", "High", "Urgent"];

		const dialog = new frappe.ui.Dialog({
			title: isEdit ? __("Update Task") : parentTask ? __("Add Child Task") : __("Add Task"),
			fields: [
				{ fieldname: "subject", label: __("Subject"), fieldtype: "Data", reqd: 1 },
				{
					fieldname: "is_group",
					label: __("Is Group (Parent Task)"),
					fieldtype: "Check",
					default: 0,
					description: __("Check this if this task will have child tasks"),
				},
				{ fieldname: "status", label: __("Status"), fieldtype: "Select", options: statusOptions.join("\n"), default: "Open" },
				{ fieldname: "priority", label: __("Priority"), fieldtype: "Select", options: priorityOptions.join("\n"), default: "Medium" },
				{ fieldname: "task_weight", label: __("Weight"), fieldtype: "Float" },
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
					description: __("Optional: link this task beneath another task in this project."),
					default: parentTask || "",
					read_only: parentTask ? 1 : 0,
				},
				{ fieldname: "description", label: __("Description"), fieldtype: "Small Text" },
			],
			primary_action_label: isEdit ? __("Update") : __("Create"),
			primary_action(values) {
				if (!values.subject) {
					frappe.msgprint(__("Subject is required."));
					return;
				}
				if (values.exp_start_date && !values.custom_actual_start_date) {
					values.custom_actual_start_date = values.exp_start_date;
				}
				if (values.exp_end_date && !values.custom_actual_end_date) {
					values.custom_actual_end_date = values.exp_end_date;
				}
				if (parentTask) values.parent_task = parentTask;
				if (isEdit) frm.events.submit_task_update(frm, task.name, values, dialog);
				else frm.events.submit_task_create(frm, values, dialog);
			},
		});

		if (isEdit) {
			dialog.set_values({
				subject: task.subject,
				is_group: task.is_group || 0,
				status: task.status,
				priority: task.priority,
				task_weight: task.task_weight,
				exp_start_date: task.exp_start_date,
				exp_end_date: task.exp_end_date,
				planned_hours: task.planned_hours,
				custom_actual_start_date: task.custom_actual_start_date,
				custom_actual_end_date: task.custom_actual_end_date,
				parent_task: task.parent_task,
				description: task.description,
			});
			dialog.add_custom_action(__("Delete"), () => frm.events.delete_single_task(frm, task, dialog), "btn-danger");
		}

		dialog.fields_dict.parent_task.get_query = () => ({ filters: { project: frm.doc.name } });
		dialog.show();
	},

	submit_task_create(frm, values, dialog) {
		frappe.call({
			method: "milestoneksa.api.project_tasks.create_project_task",
			args: { project: frm.doc.name, task: values },
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
		if (values.status === "Completed" && !values.completion_acknowledged) {
			frm.events.confirm_parent_task_completion(frm, taskName, values, (acknowledgedValues) => {
				frm.events.submit_task_update(frm, taskName, acknowledgedValues, dialog);
			});
			return;
		}

		frappe.call({
			method: "milestoneksa.api.project_tasks.update_project_task",
			args: { task_name: taskName, updates: values },
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
		const table = frm.__project_task_tabulator;
		const selected = table
			? (table.getSelectedData() || []).map((row) => row.name)
			: Array.from(frm.__selected_task_names || []);

		if (!selected.length) {
			frappe.msgprint({
				title: __("No Tasks Selected"),
				message: __("Please select at least one task to delete."),
				indicator: "orange",
			});
			return;
		}

		frappe.confirm(
			__(
				"Are you sure you want to delete {0} selected task(s)? Child tasks must be selected separately. This action cannot be undone.",
				[selected.length]
			),
			() => {
				frappe.call({
					method: "milestoneksa.api.project_tasks.delete_project_tasks",
					args: { task_names: selected, force: 1, delete_connected: 0 },
					freeze: true,
					freeze_message: __("Deleting tasks..."),
					callback: (r) => {
						frappe.show_alert({
							message: __("{0} selected task(s) deleted successfully", [r?.message?.deleted_count ?? selected.length]),
							indicator: "green",
						});
						frm.events.load_project_tasks(frm);
					},
				});
			}
		);
	},

	delete_single_task(frm, task, dialog = null) {
		if (!task?.name) return;
		const taskSubject = task.subject || task.name;

		frappe.confirm(
			__(
				"Are you sure you want to delete the task '{0}'? Child tasks must be deleted first. This action cannot be undone.",
				[taskSubject]
			),
			() => {
				if (dialog) dialog.hide();
				frappe.call({
					method: "milestoneksa.api.project_tasks.delete_project_tasks",
					args: { task_names: [task.name], force: 1, delete_connected: 0 },
					freeze: true,
					freeze_message: __("Deleting task..."),
					callback: (r) => {
						frappe.show_alert({
							message: __("Deleted {0} task(s)", [r?.message?.deleted_count ?? 1]),
							indicator: "green",
						});
						frm.events.load_project_tasks(frm);
					},
				});
			}
		);
	},
});
