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
			}, __("Actions"));
		}
		frm.events.render_financial_summary(frm);
	},
	after_save(frm) {
		frm.events.render_financial_summary(frm);
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
				content.append(frm.events.render_supplier_payments_section(frm, msg.supplier_payments_unallocated_unreconciled || []));
				content.append(frm.events.render_costs_section(frm, msg.costs));
				content.append(frm.events.render_income_section(frm, msg.income));
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
				<div class="kpi-label">${__("Project Total Cost")}</div>
				<div class="kpi-value">${fmt(payment_summary.project_total_cost)}</div>
			</div>
		`);
		section.append(kpi);
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
		const section = $(`<div class="summary-section"><h5>${__("Active Purchase Orders")} (${__("Contract with supplier")})</h5></div>`);
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
		if (hasItems) {
			poData.forEach((p, idx) => {
				const link = frappe.utils.get_form_link("Purchase Order", p.po_name, true);
				const safeId = "po-" + idx;
				const paidId = "po-paid-" + safeId;
				const remainId = "po-remain-" + safeId;
				const paidItems = (p.items || []).filter((it) => flt(it.billed_amt) > 0);
				const remainItems = (p.items || []).filter((it) => flt(it.remaining_amt, 2) > 0);
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
					</div>
				`);
				section.append(poBlock);
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
			section.append($(html));
		}
		return section;
	},
});
