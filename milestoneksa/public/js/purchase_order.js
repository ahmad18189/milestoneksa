// milestoneksa/milestoneksa/public/js/purchase_order.js

frappe.ui.form.on('Purchase Order', {
  setup: function(frm) {
    // Set up query filter for Purchase Taxes and Charges Template
    // This filters by company and excludes disabled templates
    frm.set_query("taxes_and_charges", function() {
      let filters = {
        disabled: 0
      };
      if (frm.doc.company) {
        filters.company = frm.doc.company;
      }
      return {
        filters: filters
      };
    });
  },

  company: function(frm) {
    // Update taxes_and_charges filter when company changes
    frm.set_query("taxes_and_charges", function() {
      let filters = {
        disabled: 0
      };
      if (frm.doc.company) {
        filters.company = frm.doc.company;
      }
      return {
        filters: filters
      };
    });
    // Clear taxes_and_charges if it doesn't match the new company
    if (frm.doc.company && frm.doc.taxes_and_charges) {
      frappe.db.get_value("Purchase Taxes and Charges Template", frm.doc.taxes_and_charges, ["company", "disabled"], (r) => {
        if (r && r.message) {
          if (r.message.company !== frm.doc.company || r.message.disabled === 1) {
            frm.set_value("taxes_and_charges", "");
            if (r.message.disabled === 1) {
              frappe.msgprint(__("The selected tax template is disabled and has been cleared."));
            } else if (r.message.company !== frm.doc.company) {
              frappe.msgprint(__("The selected tax template belongs to a different company and has been cleared."));
            }
          }
        }
      });
    }
  },

  supplier: function(frm) {
    // Validate taxes_and_charges after supplier is set (get_party_details may set it automatically)
    // Wait a bit for get_party_details to complete
    setTimeout(function() {
      if (frm.doc.company && frm.doc.taxes_and_charges) {
        frappe.db.get_value("Purchase Taxes and Charges Template", frm.doc.taxes_and_charges, ["company", "disabled"], (r) => {
          if (r && r.message) {
            if (r.message.company !== frm.doc.company || r.message.disabled === 1) {
              frm.set_value("taxes_and_charges", "");
              if (r.message.disabled === 1) {
                frappe.msgprint(__("The tax template set from supplier is disabled and has been cleared."));
              } else if (r.message.company !== frm.doc.company) {
                frappe.msgprint(__("The tax template set from supplier belongs to a different company and has been cleared."));
              }
            }
          }
        });
      }
    }, 500);
  },

  taxes_and_charges: function(frm) {
    // Validate when taxes_and_charges is manually selected
    if (frm.doc.company && frm.doc.taxes_and_charges) {
      frappe.db.get_value("Purchase Taxes and Charges Template", frm.doc.taxes_and_charges, ["company", "disabled"], (r) => {
        if (r && r.message) {
          if (r.message.disabled === 1) {
            frm.set_value("taxes_and_charges", "");
            frappe.throw(__("Cannot select a disabled tax template."));
          } else if (r.message.company !== frm.doc.company) {
            frm.set_value("taxes_and_charges", "");
            frappe.throw(__("The selected tax template belongs to company '{0}', but this document is for company '{1}'.", [r.message.company, frm.doc.company]));
          }
        }
      });
    }
  },

  refresh: function(frm) {
    // Generate Payment Tasks button
    frm.add_custom_button(__('Generate Payment Tasks'), function() {
      frappe.call({
        method: 'milestoneksa.milestoneksa.purchase_order.generate_payment_tasks',
        args: { name: frm.doc.name },
        callback: function(r) {
          if (!r.exc) {
            frm.reload_doc();
          }
        }
      });
    });

    // Populate Payment Schedule from Items (draft only)
   // if (frm.doc.docstatus === 1) {
      frm.add_custom_button(
        __('Populate From Items'),
        function() {
          if (!frm.doc.items || frm.doc.items.length === 0) {
            frappe.msgprint(__('No items found to generate schedule.'));
            return;
          }
          // Clear existing schedule rows
          frm.clear_table('payment_schedule');

          // Sequential monthly schedule based on posting date
          let current = frm.doc.posting_date || frm.doc.transaction_date;
          frm.doc.items.forEach(item => {
            const row = frm.add_child('payment_schedule');
            // Start date for this task
            row.start_date = current;
            // Calculate due_date one month after start_date
            const nextDue = frappe.datetime.add_months(current, 1);
            row.due_date = nextDue;
            row.payment_amount = flt(item.qty) * flt(item.rate);
            row.description = `${item.item_code} – ${item.description || item.item_name}`;
            // Next task starts when this one ends
            current = nextDue;
          });

          // Refresh table and notify
          frm.refresh_field('payment_schedule');
          frappe.msgprint(__('Payment Schedule populated sequentially from posting date.'));
        }
      );
    //}
  }
});