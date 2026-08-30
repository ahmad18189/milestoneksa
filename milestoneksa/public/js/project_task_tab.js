frappe.mks_task_plain_number = function (value, as_currency) {
	let raw = value;
	if (raw == null || raw === "") return "-";
	if (typeof raw === "string") {
		raw = raw.replace(/<[^>]*>/g, "").replace(/&nbsp;/gi, " ").trim();
	}
	if (raw === "" || raw === "-") return "-";
	const n = flt(raw);
	if (isNaN(n)) return "-";
	if (as_currency) {
		const precision = cint(frappe.defaults?.get_default?.("currency_precision")) || 2;
		return format_number(n, null, precision);
	}
	return format_number(n, null, Math.abs(n % 1) < 1e-9 ? 0 : 2);
};

// Standalone — Frappe form handlers are wrapped and lose `this` when called via frm.events.*
frappe.mks_normalize_task_date = function (value) {
	if (!value) return null;
	if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return value;
	return frappe.datetime.user_to_str(value) || value;
};

frappe.mks_read_task_date_control = function (control) {
	let value = control?.get_value?.();
	if (!value && control?.$input?.length) {
		value = control.$input.val();
	}
	return frappe.mks_normalize_task_date(value);
};

frappe.ui.form.on("Project", {
	__mks_task_tab_version: "2026-08-30T22:00Z-complete-loop-fix-v51",

	refresh(frm) {
		// Avoid double-render when both Client Script and doctype_js are present.
		if (frm.__mks_task_tab_refresh_token === frm.doc?.modified) {
			return;
		}
		frm.__mks_task_tab_refresh_token = frm.doc?.modified || true;

		if (!frm.is_new()) {
			frm.add_custom_button(__("Sync Tasks"), () => {
				frm.__mks_task_tab_refresh_token = null;
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
		const styleId = "mks-task-tab-styles-v48";
		if (!document.getElementById(styleId)) {
			const link = document.createElement("link");
			link.id = styleId;
			link.rel = "stylesheet";
			link.href = `/assets/milestoneksa/css/project_task_tab.css?v=67`;
			document.head.appendChild(link);
		}
		const inlineStyleId = "mks-task-tab-inline-styles-v48";
		if (!document.getElementById(inlineStyleId)) {
			const style = document.createElement("style");
			style.id = inlineStyleId;
			style.textContent =
				".project-task-tab-wrapper tr.task-row-focus-highlight td { box-shadow: inset 0 0 0 2px var(--primary, #2490ef); }";
			document.head.appendChild(style);
		}
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
		frm.events.destroy_project_task_table(frm);

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
		frm.__task_sort = frm.__task_sort || null;
		frm.events.load_task_expanded_state(frm);

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
					<button class="btn btn-default btn-sm d-none" data-role="clear-sort">
						${icon("close")} ${__("Custom sort active")} — ${__("Clear")}
					</button>
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
					<label class="project-task-filter-select">
						<span>${__("Assign To")}</span>
						<select class="form-control form-control-sm" data-role="assign-filter">
							<option value="">${__("All Assignees")}</option>
						</select>
					</label>
					<span class="text-muted small" data-role="filter-count"></span>
				</div>
			</div>
		`);

		const tableWrapper = $(`
			<div class="project-task-table-scroll">
				<table class="project-task-table">
					<thead data-role="task-table-head"></thead>
					<tbody data-role="task-table-body"></tbody>
					<tfoot data-role="task-table-foot"></tfoot>
				</table>
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
		header.find("[data-role='clear-sort']").on("click", () => frm.events.clear_project_task_sort(frm));
		header.find("[data-role='hide-completed']").on("change", function () {
			frm.events.set_project_task_filter(frm, { hide_completed: $(this).prop("checked") });
		});
		header.find("[data-role='status-filter']").on("change", function () {
			frm.events.set_project_task_filter(frm, { status: $(this).val() || "" });
		});
		header.find("[data-role='assign-filter']").on("change", function () {
			frm.events.set_project_task_filter(frm, { assign_to: $(this).val() || "" });
		});
		frm.events.update_project_task_filter_controls(frm, wrapper);
		frm.events.update_project_task_sort_control(frm);

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
			frm.events.destroy_project_task_table(frm);
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
		const hasRows = modalWrapper.find("[data-role='task-table-body'] tr[data-task-name]").length > 0;
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
			{ id: "status", label: __("Status"), minWidth: 86, editable: true, sortable: true },
			{ id: "priority", label: __("Priority"), minWidth: 84, editable: true, sortable: true },
			{ id: "assigned_to", label: __("Assign To"), minWidth: 160, editable: true, sortable: true },
			{ id: "exp_start_date", label: __("Plan Start"), minWidth: 96, editable: true, sortable: true },
			{ id: "exp_end_date", label: __("Plan End"), minWidth: 96, editable: true, sortable: true },
			{ id: "duration_days", label: __("Days"), minWidth: 72, sortable: true },
			{ id: "planned_hours", label: __("Plan Hrs"), minWidth: 82, editable: true, defaultVisible: false, sortable: true },
			{ id: "custom_actual_start_date", label: __("Actual Start"), minWidth: 98, editable: true, sortable: true },
			{ id: "custom_actual_end_date", label: __("Actual End"), minWidth: 98, editable: true, sortable: true },
			{ id: "actual_duration_days", label: __("Act. Days"), minWidth: 82, defaultVisible: false, sortable: true },
			{ id: "actual_hours", label: __("Act. Hrs"), minWidth: 82, defaultVisible: false, sortable: true },
			{ id: "total_costing_amount", label: __("Cost"), minWidth: 92, defaultVisible: false, sortable: true },
			{ id: "actions", label: __("Actions"), locked: true, minWidth: 110 },
		];
	},

	get_ordered_visible_columns(frm) {
		const columns = frm.events.get_project_task_columns();
		const preferences = frm.events.get_project_task_column_preferences();
		const byId = {};
		columns.forEach((column) => {
			byId[column.id] = column;
		});
		return preferences
			.filter((pref) => pref.visible !== false && byId[pref.id])
			.sort((a, b) => (a.order || 0) - (b.order || 0))
			.map((pref) => byId[pref.id]);
	},

	get_project_task_column_widths(frm) {
		const key = `mks_project_task_column_widths_${frm.doc.name || "new"}`;
		try {
			return JSON.parse(localStorage.getItem(key) || "{}");
		} catch (e) {
			return {};
		}
	},

	save_project_task_column_widths(frm, widths) {
		const key = `mks_project_task_column_widths_${frm.doc.name || "new"}`;
		localStorage.setItem(key, JSON.stringify(widths || {}));
	},

	load_task_expanded_state(frm) {
		const key = `mks_project_task_expanded_${frm.doc.name || "new"}`;
		try {
			frm.__task_expanded_state = JSON.parse(localStorage.getItem(key) || "{}");
		} catch (e) {
			frm.__task_expanded_state = {};
		}
	},

	save_task_expanded_state(frm) {
		if (frm.__applying_task_expanded_state) return;
		const key = `mks_project_task_expanded_${frm.doc.name || "new"}`;
		localStorage.setItem(key, JSON.stringify(frm.__task_expanded_state || {}));
	},

	destroy_project_task_table(frm) {
		frm.events.close_project_task_inline_editor(frm);
		frm.events.save_task_expanded_state(frm);
		const wrapper = frm.events.get_project_task_wrapper(frm);
		if (wrapper?.length) {
			wrapper.find("[data-role='task-table-body']").off();
			wrapper.find("[data-role='task-table-head']").off();
		}
		frm.__project_task_drag_state = null;
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
			if (filters.assign_to && !(task.assigned_to || []).includes(filters.assign_to)) return false;
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

	compare_project_task_sort_values(a, b, column) {
		const va = a?.[column];
		const vb = b?.[column];
		if (va == null && vb == null) return 0;
		if (va == null) return 1;
		if (vb == null) return -1;

		if (["exp_start_date", "exp_end_date", "custom_actual_start_date", "custom_actual_end_date"].includes(column)) {
			return String(va).localeCompare(String(vb));
		}
		if (column === "assigned_to") {
			const na = (a.assigned_to_names || []).join(", ");
			const nb = (b.assigned_to_names || []).join(", ");
			return String(na).localeCompare(String(nb), undefined, { sensitivity: "base" });
		}
		if (["duration_days", "planned_hours", "actual_duration_days", "actual_hours", "total_costing_amount"].includes(column)) {
			return (Number(va) || 0) - (Number(vb) || 0);
		}
		return String(va).localeCompare(String(vb), undefined, { sensitivity: "base" });
	},

	sort_project_task_siblings(frm, nodeList) {
		const sort = frm.__task_sort;
		if (sort?.column) {
			const dir = sort.direction === "desc" ? -1 : 1;
			nodeList.sort(
				(a, b) => dir * frm.events.compare_project_task_sort_values(a, b, sort.column)
			);
		} else {
			nodeList.sort((a, b) => {
				const idxDiff = (Number(a.idx) || 0) - (Number(b.idx) || 0);
				if (idxDiff) return idxDiff;
				const lftDiff = (Number(a.lft) || 0) - (Number(b.lft) || 0);
				if (lftDiff) return lftDiff;
				return (a.subject || "").localeCompare(b.subject || "");
			});
		}
		nodeList.forEach((node) => {
			if (node.children?.length) frm.events.sort_project_task_siblings(frm, node.children);
		});
	},

	build_project_task_tree(frm, tasks) {
		const filtered = frm.events.filter_project_tasks_for_display(frm, tasks);
		const nodesByName = {};
		filtered.forEach((task) => {
			nodesByName[task.name] = { ...task, children: [] };
		});

		const roots = [];
		filtered.forEach((task) => {
			const node = nodesByName[task.name];
			if (task.parent_task && nodesByName[task.parent_task]) {
				nodesByName[task.parent_task].children.push(node);
			} else {
				roots.push(node);
			}
		});

		frm.events.sort_project_task_siblings(frm, roots);

		frm.__task_hierarchy = {};
		const indexHierarchy = (nodeList, parentTask = null) => {
			nodeList.forEach((node) => {
				const children = node.children || [];
				frm.__task_hierarchy[node.name] = {
					...node,
					parent_task: parentTask,
					children: children.map((child) => ({ ...child })),
				};
				if (children.length) indexHierarchy(children, node.name);
			});
		};
		indexHierarchy(roots);

		return roots;
	},

	collect_visible_task_rows(frm, roots, depth = 0) {
		const rows = [];
		(roots || []).forEach((node) => {
			const hasChildren = Boolean(node.children?.length);
			const expanded = frm.__task_expanded_state[node.name] !== false;
			rows.push({ task: node, depth, hasChildren, expanded });
			if (hasChildren && expanded) {
				rows.push(...frm.events.collect_visible_task_rows(frm, node.children, depth + 1));
			}
		});
		return rows;
	},

	merge_project_task_patch(frm, patch) {
		if (!patch) return;

		const byName = {};
		(frm.__project_tasks_data || []).forEach((task) => {
			byName[task.name] = { ...task };
		});

		const upsert = (task) => {
			if (!task?.name) return;
			byName[task.name] = { ...(byName[task.name] || {}), ...task };
		};

		(patch.tasks || []).forEach(upsert);
		(patch.affected_parents || []).forEach(upsert);
		if (patch.task?.name) upsert(patch.task);

		(patch.removed || []).forEach((name) => {
			delete byName[name];
			frm.__selected_task_names?.delete?.(name);
		});

		const orders =
			patch.sibling_orders?.length > 0
				? patch.sibling_orders
				: patch.sibling_order
					? [patch.sibling_order]
					: [];

		orders.forEach((order) => {
			const idxByName = order?.idx_by_name || {};
			Object.keys(idxByName).forEach((name) => {
				if (byName[name]) byName[name].idx = idxByName[name];
			});
		});

		if (patch.wbs_by_name) {
			Object.keys(patch.wbs_by_name).forEach((name) => {
				if (byName[name] && patch.wbs_by_name[name] != null) {
					byName[name].wbs = patch.wbs_by_name[name];
				}
			});
		}

		if (patch.children_meta) {
			Object.entries(patch.children_meta).forEach(([name, meta]) => {
				if (!byName[name] || !meta) return;
				if ("is_group" in meta) byName[name].is_group = meta.is_group;
				if ("direct_child_count" in meta) {
					byName[name].is_group = meta.direct_child_count > 0 ? 1 : byName[name].is_group;
				}
			});
		}

		frm.__project_tasks_data = Object.values(byName);

		// Update % complete quietly — set_value dirties the Project form and can
		// trigger refresh loops / console spam while tasks are edited inline.
		if (patch.project?.name && frm.doc.name === patch.project.name && patch.project.percent_complete != null) {
			const nextPct = flt(patch.project.percent_complete);
			if (flt(frm.doc.percent_complete) !== nextPct) {
				frm.doc.percent_complete = nextPct;
				frm.refresh_field("percent_complete");
				frm.toolbar?.refresh?.();
			}
		}
	},

	capture_project_task_ui_state(frm) {
		const wrapper = frm.events.get_project_task_wrapper(frm);
		const scrollEl = wrapper?.find(".project-task-table-scroll")[0];
		return {
			scrollTop: scrollEl?.scrollTop || 0,
			selected: new Set(frm.__selected_task_names || []),
		};
	},

	restore_project_task_ui_state(frm, state, options = {}) {
		const wrapper = frm.events.get_project_task_wrapper(frm);
		const scrollEl = wrapper?.find(".project-task-table-scroll")[0];
		if (scrollEl && state?.scrollTop != null) {
			scrollEl.scrollTop = state.scrollTop;
		}

		frm.__selected_task_names = state?.selected || new Set();
		frm.events.sync_task_table_selection(frm);

		if (options.focusTask) {
			const row = wrapper.find(`tr[data-task-name="${CSS.escape(options.focusTask)}"]`)[0];
			if (row) {
				row.scrollIntoView({ block: "nearest", behavior: "smooth" });
				row.classList.add("task-row-focus-highlight");
				setTimeout(() => row.classList.remove("task-row-focus-highlight"), 1800);
			}
		}
	},

	expand_task_ancestor_path(frm, taskName) {
		if (!taskName) return;
		let current = (frm.__project_tasks_data || []).find((task) => task.name === taskName);
		while (current?.parent_task) {
			frm.__task_expanded_state[current.parent_task] = true;
			current = (frm.__project_tasks_data || []).find((task) => task.name === current.parent_task);
		}
		frm.events.save_task_expanded_state(frm);
	},

	refresh_project_task_table(frm, options = {}) {
		const wrapper = frm.events.get_project_task_wrapper(frm);
		if (!wrapper?.length) return;

		const uiState = options.preserveUi === false ? null : frm.events.capture_project_task_ui_state(frm);

		if (options.expandPath) {
			frm.events.expand_task_ancestor_path(frm, options.expandPath);
		}

		const tasks = frm.__project_tasks_data || [];
		const filtered = frm.events.filter_project_tasks_for_display(frm, tasks);
		const emptyState = wrapper.find("[data-role='empty']");
		const tableScroll = wrapper.find(".project-task-table-scroll");

		if (!tasks.length) {
			tableScroll.addClass("d-none");
			emptyState.removeClass("d-none").find("h5").text(__("No Tasks Yet"));
			emptyState.find("p").text(__("Use Add Task to create your first task for this project."));
			wrapper.find("[data-role='task-table-foot']").empty();
			frm.events.update_project_task_filter_count(frm);
			return;
		}

		if (!filtered.length) {
			tableScroll.addClass("d-none");
			emptyState.removeClass("d-none").find("h5").text(__("No Tasks Match Filters"));
			emptyState.find("p").text(
				__("Change the status filter or uncheck Hide Completed to see more tasks.")
			);
			wrapper.find("[data-role='task-table-foot']").empty();
			frm.events.update_project_task_filter_count(frm);
			return;
		}

		emptyState.addClass("d-none");
		tableScroll.removeClass("d-none");

		const roots = frm.events.build_project_task_tree(frm, tasks);
		frm.events.render_project_task_table_header(frm, wrapper);
		frm.events.render_project_task_table_body(frm, wrapper, roots);
		frm.events.render_project_task_table_footer(frm, wrapper, filtered);
		frm.events.bind_project_task_table_events(frm, wrapper);
		frm.events.update_project_task_filter_count(frm);
		frm.events.update_project_task_sort_control(frm);

		if (uiState) {
			frm.events.restore_project_task_ui_state(frm, uiState, options);
		} else if (options.focusTask) {
			frm.events.restore_project_task_ui_state(frm, { scrollTop: 0, selected: frm.__selected_task_names || new Set() }, options);
		}
	},

	apply_project_task_mutation(frm, patch, options = {}) {
		if (patch?.errors?.length) {
			frappe.msgprint({
				title: __("Some tasks could not be updated"),
				message: patch.errors.map((err) => frappe.utils.escape_html(err)).join("<br>"),
				indicator: "orange",
			});
		}
		frm.events.merge_project_task_patch(frm, patch);
		frm.events.refresh_project_task_table(frm, options);
	},

	render_project_task_table_header(frm, wrapper) {
		const columns = frm.events.get_ordered_visible_columns(frm);
		const widths = frm.events.get_project_task_column_widths(frm);
		const sort = frm.__task_sort;
		const esc = frappe.utils.escape_html;

		const cells = columns.map((column) => {
			const width = widths[column.id] || column.minWidth;
			const sortable = column.sortable && column.id !== "select" && column.id !== "move" && column.id !== "actions";
			const sortClass =
				sort?.column === column.id
					? sort.direction === "desc"
						? "sorted-desc"
						: "sorted-asc"
					: "";
			const sortIndicator = sortable
				? `<span class="sort-indicator">${sort?.column === column.id ? (sort.direction === "desc" ? "▼" : "▲") : "↕"}</span>`
				: "";
			const editableHint =
				column.editable && column.id !== "subject"
					? `<span class="column-editable-hint">${__("(editable)")}</span>`
					: "";

			if (column.id === "select") {
				return `
					<th data-column="${esc(column.id)}" style="width:${width}px;min-width:${column.minWidth}px;">
						<input type="checkbox" data-role="select-all-tasks" title="${esc(__("Select All"))}">
					</th>
				`;
			}

			return `
				<th data-column="${esc(column.id)}"
					class="${sortable ? "sortable" : ""} ${sortClass}"
					style="width:${width}px;min-width:${column.minWidth}px;position:relative;"
					${sortable ? `data-sort-column="${esc(column.id)}"` : ""}>
					${column.label}${editableHint}${sortIndicator}
					<span class="column-resize-handle" data-resize-column="${esc(column.id)}"></span>
				</th>
			`;
		});

		wrapper.find("[data-role='task-table-head']").html(`<tr>${cells.join("")}</tr>`);
	},

	render_project_task_table_body(frm, wrapper, roots) {
		const columns = frm.events.get_ordered_visible_columns(frm);
		const rows = frm.events.collect_visible_task_rows(frm, roots);
		const esc = frappe.utils.escape_html;
		const { currency } = frm.events.get_task_meta_options(frm);
		const selected = frm.__selected_task_names || new Set();

		const html = rows
			.map(({ task, depth, hasChildren, expanded }) => {
				const level = Math.min(depth, 6);
				const indent = depth * 18;
				const isSelected = selected.has(task.name);
				const rowClasses = [
					`task-level-${level}`,
					hasChildren ? "parent-task-row" : "",
					isSelected ? "task-row-selected" : "",
				]
					.filter(Boolean)
					.join(" ");

				const cells = columns
					.map((column) => frm.events.render_project_task_cell(frm, column, task, {
						depth,
						indent,
						hasChildren,
						expanded,
						currency,
					}))
					.join("");

				return `
					<tr data-task-name="${esc(task.name)}"
						data-parent-task="${esc(task.parent_task || "")}"
						data-level="${depth}"
						class="${rowClasses}"
						draggable="false">
						${cells}
					</tr>
				`;
			})
			.join("");

		wrapper.find("[data-role='task-table-body']").html(html);
	},

	get_project_task_leaf_totals(frm, filteredTasks) {
		const list = filteredTasks || [];
		const byName = {};
		list.forEach((task) => {
			byName[task.name] = task;
		});
		const parentsWithVisibleChildren = new Set();
		list.forEach((task) => {
			if (task.parent_task && byName[task.parent_task]) {
				parentsWithVisibleChildren.add(task.parent_task);
			}
		});
		const leaves = list.filter((task) => !parentsWithVisibleChildren.has(task.name));

		let planDays = 0;
		let actualDays = 0;
		let planHours = 0;
		let actualHours = 0;
		let cost = 0;
		let planDaysCount = 0;
		let actualDaysCount = 0;

		leaves.forEach((task) => {
			if (task.duration_days != null && task.duration_days !== "") {
				planDays += cint(task.duration_days);
				planDaysCount += 1;
			}
			if (task.actual_duration_days != null && task.actual_duration_days !== "") {
				actualDays += cint(task.actual_duration_days);
				actualDaysCount += 1;
			}
			planHours += flt(task.planned_hours || task.expected_time || 0);
			actualHours += flt(task.actual_hours || 0);
			cost += flt(task.total_costing_amount || 0);
		});

		return {
			leafCount: leaves.length,
			planDays,
			planDaysCount,
			actualDays,
			actualDaysCount,
			planHours,
			actualHours,
			cost,
		};
	},

	render_project_task_table_footer(frm, wrapper, filteredTasks) {
		const foot = wrapper.find("[data-role='task-table-foot']");
		if (!foot.length) return;

		const columns = frm.events.get_ordered_visible_columns(frm);
		const totals = frm.events.get_project_task_leaf_totals(frm, filteredTasks);
		const esc = frappe.utils.escape_html;
		const totalLabelHtml = `
			<strong>${esc(__("Total"))}</strong>
			<span class="text-muted small"> — ${esc(__("{0} leaf tasks", [totals.leafCount]))}</span>
		`;
		let labelPlaced = false;

		const cells = columns.map((column) => {
			if (column.id === "subject") {
				labelPlaced = true;
				return `<td data-column="subject" class="project-task-total-label">${totalLabelHtml}</td>`;
			}
			if (column.id === "duration_days") {
				return `<td data-column="duration_days" class="project-task-total-value">
					<strong>${esc(String(totals.planDays))}</strong>
					<span class="text-muted small">${esc(__("days"))}</span>
				</td>`;
			}
			if (column.id === "actual_duration_days") {
				return `<td data-column="actual_duration_days" class="project-task-total-value">
					<strong>${esc(String(totals.actualDays))}</strong>
					<span class="text-muted small">${esc(__("days"))}</span>
				</td>`;
			}
			if (column.id === "planned_hours") {
				return `<td data-column="planned_hours" class="project-task-total-value">
					<strong>${esc(frappe.mks_task_plain_number(totals.planHours))}</strong>
				</td>`;
			}
			if (column.id === "actual_hours") {
				return `<td data-column="actual_hours" class="project-task-total-value">
					<strong>${esc(frappe.mks_task_plain_number(totals.actualHours))}</strong>
				</td>`;
			}
			if (column.id === "total_costing_amount") {
				return `<td data-column="total_costing_amount" class="project-task-total-value">
					<strong>${esc(frappe.mks_task_plain_number(totals.cost, true))}</strong>
				</td>`;
			}
			return `<td data-column="${esc(column.id)}"></td>`;
		});

		if (!labelPlaced) {
			const idx = columns.findIndex((c) => !["select", "move"].includes(c.id));
			if (idx >= 0) {
				cells[idx] = `<td data-column="${esc(columns[idx].id)}" class="project-task-total-label">${totalLabelHtml}</td>`;
			}
		}

		foot.html(`<tr class="project-task-total-row">${cells.join("")}</tr>`);
	},

	render_project_task_cell(frm, column, task, ctx) {
		const esc = frappe.utils.escape_html;
		const { depth, indent, hasChildren, expanded, currency } = ctx;

		switch (column.id) {
			case "select":
				return `
					<td data-column="select">
						<input type="checkbox" data-role="select-task" data-task-name="${esc(task.name)}"
							${frm.__selected_task_names?.has(task.name) ? "checked" : ""}>
					</td>
				`;
			case "move":
				return `
					<td data-column="move">
						<span class="task-drag-handle" data-role="drag-handle" title="${esc(__("Drag to reorder"))}">⋮⋮</span>
					</td>
				`;
			case "subject": {
				const color = frm.events.get_task_level_color(depth);
				const toggle = hasChildren
					? `<span class="collapse-triangle ${expanded ? "" : "collapsed"}" data-role="toggle-expand" data-task-name="${esc(task.name)}" title="${esc(expanded ? __("Collapse") : __("Expand"))}">▼</span>`
					: `<span class="collapse-triangle" style="visibility:hidden;">▼</span>`;
				return `
					<td data-column="subject" class="task-subject" style="--task-indent:${indent}px;">
						<div class="task-subject-inner">
							${toggle}
							<span class="task-subject-title">
								<a href="#" data-task-link="${esc(task.name)}" style="color:${color};">${esc(task.subject || task.name)}</a>
							</span>
							<span class="task-actions-group">
								<button type="button" class="btn btn-link btn-sm p-0" data-action="add-child" data-task-name="${esc(task.name)}" title="${esc(__("Add Child Task"))}">
									<svg class="icon icon-sm"><use href="#icon-add"></use></svg>
								</button>
								<button type="button" class="btn btn-link btn-sm p-0" data-action="edit-task" data-task-name="${esc(task.name)}" title="${esc(__("Edit"))}">
									<svg class="icon icon-sm"><use href="#icon-edit"></use></svg>
								</button>
								<button type="button" class="btn btn-link btn-sm p-0 text-danger" data-action="delete-task" data-task-name="${esc(task.name)}" title="${esc(__("Delete"))}">
									<svg class="icon icon-sm"><use href="#icon-delete"></use></svg>
								</button>
							</span>
						</div>
					</td>
				`;
			}
			case "wbs":
				return `<td data-column="wbs">${esc(task.wbs || "-")}</td>`;
			case "status":
				return `<td data-column="status" class="editable-cell" data-field="status" data-task-name="${esc(task.name)}">${frm.events.format_task_badge(task.status, frm.events.get_task_status_class(task.status))}</td>`;
			case "priority":
				return `<td data-column="priority" class="editable-cell" data-field="priority" data-task-name="${esc(task.name)}">${frm.events.format_task_badge(task.priority, frm.events.get_task_priority_class(task.priority))}</td>`;
			case "assigned_to":
				return `<td data-column="assigned_to" class="editable-cell" data-field="assigned_to" data-task-name="${esc(task.name)}">${frm.events.format_task_assignees(task)}</td>`;
			case "exp_start_date":
				return `<td data-column="exp_start_date" class="editable-cell" data-field="exp_start_date" data-task-name="${esc(task.name)}">${esc(frm.events.format_task_date(task.exp_start_date))}</td>`;
			case "exp_end_date":
				return `<td data-column="exp_end_date" class="editable-cell" data-field="exp_end_date" data-task-name="${esc(task.name)}">${esc(frm.events.format_task_date(task.exp_end_date))}</td>`;
			case "duration_days": {
				const value = task.duration_days;
				const text = value == null || isNaN(value) ? "-" : `${value} ${__("days")}`;
				return `<td data-column="duration_days">${esc(text)}</td>`;
			}
			case "planned_hours":
				return `<td data-column="planned_hours" class="editable-cell" data-field="planned_hours" data-task-name="${esc(task.name)}">${esc(frappe.mks_task_plain_number(task.planned_hours))}</td>`;
			case "custom_actual_start_date":
				return `<td data-column="custom_actual_start_date" class="editable-cell" data-field="custom_actual_start_date" data-task-name="${esc(task.name)}">${frm.events.format_task_date_pill(task.custom_actual_start_date, frm.events.get_task_actual_date_class(task.custom_actual_start_date, task, "custom_actual_start_date"))}</td>`;
			case "custom_actual_end_date":
				return `<td data-column="custom_actual_end_date" class="editable-cell" data-field="custom_actual_end_date" data-task-name="${esc(task.name)}">${frm.events.format_task_date_pill(task.custom_actual_end_date, frm.events.get_task_actual_date_class(task.custom_actual_end_date, task, "custom_actual_end_date"))}</td>`;
			case "actual_duration_days": {
				const value = task.actual_duration_days;
				const text = value == null || isNaN(value) ? "-" : `${value} ${__("days")}`;
				return `<td data-column="actual_duration_days">${esc(text)}</td>`;
			}
			case "actual_hours":
				return `<td data-column="actual_hours">${esc(frappe.mks_task_plain_number(task.actual_hours))}</td>`;
			case "total_costing_amount":
				return `<td data-column="total_costing_amount">${esc(frappe.mks_task_plain_number(task.total_costing_amount, true))}</td>`;
			case "actions":
				return `
					<td data-column="actions">
						<span class="task-actions-group">
							<button type="button" class="btn btn-link btn-sm p-0" data-action="add-child" data-task-name="${esc(task.name)}" title="${esc(__("Add Child Task"))}">
								<svg class="icon icon-sm"><use href="#icon-add"></use></svg>
							</button>
							<button type="button" class="btn btn-link btn-sm p-0" data-action="edit-task" data-task-name="${esc(task.name)}" title="${esc(__("Edit"))}">
								<svg class="icon icon-sm"><use href="#icon-edit"></use></svg>
							</button>
							<button type="button" class="btn btn-link btn-sm p-0 text-danger" data-action="delete-task" data-task-name="${esc(task.name)}" title="${esc(__("Delete"))}">
								<svg class="icon icon-sm"><use href="#icon-delete"></use></svg>
							</button>
						</span>
					</td>
				`;
			default:
				return `<td data-column="${esc(column.id)}"></td>`;
		}
	},

	bind_project_task_table_events(frm, wrapper) {
		const tbody = wrapper.find("[data-role='task-table-body']");
		const thead = wrapper.find("[data-role='task-table-head']");

		tbody.off("click.tasktab change.tasktab");
		thead.off("click.tasktab change.tasktab mousedown.tasktab");

		tbody.on("click.tasktab", "[data-role='toggle-expand']", function (e) {
			e.preventDefault();
			e.stopPropagation();
			const taskName = $(this).data("task-name");
			const current = frm.__task_expanded_state[taskName];
			frm.__task_expanded_state[taskName] = current === false;
			frm.events.save_task_expanded_state(frm);
			frm.events.refresh_project_task_table(frm);
		});

		tbody.on("click.tasktab", "[data-task-link]", function (e) {
			e.preventDefault();
			frappe.set_route("Form", "Task", $(this).data("task-link"));
		});

		tbody.on("click.tasktab", "[data-action]", function (e) {
			e.preventDefault();
			e.stopPropagation();
			const taskName = $(this).data("task-name");
			const task = (frm.__project_tasks_data || []).find((row) => row.name === taskName);
			if (!task) return;
			const action = $(this).data("action");
			if (action === "add-child") frm.events.open_project_task_dialog(frm, null, task.name);
			if (action === "edit-task") frm.events.open_project_task_dialog(frm, task);
			if (action === "delete-task") frm.events.delete_single_task(frm, task);
			if (action === "remove-assignee") {
				const user = $(this).attr("data-user") || $(this).data("user");
				const next = (task.assigned_to || []).filter((item) => item !== user);
				frm.events.quick_update_task(frm, task.name, { assigned_to: next });
			}
		});

		tbody.on("change.tasktab", "[data-role='select-task']", function () {
			const taskName = $(this).data("task-name");
			if ($(this).prop("checked")) frm.__selected_task_names.add(taskName);
			else frm.__selected_task_names.delete(taskName);
			frm.events.sync_task_table_selection(frm);
		});

		thead.on("change.tasktab", "[data-role='select-all-tasks']", function () {
			const checked = $(this).prop("checked");
			const visibleNames = tbody.find("[data-role='select-task']").map((_, el) => $(el).data("task-name")).get();
			if (checked) visibleNames.forEach((name) => frm.__selected_task_names.add(name));
			else visibleNames.forEach((name) => frm.__selected_task_names.delete(name));
			tbody.find("[data-role='select-task']").prop("checked", checked);
			frm.events.sync_task_table_selection(frm);
		});

		thead.on("click.tasktab", "[data-sort-column]", function (e) {
			if ($(e.target).closest(".column-resize-handle").length) return;
			const column = $(this).data("sort-column");
			if (!column) return;
			if (frm.__task_sort?.column === column) {
				frm.__task_sort.direction = frm.__task_sort.direction === "asc" ? "desc" : "asc";
			} else {
				frm.__task_sort = { column, direction: "asc" };
			}
			frm.events.refresh_project_task_table(frm);
		});

		frm.events.bind_project_task_column_resize(frm, wrapper);
		frm.events.bind_project_task_inline_edit(frm, wrapper);
		frm.events.bind_project_task_drag_reorder(frm, wrapper);
	},

	bind_project_task_column_resize(frm, wrapper) {
		const thead = wrapper.find("[data-role='task-table-head']");
		thead.off("mousedown.taskresize");

		thead.on("mousedown.taskresize", ".column-resize-handle", function (e) {
			e.preventDefault();
			e.stopPropagation();
			const columnId = $(this).data("resize-column");
			const th = $(this).closest("th")[0];
			if (!th || !columnId) return;

			const startX = e.clientX;
			const startWidth = th.offsetWidth;
			const widths = frm.events.get_project_task_column_widths(frm);
			document.body.classList.add("project-task-column-resizing");

			const onMove = (moveEvent) => {
				const delta = moveEvent.clientX - startX;
				const dir = wrapper.hasClass("project-task-tab-wrapper--rtl") ? -1 : 1;
				const nextWidth = Math.max(40, startWidth + delta * dir);
				widths[columnId] = nextWidth;
				th.style.width = `${nextWidth}px`;
				th.style.minWidth = `${nextWidth}px`;
				wrapper.find(`[data-column="${columnId}"]`).css({ width: nextWidth, minWidth: nextWidth });
			};

			const onUp = () => {
				document.body.classList.remove("project-task-column-resizing");
				document.removeEventListener("mousemove", onMove);
				document.removeEventListener("mouseup", onUp);
				frm.events.save_project_task_column_widths(frm, widths);
			};

			document.addEventListener("mousemove", onMove);
			document.addEventListener("mouseup", onUp);
		});
	},

	close_project_task_inline_editor(frm) {
		if (frm.__project_task_inline_editor?.outsideHandler) {
			document.removeEventListener("mousedown", frm.__project_task_inline_editor.outsideHandler, true);
		}
		if (frm.__project_task_inline_editor?.$popover?.length) {
			frm.__project_task_inline_editor.$popover.remove();
		}
		if (frm.__project_task_inline_editor?.control?.destroy) {
			try {
				frm.__project_task_inline_editor.control.destroy();
			} catch (e) {
				// ignore
			}
		}
		frm.__project_task_inline_editor = null;
	},

	bind_project_task_inline_edit(frm, wrapper) {
		const tbody = wrapper.find("[data-role='task-table-body']");
		tbody.off("click.taskedit");

		tbody.on("click.taskedit", ".editable-cell", function (e) {
			e.stopPropagation();
			if ($(e.target).closest("[data-action='remove-assignee']").length) {
				return;
			}
			const $cell = $(this);
			const field = $cell.data("field");
			const taskName = $cell.data("task-name");
			const task = (frm.__project_tasks_data || []).find((row) => row.name === taskName);
			if (!task || !field) return;

			if (frm.__project_task_inline_editor?.taskName === taskName && frm.__project_task_inline_editor?.field === field) {
				return;
			}
			frm.events.close_project_task_inline_editor(frm);

			if (["exp_start_date", "exp_end_date", "custom_actual_start_date", "custom_actual_end_date"].includes(field)) {
				frm.events.open_project_task_date_editor(frm, $cell, task, field);
				return;
			}
			if (field === "status" || field === "priority") {
				frm.events.open_project_task_select_editor(frm, $cell, task, field);
				return;
			}
			if (field === "assigned_to") {
				frm.events.open_project_task_assign_editor(frm, $cell, task);
				return;
			}
			if (field === "planned_hours") {
				frm.events.open_project_task_number_editor(frm, $cell, task, field);
			}
		});
	},

	open_project_task_select_editor(frm, $cell, task, field) {
		const { status_options, priority_options } = frm.events.get_task_meta_options(frm);
		const options = field === "status" ? status_options : priority_options;
		const currentValue = task[field] || "";
		const hasChildren = (frm.__project_tasks_data || []).some((row) => row.parent_task === task.name);

		// Native <select> + blur races with table refresh and often closes before a change sticks.
		const $popover = $(`
			<div class="inline-select-control shadow-sm border rounded bg-white p-2" style="position:absolute;z-index:40;min-width:160px;"></div>
		`);
		$cell.css("position", "relative").append($popover);

		const label = $(`<div class="text-muted small mb-1"></div>`).text(
			field === "status" ? __("Set Status") : __("Set Priority")
		);
		$popover.append(label);

		if (field === "status" && hasChildren) {
			$popover.append(
				$(`<div class="text-muted small mb-2"></div>`).text(
					__("Parent status follows children. Completing will update child tasks.")
				)
			);
		}

		const list = $('<div class="inline-select-options d-flex flex-column" style="gap:4px;"></div>');
		options.forEach((opt) => {
			const btn = $(
				`<button type="button" class="btn btn-xs btn-default text-left inline-select-option ${
					opt === currentValue ? "btn-primary" : ""
				}"></button>`
			).text(__(opt));
			btn.on("mousedown", (e) => {
				e.preventDefault();
				e.stopPropagation();
			});
			btn.on("click", (e) => {
				e.preventDefault();
				e.stopPropagation();
				const editor = frm.__project_task_inline_editor;
				if (editor?.outsideHandler) {
					document.removeEventListener("mousedown", editor.outsideHandler, true);
				}
				frm.__project_task_inline_editor = null;
				if (editor?.$popover?.length) editor.$popover.remove();

				if (opt === currentValue) {
					frm.events.refresh_project_task_table(frm);
					return;
				}
				const updates = { [field]: opt || null };
				if (field === "status" && opt === "Completed") {
					// quick_update_task handles parent acknowledgement; do NOT refresh here
					// or the table rebuild cancels/overwrites the pending Completed update.
					frm.events.quick_update_task(frm, task.name, updates);
					return;
				}
				if (field === "status" && hasChildren) {
					frappe.confirm(
						__(
							"This is a parent task. Its status is normally calculated from children. Update this parent to {0} anyway?"
						).replace("{0}", __(opt)),
						() => frm.events.quick_update_task(frm, task.name, updates),
						() => frm.events.refresh_project_task_table(frm)
					);
					return;
				}
				frm.events.quick_update_task(frm, task.name, updates);
			});
			list.append(btn);
		});
		$popover.append(list);

		$popover.on("mousedown", (e) => e.stopPropagation());

		const outsideHandler = (event) => {
			if ($popover[0]?.contains(event.target)) return;
			// Closing without a choice — discard editor only; do not rebuild the
			// whole table (rebuild races with in-flight Completed updates).
			frm.events.close_project_task_inline_editor(frm);
		};
		setTimeout(() => document.addEventListener("mousedown", outsideHandler, true), 0);

		frm.__project_task_inline_editor = {
			taskName: task.name,
			field,
			$popover,
			outsideHandler,
		};
	},

	open_project_task_number_editor(frm, $cell, task, field) {
		const currentValue = task[field];
		const input = $(`<input type="number" class="form-control form-control-sm" step="0.01">`);
		input.val(currentValue == null ? "" : currentValue);
		$cell.empty().append(input);
		input.focus();
		input.select();

		const commit = () => {
			const raw = input.val();
			const value = raw === "" ? null : frappe.utils.flt(raw);
			input.off();
			if (value === currentValue) {
				frm.events.refresh_project_task_table(frm);
				return;
			}
			frm.events.quick_update_task(frm, task.name, { [field]: value });
		};

		input.on("keydown", (e) => {
			if (e.key === "Enter") commit();
			if (e.key === "Escape") frm.events.refresh_project_task_table(frm);
		});
		input.on("blur", () => setTimeout(commit, 120));
	},

	open_project_task_assign_editor(frm, $cell, task) {
		const currentValue = [...(task.assigned_to || [])];
		const $popover = $(`
			<div class="inline-assign-control shadow-sm border rounded bg-white p-2" style="position:absolute;z-index:30;min-width:240px;"></div>
		`);
		$cell.css("position", "relative").append($popover);

		const controlWrapper = $('<div class="control-input-wrapper"></div>').appendTo($popover);
		const actions = $(`
			<div class="inline-date-actions">
				<button type="button" class="btn btn-default btn-xs" data-role="clear-assign">${__("Clear")}</button>
				<button type="button" class="btn btn-primary btn-xs" data-role="save-assign">${__("Save")}</button>
			</div>
		`).appendTo($popover);

		const control = frappe.ui.form.make_control({
			df: {
				fieldtype: "MultiSelectPills",
				fieldname: "assign_to",
				options: "User",
				label: __("Assign To"),
				get_data: (txt) => frappe.db.get_link_options("User", txt, { enabled: 1 }),
			},
			parent: controlWrapper[0],
			render_input: true,
		});
		control.set_value(currentValue);
		setTimeout(() => control.$input?.focus?.(), 50);

		const sameAssignees = (left, right) => {
			const a = [...(left || [])].map(String).sort();
			const b = [...(right || [])].map(String).sort();
			return a.length === b.length && a.every((value, idx) => value === b[idx]);
		};

		const closeWithoutSave = () => frm.events.refresh_project_task_table(frm);
		const save = (value) => {
			const next = Array.isArray(value) ? value.filter(Boolean) : [];
			if (sameAssignees(next, currentValue)) {
				closeWithoutSave();
				return;
			}
			frm.events.close_project_task_inline_editor(frm);
			frm.events.quick_update_task(frm, task.name, { assigned_to: next });
		};

		actions.find("[data-role='clear-assign']").on("click", (e) => {
			e.preventDefault();
			e.stopPropagation();
			save([]);
		});
		actions.find("[data-role='save-assign']").on("click", (e) => {
			e.preventDefault();
			e.stopPropagation();
			save(control.get_value() || []);
		});

		const outsideHandler = (event) => {
			if ($popover[0]?.contains(event.target)) return;
			if ($(event.target).closest(".awesomplete, .frappe-control").length) return;
			closeWithoutSave();
		};
		setTimeout(() => document.addEventListener("mousedown", outsideHandler, true), 0);

		frm.__project_task_inline_editor = {
			taskName: task.name,
			field: "assigned_to",
			$popover,
			control,
			outsideHandler,
		};
	},

	is_project_task_date_picker_target(target) {
		return Boolean(
			$(target).closest(
				[
					".datepicker",
					".datepicker--cell",
					".datepicker--nav",
					".datepicker--nav-action",
					".datepicker--nav-title",
					".datepicker--time",
					".datepicker--pointer",
					".datepicker-container",
					".date-picker",
					".dt-widget",
					".flatpickr-calendar",
				].join(", ")
			).length
		);
	},

	read_project_task_date_control_value(control) {
		return frappe.mks_read_task_date_control(control);
	},

	open_project_task_date_editor(frm, $cell, task, field) {
		const currentValue = frappe.mks_normalize_task_date(task[field] || null);
		const $popover = $(`
			<div class="inline-date-control shadow-sm border rounded bg-white p-2" style="position:absolute;z-index:60;min-width:180px;"></div>
		`);
		$cell.css("position", "relative").append($popover);

		const controlWrapper = $('<div class="control-input-wrapper"></div>').appendTo($popover);
		const actions = $(`
			<div class="inline-date-actions">
				<button type="button" class="btn btn-default btn-xs" data-role="clear-date">${__("Clear")}</button>
				<button type="button" class="btn btn-primary btn-xs" data-role="save-date">${__("Save")}</button>
			</div>
		`).appendTo($popover);

		const control = frappe.ui.form.make_control({
			df: {
				fieldtype: "Date",
				fieldname: `mks_inline_${field}`,
				label: __("Date"),
			},
			parent: controlWrapper[0],
			render_input: true,
		});
		control.refresh();

		let ready = false;
		let saving = false;

		const commit = (rawValue, { force = false, closeIfUnchanged = true } = {}) => {
			if (saving || !ready) return;
			const value = frappe.mks_normalize_task_date(rawValue);
			if (!force && value === currentValue) {
				if (closeIfUnchanged) {
					frm.events.close_project_task_inline_editor(frm);
				}
				return;
			}
			saving = true;
			frm.events.close_project_task_inline_editor(frm);
			const updates = { [field]: value || null };
			if (["exp_start_date", "exp_end_date"].includes(field)) {
				const nextStart = field === "exp_start_date" ? updates.exp_start_date : task.exp_start_date;
				const nextEnd = field === "exp_end_date" ? updates.exp_end_date : task.exp_end_date;
				if (nextStart && nextEnd && nextStart > nextEnd) {
					if (field === "exp_start_date") updates.exp_end_date = nextStart;
					else updates.exp_start_date = nextEnd;
				}
			}
			frm.events.quick_update_task(frm, task.name, updates);
		};

		actions.find("[data-role='clear-date']").on("mousedown click", (e) => {
			e.preventDefault();
			e.stopPropagation();
			commit(null, { force: true });
		});
		actions.find("[data-role='save-date']").on("mousedown click", (e) => {
			e.preventDefault();
			e.stopPropagation();
			commit(frappe.mks_read_task_date_control(control));
		});

		const outsideHandler = (event) => {
			if (!ready || saving) return;
			if ($popover[0]?.contains(event.target)) return;
			// Datepicker is rendered outside the popover — ignore those clicks.
			if (frm.events.is_project_task_date_picker_target(event.target)) return;
			if ($(event.target).closest(".frappe-control, .awesomplete").length) return;
			const value = frappe.mks_read_task_date_control(control);
			if (value !== currentValue) {
				commit(value);
			} else {
				frm.events.close_project_task_inline_editor(frm);
			}
		};

		frm.__project_task_inline_editor = {
			taskName: task.name,
			field,
			$popover,
			control,
			outsideHandler,
		};

		// Set initial value, then only start listening — otherwise set_value's
		// change event closes the editor before the user can pick a date.
		control.set_value(currentValue || "");
		setTimeout(() => {
			ready = true;
			control.$input?.off?.(".mksDateInline");
			control.$input?.on?.("change.mksDateInline", () => {
				const value = frappe.mks_read_task_date_control(control);
				if (value && value !== currentValue) {
					commit(value, { closeIfUnchanged: false });
				}
			});
			document.addEventListener("mousedown", outsideHandler, true);
			control.$input?.focus?.();
			control.$input?.trigger?.("click");
		}, 80);
	},

	can_reorder_project_tasks(frm) {
		const filters = frm.events.get_project_task_filters(frm);
		if (filters.hide_completed || filters.status || filters.assign_to) {
			return {
				ok: false,
				message: __("Clear filters before reordering tasks."),
			};
		}
		if (frm.__task_sort) {
			return {
				ok: false,
				message: __("Clear column sorting before dragging tasks to change WBS order."),
			};
		}
		return { ok: true };
	},

	bind_project_task_drag_reorder(frm, wrapper) {
		const tbody = wrapper.find("[data-role='task-table-body']");
		tbody.off("dragstart.taskdrag dragover.taskdrag dragleave.taskdrag drop.taskdrag dragend.taskdrag mousedown.taskdrag");

		let dragTaskName = null;
		let dragParentTask = "";

		tbody.on("mousedown.taskdrag", "[data-role='drag-handle']", function () {
			const row = $(this).closest("tr[data-task-name]");
			row.attr("draggable", "true");
		});

		tbody.on("dragstart.taskdrag", "tr[data-task-name]", function (e) {
			const check = frm.events.can_reorder_project_tasks(frm);
			if (!check.ok) {
				e.preventDefault();
				frappe.show_alert({ message: check.message, indicator: "orange" });
				return;
			}
			dragTaskName = $(this).data("task-name");
			dragParentTask = $(this).data("parent-task") || "";
			frm.__project_task_drag_previous_tasks = (frm.__project_tasks_data || []).map((task) => ({ ...task }));
			$(this).addClass("dragging");
			if (e.originalEvent?.dataTransfer) {
				e.originalEvent.dataTransfer.effectAllowed = "move";
				e.originalEvent.dataTransfer.setData("text/plain", dragTaskName);
			}
		});

		tbody.on("dragover.taskdrag", "tr[data-task-name]", function (e) {
			e.preventDefault();
			const targetName = $(this).data("task-name");
			const targetParent = $(this).data("parent-task") || "";
			if (!dragTaskName || targetName === dragTaskName) return;
			if (targetParent !== dragParentTask) return;

			tbody.find("tr.drag-over-top, tr.drag-over-bottom").removeClass("drag-over-top drag-over-bottom");
			const rect = this.getBoundingClientRect();
			const before = e.originalEvent.clientY < rect.top + rect.height / 2;
			$(this).addClass(before ? "drag-over-top" : "drag-over-bottom");
		});

		tbody.on("dragleave.taskdrag", "tr[data-task-name]", function () {
			$(this).removeClass("drag-over-top drag-over-bottom");
		});

		tbody.on("drop.taskdrag", "tr[data-task-name]", function (e) {
			e.preventDefault();
			const targetName = $(this).data("task-name");
			const targetParent = $(this).data("parent-task") || "";
			tbody.find("tr.drag-over-top, tr.drag-over-bottom, tr.dragging").removeClass("drag-over-top drag-over-bottom dragging");

			if (!dragTaskName || targetName === dragTaskName || targetParent !== dragParentTask) {
				if (targetParent !== dragParentTask) {
					frappe.msgprint({
						title: __("Invalid Move"),
						message: __("Tasks can only be dragged within the same parent group."),
						indicator: "orange",
					});
				}
				return;
			}

			const rect = this.getBoundingClientRect();
			const insertBefore = e.originalEvent.clientY < rect.top + rect.height / 2;
			const siblingRows = tbody
				.find(`tr[data-parent-task="${CSS.escape(dragParentTask)}"]`)
				.map((_, el) => $(el).data("task-name"))
				.get();
			const filteredRows = siblingRows.filter((name) => name !== dragTaskName);
			const targetIndex = filteredRows.indexOf(targetName);
			if (targetIndex < 0) return;
			const insertIndex = insertBefore ? targetIndex : targetIndex + 1;
			filteredRows.splice(insertIndex, 0, dragTaskName);

			const siblingSet = new Set(
				(frm.__project_tasks_data || [])
					.filter((task) => (task.parent_task || "") === dragParentTask)
					.map((task) => task.name)
			);
			if (filteredRows.length !== siblingSet.size || filteredRows.some((name) => !siblingSet.has(name))) {
				frappe.msgprint({
					title: __("Invalid Move"),
					message: __("Tasks can only be dragged within the same parent group."),
					indicator: "orange",
				});
				return;
			}

			frm.events.apply_project_task_sibling_order(frm, dragParentTask, filteredRows);
			frm.events.refresh_project_task_table(frm);
			frm.events.reorder_project_task_siblings(frm, dragParentTask, filteredRows, frm.__project_task_drag_previous_tasks);
		});

		tbody.on("dragend.taskdrag", "tr[data-task-name]", function () {
			$(this).removeClass("dragging").attr("draggable", "false");
			tbody.find("tr.drag-over-top, tr.drag-over-bottom").removeClass("drag-over-top drag-over-bottom");
			dragTaskName = null;
			dragParentTask = "";
		});
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

	sync_task_table_selection(frm) {
		const wrapper = frm.events.get_project_task_wrapper(frm);
		if (!wrapper?.length) return;
		const selectedCount = frm.__selected_task_names?.size || 0;
		wrapper.find("[data-role='delete-selected']").prop("disabled", selectedCount === 0);
		wrapper.find("[data-role='select-task']").each(function () {
			const name = $(this).data("task-name");
			$(this).prop("checked", frm.__selected_task_names.has(name));
			$(this).closest("tr").toggleClass("task-row-selected", frm.__selected_task_names.has(name));
		});
		const visibleCount = wrapper.find("[data-role='select-task']").length;
		const allChecked = visibleCount > 0 && selectedCount >= visibleCount &&
			wrapper.find("[data-role='select-task']:checked").length === visibleCount;
		wrapper.find("[data-role='select-all-tasks']").prop("checked", allChecked);
	},

	clear_project_task_sort(frm) {
		frm.__task_sort = null;
		frm.events.refresh_project_task_table(frm);
		frappe.show_alert({ message: __("WBS order restored"), indicator: "blue" }, 2);
	},

	update_project_task_sort_control(frm) {
		const wrapper = frm.events.get_project_task_wrapper(frm);
		if (!wrapper?.length) return;
		wrapper.find("[data-role='clear-sort']").toggleClass("d-none", !frm.__task_sort);
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

	format_task_number(value, df) {
		if (value && value.doc) {
			df = arguments[2];
			value = arguments[1];
		}
		const as_currency = Boolean(df && df.fieldtype === "Currency");
		return frappe.mks_task_plain_number(value, as_currency);
	},

	format_task_badge(value, cls) {
		const text = frappe.utils.escape_html(value ? __(value) : "-");
		return `<span class="task-badge ${cls}">${text}</span>`;
	},

	format_task_assignees(task) {
		const esc = frappe.utils.escape_html;
		const users = task.assigned_to || [];
		const names = task.assigned_to_names || [];
		if (!users.length) {
			return `<span class="task-assign-empty">${esc(__("Unassigned"))}</span>`;
		}
		return `<span class="task-assign-list">${users
			.map((user, idx) => {
				const label = esc(names[idx] || frappe.user_info?.(user)?.fullname || user);
				return `<span class="task-assign-pill" title="${esc(user)}">
					${label}
					<button type="button" class="task-assign-remove" data-action="remove-assignee" data-task-name="${esc(task.name)}" data-user="${esc(user)}" title="${esc(__("Remove"))}">×</button>
				</span>`;
			})
			.join("")}</span>`;
	},

	format_task_date_pill(value, cls) {
		const text = frappe.utils.escape_html(value ? frappe.datetime.str_to_user(value) : "-");
		return `<span class="task-date-pill ${cls}">${text}</span>`;
	},

	normalize_project_task_date_value(value) {
		return frappe.mks_normalize_task_date(value);
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
		const storageKey = "mks_project_task_columns_v3";

		try {
			const saved = JSON.parse(localStorage.getItem(storageKey) || "[]");
			const byId = {};
			saved.forEach((item) => {
				byId[item.id] = item;
			});
			return defaults.map((item) => {
				const saved = byId[item.id] || {};
				let order = saved.order ?? item.order;
				if (!byId[item.id] && item.id === "assigned_to") {
					order = (byId.priority?.order || item.order) + 0.5;
				}
				return {
					...item,
					...saved,
					order,
					visible: columns.find((c) => c.id === item.id)?.locked
						? true
						: byId[item.id]
							? byId[item.id].visible !== false
							: item.visible,
				};
			});
		} catch (e) {
			return defaults;
		}
	},

	save_project_task_column_preferences(preferences) {
		localStorage.setItem("mks_project_task_columns_v3", JSON.stringify(preferences));
	},

	reset_project_task_column_preferences() {
		localStorage.removeItem("mks_project_task_columns_v3");
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
				frm.events.refresh_project_task_table(frm);
			},
		});

		dialog.add_custom_action(__("Reset to Default"), () => {
			frm.events.reset_project_task_column_preferences();
			dialog.hide();
			frm.events.refresh_project_task_table(frm);
			frappe.show_alert({ message: __("Column layout reset"), indicator: "green" });
		}, "btn-default");

		dialog.show();
	},

	expand_all_tasks(frm) {
		Object.values(frm.__task_hierarchy || {}).forEach((task) => {
			if ((task.children || []).length) frm.__task_expanded_state[task.name] = true;
		});
		frm.events.save_task_expanded_state(frm);
		frm.events.refresh_project_task_table(frm);
		frappe.show_alert({ message: __("All tasks expanded"), indicator: "blue" }, 2);
	},

	collapse_all_tasks(frm) {
		Object.values(frm.__task_hierarchy || {}).forEach((task) => {
			if ((task.children || []).length) frm.__task_expanded_state[task.name] = false;
		});
		frm.events.save_task_expanded_state(frm);
		frm.events.refresh_project_task_table(frm);
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

		// Don't wipe an open inline editor with a concurrent reload.
		if (frm.__project_task_inline_editor) {
			return;
		}

		frm.events.close_project_task_inline_editor(frm);
		frm.events.save_task_expanded_state(frm);

		const loadToken = (frm.__project_task_load_token = (frm.__project_task_load_token || 0) + 1);

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
				if (loadToken !== frm.__project_task_load_token) return;
				loadingState.addClass("d-none");

				if (!r?.message) {
					emptyState.removeClass("d-none");
					return;
				}

				const { tasks = [], currency, status_options = [], priority_options = [] } = r.message;
				frm.__project_task_meta = { currency, status_options, priority_options };

				if (!tasks.length) {
					frm.__project_tasks_data = [];
					emptyState.removeClass("d-none");
					wrapper.find(".project-task-table-scroll").addClass("d-none");
					return;
				}

				frm.__project_tasks_data = tasks;
				frm.events.update_project_task_filter_controls(frm, wrapper);
				frm.events.refresh_project_task_table(frm);
			},
			error: () => {
				if (loadToken !== frm.__project_task_load_token) return;
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
		const seen = new Set();
		const walk = (node, level = 1) => {
			(node.children || []).forEach((child) => {
				if (!child?.name || seen.has(child.name)) return;
				seen.add(child.name);
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

		// Fallback: hierarchy can miss children when filters hide rows.
		if (!children.length && (frm.__project_tasks_data || []).some((row) => row.parent_task === taskName)) {
			const walkFlat = (parent, level) => {
				(frm.__project_tasks_data || [])
					.filter((row) => row.parent_task === parent)
					.forEach((child) => {
						if (!child?.name || seen.has(child.name)) return;
						seen.add(child.name);
						children.push({
							name: child.name,
							subject: child.subject || child.name,
							status: child.status || "",
							level,
						});
						walkFlat(child.name, level + 1);
					});
			};
			walkFlat(taskName, 1);
		}
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
		// Leaf tasks: mark acknowledged so quick_update_task does not re-enter confirm forever.
		if (!children.length) {
			onConfirm({ ...updates, completion_acknowledged: 1 });
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
		if (
			updates.status === "Completed" &&
			!updates.completion_acknowledged &&
			!options.skip_completion_confirm
		) {
			frm.events.confirm_parent_task_completion(frm, taskName, updates, (acknowledgedUpdates) => {
				frm.events.quick_update_task(frm, taskName, acknowledgedUpdates, {
					...options,
					skip_completion_confirm: true,
				});
			});
			return;
		}

		frappe.call({
			method: "milestoneksa.api.project_tasks.update_project_task",
			args: { task_name: taskName, updates },
			freeze: true,
			freeze_message: __("Updating task..."),
			callback: (r) => {
				if (r?.exc) {
					frm.events.load_project_tasks(frm);
					return;
				}
				frappe.show_alert({ message: __("Task updated"), indicator: "green" });
				if (options.reload === false) return;
				if (r?.message) {
					frm.events.apply_project_task_mutation(frm, r.message);
				} else {
					frm.events.load_project_tasks(frm);
				}
			},
			error: () => {
				frm.events.load_project_tasks(frm);
			},
		});
	},

	reorder_project_task_siblings(frm, parentTask, orderedNames, previousTasks = null) {
		if (frm.__project_task_reorder_pending) return;

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
					if (previousTasks) frm.__project_tasks_data = previousTasks;
					frm.events.refresh_project_task_table(frm);
					return;
				}
				frappe.show_alert({
					message: __("Task order saved"),
					indicator: "green",
				});
				if (r?.message) {
					frm.events.apply_project_task_mutation(frm, r.message);
				}
			},
			error: () => {
				frm.__project_task_reorder_pending = false;
				frappe.msgprint({
					title: __("Unable to Reorder"),
					message: __("Tasks can only be dragged within the same parent group."),
					indicator: "orange",
				});
				if (previousTasks) frm.__project_tasks_data = previousTasks;
				frm.events.refresh_project_task_table(frm);
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
				{
					fieldname: "assign_to",
					label: __("Assign To"),
					fieldtype: "MultiSelectPills",
					get_data: (txt) => frappe.db.get_link_options("User", txt, { enabled: 1 }),
				},
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
				if (typeof values.assign_to === "string") {
					values.assign_to = values.assign_to
						.split(/[\n,]/)
						.map((item) => item.trim())
						.filter(Boolean);
				}
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
				assign_to: task.assigned_to || [],
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
			callback: (r) => {
				dialog.hide();
				frappe.show_alert({ message: __("Task created"), indicator: "green" });
				const patch = r?.message;
				const taskName = patch?.task?.name || patch?.tasks?.[0]?.name;
				if (patch) {
					frm.events.apply_project_task_mutation(frm, patch, {
						expandPath: taskName,
						focusTask: taskName,
					});
				} else {
					frm.events.load_project_tasks(frm);
				}
			},
			error: () => {
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
			callback: (r) => {
				dialog.hide();
				frappe.show_alert({ message: __("Task updated"), indicator: "green" });
				if (r?.message) {
					frm.events.apply_project_task_mutation(frm, r.message, { focusTask: taskName });
				} else {
					frm.events.load_project_tasks(frm);
				}
			},
			error: () => {
				frm.events.load_project_tasks(frm);
			},
		});
	},

	delete_selected_tasks(frm) {
		const selected = Array.from(frm.__selected_task_names || []);

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
						const patch = r?.message;
						const deletedCount = patch?.deleted_count ?? selected.length;
						frappe.show_alert({
							message: __("{0} selected task(s) deleted successfully", [deletedCount]),
							indicator: "green",
						});
						if (patch) {
							frm.events.apply_project_task_mutation(frm, patch);
						} else {
							frm.events.load_project_tasks(frm);
						}
					},
					error: () => {
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
						const patch = r?.message;
						frappe.show_alert({
							message: __("Deleted {0} task(s)", [patch?.deleted_count ?? 1]),
							indicator: "green",
						});
						if (patch) {
							frm.events.apply_project_task_mutation(frm, patch);
						} else {
							frm.events.load_project_tasks(frm);
						}
					},
					error: () => {
						frm.events.load_project_tasks(frm);
					},
				});
			}
		);
	},

	get_project_task_filter_key(frm) {
		return `mks_project_task_filters_${frm.doc.name || "new"}`;
	},

	get_project_task_filters(frm) {
		if (frm.__project_task_filters) return frm.__project_task_filters;
		const defaults = { hide_completed: false, status: "", assign_to: "" };
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
		frm.events.refresh_project_task_table(frm);
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

		const assignSelect = wrapper.find("[data-role='assign-filter']");
		if (assignSelect.length) {
			const currentAssign = filters.assign_to || "";
			const assignees = {};
			(frm.__project_tasks_data || []).forEach((task) => {
				(task.assigned_to || []).forEach((user, idx) => {
					if (!user) return;
					assignees[user] = (task.assigned_to_names || [])[idx] || user;
				});
			});
			assignSelect.empty().append($("<option>").val("").text(__("All Assignees")));
			Object.entries(assignees)
				.sort((a, b) => String(a[1]).localeCompare(String(b[1]), undefined, { sensitivity: "base" }))
				.forEach(([user, label]) => {
					assignSelect.append($("<option>").val(user).text(label));
				});
			if (currentAssign && !assignees[currentAssign]) {
				assignSelect.append($("<option>").val(currentAssign).text(currentAssign));
			}
			assignSelect.val(currentAssign);
		}
	},

	update_project_task_filter_count(frm) {
		const wrapper = frm.events.get_project_task_wrapper(frm);
		if (!wrapper?.length) return;

		const total = frm.__project_tasks_data?.length || 0;
		const shown = wrapper.find("[data-role='task-table-body'] tr[data-task-name]").length || 0;
		const filters = frm.events.get_project_task_filters(frm);
		const hasFilter = Boolean(filters.hide_completed || filters.status || filters.assign_to);

		wrapper.find("[data-role='filter-count']").text(
			hasFilter ? __("{0} of {1} shown", [shown, total]) : ""
		);
	},
});
