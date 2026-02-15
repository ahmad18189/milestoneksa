// milestoneksa/public/js/employee_salary_ui.js
// Employee form helpers:
//  - mksa_fetch_salary (renders Salary Structure -> Earnings/Deductions tables in custom HTML field `mksa_salary_html`)
//  - mksa_alter_salary (dialog to change a component amount on Salary Structure; amends if submitted)
//  - mksa_new_additional_salary (opens new Additional Salary prefilled with employee info)

frappe.provide("milestoneksa");

const MKSA = {
  // ---------------- RPC ----------------
  async fetchStructureSnapshot(employee) {
    const r = await frappe.call({
      method: "milestoneksa.api.salary_ui.get_structure_snapshot",
      args: { employee: employee },
    });
    return r.message || {};
  },

  async fetchStructureComponents(employee) {
    const r = await frappe.call({
      method: "milestoneksa.api.salary_ui.get_structure_components",
      args: { employee: employee },
    });
    return r.message || {};
  },

  // ---------------- UI helpers ----------------
  makeTable(title, rows, currency) {
    function tr(label, amount) {
      return (
        "<tr>" +
          "<td>" + frappe.utils.escape_html(label) + "</td>" +
          '<td class="text-right">' + format_currency(amount || 0, currency) + "</td>" +
        "</tr>"
      );
    }

    const body = (rows && rows.length)
      ? rows.map(x => tr(x.salary_component, x.amount)).join("")
      : '<tr><td colspan="2" class="text-muted">' + __("No items") + "</td></tr>";

    return (
      '<div class="frappe-card">' +
        '<div class="frappe-card-head">' + frappe.utils.escape_html(title) + "</div>" +
        '<div class="frappe-card-body" style="padding:0">' +
          '<table class="table table-sm" style="margin:0">' +
            "<thead>" +
              "<tr>" +
                '<th style="width:70%">' + __("Component") + "</th>" +
                '<th class="text-right" style="width:30%">' + __("Amount") + "</th>" +
              "</tr>" +
            "</thead>" +
            "<tbody>" + body + "</tbody>" +
          "</table>" +
        "</div>" +
      "</div>"
    );
  },

  renderStructureHTML(frm, snap) {
    const wrap = frm.get_field("mksa_salary_html").$wrapper;

    if (!snap || !snap.structure_name) {
      wrap.html('<div class="text-muted">' + __("No Salary Structure found for this employee.") + "</div>");
      return;
    }

    const net = (snap.total_earnings || 0) - (snap.total_deductions || 0);

    // Router-safe link for the Salary Structure (no #Form)
    const link_html =
      '<a href="#" class="mksa-open-structure" ' +
      'data-dt="Salary Structure" ' +
      'data-dn="' + encodeURIComponent(snap.structure_name) + '">' +
      frappe.utils.escape_html(snap.structure_name) +
      "</a>";

    const html =
      '<div class="text-muted mb-2">' +
        __("Structure") + ": " + link_html +
        ' &nbsp;•&nbsp; ' + __("Status") + ": " + (snap.docstatus === 1 ? __("Submitted") : __("Draft")) +
      "</div>" +

      '<div class="grid" style="grid-template-columns: 1fr 1fr; gap: 16px;">' +
        MKSA.makeTable(__("Earnings"), snap.earnings || [], snap.currency) +
        MKSA.makeTable(__("Deductions"), snap.deductions || [], snap.currency) +
      "</div>" +

      '<div class="mt-2">' +
        "<b>" + __("Total Earnings") + ":</b> " + format_currency(snap.total_earnings || 0, snap.currency) +
        " &nbsp;&nbsp; | &nbsp;&nbsp; " +
        "<b>" + __("Total Deductions") + ":</b> " + format_currency(snap.total_deductions || 0, snap.currency) +
        " &nbsp;&nbsp; | &nbsp;&nbsp; " +
        "<b>" + __("Net") + ":</b> " + format_currency(net, snap.currency) +
      "</div>";

    wrap.html(html);

    // Bind Desk router; fallback to /app/... if not in Desk
    wrap.off("click", ".mksa-open-structure").on("click", ".mksa-open-structure", function (e) {
      e.preventDefault();
      const dt = this.dataset.dt;                       // "Salary Structure"
      const dn = decodeURIComponent(this.dataset.dn);   // docname with spaces/Arabic
      if (typeof frappe.set_route === "function") {
        frappe.set_route("Form", dt, dn);
      } else {
        const doctypeSlug = dt.replace(/\s+/g, "-").toLowerCase();
        window.location.href = "/app/" + doctypeSlug + "/" + encodeURIComponent(dn);
      }
    });
  },

  async openAlterDialog(frm) {
    const employee = frm.doc.name;
    const data = await MKSA.fetchStructureComponents(employee);
    if (!data || !data.structure) {
      frappe.msgprint(__("No Salary Structure found for this employee."));
      return;
    }
    const compList = data.components || [];
    if (!compList.length) {
      frappe.msgprint(__("No components defined on the Salary Structure."));
      return;
    }

    const opts = compList.map(it => it.salary_component);
    let chosen = opts[0];

    function findComp(name) {
      for (let i = 0; i < compList.length; i++) {
        if (compList[i].salary_component === name) return compList[i];
      }
      return null;
    }
    function getCurrent(name) {
      const it = findComp(name);
      return it ? it.current_amount : 0;
    }

    const d = new frappe.ui.Dialog({
      title: __("Alter Salary Component (Structure)"),
      size: "small",
      fields: [
        {
          fieldtype: "HTML",
          options:
            '<div class="' + (data.docstatus === 1 ? "text-warning" : "text-muted") + ' mb-2">' +
            (data.docstatus === 1
              ? __("The Salary Structure is Submitted. I will create an amended draft and update it.")
              : __("This will update the draft Salary Structure directly.")) +
            "</div>"
        },
        {
          fieldtype: "Select",
          label: __("Component"),
          fieldname: "component",
          options: opts,
          default: chosen,
          reqd: 1
        },
        {
          fieldtype: "Currency",
          label: __("Current Value"),
          fieldname: "current_value",
          options: data.currency,
          read_only: 1,
          default: getCurrent(chosen)
        },
        {
          fieldtype: "Currency",
          label: __("New Value"),
          fieldname: "new_value",
          options: data.currency,
          reqd: 1
        }
      ],
      primary_action_label: __("Change"),
      primary_action: async function (values) {
        if (!values.component) return;
        if (values.new_value === null || values.new_value === "" || typeof values.new_value === "undefined") {
          frappe.msgprint(__("Please enter a new value."));
          return;
        }

        const res = await frappe.call({
          method: "milestoneksa.api.salary_ui.alter_structure_component",
          args: {
            employee: employee,
            component: values.component,
            new_amount: values.new_value,
            submit_after:  0
          },
          freeze: true,
          freeze_message: __("Updating…")
        });

        const info = res.message || {};
        if (info.amended && !info.submitted) {
          frappe.show_alert({ message: __("Amended draft created: {0}. Please review and Submit.", [info.structure_name]), indicator: "orange" });
        } else if (info.submitted) {
          frappe.show_alert({ message: __("Salary Structure submitted: {0}", [info.structure_name]), indicator: "green" });
        } else {
          frappe.show_alert({ message: __("Salary Structure updated: {0}", [info.structure_name]), indicator: "green" });
        }

        d.hide();
        // Refresh the HTML after change
        const snap = await MKSA.fetchStructureSnapshot(employee);
        MKSA.renderStructureHTML(frm, snap);
      },
      secondary_action_label: __("Cancel"),
      secondary_action: function () { d.hide(); }
    });

    // Keep "Current Value" in sync with the selected component
    d.fields_dict.component.df.onchange = function () {
      const c = d.get_value("component");
      d.set_value("current_value", getCurrent(c));
      d.set_value("new_value", "");
    };

    d.show();
  },

  // ---------------- Additional Salary quick-create ----------------
  routeToAdditionalSalary(frm) {
  if (!frm.doc || !frm.doc.name) {
    frappe.msgprint(__("Please save/select an Employee first."));
    return;
  }

  // payroll_date = first day of current month
  const today = frappe.datetime.now_date();
  const payroll_date = (frappe.datetime.month_start && frappe.datetime.month_start(today))
    || (today.slice(0, 7) + "-01");

  frappe.model.with_doctype("Additional Salary", () => {
    const doc = frappe.model.get_new_doc("Additional Salary");

    // Prefill from Employee
    doc.employee = frm.doc.name;
    doc.employee_name = frm.doc.employee_name || frm.doc.employee_name_en || frm.doc.employee_name_ar;
    doc.department = frm.doc.department || null;
    doc.company = frm.doc.company || null;

    // Defaults
    doc.payroll_date = payroll_date;          // e.g., 2025-08-01
    doc.type = "Deduction";                   // or "Earning"
    doc.overwrite_salary_structure_amount = 1;

    // Currency: use system default (avoids async + .finally issues)
    const sysCurrency =
      (frappe.defaults && frappe.defaults.get_default && frappe.defaults.get_default("currency")) ||
      (frappe.boot && frappe.boot.sysdefaults && frappe.boot.sysdefaults.currency);
    if (sysCurrency) doc.currency = sysCurrency;

    // Route now (no .finally)
    frappe.set_route("Form", "Additional Salary", doc.name);
  });
},



};
// ---------------- Form bindings ----------------
frappe.ui.form.on("Employee", {
  // Fetch button click (HR Manager/User only)
  async mksa_fetch_salary(frm) {
    const canHR = frappe.user.has_role("HR Manager") || frappe.user.has_role("HR User");
    if (!canHR) {
      frappe.msgprint(__("Not permitted"));
      return;
    }
    if (!frm.doc.name) return;

    try {
      const r = await frappe.call({
        method: "milestoneksa.api.salary_ui.get_structure_snapshot",
        args: { employee: frm.doc.name },
        freeze: true,
        freeze_message: __("Loading…"),
      });
      MKSA.renderStructureHTML(frm, r.message || {});
    } catch (e) {
      frm.get_field("mksa_salary_html").$wrapper.html(
        '<div class="text-danger">' + __("Failed to load salary snapshot.") + "</div>"
      );
    }
  },

  // 🔧 Alter Salary (HR Manager/User only)
  mksa_alter_salary(frm) {
    const canHR = frappe.user.has_role("HR Manager") || frappe.user.has_role("HR User");
    if (!canHR) {
      frappe.msgprint(__("Not permitted"));
      return;
    }
    if (!frm.doc.name) return;
    MKSA.openAlterDialog(frm);
  },

  // ➕ New Additional Salary (HR Manager/User only)
  mksa_new_additional_salary(frm) {
    const canHR = frappe.user.has_role("HR Manager") || frappe.user.has_role("HR User");
    if (!canHR) {
      frappe.msgprint(__("Not permitted"));
      return;
    }
    if (!frm.doc.name) return;
    MKSA.routeToAdditionalSalary(frm);
  },

  // Do NOT auto-fetch; just manage visibility + placeholder
  refresh(frm) {
    const canHR = frappe.user.has_role("HR Manager") || frappe.user.has_role("HR User");

    // Show/hide your custom Button fields by role
    if (frm.fields_dict.mksa_fetch_salary) {
      frm.toggle_display("mksa_fetch_salary", canHR);
    }
    if (frm.fields_dict.mksa_alter_salary) {
      frm.toggle_display("mksa_alter_salary", canHR);
    }
    if (frm.fields_dict.mksa_new_additional_salary) {
      frm.toggle_display("mksa_new_additional_salary", canHR);
    }

    // Optional: placeholder until user clicks Fetch
    if (frm.fields_dict.mksa_salary_html) {
      frm.get_field("mksa_salary_html").$wrapper.html(
        '<div class="text-muted">' + __("Click “Fetch Salary” to load the current structure.") + "</div>"
      );
    }
  },
});
