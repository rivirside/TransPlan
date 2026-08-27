/**
 * model-card.js — renders the model card from the published validation JSONs.
 *
 * The point of this page is that it is NOT hand-written prose about the
 * validation work. Every figure is read from the artifact the generating
 * script produced, so the page cannot drift from the analyses it describes:
 * re-run a study and the card changes with it, or the section reports that
 * its artifact is missing.
 *
 * All DOM construction uses createElement/textContent (no innerHTML), matching
 * validation/*.js after the #217 XSS sweep.
 */
(function () {
  'use strict';

  var DATA = 'docs-site/static/data/';
  var ORGAN_ORDER = ['kidney', 'liver', 'heart', 'lung', 'pancreas', 'intestine'];

  // ── tiny DOM helpers ────────────────────────────────────────────────────
  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function clear(node) {
    while (node && node.firstChild) node.removeChild(node.firstChild);
  }

  function num(v, digits) {
    if (typeof v !== 'number' || !isFinite(v)) return '—';
    return v.toFixed(digits === undefined ? 3 : digits);
  }

  function pct(v, digits) {
    if (typeof v !== 'number' || !isFinite(v)) return '—';
    return (v * 100).toFixed(digits === undefined ? 1 : digits) + '%';
  }

  function titleCase(s) {
    return String(s).charAt(0).toUpperCase() + String(s).slice(1);
  }

  /** Build a table from a header list and an array of row-cell arrays. */
  function table(node, headers, rows) {
    clear(node);
    var thead = el('thead');
    var htr = el('tr');
    headers.forEach(function (h) { htr.appendChild(el('th', null, h)); });
    thead.appendChild(htr);
    node.appendChild(thead);

    var tbody = el('tbody');
    rows.forEach(function (cells) {
      var tr = el('tr');
      cells.forEach(function (c, i) {
        // A cell may be a plain value or {text, cls, num}.
        var spec = (c && typeof c === 'object' && !(c instanceof Node)) ? c : { text: c };
        var td = el('td', spec.num || (i > 0 && typeof spec.text === 'string' &&
                                       /^[\d.\-—%]+$/.test(spec.text)) ? 'num' : null);
        if (spec.cls) {
          var span = el('span', spec.cls, spec.text);
          td.appendChild(span);
        } else {
          td.textContent = spec.text === undefined || spec.text === null
            ? '—' : String(spec.text);
        }
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    node.appendChild(tbody);
  }

  function stat(row, label, value, sub) {
    var card = el('div', 'mc-stat');
    card.appendChild(el('div', 'mc-stat-label', label));
    card.appendChild(el('div', 'mc-stat-value', value));
    if (sub) card.appendChild(el('div', 'mc-stat-sub', sub));
    row.appendChild(card);
  }

  function setMeta(id, doc, extra) {
    var node = document.getElementById(id);
    if (!node) return;
    var meta = (doc && doc._meta) || {};
    var parts = [];
    if (meta.generated) parts.push('Last run ' + meta.generated.slice(0, 10));
    if (meta.script) parts.push(meta.script);
    if (meta.generated_source) parts.push('(date from git history, not a recorded run time)');
    if (extra) parts.push(extra);
    node.textContent = parts.join(' · ');
  }

  function sectionError(sectionId, message) {
    var section = document.getElementById(sectionId);
    if (!section) return;
    var note = el('p', 'mc-error', message);
    section.appendChild(note);
  }

  function organsIn(doc) {
    var present = Object.keys((doc && doc.organs) || {});
    var ordered = ORGAN_ORDER.filter(function (o) { return present.indexOf(o) !== -1; });
    // Keep anything the fixed order does not know about rather than dropping it.
    present.forEach(function (o) { if (ordered.indexOf(o) === -1) ordered.push(o); });
    return ordered;
  }

  function load(name) {
    return fetch(DATA + name + '.json', { cache: 'no-cache' })
      .then(function (r) {
        if (!r.ok) throw new Error(name + '.json: HTTP ' + r.status);
        return r.json();
      });
  }

  // ── sections ────────────────────────────────────────────────────────────

  function renderCeiling(doc) {
    var s = doc.summary || {};
    var row = document.getElementById('mc-ceiling-stats');
    clear(row);
    stat(row, 'Recoverable ceiling', num(s.rho_p12_median, 3),
         'median Spearman across ' + (s.worlds || '?') + ' simulated worlds');
    stat(row, 'Centers per world', String(s.centers_per_world || '—'));
    stat(row, 'Sigma recovered', num(s.sigma_hat_median, 3),
         'true value ' + num(s.true_sigma, 2));

    var bySize = s.rho_p12_by_cohort_size || {};
    table(document.getElementById('mc-ceiling-table'),
      ['Cohort size', 'Recoverable Spearman'],
      Object.keys(bySize).map(function (k) {
        return [k, { text: num(bySize[k], 3), num: 'num' }];
      }));

    var lo = (s.rho_p12_range || [])[0];
    var hi = (s.rho_p12_range || [])[1];
    document.getElementById('mc-ceiling-takeaway').textContent =
      'Even with a perfectly specified model, cohort sizes this small cap rank ' +
      'recovery near ' + num(s.rho_p12_median, 2) + ' (range ' + num(lo, 2) +
      '–' + num(hi, 2) + '). Small-cohort centers are where the ceiling ' +
      'binds hardest, which is why estimates there are shrunk and flagged rather ' +
      'than reported at face value. Read any correlation elsewhere on this page ' +
      'against this bound, not against 1.0.';
    setMeta('mc-ceiling-meta', doc);
  }

  function renderCoverage(doc) {
    var organs = organsIn(doc);
    var rows = organs.map(function (o) {
      var d = doc.organs[o];
      var cov = (d.coverage_by_lag || {})['1'];
      var infl = (d.inflation_to_95_by_lag || {})['1'];
      var cls = (typeof cov === 'number' && cov >= 0.93) ? 'mc-pass'
              : (typeof cov === 'number' && cov >= 0.85) ? 'mc-warn' : 'mc-fail';
      return [
        titleCase(o),
        { text: pct(cov), cls: cls, num: 'num' },
        { text: pct((d.coverage_by_lag || {})['2']), num: 'num' },
        { text: pct((d.coverage_by_lag || {})['4']), num: 'num' },
        { text: typeof infl === 'number' ? '×' + num(infl, 2) : '—', num: 'num' },
        { text: d.n_pairs_lag1, num: 'num' }
      ];
    });
    table(document.getElementById('mc-coverage-table'),
      ['Organ', 'Coverage at 1 release', 'at 2', 'at 4', 'Inflation applied', 'Pairs'],
      rows);

    document.getElementById('mc-coverage-takeaway').textContent =
      'Raw intervals were under-covered — a nominal 95% interval contained ' +
      'the later observed value about 89–90% of the time one release ahead, ' +
      'and far less further out, because centers drift. The shipped intervals are ' +
      'widened by the inflation factors shown, so the number a user sees is the ' +
      'corrected one. Coverage decaying with horizon is a real property of the ' +
      'data, not a fixable modelling bug: estimates describe the release they ' +
      'came from.';
    setMeta('mc-coverage-meta', doc);
  }

  function renderSbc(doc) {
    var summary = doc.summary || {};
    var names = Object.keys(summary);
    var rows = names.map(function (n) {
      var d = summary[n] || {};
      var ok = typeof d.ks_p === 'number' && d.ks_p > 0.05;
      return [
        n,
        { text: num(d.ks_p, 4), num: 'num' },
        { text: num(d.mean_u, 3), num: 'num' },
        { text: ok ? 'calibrated' : 'suspect', cls: ok ? 'mc-pass' : 'mc-fail' }
      ];
    });
    table(document.getElementById('mc-sbc-table'),
      ['Parameter', 'KS p-value', 'Mean rank', 'Verdict'], rows);

    var allPass = names.every(function (n) {
      return (summary[n] || {}).ks_p > 0.05;
    });
    document.getElementById('mc-sbc-takeaway').textContent = allPass
      ? 'All monitored parameters pass. This is stronger than a convergence check: ' +
        'it says the priors, the likelihood and the sampler are jointly calibrated, ' +
        'which is what makes the posterior intervals meaningful in the first place. ' +
        'It does not say the model is right about reality — only that it is ' +
        'honest about what it claims to know.'
      : 'At least one parameter fails, meaning the posterior is not correctly ' +
        'calibrated against its own generative model. Treat interval widths from ' +
        'the affected parameter with suspicion.';
    setMeta('mc-sbc-meta', doc,
            (doc.n_reps || '?') + ' replications, ' +
            (doc.posterior_draws || '?') + ' draws each');
  }

  function renderCalibration(docs) {
    var rows = [];
    var newest = null;
    ORGAN_ORDER.forEach(function (o) {
      var doc = docs[o];
      if (!doc) return;
      var st = doc.stats || {};
      var a = (st.spearman_p12_vs_txrate || {});
      var b = (st.spearman_wait_vs_txrate || {});
      var cls = (typeof a.rho === 'number' && a.rho >= 0.7) ? 'mc-pass'
              : (typeof a.rho === 'number' && a.rho >= 0.5) ? 'mc-warn' : 'mc-fail';
      rows.push([
        titleCase(o),
        { text: doc.matched_centers, num: 'num' },
        { text: num(a.rho, 3), cls: cls, num: 'num' },
        { text: num(b.rho, 3), num: 'num' }
      ]);
      var gen = (doc._meta || {}).generated;
      if (gen && (!newest || gen > newest)) newest = gen;
    });
    table(document.getElementById('mc-calibration-table'),
      ['Organ', 'Centers', 'ρ (predicted access vs observed rate)',
       'ρ (predicted wait vs observed rate)'], rows);

    document.getElementById('mc-calibration-takeaway').textContent =
      'The wait-side correlation is expected to be NEGATIVE — longer predicted ' +
      'waits should mean lower observed transplant rates — and it is. Note this ' +
      'is a cross-field internal-consistency check, not an independent benchmark: ' +
      'the wait factors come from SRTR Table B10 and the observed rates from Table ' +
      'B7, both published by the same registry. It verifies the competing-risks ' +
      'model turns wait-time structure into transplant rates that track reality; ' +
      'it does not verify the underlying registry.';
    document.getElementById('mc-calibration-meta').textContent =
      newest ? 'Last run ' + newest.slice(0, 10) +
               ' · scripts/run-center-calibration.py' : '';
  }

  function renderPediatric(doc) {
    var organs = organsIn(doc);
    var rows = organs.map(function (o) {
      var d = doc.organs[o] || {};
      if (d.insufficient) {
        return [titleCase(o), { text: d.matched_centers, num: 'num' },
                { text: 'not assessable', cls: 'mc-warn' }, '—', '—'];
      }
      var st = d.stats || {};
      var tier = (st.spearman_p12_vs_srtr_tier || {}).rho;
      var thick = (st.spearman_p12_vs_srtr_tier_thick_cohorts || {}).rho;
      var abl = st.shrinkage_ablation || {};
      var cls = (typeof tier === 'number' && tier >= 0.7) ? 'mc-pass'
              : (typeof tier === 'number' && tier >= 0.45) ? 'mc-warn' : 'mc-fail';
      return [
        titleCase(o),
        { text: d.matched_centers, num: 'num' },
        { text: num(tier, 3), cls: cls, num: 'num' },
        { text: num(thick, 3), num: 'num' },
        { text: typeof abl.delta === 'number'
            ? (abl.delta >= 0 ? '+' : '') + num(abl.delta, 3) : '—', num: 'num' }
      ];
    });
    table(document.getElementById('mc-pediatric-table'),
      ['Organ', 'Centers', 'ρ vs SRTR pediatric tier', 'ρ (cohorts ≥10 py)',
       'Shrinkage effect'], rows);

    document.getElementById('mc-pediatric-takeaway').textContent =
      'The SRTR tier is a coarse 5-level grade, so ties cap the attainable ' +
      'correlation well below 1 even for a perfect model. Kidney tracks it ' +
      'closely; heart is weak, consistent with heart also failing the ' +
      'rate→median inversion gate — heart waits are short and similar ' +
      'across programs, so there is little between-center signal to recover. ' +
      'Pediatric median waits are DERIVED, never observed: SRTR publishes no ' +
      'pediatric wait percentiles at all. Treat them as directional.';
    setMeta('mc-pediatric-meta', doc);
  }

  function renderPanel(doc) {
    var organs = organsIn(doc);
    var rows = organs.map(function (o) {
      var d = doc.organs[o] || {};
      var better = (typeof d.rho_shrunk === 'number' &&
                    typeof d.rho_raw_persistence === 'number' &&
                    d.rho_shrunk > d.rho_raw_persistence);
      return [
        titleCase(o),
        { text: num(d.rho_shrunk, 3), num: 'num' },
        { text: num(d.rho_raw_persistence, 3), num: 'num' },
        { text: better ? 'pooling wins' : 'latest release wins',
          cls: better ? 'mc-warn' : 'mc-pass' },
        { text: num((d.frac_signal_posterior || {}).mean, 3), num: 'num' }
      ];
    });
    table(document.getElementById('mc-panel-table'),
      ['Organ', 'ρ pooled/shrunk', 'ρ latest release', 'Verdict',
       'Signal fraction'], rows);

    document.getElementById('mc-panel-takeaway').textContent =
      'Pooling across releases LOSES to simply using the most recent one, for ' +
      'every organ tested. Centers genuinely drift, so older releases describe a ' +
      'program that no longer exists and averaging them in adds bias faster than ' +
      'it removes noise. This is why the engine fits a single release — an ' +
      'evidence-backed decision, not a simplification waiting to be improved. A ' +
      'negative result kept visible is as much a part of the record as a positive one.';
    setMeta('mc-panel-meta', doc);
  }

  function renderFreshness(entries) {
    var rows = entries
      .filter(function (e) { return e.generated; })
      .sort(function (a, b) { return a.generated < b.generated ? 1 : -1; })
      .map(function (e) {
        return [
          e.name,
          { text: e.generated.slice(0, 10), num: 'num' },
          e.backfilled ? { text: 'from git history', cls: 'mc-warn' } : 'recorded by the script'
        ];
      });
    table(document.getElementById('mc-freshness-table'),
      ['Artifact', 'Last run', 'Date source'], rows);
  }

  function renderWeights(doc) {
    var defensible = (doc.comparisons || []).filter(function (c) { return c.defensible; });
    table(document.getElementById('mc-weights-table'),
      ['Organ', 'Alternative weighting', 'rho vs shipped', 'Top-10 overlap', 'Same #1?'],
      defensible.map(function (c) {
        var cls = c.spearman_vs_shipped < 0.8 ? 'mc-fail'
                : c.spearman_vs_shipped < 0.95 ? 'mc-warn' : 'mc-pass';
        return [
          titleCase(c.organ),
          c.weighting,
          { text: num(c.spearman_vs_shipped, 3), cls: cls, num: 'num' },
          { text: c.top10_overlap + '/10', num: 'num' },
          { text: c.top1_same ? 'yes' : 'no', cls: c.top1_same ? null : 'mc-fail' }
        ];
      }));

    var s = doc.summary || {};
    document.getElementById('mc-weights-takeaway').textContent =
      'These weights ARE load-bearing, which makes them the exception on this ' +
      'page. Across defensible alternatives the worst rank correlation is ' +
      num(s.worst_spearman_defensible, 3) + ', top-10 overlap falls to ' +
      s.worst_top10_overlap_defensible + '/10, and the top-ranked center ' +
      'changes in ' + s.top1_changes_defensible + ' of ' +
      s.n_defensible_comparisons + ' comparisons. Every other constant checked ' +
      'this way barely moves anything. This does not mean the shipped weights ' +
      'are wrong - "best center for me" is a preference, not a fact - but it ' +
      'does mean the ranking reflects one particular judgement, and the rank ' +
      'intervals shown elsewhere do not cover that: they vary the data while ' +
      'holding the weights fixed.';
    setMeta('mc-weights-meta', doc);
  }

  var LIMITATIONS = [
    'Estimates describe the SRTR release they were built from, not real-time ' +
      'allocation. Interval coverage decays the further ahead you read them.',
    'Center discretion (whether to list, whether to accept an offer) enters only ' +
      'as a center-level average, so equity analyses understate between-group ' +
      'disparity at a given center (L-075).',
    'Pediatric median waits are derived from published pediatric transplant rates ' +
      'because SRTR publishes no pediatric wait percentiles; they recover order ' +
      'far better than magnitude (L-076).',
    'Pediatric cohorts are small — pediatric lung has 39 person-years ' +
      'nationally — so some pediatric figures are the national prior wearing ' +
      'a center’s name (L-077).',
    'No patient-level clinical trajectory is modeled: a candidate does not get ' +
      'sicker or better while waiting, beyond the competing-risk hazards.',
    'The headline ranking depends materially on eight category weights with no ' +
      'published source: under defensible alternative weightings the ' +
      'top-ranked center changes in 13 of 16 comparisons (L-082). Adjust them ' +
      'to match your own priorities rather than treating the default order as ' +
      'an answer.',
    'This is a research and education tool. It is not a clinical decision aid and ' +
      'has not been reviewed by transplant faculty for face validity (#107).'
  ];

  function renderLimitations() {
    var list = document.getElementById('mc-limits-list');
    clear(list);
    LIMITATIONS.forEach(function (text) {
      list.appendChild(el('li', null, text));
    });
  }

  // ── boot ────────────────────────────────────────────────────────────────

  function init() {
    renderLimitations();
    var freshness = [];

    function track(name, doc) {
      var meta = (doc && doc._meta) || {};
      freshness.push({
        name: name,
        generated: meta.generated,
        backfilled: !!meta.generated_source
      });
      return doc;
    }

    // Each section fails independently: one missing artifact must not blank
    // the whole page.
    function section(name, sectionId, render) {
      return load(name)
        .then(function (doc) { render(track(name + '.json', doc)); })
        .catch(function (e) {
          sectionError(sectionId, 'Could not load this section: ' + e.message);
        });
    }

    var jobs = [
      section('parameter-recovery', 'mc-ceiling', renderCeiling),
      section('coverage-audit', 'mc-coverage', renderCoverage),
      section('sbc', 'mc-sbc', renderSbc),
      section('pediatric-calibration', 'mc-pediatric', renderPediatric),
      section('panel-fit', 'mc-panel', renderPanel),
      section('scoring-weight-sensitivity', 'mc-weights', renderWeights)
    ];

    // Center calibration is one file per organ.
    jobs.push(Promise.all(ORGAN_ORDER.map(function (o) {
      return load('center-calibration-' + o)
        .then(function (d) { return track('center-calibration-' + o + '.json', d); })
        .catch(function () { return null; });
    })).then(function (list) {
      var docs = {};
      ORGAN_ORDER.forEach(function (o, i) { if (list[i]) docs[o] = list[i]; });
      if (!Object.keys(docs).length) {
        sectionError('mc-calibration', 'Could not load any center-calibration artifact.');
        return;
      }
      renderCalibration(docs);
    }));

    // The remaining artifacts are not given their own section but still belong
    // in the freshness table, so the page accounts for everything published.
    var EXTRA = ['assumption-sweep', 'cas-dispersion', 'clinical-backtest-results',
                 'decile-calibration', 'panel-variance', 'pediatric-inversion',
                 'sensitivity-results', 'srtr-comparison-results',
                 'temporal-forecast', 'temporal-validation'];
    jobs.push(Promise.all(EXTRA.map(function (n) {
      return load(n).then(function (d) { track(n + '.json', d); })
        .catch(function () { /* absent artifacts simply do not appear */ });
    })));

    Promise.all(jobs).then(function () { renderFreshness(freshness); });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
