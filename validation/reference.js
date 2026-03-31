/**
 * validation/reference.js — Canonical seed=12345 reference run for regression testing.
 */
(function () {
  'use strict';

  function getBaseUrl() { return window.TransPlanBackend || ''; }

  function setLoading(on) {
    var el = document.getElementById('ref-loading');
    if (el) el.classList.toggle('visible', on);
  }
  function setError(msg) {
    var el = document.getElementById('ref-error');
    if (!el) return;
    if (msg) { el.textContent = msg; el.classList.add('visible'); }
    else { el.textContent = ''; el.classList.remove('visible'); }
  }
  function show(el) { if (el) el.style.display = ''; }
  function hide(el) { if (el) el.style.display = 'none'; }

  function renderResults(data) {
    var statsRow = document.getElementById('ref-stats');
    if (statsRow) {
      while (statsRow.firstChild) statsRow.removeChild(statsRow.firstChild);

      function addStat(label, value, sub) {
        var card = document.createElement('div');
        card.className = 'val-stat';
        var lbl = document.createElement('div'); lbl.className = 'val-stat-label'; lbl.textContent = label;
        var val = document.createElement('div'); val.className = 'val-stat-value'; val.textContent = value;
        card.appendChild(lbl); card.appendChild(val);
        if (sub) { var s = document.createElement('div'); s.className = 'val-stat-sub'; s.textContent = sub; card.appendChild(s); }
        statsRow.appendChild(card);
      }

      addStat('Seed', String(data.seed_used), 'deterministic');
      addStat('Iterations', String(data.iterations));
      addStat('Centers', String(data.cities ? data.cities.length : 0));
      addStat('Engine', data.inference_mode || 'monte_carlo');
    }

    var tbody = document.getElementById('ref-tbody');
    if (!tbody) return;
    while (tbody.firstChild) tbody.removeChild(tbody.firstChild);

    var cities = data.cities || [];
    cities.slice(0, 25).forEach(function (city, i) {
      var tr = document.createElement('tr');

      [
        String(i + 1),
        (city.center_name || city.city) + (city.center_code ? ' (' + city.center_code + ')' : ''),
        city.state || '',
        (city.p_transplant_24mo * 100).toFixed(1) + '%',
        city.median_wait_months ? city.median_wait_months.toFixed(1) + ' mo' : '\u2014',
      ].forEach(function (txt) {
        var td = document.createElement('td');
        td.textContent = txt;
        tr.appendChild(td);
      });

      tbody.appendChild(tr);
    });
  }

  function run() {
    var btn = document.getElementById('ref-run-btn');
    if (btn) btn.disabled = true;
    setError(null);
    setLoading(true);
    hide(document.getElementById('ref-results'));

    var organ = document.getElementById('ref-organ').value;

    fetch(getBaseUrl() + '/validation/reference-run/' + organ)
      .then(function (r) { return r.ok ? r.json() : r.json().then(function (e) { throw new Error(e.detail || r.status); }); })
      .then(function (data) {
        setLoading(false);
        renderResults(data);
        show(document.getElementById('ref-results'));
      })
      .catch(function (err) {
        setLoading(false);
        setError('Error: ' + err.message);
      })
      .finally(function () { if (btn) btn.disabled = false; });
  }

  function init() {
    var btn = document.getElementById('ref-run-btn');
    if (btn) btn.addEventListener('click', run);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
