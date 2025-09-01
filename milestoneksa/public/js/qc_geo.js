// public/js/qc_geo.js
window.mksa = window.mksa || {};

(function () {
  const LAST_LOC_KEY = 'mksa:last_loc';

  function saveLastLoc(lat, lng) {
    try { localStorage.setItem(LAST_LOC_KEY, JSON.stringify({ lat, lng, ts: Date.now() })); } catch {}
  }
  function readLastLoc(maxAgeMs = 24 * 60 * 60 * 1000) {
    try {
      const raw = localStorage.getItem(LAST_LOC_KEY);
      if (!raw) return null;
      const obj = JSON.parse(raw);
      if (typeof obj.ts !== 'number') return null;
      if (Date.now() - obj.ts > maxAgeMs) return null;
      return obj;
    } catch { return null; }
  }

  // robust geolocation chain (handles iOS kCLErrorLocationUnknown better)
  function getPositionRobust() {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error(__('Geolocation API not available in this browser.')));
        return;
      }
      const tries = [
        'watch-hi', 'watch-low',
        { enableHighAccuracy: true,  timeout: 12000, maximumAge: 0 },
        { enableHighAccuracy: false, timeout: 12000, maximumAge: 60000 },
        { enableHighAccuracy: false, timeout: 8000,  maximumAge: 24*60*60*1000 },
      ];

      function next() {
        if (!tries.length) return reject(new Error(__('Location unavailable after multiple attempts.')));
        const mode = tries.shift();

        if (mode === 'watch-hi' || mode === 'watch-low') {
          const opts = { enableHighAccuracy: mode === 'watch-hi', timeout: 10000, maximumAge: 0 };
          const id = navigator.geolocation.watchPosition(
            (p) => { navigator.geolocation.clearWatch(id); resolve({ lat: p.coords.latitude, lng: p.coords.longitude }); },
            (e) => { navigator.geolocation.clearWatch(id); if (e && e.code === 1) reject(e); else next(); },
            opts
          );
          setTimeout(() => navigator.geolocation.clearWatch(id), opts.timeout + 1500);
          return;
        }

        navigator.geolocation.getCurrentPosition(
          (p) => resolve({ lat: p.coords.latitude, lng: p.coords.longitude }),
          (e) => { if (e && e.code === 1) reject(e); else next(); },
          mode
        );
      }
      next();
    });
  }

  mksa.qc_geo = { getPositionRobust, saveLastLoc, readLastLoc };
})();
