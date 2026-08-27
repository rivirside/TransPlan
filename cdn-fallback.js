/**
 * Records third-party asset load failures without inline onerror attributes (#250).
 *
 * Nine `onerror="window._cdnFailed.X = true"` attributes across simulator.html
 * and explorer.html did this before. Each one forces `script-src
 * 'unsafe-inline'` in any Content-Security-Policy, which removes most of what
 * a CSP is for.
 *
 * They cannot simply move to `addEventListener` in a later script: a resource
 * error fires while the document is parsing, long before the page's own
 * modules run, so the listener would be registered too late to hear it.
 *
 * A capturing listener registered FIRST does hear them. Resource load errors
 * do not bubble, which is why the `true` on the last argument is required
 * rather than stylistic — without it this file is silently inert.
 *
 * Load this before any CDN tag, and keep it same-origin so it needs no
 * integrity hash of its own.
 */
(function () {
  'use strict';

  window._cdnFailed = window._cdnFailed || {};

  // Longest/most specific patterns first: "leaflet.markercluster.js" also
  // contains "leaflet", so a naive scan would mislabel it.
  var PATTERNS = [
    ['leaflet.markercluster.js', 'markerCluster'],
    ['markercluster.default.css', 'markerClusterCss'],
    ['markercluster.css', 'markerClusterCss'],
    ['leaflet-heat.js', 'leafletHeat'],
    ['leaflet.css', 'leafletCss'],
    ['leaflet.js', 'leaflet'],
    ['chart.umd.min.js', 'chartjs'],
    ['chart.js', 'chartjs']
  ];

  function flagFor(url) {
    var u = String(url || '').toLowerCase();
    for (var i = 0; i < PATTERNS.length; i++) {
      if (u.indexOf(PATTERNS[i][0]) !== -1) return PATTERNS[i][1];
    }
    return null;
  }

  window.addEventListener('error', function (event) {
    var el = event.target;
    // Script errors have window as the target; only element load failures
    // carry a src/href worth recording.
    if (!el || el === window || !el.tagName) return;
    var url = el.src || el.href;
    if (!url) return;

    var flag = flagFor(url);
    if (flag) {
      window._cdnFailed[flag] = true;
    } else {
      // An unrecognised third-party asset still failed; record it under its
      // filename rather than dropping it, so a new CDN tag added without
      // updating PATTERNS is visible instead of silently unmonitored.
      var name = String(url).split('/').pop().split('?')[0];
      if (name) window._cdnFailed[name] = true;
    }
  }, true);   // capture — resource errors do not bubble

  // Exposed for tests; not part of the page's own API.
  window._cdnFallbackFlagFor = flagFor;
})();
