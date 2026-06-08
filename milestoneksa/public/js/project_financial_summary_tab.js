frappe.ui.form.on("Project", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("Recalculate Costing"), () => {
				frappe.call({
					method: "milestoneksa.milestoneksa.project.recalculate_project_costing",
					args: { project: frm.doc.name },
					callback(r) {
						if (r && r.message) {
							const msg = r.message.message || __("Costing recalculated.");
							const total = r.message.total_purchase_cost;
							frappe.show_alert({
								message: total != null ? __("Costing recalculated. Total Purchase Cost: {0}", [frm.events.format_currency(total)]) : msg,
								indicator: "green",
							});
							frm.reload_doc(() => {
								if (frm.fields_dict.total_purchase_cost) {
									frm.refresh_field("total_purchase_cost");
								}
							});
						}
					},
					error(err) {
						frappe.msgprint({ title: __("Error"), message: err.message || err.exc, indicator: "red" });
					},
				});
			}, __("Financial Summary"));
			frm.add_custom_button(__("Purchased Items Cost"), () => {
				frm.events.show_purchased_items_cost_dialog(frm);
			}, __("Financial Summary"));
		}
		frm.events.render_financial_summary(frm);
	},
	after_save(frm) {
		frm.events.render_financial_summary(frm);
	},

	show_purchased_items_cost_dialog(frm) {
		const dialog = new frappe.ui.Dialog({
			title: __("Purchased Items Cost"),
			size: "extra-large",
			fields: [
				{
					fieldtype: "HTML",
					fieldname: "content",
					options: `
						<div class="text-center p-4">
							<div class="spinner-border text-primary"></div>
							<div class="mt-2">${__("Loading purchased items cost...")}</div>
						</div>
					`,
				},
			],
		});
		dialog.show();

		frappe.call({
			method: "milestoneksa.api.project_financial_summary.get_project_purchased_items_cost",
			args: { project: frm.doc.name },
			callback(r) {
				const data = r && r.message ? r.message : {};
				dialog.fields_dict.content.$wrapper.html(
					frm.events.render_purchased_items_cost_dialog(frm, data)
				);
			},
			error(err) {
				dialog.fields_dict.content.$wrapper.html(`
					<div class="alert alert-danger">
						${__("Failed to load purchased items cost.")}
						<br><small>${err.message || err.exc || ""}</small>
					</div>
				`);
			},
		});
	},

	render_purchased_items_cost_dialog(frm, data) {
		const fmt = (v) => frm.events.format_currency(v);
		const escapeHtml = (s) => {
			if (s == null || s === "") return "";
			return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
		};
		const itemSummary = data.item_summary || [];
		const identifierActivitySummary = data.identifier_activity_summary || [];
		const purchaseSummary = data.purchase_summary || [];
		const details = data.details || [];
		const totals = data.totals || {};

		const buildEmpty = (message) => `<p class="text-muted mb-0">${escapeHtml(message)}</p>`;
		const buildIdentifierActivitySummary = () => {
			if (!identifierActivitySummary.length) return buildEmpty(__("No Project Identifier / Activity Type costs found for this project."));
			let html = '<div class="table-responsive"><table class="summary-table purchased-items-table"><thead><tr><th>' + __("Project Identifier") + '</th><th>' + __("Activity Type") + '</th><th class="text-right">' + __("Qty") + '</th><th class="text-right">' + __("Net Amount") + '</th><th class="text-right">' + __("Total Cost (Incl. VAT)") + '</th></tr></thead><tbody>';
			identifierActivitySummary.forEach((row) => {
				html += '<tr><td>' + escapeHtml(row.project_identifier) + '</td><td>' + escapeHtml(row.activity_type) + '</td><td class="text-right">' + flt(row.qty, 2) + '</td><td class="text-right">' + fmt(row.net_amount) + '</td><td class="text-right">' + fmt(row.amount_with_vat) + '</td></tr>';
			});
			html += '<tr class="total-row"><td colspan="3"><strong>' + __("Grand Total") + '</strong></td><td class="text-right">' + fmt(totals.net_amount) + '</td><td class="text-right">' + fmt(totals.amount_with_vat) + '</td></tr>';
			html += "</tbody></table></div>";
			return html;
		};
		const buildItemSummary = () => {
			if (!itemSummary.length) return buildEmpty(__("No purchased items found for this project."));
			let html = '<div class="table-responsive"><table class="summary-table purchased-items-table"><thead><tr><th>' + __("Item") + '</th><th>' + __("Item Name") + '</th><th>' + __("Activity Type") + '</th><th>' + __("Project Identifier") + '</th><th class="text-right">' + __("Qty") + '</th><th>' + __("UOM") + '</th><th class="text-right">' + __("Net Amount") + '</th><th class="text-right">' + __("Total Cost (Incl. VAT)") + '</th></tr></thead><tbody>';
			itemSummary.forEach((row) => {
				html += '<tr><td>' + escapeHtml(row.item_code) + '</td><td>' + escapeHtml(row.item_name) + '</td><td>' + escapeHtml(row.activity_types) + '</td><td>' + escapeHtml(row.project_identifiers) + '</td><td class="text-right">' + flt(row.qty, 2) + '</td><td>' + escapeHtml(row.uom) + '</td><td class="text-right">' + fmt(row.net_amount) + '</td><td class="text-right">' + fmt(row.amount_with_vat) + '</td></tr>';
			});
			html += '<tr class="total-row"><td colspan="6"><strong>' + __("Grand Total") + '</strong></td><td class="text-right">' + fmt(totals.net_amount) + '</td><td class="text-right">' + fmt(totals.amount_with_vat) + '</td></tr>';
			html += "</tbody></table></div>";
			return html;
		};
		const buildPurchaseSummary = () => {
			if (!purchaseSummary.length) return buildEmpty(__("No purchase invoices found for this project."));
			let html = '<div class="table-responsive"><table class="summary-table purchased-items-table"><thead><tr><th>' + __("Purchase Invoice") + '</th><th>' + __("Posting Date") + '</th><th>' + __("Supplier") + '</th><th>' + __("Activity Type") + '</th><th>' + __("Project Identifier") + '</th><th>' + __("Purchase Order") + '</th><th class="text-right">' + __("Net Amount") + '</th><th class="text-right">' + __("Total Cost (Incl. VAT)") + '</th></tr></thead><tbody>';
			purchaseSummary.forEach((row) => {
				const piLink = frappe.utils.get_form_link("Purchase Invoice", row.purchase_invoice, true);
				html += '<tr><td class="doc-link">' + piLink + '</td><td>' + (row.posting_date || "") + '</td><td>' + escapeHtml(row.supplier_name || row.supplier) + '</td><td>' + escapeHtml(row.activity_types) + '</td><td>' + escapeHtml(row.project_identifiers) + '</td><td>' + escapeHtml(row.purchase_orders) + '</td><td class="text-right">' + fmt(row.net_amount) + '</td><td class="text-right">' + fmt(row.amount_with_vat) + '</td></tr>';
			});
			html += '<tr class="total-row"><td colspan="6"><strong>' + __("Grand Total") + '</strong></td><td class="text-right">' + fmt(totals.net_amount) + '</td><td class="text-right">' + fmt(totals.amount_with_vat) + '</td></tr>';
			html += "</tbody></table></div>";
			return html;
		};
		const buildDetails = () => {
			if (!details.length) return buildEmpty(__("No purchase invoice item details found for this project."));
			let html = '<div class="table-responsive"><table class="summary-table purchased-items-table"><thead><tr><th>' + __("Purchase Invoice") + '</th><th>' + __("Purchase Order") + '</th><th>' + __("Supplier") + '</th><th>' + __("Activity Type") + '</th><th>' + __("Project Identifier") + '</th><th>' + __("Item") + '</th><th class="text-right">' + __("Qty") + '</th><th class="text-right">' + __("Net Amount") + '</th><th class="text-right">' + __("Total Cost (Incl. VAT)") + '</th></tr></thead><tbody>';
			details.forEach((row) => {
				const piLink = frappe.utils.get_form_link("Purchase Invoice", row.purchase_invoice, true);
				const poLink = row.purchase_order ? frappe.utils.get_form_link("Purchase Order", row.purchase_order, true) : "";
				html += '<tr><td class="doc-link">' + piLink + '</td><td class="doc-link">' + poLink + '</td><td>' + escapeHtml(row.supplier_name || row.supplier) + '</td><td>' + escapeHtml(row.activity_type) + '</td><td>' + escapeHtml(row.project_identifier) + '</td><td>' + escapeHtml(row.item_name || row.item_code) + '</td><td class="text-right">' + flt(row.qty, 2) + '</td><td class="text-right">' + fmt(row.net_amount) + '</td><td class="text-right">' + fmt(row.amount_with_vat) + '</td></tr>';
			});
			html += "</tbody></table></div>";
			return html;
		};

		return `
			<style>
				.purchased-items-cost-dialog .cost-kpis {
					display: grid;
					grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
					gap: 12px;
					margin-bottom: 16px;
				}
				.purchased-items-cost-dialog .cost-kpi {
					background: #f8f9fa;
					border: 1px solid #e9ecef;
					border-radius: 8px;
					padding: 12px;
				}
				.purchased-items-cost-dialog .cost-kpi .label {
					color: #6c757d;
					font-size: 12px;
					margin-bottom: 6px;
				}
				.purchased-items-cost-dialog .cost-kpi .value {
					font-size: 18px;
					font-weight: 600;
				}
				.purchased-items-cost-dialog .section-title {
					color: #667eea;
					border-bottom: 1px solid #dbe1ff;
					padding-bottom: 6px;
					margin: 18px 0 10px;
				}
				.purchased-items-cost-dialog .table-responsive {
					overflow-x: auto;
				}
				.purchased-items-cost-dialog .purchased-items-table {
					min-width: 1200px;
				}
			</style>
			<div class="purchased-items-cost-dialog">
				<div class="cost-kpis">
					<div class="cost-kpi">
						<div class="label">${__("Total Cost (Incl. VAT)")}</div>
						<div class="value">${fmt(totals.amount_with_vat)}</div>
					</div>
					<div class="cost-kpi">
						<div class="label">${__("Net Amount")}</div>
						<div class="value">${fmt(totals.net_amount)}</div>
					</div>
					<div class="cost-kpi">
						<div class="label">${__("Purchased Items")}</div>
						<div class="value">${itemSummary.length}</div>
					</div>
					<div class="cost-kpi">
						<div class="label">${__("Purchase Invoices")}</div>
						<div class="value">${purchaseSummary.length}</div>
					</div>
				</div>
				<h5 class="section-title">${__("Project Identifier / Activity Type Cost")}</h5>
				${buildIdentifierActivitySummary()}
				<h5 class="section-title">${__("Item-wise Total Cost")}</h5>
				${buildItemSummary()}
				<h5 class="section-title">${__("Purchase-wise Total Cost")}</h5>
				${buildPurchaseSummary()}
				<h5 class="section-title">${__("Purchase Invoice Item Details")}</h5>
				${buildDetails()}
			</div>
		`;
	},

	render_financial_summary(frm) {
		const field = frm.fields_dict.custom_financial_summary_html;
		if (!field) return;

		const wrapper = field.$wrapper;
		wrapper.empty().addClass("project-financial-summary-wrapper").css({
			padding: "20px",
			background: "#f8f9fa",
			minHeight: "400px",
		});

		if (frm.is_new()) {
			wrapper.append(
				$("<div class='alert alert-info'>").text(__("Save the project to view the Financial Summary."))
			);
			return;
		}

		wrapper.append(`
			<div data-role="financial-summary-loading" class="text-center mt-5">
				<div class="spinner-border text-primary" style="width: 3rem; height: 3rem;"></div>
				<div class="mt-3">${__("Loading financial summary...")}</div>
			</div>
		`);
		const loading = wrapper.find("[data-role='financial-summary-loading']");

		frappe.call({
			method: "milestoneksa.api.project_financial_summary.get_financial_summary_data",
			args: { project: frm.doc.name },
			callback(r) {
				loading.hide();
				if (!r || !r.message) {
					wrapper.append(`<div class="alert alert-danger">${__("Failed to load financial summary.")}</div>`);
					return;
				}
				const msg = r.message;
				const content = $("<div data-role='financial-summary-content'></div>");
				content.append(frm.events.get_financial_summary_styles());
				content.append(frm.events.render_payment_overview_section(frm, msg.payment_summary, msg.last_month_invoiced));
				// Hidden for now: Gross Margin / Profit
				// content.append(frm.events.render_gross_margin_section(frm, msg.gross_margin));
				content.append(frm.events.render_budget_vs_actual_section(frm, msg.budget_vs_actual));
				content.append(frm.events.render_project_identifier_activity_cost_section(frm, msg.identifier_activity_cost));
				// Hidden for now: Billed vs Unbilled
				// content.append(frm.events.render_billed_vs_unbilled_section(frm, msg.billed_vs_unbilled));
				content.append(frm.events.render_outstanding_section(frm, msg.outstanding_po));
				content.append(frm.events.render_supplier_payments_section(frm, msg.supplier_payments_unallocated_unreconciled || []));
				content.append(frm.events.render_costs_section(frm, msg.costs));
				content.append(frm.events.render_income_section(frm, msg.income));
				content.append(frm.events.render_cost_breakdown_section(frm, msg.cost_breakdown));
				content.append(frm.events.render_top_suppliers_section(frm, msg.top_suppliers));
				// Hidden for now: Payment Status, Last Activity
				// content.append(frm.events.render_payment_status_section(frm, msg.payment_status));
				// content.append(frm.events.render_last_activity_section(frm, msg.last_activity));
				content.append(frm.events.render_active_po_item_section(frm, msg.active_po_item_detail || msg.active_purchase_orders));
				wrapper.append(content);
			},
			error(err) {
				loading.hide();
				wrapper.append(`
					<div class="alert alert-danger">
						<h5>${__("Error loading financial summary")}</h5>
						<small>${err.message || err.exc || "Unknown error"}</small>
					</div>
				`);
			},
		});
	},

	get_financial_summary_styles() {
		return $(`
			<style>
				.project-financial-summary-wrapper {
					max-width: 100%;
					box-sizing: border-box;
				}
				.project-financial-summary-wrapper .summary-section {
					margin-bottom: 28px;
					max-width: 100%;
				}
				.project-financial-summary-wrapper .summary-section h5 {
					border-bottom: 2px solid #667eea;
					padding-bottom: 8px;
					color: #667eea;
					margin-bottom: 12px;
				}
				/* Scrollable container for wide tables - prevents columns from being cut off */
				.project-financial-summary-wrapper .summary-section .table-responsive {
					overflow-x: auto;
					-webkit-overflow-scrolling: touch;
					margin-bottom: 8px;
					max-width: 100%;
				}
				.project-financial-summary-wrapper .summary-table {
					width: 100%;
					min-width: 640px;
					border-collapse: collapse;
					background: white;
					border-radius: 8px;
					overflow: hidden;
					box-shadow: 0 1px 3px rgba(0,0,0,0.08);
					table-layout: auto;
				}
				.project-financial-summary-wrapper .summary-table th,
				.project-financial-summary-wrapper .summary-table td {
					padding: 10px 14px;
					text-align: left;
					border-bottom: 1px solid #eee;
					word-wrap: break-word;
				}
				.project-financial-summary-wrapper .summary-table th.text-right,
				.project-financial-summary-wrapper .summary-table td.text-right {
					white-space: nowrap;
				}
				.project-financial-summary-wrapper .summary-table th {
					background: #f8f9fa;
					font-weight: 600;
					color: #495057;
				}
				.project-financial-summary-wrapper .summary-table tr.total-row td {
					font-weight: 700;
					background: #f8f9fa;
				}
				.project-financial-summary-wrapper .summary-table .text-right { text-align: right; }
				.project-financial-summary-wrapper .doc-link { color: #2490ef; }
				.project-financial-summary-wrapper .payment-overview-kpi {
					display: grid;
					grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
					gap: 12px;
					margin-bottom: 20px;
				}
				@media (max-width: 768px) {
					.project-financial-summary-wrapper .payment-overview-kpi {
						grid-template-columns: 1fr;
					}
				}
				.project-financial-summary-wrapper .payment-overview-kpi .kpi-card {
					background: white;
					border-radius: 8px;
					padding: 14px 16px;
					box-shadow: 0 1px 3px rgba(0,0,0,0.08);
					border-left: 4px solid #667eea;
					min-width: 0;
				}
				.project-financial-summary-wrapper .payment-overview-kpi .kpi-card .kpi-label {
					font-size: 12px;
					color: #6c757d;
					margin-bottom: 4px;
				}
				.project-financial-summary-wrapper .payment-overview-kpi .kpi-card .kpi-value {
					font-size: 18px;
					font-weight: 600;
					color: #212529;
				}
				.project-financial-summary-wrapper .po-item-table { margin-left: 12px; margin-bottom: 16px; }
				.project-financial-summary-wrapper .po-item-table .summary-table { font-size: 13px; min-width: 520px; }
				.project-financial-summary-wrapper .po-items-toggle { cursor: pointer; user-select: none; padding: 8px 12px; display: inline-block; margin-left: 12px; margin-bottom: 4px; font-size: 13px; color: #2490ef; }
				.project-financial-summary-wrapper .po-items-toggle:hover { text-decoration: underline; }
				.project-financial-summary-wrapper .po-items-collapse { margin-left: 12px; }
				.project-financial-summary-wrapper .po-items-collapse.collapse { display: none; }
				.project-financial-summary-wrapper .section-toggle { cursor: pointer; user-select: none; }
				.project-financial-summary-wrapper .section-toggle:hover { opacity: 0.85; }
				.project-financial-summary-wrapper .active-po-section-content.collapse { display: none; }
				.project-financial-summary-wrapper .cost-breakdown-bars .progress-bar { background-color: #667eea; }
			</style>
		`);
	},

	format_currency(val) {
		if (val == null || val === "") return "0.00";
		const currency = frappe.defaults.get_default("currency") || "SAR";
		return frappe.format(flt(val), { fieldtype: "Currency", options: currency });
	},

	render_payment_overview_section(frm, payment_summary, last_month_invoiced) {
		if (!payment_summary) return $("<div></div>");
		const fmt = (v) => frm.events.format_currency(v);
		const section = $(`<div class="summary-section"><h5>${__("Payment Overview")}</h5></div>`);
		const kpi = $(`<div class="payment-overview-kpi"></div>`);
		kpi.append(`
			<div class="kpi-card">
				<div class="kpi-label">${__("Total Paid to Date")}</div>
				<div class="kpi-value">${fmt(payment_summary.total_paid_to_date)}</div>
			</div>
			<div class="kpi-card">
				<div class="kpi-label">${__("Total Remaining")} (PO)</div>
				<div class="kpi-value">${fmt(payment_summary.total_remaining_po)}</div>
			</div>
			<div class="kpi-card">
				<div class="kpi-label">${__("Project Total Cost (Purchase Orders total)")}</div>
				<div class="kpi-value">${fmt(payment_summary.project_total_cost)}</div>
			</div>
		`);
		section.append(kpi);
		return section;
	},

	render_gross_margin_section(frm, data) {
		if (!data) return $("<div></div>");
		const fmt = (v) => frm.events.format_currency(v);
		const section = $(`<div class="summary-section"><h5>${__("Gross Margin / Profit")}</h5></div>`);
		const kpi = $(`<div class="payment-overview-kpi"></div>`);
		kpi.append(`
			<div class="kpi-card">
				<div class="kpi-label">${__("Profit")}</div>
				<div class="kpi-value">${fmt(data.profit)}</div>
			</div>
			<div class="kpi-card">
				<div class="kpi-label">${__("Margin %")}</div>
				<div class="kpi-value">${flt(data.margin_pct, 2)}%</div>
			</div>
		`);
		section.append(kpi);
		return section;
	},

	render_budget_vs_actual_section(frm, data) {
		if (!data) return $("<div></div>");
		const fmt = (v) => frm.events.format_currency(v);
		const section = $(`<div class="summary-section"><h5>${__("Budget vs Actual")}</h5></div>`);
		const rows = [
			[__("Estimated (Budget)"), data.estimated],
			[__("Actual Cost"), data.actual],
			[__("Variance"), data.variance],
		];
		const table = frm.events.build_summary_table(frm, rows);
		const p = $("<p class='mt-2 mb-0'>").text(__("Variance") + ": " + flt(data.variance_pct, 2) + "%" + (data.over_budget ? " (" + __("Over budget") + ")" : ""));
		section.append($('<div class="table-responsive">').append(table)).append(p);
		return section;
	},

	render_billed_vs_unbilled_section(frm, data) {
		if (!data) return $("<div></div>");
		const section = $(`<div class="summary-section"><h5>${__("Billed vs Unbilled")}</h5></div>`);
		const rows = [
			[__("Total Billed") + " (SI)", data.total_billed],
			[__("Sales Order Total"), data.total_sales_amount],
			[__("Unbilled"), data.unbilled],
		];
		section.append($('<div class="table-responsive">').append(frm.events.build_summary_table(frm, rows)));
		return section;
	},

	render_invoiced_this_month_section(frm, value) {
		const section = $(`<div class="summary-section"><h5>${__("Invoiced This Month")}</h5></div>`);
		section.append($("<div class='kpi-card'>").append(
			$("<div class='kpi-label'>").text(__("Purchase costs invoiced this month")),
			$("<div class='kpi-value'>").text(frm.events.format_currency(value))
		));
		return section;
	},

	render_sales_order_total_section(frm, value) {
		const section = $(`<div class="summary-section"><h5>${__("Sales Order Total")}</h5></div>`);
		section.append($("<div class='kpi-card'>").append(
			$("<div class='kpi-label'>").text(__("Total contract value (SO)")),
			$("<div class='kpi-value'>").text(frm.events.format_currency(value))
		));
		return section;
	},

	render_project_identifier_activity_cost_section(frm, data) {
		if (!data) return $("<div></div>");
		const rows = data.rows || [];
		const totals = data.totals || {};
		const fmt = (v) => frm.events.format_currency(v);
		const escapeHtml = (s) => {
			if (s == null || s === "") return "";
			return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
		};
		const displayValue = (value) => escapeHtml(value || __("Not Set"));
		const section = $(`<div class="summary-section"><h5>${__("Project Identifier / Activity Type Cost")}</h5></div>`);
		if (!rows.length) {
			section.append($("<p class='text-muted'>").text(__("No Project Identifier / Activity Type costs found for this project.")));
			return section;
		}
		let html = '<div class="table-responsive"><table class="summary-table"><thead><tr><th>' + __("Project Identifier") + '</th><th>' + __("Activity Type") + '</th><th>' + __("Purchase Invoices") + '</th><th>' + __("Journal Entries") + '</th><th class="text-right">' + __("Purchase Invoice Cost") + '</th><th class="text-right">' + __("Journal Entry Cost") + '</th><th class="text-right">' + __("Total Cost") + '</th></tr></thead><tbody>';
		rows.forEach((row) => {
			const invoiceLinks = (row.purchase_invoices || []).map((name) => {
				return frappe.utils.get_form_link("Purchase Invoice", name, true);
			}).join("<br>");
			const journalLinks = (row.journal_entries || []).map((name) => {
				return frappe.utils.get_form_link("Journal Entry", name, true);
			}).join("<br>");
			html += '<tr><td>' + displayValue(row.project_identifier) + '</td><td>' + displayValue(row.activity_type) + '</td><td class="doc-link">' + invoiceLinks + '</td><td class="doc-link">' + journalLinks + '</td><td class="text-right">' + fmt(row.purchase_invoice_cost) + '</td><td class="text-right">' + fmt(row.journal_entry_cost) + '</td><td class="text-right">' + fmt(row.total_cost) + '</td></tr>';
		});
		html += '<tr class="total-row"><td colspan="4"><strong>' + __("Grand Total") + '</strong></td><td class="text-right">' + fmt(totals.purchase_invoice_cost) + '</td><td class="text-right">' + fmt(totals.journal_entry_cost) + '</td><td class="text-right">' + fmt(totals.total_cost) + '</td></tr>';
		html += "</tbody></table></div>";
		section.append($(html));
		return section;
	},

	render_outstanding_section(frm, data) {
		if (!data) return $("<div></div>");
		const fmt = (v) => frm.events.format_currency(v);
		const section = $(`<div class="summary-section"><h5>${__("Outstanding (To Pay)")}</h5></div>`);
		const escapeHtml = (s) => {
			if (s == null || s === "") return "";
			return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
		};
		const poDetails = data.remaining_po_details || [];
		const piDetails = data.remaining_pi_details || [];
		let html = '<div class="table-responsive"><table class="summary-table"><thead><tr><th>' + __("Item") + '</th><th class="text-right">' + __("Amount") + '</th><th></th></tr></thead><tbody>';
		html += '<tr class="outstanding-toggle-row" data-detail="po"><td>' + __("Total remaining (PO)") + '</td><td class="text-right">' + fmt(data.total_remaining) + '</td><td class="text-right"><span class="outstanding-toggle-icon">▼</span></td></tr>';
		html += '<tr class="outstanding-detail-row outstanding-detail-po" style="display:none"><td colspan="3"></td></tr>';
		html += '<tr class="outstanding-toggle-row" data-detail="pi"><td>' + __("Total remaining (PI)") + '</td><td class="text-right">' + fmt(data.total_remaining_pi != null ? data.total_remaining_pi : 0) + '</td><td class="text-right"><span class="outstanding-toggle-icon">▼</span></td></tr>';
		html += '<tr class="outstanding-detail-row outstanding-detail-pi" style="display:none"><td colspan="3"></td></tr>';
		html += "</tbody></table></div>";
		const wrap = $('<div class="outstanding-section-wrap"></div>');
		wrap.append($(html));
		section.append(wrap);
		// PO details table
		if (poDetails.length) {
			let tableHtml = '<div class="table-responsive"><table class="summary-table po-item-table"><thead><tr><th>' + __("Purchase Order") + '</th><th>' + __("Supplier") + '</th><th class="text-right">' + __("Remaining") + '</th></tr></thead><tbody>';
			poDetails.forEach((r) => {
				const link = frappe.utils.get_form_link("Purchase Order", r.po_name, true);
				tableHtml += '<tr><td class="doc-link">' + link + '</td><td>' + escapeHtml(r.supplier) + '</td><td class="text-right">' + fmt(r.remaining) + '</td></tr>';
			});
			tableHtml += "</tbody></table></div>";
			wrap.find(".outstanding-detail-po td[colspan='3']").html(tableHtml);
		} else {
			wrap.find(".outstanding-detail-po td[colspan='3']").text(__("No POs with remaining amount."));
		}
		// PI details table
		if (piDetails.length) {
			let tableHtml = '<div class="table-responsive"><table class="summary-table po-item-table"><thead><tr><th>' + __("Purchase Invoice") + '</th><th>' + __("Posting Date") + '</th><th>' + __("Supplier") + '</th><th class="text-right">' + __("Outstanding") + '</th></tr></thead><tbody>';
			piDetails.forEach((r) => {
				const link = frappe.utils.get_form_link("Purchase Invoice", r.name, true);
				tableHtml += '<tr><td class="doc-link">' + link + '</td><td>' + (r.posting_date || "") + '</td><td>' + escapeHtml(r.supplier_name || r.supplier) + '</td><td class="text-right">' + fmt(r.outstanding_amount) + '</td></tr>';
			});
			tableHtml += "</tbody></table></div>";
			wrap.find(".outstanding-detail-pi td[colspan='3']").html(tableHtml);
		} else {
			wrap.find(".outstanding-detail-pi td[colspan='3']").text(__("No PIs with outstanding amount."));
		}
		wrap.find(".outstanding-toggle-row").on("click", function() {
			const row = $(this);
			const detail = row.attr("data-detail");
			const detailRow = wrap.find(".outstanding-detail-" + detail);
			const icon = row.find(".outstanding-toggle-icon");
			if (detailRow.is(":visible")) {
				detailRow.hide();
				icon.text("▼");
			} else {
				detailRow.show();
				icon.text("▲");
			}
		});
		return section;
	},

	render_cost_breakdown_section(frm, items) {
		if (!items || !items.length) return $("<div></div>");
		const fmt = (v) => frm.events.format_currency(v);
		const total = items.reduce((s, i) => s + flt(i.value), 0);
		const section = $(`<div class="summary-section"><h5>${__("Cost Breakdown")}</h5></div>`);
		const div = $("<div class='cost-breakdown-bars'></div>");
		items.forEach((i) => {
			const pct = total ? (flt(i.value) / total * 100) : 0;
			div.append(`
				<div class="mb-2">
					<div class="d-flex justify-content-between small">
						<span>${i.label}</span>
						<span>${fmt(i.value)} (${flt(pct, 1)}%)</span>
					</div>
					<div class="progress" style="height: 8px;">
						<div class="progress-bar" role="progressbar" style="width: ${pct}%"></div>
					</div>
				</div>
			`);
		});
		section.append(div);
		return section;
	},

	render_top_suppliers_section(frm, list) {
		if (!list || !list.length) return $("<div></div>");
		const fmt = (v) => frm.events.format_currency(v);
		const section = $(`<div class="summary-section"><h5>${__("Supplier Total Invoiced")}</h5></div>`);
		let html = '<table class="summary-table"><thead><tr><th>' + __("Supplier") + '</th><th class="text-right">' + __("Total Invoiced") + '</th></tr></thead><tbody>';
		let grandTotal = 0;
		list.forEach((r) => {
			grandTotal += flt(r.total, 2);
			html += '<tr><td>' + (r.supplier_name || r.supplier || "") + '</td><td class="text-right">' + fmt(r.total) + '</td></tr>';
		});
		html += '<tr class="total-row"><td><strong>' + __("Grand Total") + '</strong></td><td class="text-right">' + fmt(grandTotal) + '</td></tr>';
		html += "</tbody></table>";
		section.append($('<div class="table-responsive">').append($(html)));
		return section;
	},

	render_payment_status_section(frm, data) {
		if (!data) return $("<div></div>");
		const section = $(`<div class="summary-section"><h5>${__("Payment Status")}</h5></div>`);
		const kpi = $(`<div class="payment-overview-kpi"></div>`);
		kpi.append(`
			<div class="kpi-card"><div class="kpi-label">${__("Paid")}</div><div class="kpi-value">${data.paid}</div></div>
			<div class="kpi-card"><div class="kpi-label">${__("Partly Paid")}</div><div class="kpi-value">${data.partly_paid}</div></div>
			<div class="kpi-card"><div class="kpi-label">${__("Unpaid")}</div><div class="kpi-value">${data.unpaid}</div></div>
			<div class="kpi-card"><div class="kpi-label">${__("Total PIs")}</div><div class="kpi-value">${data.total}</div></div>
		`);
		section.append(kpi);
		return section;
	},

	render_last_activity_section(frm, data) {
		if (!data) return $("<div></div>");
		const section = $(`<div class="summary-section"><h5>${__("Last Activity")}</h5></div>`);
		const rows = [
			[__("Last Purchase Invoice"), data.last_pi_date || __("—")],
			[__("Last Payment Entry"), data.last_pe_date || __("—")],
		];
		let html = '<table class="summary-table"><thead><tr><th>' + __("Event") + '</th><th>' + __("Date") + '</th></tr></thead><tbody>';
		rows.forEach((r) => { html += '<tr><td>' + r[0] + '</td><td>' + r[1] + '</td></tr>'; });
		html += "</tbody></table>";
		section.append($('<div class="table-responsive">').append($(html)));
		return section;
	},

	render_supplier_payments_section(frm, payments) {
		const section = $(`<div class="summary-section"><h5>${__("Supplier Payments (Unallocated)")}</h5></div>`);
		if (!payments || !payments.length) {
			section.append($("<p class='text-muted'>").text(__("No supplier payments with empty references for this project.")));
			return section;
		}
		const fmt = (v) => (typeof v === "number" ? frm.events.format_currency(v) : v);
		let totalPaid = 0, totalAllocated = 0, totalUnallocated = 0;
		payments.forEach((p) => {
			totalPaid += flt(p.paid_amount);
			totalAllocated += flt(p.total_allocated_amount);
			totalUnallocated += flt(p.unallocated_amount);
		});
		let html = '<table class="summary-table"><thead><tr><th>' + __("Payment") + '</th><th>' + __("Posting Date") + '</th><th>' + __("Supplier") + '</th><th class="text-right">' + __("Paid") + '</th><th class="text-right">' + __("Allocated") + '</th><th class="text-right">' + __("Unallocated") + '</th><th>' + __("Reconciled") + '</th></tr></thead><tbody>';
		payments.forEach((p) => {
			const link = frappe.utils.get_form_link("Payment Entry", p.name, true);
			const reconciled = p.reconciled ? __("Yes") : __("No");
			html += '<tr><td class="doc-link">' + link + '</td><td>' + (p.posting_date || "") + '</td><td>' + (p.party_name || p.party || "") + '</td><td class="text-right">' + fmt(p.paid_amount) + '</td><td class="text-right">' + fmt(p.total_allocated_amount) + '</td><td class="text-right">' + fmt(p.unallocated_amount) + '</td><td>' + reconciled + '</td></tr>';
		});
		html += '<tr class="total-row"><td colspan="3"><strong>' + __("Total") + '</strong></td><td class="text-right">' + fmt(totalPaid) + '</td><td class="text-right">' + fmt(totalAllocated) + '</td><td class="text-right">' + fmt(totalUnallocated) + '</td><td></td></tr>';
		html += "</tbody></table>";
		section.append($('<div class="table-responsive">').append($(html)));
		return section;
	},

	render_costs_section(frm, costs) {
		if (!costs) return $("<div></div>");
		const section = $(`<div class="summary-section"><h5>${__("Costs")}</h5></div>`);
		const rows = [
			[__("Purchase Invoice"), costs.purchase_invoice],
			[__("Journal Entry / GL"), costs.journal_entry_gl],
			[__("Timesheet"), costs.timesheet],
			[__("Expense Claim"), costs.expense_claim],
			[__("Consumed Material"), costs.consumed_material],
			["<strong>" + __("Total") + "</strong>", costs.total],
		];
		section.append($('<div class="table-responsive">').append(frm.events.build_summary_table(frm, rows)));
		return section;
	},

	render_income_section(frm, income) {
		if (!income) return $("<div></div>");
		const section = $(`<div class="summary-section"><h5>${__("Income")}</h5></div>`);
		const rows = [
			[__("Sales Invoice"), income.sales_invoice],
		];
		section.append($('<div class="table-responsive">').append(frm.events.build_summary_table(frm, rows)));
		return section;
	},

	build_summary_table(frm, rows) {
		const fmt = (v) => (typeof v === "number" ? frm.events.format_currency(v) : v);
		let html = '<table class="summary-table"><thead><tr><th>' + __("Item") + '</th><th class="text-right">' + __("Amount") + '</th></tr></thead><tbody>';
		rows.forEach((r, i) => {
			const isTotal = i === rows.length - 1;
			html += '<tr class="' + (isTotal ? "total-row" : "") + '"><td>' + r[0] + '</td><td class="text-right">' + fmt(r[1]) + '</td></tr>';
		});
		html += "</tbody></table>";
		return $(html);
	},

	render_active_po_item_section(frm, poData) {
		const section = $(`
			<div class="summary-section active-po-summary-section">
				<h5 class="section-toggle active-po-section-toggle" data-expanded="false">
					<span class="toggle-icon">▼</span> ${__("Active Purchase Orders")} (${__("Contract with supplier")})
				</h5>
			</div>
		`);
		if (!poData || !poData.length) {
			section.append($("<p class='text-muted'>").text(__("No active purchase orders linked to this project.")));
			return section;
		}
		const fmt = (v) => (typeof v === "number" ? frm.events.format_currency(v) : v);
		const escapeHtml = (s) => {
			if (s == null || s === "") return "";
			const t = String(s);
			return t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
		};
		const hasItems = poData[0] && Array.isArray(poData[0].items);
		const content = $('<div class="active-po-section-content collapse"></div>');
		section.append(content);
		if (hasItems) {
			poData.forEach((p, idx) => {
				const link = frappe.utils.get_form_link("Purchase Order", p.po_name, true);
				const safeId = "po-" + idx;
				const paidId = "po-paid-" + safeId;
				const remainId = "po-remain-" + safeId;
				const invoicesId = "po-invoices-" + safeId;
				const paidItems = (p.items || []).filter((it) => flt(it.billed_amt) > 0);
				const remainItems = (p.items || []).filter((it) => flt(it.remaining_amt, 2) > 0);
				const hasInvoices = (p.invoices && p.invoices.length);
				const poBlock = $(`
					<div class="mb-3 po-block">
						<div class="table-responsive">
						<table class="summary-table">
							<thead><tr>
								<th>${__("Name")}</th><th>${__("Supplier")}</th>
								<th class="text-right">${__("Grand Total")}</th>
								<th class="text-right">${__("Invoiced")}</th>
								<th class="text-right">${__("Remaining")}</th>
								<th>${__("Status")}</th>
							</tr></thead>
							<tbody>
								<tr><td class="doc-link">${link}</td><td>${p.supplier || ""}</td>
								<td class="text-right">${fmt(p.grand_total)}</td>
								<td class="text-right">${fmt(p.invoiced_amount)}</td>
								<td class="text-right">${fmt(p.remaining)}</td>
								<td>${p.status || ""}</td></tr>
							</tbody>
						</table>
						</div>
						${(paidItems.length || (p.items && p.items.length)) ? `
						<div class="po-items-toggle" data-target="${paidId}" data-expanded="false">
							<span class="toggle-icon">▼</span> ${__("Paid")} (${__("Invoiced")})
						</div>
						<div class="po-items-collapse collapse" id="${paidId}"></div>
						<div class="po-items-toggle" data-target="${remainId}" data-expanded="false">
							<span class="toggle-icon">▼</span> ${__("Remaining")}
						</div>
						<div class="po-items-collapse collapse" id="${remainId}"></div>
						` : ""}
						${hasInvoices ? `
						<div class="po-items-toggle" data-target="${invoicesId}" data-expanded="false">
							<span class="toggle-icon">▼</span> ${__("Purchase Invoices")}
						</div>
						<div class="po-items-collapse collapse" id="${invoicesId}"></div>
						` : ""}
					</div>
				`);
				content.append(poBlock);
				if (paidItems.length) {
					let html = '<div class="table-responsive"><table class="summary-table po-item-table"><thead><tr><th>' + __("Item") + '</th><th class="text-right">' + __("Ordered Qty") + '</th><th class="text-right">' + __("Received Qty") + '</th><th class="text-right">' + __("Invoiced") + '</th></tr></thead><tbody>';
					paidItems.forEach((it) => {
						const label = escapeHtml(it.item_name || it.item_code || "");
						html += '<tr><td>' + label + '</td><td class="text-right">' + flt(it.qty) + '</td><td class="text-right">' + flt(it.received_qty) + '</td><td class="text-right">' + fmt(it.billed_amt) + '</td></tr>';
					});
					html += "</tbody></table></div>";
					poBlock.find("[id='" + paidId + "']").append(html);
				}
				if (p.items && p.items.length) {
					const showRemainItems = remainItems.length ? remainItems : p.items;
					let html = '<div class="table-responsive"><table class="summary-table po-item-table"><thead><tr><th>' + __("Item") + '</th><th class="text-right">' + __("Ordered Qty") + '</th><th class="text-right">' + __("Received Qty") + '</th><th class="text-right">' + __("Remaining") + '</th></tr></thead><tbody>';
					showRemainItems.forEach((it) => {
						const label = escapeHtml(it.item_name || it.item_code || "");
						html += '<tr><td>' + label + '</td><td class="text-right">' + flt(it.qty) + '</td><td class="text-right">' + flt(it.received_qty) + '</td><td class="text-right">' + fmt(it.remaining_amt) + '</td></tr>';
					});
					html += "</tbody></table></div>";
					poBlock.find("[id='" + remainId + "']").append(html);
				}
				if (hasInvoices) {
					let html = '<div class="table-responsive"><table class="summary-table po-item-table"><thead><tr><th>' + __("Purchase Invoice") + '</th><th>' + __("Posting Date") + '</th><th>' + __("Supplier") + '</th><th class="text-right">' + __("Grand Total") + '</th><th class="text-right">' + __("Paid") + '</th><th class="text-right">' + __("Remaining") + '</th></tr></thead><tbody>';
					(p.invoices || []).forEach((inv) => {
						const piLink = frappe.utils.get_form_link("Purchase Invoice", inv.name, true);
						html += '<tr><td class="doc-link">' + piLink + '</td><td>' + (inv.posting_date || "") + '</td><td>' + escapeHtml(inv.supplier_name || inv.supplier || "") + '</td><td class="text-right">' + fmt(inv.grand_total) + '</td><td class="text-right">' + fmt(inv.paid_amount) + '</td><td class="text-right">' + fmt(inv.outstanding_amount) + '</td></tr>';
					});
					html += "</tbody></table></div>";
					poBlock.find("[id='" + invoicesId + "']").append(html);
				}
				poBlock.find(".po-items-toggle").on("click", function() {
					const $tog = $(this);
					const target = $tog.attr("data-target");
					const expanded = $tog.attr("data-expanded") === "true";
					const $col = poBlock.find("[id='" + target + "']");
					if (expanded) {
						$col.addClass("collapse");
						$tog.find(".toggle-icon").text("▼");
						$tog.attr("data-expanded", "false");
					} else {
						$col.removeClass("collapse");
						$tog.find(".toggle-icon").text("▲");
						$tog.attr("data-expanded", "true");
					}
				});
			});
		} else {
			let html = '<div class="table-responsive"><table class="summary-table"><thead><tr><th>' + __("Name") + '</th><th>' + __("Supplier") + '</th><th class="text-right">' + __("Grand Total") + '</th><th class="text-right">' + __("Invoiced") + '</th><th class="text-right">' + __("Remaining") + '</th><th>' + __("Status") + '</th></tr></thead><tbody>';
			poData.forEach((p) => {
				const name = p.po_name || p.name;
				const link = frappe.utils.get_form_link("Purchase Order", name, true);
				html += '<tr><td class="doc-link">' + link + '</td><td>' + (p.supplier || "") + '</td><td class="text-right">' + fmt(p.grand_total) + '</td><td class="text-right">' + fmt(p.invoiced_amount) + '</td><td class="text-right">' + fmt(p.remaining) + '</td><td>' + (p.status || "") + '</td></tr>';
			});
			html += "</tbody></table></div>";
			content.append($(html));
		}
		section.find(".active-po-section-toggle").on("click", function() {
			const $toggle = $(this);
			const expanded = $toggle.attr("data-expanded") === "true";
			if (expanded) {
				content.addClass("collapse");
				$toggle.find(".toggle-icon").text("▼");
				$toggle.attr("data-expanded", "false");
			} else {
				content.removeClass("collapse");
				$toggle.find(".toggle-icon").text("▲");
				$toggle.attr("data-expanded", "true");
			}
		});
		return section;
	},
});
