// public/js/qc_calendar.js
window.mksa = window.mksa || {};

(function () {
  const { ymd, monthIterator } = mksa.qc_utils;

  function normalizeStatus(s) {
    if (!s) return 'none';
    const v = String(s).toLowerCase().trim();
    if (v.includes('absent')) return 'absent';
    if (v.includes('half')) return 'halfday';
    if (v.includes('work') && v.includes('home')) return 'wfh';
    if (v.includes('wfh')) return 'wfh';
    if (v.includes('leave')) return 'onleave';
    if (v.includes('present')) return 'present';
    return 'none';
  }

  function statusLabel(key) {
    switch (key) {
      case 'present':  return __('Present');
      case 'absent':   return __('Absent');
      case 'onleave':  return __('On Leave');
      case 'halfday':  return __('Half Day');
      case 'wfh':      return __('Work From Home');
      default:         return __('-');
    }
  }

  function renderCalendar($cal, records, from_date, to_date) {
    try {
      $cal.empty();

      // date → { key, late, early, name }
      const map = Object.create(null);
      for (const r of records) {
        const key = normalizeStatus(r.status);
        map[r.attendance_date] = {
          key,
          late: !!r.late_entry,
          early: !!r.early_exit,
          name: r.name || null,
        };
      }

      const start = new Date(from_date);
      const end   = new Date(to_date);
      const monthLabel = (y, m) =>
        new Date(y, m, 1).toLocaleString(undefined, { month: 'long', year: 'numeric' });

      for (const {year, month, start: mStart, end: mEnd} of monthIterator(start, end)) {
        const $month = $(`
          <div class="mksa-cal-month">
            <div class="mksa-cal-header">
              <div class="month-title">${frappe.utils.escape_html(monthLabel(year, month))}</div>
            </div>
            <div class="mksa-cal-grid">
              <div class="mksa-cal-dow">${__('Sun')}</div>
              <div class="mksa-cal-dow">${__('Mon')}</div>
              <div class="mksa-cal-dow">${__('Tue')}</div>
              <div class="mksa-cal-dow">${__('Wed')}</div>
              <div class="mksa-cal-dow">${__('Thu')}</div>
              <div class="mksa-cal-dow">${__('Fri')}</div>
              <div class="mksa-cal-dow">${__('Sat')}</div>
            </div>
          </div>
        `).appendTo($cal);

        const $grid = $month.find('.mksa-cal-grid');

        // full weeks
        const firstDow = mStart.getDay();
        const gridStart = new Date(mStart); gridStart.setDate(mStart.getDate() - firstDow);
        const lastDow = mEnd.getDay();
        const gridEnd = new Date(mEnd); gridEnd.setDate(mEnd.getDate() + (6 - lastDow));

        for (let d = new Date(gridStart); d <= gridEnd; d.setDate(d.getDate()+1)) {
          const inThisMonth = d.getMonth() === month;
          const dateStr = ymd(d);
          const inRange = d >= start && d <= end;
          const rec = inRange ? map[dateStr] : null;
          const key = rec ? rec.key : (inRange ? 'none' : null);

          const $cell = $(`
            <div class="mksa-cal-day ${inThisMonth ? '' : 'out'}">
              <div class="date-num">${d.getDate()}</div>
            </div>
          `).appendTo($grid);

          // dataset for click routing
          $cell.attr('data-date', dateStr);
          if (rec?.name) $cell.attr('data-att', rec.name);
          if (inRange) $cell.addClass('is-clickable');

          if (!inRange) {
            $cell.addClass('out');
          } else if (key) {
            // background tint
            $cell.append(`<div class="mksa-status-fill status-${key}"></div>`);
            // centered status pill
            $cell.append(
              `<div class="mksa-status-center">
                 <span class="mksa-status-pill pill-${key}">
                   ${frappe.utils.escape_html(statusLabel(key))}
                 </span>
               </div>`
            );
          }

          // late / early chips
          if (rec && (rec.late || rec.early)) {
            const $chips = $(`<div class="mksa-chips"></div>`).appendTo($cell);
            if (rec.late)  $chips.append(`<span class="mksa-chip chip-late">${__('Late Entry')}</span>`);
            if (rec.early) $chips.append(`<span class="mksa-chip chip-early">${__('Early Exit')}</span>`);
          }

          // tooltip
          if (key) {
            const tips = [];
            tips.push(statusLabel(key));
            if (rec?.late) tips.push(__('Late Entry'));
            if (rec?.early) tips.push(__('Early Exit'));
            $cell.attr('title', tips.join(' • '));
          }
        }
      }

      if (!$cal.children().length) {
        const d = new Date(from_date);
        renderCalendar(
          $cal,
          [],
          ymd(new Date(d.getFullYear(), d.getMonth(), 1)),
          ymd(new Date(d.getFullYear(), d.getMonth()+1, 0))
        );
      }
    } catch (e) {
      console.warn('Calendar render error:', e);
      $cal.html(`<div class="text-muted">${__('Unable to render calendar')}</div>`);
    }
  }

  mksa.qc_calendar = { render: renderCalendar };
})();
