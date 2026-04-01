/**
 * validation/enhancement-comparison.js — Compare MC enhancement modes.
 *
 * Runs 4 simulations with the same seed:
 *   1. Baseline (all enhancements off)
 *   2. +Acceptance (model_acceptance=true)
 *   3. +Score Drift (model_score_drift=true)
 *   4. +Trends (trend_years=2.0)
 *
 * Renders a comparison table showing rank changes and p24 deltas.
 */
(function () {
  'use strict';

  function getBaseUrl() { return window.TransPlanBackend || ''; }

  function buildPatient() {
    var organ = document.getElementById('ec-organ').value;
    var patient = {
      organ: organ,
      blood_type: document.getElementById('ec-bt').value,
      age: 45,
      sex: 'male',
      urgency: 2,
    };
    if (organ === 'liver') {
      var meld = document.getElementById('ec-meld');
      if (meld) patient.meld = parseInt(meld.value, 10) || 20;
    }
    if (organ === 'lung') {
      patient.las = 50;
    }
    return patient;
  }

  function show(el) { if (el) el.style.display = ''; }
  function hide(el) { if (el) el.style.display = 'none'; }
  function setLoading(on) {
    var el = document.getElementById('ec-loading');
    if (el) el.classList.toggle('visible', on);
  }
  function setError(msg) {
    var el = document.getElementById('ec-error');
    if (!el) return;
    if (msg) { el.textContent = msg; el.classList.add('visible'); }
    else { el.textContent = ''; el.classList.remove('visible'); }
  }

  async function fetchSim(patient, iterations, seed, queryExtra) {
    var base = getBaseUrl();
    var qp = ['iterations=' + iterations, 'seed=' + seed];
    if (queryExtra) qp.push(queryExtra);
    var url = base + '/simulate?' + qp.join('&');
    var res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patient),
    });
    if (!res.ok) throw new Error('API error: ' + res.status);
    return res.json();
  }

  async function run() {
    setLoading(true);
    setError(null);
    hide(document.getElementById('ec-results'));

    try {
      var patient = buildPatient();
      var iter = parseInt(document.getElementById('ec-iter').value, 10) || 500;
      var seed = 42;

      var results = await Promise.all([
        fetchSim(patient, iter, seed, null),
        fetchSim(patient, iter, seed, 'model_acceptance=true'),
        fetchSim(patient, iter, seed, 'model_score_drift=true'),
        fetchSim(patient, iter, seed, 'trend_years=2.0'),
      ]);

      renderResults(results[0], results[1], results[2], results[3]);
      show(document.getElementById('ec-results'));
    } catch (err) {
      setError('Comparison failed: ' + err.message);
    } finally {
      setLoading(false);
    }
  }

  function buildRankMap(result) {
    var map = {};
    result.cities.forEach(function (c, i) {
      map[c.center_code || c.city] = { rank: i + 1, p24: c.p_transplant_24mo, city: c.city, state: c.state, code: c.center_code };
    });
    return map;
  }

  function renderResults(baseline, withAccept, withDrift, withTrends) {
    var baseMap = buildRankMap(baseline);
    var acceptMap = buildRankMap(withAccept);
    var driftMap = buildRankMap(withDrift);
    var trendsMap = buildRankMap(withTrends);

    var rows = baseline.cities.map(function (c) {
      var key = c.center_code || c.city;
      var bRank = baseMap[key].rank;
      var aRank = acceptMap[key] ? acceptMap[key].rank : bRank;
      var dRank = driftMap[key] ? driftMap[key].rank : bRank;
      var tRank = trendsMap[key] ? trendsMap[key].rank : bRank;
      var bp24 = baseMap[key].p24;
      var ap24 = acceptMap[key] ? acceptMap[key].p24 : bp24;
      var dp24 = driftMap[key] ? driftMap[key].p24 : bp24;
      var tp24 = trendsMap[key] ? trendsMap[key].p24 : bp24;
      var maxDelta = Math.max(
        Math.abs(aRank - bRank),
        Math.abs(dRank - bRank),
        Math.abs(tRank - bRank)
      );
      return {
        city: c.city, state: c.state, code: key,
        bRank: bRank, aRank: aRank, dRank: dRank, tRank: tRank,
        bp24: bp24, ap24: ap24, dp24: dp24, tp24: tp24,
        maxDelta: maxDelta,
      };
    });

    rows.sort(function (a, b) { return b.maxDelta - a.maxDelta; });

    renderStats(rows, baseline.cities.length);
    renderTable(rows);
  }

  function renderStats(rows, totalCenters) {
    var statsEl = document.getElementById('ec-stats');
    if (!statsEl) return;
    var nChanged = rows.filter(function (r) { return r.maxDelta > 0; }).length;
    var maxMove = rows.length > 0 ? rows[0].maxDelta : 0;

    statsEl.textContent = '';
    var stats = [
      { value: nChanged, label: 'Centers Affected' },
      { value: maxMove, label: 'Max Rank Move' },
      { value: totalCenters, label: 'Total Centers' },
    ];
    stats.forEach(function (s) {
      var div = document.createElement('div');
      div.className = 'val-stat';
      var valSpan = document.createElement('span');
      valSpan.className = 'val-stat-value';
      valSpan.textContent = s.value;
      var lblSpan = document.createElement('span');
      lblSpan.className = 'val-stat-label';
      lblSpan.textContent = s.label;
      div.appendChild(valSpan);
      div.appendChild(lblSpan);
      statsEl.appendChild(div);
    });
  }

  function renderTable(rows) {
    var tbody = document.getElementById('ec-tbody');
    if (!tbody) return;
    tbody.textContent = '';
    var limit = Math.min(rows.length, 30);
    for (var i = 0; i < limit; i++) {
      var r = rows[i];
      var tr = document.createElement('tr');

      appendCell(tr, r.city, r.code);
      appendCell(tr, r.state);
      appendCell(tr, String(r.bRank));
      appendRankDelta(tr, r.bRank, r.aRank);
      appendRankDelta(tr, r.bRank, r.dRank);
      appendRankDelta(tr, r.bRank, r.tRank);
      appendCell(tr, r.bp24.toFixed(3));
      appendP24Delta(tr, r.bp24, r.ap24);
      appendP24Delta(tr, r.bp24, r.dp24);
      appendP24Delta(tr, r.bp24, r.tp24);
      appendCell(tr, String(r.maxDelta));

      tbody.appendChild(tr);
    }
  }

  function appendCell(tr, text, title) {
    var td = document.createElement('td');
    td.textContent = text;
    if (title) td.title = title;
    tr.appendChild(td);
  }

  function appendRankDelta(tr, base, current) {
    var td = document.createElement('td');
    var delta = current - base;
    if (delta === 0) {
      td.textContent = String(current);
    } else {
      var span = document.createElement('span');
      span.style.color = delta < 0 ? 'green' : 'red';
      var arrow = delta < 0 ? '\u25B2' : '\u25BC';
      span.textContent = current + ' (' + arrow + Math.abs(delta) + ')';
      td.appendChild(span);
    }
    tr.appendChild(td);
  }

  function appendP24Delta(tr, base, current) {
    var td = document.createElement('td');
    var delta = current - base;
    if (Math.abs(delta) < 0.0005) {
      td.textContent = current.toFixed(3);
    } else {
      var span = document.createElement('span');
      span.style.color = delta > 0 ? 'green' : 'red';
      var sign = delta > 0 ? '+' : '';
      span.textContent = current.toFixed(3) + ' (' + sign + delta.toFixed(3) + ')';
      td.appendChild(span);
    }
    tr.appendChild(td);
  }

  function init() {
    var btn = document.getElementById('ec-run-btn');
    if (btn) btn.addEventListener('click', run);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
