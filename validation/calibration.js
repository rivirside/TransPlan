/**
 * validation/calibration.js — Brier score calibration check.
 */
(function () {
  'use strict';

  function getBaseUrl() { return window.TransPlanBackend || ''; }

  function setLoading(on) {
    var el = document.getElementById('cal-loading');
    if (el) el.classList.toggle('visible', on);
  }
  function setError(msg) {
    var el = document.getElementById('cal-error');
    if (!el) return;
    if (msg) { el.textContent = msg; el.classList.add('visible'); }
    else { el.textContent = ''; el.classList.remove('visible'); }
  }
  function show(el) { if (el) el.style.display = ''; }
  function hide(el) { if (el) el.style.display = 'none'; }

  function brierClass(score) {
    if (score < 0.10) return 'badge-green';
    if (score < 0.20) return 'badge-yellow';
    return 'badge-red';
  }

  function renderResults(data) {
    var row = document.getElementById('cal-stats');
    if (!row) return;
    while (row.firstChild) row.removeChild(row.firstChild);

    function addStat(label, brier) {
      var card = document.createElement('div');
      card.className = 'val-stat';
      var lbl = document.createElement('div'); lbl.className = 'val-stat-label'; lbl.textContent = label;
      var val = document.createElement('div'); val.className = 'val-stat-value';
      var badge = document.createElement('span');
      badge.className = 'badge ' + brierClass(brier);
      badge.textContent = brier.toFixed(4);
      val.appendChild(badge);
      card.appendChild(lbl); card.appendChild(val);
      var sub = document.createElement('div'); sub.className = 'val-stat-sub'; sub.textContent = 'Brier score';
      card.appendChild(sub);
      row.appendChild(card);
    }

    addStat('6-Month', data.brier_score_6mo);
    addStat('12-Month', data.brier_score_12mo);
    addStat('24-Month', data.brier_score_24mo);

    var noteEl = document.getElementById('cal-note');
    if (noteEl) noteEl.textContent = data.calibration_note || '';
  }

  function run() {
    var btn = document.getElementById('cal-run-btn');
    if (btn) btn.disabled = true;
    setError(null);
    setLoading(true);
    hide(document.getElementById('cal-results'));

    var organ = document.getElementById('cal-organ').value;
    var bt = document.getElementById('cal-bt').value;
    var age = parseInt(document.getElementById('cal-age').value, 10) || 45;
    var iters = parseInt(document.getElementById('cal-iter').value, 10) || 300;

    var patient = { organ: organ, blood_type: bt, age: age, sex: 'male', urgency: 2 };
    var payload = { patient: patient, iterations: iters };

    fetch(getBaseUrl() + '/validation/calibration', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
      .then(function (r) { return r.ok ? r.json() : r.json().then(function (e) { throw new Error(e.detail || r.status); }); })
      .then(function (data) {
        setLoading(false);
        renderResults(data);
        show(document.getElementById('cal-results'));
      })
      .catch(function (err) {
        setLoading(false);
        setError('Error: ' + err.message);
      })
      .finally(function () { if (btn) btn.disabled = false; });
  }

  function init() {
    var btn = document.getElementById('cal-run-btn');
    if (btn) btn.addEventListener('click', run);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
