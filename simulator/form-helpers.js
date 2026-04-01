/**
 * simulator/form-helpers.js — Simulator-specific form helpers.
 * Handles home center dropdown population and age multiplier logic.
 */
(function () {
  'use strict';

  /**
   * Populate the home center dropdown from the /centers API.
   * @param {string} selectId - ID of the select element
   * @param {string} [organ] - Optional organ filter
   */
  async function populateHomeCenterDropdown(selectId, organ) {
    var select = document.getElementById(selectId);
    if (!select) return;

    // Keep existing placeholder option
    var placeholder = select.querySelector('option[value=""]');

    try {
      var opts = {};
      if (organ) opts.organ = organ;
      var result = await window.TransPlanAPI.fetchCenters(opts);

      if (result && result.centers) {
        // Clear existing options except placeholder
        while (select.options.length > 1) {
          select.remove(1);
        }

        // Sort by state then name
        var centers = result.centers.sort(function (a, b) {
          var sa = (a.state_abbr || a.state || '').localeCompare(b.state_abbr || b.state || '');
          if (sa !== 0) return sa;
          return (a.name || '').localeCompare(b.name || '');
        });

        centers.forEach(function (c) {
          var option = document.createElement('option');
          option.value = c.code || c.name;
          option.textContent = (c.name || c.city) + ', ' + (c.state_abbr || c.state);
          select.appendChild(option);
        });
      }
    } catch (e) {
      console.warn('Failed to load centers for dropdown:', e.message);
    }
  }

  /**
   * Get age-based multiplier for scoring adjustment.
   * Younger and older patients face different challenges.
   * @param {number} age
   * @returns {number} multiplier (0.8 to 1.0)
   */
  function getAgeMultiplier(age) {
    if (age < 18) return 0.85;
    if (age > 65) return 0.9;
    if (age > 55) return 0.95;
    return 1.0;
  }

  /**
   * Collect advanced simulation parameters from the form.
   * Reads iteration slider, inference mode, copula theta, elasticity, BBN granularity.
   * @returns {Object} advancedParams for API calls
   */
  function collectAdvancedParams() {
    var params = {};

    var iterSlider = document.getElementById('sim-iterations');
    if (iterSlider) {
      params.iterations = parseInt(iterSlider.value, 10);
    }

    var inferenceSelect = document.getElementById('inferenceMode');
    if (inferenceSelect) {
      params.inference_mode = inferenceSelect.value;
    }

    var thetaSlider = document.getElementById('sim-copula-theta');
    if (thetaSlider && !thetaSlider.closest('[hidden]')) {
      params.copula_theta = parseFloat(thetaSlider.value);
    }

    var elastSlider = document.getElementById('sim-elasticity');
    if (elastSlider && !elastSlider.closest('[hidden]')) {
      params.elasticity = parseFloat(elastSlider.value);
    }

    var bbnSelect = document.getElementById('sim-bbn-granularity');
    if (bbnSelect && !bbnSelect.closest('[hidden]')) {
      params.bbn_granularity = bbnSelect.value;
    }

    var acceptCb = document.getElementById('sim-acceptance');
    if (acceptCb && acceptCb.checked) {
      params.model_acceptance = true;
    }

    var driftCb = document.getElementById('sim-score-drift');
    if (driftCb && driftCb.checked) {
      params.model_score_drift = true;
    }

    var trendSlider = document.getElementById('sim-trend-years');
    if (trendSlider && parseFloat(trendSlider.value) > 0) {
      params.trend_years = parseFloat(trendSlider.value);
    }

    return params;
  }

  /**
   * Update a range slider's display label.
   * @param {string} sliderId - ID of the range input
   * @param {string} labelId - ID of the display label element
   * @param {string} [suffix] - Optional suffix (e.g., '%', 'x')
   */
  function wireSliderLabel(sliderId, labelId, suffix) {
    var slider = document.getElementById(sliderId);
    var label = document.getElementById(labelId);
    if (!slider || !label) return;
    function update() {
      label.textContent = slider.value + (suffix || '');
    }
    slider.addEventListener('input', update);
    update();
  }

  window.SimFormHelpers = {
    populateHomeCenterDropdown: populateHomeCenterDropdown,
    getAgeMultiplier: getAgeMultiplier,
    collectAdvancedParams: collectAdvancedParams,
    wireSliderLabel: wireSliderLabel
  };
})();
