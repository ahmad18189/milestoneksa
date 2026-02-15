/* File: milestoneksa/public/js/employee_custody_ui.js */
/* global frappe, $ */

function is_hr() {
	// Allow HR User, HR Manager, or System Manager to manage custody
	return frappe.user.has_role('HR Manager') || frappe.user.has_role('HR User') || frappe.user.has_role('System Manager');
}

async function fetch_assigned(employee) {
	try {
		const r = await frappe.call({
			method: 'milestoneksa.milestoneksa.doctype.employee_custody.employee_custody.list_assigned_for_employee',
			args: { employee }
		});
		return r.message || [];
	} catch (e) {
		console.error('Failed to fetch assigned custodies:', e);
		return [];
	}
}

function render_dashboard(frm, list) {
	const can_manage = is_hr();

	// Ensure the HTML field exists
	if (!frm.fields_dict.custody_dashboard) return;

	const wrap = $(frm.get_field('custody_dashboard').wrapper);
	// Clear previous content & handlers (namespace to avoid nuking others)
	wrap.off('.mksa').empty();

	const header = `
		<div class="flex items-center justify-between" style="margin-bottom:8px;">
			<h4 style="margin:0;">${__('Assigned Custody')}</h4>
			${can_manage ? `<button class="btn btn-xs btn-primary" id="mksa-assign-custody">${__('Assign Custody')}</button>` : ``}
		</div>
	`;

	let body = '';
	if (!list.length) {
		body = `<div class="text-muted">${__('No assigned custody.')}</div>`;
	} else {
		body = list.map(row => {
			const name = frappe.utils.escape_html(row.name || '');
			const title = frappe.utils.escape_html(row.custody_name || row.name || '');
			const asset = row.asset ? `Asset: <b>${frappe.utils.escape_html(row.asset)}</b>` : null;
			const item = row.item_code ? `Item: <b>${frappe.utils.escape_html(row.item_code)}</b>` : null;
			const sn = row.serial_no ? `SN: <b>${frappe.utils.escape_html(row.serial_no)}</b>` : null;
			const since = row.last_activity_date ? `${__('Since')}: ${frappe.datetime.str_to_user(row.last_activity_date)}` : null;
			const meta = [asset, item, sn, since].filter(Boolean).join(' &middot; ');

			const viewBtn = `<button class="btn btn-xs btn-secondary mksa-view" data-name="${name}">${__('View')}</button>`;
			const returnBtn = can_manage
				? `<button class="btn btn-xs btn-default mksa-return" data-custody="${name}">${__('Return')}</button>`
				: ``;

			return `
				<div class="card" style="padding:10px; margin-bottom:8px;">
					<div class="flex items-center justify-between">
						<div>
							<div>
								<a href="#" class="mksa-link" data-name="${name}">
									<b>${title}</b>
								</a>
							</div>
							<div class="text-muted" style="font-size:12px;">${meta || ''}</div>
						</div>
						<div class="flex gap-2">
							${viewBtn}
							${returnBtn}
						</div>
					</div>
				</div>
			`;
		}).join('');
	}

	wrap.append(header + body);

	// Open link (title click)
	wrap.on('click.mksa', 'a.mksa-link', function (e) {
		e.preventDefault();
		const name = $(this).data('name');
		if (name) frappe.set_route('Form', 'Employee Custody', name);
	});

	// Explicit "View" button
	wrap.on('click.mksa', 'button.mksa-view', function () {
		const name = $(this).data('name');
		if (name) frappe.set_route('Form', 'Employee Custody', name);
	});

	// "Assign Custody" (HR only)
	if (can_manage) {
		wrap.on('click.mksa', '#mksa-assign-custody', async () => {
			const d = new frappe.ui.Dialog({
				title: __('Assign Custody'),
				fields: [
					{
						fieldname: 'custody', label: __('Custody'), fieldtype: 'Link', options: 'Employee Custody', reqd: 1,
						get_query: () => ({ filters: { status: 'Available' } })
					},
					{ fieldname: 'note', label: __('Note'), fieldtype: 'Small Text' },
					{ fieldname: 'transaction_datetime', label: __('Date/Time'), fieldtype: 'Datetime', default: frappe.datetime.now_datetime(), reqd: 1 },
				],
				primary_action_label: __('Assign'),
				primary_action: async (v) => {
					try {
						await frappe.call({
							method: 'milestoneksa.milestoneksa.doctype.employee_custody.employee_custody.assign_available_to_employee',
							args: {
								custody: v.custody,
								employee: frm.doc.name,
								transaction_datetime: v.transaction_datetime,
								note: v.note
							}
						});
						d.hide();
						await frm.reload_doc();
					} catch (e) {
						console.error('Assign failed', e);
						frappe.msgprint({ message: __('Failed to assign custody'), indicator: 'red' });
					}
				}
			});
			d.show();
		});

		// "Return" button per card
		wrap.on('click.mksa', 'button.mksa-return', function () {
			const custody = $(this).data('custody');
			const d = new frappe.ui.Dialog({
				title: __('Return Custody'),
				fields: [
					{ fieldname: 'transaction_datetime', label: __('Date/Time'), fieldtype: 'Datetime', default: frappe.datetime.now_datetime(), reqd: 1 },
					{ fieldname: 'note', label: __('Note'), fieldtype: 'Small Text' },
				],
				primary_action_label: __('Return'),
				primary_action: async (v) => {
					try {
						await frappe.call({
							method: 'milestoneksa.milestoneksa.doctype.employee_custody.employee_custody.return_assigned_custody',
							args: {
								custody,
								transaction_datetime: v.transaction_datetime,
								note: v.note
							}
						});
						d.hide();
						await frm.reload_doc();
					} catch (e) {
						console.error('Return failed', e);
						frappe.msgprint({ message: __('Failed to return custody'), indicator: 'red' });
					}
				}
			});
			d.show();
		});
	}
}

frappe.ui.form.on('Employee', {
	async refresh(frm) {
		if (!frm.doc || !frm.doc.name) return;
		if (!frm.fields_dict.custody_dashboard) return;

		const list = await fetch_assigned(frm.doc.name);
		render_dashboard(frm, list);
	}
});
