// public/js/qc_api.js
window.mksa = window.mksa || {};

(function () {
  async function getNextAction(filters) {
    const r = await frappe.call('milestoneksa.api.quick_checkin.get_next_action', { filters });
    return r.message || {};
  }

  async function getLastIn(employee_name) {
    const r = await frappe.call({
      method: 'frappe.client.get_list',
      args: {
        doctype: 'Employee Checkin',
        fields: ['name','time','log_type'],
        filters: { employee: employee_name, log_type: 'IN' },
        order_by: 'time desc',
        limit_page_length: 1
      }
    });
    return (r?.message && r.message[0]) || null;
  }

  async function createCheckin(args) {
    return frappe.call({
      method: 'milestoneksa.api.quick_checkin.quick_checkin',
      args,  // {log_type, latitude?, longitude?, geolocation?}
      freeze: true,
      freeze_message: __('Recording…'),
    });
  }

  async function fetchAttendance(employee_name, from_date, to_date) {
    if (!employee_name) return [];
    const r = await frappe.call({
      method: 'frappe.client.get_list',
      args: {
        doctype: 'Attendance',
        fields: ['name','attendance_date','status','late_entry','early_exit'],
        filters: {
          employee: employee_name,
          attendance_date: ['between', [from_date, to_date]]
        },
        order_by: 'attendance_date asc',
        limit_page_length: 500
      }
    });
    return r?.message || [];
  }

  mksa.qc_api = { getNextAction, getLastIn, createCheckin, fetchAttendance };
})();
