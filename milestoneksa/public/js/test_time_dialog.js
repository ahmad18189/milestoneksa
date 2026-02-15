// Minimal: dialog with a single HTML field, live time text.
// Usage (console): frappe.ui.toolbar.test_time_htmlfield()

frappe.provide("frappe.ui.toolbar");

frappe.ui.toolbar.test_time_htmlfield = function () {
	// singleton
	if (frappe.ui.toolbar._test_time_htmlfield) {
		frappe.ui.toolbar._test_time_htmlfield.show();
		return;
	}

	const d = new frappe.ui.Dialog({
		title: __("HTML Render Test"),
		size: "small",
		fields: [{ fieldtype: "HTML", fieldname: "html" }],
		primary_action_label: __("Close"),
		primary_action: () => d.hide(),
	});

	frappe.ui.toolbar._test_time_htmlfield = d;
	d.show();

	// Put REAL HTML into the HTML field wrapper (not set_message)
	const $w = d.fields_dict.html.$wrapper;
	$w.html(`
		<div id="mksa-htest" class="p-3" style="display:flex;flex-direction:column;gap:12px;">
			<div>
				<div class="small text-muted">${__("Current Time (user format)")}</div>
				<div id="mksa-now" class="font-weight-bold"></div>
			</div>

			<div>
				<span class="badge badge-primary">${__("HTML OK")}</span>
				<span class="text-muted">${__("If you can see this badge and bold time, HTML isn’t escaped.")}</span>
			</div>

			<div>
				<button type="button" class="btn btn-sm btn-secondary" id="mksa-toggle-raw">${__("Show Raw HTML")}</button>
				<pre id="mksa-raw" class="mt-2 hide" style="white-space:pre-wrap;"></pre>
			</div>
		</div>
	`);

	const $now = $w.find("#mksa-now");
	const $raw = $w.find("#mksa-raw");
	const $btn = $w.find("#mksa-toggle-raw");

	function tick() {
		// Use Frappe's user formatting
		$now.text(frappe.datetime.str_to_user(frappe.datetime.now_datetime()));
	}
	tick();
	const timer = setInterval(tick, 1000);
	d.$wrapper.on("hidden.bs.modal", () => clearInterval(timer));

	$btn.on("click", () => {
		$raw.text($w.find("#mksa-htest").html()).toggleClass("hide");
	});
};
