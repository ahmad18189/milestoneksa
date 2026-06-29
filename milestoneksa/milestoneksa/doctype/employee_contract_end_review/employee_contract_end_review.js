// Copyright (c) 2026, ahmed and contributors

frappe.ui.form.on("Employee Contract End Review", {
	refresh(frm) {
		if (frm.doc.status !== "Pending Review" || frm.is_new()) {
			return;
		}

		frm.add_custom_button(__("Extend Contract"), () => {
			frappe.confirm(
				__("Extend contract by 1 year for {0}?", [frm.doc.employee_name]),
				() => {
					frappe.call({
						method: "milestoneksa.milestoneksa.doctype.employee_contract_end_review.employee_contract_end_review.extend_contract",
						args: { name: frm.doc.name },
						freeze: true,
						callback(r) {
							if (r.exc) return;
							frappe.show_alert({
								message: r.message?.message || __("Contract extended."),
								indicator: "green",
							});
							frm.reload_doc();
						},
					});
				}
			);
		}, __("Actions"));

		frm.add_custom_button(__("End Contract"), () => {
			frappe.confirm(
				__("End contract for {0} and calculate EOS benefits?", [frm.doc.employee_name]),
				() => {
					frappe.call({
						method: "milestoneksa.milestoneksa.doctype.employee_contract_end_review.employee_contract_end_review.end_contract",
						args: { name: frm.doc.name },
						freeze: true,
						callback(r) {
							if (r.exc) return;
							frappe.show_alert({
								message: r.message?.message || __("Contract ended."),
								indicator: "orange",
							});
							frm.reload_doc();
						},
					});
				}
			);
		}, __("Actions")).addClass("btn-danger");
	},
});
