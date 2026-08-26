/* global frappe */

(function () {
	// No sessionStorage guard: we want this to run on every Desk boot (i.e., every login).

	function escapeHtml(value) {
		return frappe.utils.escape_html(String(value == null ? "" : value));
	}

	function extractLegacyField(html, label) {
		const re = new RegExp(
			label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") +
				"\\s*:?</td>\\s*<td[^>]*>([\\s\\S]*?)</td>",
			"i"
		);
		const match = html.match(re);
		if (!match) return "";
		return frappe.utils.strip_html(match[1] || "").replace(/\s+/g, " ").trim();
	}

	function normalizePaymentApprovalMessage(rawMessage) {
		let message = rawMessage || "";
		message = message.replace(/<img[^>]*Riyal_Symbol\.svg[^>]*>/gi, " ");
		message = message.replace(/&lt;img[^&]*?Riyal_Symbol\.svg[^&]*?&gt;/gi, " ");

		// Already using compact template
		if (message.indexOf("par-announcement") !== -1) {
			return message
				.replace(/<div[^>]*class=["'][^"']*par-announcement__actions[^"']*["'][^>]*>[\s\S]*?<\/div>/gi, "")
				.replace(/<a[^>]*>\s*View\s*&amp;\s*Take\s*Action\s*<\/a>/gi, "")
				.replace(/<a[^>]*>\s*View\s*&\s*Take\s*Action\s*<\/a>/gi, "");
		}

		// Convert legacy inline HTML into compact card layout
		const statusMatch = message.match(/Status:\s*<\/strong>\s*([^<]+)/i) || message.match(/<strong>Status:<\/strong>\s*([^<]+)/i);
		const status = ((statusMatch && statusMatch[1]) || "").trim();
		const rows = [
			["Request ID", extractLegacyField(message, "Request ID")],
			["Employee", extractLegacyField(message, "Employee")],
			["Department", extractLegacyField(message, "Department")],
			["Application Date", extractLegacyField(message, "Application Date")],
			["Amount", extractLegacyField(message, "Amount")],
			["Priority", extractLegacyField(message, "Priority")],
			["Description", extractLegacyField(message, "Description")],
		].filter((row) => row[1]);

		if (!rows.length) {
			// Fallback: strip CTA and keep content, marked as legacy for CSS
			return `<div class="par-announcement-legacy">${message
				.replace(/<a[^>]*>\s*View\s*&amp;\s*Take\s*Action\s*<\/a>/gi, "")
				.replace(/<a[^>]*>\s*View\s*&\s*Take\s*Action\s*<\/a>/gi, "")
				.replace(/<p[^>]*>\s*<\/p>/gi, "")
				.replace(/<hr\s*\/?>\s*<hr\s*\/?>/gi, "<hr>")}</div>`;
		}

		const rowHtml = rows
			.map(
				([label, value]) => `
			<tr>
				<td class="par-announcement__label">${escapeHtml(label)}</td>
				<td class="par-announcement__value">${escapeHtml(value)}</td>
			</tr>`
			)
			.join("");

		return `
		<div class="par-announcement">
			<div class="par-announcement__header">
				<span class="par-announcement__icon" aria-hidden="true">&#128197;</span>
				${
					status
						? `<span class="par-announcement__badge par-announcement__badge--pending">${escapeHtml(
								status
						  )}</span>`
						: ""
				}
			</div>
			<p class="par-announcement__subtitle">${escapeHtml(
				__("Action required — please review and approve or reject.")
			)}</p>
			<div class="par-announcement__card">
				<table class="par-announcement__table">${rowHtml}</table>
			</div>
		</div>`;
	}

	function show_queue(items) {
		if (!items || !items.length) return;

		const next = () => {
			const it = items.shift();
			if (!it) return;

			const isPaymentApproval = (it.title || "").indexOf("Payment Approval Required") === 0;
			const d = new frappe.ui.Dialog({
				title: it.title || __("Announcement"),
				fields: [
					{ fieldtype: "HTML", fieldname: "msg_html" },
					{ fieldtype: "Check", fieldname: "dont_show", label: __("Do not show this again") },
				],
				primary_action_label: __("Close"),
				primary_action: async () => {
					try {
						const dont = !!d.get_value("dont_show");
						if (dont) {
							await frappe.call({
								method: "milestoneksa.milestoneksa.doctype.desk_announcement.desk_announcement.acknowledge",
								args: { announcement: it.name, action: "dismiss" },
							});
						} else if (it.show_policy === "Once") {
							await frappe.call({
								method: "milestoneksa.milestoneksa.doctype.desk_announcement.desk_announcement.acknowledge",
								args: { announcement: it.name, action: "seen" },
							});
						}
					} catch (e) {
						console.warn("Announcement acknowledge failed:", e);
					} finally {
						d.hide();
						next();
					}
				},
				secondary_action_label: it.link_url ? __("Open Link") : null,
				secondary_action: () => {
					if (it.link_url) window.open(it.link_url, "_blank", "noopener");
				},
			});

			let message = it.message || "";
			if (isPaymentApproval) {
				message = normalizePaymentApprovalMessage(message);
			}
			d.get_field("msg_html").$wrapper.html(`<div class="ql-editor">${message}</div>`);

			if (it.show_policy === "Once") {
				d.get_field("dont_show").$wrapper.hide();
			}

			if (isPaymentApproval && d.$wrapper) {
				d.$wrapper.addClass("desk-announcement--payment-approval");
				d.$wrapper.find(".par-announcement__actions").remove();
				d.$wrapper.find("a").filter(function () {
					return /view\s*&\s*take\s*action/i.test($(this).text());
				}).closest("p").addBack().remove();
			}

			d.show();
		};

		next();
	}

	const boot_items = (frappe.boot && frappe.boot.desk_announcements) || [];
	if (boot_items.length) {
		show_queue(boot_items.slice());
	} else {
		frappe
			.call("milestoneksa.milestoneksa.doctype.desk_announcement.desk_announcement.get_pending_announcements")
			.then((r) => show_queue((r && r.message) || []))
			.catch((e) => console.warn("Announcements fetch failed:", e));
	}
})();
