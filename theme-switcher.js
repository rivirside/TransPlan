/**
 * TransPlan — Theme Switcher
 *
 * Floating UI for comparing 6 themes (4 professional + 2 retro).
 * Sets data-theme attribute on <html> and persists to localStorage.
 * Toggle SHOW_SWITCHER to show/hide the floating picker.
 */
(function () {
  'use strict';

  var THEMES = [
    { id: '',           label: 'Default',    color: '#5B6FE6' },
    { id: 'clinical',   label: 'Clinical',   color: '#3B6B8A' },
    { id: 'research',   label: 'Research',   color: '#1A6B5A' },
    { id: 'government', label: 'Government', color: '#1A4480' },
    { id: 'xp',         label: 'Windows XP', color: '#0055E5' },
    { id: 'twenty10',   label: '2010s Flat', color: '#2196F3' }
  ];

  var STORAGE_KEY = 'transplan-theme';
  var SHOW_SWITCHER = true; // Theme picker enabled for comparison

  // Apply saved theme immediately (before paint)
  var saved = localStorage.getItem(STORAGE_KEY) || '';
  if (saved) {
    document.documentElement.setAttribute('data-theme', saved);
  }

  function buildSwitcher() {
    if (!SHOW_SWITCHER) return; // Hidden — flip SHOW_SWITCHER to re-enable
    var bar = document.createElement('div');
    bar.id = 'theme-switcher';
    bar.style.cssText = [
      'position: fixed',
      'bottom: 56px',
      'right: 16px',
      'z-index: 10000',
      'display: flex',
      'gap: 6px',
      'padding: 8px 12px',
      'background: rgba(255,255,255,0.95)',
      'backdrop-filter: blur(8px)',
      'border: 1px solid #ddd',
      'border-radius: 8px',
      'box-shadow: 0 4px 16px rgba(0,0,0,0.12)',
      'font-family: Inter, system-ui, sans-serif',
      'font-size: 12px',
      'align-items: center'
    ].join('; ');

    var label = document.createElement('span');
    label.textContent = 'Theme:';
    label.style.cssText = 'color: #666; font-weight: 600; margin-right: 4px;';
    bar.appendChild(label);

    THEMES.forEach(function (theme) {
      var btn = document.createElement('button');
      btn.textContent = theme.label;
      btn.dataset.themeId = theme.id;
      btn.style.cssText = [
        'padding: 4px 10px',
        'border: 1px solid #ccc',
        'border-radius: 4px',
        'background: white',
        'color: #333',
        'cursor: pointer',
        'font-size: 11px',
        'font-weight: 500',
        'font-family: inherit',
        'transition: all 0.15s ease'
      ].join('; ');

      btn.addEventListener('click', function () {
        applyTheme(theme.id);
        updateActive(bar, theme.id);
      });

      bar.appendChild(btn);
    });

    document.body.appendChild(bar);
    updateActive(bar, saved);
  }

  function applyTheme(themeId) {
    if (themeId) {
      document.documentElement.setAttribute('data-theme', themeId);
      localStorage.setItem(STORAGE_KEY, themeId);
    } else {
      document.documentElement.removeAttribute('data-theme');
      localStorage.removeItem(STORAGE_KEY);
    }
  }

  function updateActive(bar, activeId) {
    var buttons = bar.querySelectorAll('button');
    buttons.forEach(function (btn) {
      var isActive = btn.dataset.themeId === activeId;
      var theme = THEMES.find(function (t) { return t.id === btn.dataset.themeId; });
      if (isActive) {
        btn.style.background = theme.color;
        btn.style.color = 'white';
        btn.style.borderColor = theme.color;
      } else {
        btn.style.background = 'white';
        btn.style.color = '#333';
        btn.style.borderColor = '#ccc';
      }
    });
  }

  // Build on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', buildSwitcher);
  } else {
    buildSwitcher();
  }
})();
