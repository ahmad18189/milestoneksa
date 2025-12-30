frappe.ui.form.on("Project", {
	refresh(frm) {
		frm.events.render_project_dashboard(frm);
	},

	after_save(frm) {
		frm.events.render_project_dashboard(frm);
	},

	render_project_dashboard(frm) {
		console.log("🔍 Dashboard: render_project_dashboard called");
		
		const field = frm.fields_dict.custom_dashboard_html;
		if (!field) {
			console.warn("❌ Dashboard: custom_dashboard_html field not found");
			return;
		}

		const wrapper = field.$wrapper;
		wrapper.empty().addClass("project-dashboard-wrapper").css({
			"padding": "20px",
			"background": "#f8f9fa",
			"min-height": "600px"
		});

		if (frm.is_new()) {
			wrapper.append(
				$("<div class='alert alert-info'>").text(__("Save the project to view the dashboard."))
			);
			return;
		}

		// Load Chart.js if not already loaded
		if (typeof Chart === 'undefined') {
			console.log("📊 Dashboard: Loading Chart.js...");
			frappe.require('https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js', () => {
				console.log("✅ Dashboard: Chart.js loaded");
				frm.events.init_dashboard_content(frm, wrapper);
			});
		} else {
			console.log("✅ Dashboard: Chart.js already loaded");
			frm.events.init_dashboard_content(frm, wrapper);
		}
	},
	
	init_dashboard_content(frm, wrapper) {
		// Add CSS styles
		wrapper.append(frm.events.get_dashboard_styles());
		
		// Date filter section
		const filterSection = frm.events.create_date_filter(frm);
		wrapper.append(filterSection);
		
		// Loading state
		const loadingDiv = $(`
			<div class="text-center mt-5" data-role="dashboard-loading">
				<div class="spinner-border text-primary" style="width: 3rem; height: 3rem;"></div>
				<div class="mt-3">${__("Loading dashboard...")}</div>
			</div>
		`);
		wrapper.append(loadingDiv);
		
		// Load dashboard data
		frm.events.load_dashboard_data(frm);
	},

	get_dashboard_styles() {
		return $(`
			<style>
				/* Dashboard Container */
				.project-dashboard-wrapper {
					font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
				}
				
				/* KPI Cards */
				.dashboard-kpi-grid {
					display: grid;
					grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
					gap: 16px;
					margin-bottom: 30px;
				}
				
				.kpi-card {
					background: white;
					border-radius: 12px;
					padding: 24px;
					box-shadow: 0 2px 8px rgba(0,0,0,0.08);
					transition: all 0.3s ease;
					border-left: 4px solid #6c757d;
				}
				
				.kpi-card:hover {
					transform: translateY(-4px);
					box-shadow: 0 4px 16px rgba(0,0,0,0.12);
				}
				
				.kpi-card.good { border-left-color: #28a745; }
				.kpi-card.warning { border-left-color: #ffc107; }
				.kpi-card.danger { border-left-color: #dc3545; }
				.kpi-card.info { border-left-color: #17a2b8; }
				
				.kpi-card-title {
					font-size: 12px;
					font-weight: 600;
					text-transform: uppercase;
					letter-spacing: 0.5px;
					color: #6c757d;
					margin-bottom: 12px;
				}
				
				.kpi-card-value {
					font-size: 32px;
					font-weight: 700;
					color: #212529;
					margin-bottom: 8px;
				}
				
				.kpi-card-subtitle {
					font-size: 13px;
					color: #6c757d;
				}
				
				.kpi-card-change {
					display: inline-block;
					padding: 4px 8px;
					border-radius: 4px;
					font-size: 11px;
					font-weight: 600;
					margin-top: 8px;
				}
				
				.kpi-card-change.positive {
					background: #d4edda;
					color: #155724;
				}
				
				.kpi-card-change.negative {
					background: #f8d7da;
					color: #721c24;
				}
				
				/* Charts Section */
				.dashboard-charts-grid {
					display: grid;
					grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
					gap: 20px;
					margin-bottom: 30px;
				}
				
				.chart-card {
					background: white;
					border-radius: 12px;
					padding: 24px;
					box-shadow: 0 2px 8px rgba(0,0,0,0.08);
				}
				
				.chart-card-title {
					font-size: 16px;
					font-weight: 600;
					color: #212529;
					margin-bottom: 20px;
					padding-bottom: 12px;
					border-bottom: 2px solid #e9ecef;
				}
				
				/* Date Filter */
				.dashboard-date-filter {
					background: white;
					padding: 16px 20px;
					border-radius: 8px;
					margin-bottom: 24px;
					box-shadow: 0 1px 4px rgba(0,0,0,0.06);
					display: flex;
					gap: 12px;
					align-items: center;
					flex-wrap: wrap;
				}
				
				.dashboard-date-filter .btn-group {
					display: flex;
					gap: 4px;
				}
				
				.dashboard-date-filter .btn {
					padding: 6px 16px;
					font-size: 13px;
				}
				
				/* Table Styling */
				.dashboard-table {
					width: 100%;
					font-size: 13px;
				}
				
				.dashboard-table th {
					background: #f8f9fa;
					font-weight: 600;
					padding: 12px;
					border-bottom: 2px solid #dee2e6;
				}
				
				.dashboard-table td {
					padding: 10px 12px;
					border-bottom: 1px solid #e9ecef;
				}
				
				/* Progress Bars */
				.mini-progress {
					height: 8px;
					border-radius: 4px;
					background: #e9ecef;
					overflow: hidden;
					margin-top: 8px;
				}
				
				.mini-progress-bar {
					height: 100%;
					background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
					transition: width 0.6s ease;
				}
				
				/* Responsive */
				@media (max-width: 768px) {
					.dashboard-kpi-grid {
						grid-template-columns: 1fr;
					}
					.dashboard-charts-grid {
						grid-template-columns: 1fr;
					}
				}
			</style>
		`);
	},

	create_date_filter(frm) {
		const filterDiv = $(`
			<div class="dashboard-date-filter">
				<strong class="me-2">${__("Period")}:</strong>
				<div class="btn-group" role="group">
					<button type="button" class="btn btn-sm btn-outline-primary" data-period="week">${__("This Week")}</button>
					<button type="button" class="btn btn-sm btn-outline-primary" data-period="month">${__("This Month")}</button>
					<button type="button" class="btn btn-sm btn-outline-primary" data-period="quarter">${__("This Quarter")}</button>
					<button type="button" class="btn btn-sm btn-outline-primary active" data-period="all">${__("All Time")}</button>
				</div>
				<div class="ms-auto d-flex gap-2 align-items-center">
					<input type="date" class="form-control form-control-sm" data-field="from_date" placeholder="${__("From Date")}" style="width: 140px;">
					<span>-</span>
					<input type="date" class="form-control form-control-sm" data-field="to_date" placeholder="${__("To Date")}" style="width: 140px;">
					<button class="btn btn-sm btn-primary" data-action="apply-filter">${__("Apply")}</button>
				</div>
			</div>
		`);
		
		// Quick period buttons
		filterDiv.find("[data-period]").on("click", function() {
			filterDiv.find("[data-period]").removeClass("active");
			$(this).addClass("active");
			
			const period = $(this).data("period");
			let from_date = null;
			let to_date = null;
			
			const today = frappe.datetime.get_today();
			
			if (period === "week") {
				from_date = frappe.datetime.week_start();
				to_date = frappe.datetime.week_end();
			} else if (period === "month") {
				from_date = frappe.datetime.month_start();
				to_date = frappe.datetime.month_end();
			} else if (period === "quarter") {
				const quarter_start = frappe.datetime.get_first_day_of_the_week(today);
				from_date = frappe.datetime.add_days(quarter_start, -90);
				to_date = today;
			}
			
			frm.__dashboard_from_date = from_date;
			frm.__dashboard_to_date = to_date;
			
			if (from_date) {
				filterDiv.find("[data-field='from_date']").val(from_date);
			}
			if (to_date) {
				filterDiv.find("[data-field='to_date']").val(to_date);
			}
			
			if (period !== "all") {
				frm.events.load_dashboard_data(frm, from_date, to_date);
			} else {
				frm.events.load_dashboard_data(frm);
			}
		});
		
		// Custom date apply button
		filterDiv.find("[data-action='apply-filter']").on("click", () => {
			const from_date = filterDiv.find("[data-field='from_date']").val();
			const to_date = filterDiv.find("[data-field='to_date']").val();
			
			frm.__dashboard_from_date = from_date;
			frm.__dashboard_to_date = to_date;
			
			frm.events.load_dashboard_data(frm, from_date, to_date);
		});
		
		return filterDiv;
	},

	load_dashboard_data(frm, from_date = null, to_date = null) {
		console.log("🔍 Dashboard: Loading data...", {project: frm.doc.name, from_date, to_date});
		
		const wrapper = frm.fields_dict.custom_dashboard_html.$wrapper;
		const loading = wrapper.find("[data-role='dashboard-loading']");
		const content = wrapper.find("[data-role='dashboard-content']");
		
		loading.show();
		content.remove();
		
		frappe.call({
			method: "milestoneksa.api.project_dashboard.get_dashboard_data",
			args: {
				project: frm.doc.name,
				from_date: from_date,
				to_date: to_date
			},
			callback: (r) => {
				console.log("🔍 Dashboard: API Response received", r);
				loading.hide();
				
				if (!r || !r.message) {
					console.error("❌ Dashboard: No data in response");
					wrapper.append(`<div class="alert alert-danger">${__("Failed to load dashboard data")}</div>`);
					return;
				}
				
				const data = r.message;
				console.log("✅ Dashboard: Data structure:", {
					financial: data.financial,
					timeline: data.timeline,
					tasks: data.tasks,
					team: data.team,
					trends: data.trends
				});
				frm.__dashboard_data = data;
				
				const contentDiv = $("<div data-role='dashboard-content'></div>");
				
				// KPI Cards
				contentDiv.append(frm.events.render_kpi_cards(frm, data));
				
				// Charts
				contentDiv.append(frm.events.render_charts(frm, data));
				
				// Tables
				contentDiv.append(frm.events.render_tables(frm, data));
				
				wrapper.append(contentDiv);
				
				// Add export button to toolbar
				frm.events.add_dashboard_toolbar(frm);
			},
			error: (err) => {
				console.error("❌ Dashboard: API Error", err);
				loading.hide();
				wrapper.append(`
					<div class="alert alert-danger">
						<h5>${__("Error loading dashboard")}</h5>
						<p>${__("Check browser console (F12) for details.")}</p>
						<small>${err.message || err.exc || 'Unknown error'}</small>
					</div>
				`);
			}
		});
	},

	render_kpi_cards(frm, data) {
		console.log("🔍 Dashboard: Rendering KPI cards with data", data);
		
		const kpiGrid = $("<div class='dashboard-kpi-grid'></div>");
		
		// Project Health Score Card (NEW!)
		const health = data.health || {};
		const healthCard = frm.events.create_health_card(health);
		kpiGrid.append(healthCard);
		
		// Financial Card
		const financial = data.financial || {};
		const finCard = frm.events.create_kpi_card(
			"💰 " + __("Actual Cost"),
			frappe.format(financial.actual_cost, {fieldtype: "Currency"}),
			financial.estimated_budget > 0 ? `${__("of")} ${frappe.format(financial.estimated_budget, {fieldtype: "Currency"})} ${__("budget")}` : __("No budget set"),
			financial.budget_health || "info",
			financial.budget_variance_pct ? `${financial.budget_variance_pct > 0 ? '+' : ''}${financial.budget_variance_pct.toFixed(1)}%` : null
		);
		kpiGrid.append(finCard);
		
		// Revenue Card (NEW!)
		const revenueCard = frm.events.create_kpi_card(
			"💵 " + __("Revenue"),
			frappe.format(financial.total_revenue, {fieldtype: "Currency"}),
			`${__("Billed")}: ${frappe.format(financial.total_billed, {fieldtype: "Currency"})}`,
			financial.total_revenue > 0 ? "good" : "info",
			financial.revenue_realization_pct ? `${financial.revenue_realization_pct.toFixed(0)}% ${__("realized")}` : null
		);
		kpiGrid.append(revenueCard);
		
		// Profitability Card (NEW!)
		const profitCard = frm.events.create_kpi_card(
			"📊 " + __("Gross Profit"),
			frappe.format(financial.gross_profit, {fieldtype: "Currency"}),
			`${__("Margin")}: ${financial.profit_margin_pct.toFixed(1)}%`,
			financial.gross_profit >= 0 ? "good" : "danger",
			financial.gross_profit >= 0 ? __("Profitable") : __("Loss")
		);
		kpiGrid.append(profitCard);
		
		// Timeline Card
		const timeline = data.timeline || {};
		const timeCard = frm.events.create_kpi_card(
			"📅 " + __("Timeline"),
			timeline.days_remaining >= 0 ? `${timeline.days_remaining} ${__("days left")}` : __("Completed"),
			timeline.delay_days ? `${timeline.delay_days} ${__("days delay")}` : __("On schedule"),
			timeline.status === "delayed" ? "warning" : "good",
			`${timeline.percent_complete || 0}% ${__("complete")}`
		);
		kpiGrid.append(timeCard);
		
		// Tasks Card
		const tasks = data.tasks || {};
		const taskCard = frm.events.create_kpi_card(
			"✅ " + __("Tasks"),
			`${tasks.completed || 0}/${tasks.total || 0}`,
			__("completed"),
			tasks.completion_pct >= 80 ? "good" : (tasks.completion_pct >= 50 ? "warning" : "info"),
			tasks.overdue ? `${tasks.overdue} ${__("overdue")}` : __("None overdue")
		);
		kpiGrid.append(taskCard);
		
		// Team Card
		const team = data.team || {};
		const teamCard = frm.events.create_kpi_card(
			"👥 " + __("Team"),
			`${team.total_hours || 0} ${__("hrs")}`,
			`${team.team_size || 0} ${__("members")}`,
			team.team_size > 0 ? "good" : "warning",
			team.total_hours && team.team_size ? `${(team.total_hours / team.team_size).toFixed(1)} ${__("hrs/person")}` : __("No team assigned")
		);
		kpiGrid.append(teamCard);
		
		return kpiGrid;
	},
	
	create_health_card(health) {
		const score = health.score || 0;
		const level = health.level || "warning";
		const components = health.components || {};
		
		let color, bgColor, label;
		if (level === "excellent") {
			color = "#28a745";
			bgColor = "#d4edda";
			label = "Excellent";
		} else if (level === "good") {
			color = "#17a2b8";
			bgColor = "#d1ecf1";
			label = "Good";
		} else if (level === "warning") {
			color = "#ffc107";
			bgColor = "#fff3cd";
			label = "Needs Attention";
		} else {
			color = "#dc3545";
			bgColor = "#f8d7da";
			label = "At Risk";
		}
		
		const card = $(`
			<div class="kpi-card ${level}" style="grid-column: span 1; border-left-color: ${color};">
				<div class="kpi-card-title">🏆 ${__("Project Health")}</div>
				<div class="kpi-card-value" style="color: ${color};">${score}/100</div>
				<div class="kpi-card-subtitle">${__(label)}</div>
				<div class="health-breakdown mt-3" style="font-size: 11px;">
					<div class="d-flex justify-content-between mb-1">
						<span>💰 Budget:</span>
						<span class="fw-bold">${components.budget || 0}/30</span>
					</div>
					<div class="d-flex justify-content-between mb-1">
						<span>📅 Schedule:</span>
						<span class="fw-bold">${components.schedule || 0}/30</span>
					</div>
					<div class="d-flex justify-content-between mb-1">
						<span>✅ Tasks:</span>
						<span class="fw-bold">${components.tasks || 0}/25</span>
					</div>
					<div class="d-flex justify-content-between">
						<span>👥 Team:</span>
						<span class="fw-bold">${components.team || 0}/15</span>
					</div>
				</div>
			</div>
		`);
		
		return card;
	},

	create_kpi_card(title, value, subtitle, status = "info", badge = null) {
		const card = $(`
			<div class="kpi-card ${status}">
				<div class="kpi-card-title">${title}</div>
				<div class="kpi-card-value">${value}</div>
				<div class="kpi-card-subtitle">${subtitle}</div>
				${badge ? `<div class="kpi-card-change ${status === 'good' ? 'positive' : (status === 'danger' || status === 'warning' ? 'negative' : '')}">${badge}</div>` : ''}
			</div>
		`);
		return card;
	},

	render_charts(frm, data) {
		const chartsGrid = $("<div class='dashboard-charts-grid'></div>");
		
		// Profit vs Cost Chart (NEW!)
		const profitChart = frm.events.create_profit_chart(data.financial);
		chartsGrid.append(profitChart);
		
		// Financial Breakdown Chart
		const finChart = frm.events.create_financial_chart(data.financial);
		chartsGrid.append(finChart);
		
		// Task Status Chart
		const taskChart = frm.events.create_task_status_chart(data.tasks);
		chartsGrid.append(taskChart);
		
		// Cost Trend Chart
		const costTrendChart = frm.events.create_cost_trend_chart(data.trends);
		chartsGrid.append(costTrendChart);
		
		// Task Completion Trend
		const completionChart = frm.events.create_completion_trend_chart(data.trends);
		chartsGrid.append(completionChart);
		
		// Task Priority Distribution (NEW!)
		const priorityChart = frm.events.create_priority_chart(data.tasks);
		chartsGrid.append(priorityChart);
		
		// Team Breakdown Chart (NEW!)
		const teamChart = frm.events.create_team_chart(data.team);
		chartsGrid.append(teamChart);
		
		return chartsGrid;
	},
	
	create_team_chart(team) {
		console.log("🔍 Dashboard: Creating team chart", team);
		
		const card = $(`
			<div class="chart-card">
				<div class="chart-card-title">👥 ${__("Team Hours Breakdown")}</div>
				<div class="chart-container" style="height: 250px;"></div>
			</div>
		`);
		
		const breakdown = team.user_breakdown || [];
		
		if (breakdown.length === 0) {
			card.find(".chart-container").html(`
				<div class="text-center text-muted pt-5">
					<p>${__("No timesheet data available")}</p>
					<small>${__("Assign team members and log timesheets to see breakdown")}</small>
				</div>
			`);
			return card;
		}
		
		setTimeout(() => {
			const canvas = $("<canvas></canvas>");
			card.find(".chart-container").append(canvas);
			
			// Sort and take top 10
			const topUsers = breakdown.slice(0, 10);
			const labels = topUsers.map(u => u.user.split('@')[0]);  // Get username before @
			const values = topUsers.map(u => u.hours);
			
			try {
				new Chart(canvas[0], {
					type: 'horizontalBar',
					data: {
						labels: labels,
						datasets: [{
							label: __('Hours'),
							data: values,
							backgroundColor: '#4e73df',
							borderWidth: 0
						}]
					},
					options: {
						responsive: true,
						maintainAspectRatio: false,
						indexAxis: 'y',
						plugins: {
							legend: { display: false },
							tooltip: {
								callbacks: {
									label: function(context) {
										return `${context.parsed.x.toFixed(1)} hours`;
									}
								}
							}
						},
						scales: {
							x: { beginAtZero: true }
						}
					}
				});
				console.log("✅ Team Chart: Rendered with", topUsers.length, "members");
			} catch (err) {
				console.error("❌ Team Chart: Error", err);
			}
		}, 100);
		
		return card;
	},
	
	create_profit_chart(financial) {
		console.log("🔍 Dashboard: Creating profit chart", financial);
		
		const card = $(`
			<div class="chart-card">
				<div class="chart-card-title">💹 ${__("Revenue vs Cost")}</div>
				<div class="chart-container" style="height: 250px;"></div>
			</div>
		`);
		
		const revenue = financial.total_revenue || 0;
		const cost = financial.actual_cost || 0;
		const profit = financial.gross_profit || 0;
		
		setTimeout(() => {
			const canvas = $("<canvas></canvas>");
			card.find(".chart-container").append(canvas);
			
			if (revenue === 0 && cost === 0) {
				card.find(".chart-container").html(`
					<div class="text-center text-muted pt-5">
						<p>${__("No financial data available")}</p>
					</div>
				`);
				return;
			}
			
			try {
				new Chart(canvas[0], {
					type: 'bar',
					data: {
						labels: [__('Revenue'), __('Cost'), __('Profit')],
						datasets: [{
							label: __('Amount (SAR)'),
							data: [revenue, cost, profit],
							backgroundColor: ['#28a745', '#dc3545', profit >= 0 ? '#17a2b8' : '#ffc107'],
							borderWidth: 0
						}]
					},
					options: {
						responsive: true,
						maintainAspectRatio: false,
						plugins: {
							legend: { display: false },
							tooltip: {
								callbacks: {
									label: function(context) {
										return frappe.format(context.parsed.y, {fieldtype: 'Currency'});
									}
								}
							}
						},
						scales: {
							y: { beginAtZero: true }
						}
					}
				});
				console.log("✅ Profit Chart: Rendered");
			} catch (err) {
				console.error("❌ Profit Chart: Error", err);
			}
		}, 100);
		
		return card;
	},
	
	create_priority_chart(tasks) {
		console.log("🔍 Dashboard: Creating priority chart", tasks);
		
		const card = $(`
			<div class="chart-card">
				<div class="chart-card-title">⭐ ${__("Tasks by Priority")}</div>
				<div class="chart-container" style="height: 250px;"></div>
			</div>
		`);
		
		const byPriority = tasks.by_priority || {};
		const labels = Object.keys(byPriority);
		const values = Object.values(byPriority);
		
		if (labels.length === 0) {
			card.find(".chart-container").html(`<div class="text-center text-muted pt-5">${__("No task data")}</div>`);
			return card;
		}
		
		setTimeout(() => {
			const canvas = $("<canvas></canvas>");
			card.find(".chart-container").append(canvas);
			
			const colors = {
				'Urgent': '#dc3545',
				'High': '#fd7e14',
				'Medium': '#ffc107',
				'Low': '#28a745'
			};
			
			const bgColors = labels.map(label => colors[label] || '#6c757d');
			
			try {
				new Chart(canvas[0], {
					type: 'doughnut',
					data: {
						labels: labels,
						datasets: [{
							data: values,
							backgroundColor: bgColors,
							borderWidth: 2,
							borderColor: '#fff'
						}]
					},
					options: {
						responsive: true,
						maintainAspectRatio: false,
						plugins: {
							legend: {
								position: 'bottom',
								labels: { padding: 10, font: { size: 11 } }
							}
						}
					}
				});
				console.log("✅ Priority Chart: Rendered");
			} catch (err) {
				console.error("❌ Priority Chart: Error", err);
			}
		}, 100);
		
		return card;
	},

	create_financial_chart(financial) {
		console.log("🔍 Dashboard: Creating financial chart", financial);
		
		const card = $(`
			<div class="chart-card">
				<div class="chart-card-title">💰 ${__("Cost Breakdown")}</div>
				<div class="chart-container" style="height: 250px;"></div>
			</div>
		`);
		
		const breakdown = financial.breakdown || {};
		console.log("🔍 Dashboard: Financial breakdown data", breakdown);
		
		const chartData = {
			labels: [__("Timesheet"), __("Purchases"), __("Expenses")],
			datasets: [{
				data: [
					breakdown.timesheet_cost || 0,
					breakdown.purchase_cost || 0,
					breakdown.expense_claims || 0
				],
				backgroundColor: ['#667eea', '#764ba2', '#f093fb']
			}]
		};
		
		console.log("🔍 Dashboard: Chart data prepared", chartData);
		
		setTimeout(() => {
			const canvas = $("<canvas></canvas>");
			card.find(".chart-container").append(canvas);
			
			const total = chartData.datasets[0].data.reduce((a, b) => a + b, 0);
			console.log("📊 Financial Chart: Total =", total, "Data:", chartData.datasets[0].data);
			
			if (total === 0) {
				card.find(".chart-container").html(`
					<div class="text-center text-muted pt-5">
						<p class="mb-2">${__("No cost data available")}</p>
						<small>${__("Costs will appear once timesheet, purchases, or expenses are logged")}</small>
					</div>
				`);
				return;
			}
			
			try {
				new Chart(canvas[0], {
					type: 'doughnut',
					data: {
						labels: chartData.labels,
						datasets: [{
							data: chartData.datasets[0].data,
							backgroundColor: ['#667eea', '#764ba2', '#f093fb'],
							borderWidth: 2,
							borderColor: '#fff'
						}]
					},
					options: {
						responsive: true,
						maintainAspectRatio: false,
						plugins: {
							legend: {
								position: 'bottom',
								labels: { padding: 15, font: { size: 12 } }
							}
						}
					}
				});
				console.log("✅ Financial Chart: Rendered successfully");
			} catch (err) {
				console.error("❌ Financial Chart: Error rendering", err);
			}
		}, 100);
		
		return card;
	},

	create_task_status_chart(tasks) {
		console.log("🔍 Dashboard: Creating task status chart", tasks);
		
		const card = $(`
			<div class="chart-card">
				<div class="chart-card-title">📊 ${__("Tasks by Status")}</div>
				<div class="chart-container" style="height: 250px;"></div>
			</div>
		`);
		
		const byStatus = tasks.by_status || {};
		console.log("🔍 Dashboard: Task by_status data", byStatus);
		
		const labels = Object.keys(byStatus);
		const values = Object.values(byStatus);
		console.log("🔍 Dashboard: Chart labels/values", {labels, values});
		
		setTimeout(() => {
			const canvas = $("<canvas></canvas>");
			card.find(".chart-container").append(canvas);
			
			if (labels.length === 0) {
				card.find(".chart-container").html(`<div class="text-center text-muted pt-5">${__("No task data available")}</div>`);
				return;
			}
			
			try {
				new Chart(canvas[0], {
					type: 'bar',
					data: {
						labels: labels,
						datasets: [{
							label: __('Tasks'),
							data: values,
							backgroundColor: '#28a745',
							borderColor: '#1e7e34',
							borderWidth: 1
						}]
					},
					options: {
						responsive: true,
						maintainAspectRatio: false,
						plugins: {
							legend: { display: false }
						},
						scales: {
							y: {
								beginAtZero: true,
								ticks: { stepSize: 1 }
							}
						}
					}
				});
				console.log("✅ Task Status Chart: Rendered with", labels.length, "statuses");
			} catch (err) {
				console.error("❌ Task Status Chart: Error", err);
			}
		}, 100);
		
		return card;
	},

	create_cost_trend_chart(trends) {
		const card = $(`
			<div class="chart-card">
				<div class="chart-card-title">📈 ${__("Cost Trend")}</div>
				<div class="chart-container" style="height: 250px;"></div>
			</div>
		`);
		
		const costTrend = trends.cost_trend || [];
		
		if (costTrend.length === 0) {
			card.find(".chart-container").html(`<div class="text-center text-muted pt-5">${__("No cost data available")}</div>`);
			return card;
		}
		
		const labels = costTrend.map(d => frappe.datetime.str_to_user(d.date));
		const values = costTrend.map(d => d.amount);
		
		setTimeout(() => {
			const canvas = $("<canvas></canvas>");
			card.find(".chart-container").append(canvas);
			
			try {
				new Chart(canvas[0], {
					type: 'line',
					data: {
						labels: labels,
						datasets: [{
							label: __('Cumulative Cost'),
							data: values,
							borderColor: '#dc3545',
							backgroundColor: 'rgba(220, 53, 69, 0.1)',
							borderWidth: 2,
							fill: true,
							tension: 0.4
						}]
					},
					options: {
						responsive: true,
						maintainAspectRatio: false,
						plugins: {
							legend: { display: false }
						},
						scales: {
							y: { beginAtZero: true }
						}
					}
				});
				console.log("✅ Cost Trend Chart: Rendered with", labels.length, "points");
			} catch (err) {
				console.error("❌ Cost Trend Chart: Error", err);
			}
		}, 100);
		
		return card;
	},

	create_completion_trend_chart(trends) {
		const card = $(`
			<div class="chart-card">
				<div class="chart-card-title">✅ ${__("Tasks Completed (Weekly)")}</div>
				<div class="chart-container" style="height: 250px;"></div>
			</div>
		`);
		
		const completions = trends.task_completion || [];
		
		if (completions.length === 0) {
			card.find(".chart-container").html(`<div class="text-center text-muted pt-5">${__("No completion data available")}</div>`);
			return card;
		}
		
		const labels = completions.map(d => frappe.datetime.str_to_user(d.week));
		const values = completions.map(d => d.count);
		
		setTimeout(() => {
			const canvas = $("<canvas></canvas>");
			card.find(".chart-container").append(canvas);
			
			try {
				new Chart(canvas[0], {
					type: 'bar',
					data: {
						labels: labels,
						datasets: [{
							label: __('Tasks Completed'),
							data: values,
							backgroundColor: '#17a2b8',
							borderColor: '#117a8b',
							borderWidth: 1
						}]
					},
					options: {
						responsive: true,
						maintainAspectRatio: false,
						plugins: {
							legend: { display: false }
						},
						scales: {
							y: {
								beginAtZero: true,
								ticks: { stepSize: 1 }
							}
						}
					}
				});
				console.log("✅ Completion Trend Chart: Rendered with", labels.length, "weeks");
			} catch (err) {
				console.error("❌ Completion Trend Chart: Error", err);
			}
		}, 100);
		
		return card;
	},

	add_dashboard_toolbar(frm) {
		// Remove previous buttons if any
		frm.page.remove_inner_button("Export PDF", "Dashboard");
		frm.page.remove_inner_button("Print Dashboard");
		
		// Add export PDF button
		frm.page.add_inner_button(__("Export PDF"), () => {
			frm.events.export_dashboard_pdf(frm);
		}, __("Dashboard"));
		
		// Add print button
		frm.page.add_inner_button(__("Print Dashboard"), () => {
			window.print();
		});
	},
	
	export_dashboard_pdf(frm) {
		const data = frm.__dashboard_data;
		if (!data) {
			frappe.msgprint(__("Please load dashboard data first"));
			return;
		}
		
		frappe.show_alert({
			message: __("Preparing PDF export..."),
			indicator: "blue"
		});
		
		// Create printable HTML
		const html = frm.events.generate_dashboard_html(frm, data);
		
		// Open print preview in new window
		const printWindow = window.open('', '_blank');
		printWindow.document.write(html);
		printWindow.document.close();
		
		// Trigger print after a short delay to allow content to render
		setTimeout(() => {
			printWindow.print();
		}, 500);
	},
	
	generate_dashboard_html(frm, data) {
		const financial = data.financial || {};
		const timeline = data.timeline || {};
		const tasks = data.tasks || {};
		const team = data.team || {};
		const health = data.health || {};
		const project_info = data.project_info || {};
		
		return `
		<!DOCTYPE html>
		<html>
		<head>
			<title>Project Dashboard - ${project_info.project_name || project_info.name}</title>
			<style>
				@media print {
					@page { margin: 1cm; }
				}
				body {
					font-family: Arial, sans-serif;
					padding: 20px;
					color: #333;
				}
				.header {
					text-align: center;
					border-bottom: 3px solid #667eea;
					padding-bottom: 20px;
					margin-bottom: 30px;
				}
				.header h1 {
					margin: 0;
					color: #667eea;
				}
				.header p {
					margin: 5px 0;
					color: #666;
				}
				.kpi-grid {
					display: grid;
					grid-template-columns: repeat(3, 1fr);
					gap: 15px;
					margin-bottom: 30px;
				}
				.kpi-box {
					border: 1px solid #ddd;
					padding: 15px;
					border-radius: 8px;
					text-align: center;
				}
				.kpi-box h3 {
					margin: 0 0 10px 0;
					font-size: 14px;
					color: #666;
					font-weight: normal;
				}
				.kpi-box .value {
					font-size: 24px;
					font-weight: bold;
					color: #333;
				}
				.kpi-box .subtitle {
					font-size: 12px;
					color: #999;
					margin-top: 5px;
				}
				.health-section {
					background: #f8f9fa;
					padding: 20px;
					border-radius: 8px;
					margin-bottom: 30px;
					text-align: center;
				}
				.health-score {
					font-size: 48px;
					font-weight: bold;
					color: ${health.level === 'excellent' ? '#28a745' : health.level === 'good' ? '#17a2b8' : health.level === 'warning' ? '#ffc107' : '#dc3545'};
				}
				.section {
					margin-bottom: 30px;
					page-break-inside: avoid;
				}
				.section h2 {
					border-bottom: 2px solid #667eea;
					padding-bottom: 10px;
					color: #667eea;
				}
				table {
					width: 100%;
					border-collapse: collapse;
					margin-top: 10px;
				}
				th, td {
					padding: 10px;
					text-align: left;
					border-bottom: 1px solid #ddd;
				}
				th {
					background: #f8f9fa;
					font-weight: bold;
				}
				.footer {
					margin-top: 40px;
					text-align: center;
					font-size: 12px;
					color: #999;
					border-top: 1px solid #ddd;
					padding-top: 20px;
				}
			</style>
		</head>
		<body>
			<div class="header">
				<h1>Project Management Dashboard</h1>
				<p><strong>${project_info.project_name || project_info.name}</strong></p>
				<p>Generated on: ${new Date().toLocaleString()}</p>
			</div>
			
			<div class="health-section">
				<h2 style="margin-top:0;">Project Health Score</h2>
				<div class="health-score">${health.score || 0}/100</div>
				<p style="font-size:16px; margin:10px 0;">${health.level === 'excellent' ? 'Excellent' : health.level === 'good' ? 'Good' : health.level === 'warning' ? 'Needs Attention' : 'At Risk'}</p>
			</div>
			
			<div class="kpi-grid">
				<div class="kpi-box">
					<h3>💰 Actual Cost</h3>
					<div class="value">${frappe.format(financial.actual_cost || 0, {fieldtype: 'Currency'})}</div>
					<div class="subtitle">${financial.budget_variance_pct ? (financial.budget_variance_pct > 0 ? '+' : '') + financial.budget_variance_pct.toFixed(1) + '%' : ''}</div>
				</div>
				<div class="kpi-box">
					<h3>💵 Revenue</h3>
					<div class="value">${frappe.format(financial.total_revenue || 0, {fieldtype: 'Currency'})}</div>
					<div class="subtitle">Billed: ${frappe.format(financial.total_billed || 0, {fieldtype: 'Currency'})}</div>
				</div>
				<div class="kpi-box">
					<h3>📊 Gross Profit</h3>
					<div class="value">${frappe.format(financial.gross_profit || 0, {fieldtype: 'Currency'})}</div>
					<div class="subtitle">${(financial.profit_margin_pct || 0).toFixed(1)}% margin</div>
				</div>
				<div class="kpi-box">
					<h3>📅 Timeline</h3>
					<div class="value">${timeline.days_remaining >= 0 ? timeline.days_remaining + ' days left' : 'Completed'}</div>
					<div class="subtitle">${(timeline.percent_complete || 0)}% complete</div>
				</div>
				<div class="kpi-box">
					<h3>✅ Tasks</h3>
					<div class="value">${tasks.completed || 0}/${tasks.total || 0}</div>
					<div class="subtitle">${tasks.overdue ? tasks.overdue + ' overdue' : 'None overdue'}</div>
				</div>
				<div class="kpi-box">
					<h3>👥 Team</h3>
					<div class="value">${team.total_hours || 0} hrs</div>
					<div class="subtitle">${team.team_size || 0} members</div>
				</div>
			</div>
			
			<div class="section">
				<h2>Financial Breakdown</h2>
				<table>
					<tr>
						<th>Metric</th>
						<th>Amount</th>
					</tr>
					<tr>
						<td>Estimated Budget</td>
						<td>${frappe.format(financial.estimated_budget || 0, {fieldtype: 'Currency'})}</td>
					</tr>
					<tr>
						<td>Actual Cost</td>
						<td>${frappe.format(financial.actual_cost || 0, {fieldtype: 'Currency'})}</td>
					</tr>
					<tr>
						<td>Timesheet Cost</td>
						<td>${frappe.format(financial.breakdown?.timesheet_cost || 0, {fieldtype: 'Currency'})}</td>
					</tr>
					<tr>
						<td>Purchase Cost</td>
						<td>${frappe.format(financial.breakdown?.purchase_cost || 0, {fieldtype: 'Currency'})}</td>
					</tr>
					<tr>
						<td>Total Revenue</td>
						<td>${frappe.format(financial.total_revenue || 0, {fieldtype: 'Currency'})}</td>
					</tr>
					<tr>
						<td><strong>Gross Profit</strong></td>
						<td><strong>${frappe.format(financial.gross_profit || 0, {fieldtype: 'Currency'})}</strong></td>
					</tr>
				</table>
			</div>
			
			<div class="section">
				<h2>Task Status</h2>
				<table>
					<tr>
						<th>Status</th>
						<th>Count</th>
					</tr>
					${Object.entries(tasks.by_status || {}).map(([status, count]) => `
						<tr>
							<td>${status}</td>
							<td>${count}</td>
						</tr>
					`).join('')}
				</table>
			</div>
			
			<div class="footer">
				<p>Generated by ERPNext | ${frappe.boot.sitename}</p>
			</div>
		</body>
		</html>
		`;
	},
	
	render_tables(frm, data) {
		const tablesDiv = $("<div class='dashboard-charts-grid'></div>");
		
		// Overdue Tasks Table
		const overdueCard = frm.events.create_overdue_tasks_table(data.tasks);
		tablesDiv.append(overdueCard);
		
		// Milestones Table
		const milestoneCard = frm.events.create_milestone_summary(data.timeline);
		tablesDiv.append(milestoneCard);
		
		return tablesDiv;
	},

	create_overdue_tasks_table(tasks) {
		const card = $(`
			<div class="chart-card">
				<div class="chart-card-title">⚠️ ${__("Overdue Tasks")}</div>
				<div class="table-container"></div>
			</div>
		`);
		
		const overdueTasks = tasks.overdue_tasks || [];
		
		if (overdueTasks.length === 0) {
			card.find(".table-container").html(`<div class="text-center text-muted py-4">${__("No overdue tasks")}</div>`);
			return card;
		}
		
		const table = $(`
			<table class="dashboard-table">
				<thead>
					<tr>
						<th>${__("Task")}</th>
						<th>${__("Due Date")}</th>
						<th>${__("Priority")}</th>
					</tr>
				</thead>
				<tbody></tbody>
			</table>
		`);
		
		const tbody = table.find("tbody");
		overdueTasks.forEach(task => {
			const row = $(`
				<tr style="cursor: pointer;">
					<td><a href="/app/task/${task.name}">${task.name}</a></td>
					<td>${frappe.datetime.str_to_user(task.exp_end_date)}</td>
					<td><span class="badge bg-${task.priority === 'High' || task.priority === 'Urgent' ? 'danger' : 'warning'}">${task.priority}</span></td>
				</tr>
			`);
			row.on("click", () => frappe.set_route("Form", "Task", task.name));
			tbody.append(row);
		});
		
		card.find(".table-container").append(table);
		return card;
	},

	create_milestone_summary(timeline) {
		const card = $(`
			<div class="chart-card">
				<div class="chart-card-title">🎯 ${__("Milestones")}</div>
				<div class="milestone-summary"></div>
			</div>
		`);
		
		const milestones = timeline.milestones || {};
		const total = milestones.total || 0;
		const completed = milestones.completed || 0;
		const pending = milestones.pending || 0;
		
		const summary = $(`
			<div>
				<div class="d-flex justify-content-between mb-3">
					<div>
						<div class="h2 mb-0">${completed}/${total}</div>
						<small class="text-muted">${__("Completed")}</small>
					</div>
					<div class="text-end">
						<div class="h2 mb-0 text-warning">${pending}</div>
						<small class="text-muted">${__("Pending")}</small>
					</div>
				</div>
				<div class="mini-progress">
					<div class="mini-progress-bar" style="width: ${total ? (completed / total * 100) : 0}%"></div>
				</div>
				<div class="text-center mt-2 small text-muted">
					${total ? ((completed / total * 100).toFixed(0)) : 0}% ${__("milestone completion")}
				</div>
			</div>
		`);
		
		card.find(".milestone-summary").append(summary);
		return card;
	},
});

