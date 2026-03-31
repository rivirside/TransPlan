/**
 * validation/temporal.js — Walk-forward temporal validation.
 */
(function () {
  'use strict';

  function getBaseUrl() { return window.TransPlanBackend || ''; }

  function setLoading(on) {
    var el = document.getElementById('tv-loading');
    if (el) el.classList.toggle('visible', on);
  }
  function setError(msg) {
    var el = document.getElementById('tv-error');
    if (!el) return;
    if (msg) { el.textContent = msg; el.classList.add('visible'); }
    else { el.textContent = ''; el.classList.remove('visible'); }
  }
  function show(el) { if (el) el.style.display = ''; }
  function hide(el) { if (el) el.style.display = 'none'; }

  function rhoClass(rho) {
    if (rho >= 0.85) return 'badge-green';
    if (rho >= 0.7) return 'badge-yellow';
    return 'badge-red';
  }

  function renderStats(data) {
    var row = document.getElementById('tv-stats');
    if (!row) return;
    while (row.firstChild) row.removeChild(row.firstChild);

    function addStat(label, value, sub) {
      var card = document.createElement('div');
      card.className = 'val-stat';
      var lbl = document.createElement('div'); lbl.className = 'val-stat-label'; lbl.textContent = label;
      var val = document.createElement('div'); val.className = 'val-stat-value'; val.textContent = value;
      card.appendChild(lbl); card.appendChild(val);
      if (sub) { var s = document.createElement('div'); s.className = 'val-stat-sub'; s.textContent = sub; card.appendChild(s); }
      row.appendChild(card);
    }

    addStat('Mean \u03c1', data.mean_spearman_rho.toFixed(3), 'avg across folds');
    addStat('Mean Top-5 Overlap', (data.mean_top5_overlap * 100).toFixed(0) + '%', 'Jaccard avg');
    addStat('Folds', String(data.folds.length));
    addStat('Elapsed', data.elapsed_seconds.toFixed(1) + 's');
  }

  function renderTable(folds) {
    var tbody = document.getElementById('tv-tbody');
    if (!tbody) return;
    while (tbody.firstChild) tbody.removeChild(tbody.firstChild);

    folds.forEach(function (fold) {
      var tr = document.createElement('tr');
      [
        fold.train_end_year,
        fold.test_year,
        null,
        null,
        fold.n_centers,
      ].forEach(function (val, i) {
        var td = document.createElement('td');
        if (i === 2) {
          var badge = document.createElement('span');
          badge.className = 'badge ' + rhoClass(fold.spearman_rho);
          badge.textContent = fold.spearman_rho.toFixed(3);
          td.appendChild(badge);
        } else if (i === 3) {
          td.textContent = (fold.top5_overlap * 100).toFixed(0) + '%';
        } else {
          td.textContent = String(val);
        }
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
  }

  function run() {
    var btn = document.getElementById('tv-run-btn');
    if (btn) btn.disabled = true;
    setError(null);
    setLoading(true);
    hide(document.getElementById('tv-results'));

    var organ = document.getElementById('tv-organ').value;
    var bt = document.getElementById('tv-bt').value;
    var trainStart = parseInt(document.getElementById('tv-train-start').value, 10) || 2019;
    var trainEnd = parseInt(document.getElementById('tv-train-end').value, 10) || 2022;
    var testEnd = parseInt(document.getElementById('tv-test-end').value, 10) || 2024;
    var iters = parseInt(document.getElementById('tv-iter').value, 10) || 200;

    var patient = { organ: organ, blood_type: bt, age: 45, sex: 'male', urgency: 2 };
    var payload = {
      patient: patient,
      train_start: trainStart,
      train_end: trainEnd,
      test_end: testEnd,
      iterations: iters,
    };

    fetch(getBaseUrl() + '/validation/temporal', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
      .then(function (r) { return r.ok ? r.json() : r.json().then(function (e) { throw new Error(e.detail || r.status); }); })
      .then(function (data) {
        setLoading(false);
        renderStats(data);
        renderTable(data.folds);

        var notesEl = document.getElementById('tv-notes');
        if (notesEl && data.notes && data.notes.length) {
          notesEl.textContent = data.notes.join(' | ');
        }

        show(document.getElementById('tv-results'));
      })
      .catch(function (err) {
        setLoading(false);
        setError('Error: ' + err.message);
      })
      .finally(function () { if (btn) btn.disabled = false; });
  }

  function init() {
    var btn = document.getElementById('tv-run-btn');
    if (btn) btn.addEventListener('click', run);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
