// File: milestoneksa/public/js/test_fields_dialog.js
// Usage (console): frappe.ui.toolbar.test_time_fields()

frappe.provide("frappe.ui.toolbar");

frappe.ui.toolbar.test_time_fields = function () {
	if (frappe.ui.toolbar._test_time_fields) {
		frappe.ui.toolbar._test_time_fields.show();
		return;
	}

	const CACHE_KEY = "mksa:last_loc"; // { lat, lng, ts }
	const CACHE_MAX_AGE_MS = 24 * 60 * 60 * 1000; // 24h

	function saveCache(lat, lng) {
		try { localStorage.setItem(CACHE_KEY, JSON.stringify({ lat, lng, ts: Date.now() })); } catch {}
	}
	function readCache() {
		try {
			const raw = localStorage.getItem(CACHE_KEY);
			if (!raw) return null;
			const obj = JSON.parse(raw);
			if (!obj || typeof obj.lat !== "number" || typeof obj.lng !== "number" || typeof obj.ts !== "number") return null;
			if (Date.now() - obj.ts > CACHE_MAX_AGE_MS) return null;
			return obj;
		} catch { return null; }
	}
	function fmtAge(ms) {
		const m = Math.max(1, Math.round(ms / 60000));
		return __("{0} min ago", [m]);
	}

	const d = new frappe.ui.Dialog({
		title: __("Geolocation Field Test"),
		size: "small",
		fields: [
			{ fieldtype: "Section Break", label: __("Now") },
			{ fieldtype: "Date", fieldname: "today", label: __("Today"), default: frappe.datetime.nowdate(), read_only: 1 },
			{ fieldtype: "Time", fieldname: "now_time", label: __("Current Time"), read_only: 1 },

			{ fieldtype: "Column Break" },
			{ fieldtype: "Float", fieldname: "latitude", label: __("Latitude"), read_only: 1, precision: 6 },
			{ fieldtype: "Float", fieldname: "longitude", label: __("Longitude"), read_only: 1, precision: 6 },

			{ fieldtype: "Section Break", label: __("Status & Actions") },
			{ fieldtype: "HTML", fieldname: "status_html" },

			{ fieldtype: "Button", fieldname: "btn_loc", label: __("Update Location"), click: () => updateLocation() },
			{ fieldtype: "Button", fieldname: "btn_cached", label: __("Use Cached Location"), click: () => useCached() },
			{ fieldtype: "Button", fieldname: "btn_ip", label: __("Approximate via IP (Server)"), click: () => ipApprox() },

			{ fieldtype: "Section Break", label: __("Warm-up (macOS/Safari)") },
			{ fieldtype: "HTML", fieldname: "tips_html" },

			// Optional map preview (will render only if coords exist and your CSP allows it)
			{ fieldtype: "Section Break", label: __("Map (optional)") },
			{ fieldtype: "HTML", fieldname: "map_html" },
		],
		primary_action_label: __("Close"),
		primary_action: () => d.hide(),
	});

	frappe.ui.toolbar._test_time_fields = d;
	d.show();

	// ---- live time (every 1s) ----
	const setTime = () => d.get_field("now_time").set_value(frappe.datetime.now_time());
	setTime();
	const timer = setInterval(setTime, 1000);
	d.$wrapper.on("hidden.bs.modal", () => clearInterval(timer));

	// ---- status + tips ----
	function setStatus(msg, is_error = false) {
		d.fields_dict.status_html.$wrapper.html(
			`<div class="${is_error ? "text-danger" : "text-muted"}" style="margin-top:6px;">${msg}</div>`
		);
	}
	d.fields_dict.tips_html.$wrapper.html(`
		<div class="small text-muted">
			${__("If you see “kCLErrorLocationUnknown”:")}
			<ul style="margin:6px 0 0 18px;">
				<li>${__("Turn <b>Wi-Fi ON</b> (Macs use nearby Wi-Fi for location).")}</li>
				<li>${__("Disable <b>VPN</b> temporarily.")}</li>
				<li>${__("Safari ▸ Settings ▸ Websites ▸ Location → Allow for this site.")}</li>
				<li>${__("System Settings ▸ Privacy & Security ▸ Location Services → Safari ON.")}</li>
			</ul>
			<div style="margin-top:6px;">
				<a href="https://maps.apple.com/?q=Current+Location" target="_blank" rel="noopener">${__("Open Apple Maps to warm up location")}</a>
			</div>
		</div>
	`);

	// ---- map (optional) ----
	function renderMap(lat, lng) {
		// Start with a simple, same-origin-free message (CSP-safe). You can replace with your data-URI proxy later.
		d.fields_dict.map_html.$wrapper.html(`
			<div class="text-muted small" style="margin-bottom:6px;">
				${__("Map disabled in this test to avoid CSP issues. Coords are shown above.")}<br>
				<a href="https://maps.google.com/?q=${lat},${lng}" target="_blank" rel="noopener">${__("Open in Google Maps")}</a>
			</div>
		`);
	}

	// ---- geolocation (user gesture only) ----
	function getGeoSmart(onOk, onErr) {
		if (!navigator.geolocation) return onErr(new Error(__("No Geolocation API")));

		// Warm-first: short watch helps Safari/CoreLocation
		const tries = [
			"watch-hi", "watch-low",
			{ enableHighAccuracy: true,  timeout: 10000, maximumAge: 0 },
			{ enableHighAccuracy: false, timeout: 10000, maximumAge: 60000 },
			{ enableHighAccuracy: false, timeout: 8000, maximumAge: 24*60*60*1000 },
		];

		const next = () => {
			if (!tries.length) return onErr(new Error(__("Location unavailable (try Wi-Fi on / allow location / disable VPN).")));
			const mode = tries.shift();

			if (mode === "watch-hi" || mode === "watch-low") {
				const opts = { enableHighAccuracy: mode === "watch-hi", timeout: 12000, maximumAge: 0 };
				const id = navigator.geolocation.watchPosition(
					(p) => { navigator.geolocation.clearWatch(id); onOk(p.coords.latitude, p.coords.longitude); },
					(e) => { navigator.geolocation.clearWatch(id); if (e && e.code === 1) onErr(e); else next(); },
					opts
				);
				setTimeout(() => navigator.geolocation.clearWatch(id), opts.timeout + 2000);
				return;
			}

			navigator.geolocation.getCurrentPosition(
				(p) => onOk(p.coords.latitude, p.coords.longitude),
				(e) => { if (e && e.code === 1) onErr(e); else next(); },
				mode
			);
		};
		next();
	}

	// ---- actions ----
	function updateLocation() {
		setStatus(__("Locating…"));
		getGeoSmart(
			(lat, lng) => {
				d.set_values({ latitude: Number(lat.toFixed(6)), longitude: Number(lng.toFixed(6)) });
				saveCache(lat, lng);
				setStatus(__("Latitude: {0}°, Longitude: {1}°", [lat.toFixed(5), lng.toFixed(5)]));
				renderMap(lat, lng); // optional map
			},
			(err) => {
				const msg = frappe.utils.escape_html(err?.message || __("Unknown error"));
				setStatus(`${__("Unable to retrieve your location")}: ${msg}`, true);
				// Offer cached if available
				const cached = readCache();
				if (cached) {
					const age = fmtAge(Date.now() - cached.ts);
					const $s = d.fields_dict.status_html.$wrapper;
					$s.append(
						`<div class="small" style="margin-top:6px;">
							${__("Cached location is available ({0}). Click <b>Use Cached Location</b>.", [age])}
						</div>`
					);
				}
			}
		);
	}

	function useCached() {
		const cached = readCache();
		if (!cached) {
			setStatus(__("No cached location found within the last 24 hours."), true);
			return;
		}
		d.set_values({ latitude: Number(cached.lat.toFixed(6)), longitude: Number(cached.lng.toFixed(6)) });
		setStatus(__("Using cached location — Latitude: {0}°, Longitude: {1}°", [cached.lat.toFixed(5), cached.lng.toFixed(5)]));
		renderMap(cached.lat, cached.lng);
	}

	// OPTIONAL: Server-side approximate by IP (implement `milestoneksa.api.geo.ip_guess`)
	function ipApprox() {
		setStatus(__("Estimating via IP… (city-level accuracy)"));
		frappe.call({
			method: "milestoneksa.api.geo.ip_guess",
			args: {},
			callback: (r) => {
				const { lat, lng, note } = (r && r.message) || {};
				if (typeof lat === "number" && typeof lng === "number") {
					d.set_values({ latitude: Number(lat.toFixed(6)), longitude: Number(lng.toFixed(6)) });
					setStatus((note || __("Approximate IP location")) + ` — ` + __(
						"Latitude: {0}°, Longitude: {1}°",
						[lat.toFixed(5), lng.toFixed(5)]
					));
					renderMap(lat, lng);
				} else {
					setStatus(__("Could not get IP-based approximation."), true);
				}
			},
			error: () => setStatus(__("Could not get IP-based approximation."), true),
		});
	}
};
