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

  // ── Center shortlist (#304 / L-067) ─────────────────────────────────────────
  var _shortlist = null;  // array of SRTR codes from ?centers=..., or null

  function parseShortlistParam(params) {
    var raw = params.get('centers');
    if (!raw) return null;
    var codes = raw.split(',')
      .map(function (c) { return c.trim().toUpperCase(); })
      .filter(function (c) { return /^[A-Z0-9]{3,5}$/.test(c); })
      .slice(0, 248);
    return codes.length ? codes : null;
  }

  function renderShortlistNote() {
    var el = document.getElementById('sim-shortlist-note');
    if (!_shortlist || !_shortlist.length) {
      if (el) el.style.display = 'none';
      return;
    }
    if (!el) {
      var anchor = document.getElementById('sim-results-container') ||
                   document.getElementById('sim-run-btn');
      if (!anchor || !anchor.parentNode) return;
      el = document.createElement('div');
      el.id = 'sim-shortlist-note';
      el.style.cssText = 'margin:0.5rem 0; padding:0.5rem 0.75rem; border-left:3px solid var(--warm-accent,#c97c4a); background:var(--surface-2,#f8f5f1); font-size:0.85rem; border-radius:4px;';
      anchor.parentNode.insertBefore(el, anchor);
    }
    while (el.firstChild) el.removeChild(el.firstChild);
    el.appendChild(document.createTextNode(
      'Shortlist active: only ' + _shortlist.length + ' selected center' +
      (_shortlist.length === 1 ? '' : 's') + ' will be scored and simulated. '));
    var clear = document.createElement('a');
    clear.href = '#';
    clear.textContent = 'Show all centers';
    clear.addEventListener('click', function (e) {
      e.preventDefault();
      _shortlist = null;
      var url = new URL(window.location);
      url.searchParams.delete('centers');
      history.replaceState(null, '', url);
      renderShortlistNote();
    });
    el.appendChild(clear);
    el.style.display = '';
  }

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
    var cas = val('cas');   if (cas)  data.cas  = cas;
    var mw = val('monthsWaiting'); if (mw) data.monthsWaiting = mw;
    // PELD can be 0 or negative — a truthiness test discards real scores.
    var peld = val('peld');
    if (peld !== '' && peld !== null && !isNaN(parseFloat(peld))) data.peld = peld;

    // Boolean flags
    data.adjustForCauseOfDeath = checked('adjustCauseOfDeath');
    data.useCopula             = checked('useCopula');

    // Scoring weights (from weight-config.js)
    if (window.TransPlanWeights) {
      data.weights = window.TransPlanWeights.getWeights();
    }

    // Center shortlist (#304)
    if (_shortlist && _shortlist.length) {
      data.centerCodes = _shortlist;
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

    _shortlist = parseShortlistParam(params);
    renderShortlistNote();

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
    setVal('cas', params.get('cas'));
    setVal('monthsWaiting', params.get('mw'));

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

  /**
   * Surface the backend's data-provenance summary (#300) so degraded results
   * are never silent: says how many centers fell back to national defaults.
   */
  function renderDataQualityNote(dq, vintage) {
    var el = document.getElementById('sim-data-quality');
    if (!el) {
      var seedEl = document.getElementById('sim-seed-display');
      if (!seedEl || !seedEl.parentNode) return;
      el = document.createElement('div');
      el.id = 'sim-data-quality';
      el.style.cssText = 'font-size: 0.78rem; color: var(--text-muted, #888); margin-top: 0.25rem;';
      seedEl.parentNode.insertBefore(el, seedEl.nextSibling);
    }
    if (!dq || !dq.centers_total) {
      el.style.display = 'none';
      return;
    }
    // Data-vintage disclosure (#334): estimates reflect the SRTR release's
    // cohorts, not real-time allocation behavior.
    var vintageText = '';
    if (vintage && vintage.srtr_source) {
      vintageText = ' Source: ' + vintage.srtr_source +
        ' (reflects that release\'s cohorts, not real-time allocation).';
    }
    var degraded = dq.centers_total - (dq.fully_center_level || 0);
    if (degraded === 0) {
      el.textContent = 'Data: center-level SRTR inputs for all ' + dq.centers_total + ' centers.' + vintageText;
    } else {
      // Render every family the backend reports (#340: extensible — new tag
      // families appear here without a frontend change)
      var labels = {
        wait_time_factors: 'wait', competing_risks: 'risk',
        observed_outcomes: 'outcomes', acceptance_rates: 'acceptance',
        trend_series: 'trends'
      };
      var parts = [];
      Object.keys(dq).forEach(function (key) {
        var fam = dq[key];
        if (!fam || typeof fam !== 'object' || Array.isArray(fam)) return;
        var bad = (fam.national_default !== undefined) ? fam.national_default : fam.missing;
        if (typeof bad === 'number' && bad > 0) {
          parts.push(bad + ' ' + (labels[key] || key.replace(/_/g, ' ')));
        }
      });
      el.textContent = 'Data note: ' + degraded + ' of ' + dq.centers_total +
        ' centers use partial national-default inputs (' + parts.join(', ') + ').' + vintageText;
    }
    el.style.display = '';
  }

  /**
   * #376/L-080: when SRTR censors an organ's national median, every displayed
   * "median wait" for that organ derives from a RECONSTRUCTED figure rather
   * than a published one. Pancreas is the only organ affected today. Say so
   * where the medians are read — the column otherwise looks exactly like the
   * five organs whose medians the registry does publish.
   */
  function renderMedianProvenanceNote(dq) {
    var el = document.getElementById('sim-median-provenance');
    if (!el) {
      var anchor = document.getElementById('sim-data-quality') ||
                   document.getElementById('sim-seed-display');
      if (!anchor || !anchor.parentNode) return;
      el = document.createElement('div');
      el.id = 'sim-median-provenance';
      el.style.cssText = 'font-size: 0.82rem; margin-top: 0.4rem; padding: 0.5rem 0.65rem; border-left: 3px solid var(--warning, #d98a1f); background: var(--bg-subtle, rgba(217,138,31,0.07));';
      anchor.parentNode.insertBefore(el, anchor.nextSibling);
    }
    var fam = dq && dq.wait_median;
    if (!fam || !fam.reconstructed) {
      el.style.display = 'none';
      return;
    }
    el.textContent =
      'Median wait note: SRTR does not publish a national median for this ' +
      'organ — it reports only that the median exceeds 72 months. The median ' +
      'waits shown below are reconstructed by the model from the 25th ' +
      'percentile, so treat them as indicative rather than as registry ' +
      'figures. The transplant probabilities are calibrated against observed ' +
      'transplant rates and are not affected in the same way.';
    el.style.display = '';
  }

  /**
   * #335: pediatric candidates are scored against a different center set and
   * a different allocation system, so say so where the results are read. The
   * center count comes from the response, not the client, so it can never
   * disagree with the table below it.
   */
  function renderPediatricNote(dq, age) {
    var el = document.getElementById('sim-pediatric-note');
    if (!el) {
      var anchor = document.getElementById('sim-data-quality') ||
                   document.getElementById('sim-seed-display');
      if (!anchor || !anchor.parentNode) return;
      el = document.createElement('div');
      el.id = 'sim-pediatric-note';
      el.style.cssText = 'font-size: 0.82rem; margin-top: 0.4rem; padding: 0.5rem 0.65rem; border-left: 3px solid var(--warning, #d98a1f); background: var(--bg-subtle, rgba(217,138,31,0.07));';
      anchor.parentNode.insertBefore(el, anchor.nextSibling);
    }
    var peds = dq && dq.pediatric_cohort;
    if (!(age !== '' && age !== null && Number(age) < 18) || !peds) {
      el.style.display = 'none';
      return;
    }
    var total = (peds.adequate || 0) + (peds.small || 0);
    var txt = 'Pediatric mode: results cover only the ' + total +
      ' centers with a pediatric program for this organ, using SRTR pediatric ' +
      'cohort data. Children are allocated under different rules than adults, ' +
      'and pediatric cohorts are far smaller, so intervals are wider.';
    if (peds.small) {
      txt += ' ' + peds.small + ' of these centers have under 10 pediatric ' +
        'person-years of follow-up; their estimates are shrunk toward the ' +
        'national pediatric baseline and should be read as directional.';
    }
    // L-079: the alternative engines restrict to pediatric centers but have no
    // pediatric WAIT model, so switching inference mode silently returns adult
    // numbers. Say which model actually produced these figures.
    var waitModel = dq && dq.pediatric_wait_model;
    if (waitModel && waitModel.adult_fallback > 0) {
      txt += ' Note: this engine applies the pediatric CENTER restriction but ' +
        'not a pediatric wait model, so the wait and probability figures for ' +
        waitModel.adult_fallback + ' of these centers are adult estimates. ' +
        'Use the Monte Carlo engine for pediatric-anchored probabilities.';
    }
    el.textContent = txt;
    el.style.display = '';
  }

  /**
   * #321: when a 2-5 center shortlist is simulated, show the joint
   * probability of listing at ALL of them (with the honest coupling note).
   */
  function renderMultiListingNote(ml) {
    var el = document.getElementById('sim-multi-listing');
    if (!el) {
      var seedEl = document.getElementById('sim-data-quality') ||
                   document.getElementById('sim-seed-display');
      if (!seedEl || !seedEl.parentNode) return;
      el = document.createElement('div');
      el.id = 'sim-multi-listing';
      el.style.cssText = 'font-size: 0.82rem; margin-top: 0.4rem; padding: 0.5rem 0.65rem; border-left: 3px solid var(--accent, #4a90d9); background: var(--bg-subtle, rgba(74,144,217,0.06));';
      seedEl.parentNode.insertBefore(el, seedEl.nextSibling);
    }
    if (!ml) { el.style.display = 'none'; return; }
    var best = 0;
    ml.listings.forEach(function (l) { if (l.p24 > best) best = l.p24; });
    var names = ml.listings.map(function (l) { return l.center_code; }).join(' + ');
    el.textContent = 'Listed at all ' + ml.listings.length + ' (' + names + '): ' +
      'P(transplant \u2264 24mo) \u2248 ' + Math.round(ml.joint_p24 * 100) + '% ' +
      'vs ' + Math.round(best * 100) + '% at the best single center ' +
      '(gain +' + Math.round(ml.gain_over_best_single * 100) + ' points, an upper-bound estimate; ' +
      'nearby centers share a donor pool and add little).';
    el.title = ml.note || '';
    el.style.display = '';
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
      renderDataQualityNote(result.data_quality, result.data_vintage);
      renderPediatricNote(result.data_quality, formData.age);
      renderMedianProvenanceNote(result.data_quality);
      refreshTable(true);

      // #321: joint probability across an active 2-5 center shortlist
      if (Array.isArray(formData.centerCodes) && formData.centerCodes.length >= 2 &&
          formData.centerCodes.length <= 5 && window.TransPlanAPI.multiListing) {
        window.TransPlanAPI.multiListing(formData, formData.centerCodes,
                                         window.SimResults.getLastSeed())
          .then(renderMultiListingNote);
      } else {
        renderMultiListingNote(null);
      }

      // #313/#322: annotate ranks with bootstrap intervals (background —
      // the table renders immediately and gains intervals when they arrive)
      if (window.TransPlanAPI.rankStability && window.SimResultsTable.setRankIntervals) {
        // #350: was a hardcoded 300 while tier_config caps this at 500 — and
        // that cap was not even serialized by GET /tier until this change, so
        // there was no way to honour it. Wider intervals come from more
        // bootstrap resamples, so taking what the tier allows makes the
        // reported rank ranges as precise as the tier permits.
        var nBoot = (window.SimTierPanel && SimTierPanel.getMax('rank_stability_boot')) || 300;
        window.TransPlanAPI.rankStability(formData, nBoot, window.SimResults.getLastSeed())
          .then(function (rs) {
            if (!rs || !rs.centers) return;
            var byCode = {};
            rs.centers.forEach(function (c) {
              byCode[c.center_code] = { rank_lo: c.rank_lo, rank_hi: c.rank_hi };
            });
            // With a shortlist active the table ranks are shortlist-
            // relative while the intervals are national — label them.
            var shortlisted = Array.isArray(formData.centerCodes) &&
                              formData.centerCodes.length > 0;
            window.SimResultsTable.setRankIntervals(byCode, { national: shortlisted });
            refreshTable(true);
          });
      }
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
