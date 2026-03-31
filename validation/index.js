/**
 * validation/index.js — Tab routing for the Model Validation page.
 *
 * Reads the data-tab attribute on .val-tab buttons and shows/hides .val-panel
 * elements with matching id="panel-{tab}". Also parses ?tab= URL param.
 */
(function () {
  'use strict';

  function init() {
    var tabBar = document.getElementById('val-tabbar');
    if (!tabBar) return;

    var tabs = tabBar.querySelectorAll('.val-tab[data-tab]');

    tabs.forEach(function (btn) {
      btn.addEventListener('click', function () {
        switchTab(btn.getAttribute('data-tab'));
      });
    });

    // Parse ?tab= URL param
    var params = new URLSearchParams(window.location.search);
    var tab = params.get('tab');
    if (tab && document.getElementById('panel-' + tab)) {
      switchTab(tab);
    }
  }

  function switchTab(tabId) {
    var tabBar = document.getElementById('val-tabbar');
    if (!tabBar) return;

    // Update tab button states
    var tabs = tabBar.querySelectorAll('.val-tab[data-tab]');
    tabs.forEach(function (btn) {
      btn.classList.toggle('active', btn.getAttribute('data-tab') === tabId);
    });

    // Show/hide panels
    var panels = document.querySelectorAll('.val-panel');
    panels.forEach(function (panel) {
      panel.classList.toggle('active', panel.id === 'panel-' + tabId);
    });

    // Update URL
    var url = new URL(window.location);
    url.searchParams.set('tab', tabId);
    history.replaceState(null, '', url);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
