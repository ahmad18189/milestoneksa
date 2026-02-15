/* global frappe */

(function () {
	// No sessionStorage guard: we want this to run on every Desk boot (i.e., every login).

	function show_queue(items) {
		if (!items || !items.length) return;

		const next = () => {
			const it = items.shift();
			if (!it) return;

			const d = new frappe.ui.Dialog({
				title: it.title || __("Announcement"),
				fields: [
					{ fieldtype: "HTML", fieldname: "msg_html" },
					{ fieldtype: "Check", fieldname: "dont_show", label: __("Do not show this again") }
				],
				primary_action_label: __("Close"),
				primary_action: async () => {
					try {
						const dont = !!d.get_value("dont_show");
						if (dont) {
							await frappe.call({
								method: "milestoneksa.milestoneksa.doctype.desk_announcement.desk_announcement.acknowledge",
								args: { announcement: it.name, action: "dismiss" }
							});
						} else if (it.show_policy === "Once") {
							await frappe.call({
								method: "milestoneksa.milestoneksa.doctype.desk_announcement.desk_announcement.acknowledge",
								args: { announcement: it.name, action: "seen" }
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
				}
			});

			// Render rich text body
			d.get_field("msg_html").$wrapper.html(`<div class="ql-editor">${it.message || ""}</div>`);

			// If policy is "Once", don't show the 'do not show again' checkbox
			if (it.show_policy === "Once") {
				d.get_field("dont_show").$wrapper.hide();
			}

			d.show();
		};

		next();
	}

	// Prefer server-provided announcements from boot (fresh every login)
	const boot_items = (frappe.boot && frappe.boot.desk_announcements) || [];
	if (boot_items.length) {
		// Use a shallow copy so we don't mutate bootinfo for debugging
		show_queue(boot_items.slice());
	} else {
		// Fallback: manual fetch (e.g., if boot hook was temporarily unavailable)
		frappe
			.call("milestoneksa.milestoneksa.doctype.desk_announcement.desk_announcement.get_pending_announcements")
			.then(r => show_queue((r && r.message) || []))
			.catch(e => console.warn("Announcements fetch failed:", e));
	}
})();
