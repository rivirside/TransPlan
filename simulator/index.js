/**
 * simulator/index.js — Entry point for the simulator tool.
 *
 * Wires form → scoring → simulation → table/map rendering.
 * Handles URL param pre-fill for inter-tool linking.
 * Coordinates SimTierPanel, SimFormHelpers, SimMap, SimResultsTable.
 */
(function () {
  'use strict';

  // ── Collect raw form values ─────────────────────────────────────────────────

  function collectFormData() {
    var data = {
      organ:     val('organ'),
      bloodType: val('bloodType'),
      age:       val('age'),
      sex:       val('sex'),
      urgency:   val('urgency')
    };

    // Optional profile
    var w = val('weight');    if (w) data.weight = w;
    var h = val('height');    if (h) data.height = h;
    var ins = val('insurance'); if (ins) data.insurance = ins;

    // Location / reference
    var hc = val('homeCenter');      if (hc) data.homeCenter = hc;
    var loc = val('patientLocation'); if (loc) data.patientLocation = loc;

    // Organ-specific clinical scores
    var cpra = document.getElementById('cpra');
    if (cpra) data.cpra = cpra.value;
    var meld = val('meld'); if (meld) data.meld = meld;
    var las = val('las');   if (las)  data.las  = las;

    // Boolean flags
    data.adjustForCauseOfDeath = checked('adjustCauseOfDeath');
    data.useCopula             = checked('useCopula');

    // Scoring weights (from weight-config.js)
    if (window.TransPlanWeights) {
      data.weights = window.TransPlanWeights.getWeights();
    }

    return data;
  }

  function val(id) {
    var el = document.getElementById(id);
    return el ? el.value : '';
  }

  function checked(id) {
    var el = document.getElementById(id);
    return el ? el.checked : false;
  }

  // ── Validate required fields ────────────────────────────────────────────────

  function validate(formData) {
    if (!formData.organ)     return 'Organ is required.';
    if (!formData.bloodType) return 'Blood type is required.';
    if (!formData.age)       return 'Age is required.';
    if (!formData.sex)       return 'Sex is required.';
    if (!formData.urgency)   return 'Urgency level is required.';
    return null;
  }

  // ── URL param pre-fill ──────────────────────────────────────────────────────

  function populateFromURL() {
    var params = new URLSearchParams(window.location.search);
    if (!params.toString()) return false;

    setVal('organ', params.get('organ'));
    setVal('bloodType', params.get('bt'));
    setVal('age', params.get('age'));
    setVal('sex', params.get('sex'));
    setVal('urgency', params.get('urg'));
    setVal('insurance', params.get('ins'));

    var cpra = params.get('cpra');
    if (cpra != null) {
      setVal('cpra', cpra);
      var cpraOut = document.getElementById('cpra-output');
      if (cpraOut) cpraOut.textContent = cpra + '%';
    }

    setVal('meld', params.get('meld'));
    setVal('las', params.get('las'));

    if (params.get('cop') === '1') setChecked('useCopula', true);
    if (params.get('cod') === '1') setChecked('adjustCauseOfDeath', true);

    var im = params.get('im');
    if (im) setVal('inferenceMode', im);

    // Trigger organ change to show conditional fields
    var organEl = document.getElementById('organ');
    if (organEl && organEl.value) {
      organEl.dispatchEvent(new Event('change'));
    }

    return true;
  }

  function setVal(id, v) {
    if (v == null) return;
    var el = document.getElementById(id);
    if (el) el.value = v;
  }

  function setChecked(id, v) {
    var el = document.getElementById(id);
    if (el) el.checked = v;
  }

  // ── UI state helpers ────────────────────────────────────────────────────────

  function setLoading(loading, message) {
    var spinner = document.getElementById('sim-spinner');
    var txt = document.getElementById('sim-spinner-text');
    if (!spinner) return;
    spinner.style.display = loading ? 'flex' : 'none';
    if (txt && message) txt.textContent = message;
  }

  function showResults() {
    var section = document.getElementById('sim-results-section');
    var empty   = document.getElementById('sim-empty-state');
    if (section) section.style.display = '';
    if (empty)   empty.style.display   = 'none';
  }

  function showError(msg) {
    var el = document.getElementById('sim-error');
    if (!el) return;
    el.textContent = msg;
    el.style.display = '';
    setTimeout(function () { el.style.display = 'none'; }, 8000);
  }

  function updateSeedDisplay(seed) {
    var el = document.getElementById('sim-seed-display');
    if (el && seed != null) {
      el.textContent = 'Seed: ' + seed;
      el.style.display = '';
    }
  }

  // ── Map/table update helpers ────────────────────────────────────────────────

  function refreshTable(showSimColumns) {
    var container = document.getElementById('sim-results-container');
    if (!container || !window.SimResultsTable) return;

    var scoreResult = window.SimResults.getScoreResults() || {};
    var simResult   = window.SimResults.getSimResults()   || {};
    var home        = window.SimResults.getHomeLocation();

    window.SimResultsTable.render(container, {
      scores:     scoreResult.centers   || [],
      simulation: simResult.cities      || [],
      homeLocation: home || null,
      formData:   window.SimResults.getFormData() || null
    });
  }

  function refreshMap() {
    if (!window.SimMap) return;

    var scoreResult = window.SimResults.getScoreResults() || {};
    var centers = scoreResult.centers || [];
    var home    = window.SimResults.getHomeLocation();

    // Adapt: map.js uses center_name / city; our data uses .name
    var mapped = centers.map(function (c) {
      return {
        center_name: c.name,
        city:        c.name,
        code:        c.code,
        state:       c.state,
        lat:         c.lat,
        lon:         c.lon,
        score:       c.total,
        rank:        c.rank,
        p24:         null  // filled by simulation run
      };
    });

    // Patch in simulation p24 values if available
    var simResult = window.SimResults.getSimResults();
    if (simResult && simResult.cities) {
      var simLookup = {};
      simResult.cities.forEach(function (s) {
        simLookup[s.center_code || s.city] = s;
      });
      mapped.forEach(function (m) {
        var s = simLookup[m.code] || simLookup[m.city];
        if (s) m.p24 = s.p_transplant_24mo;
      });
    }

    window.SimMap.updateWithResults(mapped, home || null);
  }

  function renderContinueButtons(formData) {
    var container = document.getElementById('sim-continue-buttons');
    if (!container || !window.TransPlanContinue) return;
    window.TransPlanContinue.renderContinueButtons(container, 'simulator', formData);
  }

  // ── Score Centers handler ───────────────────────────────────────────────────

  async function handleScore() {
    var formData = collectFormData();
    var err = validate(formData);
    if (err) { showError(err); return; }

    showResults();
    setLoading(true, 'Scoring centers...');

    try {
      // Geocode home location (best-effort, non-blocking on failure)
      if (formData.patientLocation && window.SimResults) {
        await window.SimResults.geocodeHome(formData.patientLocation);
      }

      var result = await window.SimResults.runScoring(formData);
      if (!result) {
        showError('Could not reach the API server. Is the backend running?');
        return;
      }

      refreshTable(false);
      refreshMap();
      renderContinueButtons(formData);
    } catch (e) {
      showError('Scoring failed: ' + e.message);
    } finally {
      setLoading(false);
    }
  }

  // ── Run Simulation handler ──────────────────────────────────────────────────

  async function handleSimulate() {
    var formData = collectFormData();
    var err = validate(formData);
    if (err) { showError(err); return; }

    showResults();
    setLoading(true, 'Running simulation...');

    try {
      // Score first if not already done
      if (!window.SimResults.getScoreResults()) {
        setLoading(true, 'Scoring centers...');
        var scoreResult = await window.SimResults.runScoring(formData);
        if (!scoreResult) {
          showError('Could not reach the API server. Is the backend running?');
          return;
        }
      }

      // Geocode home location
      if (formData.patientLocation && !window.SimResults.getHomeLocation()) {
        await window.SimResults.geocodeHome(formData.patientLocation);
      }

      setLoading(true, 'Running simulation...');

      var inferenceMode = val('inferenceMode') || 'monte_carlo';
      var advancedParams = window.SimFormHelpers
        ? window.SimFormHelpers.collectAdvancedParams()
        : {};

      var result = await window.SimResults.runSimulation(formData, inferenceMode, advancedParams);
      if (!result) {
        showError('Simulation failed. Check that the backend is running.');
        return;
      }

      updateSeedDisplay(window.SimResults.getLastSeed());
      refreshTable(true);
      refreshMap();
      renderContinueButtons(formData);

      // Show export button
      var exportBtn = document.getElementById('sim-export-btn');
      if (exportBtn) {
        exportBtn.style.display = '';
        exportBtn.onclick = function () {
          if (window.TransPlanExport) {
            var params = Object.assign({ inferenceMode: inferenceMode }, advancedParams);
            window.TransPlanExport.exportRunArtifact(
              'simulator', params,
              window.SimResults.getSimResults(),
              window.SimResults.getLastSeed()
            );
          }
        };
      }
    } catch (e) {
      showError('Simulation failed: ' + e.message);
    } finally {
      setLoading(false);
    }
  }

  // ── Organ change ────────────────────────────────────────────────────────────

  function handleOrganChange() {
    var organ = val('organ');

    // Show/hide conditional clinical score fields
    document.querySelectorAll('.conditional-field').forEach(function (el) {
      el.style.display = (el.getAttribute('data-organ') === organ) ? '' : 'none';
    });

    // Refresh home center dropdown
    if (window.SimFormHelpers && organ) {
      window.SimFormHelpers.populateHomeCenterDropdown('homeCenter', organ);
    }

    // Clear stale results when organ changes
    if (window.SimResults) {
      window.SimResults.clear();
    }
  }

  // ── Wire slider labels ──────────────────────────────────────────────────────

  function wireSliders() {
    if (!window.SimFormHelpers) return;
    window.SimFormHelpers.wireSliderLabel('sim-iterations', 'sim-iterations-value');
    window.SimFormHelpers.wireSliderLabel('sim-copula-theta', 'sim-copula-theta-value');
    window.SimFormHelpers.wireSliderLabel('sim-elasticity', 'sim-elasticity-value');
    window.SimFormHelpers.wireSliderLabel('sim-trend-years', 'sim-trend-years-value', ' yr');
    window.SimFormHelpers.wireSliderLabel('cpra', 'cpra-output', '%');
  }

  // ── Init ────────────────────────────────────────────────────────────────────

  function init() {
    try {
      // Tier panel (fetches /tier, applies caps)
      if (window.SimTierPanel) {
        window.SimTierPanel.init();
      }

      // Map (requires Leaflet loaded before this script)
      if (window.SimMap) {
        window.SimMap.init('sim-map');
      }

      // Wire organ change handler
      var organEl = document.getElementById('organ');
      if (organEl) {
        organEl.addEventListener('change', handleOrganChange);
        if (organEl.value) handleOrganChange();
      }

      // Wire sliders
      wireSliders();

      // Wire buttons
      var scoreBtn = document.getElementById('sim-score-btn');
      if (scoreBtn) scoreBtn.addEventListener('click', handleScore);

      var simBtn = document.getElementById('sim-run-btn');
      if (simBtn) simBtn.addEventListener('click', handleSimulate);

      // Re-score when weights change
      if (window.TransPlanWeights) {
        window.TransPlanWeights.onReScore(function () {
          if (window.SimResults && window.SimResults.getFormData()) {
            handleScore();
          }
        });
      }

      // URL param pre-fill
      var hadParams = populateFromURL();
      if (hadParams) {
        var fd = collectFormData();
        if (fd.organ && fd.bloodType && fd.age && fd.sex && fd.urgency) {
          handleScore();
        }
      }
    } catch (e) {
      console.error('[SimulatorInit] init() failed:', e.message, e.stack);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Listen for sim-center-hover events from the table to highlight map markers
  document.addEventListener('sim-center-hover', function (e) {
    if (window.SimMap && e.detail) {
      window.SimMap.highlightCenter(e.detail.code);
    }
  });

})();
