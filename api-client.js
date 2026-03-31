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
   * @param {Object} [advancedParams] - Optional advanced params from tier panel
   * @returns {Promise<Object|null>} SimulationResult or null on failure
   */
  async function simulate(formData, inferenceMode, advancedParams) {
    var base = getBaseUrl();
    var controller = new AbortController();
    var timeoutId = setTimeout(function () { controller.abort(); }, API_TIMEOUT_MS);

    try {
      var body = normalizeFormData(formData);
      var qp = [];
      if (inferenceMode && inferenceMode !== 'monte_carlo') {
        qp.push('inference_mode=' + encodeURIComponent(inferenceMode));
      }
      // Append advanced params as query parameters
      if (advancedParams) {
        if (advancedParams.iterations && advancedParams.iterations !== 1000) {
          qp.push('iterations=' + advancedParams.iterations);
        }
        if (advancedParams.bbn_granularity) {
          qp.push('bbn_granularity=' + encodeURIComponent(advancedParams.bbn_granularity));
        }
        if (advancedParams.copula_theta !== undefined) {
          qp.push('copula_theta=' + advancedParams.copula_theta);
        }
        if (advancedParams.elasticity !== undefined) {
          qp.push('elasticity=' + advancedParams.elasticity);
        }
        if (advancedParams.seed !== undefined && advancedParams.seed !== null) {
          qp.push('seed=' + advancedParams.seed);
        }
      }
      var url = base + '/simulate' + (qp.length ? '?' + qp.join('&') : '');
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
   * @param {string} city - City name or center code to analyze
   * @param {number} [iterations] - Number of Monte Carlo iterations (default 300)
   * @returns {Promise<Object|null>} SensitivityResult or null on failure
   */
  async function sensitivity(formData, city, iterations, seed) {
    var base = getBaseUrl();
    var controller = new AbortController();
    var timeoutId = setTimeout(function () { controller.abort(); }, API_TIMEOUT_MS);

    try {
      var body = {
        patient: normalizeFormData(formData),
        city: city || 'Nashville',
        center_code: city || '',
        iterations: iterations || 300
      };
      if (seed !== undefined && seed !== null) body.seed = seed;
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
   * @param {number} [maxCenters] - Max centers to include (default 30)
   * @returns {Promise<Object|null>} EquityAnalysisResult or null on failure
   */
  async function equityAnalysis(formData, iterationsPerProfile, maxCenters, seed) {
    var base = getBaseUrl();
    var controller = new AbortController();
    // Equity analysis is expensive (48 profiles × 22 cities) — 30s timeout
    var timeoutId = setTimeout(function () { controller.abort(); }, 30000);

    try {
      var body = {
        patient: normalizeFormData(formData),
        iterations_per_profile: iterationsPerProfile || 300,
        max_centers: maxCenters || 30
      };
      if (seed !== undefined && seed !== null) body.seed = seed;
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
  async function whatIf(formData, city, donorRateMultiplier, waitTimeMultiplier, iterations, seed) {
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
      if (seed !== undefined && seed !== null) body.seed = seed;
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
  async function policyScenario(formData, scenarioId, city, iterations, seed) {
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
      if (seed !== undefined && seed !== null) body.seed = seed;
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

  /**
   * Call POST /score on the backend — comprehensive center-level scoring.
   * Returns 248 centers with 8-category breakdown, or null on failure.
   */
  async function scoreAll(formData) {
    var base = getBaseUrl();
    var controller = new AbortController();
    var timeoutId = setTimeout(function () { controller.abort(); }, API_TIMEOUT_MS);

    try {
      var body = normalizeFormData(formData);
      var response = await fetch(base + '/score', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        console.warn('TransPlan scoring API error:', response.status);
        return null;
      }

      return await response.json();
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError') {
        console.warn('TransPlan scoring API timeout after', API_TIMEOUT_MS, 'ms');
      }
      return null;
    }
  }

  /**
   * Run travel subsidy multi-price-point comparison via POST /travel-subsidy-analysis.
   * @param {Object} formData - Raw form data from the frontend
   * @param {Array<string>} [cities] - Optional city list (empty = all 22)
   * @param {number} [iterations] - Monte Carlo iterations per city (default 500)
   * @returns {Promise<Object|null>} TravelSubsidyAnalysisResult or null
   */
  async function travelSubsidyAnalysis(formData, cities, iterations, seed) {
    var base = getBaseUrl();
    var controller = new AbortController();
    // Longer timeout — this runs 4 tiers × N cities
    var timeoutId = setTimeout(function () { controller.abort(); }, API_TIMEOUT_MS * 4);

    try {
      var body = {
        patient: normalizeFormData(formData),
        cities: cities || [],
        iterations: iterations || 500
      };
      if (seed !== undefined && seed !== null) body.seed = seed;
      var response = await fetch(base + '/travel-subsidy-analysis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        console.warn('TransPlan Travel Subsidy API error:', response.status, response.statusText);
        return null;
      }

      return await response.json();
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError') {
        console.warn('TransPlan Travel Subsidy API timeout');
      }
      return null;
    }
  }

  // ---------------------------------------------------------------------------
  // Validation API methods (Phase 4)
  // ---------------------------------------------------------------------------

  function _postJSON(path, payload, timeoutMs) {
    var to = timeoutMs || API_TIMEOUT_MS;
    var ctrl = new AbortController();
    var timer = setTimeout(function () { ctrl.abort(); }, to);
    return fetch(getBaseUrl() + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: ctrl.signal,
    }).then(function (r) {
      clearTimeout(timer);
      return r.ok ? r.json() : r.json().then(function (e) { throw new Error(e.detail || r.status); });
    }).catch(function (err) {
      clearTimeout(timer);
      throw err;
    });
  }

  function _getJSON(path) {
    var ctrl = new AbortController();
    var timer = setTimeout(function () { ctrl.abort(); }, API_TIMEOUT_MS);
    return fetch(getBaseUrl() + path, { signal: ctrl.signal })
      .then(function (r) {
        clearTimeout(timer);
        return r.ok ? r.json() : r.json().then(function (e) { throw new Error(e.detail || r.status); });
      }).catch(function (err) { clearTimeout(timer); throw err; });
  }

  /**
   * Compare MC / BBN / MCMC rankings for a patient profile.
   * @param {Object} patient  PatientProfile dict
   * @param {number} iterations
   * @param {number|null} seed
   */
  function crossEngine(patient, iterations, seed) {
    return _postJSON('/validation/cross-engine', { patient: patient, iterations: iterations || 300, seed: seed || null }, 60000);
  }

  /**
   * Sweep a model parameter and measure ranking stability.
   * @param {Object} patient PatientProfile dict
   * @param {string} param   e.g. 'copula_theta', 'elasticity', 'cpra'
   * @param {number} nSteps
   * @param {number} baseIterations
   * @param {number|null} seed
   */
  function modelSensitivity(patient, param, nSteps, baseIterations, seed) {
    return _postJSON('/validation/model-sensitivity', {
      patient: patient,
      param: param,
      n_steps: nSteps || 6,
      base_iterations: baseIterations || 200,
      seed: seed || null,
    }, 120000);
  }

  /**
   * Brier score calibration check.
   * @param {Object} patient PatientProfile dict
   * @param {number} iterations
   * @param {number|null} seed
   */
  function calibration(patient, iterations, seed) {
    return _postJSON('/validation/calibration', { patient: patient, iterations: iterations || 300, seed: seed || null }, 60000);
  }

  /**
   * Walk-forward temporal validation.
   * @param {Object} patient
   * @param {number} trainStart
   * @param {number} trainEnd
   * @param {number} testEnd
   * @param {number} iterations
   * @param {number|null} seed
   */
  function temporalValidation(patient, trainStart, trainEnd, testEnd, iterations, seed) {
    return _postJSON('/validation/temporal', {
      patient: patient,
      train_start: trainStart || 2019,
      train_end: trainEnd || 2022,
      test_end: testEnd || 2024,
      iterations: iterations || 200,
      seed: seed || null,
    }, 120000);
  }

  /**
   * MCMC convergence diagnostics for an organ.
   * @param {string} organ
   */
  function convergence(organ) {
    return _getJSON('/validation/convergence/' + organ);
  }

  /**
   * Canonical deterministic reference run (seed=12345).
   * @param {string} organ
   */
  function referenceRun(organ) {
    return _getJSON('/validation/reference-run/' + organ);
  }

  // Expose globally
  window.TransPlanAPI = {
    simulate: simulate,
    scoreAll: scoreAll,
    sensitivity: sensitivity,
    equityAnalysis: equityAnalysis,
    whatIf: whatIf,
    policyScenarios: policyScenarios,
    policyScenario: policyScenario,
    travelSubsidyAnalysis: travelSubsidyAnalysis,
    isBackendAvailable: isBackendAvailable,
    normalizeFormData: normalizeFormData,
    fetchCenters: fetchCenters,
    getBaseUrl: getBaseUrl,
    // Phase 4: Validation
    crossEngine: crossEngine,
    modelSensitivity: modelSensitivity,
    calibration: calibration,
    temporalValidation: temporalValidation,
    convergence: convergence,
    referenceRun: referenceRun,
  };
})();
