/**
 * explorer/index.js — Entry point for the unified Explorer page.
 * Handles tab switching between Data Layers and Spatial Analysis tabs.
 * Lazy-initializes each tab's module on first activation.
 */
(function () {
  'use strict';

  var initialized = { 'data-layers': false, 'spatial': false };
  var currentTab = 'data-layers';

  var tabBtns, tabPanels;

  function switchTab(tabId) {
    currentTab = tabId;

    tabBtns.forEach(function (btn) {
      btn.classList.toggle('active', btn.getAttribute('data-tab') === tabId);
    });

    tabPanels.forEach(function (panel) {
      panel.style.display = panel.id === tabId + '-panel' ? '' : 'none';
    });

    // Lazy-init the module on first activation
    if (!initialized[tabId]) {
      initialized[tabId] = true;
      if (tabId === 'data-layers' && window.TransPlanDataLayers) {
        TransPlanDataLayers.init();
      } else if (tabId === 'spatial' && window.TransPlanSpatial) {
        TransPlanSpatial.init();
      }
    } else {
      // If already initialized, invalidate map size (Leaflet needs this after show/hide)
      if (tabId === 'data-layers' && window.TransPlanDataLayers && TransPlanDataLayers.invalidateMap) {
        TransPlanDataLayers.invalidateMap();
      } else if (tabId === 'spatial' && window.TransPlanSpatial && TransPlanSpatial.invalidateMap) {
        TransPlanSpatial.invalidateMap();
      }
    }

    // Update URL
    var url = new URL(window.location);
    url.searchParams.set('tab', tabId);
    history.replaceState(null, '', url);
  }

  function parseURLTab() {
    var params = new URLSearchParams(window.location.search);
    var tab = params.get('tab');
    if (tab === 'spatial' || tab === 'spatial-analysis') return 'spatial';
    return 'data-layers';
  }

  function init() {
    tabBtns = Array.from(document.querySelectorAll('.explorer-tab'));
    tabPanels = Array.from(document.querySelectorAll('.explorer-panel'));

    tabBtns.forEach(function (btn) {
      btn.addEventListener('click', function () {
        switchTab(btn.getAttribute('data-tab'));
      });
    });

    var startTab = parseURLTab();
    switchTab(startTab);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  window.TransPlanExplorer = { switchTab: switchTab };
})();
