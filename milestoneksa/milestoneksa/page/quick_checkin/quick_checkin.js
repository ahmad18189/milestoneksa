// milestoneksa/milestoneksa/page/quick_checkin/quick_checkin.js
frappe.provide('milestoneksa.quick_checkin');

frappe.pages['quick-checkin'].on_page_load = function (wrapper) {
  // load our modules first
  frappe.require([
    '/assets/milestoneksa/js/qc_utils.js',
    '/assets/milestoneksa/js/qc_geo.js',
    '/assets/milestoneksa/js/qc_api.js',
    '/assets/milestoneksa/js/qc_calendar.js',
  ], () => init_page(wrapper));
};

function init_page(wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: __('Quick Check-in'),
    single_column: true
  });

  const { ymd, firstOfMonth, lastOfMonth, fmtUser, isFiniteNum, hhmm_since, setPill, initTheme, applyTheme } = mksa.qc_utils;
  const { getPositionRobust, saveLastLoc, readLastLoc } = mksa.qc_geo;
  const { getNextAction, getLastIn, createCheckin, fetchAttendance } = mksa.qc_api;
  const { render: renderCalendar } = mksa.qc_calendar;

  // UI markup
  const $container = $(`
    <div class="mksa-qc box" data-theme="light">
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
            <div class="title">${__('Welcome')+' '+frappe.session.user_fullname}</div>
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

      <div class="row">
        <div class="col">
          <div class="card">
            <div class="title">${__('Attendance Calendar')}</div>
            <div class="muted" style="margin-bottom:8px;">${__('Based on Attendance records for the selected period')}</div>
            <div class="mksa-cal-legend">
				<span class="mksa-leg-item"><span class="mksa-leg-swatch" style="background:#e0f2fe; border-color:#0284c7;"></span> ${__('Present')}</span>
				<span class="mksa-leg-item"><span class="mksa-leg-swatch" style="background:#fee2e2; border-color:#ef4444;"></span> ${__('Absent')}</span>
				<span class="mksa-leg-item"><span class="mksa-leg-swatch" style="background:#dbeafe; border-color:#3b82f6;"></span> ${__('On Leave')}</span>
				<span class="mksa-leg-item"><span class="mksa-leg-swatch" style="background:#fed7aa; border-color:#f97316;"></span> ${__('Half Day')}</span>
				<span class="mksa-leg-item"><span class="mksa-leg-swatch" style="background:#c7d2fe; border-color:#1e3a8a;"></span> ${__('Work From Home')}</span>
				<span class="mksa-leg-item"><span class="mksa-leg-swatch" style="background:#f3f4f6; border-color:#cbd5e1;"></span> ${__('-')}</span>
				<span class="mksa-leg-item"><span class="mksa-leg-dot" style="background:#fde68a; outline:1px solid #f59e0b;"></span> ${__('Late Entry')}</span>
				<span class="mksa-leg-item"><span class="mksa-leg-dot" style="background:#fdba74; outline:1px solid #ea580c;"></span> ${__('Early Exit')}</span>
			</div>
            <div class="mksa-cal" data-cal></div>
          </div>
        </div>
      </div>
    </div>
  `).appendTo(page.body);

  // refs
  const $from = $container.find('[data-from]');
  const $to   = $container.find('[data-to]');
  const $apply = $container.find('[data-apply]');
  const $btnTheme = $container.find('[data-theme-toggle]');

  const $emp  = $container.find('[data-emp]');
  const $last = $container.find('[data-last]');
  const $lastIn = $container.find('[data-last-in]');
  const $todayTotal = $container.find('[data-today-total]');

  const $btnCheck = $container.find('[data-check]');
  const $map = $container.find('[data-map]');
  const $loc = $container.find('[data-loc-status]');
  const $btnRefreshLoc = $container.find('[data-refresh-loc]');
  const $cal = $container.find('[data-cal]');

  // theme (light default)
  let themeMode = initTheme($container);
  function updateThemeButton() {
    $btnTheme.text(themeMode === 'light' ? __('Switch to Dark') : __('Switch to Light'));
  }
  updateThemeButton();
  $btnTheme.on('click', () => {
    themeMode = (themeMode === 'light') ? 'dark' : 'light';
    applyTheme($container, themeMode);
    updateThemeButton();
  });

  // default filters (this month)
  const now = new Date();
  $from.val( ymd(firstOfMonth(now)) );
  $to.val( ymd(lastOfMonth(now)) );
  $from.on('change', () => {
    const f = new Date($from.val());
    if (!isNaN(f.getTime())) $to.val( ymd(lastOfMonth(f)) );
  });

  // local state
  const state = {
    next_action: 'IN',
    employee: null,
    last: null,
    last_in: null,
    latitude: null,
    longitude: null,
  };

  // helpers
  function setMap(lat, lng) {
    if (isFiniteNum(lat) && isFiniteNum(lng)) {
      $map.attr('src', `https://maps.google.com/maps?q=${lat},${lng}&hl=en&z=15&output=embed`);
    }
  }

  function updateTodayTotalPreview() {
    if (state.next_action !== 'OUT' || !state.last_in) return setPill($todayTotal, 'neutral', '—');
    const inTime = state.last_in.time;
    const inDate = inTime?.split(' ')?.[0];
    const todayStr = ymd(new Date());
    if (inDate !== todayStr) return setPill($todayTotal, 'neutral', '—');
    const hhmm = hhmm_since(inTime);
    setPill($todayTotal, hhmm ? 'info' : 'neutral', hhmm ? __('Worked today: {0}', [hhmm]) : '—');
  }
  function ensureQuickCheckinCSS() {
	const id = 'mksa-qc-css';
	if (document.getElementById(id)) return;

	// Prefer the built asset
	const href = '/assets/milestoneksa/css/quick_checkin.css?v=' + Date.now();

	const link = document.createElement('link');
	link.id = id;
	link.rel = 'stylesheet';
	link.href = href;
	document.head.appendChild(link);
  }
  ensureQuickCheckinCSS();

  async function refreshState() {
    const filters = { from_date: $from.val(), to_date: $to.val() };
    const data = await getNextAction(filters);

    state.next_action = data.next_action || 'IN';
    state.employee = data.employee || null;
    state.last = data.last || null;

    $emp.text(state.employee ? state.employee.employee_name : '');

    const label = state.next_action === 'IN' ? __('Check In') : __('Check Out');
    $btnCheck.text(label);

    const lastLabel = state.last
      ? (state.last.log_type === 'IN'
        ? __('Last check-in: {0}', [fmtUser(state.last.time)])
        : __('Last check-out: {0}', [fmtUser(state.last.time)]))
      : __('No previous logs');
    const lastVariant = state.last ? (state.last.log_type === 'IN' ? 'success' : 'warning') : 'neutral';
    setPill($last, lastVariant, lastLabel);

    state.last_in = state.employee ? await getLastIn(state.employee.name) : null;
    const lastInText = state.last_in ? __('Last check-in: {0}', [fmtUser(state.last_in.time)]) : '—';
    setPill($lastIn, state.last_in ? 'info' : 'neutral', lastInText);

    updateTodayTotalPreview();
  }

  async function loadCalendar() {
    const from_date = $from.val();
    const to_date   = $to.val();
    if (!from_date || !to_date || !state.employee?.name) {
      $cal.empty();
      return;
    }
    const records = await fetchAttendance(state.employee.name, from_date, to_date);
    renderCalendar($cal, records, from_date, to_date);
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
    // best-effort position (non-blocking)
    try {
      const pos = await getPositionRobust();
      state.latitude  = +pos.lat;
      state.longitude = +pos.lng;
      saveLastLoc(state.latitude, state.longitude);
    } catch (_) {}

    let geoj = null;
    if (isFiniteNum(state.latitude) && isFiniteNum(state.longitude)) {
      geoj = JSON.stringify({
        type: 'FeatureCollection',
        features: [{ type:'Feature', properties:{}, geometry:{ type:'Point', coordinates:[state.longitude, state.latitude] } }]
      });
    }

    const label = state.next_action === 'IN' ? __('Check-in') : __('Check-out');

    try {
      await createCheckin({
        log_type: state.next_action,
        latitude: state.latitude,
        longitude: state.longitude,
        geolocation: geoj
      });

      frappe.show_alert({ message: __('{0} recorded', [label]), indicator: 'green' });
      await refreshState();
      await loadCalendar();

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

  // events
  $apply.on('click', async () => { await refreshState(); await loadCalendar(); });
  $btnRefreshLoc.on('click', () => fetchLocationAndPreview());
  $btnCheck.on('click', () => submitCheck());
  // Click to open Attendance (Form if exists, else List filtered)
$cal.on('click', '.mksa-cal-day.is-clickable', function () {
const date = this.dataset.date;
const att  = this.dataset.att;
if (att) {
	frappe.set_route('Form', 'Attendance', att);
} else {
	frappe.route_options = { attendance_date: date };
	if (state.employee?.name) frappe.route_options.employee = state.employee.name;
	frappe.set_route('List', 'Attendance');
}
});


  // init
  (async () => {
    await refreshState();
    await loadCalendar();
  })();
}
