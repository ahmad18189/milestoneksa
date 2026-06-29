frappe.ui.form.on("HR Settings", {
	mksa_send_contract_alert_test_email(frm) {
		frappe.call({
			method: "milestoneksa.tasks.contract_expiry_alerts.send_test_contract_expiry_email",
			freeze: true,
			freeze_message: __("جاري إرسال بريد الاختبار..."),
			callback(r) {
				if (r.exc) return;
				frappe.show_alert({
					message: r.message?.message || __("تم إرسال بريد الاختبار."),
					indicator: "green",
				});
			},
		});
	},
});
