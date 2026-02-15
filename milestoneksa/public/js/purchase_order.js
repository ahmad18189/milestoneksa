// milestoneksa/milestoneksa/public/js/purchase_order.js

frappe.ui.form.on('Purchase Order', {
  refresh(frm) {
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