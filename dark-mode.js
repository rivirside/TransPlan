/**
 * TransPlan — Dark Mode Toggle
 *
 * Detects prefers-color-scheme, persists to localStorage, adds toggle to nav.
 * Apply before paint to avoid flash of wrong theme.
 */
(function () {
  'use strict';

  var STORAGE_KEY = 'transplan-dark';
  var ATTR = 'data-dark';

  // --- Determine initial state (before DOM ready) ---
  var stored = localStorage.getItem(STORAGE_KEY); // 'true', 'false', or null
  var prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  var isDark = stored !== null ? stored === 'true' : prefersDark;

  // Apply immediately to prevent flash
  if (isDark) {
    document.documentElement.setAttribute(ATTR, 'true');
  }

  // --- Listen for OS preference changes (only if user hasn't overridden) ---
  if (window.matchMedia) {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function (e) {
      // Only auto-switch if user hasn't manually set a preference
      if (localStorage.getItem(STORAGE_KEY) === null) {
        setDark(e.matches);
      }
    });
  }

  function setDark(value) {
    isDark = value;
    if (isDark) {
      document.documentElement.setAttribute(ATTR, 'true');
    } else {
      document.documentElement.removeAttribute(ATTR);
    }
    localStorage.setItem(STORAGE_KEY, String(isDark));

    // Notify Chart.js instances to update colors if available
    if (window.TransPlanCharts && window.TransPlanCharts.onDarkModeChange) {
      window.TransPlanCharts.onDarkModeChange(isDark);
    }
    if (window.TransPlanProbCharts && window.TransPlanProbCharts.onDarkModeChange) {
      window.TransPlanProbCharts.onDarkModeChange(isDark);
    }
    if (window.TransPlanEquityCharts && window.TransPlanEquityCharts.onDarkModeChange) {
      window.TransPlanEquityCharts.onDarkModeChange(isDark);
    }
  }

  function toggle() {
    setDark(!isDark);
  }

  function createSvgElement(tag, attrs) {
    var el = document.createElementNS('http://www.w3.org/2000/svg', tag);
    Object.keys(attrs).forEach(function (key) {
      el.setAttribute(key, attrs[key]);
    });
    return el;
  }

  function buildSunIcon() {
    var svg = createSvgElement('svg', {
      'class': 'icon-sun',
      viewBox: '0 0 24 24',
      fill: 'none',
      stroke: 'currentColor',
      'stroke-width': '2',
      'stroke-linecap': 'round',
      'stroke-linejoin': 'round'
    });
    svg.appendChild(createSvgElement('circle', { cx: '12', cy: '12', r: '5' }));
    var lines = [
      [12,1,12,3], [12,21,12,23], [4.22,4.22,5.64,5.64],
      [18.36,18.36,19.78,19.78], [1,12,3,12], [21,12,23,12],
      [4.22,19.78,5.64,18.36], [18.36,5.64,19.78,4.22]
    ];
    lines.forEach(function (l) {
      svg.appendChild(createSvgElement('line', { x1: l[0], y1: l[1], x2: l[2], y2: l[3] }));
    });
    return svg;
  }

  function buildMoonIcon() {
    var svg = createSvgElement('svg', {
      'class': 'icon-moon',
      viewBox: '0 0 24 24',
      fill: 'none',
      stroke: 'currentColor',
      'stroke-width': '2',
      'stroke-linecap': 'round',
      'stroke-linejoin': 'round'
    });
    svg.appendChild(createSvgElement('path', { d: 'M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z' }));
    return svg;
  }

  function buildToggle() {
    var navLinks = document.querySelector('.nav-links');
    if (!navLinks) return;

    var btn = document.createElement('button');
    btn.className = 'dark-toggle';
    btn.setAttribute('aria-label', 'Toggle dark mode');
    btn.setAttribute('title', 'Toggle dark mode');
    btn.appendChild(buildSunIcon());
    btn.appendChild(buildMoonIcon());
    btn.addEventListener('click', toggle);
    navLinks.appendChild(btn);
  }

  // Expose for external use
  window.TransPlanDarkMode = {
    toggle: toggle,
    isDark: function () { return isDark; },
    set: setDark
  };

  // Build toggle on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', buildToggle);
  } else {
    buildToggle();
  }
})();
