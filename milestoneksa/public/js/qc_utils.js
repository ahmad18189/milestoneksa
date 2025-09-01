// public/js/qc_utils.js
window.mksa = window.mksa || {};

(function () {
  const pad = (n) => String(n).padStart(2, '0');
  const ymd = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  const firstOfMonth = (d) => new Date(d.getFullYear(), d.getMonth(), 1);
  const lastOfMonth  = (d) => new Date(d.getFullYear(), d.getMonth() + 1, 0);
  const isFiniteNum = (v) => typeof v === 'number' && isFinite(v);
  const fmtUser = (ts) => (ts ? frappe.datetime.str_to_user(ts) : __('—'));

  // elapsed hh:mm since a datetime string "YYYY-MM-DD HH:mm:ss"
  function hhmm_since(dtStr) {
    if (!dtStr) return '';
    const start = new Date(dtStr.replace(' ', 'T'));
    const now = new Date();
    if (isNaN(start.getTime()) || now <= start) return '';
    let mins = Math.floor((now - start) / 60000);
    const h = Math.floor(mins / 60);
    const m = mins % 60;
    return `${pad(h)}:${pad(m)}`;
  }

  function setPill($el, variant, text) {
    $el
      .removeClass('pill--neutral pill--info pill--success pill--warning pill--danger')
      .addClass(`pill--${variant}`)
      .text(text);
  }

  // iterate months between two dates (inclusive)
  function* monthIterator(startDate, endDate) {
    let y = startDate.getFullYear(), m = startDate.getMonth();
    while (true) {
      const first = new Date(y, m, 1);
      if (first > endDate) break;
      const last  = new Date(y, m + 1, 0);
      yield { year: y, month: m, start: first, end: last };
      m += 1; if (m > 11) { m = 0; y += 1; }
    }
  }

  // simple theme toggle helpers (page-scoped)
  const THEME_KEY = 'mksa:theme_mode';
  function initTheme($container) {
    let mode = localStorage.getItem(THEME_KEY);
    if (mode !== 'dark' && mode !== 'light') mode = 'light';
    $container.attr('data-theme', mode);
    return mode;
  }
  function applyTheme($container, mode) {
    $container.attr('data-theme', mode);
    localStorage.setItem(THEME_KEY, mode);
  }

  // expose
  mksa.qc_utils = {
    pad, ymd, firstOfMonth, lastOfMonth, isFiniteNum, fmtUser, hhmm_since,
    setPill, monthIterator, THEME_KEY, initTheme, applyTheme
  };
})();
