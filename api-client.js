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
    // PELD can legitimately be 0 or negative, so a truthiness test drops
    // real scores. components/patient-form.js already collects 0 correctly;
    // this threw it away one layer down, so a typed 0 never reached the API.
    if (formData.organ === 'liver' && formData.peld !== undefined &&
        formData.peld !== null && formData.peld !== '' &&
        !isNaN(parseFloat(formData.peld))) {
      profile.peld = parseFloat(formData.peld);
    }
    if (formData.organ === 'lung' && formData.cas) {
      profile.cas = parseFloat(formData.cas);
    }
    // #329: accrued waiting time (kidney: since dialysis start; travels)
    if (formData.monthsWaiting) {
      profile.months_waiting = parseFloat(formData.monthsWaiting);
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

    // L-067 (#304): user-defined center shortlist
    if (Array.isArray(formData.centerCodes) && formData.centerCodes.length) {
      profile.center_codes = formData.centerCodes;
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
        if (advancedParams.model_acceptance) {
          qp.push('model_acceptance=true');
        }
        if (advancedParams.model_score_drift) {
          qp.push('model_score_drift=true');
        }
        if (advancedParams.trend_years !== undefined && advancedParams.trend_years > 0) {
          qp.push('trend_years=' + advancedParams.trend_years);
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
        iterations: iterations || 300
      };
      // Callers pass an SRTR center code; the backend prefers center_code and
      // keeps city only as a display fallback. No hardcoded city default (#285).
      if (city) {
        body.city = city;
        body.center_code = city;
      }
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
  /**
   * POST /bias-audit — publication-grade disparity metrics (disparity ratios,
   * absolute gaps, Cohen's d) per center and dimension.
   *
   * The endpoint has existed since #254 with NO frontend caller, so its
   * output was unreachable from the app.
   */
  /**
   * POST /weight-range — how much each center's rank moves across the app's
   * own scoring-weight presets (#386 / L-082).
   *
   * Separate from rankStability on purpose: that one bootstraps the DATA and
   * ranks by p24, holding the weights fixed. This one varies the weights,
   * which L-082 measured to be the larger source of movement in the score
   * ranking the table actually sorts by.
   */
  async function weightRange(formData) {
    var base = getBaseUrl();
    var controller = new AbortController();
    // Four scoring passes; the first is slow because the spatial surfaces
    // build lazily, so this gets a generous timeout.
    var timeoutId = setTimeout(function () { controller.abort(); }, API_TIMEOUT_MS * 3);
    try {
      var response = await fetch(base + '/weight-range', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ patient: normalizeFormData(formData) }),
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      if (!response.ok) {
        console.warn('TransPlan weight-range error:', response.status);
        return null;
      }
      return await response.json();
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError') console.warn('TransPlan weight-range timeout');
      return null;
    }
  }

  async function biasAudit(formData, maxCenters, seed) {
    var base = getBaseUrl();
    var controller = new AbortController();
    var timeoutId = setTimeout(function () { controller.abort(); }, 30000);

    try {
      var body = { patient: normalizeFormData(formData) };
      if (maxCenters !== undefined && maxCenters !== null && maxCenters !== '') {
        body.max_centers = maxCenters;
      }
      if (seed !== undefined && seed !== null) body.seed = seed;

      var response = await fetch(base + '/bias-audit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      if (!response.ok) {
        console.warn('TransPlan bias-audit error:', response.status, response.statusText);
        return null;
      }
      return await response.json();
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError') console.warn('TransPlan bias-audit timeout');
      return null;
    }
  }

  async function equityAnalysis(formData, iterationsPerProfile, maxCenters, seed) {
    var base = getBaseUrl();
    var controller = new AbortController();
    // Equity analysis sweeps 48 demographic profiles across every center the
    // tier allows — 30s timeout.
    var timeoutId = setTimeout(function () { controller.abort(); }, 30000);

    try {
      var body = {
        patient: normalizeFormData(formData),
        iterations_per_profile: iterationsPerProfile || 300
      };
      // #350: this defaulted max_centers to 30 while the web tier's cap is
      // 248, so any caller that omitted it silently analyzed an eighth of
      // the centers. Omitting the field lets the server apply the tier cap,
      // which is the single source of truth.
      if (maxCenters !== undefined && maxCenters !== null && maxCenters !== '') {
        body.max_centers = maxCenters;
      }
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
  async function whatIf(formData, center, donorRateMultiplier, waitTimeMultiplier, iterations, seed) {
    var base = getBaseUrl();
    var controller = new AbortController();
    var timeoutId = setTimeout(function () { controller.abort(); }, API_TIMEOUT_MS);

    try {
      var body = {
        patient: normalizeFormData(formData),
        donor_rate_multiplier: donorRateMultiplier ?? 1.0,
        wait_time_multiplier: waitTimeMultiplier ?? 1.0,
        iterations: iterations ?? 500
      };
      // center: {code, label} (preferred, any of the 248 centers) or a bare
      // SRTR center-code string. The legacy city-name mode was retired
      // (#285/#286): the backend rejects requests without center_code.
      if (center && typeof center === 'object') {
        body.center_code = center.code || '';
        body.city = center.label || center.code || '';
      } else if (center) {
        body.center_code = center;
        body.city = center;
      }
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
  async function policyScenario(formData, scenarioId, center, iterations, seed) {
    var base = getBaseUrl();
    var controller = new AbortController();
    var timeoutId = setTimeout(function () { controller.abort(); }, API_TIMEOUT_MS);

    try {
      var body = {
        patient: normalizeFormData(formData),
        scenario_id: scenarioId,
        iterations: iterations || 500
      };
      // center: {code, label} (preferred) or a bare SRTR center-code string
      // (the legacy city-name mode was retired, #285/#286)
      if (center && typeof center === 'object') {
        body.center_code = center.code || '';
        body.city = center.label || center.code || '';
      } else if (center) {
        body.center_code = center;
        body.city = center;
      }
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
   * @returns {Promise<Object|null>} {centers: [...], total: N} or null
   */
  async function fetchCenters(options) {
    var base = getBaseUrl();
    var params = [];
    if (options && options.organ) params.push('organ=' + encodeURIComponent(options.organ));
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
   * Call POST /score/explain — same as scoreAll but with full calculation provenance.
   * Returns centers, provenance trails (top-N), or null on failure.
   * @param {Object} formData - Raw form data from the frontend
   * @param {number} [limit=20] - Limit provenance to top N centers (1-248)
   */
  async function scoreExplain(formData, limit) {
    var base = getBaseUrl();
    var controller = new AbortController();
    var timeoutId = setTimeout(function () { controller.abort(); }, API_TIMEOUT_MS * 2);

    try {
      var body = normalizeFormData(formData);
      var lim = (typeof limit === 'number' && limit > 0) ? Math.min(248, limit) : 20;
      var response = await fetch(base + '/score/explain?limit=' + lim, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      if (!response.ok) {
        console.warn('TransPlan score/explain API error:', response.status);
        return null;
      }
      return await response.json();
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError') {
        console.warn('TransPlan score/explain API timeout');
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
  /**
   * POST /rank-stability — bootstrap rank intervals (#313/#322).
   */
  async function rankStability(formData, nBoot, seed) {
    var base = getBaseUrl();
    var controller = new AbortController();
    var timeoutId = setTimeout(function () { controller.abort(); }, API_TIMEOUT_MS);
    try {
      var body = { patient: normalizeFormData(formData), n_boot: nBoot || 300 };
      if (seed !== undefined && seed !== null) body.seed = seed;
      var response = await fetch(base + '/rank-stability', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
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
   * POST /multi-listing — joint P(transplant) across 2-5 listings (#321).
   */
  async function multiListing(formData, centerCodes, seed) {
    var base = getBaseUrl();
    var controller = new AbortController();
    var timeoutId = setTimeout(function () { controller.abort(); }, API_TIMEOUT_MS);
    try {
      var body = { patient: normalizeFormData(formData), center_codes: centerCodes };
      if (seed !== undefined && seed !== null) body.seed = seed;
      var response = await fetch(base + '/multi-listing', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
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


  window.TransPlanAPI = {
    simulate: simulate,
    scoreAll: scoreAll,
    scoreExplain: scoreExplain,
    sensitivity: sensitivity,
    rankStability: rankStability,
    multiListing: multiListing,
    equityAnalysis: equityAnalysis,
    biasAudit: biasAudit,
    weightRange: weightRange,
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
