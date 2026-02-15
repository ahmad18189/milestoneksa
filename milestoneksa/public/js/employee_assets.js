// File: milestoneksa/public/js/employee_assets.js

frappe.ui.form.on('Employee', {
	refresh(frm) {
		// Custom button
		frm.add_custom_button(__('Fetch Assets'), () => {
			fetch_and_render_assets(frm);
		}, __('Actions'));

		// Auto-load when opening a saved Employee
		if (!frm.is_new()) {
			fetch_and_render_assets(frm);
		}
	}
});

function fetch_and_render_assets(frm) {
	if (!frm.doc.name) {
		frappe.msgprint(__('Please save the Employee first.'));
		return;
	}
	frappe.call({
		method: 'milestoneksa.api.employee_assets.get_assets_for_employee',
		args: { employee: frm.doc.name },
		freeze: true,
		freeze_message: __('Loading assets…'),
		callback: (r) => {
			const data = r.message || [];
			render_assets_html(frm, data);
		}
	});
}

function render_assets_html(frm, assets) {
	const field = frm.get_field('custom_assets_html');
	if (!field || !field.$wrapper) return;
	field.$wrapper.html(build_assets_html(assets));
}

function build_assets_html(assets) {
	if (!assets || !assets.length) {
		return `
			<div class="mksa-empty" style="padding:12px;color:#6b7280;border:1px dashed #e5e7eb;border-radius:10px;background:#fafafa;">
				${__('No assets found for this Employee as Custodian.')}
			</div>
		`;
	}

	const rows = assets.map(a => asset_row(a)).join('');
	const count = assets.length;

	return `
		<style>
			/* Container */
			.mksa-box {
				border: 1px solid var(--border-color, #e5e7eb);
				border-radius: 12px;
				background: var(--surface, #ffffff);
				box-shadow: 0 1px 2px rgba(0,0,0,0.04);
				overflow: hidden;
			}
			/* Header */
			.mksa-head {
				display: flex; align-items: center; justify-content: space-between;
				padding: 10px 12px;
				background: var(--card-bg, #f8fafc);
				border-bottom: 1px solid var(--border-color, #e5e7eb);
			}
			.mksa-title { font-weight: 600; }
			.mksa-pill {
				min-width: 26px; height: 22px; padding: 0 8px;
				display:inline-flex; align-items:center; justify-content:center;
				border-radius: 999px; font-size: 12px; background: #eef2ff; color: #3730a3;
				border: 1px solid #e0e7ff;
			}

			/* Table wrapper with sticky header */
			.mksa-table-wrap { max-height: 380px; overflow: auto; }
			.mksa-table { width: 100%; border-collapse: separate; border-spacing: 0; }
			.mksa-table th, .mksa-table td { padding: 10px 12px; }
			.mksa-table thead th {
				position: sticky; top: 0; z-index: 1;
				background: #f3f4f6; border-bottom: 1px solid #e5e7eb; text-align: left; font-weight: 600;
			}
			.mksa-table tbody tr { transition: background 120ms ease; cursor: pointer; }
			.mksa-table tbody tr:nth-child(even) { background: #fcfcfd; }
			.mksa-table tbody tr:hover { background: #f1f5f9; }
			.mksa-cell-sub { color: #6b7280; font-size: 12px; margin-top: 2px; }

			/* Link style (kept subtle; whole row is clickable) */
			.mksa-asset-link { text-decoration: none; color: var(--text-color, #111827); font-weight: 600; }
			.mksa-code { color:#6b7280; }
		</style>

		<div class="mksa-box">
			<div class="mksa-head">
				<div class="mksa-title">${__('Assets (Custodian)')}</div>
				<div class="mksa-pill">${count}</div>
			</div>
			<div class="mksa-table-wrap">
				<table class="mksa-table">
					<thead>
						<tr>
							<th style="width:60%">${__('Asset')}</th>
							<th style="width:40%">${__('Code')}</th>
						</tr>
					</thead>
					<tbody>
						${rows}
					</tbody>
				</table>
			</div>
		</div>
	`;
}

function asset_row(a) {
	const label = frappe.utils.escape_html(a.asset_name || a.name);
	const code = frappe.utils.escape_html(a.name);
	const link = `/app/asset/${encodeURIComponent(a.name)}`;
	// Open via Desk routing when clicking row (smoother than new tab)
	const route = `frappe.set_route('Form','Asset','${frappe.utils.escape_html(a.name)}')`;

	return `
		<tr onclick="${route}">
			<td>
				<a href="${link}" class="mksa-asset-link" onclick="event.stopPropagation();">${label}</a>
				<div class="mksa-cell-sub">${__('Open Asset')}</div>
			</td>
			<td class="mksa-code">${code}</td>
		</tr>
	`;
}
