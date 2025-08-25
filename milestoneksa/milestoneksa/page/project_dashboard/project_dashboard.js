// File: milestoneksa/milestoneksa/page/project_dashboard/project_dashboard.js

// Ensure frappe-gantt and frappe-charts are loaded via HTML or hooks before this script runs.

frappe.pages['project_dashboard'].on_page_load = function(wrapper) {
    // Create the dashboard page
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Project Dashboard',
        single_column: true
    });

    // --- View Mode Selector (default to Monthly) ---
    $(page.main).append(`
        <div style="margin-top: 10px;">
            <label for="gantt-view-mode" style="margin-right:8px;">View Mode:</label>
            <select id="gantt-view-mode">
                <option value="Month" selected>Monthly</option>
                <option value="Week">Weekly</option>
                <option value="Year">Yearly</option>
            </select>
        </div>
    `);

    // --- Project Link Field ---
    page.add_field({
        label: 'Project',
        fieldname: 'project',
        fieldtype: 'Link',
        options: 'Project',
        change: function() {
            const project = page.fields_dict.project.get_value();
            if (project) {
                load_project_dashboard(project);
            }
        }
    });

    // --- Chart Containers: Gantt + 4 charts in a 2×2 grid ---
    $(page.main).append(`
        <div id="gantt-container" style="height:400px; margin-top:20px; overflow-x:auto; border:1px solid #e0e0e0;"></div>

        <div class="chart-grid" style="
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin-top: 20px;
        ">
            <div id="status-chart" class="chart-block" style="height:260px;"></div>
            <div id="priority-chart" class="chart-block" style="height:260px;"></div>
            <div id="budget-chart" class="chart-block" style="height:260px;"></div>
            <div id="pending-chart" class="chart-block" style="height:260px;"></div>
        </div>
    `);

    // --- Switch Gantt View Mode on Dropdown Change ---
    $(page.main).on('change', '#gantt-view-mode', function() {
        const mode = $(this).val();
        if (window.ganttChart) {
            window.ganttChart.change_view_mode(mode);
        }
    });
};

async function load_project_dashboard(project) {
    frappe.dom.freeze('Loading dashboard...');
    try {
        const r = await frappe.call({
            method: 'milestoneksa.milestoneksa.page.project_dashboard.project_dashboard.get_project_dashboard_data',
            args: { project_name: project }
        });
        const data = r.message;
        if (data) {
            const viewMode = $('#gantt-view-mode').val() || 'Month';
            renderGanttChart(data.tasks, viewMode);
            renderStatusChart(data.status_counts);
            renderPriorityChart(data.priority_counts);
            renderBudgetChart(data.project);
            renderPendingChart(data.pending_counts);
        } else {
            frappe.msgprint(__('No data found for project: {0}', [project]));
        }
    } finally {
        frappe.dom.unfreeze();
    }
}

/**
 * Render the Gantt chart for the given tasks.
 * @param {Array} tasks
 * @param {String} view_mode  - 'Week' | 'Month' | 'Year'
 */
function renderGanttChart(tasks, view_mode = 'Month') {
    // Sort tasks by start date (oldest first)
    tasks.sort((a, b) => new Date(a.exp_start_date) - new Date(b.exp_start_date));

    const ganttData = tasks.map(t => ({
        id: t.name,
        name: t.subject || t.name,
        start: t.exp_start_date || frappe.datetime.get_today(),
        end: t.exp_end_date || t.exp_start_date || frappe.datetime.get_today(),
        progress: (t.status === 'Completed' ? 100 : (t.progress || 0)),
       dependencies: Array.isArray(t.depends_on_tasks)
        ? t.depends_on_tasks.join(',')
        : (typeof t.depends_on_tasks === 'string' ? t.depends_on_tasks : '')
    }));

    $('#gantt-container').empty();
    if (ganttData.length) {
        window.ganttChart = new Gantt("#gantt-container", ganttData, {
            view_mode: view_mode,
            date_format: "YYYY-MM-DD"
        });
    }
}

function renderStatusChart(status_counts) {
    const labels = Object.keys(status_counts);
    const values = labels.map(l => status_counts[l] || 0);

    $('#status-chart').empty();
    new frappe.Chart('#status-chart', {
        data: { labels, datasets: [{ values }] },
        type: 'pie',
        height: 250
    });
}

function renderPriorityChart(priority_counts) {
    const labels = Object.keys(priority_counts);
    const values = labels.map(l => priority_counts[l] || 0);

    $('#priority-chart').empty();
    new frappe.Chart('#priority-chart', {
        data: { labels, datasets: [{ values }] },
        type: 'pie',
        height: 250
    });
}

function renderBudgetChart(project) {
    const labels = ['Planned', 'Actual'];
    const values = [project.estimated_cost || 0, project.actual_cost || 0];

    $('#budget-chart').empty();
    new frappe.Chart('#budget-chart', {
        data: { labels, datasets: [{ name: 'Budget', values }] },
        type: 'bar',
        height: 250
    });
}

function renderPendingChart(pending_counts) {
    const labels = Object.keys(pending_counts).map(k => k.replace('Project ', ''));
    const values = labels.map(l => pending_counts['Project ' + l] || pending_counts[l] || 0);

    $('#pending-chart').empty();
    new frappe.Chart('#pending-chart', {
        data: { labels, datasets: [{ values }] },
        type: 'bar',
        height: 250
    });
}
