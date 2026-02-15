frappe.ui.form.on('Employee Custody', {
	refresh(frm) {
		// Status is computed server-side; lock it
		frm.set_df_property('status', 'read_only', 1);

		const last = frm.doc.status;

		// Add quick actions that append a transaction row then reload
		if (['Available', 'Returned'].includes(last)) {
			frm.add_custom_button(__('Assign to Employee'), () => {
				frappe.prompt([
					{ fieldname:'employee', label:'Employee', fieldtype:'Link', options:'Employee', reqd:1 },
					{ fieldname:'transaction_date', label:'Date', fieldtype:'Datetime', reqd:1, default: frappe.datetime.now_datetime() },
					{ fieldname:'note', label:'Note', fieldtype:'Small Text' },
				], (v) => {
					frm.call('add_assigned', v).then(() => frm.reload_doc());
				}, __('Add Transaction'), __('Add Assigned'));
			}, __('Actions'));
		}

		if (last === 'Assigned') {
			frm.add_custom_button(__('Return Custody'), () => {
				frappe.prompt([
					{ fieldname:'transaction_date', label:'Date', fieldtype:'Datetime', reqd:1, default: frappe.datetime.now_datetime() },
					{ fieldname:'note', label:'Note', fieldtype:'Small Text' },
				], (v) => {
					frm.call('add_returned', v).then(() => frm.reload_doc());
				}, __('Add Transaction'), __('Add Returned'));
			}, __('Actions'));
		}

		if (last !== 'Disabled') {
			frm.add_custom_button(__('Disable Custody'), () => {
				frappe.prompt([
					{ fieldname:'transaction_date', label:'Date', fieldtype:'Datetime', reqd:1, default: frappe.datetime.now_datetime() },
					{ fieldname:'note', label:'Note', fieldtype:'Small Text' },
				], (v) => {
					frm.call('add_disabled', v).then(() => frm.reload_doc());
				}, __('Add Transaction'), __('Add Disabled'));
			}, __('Actions'));
		}
	}
});
