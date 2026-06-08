frappe.ui.form.on("HR Settings", {
	mksa_send_attendance_test_email(frm) {
		const test_email = (frm.doc.mksa_attendance_test_email || "").trim();
		const report_type = frm.doc.mksa_attendance_test_report_type;

		if (!test_email) {
			frappe.msgprint({
				title: __("تنبيه"),
				message: __("يرجى إدخال بريد الاختبار."),
				indicator: "orange",
			});
			return;
		}

		if (!report_type) {
			frappe.msgprint({
				title: __("تنبيه"),
				message: __("يرجى اختيار نوع التقرير."),
				indicator: "orange",
			});
			return;
		}

		frappe.call({
			method: "milestoneksa.tasks.attendance_email_reports.send_test_attendance_email",
			args: {
				test_email,
				report_type,
			},
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
