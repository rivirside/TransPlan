/**
 * shared/continue-buttons.js — Inter-tool linking buttons.
 * Renders "Continue to..." buttons after results, carrying patient profile via URL params.
 */
(function () {
  'use strict';

  var TOOL_MAP = {
    simulator:   { label: 'Simulator',        href: 'simulator.html' },
    scenarios:   { label: 'Scenario Lab',      href: 'scenarios.html' },
    equity:      { label: 'Equity Audit',      href: 'equity.html' },
    sensitivity: { label: 'Sensitivity',       href: 'sensitivity.html' },
    validation:  { label: 'Model Validation',  href: 'validation.html' },
    compare:     { label: 'Compare Centers',   href: 'compare.html' }
  };

  var LINKS_FROM = {
    simulator:   ['scenarios', 'equity', 'sensitivity', 'validation'],
    scenarios:   ['simulator', 'sensitivity'],
    equity:      ['simulator', 'compare'],
    sensitivity: ['simulator', 'scenarios'],
    validation:  ['simulator']
  };

  /**
   * Encode patient form data as URL search params.
   * @param {Object} formData - Raw form data (camelCase keys)
   * @returns {string} Query string (without leading ?)
   */
  function encodePatientParams(formData) {
    var params = [];
    if (formData.organ)     params.push('organ=' + encodeURIComponent(formData.organ));
    if (formData.bloodType) params.push('bt=' + encodeURIComponent(formData.bloodType));
    if (formData.age)       params.push('age=' + formData.age);
    if (formData.sex)       params.push('sex=' + encodeURIComponent(formData.sex));
    if (formData.urgency)   params.push('urg=' + formData.urgency);
    if (formData.cpra !== undefined && formData.cpra !== '') params.push('cpra=' + formData.cpra);
    if (formData.meld)      params.push('meld=' + formData.meld);
    if (formData.las)       params.push('las=' + formData.las);
    if (formData.insurance) params.push('ins=' + encodeURIComponent(formData.insurance));
    if (formData.useCopula) params.push('cop=1');
    if (formData.adjustForCauseOfDeath) params.push('cod=1');
    return params.join('&');
  }

  /**
   * Render "Continue to..." buttons into a container using safe DOM methods.
   * @param {HTMLElement} container - Where to render buttons
   * @param {string} currentTool - Current tool name (e.g., 'simulator')
   * @param {Object} formData - Current form data to carry forward
   */
  function renderContinueButtons(container, currentTool, formData) {
    var links = LINKS_FROM[currentTool];
    if (!links || !links.length) return;

    var qs = encodePatientParams(formData);

    // Clear container safely
    while (container.firstChild) container.removeChild(container.firstChild);

    var wrapper = document.createElement('div');
    wrapper.className = 'continue-buttons';

    var label = document.createElement('span');
    label.className = 'continue-label';
    label.textContent = 'Continue analysis:';
    wrapper.appendChild(label);

    for (var i = 0; i < links.length; i++) {
      var tool = TOOL_MAP[links[i]];
      if (!tool) continue;
      var a = document.createElement('a');
      a.href = tool.href + (qs ? '?' + qs : '');
      a.className = 'continue-btn';
      a.textContent = tool.label;
      wrapper.appendChild(a);
    }

    container.appendChild(wrapper);
  }

  window.TransPlanContinue = {
    renderContinueButtons: renderContinueButtons,
    encodePatientParams: encodePatientParams
  };
})();
