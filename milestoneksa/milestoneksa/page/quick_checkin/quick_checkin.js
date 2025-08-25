// milestoneksa/milestoneksa/page/quick_checkin/quick_checkin.js
frappe.provide('milestoneksa.quick_checkin');

frappe.pages['quick-checkin'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Quick Check-in'),
		single_column: true
	});

	// ---------- Helpers ----------
	const pad = (n) => String(n).padStart(2, '0');
	const ymd = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
	const firstOfMonth = (d) => new Date(d.getFullYear(), d.getMonth(), 1);
	const lastOfMonth  = (d) => new Date(d.getFullYear(), d.getMonth() + 1, 0);
	const fmtUser = (ts) => (ts ? frappe.datetime.str_to_user(ts) : __('—'));
	const isFiniteNum = (v) => typeof v === 'number' && isFinite(v);

	function hhmm_since(dtStr) {
		if (!dtStr) return '';
		const start = new Date(dtStr.replace(' ', 'T'));
		const now = new Date();
		if (isNaN(start.getTime()) || now <= start) return '';
		let mins = Math.floor((now - start) / 60000);
		const h = Math.floor(mins / 60);
		const m = mins % 60;
		return `${pad(h)}:${pad(m)}`;
	}

	// Cache last good fix (24h)
	const LAST_LOC_KEY = 'mksa:last_loc';
	function saveLastLoc(lat, lng) {
		try { localStorage.setItem(LAST_LOC_KEY, JSON.stringify({ lat, lng, ts: Date.now() })); } catch {}
	}
	function readLastLoc(maxAgeMs = 24 * 60 * 60 * 1000) {
		try {
			const raw = localStorage.getItem(LAST_LOC_KEY);
			if (!raw) return null;
			const obj = JSON.parse(raw);
			if (!isFiniteNum(obj?.lat) || !isFiniteNum(obj?.lng) || typeof obj.ts !== 'number') return null;
			if (Date.now() - obj.ts > maxAgeMs) return null;
			return obj;
		} catch { return null; }
	}

	// Robust geolocation: brief watch → getCurrentPosition variants → accept cached device fix
	function getPositionRobust() {
		return new Promise((resolve, reject) => {
			if (!navigator.geolocation) {
				reject(new Error(__('Geolocation API not available in this browser.')));
				return;
			}
			const tries = [
				'watch-hi', 'watch-low',
				{ enableHighAccuracy: true,  timeout: 12000, maximumAge: 0 },
				{ enableHighAccuracy: false, timeout: 12000, maximumAge: 60000 },
				{ enableHighAccuracy: false, timeout: 8000,  maximumAge: 24 * 60 * 60 * 1000 },
			];

			function next() {
				if (!tries.length) return reject(new Error(__('Location unavailable after multiple attempts.')));
				const mode = tries.shift();

				if (mode === 'watch-hi' || mode === 'watch-low') {
					const opts = { enableHighAccuracy: mode === 'watch-hi', timeout: 10000, maximumAge: 0 };
					const id = navigator.geolocation.watchPosition(
						(p) => { navigator.geolocation.clearWatch(id); resolve({ lat: p.coords.latitude, lng: p.coords.longitude }); },
						(e) => { navigator.geolocation.clearWatch(id); if (e && e.code === 1) reject(e); else next(); },
						opts
					);
					setTimeout(() => navigator.geolocation.clearWatch(id), opts.timeout + 1500);
					return;
				}

				navigator.geolocation.getCurrentPosition(
					(p) => resolve({ lat: p.coords.latitude, lng: p.coords.longitude }),
					(e) => { if (e && e.code === 1) reject(e); else next(); },
					mode
				);
			}
			next();
		});
	}

	// Helper to style + set pill text
	function setPill($el, variant, text) {
		$el
			.removeClass('pill--neutral pill--info pill--success pill--warning pill--danger')
			.addClass(`pill--${variant}`)
			.text(text);
	}

	// ---------- UI ----------
	const now = new Date();
	const defFrom = firstOfMonth(now);
	const defTo   = lastOfMonth(now);

	const $container = $(`
		<div class="mksa-qc box" data-theme="light">
			<style>
				/* Base: bright light mode */
				.mksa-qc { background: transparent; }
				.mksa-qc .row { display:flex; gap:16px; flex-wrap:wrap; }
				.mksa-qc .col { flex:1 1 360px; min-width:300px; }
				.mksa-qc .card {
					border:1px solid #e5e7eb;
					border-radius:14px;
					background:#ffffff;
					box-shadow: 0 8px 24px rgba(2, 8, 20, 0.06);
					padding:16px;
				}
				.mksa-qc .title { font-weight:800; font-size:16px; color:#0f172a; margin-bottom:10px; letter-spacing:.1px; }
				.mksa-qc .muted { color:#64748b; font-size:12px; }

				/* Bright pill styles (light) */
				.mksa-qc .pill{
					--pill-bg:#F8FAFC; --pill-fg:#0F172A; --pill-border:#E2E8F0;
					display:inline-flex; align-items:center; justify-content:center;
					padding:6px 12px; border-radius:999px;
					font-size:12px; font-weight:700;
					background:var(--pill-bg); color:var(--pill-fg); border:1px solid var(--pill-border);
					letter-spacing:.2px;
				}
				.mksa-qc .pill--neutral{ --pill-bg:#F8FAFC; --pill-fg:#0F172A; --pill-border:#E2E8F0; }
				.mksa-qc .pill--info   { --pill-bg:#E0EAFF; --pill-fg:#1E3A8A; --pill-border:#93C5FD; }
				.mksa-qc .pill--success{ --pill-bg:#D1FAE5; --pill-fg:#065F46; --pill-border:#34D399; }
				.mksa-qc .pill--warning{ --pill-bg:#FEF3C7; --pill-fg:#92400E; --pill-border:#FBBF24; }
				.mksa-qc .pill--danger { --pill-bg:#FEE2E2; --pill-fg:#991B1B; --pill-border:#FCA5A5; }

				.mksa-qc .btn-lg { padding:12px 14px; font-size:14px; font-weight:700; }
				.mksa-map {
					border:4px solid #e5e7eb; border-radius:12px; overflow:hidden;
					width:100%; height:220px;
				}
				.mksa-qc .filters { display:flex; gap:10px; align-items:flex-end; flex-wrap:wrap; margin: 0 0 16px; }
				.mksa-qc .filters .group { display:flex; flex-direction:column; gap:6px; }
				.mksa-qc label { font-size:12px; color:#0f172a; font-weight:700; letter-spacing:.2px; }
				.mksa-qc input[type="date"] {
					padding:8px 10px; border:1px solid #e2e8f0; border-radius:10px; color:#0f172a;
					background:#ffffff; box-shadow: 0 1px 2px rgba(2,8,20,.04) inset;
				}
				.mksa-qc .btn-default { background:#f8fafc; border:1px solid #e2e8f0; color:#0f172a; }
				.mksa-qc .btn-default:hover { background:#eef2f7; }

				/* Dark mode (only when data-theme="dark") */
				.mksa-qc[data-theme="dark"] .card { background:#111827; border-color:#1f2937; box-shadow: 0 10px 24px rgba(0,0,0,.35); }
				.mksa-qc[data-theme="dark"] .title { color:#e5e7eb; }
				.mksa-qc[data-theme="dark"] .muted { color:#9ca3af; }
				.mksa-qc[data-theme="dark"] input[type="date"] { background:#0b1220; color:#e5e7eb; border-color:#374151; }
				.mksa-qc[data-theme="dark"] .btn-default { background:#0b1220; border-color:#374151; color:#e5e7eb; }
				.mksa-qc[data-theme="dark"] .btn-default:hover { background:#0f172a; }
				.mksa-qc[data-theme="dark"] .pill--neutral{ --pill-bg:#1F2937; --pill-fg:#E5E7EB; --pill-border:#374151; }
				.mksa-qc[data-theme="dark"] .pill--info   { --pill-bg:#1E1B4B; --pill-fg:#C7D2FE; --pill-border:#3730A3; }
				.mksa-qc[data-theme="dark"] .pill--success{ --pill-bg:#052E2B; --pill-fg:#A7F3D0; --pill-border:#065F46; }
				.mksa-qc[data-theme="dark"] .pill--warning{ --pill-bg:#3B2F0B; --pill-fg:#FDE68A; --pill-border:#92400E; }
				.mksa-qc[data-theme="dark"] .pill--danger { --pill-bg:#3B0D0C; --pill-fg:#FECACA; --pill-border:#991B1B; }

				@media (max-width: 480px){
					.mksa-qc .col { min-width: 100%; }
				}
			</style>

			<div class="filters">
				<div class="group">
					<label>${__('From')}</label>
					<input type="date" data-from />
				</div>
				<div class="group">
					<label>${__('To')}</label>
					<input type="date" data-to />
				</div>
				<button class="btn btn-default" data-apply>${__('Apply')}</button>
				<button class="btn btn-default" data-theme-toggle>${__('Switch Theme')}</button>
			</div>

			<div class="row">
				<div class="col">
					<div class="card">
						<div class="title">${__('Welcome')}</div>
						<div class="muted" data-emp></div>

						<div style="height:8px"></div>
						<div class="muted">${__('Last Log')}</div>
						<div><span class="pill pill--neutral" data-last>—</span></div>

						<div style="height:8px"></div>
						<div class="muted">${__('Last Check-In')}</div>
						<div><span class="pill pill--neutral" data-last-in>—</span></div>

						<div style="height:8px"></div>
						<div class="muted">${__('If checking out now')}</div>
						<div><span class="pill pill--neutral" data-today-total>—</span></div>

						<div style="height:12px"></div>
						<button class="btn btn-primary btn-lg" data-check>${__('Check In')}</button>
					</div>
				</div>

				<div class="col">
					<div class="card">
						<div class="title">${__('Location Preview')}</div>
						<div class="muted" data-loc-status>${__('Click “Refresh Location” to attach your current location')}</div>
						<div style="height:8px"></div>
						<div class="mksa-map">
							<iframe data-map width="100%" height="100%" frameborder="0" style="border:0"></iframe>
						</div>
						<div style="height:8px"></div>
						<button class="btn btn-default" data-refresh-loc>${__('Refresh Location')}</button>
					</div>
				</div>
			</div>
		</div>
	`).appendTo(page.body);

	// Elements
	const $from = $container.find('[data-from]');
	const $to   = $container.find('[data-to]');
	const $apply= $container.find('[data-apply]');
	const $btnTheme = $container.find('[data-theme-toggle]');

	const $emp  = $container.find('[data-emp]');
	const $last = $container.find('[data-last]');
	const $lastIn = $container.find('[data-last-in]');
	const $todayTotal = $container.find('[data-today-total]');

	const $btnCheck  = $container.find('[data-check]');
	const $map  = $container.find('[data-map]');
	const $loc  = $container.find('[data-loc-status]');
	const $btnRefreshLoc = $container.find('[data-refresh-loc]');

	// Theme toggle (Light default)
	const THEME_KEY = 'mksa:theme_mode';
	let themeMode = localStorage.getItem(THEME_KEY);
	if (themeMode !== 'dark' && themeMode !== 'light') {
		themeMode = 'light'; // default
	}
	function applyTheme() {
		$container.attr('data-theme', themeMode);
		$btnTheme.text(themeMode === 'light' ? __('Switch to Dark') : __('Switch to Light'));
	}
	function toggleTheme() {
		themeMode = (themeMode === 'light') ? 'dark' : 'light';
		localStorage.setItem(THEME_KEY, themeMode);
		applyTheme();
	}
	applyTheme();
	$btnTheme.on('click', toggleTheme);

	// Set default filters to current month
	$from.val(ymd(defFrom));
	$to.val(ymd(defTo));

	// If "From" changes, move "To" to end of that month
	$from.on('change', () => {
		const f = new Date($from.val());
		if (!isNaN(f.getTime())) {
			$to.val(ymd(lastOfMonth(f)));
		}
	});

	// State
	let state = {
		next_action: 'IN',
		employee: null,
		latitude: null,
		longitude: null,
		last: null,
		last_in: null
	};

	// Map helper
	function setMap(lat, lng) {
		if (isFiniteNum(lat) && isFiniteNum(lng)) {
			$map.attr('src', `https://maps.google.com/maps?q=${lat},${lng}&hl=en&z=15&output=embed`);
		}
	}

	// Server helpers
	async function getLastIn(employee_name) {
		const r = await frappe.call({
			method: 'frappe.client.get_list',
			args: {
				doctype: 'Employee Checkin',
				fields: ['name','time','log_type'],
				filters: { employee: employee_name, log_type: 'IN' },
				order_by: 'time desc',
				limit_page_length: 1
			}
		});
		return (r?.message && r.message[0]) || null;
	}

	function updateTodayTotalPreview() {
		// only when next action is OUT and the last IN is today
		if (state.next_action !== 'OUT' || !state.last_in) {
			return setPill($todayTotal, 'neutral', '—');
		}
		const inTime = state.last_in.time;
		const inDate = inTime?.split(' ')?.[0];
		const todayStr = ymd(new Date());
		if (inDate !== todayStr) {
			return setPill($todayTotal, 'neutral', '—');
		}
		const hhmm = hhmm_since(inTime);
		setPill($todayTotal, hhmm ? 'info' : 'neutral',
			hhmm ? __('Worked today: {0}', [hhmm]) : '—');
	}

	async function refreshState() {
		const filters = { from_date: $from.val(), to_date: $to.val() }; // reserved for server, if used

		const r = await frappe.call('milestoneksa.api.quick_checkin.get_next_action', { filters });
		const data = r.message || {};

		state.next_action = data.next_action || 'IN';
		state.employee = data.employee || null;
		state.last = data.last || null;

		$emp.text(state.employee ? state.employee.employee_name : '');

		const label = state.next_action === 'IN' ? __('Check In') : __('Check Out');
		$btnCheck.text(label);

		// Last log pill
		const lastLabel = state.last
			? (state.last.log_type === 'IN'
				? __('Last check-in: {0}', [fmtUser(state.last.time)])
				: __('Last check-out: {0}', [fmtUser(state.last.time)]))
			: __('No previous logs');
		const lastVariant = state.last ? (state.last.log_type === 'IN' ? 'success' : 'warning') : 'neutral';
		setPill($last, lastVariant, lastLabel);

		// Last IN pill
		state.last_in = state.employee ? await getLastIn(state.employee.name) : null;
		const lastInText = state.last_in ? __('Last check-in: {0}', [fmtUser(state.last_in.time)]) : '—';
		setPill($lastIn, state.last_in ? 'info' : 'neutral', lastInText);

		// Today total preview
		updateTodayTotalPreview();
	}

	async function fetchLocationAndPreview() {
		$loc.text(__('Locating…'));
		try {
			const pos = await getPositionRobust();
			state.latitude  = +pos.lat;
			state.longitude = +pos.lng;
			saveLastLoc(state.latitude, state.longitude);
			$loc.text([
				__('Latitude: {0}°',  [Number(state.latitude).toFixed(5)]),
				__('Longitude: {0}°', [Number(state.longitude).toFixed(5)])
			].join(', '));
			setMap(state.latitude, state.longitude);
		} catch (err) {
			const cached = readLastLoc();
			if (cached) {
				state.latitude = +cached.lat;
				state.longitude = +cached.lng;
				$loc.text(__('Using cached location'));
				setMap(state.latitude, state.longitude);
			} else {
				$loc.text(__('Unable to retrieve your location: ERROR({0}): {1}', [err?.code ?? '?', err?.message || __('Unknown')]));
			}
		}
	}

	async function submitCheck() {
		// Try best-effort location (but do NOT block if unavailable)
		try {
			const pos = await getPositionRobust();
			state.latitude  = +pos.lat;
			state.longitude = +pos.lng;
			saveLastLoc(state.latitude, state.longitude);
		} catch (_) {
			// keep nulls if not available
		}

		let geoj = null;
		if (isFiniteNum(state.latitude) && isFiniteNum(state.longitude)) {
			geoj = JSON.stringify({
				type: 'FeatureCollection',
				features: [{ type:'Feature', properties:{}, geometry:{ type:'Point', coordinates:[state.longitude, state.latitude] } }]
			});
		}

		const label = state.next_action === 'IN' ? __('Check-in') : __('Check-out');

		try {
			await frappe.call({
				method: 'milestoneksa.api.quick_checkin.quick_checkin',
				args: {
					log_type: state.next_action,
					latitude: state.latitude,
					longitude: state.longitude,
					geolocation: geoj
				},
				freeze: true,
				freeze_message: __('Recording…'),
			});
			frappe.show_alert({ message: __('{0} recorded', [label]), indicator: 'green' });

			// Refresh UI
			await refreshState();

			// Update map/status if we have coords now
			if (isFiniteNum(state.latitude) && isFiniteNum(state.longitude)) {
				$loc.text([
					__('Latitude: {0}°',  [Number(state.latitude).toFixed(5)]),
					__('Longitude: {0}°', [Number(state.longitude).toFixed(5)])
				].join(', '));
				setMap(state.latitude, state.longitude);
			}
		} catch (e) {
			frappe.msgprint({ title: __('Error'), message: e?.message || __('Failed'), indicator: 'red' });
		}
	}

	// Events
	$apply.on('click', () => refreshState());
	$btnRefreshLoc.on('click', () => fetchLocationAndPreview());
	$btnCheck.on('click', () => submitCheck());

	// Init
	refreshState();
};
