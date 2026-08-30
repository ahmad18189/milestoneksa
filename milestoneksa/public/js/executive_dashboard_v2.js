/**
 * CEO Executive KPI Dashboard (RTL)
 *
 * Custom HTML Blocks render inside Shadow DOM, so callers must mount into
 * the shadow root (see Custom HTML Block script). App include only exposes
 * the mount API.
 */
(function () {
	"use strict";

	const UNAVAILABLE = "غير متوفر في النظام";

	function qs(root, sel) {
		return root.querySelector(sel);
	}

	function formatCurrency(value, currency) {
		if (value === null || value === undefined || Number.isNaN(Number(value))) {
			return "—";
		}
		try {
			return new Intl.NumberFormat("ar-SA", {
				style: "currency",
				currency: currency || "SAR",
				maximumFractionDigits: 0,
			}).format(Number(value));
		} catch (e) {
			return Number(value).toLocaleString("ar-SA") + " " + (currency || "");
		}
	}

	function formatNumber(value, digits) {
		if (value === null || value === undefined || Number.isNaN(Number(value))) {
			return "—";
		}
		return Number(value).toLocaleString("ar-SA", {
			maximumFractionDigits: digits == null ? 1 : digits,
		});
	}

	function formatPct(value) {
		if (value === null || value === undefined) return "—";
		return formatNumber(value, 1) + "%";
	}

	function esc(s) {
		if (window.frappe && frappe.utils && frappe.utils.escape_html) {
			return frappe.utils.escape_html(String(s == null ? "" : s));
		}
		return String(s == null ? "" : s)
			.replace(/&/g, "&amp;")
			.replace(/</g, "&lt;")
			.replace(/>/g, "&gt;")
			.replace(/"/g, "&quot;");
	}

	function freshnessHtml(freshness) {
		if (!freshness) return "";
		const stale = freshness.is_stale ? " is-stale" : "";
		const ts = freshness.calculated_at || "";
		const note = freshness.is_stale
			? " · بيانات قديمة" + (freshness.stale_reason ? ": " + freshness.stale_reason : "")
			: "";
		return `<span class="ed-freshness${stale}">آخر حساب: ${esc(ts)}${esc(note)}</span>`;
	}

	function kpiCard(kpi, currency, stale) {
		if (!kpi) return "";
		const available = kpi.available !== false;
		const cls = ["ed-kpi"];
		if (!available) cls.push("unavailable");
		if (stale) cls.push("stale");
		let valueHtml;
		if (!available) {
			valueHtml = esc(kpi.message || UNAVAILABLE);
		} else if (typeof kpi.value === "number") {
			const label = kpi.label || "";
			const isPct = label.indexOf("هامش") >= 0;
			const isCount =
				label.indexOf("وحدات") >= 0 ||
				label.indexOf("وحدة") >= 0 ||
				label.indexOf("حجز") >= 0 ||
				label.indexOf("إلغ") >= 0 ||
				label.indexOf("الغ") >= 0;
			if (isPct) valueHtml = esc(formatPct(kpi.value));
			else if (isCount) valueHtml = esc(formatNumber(kpi.value, 0));
			else valueHtml = esc(formatCurrency(kpi.value, currency));
		} else if (kpi.message && (kpi.value === null || kpi.value === undefined)) {
			valueHtml = esc(kpi.message);
		} else {
			valueHtml = esc(kpi.value == null ? "—" : kpi.value);
		}
		return `
			<div class="${cls.join(" ")}">
				<div class="ed-kpi-label">${esc(kpi.label || "")}</div>
				<div class="ed-kpi-value">${valueHtml}</div>
			</div>`;
	}

	function openDoc(doctype, name) {
		if (!doctype || !name || !window.frappe) return;
		frappe.set_route("Form", doctype, name);
	}

	function renderToolbar(state) {
		const companies = (state.companies || []).map(
			(c) =>
				`<option value="${esc(c)}" ${c === state.company ? "selected" : ""}>${esc(c)}</option>`
		);
		return `
			<div class="ed-toolbar">
				<div class="ed-toolbar-title">لوحة المؤشرات التنفيذية</div>
				<div class="ed-filters">
					<label>الشركة
						<select id="ed-company">${companies.join("")}</select>
					</label>
					<label>من
						<input type="date" id="ed-from" value="${esc(state.from_date || "")}">
					</label>
					<label>إلى
						<input type="date" id="ed-to" value="${esc(state.to_date || "")}">
					</label>
					<button type="button" class="ed-btn" id="ed-refresh">تحديث</button>
				</div>
			</div>`;
	}

	function renderCompanySummary(section, currency) {
		if (!section) return "";
		const stale = !!(section.freshness && section.freshness.is_stale);
		const kpis = section.kpis || {};
		return `
			<section class="ed-zone" data-zone="company">
				<div class="ed-zone-header">
					<h2>ملخص الشركة</h2>
					${freshnessHtml(section.freshness)}
				</div>
				<div class="ed-kpi-grid">
					${kpiCard(kpis.portfolio_value, currency, stale)}
					${kpiCard(kpis.available_cash, currency, stale)}
					${kpiCard(kpis.sales, currency, stale)}
					${kpiCard(kpis.collections, currency, stale)}
					${kpiCard(kpis.expected_margin, currency, stale)}
				</div>
			</section>`;
	}

	function renderProjects(section) {
		if (!section) return "";
		const rows = section.projects || [];
		const gaps = section.data_gaps || {};
		if (!rows.length) {
			return `
				<section class="ed-zone" data-zone="projects">
					<div class="ed-zone-header"><h2>حالة المشاريع</h2>${freshnessHtml(section.freshness)}</div>
					<div class="ed-empty">لا توجد مشاريع وفق الإعدادات.</div>
				</section>`;
		}
		const gapsBanner =
			gaps.missing_budget_count > 0
				? `<div class="ed-gaps-banner">
					<strong>نواقص للمحاسبة (${gaps.missing_budget_count}):</strong>
					${esc(gaps.note || "")}
					<div class="ed-gaps-list">${esc((gaps.projects_missing_budget || []).join(" · "))}</div>
					<div class="ed-gaps-hint">الحقل المطلوب في بطاقة المشروع: <code>Estimated Costing</code></div>
				</div>`
				: "";
		const body = rows
			.map(function (p) {
				const planned = p.progress_planned_available
					? formatPct(p.progress_planned)
					: UNAVAILABLE;
				const delay =
					p.delay_days === null || p.delay_days === undefined
						? "—"
						: formatNumber(p.delay_days, 0);
				const budgetCell = p.budget_available
					? formatNumber(p.budget, 0)
					: "غير مُدخل";
				const remain =
					p.remaining_vs_estimate === null || p.remaining_vs_estimate === undefined
						? "—"
						: formatNumber(p.remaining_vs_estimate, 0);
				const missing = (p.missing_fields || [])
					.map(function (m) {
						return esc(m.label || m.field);
					})
					.join("، ");
				return (
					'<tr class="clickable" data-doctype="Project" data-name="' +
					esc(p.name) +
					'">' +
					'<td><span class="ed-rag ' +
					esc(p.rag || "grey") +
					'"></span>' +
					esc(p.project_name) +
					"</td>" +
					"<td>" +
					esc(p.status || "") +
					"</td>" +
					"<td>" +
					esc(formatPct(p.progress_actual)) +
					"</td>" +
					'<td class="unavailable-cell">' +
					esc(planned) +
					"</td>" +
					"<td>" +
					esc(delay) +
					"</td>" +
					'<td class="' +
					(p.budget_available ? "" : "ed-missing") +
					'">' +
					esc(budgetCell) +
					"</td>" +
					"<td>" +
					esc(formatNumber(p.paid, 0)) +
					"</td>" +
					"<td>" +
					esc(formatNumber(p.actual_cost, 0)) +
					"</td>" +
					"<td>" +
					esc(remain) +
					"</td>" +
					"<td>" +
					esc(formatNumber(p.po_remaining, 0)) +
					"</td>" +
					'<td class="ed-missing-cell">' +
					(missing || "—") +
					"</td>" +
					"</tr>"
				);
			})
			.join("");
		return (
			'<section class="ed-zone" data-zone="projects">' +
			'<div class="ed-zone-header"><h2>حالة المشاريع (' +
			rows.length +
			")</h2>" +
			freshnessHtml(section.freshness) +
			"</div>" +
			gapsBanner +
			'<div class="ed-table-wrap"><table class="ed-table ed-table-finance"><thead><tr>' +
			"<th>المشروع</th><th>الحالة</th><th>الإنجاز %</th><th>المخطط %</th><th>تأخير</th>" +
			"<th>الميزانية (تقدير)</th><th>المدفوع</th><th>التكلفة الفعلية</th>" +
			"<th>المتبقي vs تقدير</th><th>متبقي أوامر شراء</th><th>حقول ناقصة</th>" +
			"</tr></thead><tbody>" +
			body +
			"</tbody></table></div></section>"
		);
	}

	function renderLiquidity(section, currency, showUnavailable) {
		if (!section) return "";
		const stale = !!(section.freshness && section.freshness.is_stale);
		let unavailableHtml = "";
		if (showUnavailable && section.unavailable_kpis) {
			unavailableHtml = Object.values(section.unavailable_kpis)
				.map((k) => kpiCard(k, currency, true))
				.join("");
		}
		const cv = section.collections_vs_due || {};
		const overdue = section.overdue_receivables || {};
		const forecast = section.cash_forecast || {};
		const samples = (overdue.samples || [])
			.map(
				(s) => `
			<tr class="clickable" data-doctype="Sales Invoice" data-name="${esc(s.name)}">
				<td>${esc(s.name)}</td>
				<td>${esc(s.customer || "")}</td>
				<td>${esc(formatCurrency(s.outstanding, currency))}</td>
				<td>${esc(s.due_date || "")}</td>
				<td>${esc(formatNumber(s.overdue_days, 0))}</td>
			</tr>`
			)
			.join("");

		return `
			<section class="ed-zone" data-zone="liquidity">
				<div class="ed-zone-header">
					<h2>السيولة والمبيعات</h2>
					${freshnessHtml(section.freshness)}
				</div>
				<div class="ed-kpi-grid">
					${unavailableHtml}
					${kpiCard(
						{
							label: "تحصيل مقابل مستحق",
							available: true,
							value: null,
							message:
								"تحصيل: " +
								formatCurrency(cv.collections, currency) +
								" / مستحق: " +
								formatCurrency(cv.due_outstanding, currency),
						},
						currency,
						stale
					)}
					${kpiCard(
						{ label: "متأخرات التحصيل", available: true, value: overdue.total },
						currency,
						stale
					)}
					${kpiCard(
						{
							label: forecast.label || "التدفق المتوقع",
							available: forecast.available !== false,
							value: forecast.net_estimate,
							message: forecast.is_estimate ? "تقدير" : null,
						},
						currency,
						stale
					)}
					${kpiCard(section.funding_gap, currency, stale)}
					${kpiCard(section.available_cash, currency, stale)}
				</div>
				${forecast.note ? `<p class="ed-note">${esc(forecast.note)}</p>` : ""}
				${
					samples
						? `<div class="ed-table-wrap" style="margin-top:0.75rem">
					<table class="ed-table">
						<thead><tr><th>فاتورة</th><th>عميل</th><th>المستحق</th><th>الاستحقاق</th><th>أيام التأخير</th></tr></thead>
						<tbody>${samples}</tbody>
					</table>
				</div>`
						: ""
				}
			</section>`;
	}

	function renderAlerts(section) {
		if (!section) return "";
		const alerts = section.alerts || [];
		if (!alerts.length) {
			return `
				<section class="ed-zone" data-zone="alerts">
					<div class="ed-zone-header"><h2>المخاطر والقرارات</h2>${freshnessHtml(section.freshness)}</div>
					<div class="ed-empty">لا توجد تنبيهات حالياً.</div>
				</section>`;
		}
		const items = alerts
			.map(
				(a) => `
			<div class="ed-alert ${esc(a.severity || "")}" data-doctype="${esc(a.ref_doctype || "")}" data-name="${esc(
					a.ref_name || ""
				)}">
				<div class="ed-alert-problem">${esc(a.problem || "")}</div>
				<div class="ed-alert-meta">
					<span>الإجراء: ${esc(a.recommended_action || "")}</span>
					<span>المسؤول: ${esc(a.owner || "")}</span>
					<span>الموعد: ${esc(a.deadline || "")}</span>
				</div>
			</div>`
			)
			.join("");
		return `
			<section class="ed-zone" data-zone="alerts">
				<div class="ed-zone-header">
					<h2>المخاطر والقرارات</h2>
					${freshnessHtml(section.freshness)}
				</div>
				${items}
			</section>`;
	}

	function bindEvents(root, state) {
		const btn = qs(root, "#ed-refresh");
		if (btn) {
			btn.onclick = function () {
				state.company = (qs(root, "#ed-company") || {}).value || state.company;
				state.from_date = (qs(root, "#ed-from") || {}).value || null;
				state.to_date = (qs(root, "#ed-to") || {}).value || null;
				load(root, state);
			};
		}
		root.querySelectorAll("[data-doctype][data-name]").forEach(function (el) {
			el.addEventListener("click", function () {
				openDoc(el.getAttribute("data-doctype"), el.getAttribute("data-name"));
			});
		});
	}

	function render(root, data, state) {
		const currency = data.currency || "SAR";
		const showUnavailable = !!(data.settings && data.settings.show_unavailable_kpis);
		root.innerHTML =
			renderToolbar(
				Object.assign({}, state, {
					company: data.company,
					from_date: data.from_date,
					to_date: data.to_date,
				})
			) +
			(data.company_summary ? renderCompanySummary(data.company_summary, currency) : "") +
			(data.projects ? renderProjects(data.projects) : "") +
			(data.liquidity ? renderLiquidity(data.liquidity, currency, showUnavailable) : "") +
			(data.alerts ? renderAlerts(data.alerts) : "");
		bindEvents(root, state);
	}

	function load(root, state) {
		root.innerHTML = '<div class="ed-loading">جاري تحميل لوحة المؤشرات التنفيذية…</div>';
		frappe.call({
			method: "milestoneksa.api.executive_dashboard.get_executive_dashboard",
			args: {
				company: state.company || null,
				from_date: state.from_date || null,
				to_date: state.to_date || null,
			},
			callback: function (r) {
				if (!r || !r.message) {
					root.innerHTML = '<div class="ed-error">تعذر تحميل البيانات.</div>';
					return;
				}
				render(root, r.message, state);
			},
			error: function (err) {
				let msg = "تعذر تحميل لوحة المؤشرات.";
				try {
					if (err && err.message) msg = String(err.message);
				} catch (e) {
					/* keep default */
				}
				root.innerHTML = `<div class="ed-error">${esc(msg)}</div>`;
			},
		});
	}

	function injectShadowCss(shadowRoot) {
		if (!shadowRoot || shadowRoot.querySelector("link[data-ed-css]")) return;
		const link = document.createElement("link");
		link.rel = "stylesheet";
		link.href = "/assets/milestoneksa/css/executive_dashboard_v4.css";
		link.setAttribute("data-ed-css", "1");
		shadowRoot.appendChild(link);
	}

	function mount(root) {
		if (!root) return;
		if (root.dataset.edInit === "1") return;
		root.dataset.edInit = "1";
		if (root.getRootNode && root.getRootNode() instanceof ShadowRoot) {
			injectShadowCss(root.getRootNode());
		}
		const state = { company: null, from_date: null, to_date: null, companies: [] };
		frappe.call({
			method: "frappe.client.get_list",
			args: { doctype: "Company", fields: ["name"], limit_page_length: 50 },
			callback: function (r) {
				state.companies = (r.message || []).map(function (c) {
					return c.name;
				});
				load(root, state);
			},
			error: function () {
				load(root, state);
			},
		});
	}

	/**
	 * Desk boot can replace window.frappe after app_include_js runs, wiping
	 * nested namespaces. Keep a durable window export and re-bind on ready.
	 */
	function register() {
		const api = { mount: mount, autoMount: autoMount };
		window.__mk_executive_dashboard = api;
		if (!window.frappe) return api;
		try {
			if (typeof frappe.provide === "function") {
				frappe.provide("frappe.milestoneksa.executive_dashboard");
			} else {
				frappe.milestoneksa = frappe.milestoneksa || {};
			}
			frappe.milestoneksa.executive_dashboard = api;
		} catch (e) {
			/* ignore */
		}
		return api;
	}

	function autoMount() {
		register();
		const nodes = document.querySelectorAll("*");
		for (let i = 0; i < nodes.length; i++) {
			const el = nodes[i];
			if (!el.tagName || el.tagName.indexOf("-") < 0 || !el.shadowRoot) continue;
			const root = el.shadowRoot.querySelector("#executive-dashboard-root");
			if (root) mount(root);
		}
	}

	register();

	if (window.frappe && typeof frappe.ready === "function") {
		frappe.ready(function () {
			register();
			autoMount();
		});
	}
	if (window.jQuery) {
		// Never use $() here — a prior helper named $ shadowed jQuery and crashed.
		jQuery(document).on("page-change", function () {
			setTimeout(autoMount, 150);
		});
	}
	// Workspace custom blocks mount asynchronously into Shadow DOM
	let tries = 0;
	const poll = setInterval(function () {
		autoMount();
		if (++tries >= 80) clearInterval(poll);
	}, 250);
})();
