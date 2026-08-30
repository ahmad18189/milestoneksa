frappe.ui.form.on("Executive Dashboard Settings", {
	refresh(frm) {
		frm.set_query("account", "cash_accounts", () => ({
			filters: {
				company: frm.doc.default_company || undefined,
				is_group: 0,
			},
		}));
		frm.set_query("account", "excluded_cash_accounts", () => ({
			filters: {
				company: frm.doc.default_company || undefined,
				is_group: 0,
			},
		}));
		frm.set_query("project", "target_projects", () => {
			const filters = {};
			if (frm.doc.default_company) {
				filters.company = frm.doc.default_company;
			}
			return { filters };
		});
	},

	select_target_projects(frm) {
		open_target_projects_modal(frm);
	},
});

let _ed_target_projects_dialog = null;

function open_target_projects_modal(frm) {
	if (_ed_target_projects_dialog) {
		_ed_target_projects_dialog.hide();
		_ed_target_projects_dialog = null;
	}

	const company = frm.doc.default_company;
	const existing = (frm.doc.target_projects || [])
		.map((r) => r.project)
		.filter(Boolean);

	const dialog = new frappe.ui.Dialog({
		title: __("Select Target Projects"),
		size: "large",
		fields: [
			{
				fieldname: "filter_status",
				fieldtype: "Select",
				label: __("Status"),
				options: "\nOpen\nCompleted\nCancelled",
				default: "",
			},
			{
				fieldname: "project_html",
				fieldtype: "HTML",
			},
		],
		primary_action_label: __("Update Target Projects"),
		primary_action() {
			const checked = [];
			dialog.$wrapper.find("input.ed-project-check:checked").each(function () {
				checked.push({
					name: this.value,
					project_name: this.getAttribute("data-project-name") || this.value,
					status: this.getAttribute("data-status") || "",
				});
			});
			apply_target_projects(frm, checked);
			dialog.hide();
			_ed_target_projects_dialog = null;
		},
	});

	_ed_target_projects_dialog = dialog;
	dialog.show();

	const render = () => {
		const status = dialog.get_value("filter_status");
		const filters = {};
		if (company) filters.company = company;
		if (status) filters.status = status;

		frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "Project",
				fields: ["name", "project_name", "status", "company", "percent_complete"],
				filters,
				limit_page_length: 200,
				order_by: "project_name asc",
			},
			callback(r) {
				const projects = r.message || [];
				const rows = projects
					.map((p) => {
						const selected = existing.includes(p.name) ? "checked" : "";
						return `<label class="ed-project-row" style="display:flex;gap:0.75rem;align-items:center;padding:0.45rem 0.25rem;border-bottom:1px solid #eee;cursor:pointer;">
							<input type="checkbox" class="ed-project-check" value="${frappe.utils.escape_html(p.name)}"
								data-project-name="${frappe.utils.escape_html(p.project_name || p.name)}"
								data-status="${frappe.utils.escape_html(p.status || "")}" ${selected}>
							<span style="flex:1;">
								<strong>${frappe.utils.escape_html(p.project_name || p.name)}</strong>
								<span class="text-muted" style="margin-inline-start:0.5rem;">${frappe.utils.escape_html(p.name)}</span>
							</span>
							<span class="indicator-pill ${p.status === "Open" ? "green" : "gray"}">${frappe.utils.escape_html(p.status || "")}</span>
							<span class="text-muted">${flt(p.percent_complete || 0).toFixed(0)}%</span>
						</label>`;
					})
					.join("");

				const html = `
					<div style="margin-bottom:0.5rem;display:flex;gap:0.5rem;align-items:center;">
						<button class="btn btn-xs btn-default ed-select-all" type="button">${__("Select All")}</button>
						<button class="btn btn-xs btn-default ed-clear-all" type="button">${__("Clear")}</button>
						<span class="text-muted" style="margin-inline-start:auto;">${projects.length} ${__("projects")}</span>
					</div>
					<div class="ed-project-list" style="max-height:420px;overflow:auto;border:1px solid #e5e7eb;border-radius:6px;padding:0.25rem 0.75rem;">
						${rows || `<div class="text-muted" style="padding:1rem;">${__("No projects found")}</div>`}
					</div>`;
				dialog.fields_dict.project_html.$wrapper.html(html);
				dialog.$wrapper.find(".ed-select-all").on("click", () => {
					dialog.$wrapper.find("input.ed-project-check").prop("checked", true);
				});
				dialog.$wrapper.find(".ed-clear-all").on("click", () => {
					dialog.$wrapper.find("input.ed-project-check").prop("checked", false);
				});
			},
		});
	};

	dialog.fields_dict.filter_status.$input.on("change", render);
	render();
}

function apply_target_projects(frm, selected) {
	frm.clear_table("target_projects");
	(selected || []).forEach((p) => {
		const row = frm.add_child("target_projects");
		row.project = p.name;
		row.project_name = p.project_name;
		row.status = p.status;
		row.include_in_dashboard = 1;
	});
	frm.refresh_field("target_projects");
	frm.dirty();
	frappe.show_alert({
		message: __("Target projects updated ({0}). Save to apply.", [(selected || []).length]),
		indicator: "green",
	});
}

function flt(v) {
	const n = Number(v);
	return Number.isFinite(n) ? n : 0;
}
