// my_app/public/js/quick_checkin_toolbar.js
// Adds a "Quick Check-In/Out" button to the User menu and opens a dialog
// Uses Frappe's native Dialog + Geolocation field (no custom HTML escaping issues)

frappe.provide("mksa.quick_checkin");

(function () {
	// add menu entry once the toolbar is ready
	$(document).on("toolbar_setup", function () {
		// Put under the "User" dropdown (same pattern as setup_session_defaults)
		frappe.ui.toolbar.add_dropdown_button(
			"User",
			__("Quick Check-In/Out"),
			() => mksa.quick_checkin.open_dialog(),
			"octicon octicon-location"
		);
	});

	// Small helpers
	function pad(n) {
		return String(n).padStart(2, "0");
	}
	function nowDateISO() {
		const d = new Date();
		return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
	}
	function nowTimeISO() {
		const d = new Date();
		return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
	}

	// Build a GeoJSON FeatureCollection Point from lat/lng
	function pointGeoJSON(lat, lng) {
		// GeoJSON order: [lng, lat]
		return {
			type: "FeatureCollection",
			features: [
				{
					type: "Feature",
					properties: {},
					geometry: { type: "Point", coordinates: [lng, lat] },
				},
			],
		};
	}

	// Get session's employee (via frappe.boot or via server fallback)
	async function get_session_employee() {
		// If you already keep employee in boot, use that.
		// Fallback: fetch linked Employee from the current user (standard pattern in HRMS sites).
		try {
			const r = await frappe.call({
				method: "frappe.client.get_value",
				args: {
					doctype: "Employee",
					fieldname: ["name", "employee_name"],
					filters: { user_id: frappe.session.user },
				},
			});
			return r?.message?.name
				? { name: r.message.name, employee_name: r.message.employee_name }
				: null;
		} catch (e) {
			return null;
		}
	}

	// Fetch last checkin (most recent)
	async function get_last_checkin(employee) {
		const r = await frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "Employee Checkin",
				fields: ["name", "log_type", "time"],
				filters: { employee },
				order_by: "time desc",
				limit_page_length: 1,
			},
		});
		return (r?.message && r.message[0]) || null;
	}

	// Decide next action based on last log
	function next_action_from(last) {
		// If last is IN, next is OUT; else IN
		if (last && last.log_type === "IN") {
			return { action: "OUT", label: __("Check Out") };
		}
		return { action: "IN", label: __("Check In") };
	}

	// Robust geolocation getter (must be called from a user gesture)
	function get_current_position() {
		return new Promise((resolve, reject) => {
			if (!("geolocation" in navigator)) {
				reject(new Error("Geolocation API not available in this browser."));
				return;
			}
			navigator.geolocation.getCurrentPosition(
				(pos) => resolve(pos),
				(err) => reject(err),
				{
					enableHighAccuracy: true,
					timeout: 15000,
					maximumAge: 0,
				}
			);
		});
	}

	mksa.quick_checkin.open_dialog = async function () {
		const emp = await get_session_employee();
		if (!emp) {
			frappe.msgprint({
				title: __("No Employee Linked"),
				message: __(
					"Your user is not linked to an Employee. Please set <b>User ID</b> on your Employee record."
				),
				indicator: "red",
			});
			return;
		}

		// prefetch last log
		const last = await get_last_checkin(emp.name);
		const nextAction = next_action_from(last);

		const d = new frappe.ui.Dialog({
			title: nextAction.label,
			fields: [
				{ fieldtype: "Section Break", label: __("Info") },
				{
					fieldtype: "Read Only",
					label: __("Employee"),
					fieldname: "employee_name",
					default: emp.employee_name || emp.name,
				},
				{
					fieldtype: "Read Only",
					label: __("Last Entry"),
					fieldname: "last_entry",
					default: last
						? `${last.log_type} • ${frappe.datetime.user_to_str(last.time)}`
						: __("No entries yet"),
				},
				{ fieldtype: "Column Break" },
				{
					fieldtype: "Date",
					label: __("Today"),
					fieldname: "today",
					read_only: 1,
					default: nowDateISO(),
				},
				{
					fieldtype: "Time",
					label: __("Current Time"),
					fieldname: "now_time",
					read_only: 1,
					default: nowTimeISO(),
				},

				{ fieldtype: "Section Break", label: __("Location") },
				{
					fieldtype: "Geolocation",
					label: __("Location"),
					fieldname: "geolocation",
					description: __(
						"You can drag the marker if needed. Alternatively click <b>Update Location</b> to use device GPS."
					),
				},
				{ fieldtype: "Column Break" },
				{
					fieldtype: "Float",
					label: __("Latitude"),
					fieldname: "latitude",
					read_only: 1,
				},
				{
					fieldtype: "Float",
					label: __("Longitude"),
					fieldname: "longitude",
					read_only: 1,
				},
				{
					fieldtype: "Button",
					fieldname: "update_location_btn",
					label: __("Update Location"),
					click: async () => {
						// IMPORTANT: runs on user gesture
						d.fields_dict.update_location_btn.df.read_only = 1;
						d.fields_dict.update_location_btn.refresh();
						try {
							const pos = await get_current_position();
							const lat = Number(pos.coords.latitude);
							const lng = Number(pos.coords.longitude);
							d.set_value("latitude", lat);
							d.set_value("longitude", lng);

							// Use GeoJSON FeatureCollection (Geolocation field expects this)
							const geo = pointGeoJSON(lat, lng);
							// Setting as object is fine; control serializes when saving
							d.get_field("geolocation").set_value(geo);

							frappe.show_alert({
								message: __("Location updated."),
								indicator: "green",
							});
						} catch (e) {
							// Common on macOS/iOS when location is off (kCLErrorLocationUnknown)
							frappe.msgprint({
								title: __("Location Unavailable"),
								message: __(
									"Could not fetch your location.<br>If you're on Safari/iOS/macOS, enable Location Services for your browser and reload this page. You can still drop the marker on the map manually."
								),
								indicator: "orange",
							});
						} finally {
							d.fields_dict.update_location_btn.df.read_only = 0;
							d.fields_dict.update_location_btn.refresh();
						}
					},
				},
			],
			primary_action_label: __(`Confirm ${nextAction.label}`),
			primary_action: async () => {
				const v = d.get_values();
				// Require lat/lng (consistent with your validation)
				if (!v.latitude || !v.longitude) {
					frappe.msgprint({
						title: __("Missing Location"),
						message: __(
							"Latitude and longitude are required for checking in/out. Click <b>Update Location</b> or place the marker on the map."
						),
						indicator: "red",
					});
					return;
				}

				// Use now; server will store in server TZ
				const now_dt = frappe.datetime.now_datetime();

				try {
					await frappe.call({
						method: "frappe.client.insert",
						args: {
							doc: {
								doctype: "Employee Checkin",
								employee: emp.name,
								employee_name: emp.employee_name,
								log_type: nextAction.action,
								time: now_dt,
								latitude: v.latitude,
								longitude: v.longitude,
								// store the Geolocation field if you have it on the doctype
								// (many sites add a 'geolocation' field to Employee Checkin)
								...(v.geolocation ? { geolocation: v.geolocation } : {}),
							},
						},
					});

					frappe.show_alert({
						message: __("{0} successful!", [nextAction.label]),
						indicator: "green",
					});
					d.hide();
				} catch (e) {
					frappe.msgprint({
						title: __("Failed"),
						message: e?.message || __("Could not save check-in/out."),
						indicator: "red",
					});
				}
			},
		});

		// keep "Current Time" ticking every second while dialog is open
		let tickId = null;
		d.on_page_show = () => {
			tickId = setInterval(() => d.set_value("now_time", nowTimeISO()), 1000);
		};
		d.on_hide = () => {
			if (tickId) clearInterval(tickId);
		};

		d.show();
	};
})();
