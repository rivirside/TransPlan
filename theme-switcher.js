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

  var DEFAULT_THEME = 'xp'; // Windows XP Luna as default

  // Apply saved theme immediately (before paint), fall back to default
  var saved = localStorage.getItem(STORAGE_KEY);
  var activeTheme = saved !== null ? saved : DEFAULT_THEME;
  if (activeTheme) {
    document.documentElement.setAttribute('data-theme', activeTheme);
  }

  function buildSwitcher() {
    if (!SHOW_SWITCHER) return;

    // Mount into footer container if available, else append to body
    var mount = document.getElementById('theme-switcher-mount');

    var bar = document.createElement('div');
    bar.id = 'theme-switcher';
    bar.style.cssText = [
      'display: flex',
      'flex-wrap: wrap',
      'gap: 6px',
      'padding: 10px 0',
      'margin-top: 8px',
      'font-family: Inter, system-ui, sans-serif',
      'font-size: 12px',
      'align-items: center',
      'justify-content: center'
    ].join('; ');

    var label = document.createElement('span');
    label.textContent = 'Theme:';
    label.style.cssText = 'color: #999; font-weight: 600; margin-right: 4px;';
    bar.appendChild(label);

    THEMES.forEach(function (theme) {
      var btn = document.createElement('button');
      btn.textContent = theme.label;
      btn.dataset.themeId = theme.id;
      btn.style.cssText = [
        'padding: 4px 10px',
        'border: 1px solid rgba(255,255,255,0.2)',
        'border-radius: 4px',
        'background: rgba(255,255,255,0.1)',
        'color: #ccc',
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

    if (mount) {
      mount.appendChild(bar);
    } else {
      // Fallback: fixed position if no mount point
      bar.style.position = 'fixed';
      bar.style.bottom = '16px';
      bar.style.right = '16px';
      bar.style.zIndex = '10000';
      bar.style.background = 'rgba(255,255,255,0.95)';
      bar.style.padding = '8px 12px';
      bar.style.borderRadius = '8px';
      bar.style.boxShadow = '0 4px 16px rgba(0,0,0,0.12)';
      document.body.appendChild(bar);
    }
    updateActive(bar, activeTheme);
  }

  function applyTheme(themeId) {
    if (themeId) {
      document.documentElement.setAttribute('data-theme', themeId);
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
    // Always persist so we know user made a choice (even '' = original default)
    localStorage.setItem(STORAGE_KEY, themeId);
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
        btn.style.background = 'rgba(255,255,255,0.1)';
        btn.style.color = '#ccc';
        btn.style.borderColor = 'rgba(255,255,255,0.2)';
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
