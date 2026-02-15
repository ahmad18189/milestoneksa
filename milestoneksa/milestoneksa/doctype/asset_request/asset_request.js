frappe.ui.form.on("Asset Request", {
	setup(frm) {
		// Filter item_code in child table: only fixed assets
		frm.set_query("item_code", "items", function() {
			return {
				filters: {
					"is_fixed_asset": 1
				}
			};
		});
	},

	refresh(frm) {
		// Prevent edits when already approved or issued
		if (["Approved", "Issued"].includes(frm.doc.status)) {
			frm.set_df_property("company", "read_only", 1);
			frm.set_df_property("employee", "read_only", 1);
			frm.set_df_property("items", "read_only", 1);
		}
	},

	// Recalculate total when form is saved
	validate(frm) {
		let total = 0;
		(frm.doc.items || []).forEach(row => {
			total += row.qty || 0;
		});
		frm.set_value("total_qty", total);
	}
});

// Trigger total update when qty changes in child table
frappe.ui.form.on("Asset Request Item", {
	qty: function(frm) {
		let total = 0;
		(frm.doc.items || []).forEach(row => {
			total += row.qty || 0;
		});
		frm.set_value("total_qty", total);
	}
});
