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

    return profile;
  }

  /**
   * Call POST /simulate on the backend.
   * @param {Object} formData - Raw form data from the frontend
   * @returns {Promise<Object|null>} SimulationResult or null on failure
   */
  async function simulate(formData) {
    var base = getBaseUrl();
    var controller = new AbortController();
    var timeoutId = setTimeout(function () { controller.abort(); }, API_TIMEOUT_MS);

    try {
      var body = normalizeFormData(formData);
      var response = await fetch(base + '/simulate', {
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
   * Check if the backend is reachable (GET /health).
   * @returns {Promise<boolean>}
   */
  async function isBackendAvailable() {
    var base = getBaseUrl();
    try {
      var response = await fetch(base + '/health', {
        method: 'GET',
        signal: AbortSignal.timeout(3000)
      });
      return response.ok;
    } catch (err) {
      return false;
    }
  }

  // Expose globally
  window.TransPlanAPI = {
    simulate: simulate,
    sensitivity: sensitivity,
    isBackendAvailable: isBackendAvailable,
    normalizeFormData: normalizeFormData
  };
})();
