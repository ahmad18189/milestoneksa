// milestoneksa/public/js/employee_contract_end_date.js
// Auto-set Contract End Date from Date of Joining (+1 year, rolled forward if past).

function mksa_compute_contract_end_date(date_of_joining) {
	if (!date_of_joining) {
		return null;
	}

	let contract_end = moment(date_of_joining).add(1, "year").format("YYYY-MM-DD");
	const today = frappe.datetime.get_today();

	while (contract_end < today) {
		contract_end = moment(contract_end).add(1, "year").format("YYYY-MM-DD");
	}

	return contract_end;
}

frappe.ui.form.on("Employee", {
	date_of_joining(frm) {
		if (!frm.doc.date_of_joining || frm.doc.contract_end_date) {
			return;
		}

		frm.set_value(
			"contract_end_date",
			mksa_compute_contract_end_date(frm.doc.date_of_joining)
		);
	},
});
