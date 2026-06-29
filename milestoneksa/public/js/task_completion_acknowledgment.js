frappe.ui.form.on("Task", {
	status(frm) {
		if (frm.doc.status !== "Completed") {
			frm.__completion_acknowledged = false;
		}
	},

	validate(frm) {
		if (
			frm.is_new() ||
			frm.doc.status !== "Completed" ||
			frm.__completion_acknowledged ||
			frm.__checking_completion_acknowledgement
		) {
			return;
		}

		frappe.validated = false;
		frm.__checking_completion_acknowledgement = true;

		frappe.call({
			method: "milestoneksa.api.project_tasks.get_task_completion_children",
			args: { task_name: frm.doc.name },
			callback(r) {
				frm.__checking_completion_acknowledgement = false;
				const children = r?.message?.children || [];
				if (!children.length) {
					frm.__completion_acknowledged = true;
					frm.save();
					return;
				}

				frm.events.show_completion_acknowledgement(frm, children);
			},
			error() {
				frm.__checking_completion_acknowledgement = false;
			},
		});
	},

	show_completion_acknowledgement(frm, children) {
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
						<div class="mb-2"><strong>${escapeHtml(frm.doc.subject || frm.doc.name)}</strong></div>
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
				frm.__completion_acknowledged = true;
				frappe.call({
					method: "milestoneksa.api.project_tasks.complete_parent_task_with_acknowledgement",
					args: { task_name: frm.doc.name },
					freeze: true,
					freeze_message: __("Updating task..."),
					callback() {
						frappe.show_alert({ message: __("Task updated"), indicator: "green" });
						frm.reload_doc();
					},
				});
			},
		});
		dialog.show();
	},
});
