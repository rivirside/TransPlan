/**
 * SimTierPanel -- tier configuration and advanced simulation settings.
 *
 * Fetches the active tier (web / local) from GET /tier and applies caps
 * to sliders, dropdowns, and locked controls.  On web tier, locked
 * features are hidden entirely rather than shown disabled.
 *
 * Depends on: TransPlanAPI (api-client.js) for getBaseUrl().
 */
(function () {
  'use strict';

  // ── Default web tier (fallback when API unreachable) ──────────────
  var DEFAULT_WEB_TIER = {
    name: 'web',
    caps: {
      max_iterations: 1000,
      allowed_inference_modes: ['monte_carlo', 'bayesian'],
      allowed_bbn_granularity: ['classic', 'state'],
      copula_theta_locked: true,
      elasticity_locked: true,
      max_equity_centers: 30,
      max_equity_iterations: 200,
      max_sensitivity_iterations: 500,
      max_whatif_iterations: 500,
      max_spatial_resolution: 30
    }
  };

  // ── Internal state ────────────────────────────────────────────────
  var _config = null;

  // ── DOM helpers ───────────────────────────────────────────────────

  /** Cap a range slider's max and clamp its current value. */
  function _capSlider(sliderId, valueId, maxVal) {
    var slider = document.getElementById(sliderId);
    if (!slider) return;
    slider.max = maxVal;
    if (parseInt(slider.value, 10) > maxVal) {
      slider.value = maxVal;
    }
    var display = document.getElementById(valueId);
    if (display) {
      display.textContent = slider.value;
    }
  }

  /**
   * Filter a <select> so only allowed values remain.
   * Disallowed options are REMOVED entirely (Phase 6: hide, don't disable).
   * If the currently selected value is disallowed, switch to the
   * last allowed value.
   */
  function _capSelect(selectId, allowedValues) {
    var sel = document.getElementById(selectId);
    if (!sel) return;
    // Remove disallowed options (iterate backwards for safe removal)
    for (var i = sel.options.length - 1; i >= 0; i--) {
      var opt = sel.options[i];
      if (opt.value && allowedValues.indexOf(opt.value) === -1) {
        sel.removeChild(opt);
      }
    }
    if (allowedValues.indexOf(sel.value) === -1) {
      sel.value = allowedValues[allowedValues.length - 1] || '';
    }
  }

  /**
   * Hide or show a control row.
   * On web tier we HIDE locked controls entirely (display:none)
   * rather than showing them as disabled.  On local tier we
   * ensure they are visible.
   */
  function _hideControl(rowId, locked) {
    var row = document.getElementById(rowId);
    if (!row) return;
    if (locked) {
      row.style.display = 'none';
      row.classList.add('tier-locked');
    } else {
      row.style.display = '';
      row.classList.remove('tier-locked');
    }
  }

  /**
   * Hide MCMC inference option when it is not in the allowed list.
   * Removes the <option> from the DOM on web tier; re-adds it on
   * local tier if it is missing.
   */
  function _filterInferenceOptions(allowedModes) {
    var sel = document.getElementById('inferenceMode');
    if (!sel) return;

    var mcmcAllowed = allowedModes.indexOf('mcmc') !== -1;
    var existing = sel.querySelector('option[value="mcmc"]');

    if (!mcmcAllowed && existing) {
      // Remove MCMC option entirely on web tier
      sel.removeChild(existing);
      // If MCMC was selected, fall back
      if (sel.value === 'mcmc' || !sel.value) {
        sel.value = allowedModes[0] || 'monte_carlo';
      }
    } else if (mcmcAllowed && !existing) {
      // Re-add MCMC option on local tier
      var opt = document.createElement('option');
      opt.value = 'mcmc';
      opt.textContent = 'MCMC Hierarchical (posterior sampling)';
      sel.appendChild(opt);
    }

    // Also apply standard select capping for remaining modes
    _capSelect('inferenceMode', allowedModes);
  }

  /** Update the tier badge element (handles both old and new IDs). */
  function _showBadge(tierName) {
    var label = tierName === 'local' ? 'Local' : 'Web';
    var cls = 'tier-badge tier-' + tierName;
    ['tierBadge', 'sim-tier-badge'].forEach(function (id) {
      var badge = document.getElementById(id);
      if (!badge) return;
      badge.textContent = label;
      badge.className = cls;
    });
  }

  // ── Apply all tier caps to the DOM ────────────────────────────────

  function _applyTierCaps() {
    if (!_config) return;
    var caps = _config.caps;

    _showBadge(_config.name);

    // Main simulator sliders (new sim-* IDs; also try legacy IDs)
    _capSlider('sim-iterations', 'sim-iterations-value', caps.max_iterations);
    _capSlider('iterationsSlider', 'iterationsValue', caps.max_iterations);

    // Inference mode (hide MCMC on web)
    _filterInferenceOptions(caps.allowed_inference_modes);

    // BBN granularity (new and legacy IDs)
    _capSelect('sim-bbn-granularity', caps.allowed_bbn_granularity);
    _capSelect('bbnGranularity', caps.allowed_bbn_granularity);

    // Copula theta -- hide entirely on web (new and legacy IDs)
    _hideControl('sim-copula-theta-row', caps.copula_theta_locked);
    _hideControl('copulaThetaRow', caps.copula_theta_locked);

    // Elasticity -- hide entirely on web (new and legacy IDs)
    _hideControl('sim-elasticity-row', caps.elasticity_locked);
    _hideControl('elasticityRow', caps.elasticity_locked);

    // Equity page sliders
    _capSlider('equityCentersSlider', 'equityCentersValue', caps.max_equity_centers);
    _capSlider('equityIterSlider', 'equityIterValue', caps.max_equity_iterations);
    // Equity standalone page (different IDs)
    _capSlider('equityMaxCenters', 'equityMaxCentersVal', caps.max_equity_centers);
    _capSlider('equityIters', 'equityItersVal', caps.max_equity_iterations);

    // Sensitivity page
    _capSlider('sensitivityIterSlider', 'sensitivityIterVal', caps.max_sensitivity_iterations);

    // Scenarios / what-if page
    _capSlider('whatifIterSlider', 'whatifIterVal', caps.max_whatif_iterations);
    _capSlider('policyIterSlider', 'policyIterVal', caps.max_whatif_iterations);
    _capSlider('subsidyIterSlider', 'subsidyIterVal', caps.max_whatif_iterations);

    // Validation page — cap iteration inputs
    var valIterIds = ['ce-iter', 'ms-iter', 'cs-iter', 'cal-iter', 'tv-iter'];
    var valMaxIter = caps.max_validation_iterations || caps.max_sensitivity_iterations || 500;
    valIterIds.forEach(function (id) {
      var input = document.getElementById(id);
      if (input) {
        input.max = valMaxIter;
        if (parseInt(input.value, 10) > valMaxIter) input.value = valMaxIter;
      }
    });
    // Cap sweep steps
    var msSteps = document.getElementById('ms-steps');
    if (msSteps && caps.max_validation_sweep_steps) {
      msSteps.max = caps.max_validation_sweep_steps;
      if (parseInt(msSteps.value, 10) > caps.max_validation_sweep_steps) {
        msSteps.value = caps.max_validation_sweep_steps;
      }
    }

    // Trend projection slider
    _capSlider('sim-trend-years', 'sim-trend-years-value', caps.max_trend_years);

    // Spatial page
    var resSlider = document.getElementById('resolutionSlider');
    if (resSlider) {
      resSlider.max = caps.max_spatial_resolution;
      if (parseInt(resSlider.value, 10) > caps.max_spatial_resolution) {
        resSlider.value = caps.max_spatial_resolution;
        var resVal = document.getElementById('resolutionValue');
        if (resVal) resVal.textContent = resSlider.value;
      }
    }
  }

  // ── Public API ────────────────────────────────────────────────────

  /**
   * Fetch tier config from the backend and apply caps.
   * Returns a Promise that resolves once caps are applied.
   */
  function init() {
    var apiBase = (window.TransPlanAPI && window.TransPlanAPI.getBaseUrl)
      ? window.TransPlanAPI.getBaseUrl()
      : '';

    return fetch(apiBase + '/tier')
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        _config = data || _cloneDefault();
      })
      .catch(function () {
        _config = _cloneDefault();
      })
      .then(function () {
        window._tierConfig = _config;
        _applyTierCaps();
      });
  }

  /** Return a fresh copy of the default web tier. */
  function _cloneDefault() {
    return JSON.parse(JSON.stringify(DEFAULT_WEB_TIER));
  }

  /** Return the current tier config object. */
  function getConfig() {
    return _config;
  }

  /**
   * Check whether a parameter is locked on the current tier.
   * Supports: 'copula_theta', 'elasticity', and inference mode names.
   */
  function isLocked(paramName) {
    if (!_config) return true;
    var caps = _config.caps;

    if (paramName === 'copula_theta') return !!caps.copula_theta_locked;
    if (paramName === 'elasticity') return !!caps.elasticity_locked;
    if (paramName === 'mcmc') {
      return caps.allowed_inference_modes.indexOf('mcmc') === -1;
    }
    return false;
  }

  /**
   * Return the maximum allowed value for a numeric parameter.
   * Returns Infinity if the parameter has no cap defined.
   */
  function getMax(paramName) {
    if (!_config) return 0;
    var caps = _config.caps;
    var key = 'max_' + paramName;
    if (key in caps) return caps[key];

    // Direct cap field lookup (e.g. 'iterations' -> max_iterations)
    if (paramName in caps) return caps[paramName];

    return Infinity;
  }

  // ── Export ────────────────────────────────────────────────────────

  window.SimTierPanel = {
    init: init,
    getConfig: getConfig,
    isLocked: isLocked,
    getMax: getMax
  };
})();
