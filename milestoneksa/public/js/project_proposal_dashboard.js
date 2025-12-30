// Project Proposal Dashboard JavaScript
// Comprehensive dashboard with summary from all tabs, charts, and management decision-making tools

frappe.ui.form.on('Project Proposal', {
	refresh: function(frm) {
		// Always render dashboard when on dashboard tab
		if (frm.current_dialog) return;
		
		// Wait a bit for form to fully load
		setTimeout(() => {
			frm.events.render_dashboard(frm);
		}, 500);
	},

	// Helper function to format currency with Riyal symbol
	format_currency_with_symbol: function(amount, currency) {
		if (!amount) amount = 0;
		const formatted = format_currency(amount, currency || 'SAR', 0);
		const riyalSymbol = '<img src="/files/Riyal_Symbol.svg" style="height: 1.25em; width: 1.5em !important; vertical-align: middle; display: inline-block;">';
		// Replace SAR with symbol
		return formatted.replace(/SAR/g, riyalSymbol);
	},

	after_save: function(frm) {
		setTimeout(() => {
			frm.events.render_dashboard(frm);
		}, 300);
	},

	render_dashboard: function(frm) {
		try {
			const field = frm.fields_dict.dashboard_html;
			if (!field) {
				console.warn('Project Proposal Dashboard: dashboard_html field not found');
				return;
			}

			const wrapper = field.$wrapper;
			if (!wrapper || wrapper.length === 0) {
				console.warn('Project Proposal Dashboard: wrapper not found');
				return;
			}

			// Clear and setup wrapper
			wrapper.empty().addClass("project-proposal-dashboard-wrapper").css({
				"padding": "20px",
				"background": "#f8f9fa",
				"min-height": "800px"
			});

			if (frm.is_new()) {
				wrapper.append(
					$("<div class='alert alert-info'>").text(__("Save the project proposal to view the dashboard."))
				);
				return;
			}

			// Show loading indicator
			wrapper.append($('<div class="text-center" style="padding: 40px;"><i class="fa fa-spinner fa-spin fa-2x"></i><p>' + __("Loading dashboard...") + '</p></div>'));

			// Load Chart.js if not already loaded
			if (typeof Chart === 'undefined') {
				frappe.require('https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js', () => {
					console.log('Chart.js loaded successfully');
					frm.events.init_dashboard_content(frm, wrapper);
				}, () => {
					console.error('Failed to load Chart.js');
					wrapper.empty().append($('<div class="alert alert-danger">Failed to load Chart.js library. Please refresh the page.</div>'));
				});
			} else {
				console.log('Chart.js already available');
				frm.events.init_dashboard_content(frm, wrapper);
			}
		} catch (error) {
			console.error('Error in render_dashboard:', error);
		}
	},

	init_dashboard_content: function(frm, wrapper) {
		try {
			// Clear loading indicator
			wrapper.empty();
			
			// Add CSS styles
			wrapper.append(frm.events.get_dashboard_styles());

			// Create main dashboard container
			const dashboard = $('<div class="dashboard-main-container">').appendTo(wrapper);

		// Executive Summary Section (Full Width)
		frm.events.render_executive_summary(frm, dashboard);

		// Key Metrics KPI Cards (Top Row)
		frm.events.render_kpi_cards(frm, dashboard);

		// Charts Row 1: Financial & Progress
		const chartsRow1 = $('<div class="charts-row">').appendTo(dashboard);
		frm.events.render_financial_charts(frm, chartsRow1);
		frm.events.render_progress_charts(frm, chartsRow1);

		// Charts Row 2: Timeline & Team
		const chartsRow2 = $('<div class="charts-row">').appendTo(dashboard);
		frm.events.render_timeline_chart(frm, chartsRow2);
		frm.events.render_team_chart(frm, chartsRow2);

		// Summary Sections from All Tabs
		frm.events.render_tabs_summary(frm, dashboard);

		// Decision Support Section
		frm.events.render_decision_support(frm, dashboard);
		} catch (error) {
			console.error('Error in init_dashboard_content:', error);
			wrapper.empty().append($('<div class="alert alert-danger">Error loading dashboard: ' + error.message + '</div>'));
		}
	},

	get_dashboard_styles: function() {
		return $(`
			<style>
				.project-proposal-dashboard-wrapper {
					font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
				}
				.dashboard-main-container {
					max-width: 1400px;
					margin: 0 auto;
				}
				.executive-summary {
					background: #2c3e50;
					color: white;
					border-radius: 12px;
					padding: 30px;
					margin-bottom: 30px;
					box-shadow: 0 4px 6px rgba(0,0,0,0.1);
					border-left: 4px solid #3498db;
				}
				.executive-summary h2 {
					margin-top: 0;
					color: white;
					font-size: 24px;
					margin-bottom: 20px;
				}
				.executive-summary-grid {
					display: grid;
					grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
					gap: 20px;
					margin-top: 20px;
				}
				.executive-metric {
					background: rgba(255,255,255,0.2);
					padding: 15px;
					border-radius: 8px;
					backdrop-filter: blur(10px);
				}
				.executive-metric-label {
					font-size: 12px;
					opacity: 0.9;
					margin-bottom: 5px;
				}
				.executive-metric-value {
					font-size: 24px;
					font-weight: bold;
				}
				.kpi-cards {
					display: grid;
					grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
					gap: 20px;
					margin-bottom: 30px;
				}
				.kpi-card {
					background: white;
					border-radius: 12px;
					padding: 20px;
					box-shadow: 0 2px 8px rgba(0,0,0,0.1);
					border-left: 4px solid #5e64ff;
					transition: transform 0.2s;
				}
				.kpi-card:hover {
					transform: translateY(-4px);
					box-shadow: 0 4px 12px rgba(0,0,0,0.15);
				}
				.kpi-card.good { border-left-color: #28a745; }
				.kpi-card.warning { border-left-color: #ffc107; }
				.kpi-card.danger { border-left-color: #dc3545; }
				.kpi-label {
					color: #74808a;
					font-size: 13px;
					margin-bottom: 8px;
				}
				.kpi-value {
					color: #36414C;
					font-size: 28px;
					font-weight: 700;
					margin-bottom: 5px;
				}
				.kpi-change {
					font-size: 12px;
					color: #74808a;
				}
				.charts-row {
					display: grid;
					grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
					gap: 20px;
					margin-bottom: 30px;
				}
				.dashboard-card {
					background: white;
					border-radius: 12px;
					padding: 25px;
					box-shadow: 0 2px 8px rgba(0,0,0,0.1);
				}
				.dashboard-card h3 {
					margin-top: 0;
					color: #36414C;
					font-size: 18px;
					border-bottom: 2px solid #5e64ff;
					padding-bottom: 12px;
					margin-bottom: 20px;
					display: flex;
					align-items: center;
				}
				.dashboard-card h3:before {
					content: "📊";
					margin-right: 10px;
				}
				.chart-container {
					position: relative;
					height: 300px;
					margin-top: 15px;
				}
				.summary-section {
					background: white;
					border-radius: 12px;
					padding: 25px;
					margin-bottom: 20px;
					box-shadow: 0 2px 8px rgba(0,0,0,0.1);
				}
				.summary-section h3 {
					margin-top: 0;
					color: #36414C;
					font-size: 18px;
					border-bottom: 2px solid #5e64ff;
					padding-bottom: 12px;
					margin-bottom: 20px;
				}
				.summary-grid {
					display: grid;
					grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
					gap: 15px;
				}
				.summary-item {
					padding: 12px;
					background: #f8f9fa;
					border-radius: 6px;
					border-left: 3px solid #5e64ff;
				}
				.summary-label {
					color: #74808a;
					font-size: 12px;
					margin-bottom: 5px;
				}
				.summary-value {
					color: #36414C;
					font-weight: 600;
					font-size: 14px;
				}
				.decision-support {
					background: #ffffff;
					color: #36414C;
					border-radius: 12px;
					padding: 30px;
					margin-top: 30px;
					box-shadow: 0 2px 8px rgba(0,0,0,0.1);
					border-left: 4px solid #5e64ff;
				}
				.decision-support h3 {
					color: #36414C;
					margin-top: 0;
					border-bottom: 2px solid #e0e0e0;
					padding-bottom: 15px;
				}
				.decision-item {
					background: #f8f9fa;
					padding: 15px;
					border-radius: 8px;
					margin-bottom: 15px;
					border-left: 3px solid #5e64ff;
				}
				.decision-item strong {
					display: block;
					margin-bottom: 8px;
					font-size: 14px;
					color: #36414C;
				}
				.decision-item {
					color: #74808a;
				}
				.decision-item.success {
					border-left-color: #28a745;
					background: #f0f9f4;
				}
				.decision-item.warning {
					border-left-color: #ffc107;
					background: #fffbf0;
				}
				.decision-item.danger {
					border-left-color: #dc3545;
					background: #fff5f5;
				}
				.status-badge {
					display: inline-block;
					padding: 4px 12px;
					border-radius: 12px;
					font-size: 12px;
					font-weight: 600;
				}
				.status-draft { background: #f0f0f0; color: #74808a; }
				.status-pending { background: #fff4e5; color: #f39c12; }
				.status-approved { background: #e8f5e9; color: #2e7d32; }
				.status-execution { background: #e3f2fd; color: #1976d2; }
				.status-completed { background: #c8e6c9; color: #1b5e20; }
				.status-rejected { background: #ffebee; color: #c62828; }
				.alert-box {
					padding: 15px;
					border-radius: 8px;
					margin: 10px 0;
				}
				.alert-success {
					background: #d4edda;
					border-left: 4px solid #28a745;
					color: #155724;
				}
				.alert-warning {
					background: #fff3cd;
					border-left: 4px solid #ffc107;
					color: #856404;
				}
				.alert-danger {
					background: #f8d7da;
					border-left: 4px solid #dc3545;
					color: #721c24;
				}
			</style>
		`);
	},

	render_executive_summary: function(frm, container) {
		const summary = $('<div class="executive-summary">').appendTo(container);
		summary.append('<h2>📋 ' + __("Executive Summary") + '</h2>');
		
		const summaryGrid = $('<div class="executive-summary-grid">').appendTo(summary);
		
		const projectName = frm.doc.project_name || __('N/A');
		const projectType = frm.doc.project_type || __('N/A');
		const status = frm.doc.status || 'Draft';
		const estimatedCost = frm.doc.estimated_total_cost || 0;
		const estimatedROI = frm.doc.estimated_roi || 0;
		const progress = frm.doc.progress_percentage || 0;
		
		// Calculate totals from child tables
		const teamCount = (frm.doc.team_members || []).length;
		const evaluationReports = (frm.doc.evaluation_reports || []).length;
		const licensesCount = (frm.doc.licenses || []).length;
		const approvedLicenses = (frm.doc.licenses || []).filter(l => l.status === 'Approved').length;
		const contractorOffers = (frm.doc.contractor_offers || []).length;
		const weeklyReports = (frm.doc.weekly_reports || []).length;
		const monthlyReports = (frm.doc.monthly_financial_reports || []).length;
		
		// Calculate BOQ total
		let boqTotal = 0;
		(frm.doc.feasibility_items || []).forEach(item => {
			if (item.item_type === 'BOQ Item' && item.amount) {
				boqTotal += parseFloat(item.amount) || 0;
			}
		});
		
		const metrics = [
			{ label: __("Project Status"), value: status, icon: '📊', isHtml: false },
			{ label: __("Total Cost (SAR)"), value: frm.events.format_currency_with_symbol(estimatedCost), icon: '💰', isHtml: true },
			{ label: __("ROI (%)"), value: estimatedROI + '%', icon: '📈', isHtml: false },
			{ label: __("Progress"), value: progress + '%', icon: '⚡', isHtml: false },
			{ label: __("Team Members"), value: teamCount, icon: '👥', isHtml: false },
			{ label: __("Licenses"), value: approvedLicenses + '/' + licensesCount, icon: '📜', isHtml: false },
		];
		
		metrics.forEach(metric => {
			const metricDiv = $('<div class="executive-metric">').appendTo(summaryGrid);
			$('<div class="executive-metric-label">').text(metric.label).appendTo(metricDiv);
			const valueDiv = $('<div class="executive-metric-value">').html(metric.icon + ' ').appendTo(metricDiv);
			if (metric.isHtml) {
				valueDiv.append(metric.value);
			} else {
				valueDiv.append(metric.value);
			}
		});
	},

	render_kpi_cards: function(frm, container) {
		const kpiContainer = $('<div class="kpi-cards">').appendTo(container);
		
		const estimatedCost = frm.doc.estimated_total_cost || 0;
		const initialCost = frm.doc.initial_estimated_cost || 0;
		const contractAmount = frm.doc.contract_amount || 0;
		const costVariance = contractAmount > 0 ? ((contractAmount - estimatedCost) / estimatedCost * 100).toFixed(1) : 0;
		
		const kpis = [
			{
				label: __("Estimated Cost"),
				value: frm.events.format_currency_with_symbol(estimatedCost),
				change: initialCost > 0 ? ((estimatedCost - initialCost) / initialCost * 100).toFixed(1) + '%' : __('N/A'),
				type: estimatedCost > 10000000 ? 'warning' : 'good',
				isHtml: true
			},
			{
				label: __("Contract Amount"),
				value: frm.events.format_currency_with_symbol(contractAmount),
				change: costVariance + '% ' + __('variance'),
				type: contractAmount > 0 ? 'good' : 'warning',
				isHtml: true
			},
			{
				label: __("Estimated ROI"),
				value: (frm.doc.estimated_roi || 0) + '%',
				change: __('Annual return'),
				type: (frm.doc.estimated_roi || 0) >= 15 ? 'good' : 'warning'
			},
			{
				label: __("Project Progress"),
				value: (frm.doc.progress_percentage || 0) + '%',
				change: __('Completion'),
				type: (frm.doc.progress_percentage || 0) >= 50 ? 'good' : 'warning'
			},
			{
				label: __('Team Size'),
				value: (frm.doc.team_members || []).length,
				change: __('Members'),
				type: 'good'
			},
			{
				label: __("Weekly Reports"),
				value: (frm.doc.weekly_reports || []).length,
				change: __('Submitted'),
				type: 'good'
			}
		];
		
		kpis.forEach(kpi => {
			const card = $('<div class="kpi-card ' + kpi.type + '">').appendTo(kpiContainer);
			$('<div class="kpi-label">').text(kpi.label).appendTo(card);
			const valueDiv = $('<div class="kpi-value">').appendTo(card);
			if (kpi.isHtml) {
				valueDiv.html(kpi.value);
			} else {
				valueDiv.text(kpi.value);
			}
			$('<div class="kpi-change">').text(kpi.change).appendTo(card);
		});
	},

	render_financial_charts: function(frm, container) {
		const card = $('<div class="dashboard-card">').appendTo(container);
		card.append('<h3>' + __("Financial Analysis") + '</h3>');
		
		// Financial summary
		const financialGrid = $('<div class="summary-grid">').appendTo(card);
		
		const financialData = [
			{ label: __("Initial Estimate"), value: frm.events.format_currency_with_symbol(frm.doc.initial_estimated_cost || 0), isHtml: true },
			{ label: __("Final Estimate"), value: frm.events.format_currency_with_symbol(frm.doc.estimated_total_cost || 0), isHtml: true },
			{ label: __("Contract Amount"), value: frm.events.format_currency_with_symbol(frm.doc.contract_amount || 0), isHtml: true },
			{ label: __("BOQ Total"), value: frm.events.format_currency_with_symbol(frm.doc.total_boq_amount || 0), isHtml: true },
		];
		
		financialData.forEach(item => {
			const summaryItem = $('<div class="summary-item">').appendTo(financialGrid);
			$('<div class="summary-label">').text(item.label).appendTo(summaryItem);
			const valueDiv = $('<div class="summary-value">').appendTo(summaryItem);
			if (item.isHtml) {
				valueDiv.html(item.value);
			} else {
				valueDiv.text(item.value);
			}
		});
		
		// Cash Flow Chart
		if (frm.doc.cash_flow_year_1 || frm.doc.cash_flow_year_2 || frm.doc.cash_flow_year_3) {
			// Add currency label before chart
			const currencyLabel = $('<div style="text-align: center; margin-bottom: 10px; color: #74808a; font-size: 12px;">').html(
				'<img src="/files/Riyal_Symbol.svg" style="height: 1em; width: 1.2em; vertical-align: middle; display: inline-block;"> ' + __("Amount in Saudi Riyal")
			).appendTo(card);
			
			const chartContainer = $('<div class="chart-container">').appendTo(card);
			const canvas = $('<canvas id="cashFlowChart">').appendTo(chartContainer);
			
			setTimeout(() => {
				const ctx = canvas[0].getContext('2d');
				new Chart(ctx, {
					type: 'line',
					data: {
						labels: [__("Year 1"), __("Year 2"), __("Year 3")],
						datasets: [{
							label: __('Cash Flow'),
							data: [
								frm.doc.cash_flow_year_1 || 0,
								frm.doc.cash_flow_year_2 || 0,
								frm.doc.cash_flow_year_3 || 0
							],
							borderColor: '#5e64ff',
							backgroundColor: 'rgba(94, 100, 255, 0.1)',
							tension: 0.4,
							fill: true
						}]
					},
					options: {
						responsive: true,
						maintainAspectRatio: false,
						plugins: {
							legend: { display: true, position: 'top' },
							title: {
								display: true,
								text: __("3-Year Cash Flow Projection")
							},
							tooltip: {
								callbacks: {
									label: function(context) {
										const value = context.parsed.y;
										const formatted = value.toLocaleString('en-US', { maximumFractionDigits: 0 });
										const riyalSymbol = '<img src="/files/Riyal_Symbol.svg" style="height: 1em; width: 1.2em; vertical-align: middle; display: inline-block;">';
										return context.dataset.label + ': ' + formatted + ' ' + riyalSymbol;
									}
								}
							}
						},
						scales: {
							y: {
								beginAtZero: false,
								ticks: {
									callback: function(value) {
										// Format number with commas
										const num = parseFloat(value);
										if (isNaN(num)) return value;
										return num.toLocaleString('en-US', { maximumFractionDigits: 0 });
									}
								},
								title: {
									display: true,
									text: ''
								}
							}
						}
					}
				});
			}, 100);
		}
	},

	render_progress_charts: function(frm, container) {
		const card = $('<div class="dashboard-card">').appendTo(container);
		card.append('<h3>' + __("Progress Tracking") + '</h3>');
		
		// Progress summary
		const progressGrid = $('<div class="summary-grid">').appendTo(card);
		
		const progressData = [
			{ label: __('Overall Progress'), value: (frm.doc.progress_percentage || 0) + '%' },
			{ label: __('Start Date'), value: frm.doc.start_date ? frappe.datetime.str_to_user(frm.doc.start_date) : __('Not Started') },
			{ label: __('Expected Completion'), value: frm.doc.expected_completion_date ? frappe.datetime.str_to_user(frm.doc.expected_completion_date) : __('Not Set') },
			{ label: __("Weekly Reports"), value: (frm.doc.weekly_reports || []).length },
		];
		
		progressData.forEach(item => {
			const summaryItem = $('<div class="summary-item">').appendTo(progressGrid);
			$('<div class="summary-label">').text(item.label).appendTo(summaryItem);
			$('<div class="summary-value">').text(item.value).appendTo(summaryItem);
		});
		
		// Progress Chart
		if (frm.doc.progress_percentage !== undefined) {
			const chartContainer = $('<div class="chart-container">').appendTo(card);
			const canvas = $('<canvas id="progressChart">').appendTo(chartContainer);
			
			setTimeout(() => {
				const ctx = canvas[0].getContext('2d');
				new Chart(ctx, {
					type: 'doughnut',
					data: {
						labels: [__("Completed"), __("Remaining")],
						datasets: [{
							data: [
								frm.doc.progress_percentage || 0,
								100 - (frm.doc.progress_percentage || 0)
							],
							backgroundColor: ['#26a69a', '#e0e0e0']
						}]
					},
					options: {
						responsive: true,
						maintainAspectRatio: false,
						plugins: {
							legend: { position: 'bottom' },
							title: {
								display: true,
								text: __("Project Completion Status")
							}
						}
					}
				});
			}, 100);
		}
	},

	render_timeline_chart: function(frm, container) {
		const card = $('<div class="dashboard-card">').appendTo(container);
		card.append('<h3>' + __("Project Timeline") + '</h3>');
		
		// Timeline data
		const timelineData = [
			{ label: __("Proposal Date"), value: frm.doc.proposal_date ? frappe.datetime.str_to_user(frm.doc.proposal_date) : 'N/A' },
			{ label: __("Deputy CEO Approval"), value: frm.doc.deputy_ceo_approval_date ? frappe.datetime.str_to_user(frm.doc.deputy_ceo_approval_date) : __('Pending') },
			{ label: __("CEO Approval"), value: frm.doc.ceo_approval_date ? frappe.datetime.str_to_user(frm.doc.ceo_approval_date) : __('Pending') },
			{ label: __('Start Date'), value: frm.doc.start_date ? frappe.datetime.str_to_user(frm.doc.start_date) : __('Not Started') },
			{ label: __('Expected Completion'), value: frm.doc.expected_completion_date ? frappe.datetime.str_to_user(frm.doc.expected_completion_date) : __('Not Set') },
			{ label: __("Handover Date"), value: frm.doc.handover_date ? frappe.datetime.str_to_user(frm.doc.handover_date) : __('Pending') },
		];
		
		const timelineGrid = $('<div class="summary-grid">').appendTo(card);
		timelineData.forEach(item => {
			const summaryItem = $('<div class="summary-item">').appendTo(timelineGrid);
			$('<div class="summary-label">').text(item.label).appendTo(summaryItem);
			$('<div class="summary-value">').text(item.value).appendTo(summaryItem);
		});
	},

	render_team_chart: function(frm, container) {
		const card = $('<div class="dashboard-card">').appendTo(container);
		card.append('<h3>' + __("Team Overview") + '</h3>');
		
		const teamCount = (frm.doc.team_members || []).length;
		const teamMetric = $('<div class="summary-item">').appendTo(card);
		$('<div class="summary-label">').text(__("Total Team Members")).appendTo(teamMetric);
		$('<div class="summary-value">').text(teamCount).appendTo(teamMetric);
		
		if (teamCount > 0) {
			// Team roles chart
			const roles = {};
			(frm.doc.team_members || []).forEach(member => {
				const role = member.role || __('Unassigned');
				roles[role] = (roles[role] || 0) + 1;
			});
			
			const chartContainer = $('<div class="chart-container">').appendTo(card);
			const canvas = $('<canvas id="teamChart">').appendTo(chartContainer);
			
			setTimeout(() => {
				const ctx = canvas[0].getContext('2d');
				new Chart(ctx, {
					type: 'pie',
					data: {
						labels: Object.keys(roles),
						datasets: [{
							data: Object.values(roles),
							backgroundColor: ['#5e64ff', '#26a69a', '#ffa726', '#ef5350', '#ab47bc', '#42a5f5']
						}]
					},
					options: {
						responsive: true,
						maintainAspectRatio: false,
						plugins: {
							legend: { position: 'bottom' },
							title: {
								display: true,
								text: __("Team by Role")
							}
						}
					}
				});
			}, 100);
		} else {
			card.append('<p style="color: #74808a; text-align: center; padding: 20px;">' + __("No team members assigned") + '</p>');
		}
	},

	render_tabs_summary: function(frm, container) {
		// Proposal Tab Summary
		const proposalSummary = $('<div class="summary-section">').appendTo(container);
		proposalSummary.append('<h3>📝 ' + __("Proposal Summary") + '</h3>');
		const proposalGrid = $('<div class="summary-grid">').appendTo(proposalSummary);
		
		const proposalData = [
			{ label: __("Project Name"), value: frm.doc.project_name || __('N/A') },
			{ label: __("Project Type"), value: frm.doc.project_type || __('N/A') },
			{ label: __("Location"), value: frm.doc.location ? frm.doc.location.substring(0, 50) + '...' : __('N/A') },
			{ label: __("Proposal Date"), value: frm.doc.proposal_date ? frappe.datetime.str_to_user(frm.doc.proposal_date) : __('N/A') },
		];
		
		proposalData.forEach(item => {
			const summaryItem = $('<div class="summary-item">').appendTo(proposalGrid);
			$('<div class="summary-label">').text(item.label).appendTo(summaryItem);
			$('<div class="summary-value">').text(item.value).appendTo(summaryItem);
		});
		
		// Evaluation Tab Summary
		const evalSummary = $('<div class="summary-section">').appendTo(container);
		evalSummary.append('<h3>📊 ' + __("Evaluation Summary") + '</h3>');
		const evalGrid = $('<div class="summary-grid">').appendTo(evalSummary);
		
		const projectsFeasibleText = frm.doc.projects_mgmt_feasible ? '✓ ' + __('Feasible') : __('Pending');
		const financialFeasibleText = frm.doc.financial_mgmt_feasible ? '✓ ' + __('Feasible') : __('Pending');
		
		const evalData = [
			{ label: __("Projects Management"), value: projectsFeasibleText, isHtml: false },
			{ label: __("Financial Management"), value: financialFeasibleText, isHtml: false },
			{ label: __("Evaluation Reports"), value: (frm.doc.evaluation_reports || []).length, isHtml: false },
			{ label: __("Initial Cost Estimate"), value: frm.events.format_currency_with_symbol(frm.doc.initial_estimated_cost || 0), isHtml: true },
		];
		
		evalData.forEach(item => {
			const summaryItem = $('<div class="summary-item">').appendTo(evalGrid);
			$('<div class="summary-label">').text(item.label).appendTo(summaryItem);
			const valueDiv = $('<div class="summary-value">').appendTo(summaryItem);
			if (item.isHtml) {
				valueDiv.html(item.value);
			} else {
				valueDiv.text(item.value);
			}
		});
		
		// Feasibility Tab Summary
		const feasibilitySummary = $('<div class="summary-section">').appendTo(container);
		feasibilitySummary.append('<h3>💰 ' + __("Feasibility Study Summary") + '</h3>');
		const feasibilityGrid = $('<div class="summary-grid">').appendTo(feasibilitySummary);
		
		const boqItems = (frm.doc.feasibility_items || []).filter(item => item.item_type === 'BOQ Item').length;
		const financialItems = (frm.doc.feasibility_items || []).filter(item => item.item_type === 'Financial Projection').length;
		
		const feasibilityData = [
			{ label: __("BOQ Items"), value: boqItems, isHtml: false },
			{ label: __("BOQ Total"), value: frm.events.format_currency_with_symbol(frm.doc.total_boq_amount || 0), isHtml: true },
			{ label: __("Estimated ROI"), value: (frm.doc.estimated_roi || 0) + '%', isHtml: false },
			{ label: __("Break Even Point"), value: frm.doc.break_even_point || __('N/A'), isHtml: false },
		];
		
		feasibilityData.forEach(item => {
			const summaryItem = $('<div class="summary-item">').appendTo(feasibilityGrid);
			$('<div class="summary-label">').text(item.label).appendTo(summaryItem);
			const valueDiv = $('<div class="summary-value">').appendTo(summaryItem);
			if (item.isHtml) {
				valueDiv.html(item.value);
			} else {
				valueDiv.text(item.value);
			}
		});
		
		// Execution Tab Summary
		const executionSummary = $('<div class="summary-section">').appendTo(container);
		executionSummary.append('<h3>🏗️ ' + __("Execution Summary") + '</h3>');
		const executionGrid = $('<div class="summary-grid">').appendTo(executionSummary);
		
		const licensesCount = (frm.doc.licenses || []).length;
		const approvedLicenses = (frm.doc.licenses || []).filter(l => l.status === 'Approved').length;
		const contractorOffers = (frm.doc.contractor_offers || []).length;
		const selectedContractor = frm.doc.selected_contractor || __('Not Selected');
		
		const executionData = [
			{ label: __("Licenses"), value: approvedLicenses + '/' + licensesCount + ' ' + __('Approved'), isHtml: false },
			{ label: __("Contractor Offers"), value: contractorOffers, isHtml: false },
			{ label: __("Selected Contractor"), value: selectedContractor, isHtml: false },
			{ label: __("Contract Amount"), value: frm.events.format_currency_with_symbol(frm.doc.contract_amount || 0), isHtml: true },
			{ label: __("Weekly Reports"), value: (frm.doc.weekly_reports || []).length, isHtml: false },
			{ label: __("Monthly Reports"), value: (frm.doc.monthly_financial_reports || []).length, isHtml: false },
		];
		
		executionData.forEach(item => {
			const summaryItem = $('<div class="summary-item">').appendTo(executionGrid);
			$('<div class="summary-label">').text(item.label).appendTo(summaryItem);
			const valueDiv = $('<div class="summary-value">').appendTo(summaryItem);
			if (item.isHtml) {
				valueDiv.html(item.value);
			} else {
				valueDiv.text(item.value);
			}
		});
		
		// Handover Tab Summary
		const handoverSummary = $('<div class="summary-section">').appendTo(container);
		handoverSummary.append('<h3>✅ ' + __("Handover Summary") + '</h3>');
		const handoverGrid = $('<div class="summary-grid">').appendTo(handoverSummary);
		
		const handoverItems = (frm.doc.handover_items || []).length;
		const verifiedItems = (frm.doc.handover_items || []).filter(item => item.status === 'Verified').length;
		
		const handoverData = [
			{ label: __("Handover Status"), value: frm.doc.handover_status || __('Pending') },
			{ label: __("Handover Date"), value: frm.doc.handover_date ? frappe.datetime.str_to_user(frm.doc.handover_date) : __('Pending') },
			{ label: __("Handed Over To"), value: frm.doc.handed_over_to || __('N/A') },
			{ label: __("Checklist Items"), value: verifiedItems + '/' + handoverItems + ' ' + __("Verified") },
		];
		
		handoverData.forEach(item => {
			const summaryItem = $('<div class="summary-item">').appendTo(handoverGrid);
			$('<div class="summary-label">').text(item.label).appendTo(summaryItem);
			$('<div class="summary-value">').text(item.value).appendTo(summaryItem);
		});
	},

	render_decision_support: function(frm, container) {
		const decisionSection = $('<div class="decision-support">').appendTo(container);
		decisionSection.append('<h3>🎯 ' + __("Decision Support for Management") + '</h3>');
		
		// Calculate key decision factors
		const estimatedCost = frm.doc.estimated_total_cost || 0;
		const estimatedROI = frm.doc.estimated_roi || 0;
		const progress = frm.doc.progress_percentage || 0;
		const projectsFeasible = frm.doc.projects_mgmt_feasible;
		const financialFeasible = frm.doc.financial_mgmt_feasible;
		const deputyCEOApproval = frm.doc.deputy_ceo_approval;
		const ceoApproval = frm.doc.ceo_approval;
		const licensesCount = (frm.doc.licenses || []).length;
		const approvedLicenses = (frm.doc.licenses || []).filter(l => l.status === 'Approved').length;
		
		// Decision recommendations
		const recommendations = [];
		
		if (estimatedCost > 2000000) {
			recommendations.push({
				type: 'warning',
				title: __("High Value Project"),
				message: __("This project exceeds 2M SAR threshold. Requires CEO final approval.")
			});
		}
		
		if (projectsFeasible && financialFeasible) {
			recommendations.push({
				type: 'success',
				title: __("Feasibility Confirmed"),
				message: __("Both Projects Management and Financial Management confirmed feasibility. Project is ready for approval.")
			});
		} else {
			recommendations.push({
				type: 'warning',
				title: __("Pending Evaluations"),
				message: __("Some evaluations are still pending. Complete all evaluations before proceeding.")
			});
		}
		
		if (approvedLicenses < licensesCount && licensesCount > 0) {
			const pendingCount = licensesCount - approvedLicenses;
			recommendations.push({
				type: 'warning',
				title: __("Incomplete Licenses"),
				message: pendingCount + ' ' + __("license(s) still pending. Ensure all licenses are approved before execution.")
			});
		}
		
		if (estimatedROI >= 20) {
			recommendations.push({
				type: 'success',
				title: __("High ROI Project"),
				message: __("Excellent ROI of {0}%. This is a highly profitable investment opportunity.", [estimatedROI])
			});
		} else if (estimatedROI < 10) {
			recommendations.push({
				type: 'danger',
				title: __("Low ROI Warning"),
				message: __("ROI is below 10%. Review project feasibility and cost structure.")
			});
		}
		
		if (progress > 0 && progress < 25) {
			recommendations.push({
				type: 'warning',
				title: __("Early Stage Project"),
				message: __("Project is in early stages. Monitor closely for any delays or issues.")
			});
		}
		
		recommendations.forEach(rec => {
			const decisionItem = $('<div class="decision-item ' + rec.type + '">').appendTo(decisionSection);
			$('<strong>').text(rec.title).appendTo(decisionItem);
			$('<div>').text(rec.message).appendTo(decisionItem);
		});
		
		// Key Decision Points
		const keyPoints = $('<div style="margin-top: 20px;">').appendTo(decisionSection);
		keyPoints.append('<h4 style="margin-bottom: 15px;">' + __("Key Decision Points") + ':</h4>');
		
		const decisionPoints = [
			{ label: __("Deputy CEO Approval"), status: deputyCEOApproval, required: true },
			{ label: __("CEO Approval"), status: ceoApproval, required: true },
			{ label: __("Projects Management"), status: projectsFeasible, required: true },
			{ label: __("Financial Management"), status: financialFeasible, required: true },
			{ label: __("All Licenses Approved"), status: approvedLicenses === licensesCount && licensesCount > 0, required: licensesCount > 0 },
		];
		
		decisionPoints.forEach(point => {
			const pointDiv = $('<div class="decision-item">').appendTo(keyPoints);
			const statusIcon = point.status ? '✅' : '⏳';
			const statusText = point.status ? __('Completed') : __('Pending');
			$('<strong>').html(`${statusIcon} ${point.label}: ${statusText}`).appendTo(pointDiv);
		});
	}
});
