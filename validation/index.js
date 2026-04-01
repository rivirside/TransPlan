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

    // Pre-fill all organ/blood-type/age/sex selects from URL params
    populateFromURL(params);
  }

  /**
   * Pre-fill validation form fields from URL query params.
   * Validation page has multiple independent forms (ce-, ms-, cs-, cal-, tv-, ref-).
   * All share the same canonical param names: organ, bt, age, sex, urg.
   */
  function populateFromURL(params) {
    if (!params.toString()) return;

    var prefixes = ['ce', 'ms', 'cs', 'cal', 'tv', 'cv', 'ref', 'ec'];
    var organ = params.get('organ');
    var bt = params.get('bt');
    var age = params.get('age');
    var sex = params.get('sex');
    var urg = params.get('urg');

    prefixes.forEach(function (pfx) {
      if (organ) setVal(pfx + '-organ', organ);
      if (bt) setVal(pfx + '-bt', bt);
      if (age) setVal(pfx + '-age', age);
      if (sex) setVal(pfx + '-sex', sex);
      if (urg) setVal(pfx + '-urgency', urg);
    });
  }

  function setVal(id, val) {
    var el = document.getElementById(id);
    if (el && val) el.value = val;
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
