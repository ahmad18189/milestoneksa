(() => {
  // Which Query Reports should get the button?
  const TARGET_REPORTS = ['Salary Register', 'Monthly Salary Register'];




  console.log('asdasdasdagsuygdyasbgdiahshuidbiasdiabsdbdjabsjkbdnkasbn')
  const attachButton = (report) => {
    const label = __('Download Cairo PDF');
    const handler = () => {
      const filters = (report.get_values && report.get_values()) || {};
      frappe.utils.open_url_post(
        '/api/method/milestoneksa.api.pdf.download_salary_report_pdf',
        { report_name: report.report_name || report.report_name || '', filters: JSON.stringify(filters) }
      );
    };

    // v15 friendly APIs:
    if (report.page && report.page.set_secondary_action && !report.__mksa_btn__) {
      // Visible button near the primary action
      report.page.set_secondary_action(label, handler);
      report.__mksa_btn__ = true;
      return;
    }

    if (report.page && report.page.add_menu_item && !report.__mksa_btn_menu__) {
      // Add under "Menu" as a safe fallback
      report.page.add_menu_item(label, handler);
      report.__mksa_btn_menu__ = true;
      // Optional hint so users notice it:
      frappe.show_alert({ message: __('Find “{0}” in the Menu', [label]), indicator: 'blue' });
      return;
    }

    // Ultimate fallback: DOM inject (works across builds)
    try {
      const $page = (report.page && report.page.$page) || $('.page-container');
      if ($page.length && !report.__mksa_btn_dom__) {
        const $actions = $page.find('.page-actions');
        const $btn = $(
          `<button class="btn btn-sm btn-secondary">${label}</button>`
        ).on('click', handler);
        $actions.prepend($btn);
        report.__mksa_btn_dom__ = true;
      }
    } catch (e) {
      console.warn('MKSA Cairo PDF button DOM fallback failed:', e);
    }
  };

  // Register per-report onload hooks
  TARGET_REPORTS.forEach((name) => {
    frappe.query_reports[name] = frappe.query_reports[name] || {};
    const prev_onload = frappe.query_reports[name].onload;
    frappe.query_reports[name].onload = function (report) {
      try { attachButton(report); } catch (e) { console.error(e); }
      if (typeof prev_onload === 'function') {
        try { prev_onload(report); } catch (e) { console.error(e); }
      }
    };
  });
})();
