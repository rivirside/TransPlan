/**
 * simulator/results.js — Results orchestrator.
 * Calls POST /score and POST /simulate, manages result state,
 * and coordinates rendering between table, map, and charts.
 */
(function () {
  'use strict';

  // Module state
  var _scoreResults = null;    // from POST /score
  var _simResults = null;      // from POST /simulate
  var _formData = null;        // last submitted form data
  var _homeLocation = null;    // geocoded home location

  /**
   * Run scoring for all 248 centers (instant, deterministic).
   * @param {Object} formData - Raw form data from patient-form
   * @returns {Promise<Object|null>} ScoringResult or null
   */
  async function runScoring(formData) {
    _formData = formData;
    if (!window.TransPlanAPI) return null;

    var result = await window.TransPlanAPI.scoreAll(formData);
    if (result && result.centers) {
      _scoreResults = result;
    }
    return result;
  }

  /**
   * Run Monte Carlo / BBN / MCMC simulation.
   * @param {Object} formData - Raw form data
   * @param {string} inferenceMode - 'monte_carlo', 'bayesian', or 'mcmc'
   * @param {Object} advancedParams - iterations, copula_theta, elasticity, seed, bbn_granularity
   * @returns {Promise<Object|null>} SimulationResult or null
   */
  async function runSimulation(formData, inferenceMode, advancedParams) {
    _formData = formData;
    if (!window.TransPlanAPI) return null;

    var result = await window.TransPlanAPI.simulate(formData, inferenceMode, advancedParams);
    if (result && result.cities) {
      _simResults = result;
    }
    return result;
  }

  /**
   * Geocode the home location from form data.
   * @param {string} locationQuery - Address or zip code
   * @returns {Promise<{lat, lon, display}|null>}
   */
  async function geocodeHome(locationQuery) {
    if (!locationQuery || !window.TransPlanGeo) return null;
    _homeLocation = await window.TransPlanGeo.geocodeLocation(locationQuery);
    return _homeLocation;
  }

  /**
   * Merge scoring and simulation results for the table.
   * Returns a unified array with both score and probability data per center.
   * @returns {Array} Merged results sorted by score (or p24 if simulation ran)
   */
  function getMergedResults() {
    if (!_scoreResults && !_simResults) return [];

    // Build lookup of simulation results by center_code
    var simLookup = {};
    if (_simResults && _simResults.cities) {
      _simResults.cities.forEach(function (c) {
        var key = c.center_code || c.city;
        simLookup[key] = c;
      });
    }

    // If we have scoring results, merge sim data onto them
    if (_scoreResults && _scoreResults.centers) {
      return _scoreResults.centers.map(function (sc) {
        var sim = simLookup[sc.code] || simLookup[sc.name] || null;
        return {
          code: sc.code,
          name: sc.name,
          state: sc.state,
          stateAbbr: sc.state_abbr,
          lat: sc.lat,
          lon: sc.lon,
          score: sc.total,
          breakdown: sc.breakdown,
          rank: sc.rank,
          // Simulation data (null if not run yet)
          p24: sim ? sim.p_transplant_24mo : null,
          p6: sim ? sim.p_transplant_6mo : null,
          p12: sim ? sim.p_transplant_12mo : null,
          p36: sim ? sim.p_transplant_36mo : null,
          ci95: sim ? sim.confidence_interval_95 : null,
          medianWait: sim ? sim.median_wait_months : null,
          competingRisks: sim ? sim.competing_risks : null,
          outcomes: sim ? sim.outcomes : null,
          trends: sim ? sim.trends : null
        };
      });
    }

    // If we only have simulation results (no scoring), use those
    if (_simResults && _simResults.cities) {
      return _simResults.cities.map(function (c, i) {
        return {
          code: c.center_code || '',
          name: c.center_name || c.city,
          state: c.state,
          stateAbbr: '',
          lat: c.lat,
          lon: c.lon,
          score: null,
          breakdown: null,
          rank: i + 1,
          p24: c.p_transplant_24mo,
          p6: c.p_transplant_6mo,
          p12: c.p_transplant_12mo,
          p36: c.p_transplant_36mo,
          ci95: c.confidence_interval_95,
          medianWait: c.median_wait_months,
          competingRisks: c.competing_risks,
          outcomes: c.outcomes,
          trends: c.trends
        };
      });
    }

    return [];
  }

  /**
   * Get the seed used in the last simulation run.
   * @returns {number|null}
   */
  function getLastSeed() {
    return _simResults ? _simResults.seed_used : null;
  }

  /**
   * Get the last form data submitted.
   * @returns {Object|null}
   */
  function getFormData() {
    return _formData;
  }

  /**
   * Get the home location (geocoded).
   * @returns {{lat, lon, display}|null}
   */
  function getHomeLocation() {
    return _homeLocation;
  }

  /**
   * Get raw scoring result.
   */
  function getScoreResults() {
    return _scoreResults;
  }

  /**
   * Get raw simulation result.
   */
  function getSimResults() {
    return _simResults;
  }

  /**
   * Clear all results.
   */
  function clear() {
    _scoreResults = null;
    _simResults = null;
    _formData = null;
    _homeLocation = null;
  }

  window.SimResults = {
    runScoring: runScoring,
    runSimulation: runSimulation,
    geocodeHome: geocodeHome,
    getMergedResults: getMergedResults,
    getLastSeed: getLastSeed,
    getFormData: getFormData,
    getHomeLocation: getHomeLocation,
    getScoreResults: getScoreResults,
    getSimResults: getSimResults,
    clear: clear
  };
})();
