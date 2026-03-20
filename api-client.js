/**
 * TransPlan Phase 2 API Client
 *
 * Calls the backend for Monte Carlo simulation.
 * Works in two modes:
 *   1. Same-origin (single process): API at /simulate (no CORS needed)
 *   2. Cross-origin (separate servers): API at window.TransPlanBackend + /simulate
 * Gracefully returns null if backend is unreachable (GitHub Pages, backend down).
 */
(function () {
  'use strict';

  var API_TIMEOUT_MS = 15000;

  /**
   * Get the base URL for API calls.
   * Returns '' for same-origin (relative URLs) or an explicit backend URL.
   */
  function getBaseUrl() {
    // Explicit backend URL (set by session.js for multi-process mode)
    if (window.TransPlanBackend) return window.TransPlanBackend;
    // Same-origin mode: use relative URLs (works when FastAPI serves static files)
    return '';
  }

  /**
   * Normalize frontend form data to backend PatientProfile schema.
   * Frontend uses camelCase; backend expects snake_case.
   */
  function normalizeFormData(formData) {
    var profile = {
      organ: formData.organ,
      blood_type: formData.bloodType,
      age: parseInt(formData.age, 10),
      sex: formData.sex,
      urgency: parseInt(formData.urgency, 10)
    };

    // Optional fields — only include if provided
    if (formData.insurance) profile.insurance = formData.insurance;
    if (formData.weight) profile.weight_lbs = parseFloat(formData.weight);
    if (formData.height) profile.height_inches = parseFloat(formData.height);

    // Organ-specific clinical scores
    if (formData.organ === 'kidney' && formData.cpra !== undefined && formData.cpra !== '') {
      profile.cpra = parseInt(formData.cpra, 10);
    }
    if (formData.organ === 'liver' && formData.meld) {
      profile.meld = parseInt(formData.meld, 10);
    }
    if (formData.organ === 'lung' && formData.las) {
      profile.las = parseFloat(formData.las);
    }

    // Relocation comparison
    if (formData.homeCenter) profile.home_center = formData.homeCenter;

    // M2: Organ-specific donor availability adjustment
    if (formData.adjustForCauseOfDeath) profile.adjust_for_cause_of_death = true;

    // Phase 5 M2: Correlated competing risks via Clayton copula
    if (formData.useCopula) profile.use_copula = true;

    // Phase 4 M1: Custom scoring weights (pass-through for export fidelity)
    if (formData.weights && typeof formData.weights === 'object') {
      profile.custom_weights = formData.weights;
    }

    return profile;
  }

  /**
   * Call POST /simulate on the backend.
   * @param {Object} formData - Raw form data from the frontend
   * @param {string} [inferenceMode] - 'monte_carlo' (default) or 'bayesian'
   * @returns {Promise<Object|null>} SimulationResult or null on failure
   */
  async function simulate(formData, inferenceMode) {
    var base = getBaseUrl();
    var controller = new AbortController();
    var timeoutId = setTimeout(function () { controller.abort(); }, API_TIMEOUT_MS);

    try {
      var body = normalizeFormData(formData);
      var url = base + '/simulate';
      if (inferenceMode && inferenceMode !== 'monte_carlo') {
        url += '?inference_mode=' + encodeURIComponent(inferenceMode);
      }
      var response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        console.warn('TransPlan API error:', response.status, response.statusText);
        return null;
      }

      return await response.json();
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError') {
        console.warn('TransPlan API timeout after', API_TIMEOUT_MS, 'ms');
      } else {
        // Expected on GitHub Pages or when backend is down
      }
      return null;
    }
  }

  /**
   * Call POST /sensitivity on the backend.
   * @param {Object} formData - Raw form data from the frontend
   * @param {string} city - City to analyze (use top-ranked city from simulate result)
   * @param {number} [iterations] - Number of Monte Carlo iterations (default 300)
   * @returns {Promise<Object|null>} SensitivityResult or null on failure
   */
  async function sensitivity(formData, city, iterations) {
    var base = getBaseUrl();
    var controller = new AbortController();
    var timeoutId = setTimeout(function () { controller.abort(); }, API_TIMEOUT_MS);

    try {
      var body = {
        patient: normalizeFormData(formData),
        city: city || 'Nashville',
        iterations: iterations || 300
      };
      var response = await fetch(base + '/sensitivity', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        console.warn('TransPlan Sensitivity API error:', response.status, response.statusText);
        return null;
      }

      return await response.json();
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError') {
        console.warn('TransPlan Sensitivity API timeout after', API_TIMEOUT_MS, 'ms');
      }
      return null;
    }
  }

  /**
   * Call POST /equity-analysis on the backend.
   * Runs demographic stratification across 48 profiles × 22 cities.
   * @param {Object} formData - Raw form data from the frontend
   * @param {number} [iterationsPerProfile] - Monte Carlo iterations per profile (default 300)
   * @returns {Promise<Object|null>} EquityAnalysisResult or null on failure
   */
  async function equityAnalysis(formData, iterationsPerProfile) {
    var base = getBaseUrl();
    var controller = new AbortController();
    // Equity analysis is expensive (48 profiles × 22 cities) — 30s timeout
    var timeoutId = setTimeout(function () { controller.abort(); }, 30000);

    try {
      var body = {
        patient: normalizeFormData(formData),
        iterations_per_profile: iterationsPerProfile || 300
      };
      var response = await fetch(base + '/equity-analysis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        console.warn('TransPlan Equity API error:', response.status, response.statusText);
        return null;
      }

      return await response.json();
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError') {
        console.warn('TransPlan Equity API timeout after 30000ms');
      }
      return null;
    }
  }

  /**
   * Call POST /what-if on the backend.
   * Runs Monte Carlo with adjusted model assumptions for a single city.
   * @param {Object} formData - Raw form data from the frontend
   * @param {string} city - City to run what-if analysis for
   * @param {number} donorRateMultiplier - Donor availability multiplier (0.5-2.0)
   * @param {number} waitTimeMultiplier - Wait time multiplier (0.5-2.0)
   * @param {number} [iterations] - Monte Carlo iterations (default 500)
   * @returns {Promise<Object|null>} WhatIfResult or null on failure
   */
  async function whatIf(formData, city, donorRateMultiplier, waitTimeMultiplier, iterations) {
    var base = getBaseUrl();
    var controller = new AbortController();
    var timeoutId = setTimeout(function () { controller.abort(); }, API_TIMEOUT_MS);

    try {
      var body = {
        patient: normalizeFormData(formData),
        city: city || 'Nashville',
        donor_rate_multiplier: donorRateMultiplier ?? 1.0,
        wait_time_multiplier: waitTimeMultiplier ?? 1.0,
        iterations: iterations ?? 500
      };
      var response = await fetch(base + '/what-if', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        console.warn('TransPlan What-If API error:', response.status, response.statusText);
        return null;
      }

      return await response.json();
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError') {
        console.warn('TransPlan What-If API timeout after', API_TIMEOUT_MS, 'ms');
      }
      return null;
    }
  }

  /**
   * Fetch available policy scenarios from GET /policy-scenarios.
   * @param {string} [organ] - Optional organ filter
   * @returns {Promise<Array|null>} List of PolicyScenario objects or null
   */
  async function policyScenarios(organ) {
    var base = getBaseUrl();
    var url = base + '/policy-scenarios';
    if (organ) url += '?organ=' + encodeURIComponent(organ);
    var controller = new AbortController();
    var timeoutId = setTimeout(function () { controller.abort(); }, 5000);
    try {
      var response = await fetch(url, {
        method: 'GET',
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      if (!response.ok) return null;
      return await response.json();
    } catch (err) {
      clearTimeout(timeoutId);
      return null;
    }
  }

  /**
   * Run a policy scenario analysis via POST /policy-scenario.
   * @param {Object} formData - Raw form data from the frontend
   * @param {string} scenarioId - ID of the predefined policy scenario
   * @param {string} city - City to analyze
   * @param {number} [iterations] - Monte Carlo iterations (default 500)
   * @returns {Promise<Object|null>} PolicyScenarioResult or null
   */
  async function policyScenario(formData, scenarioId, city, iterations) {
    var base = getBaseUrl();
    var controller = new AbortController();
    var timeoutId = setTimeout(function () { controller.abort(); }, API_TIMEOUT_MS);

    try {
      var body = {
        patient: normalizeFormData(formData),
        scenario_id: scenarioId,
        city: city || 'Nashville',
        iterations: iterations || 500
      };
      var response = await fetch(base + '/policy-scenario', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        console.warn('TransPlan Policy Scenario API error:', response.status, response.statusText);
        return null;
      }

      return await response.json();
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError') {
        console.warn('TransPlan Policy Scenario API timeout after', API_TIMEOUT_MS, 'ms');
      }
      return null;
    }
  }

  /**
   * Check if the backend is reachable (GET /health).
   * @returns {Promise<boolean>}
   */
  async function isBackendAvailable() {
    var base = getBaseUrl();
    var controller = new AbortController();
    var timeoutId = setTimeout(function () { controller.abort(); }, 3000);
    try {
      var response = await fetch(base + '/health', {
        method: 'GET',
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      return response.ok;
    } catch (err) {
      clearTimeout(timeoutId);
      return false;
    }
  }

  /**
   * Fetch the list of transplant centers from GET /centers.
   * @param {Object} [options] - Query options
   * @param {string} [options.organ] - Filter by organ program
   * @param {boolean} [options.focusOnly] - Return only 22 focus cities
   * @returns {Promise<Object|null>} {centers: [...], total: N} or null
   */
  async function fetchCenters(options) {
    var base = getBaseUrl();
    var params = [];
    if (options && options.organ) params.push('organ=' + encodeURIComponent(options.organ));
    if (options && options.focusOnly) params.push('focus_only=true');
    var url = base + '/centers' + (params.length ? '?' + params.join('&') : '');
    var controller = new AbortController();
    var timeoutId = setTimeout(function () { controller.abort(); }, 5000);
    try {
      var response = await fetch(url, { method: 'GET', signal: controller.signal });
      clearTimeout(timeoutId);
      if (!response.ok) return null;
      return await response.json();
    } catch (err) {
      clearTimeout(timeoutId);
      return null;
    }
  }

  // Expose globally
  window.TransPlanAPI = {
    simulate: simulate,
    sensitivity: sensitivity,
    equityAnalysis: equityAnalysis,
    whatIf: whatIf,
    policyScenarios: policyScenarios,
    policyScenario: policyScenario,
    isBackendAvailable: isBackendAvailable,
    normalizeFormData: normalizeFormData,
    fetchCenters: fetchCenters
  };
})();
