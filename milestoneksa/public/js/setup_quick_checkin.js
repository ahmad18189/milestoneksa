// milestoneksa/public/js/setup_quick_checkin.js
frappe.provide("frappe.ui.toolbar");

frappe.ui.toolbar.setup_quick_checkin = function () {
	const state = { lat: null, lng: null, next: "IN", emp: null, last: null, timer: null };

	// ------------------ helpers ------------------
	const fmtUser   = (ts) => (ts ? frappe.datetime.str_to_user(ts) : __("—"));
	const nextLabel = (a)  => (a === "IN" ? __("Check In") : __("Check Out"));

	function hours_since(dt_str) {
		if (!dt_str) return "";
		const start = new Date(dt_str.replace(" ", "T"));
		const now = new Date();
		if (isNaN(start.getTime()) || now <= start) return "";
		return Number(((now - start) / 36e5).toFixed(2));
	}

	// cache last good fix (24h)
	const LAST_LOC_KEY = "mksa:last_loc";
	function saveLastLoc(lat, lng) {
		try { localStorage.setItem(LAST_LOC_KEY, JSON.stringify({ lat, lng, ts: Date.now() })); } catch {}
	}
	function readLastLoc(maxAgeMs = 24 * 60 * 60 * 1000) {
		try {
			const raw = localStorage.getItem(LAST_LOC_KEY);
			if (!raw) return null;
			const obj = JSON.parse(raw);
			if (!obj || typeof obj.lat !== "number" || typeof obj.lng !== "number" || typeof obj.ts !== "number") return null;
			if (Date.now() - obj.ts > maxAgeMs) return null;
			return obj;
		} catch { return null; }
	}

	// robust geolocation, better for kCLErrorLocationUnknown
	function getPositionRobust() {
		return new Promise((resolve, reject) => {
			if (!navigator.geolocation) {
				reject(new Error("Geolocation API not available in this browser."));
				return;
			}
			const tries = [
				"watch-hi", "watch-low",
				{ enableHighAccuracy: true,  timeout: 12000, maximumAge: 0 },
				{ enableHighAccuracy: false, timeout: 12000, maximumAge: 60000 },
				{ enableHighAccuracy: false, timeout: 8000,  maximumAge: 24 * 60 * 60 * 1000 },
			];

			function next() {
				if (!tries.length) return reject(new Error("Location unavailable after multiple attempts."));
				const mode = tries.shift();

				if (mode === "watch-hi" || mode === "watch-low") {
					const opts = { enableHighAccuracy: mode === "watch-hi", timeout: 10000, maximumAge: 0 };
					const id = navigator.geolocation.watchPosition(
						(p) => { navigator.geolocation.clearWatch(id); resolve({ lat: p.coords.latitude, lng: p.coords.longitude, source: mode }); },
						(e) => { navigator.geolocation.clearWatch(id); if (e && e.code === 1) reject(e); else next(); },
						opts
					);
					setTimeout(() => navigator.geolocation.clearWatch(id), opts.timeout + 1500);
					return;
				}

				navigator.geolocation.getCurrentPosition(
					(p) => resolve({ lat: p.coords.latitude, lng: p.coords.longitude, source: "current" }),
					(e) => { if (e && e.code === 1) reject(e); else next(); },
					mode
				);
			}
			next();
		});
	}

	// ------------------ dialog (fields-first) ------------------
	const d = new frappe.ui.Dialog({
		title: __("Quick Check-In/Out"),
		size: "small",
		fields: [
			{ fieldtype: "Section Break", label: __("Info") },
			{ fieldtype: "Read Only", fieldname: "employee_name", label: __("Employee") },
			{ fieldtype: "Date",      fieldname: "today",        label: __("Today"),        read_only: 1, default: frappe.datetime.nowdate() },
			{ fieldtype: "Time",      fieldname: "now_time",     label: __("Current Time"), read_only: 1, default: frappe.datetime.now_time() },

			{ fieldtype: "Column Break" },

			{ fieldtype: "Read Only", fieldname: "last_entry_label", label: __("Last Entry") },
			{ fieldtype: "Date",      fieldname: "last_entry_date",  label: __("Last Entry Date"), read_only: 1 },
			{ fieldtype: "Time",      fieldname: "last_entry_time",  label: __("Last Entry Time"), read_only: 1 },

			{ fieldtype: "Section Break", label: __("Work Summary") },
			{ fieldtype: "Float", fieldname: "total_hours", label: __("Total Hours (since last IN)"), read_only: 1, precision: 2 },

			{ fieldtype: "Section Break", label: __("Location") },
			{ fieldtype: "Float", fieldname: "latitude",  label: __("Latitude"),  read_only: 1, precision: 6 },
			{ fieldtype: "Float", fieldname: "longitude", label: __("Longitude"), read_only: 1, precision: 6 },

			{ fieldtype: "Column Break" },
			{
				fieldtype: "Button",
				fieldname: "fetch_location_btn",
				label: __("Fetch Location"),
				click: async () => {
					const btn = d.fields_dict.fetch_location_btn;
					btn.df.read_only = 1; btn.refresh();
					try {
						const pos = await getPositionRobust();
						const lat = +pos.lat, lng = +pos.lng;
						state.lat = lat; state.lng = lng;

						d.set_value("latitude",  Number(lat.toFixed(6)));
						d.set_value("longitude", Number(lng.toFixed(6)));

						saveLastLoc(lat, lng);
						frappe.show_alert({ message: __("Location updated"), indicator: "green" });
					} catch (e) {
						const cached = readLastLoc();
						if (cached) {
							state.lat = +cached.lat; state.lng = +cached.lng;
							d.set_value("latitude",  Number(state.lat.toFixed(6)));
							d.set_value("longitude", Number(state.lng.toFixed(6)));
							frappe.msgprint({
								title: __("Using Cached Location"),
								message: __(
									"Live location unavailable (e.g. kCLErrorLocationUnknown). Filled with your last known location."
								),
								indicator: "orange",
							});
						} else {
							frappe.msgprint({
								title: __("Location Unavailable"),
								message: __(
									"Could not fetch your location. Turn Wi-Fi ON, disable VPN, allow Precise Location for this site, or open Apple Maps, then try again."
								),
								indicator: "orange",
							});
							state.lat = state.lng = null;
							d.set_value("latitude",  "");
							d.set_value("longitude", "");
						}
					} finally {
						btn.df.read_only = 0; btn.refresh();
						sync_primary();
					}
				}
			},
		],
		primary_action_label: __("Confirm"),
		primary_action: () => submit(d)
	});

	d.show();

	// live clock + live total hours if applicable
	function tick() {
		d.set_value("now_time", frappe.datetime.now_time());
		if (state.last && state.last.log_type === "IN" && state.next === "OUT") {
			const hrs = hours_since(state.last.time);
			if (hrs !== "") d.set_value("total_hours", hrs);
		}
	}
	tick();
	state.timer = setInterval(tick, 1000);
	d.$wrapper.on("hidden.bs.modal", () => { if (state.timer) clearInterval(state.timer); });

	// confirm gating (needs lat & lng)
	const $primary = d.get_primary_btn();
	function sync_primary() {
		const lat = parseFloat(d.get_value("latitude"));
		const lng = parseFloat(d.get_value("longitude"));
		$primary.prop("disabled", !(isFinite(lat) && isFinite(lng)));
	}
	sync_primary();

	// fill info from server
	frappe.call("milestoneksa.api.quick_checkin.get_next_action")
		.then(r => {
			const data = r.message || {};
			state.next = data.next_action || "IN";
			state.emp  = data.employee || null;
			state.last = data.last || null;

			d.set_title(nextLabel(state.next));
			d.set_primary_action_label(__("Confirm {0}", [nextLabel(state.next)]));
			d.set_value("employee_name", state.emp?.employee_name || state.emp?.name || "");

			const last_label = state.last
				? `${state.last.log_type === "IN" ? __("Check-in") : __("Check-out")}: ${fmtUser(state.last.time)}`
				: __("No previous logs");
			d.set_value("last_entry_label", last_label);

			if (state.last?.time) {
				const [ld, lt] = state.last.time.split(" ");
				d.set_value("last_entry_date", ld || "");
				d.set_value("last_entry_time", lt || "");
			} else {
				d.set_value("last_entry_date", "");
				d.set_value("last_entry_time", "");
			}

			// initial total hours
			if (state.last && state.last.log_type === "IN" && state.next === "OUT") {
				const hrs = hours_since(state.last.time);
				if (hrs !== "") d.set_value("total_hours", hrs);
			} else {
				d.set_value("total_hours", "");
			}
		})
		.catch(e => {
			frappe.msgprint({ title: __("Error"), message: e?.message || __("Failed to load"), indicator: "red" });
		});

	// submit (records the check-in/out)
	function submit(dlg) {
		const lat = parseFloat(d.get_value("latitude"));
		const lng = parseFloat(d.get_value("longitude"));
		if (!isFinite(lat) || !isFinite(lng)) {
			frappe.msgprint({
				title: __("Location Required"),
				message: __("Latitude and longitude values are required for checking in/out."),
				indicator: "red"
			});
			return;
		}

		const geoj = JSON.stringify({
			type: "FeatureCollection",
			features: [{ type: "Feature", properties: {}, geometry: { type: "Point", coordinates: [lng, lat] } }]
		});

		frappe.call({
			method: "milestoneksa.api.quick_checkin.quick_checkin",
			args: { log_type: state.next, latitude: lat, longitude: lng, geolocation: geoj },
			freeze: true, freeze_message: __("Recording…"),
			callback: () => {
				dlg && dlg.hide();
				frappe.show_alert({ message: __("{0} recorded", [nextLabel(state.next)]), indicator: "green" });
			},
			error: (err) => {
				frappe.msgprint({ title: __("Error"), message: err?.message || __("Failed"), indicator: "red" });
			}
		});
	}
};
