frappe.provide("milestoneksa.rfq_ceo");

frappe.ui.form.on("Request for Quotation", {
	refresh(frm) {
		frm.events.setup_rfq_ceo_review(frm);
	},

	setup_rfq_ceo_review(frm) {
		if (frm.is_new()) return;

		frm.events.render_rfq_ceo_comparison(frm);

		if (frm.doc.docstatus !== 1) return;

		frm.add_custom_button(__("Send Comparison to CEO"), () => {
			frm.events.open_send_rfq_to_ceo_dialog(frm);
		}, __("CEO Review"));

		const canDecide =
			frm.doc.custom_ceo_review_status === "Pending CEO Review" &&
			(frappe.session.user === frm.doc.custom_ceo_reviewer ||
				frappe.user.has_role("System Manager") ||
				frappe.session.user === "Administrator");

		if (canDecide) {
			frm.add_custom_button(__("Approve Recommended Quotation"), () => {
				frm.events.open_rfq_ceo_decision_dialog(frm, "Approved");
			}, __("CEO Review"));
			frm.add_custom_button(__("Reject Comparison"), () => {
				frm.events.open_rfq_ceo_decision_dialog(frm, "Rejected");
			}, __("CEO Review")).addClass("btn-danger");
		}
	},

	render_rfq_ceo_comparison(frm) {
		const field = frm.fields_dict.custom_sq_comparison_html;
		if (!field) return;

		const set_html = (html) => {
			const content = `<div class="rfq-ceo-comparison">${html || ""}</div>`;
			// HTML controls re-render from df.options; setting only $wrapper gets wiped.
			frm.set_df_property("custom_sq_comparison_html", "options", content);
			if (typeof field.html === "function") {
				field.html(content);
			} else if (field.$wrapper?.length) {
				field.$wrapper.html(content);
			}
		};

		set_html(`<div class="text-muted text-center py-3">${__("Loading comparison...")}</div>`);

		frappe.call({
			method: "milestoneksa.api.rfq_ceo_review.get_rfq_supplier_quotations",
			args: { rfq: frm.doc.name },
			callback(r) {
				const data = r.message || {};
				frm.__rfq_ceo_quotations = data.quotations || [];
				frm.__rfq_ceo_users = data.ceo_users || frm.__rfq_ceo_users || [];
				set_html(data.html || "");
			},
			error() {
				set_html(
					`<div class="text-danger">${__("Unable to load supplier quotation comparison.")}</div>`
				);
			},
		});
	},

	open_send_rfq_to_ceo_dialog(frm) {
		const openWithUsers = (ceoUsers) => {
			const names = (ceoUsers || []).map((u) => u.value);
			if (!names.length) {
				frappe.msgprint(__("No enabled users with the CEO role were found."));
				return;
			}
			const dialog = new frappe.ui.Dialog({
				title: __("Send Comparison to CEO"),
				fields: [
					{
						fieldname: "ceo_user",
						label: __("CEO User"),
						fieldtype: "Link",
						options: "User",
						reqd: 1,
						default: frm.doc.custom_ceo_reviewer || names[0],
						get_query: () => ({
							filters: {
								name: ["in", names],
								enabled: 1,
							},
						}),
					},
					{
						fieldname: "remarks",
						label: __("Remarks"),
						fieldtype: "Small Text",
					},
				],
				primary_action_label: __("Send"),
				primary_action(values) {
					if (!values.ceo_user) {
						frappe.msgprint(__("Please select a CEO user."));
						return;
					}
					dialog.disable_primary_action();
					frappe.call({
						method: "milestoneksa.api.rfq_ceo_review.send_rfq_comparison_to_ceo",
						args: {
							rfq: frm.doc.name,
							ceo_user: values.ceo_user,
							remarks: values.remarks || "",
						},
						freeze: true,
						freeze_message: __("Sending comparison to CEO..."),
						callback() {
							dialog.hide();
							frappe.show_alert({
								message: __("Comparison sent to CEO"),
								indicator: "green",
							});
							frm.reload_doc().then(() => {
								frm.events.render_rfq_ceo_comparison(frm);
							});
						},
						error() {
							dialog.enable_primary_action();
						},
					});
				},
			});
			dialog.show();
		};

		if (frm.__rfq_ceo_users?.length) {
			openWithUsers(frm.__rfq_ceo_users);
			return;
		}

		frappe.call({
			method: "milestoneksa.api.rfq_ceo_review.get_ceo_users",
			callback(r) {
				frm.__rfq_ceo_users = r.message || [];
				openWithUsers(frm.__rfq_ceo_users);
			},
		});
	},

	open_rfq_ceo_decision_dialog(frm, decision) {
		const quotations = frm.__rfq_ceo_quotations || [];
		if (!quotations.length) {
			frappe.msgprint(__("No submitted supplier quotations linked to this RFQ yet."));
			return;
		}

		const optionMap = {};
		const options = quotations
			.map((q) => {
				const label = `${q.name} — ${q.supplier_name || q.supplier || ""} — ${q.formatted_grand_total || ""}`;
				optionMap[label] = q.name;
				return label;
			})
			.join("\n");
		const lowest = quotations.find((q) => q.is_lowest);
		const defaultLabel = quotations
			.map((q) => {
				const label = `${q.name} — ${q.supplier_name || q.supplier || ""} — ${q.formatted_grand_total || ""}`;
				return { name: q.name, label };
			})
			.find((row) => row.name === (frm.doc.custom_winning_supplier_quotation || lowest?.name))?.label;

		const dialog = new frappe.ui.Dialog({
			title: decision === "Approved" ? __("Approve Recommended Quotation") : __("Reject Comparison"),
			fields: [
				{
					fieldname: "recommended_quotation_label",
					label: __("Recommended Supplier Quotation"),
					fieldtype: "Select",
					options,
					reqd: decision === "Approved" ? 1 : 0,
					default: defaultLabel || "",
					description: __("Select the supplier quotation you recommend."),
				},
				{
					fieldname: "remarks",
					label: __("Remarks"),
					fieldtype: "Small Text",
				},
			],
			primary_action_label: decision === "Approved" ? __("Approve") : __("Reject"),
			primary_action(values) {
				const recommended = optionMap[values.recommended_quotation_label] || "";
				if (decision === "Approved" && !recommended) {
					frappe.msgprint(__("Please select a recommended supplier quotation."));
					return;
				}
				dialog.disable_primary_action();
				frappe.call({
					method: "milestoneksa.api.rfq_ceo_review.record_rfq_ceo_decision",
					args: {
						rfq: frm.doc.name,
						recommended_quotation: recommended,
						decision,
						remarks: values.remarks || "",
					},
					freeze: true,
					freeze_message: __("Saving CEO decision..."),
					callback() {
						dialog.hide();
						frappe.show_alert({
							message:
								decision === "Approved"
									? __("Quotation approved")
									: __("Comparison rejected"),
							indicator: decision === "Approved" ? "green" : "orange",
						});
						frm.reload_doc().then(() => {
							frm.events.render_rfq_ceo_comparison(frm);
						});
					},
					error() {
						dialog.enable_primary_action();
					},
				});
			},
		});

		dialog.show();
	},
});
