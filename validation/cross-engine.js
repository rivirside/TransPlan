/**
 * validation/cross-engine.js — Cross-engine comparison (MC vs BBN vs MCMC).
 */
(function () {
  'use strict';

  function getBaseUrl() { return window.TransPlanBackend || ''; }

  function buildPatient() {
    return {
      organ:      document.getElementById('ce-organ').value,
      blood_type: document.getElementById('ce-bt').value,
      age:        parseInt(document.getElementById('ce-age').value, 10),
      sex:        document.getElementById('ce-sex').value,
      urgency:    parseInt(document.getElementById('ce-urgency').value, 10),
    };
  }

  function show(el) { if (el) el.style.display = ''; }
  function hide(el) { if (el) el.style.display = 'none'; }
  function setLoading(on) {
    var el = document.getElementById('ce-loading');
    if (el) el.classList.toggle('visible', on);
  }
  function setError(msg) {
    var el = document.getElementById('ce-error');
    if (!el) return;
    if (msg) { el.textContent = msg; el.classList.add('visible'); }
    else { el.textContent = ''; el.classList.remove('visible'); }
  }

  function rhoColor(rho) {
    if (rho === null || rho === undefined) return 'badge-gray';
    if (rho >= 0.9) return 'badge-green';
    if (rho >= 0.7) return 'badge-yellow';
    return 'badge-red';
  }

  function renderStats(data) {
    var row = document.getElementById('ce-stats');
    if (!row) return;
    while (row.firstChild) row.removeChild(row.firstChild);

    function addStat(label, value, sub) {
      var card = document.createElement('div');
      card.className = 'val-stat';
      var lbl = document.createElement('div');
      lbl.className = 'val-stat-label';
      lbl.textContent = label;
      var val = document.createElement('div');
      val.className = 'val-stat-value';
      val.textContent = value;
      card.appendChild(lbl);
      card.appendChild(val);
      if (sub) {
        var subEl = document.createElement('div');
        subEl.className = 'val-stat-sub';
        subEl.textContent = sub;
        card.appendChild(subEl);
      }
      row.appendChild(card);
    }

    if (data.spearman_mc_bbn !== null && data.spearman_mc_bbn !== undefined) {
      addStat('MC vs BBN \u03c1', data.spearman_mc_bbn.toFixed(3), 'Spearman rank correlation');
    }
    if (data.top5_overlap_mc_bbn !== null && data.top5_overlap_mc_bbn !== undefined) {
      addStat('MC vs BBN Top-5', (data.top5_overlap_mc_bbn * 100).toFixed(0) + '%', 'Jaccard overlap');
    }
    if (data.spearman_mc_mcmc !== null && data.spearman_mc_mcmc !== undefined) {
      addStat('MC vs MCMC \u03c1', data.spearman_mc_mcmc.toFixed(3), 'Spearman rank correlation');
    }
    if (data.top5_overlap_mc_mcmc !== null && data.top5_overlap_mc_mcmc !== undefined) {
      addStat('MC vs MCMC Top-5', (data.top5_overlap_mc_mcmc * 100).toFixed(0) + '%', 'Jaccard overlap');
    }
    var elapsed = data.elapsed_seconds ? data.elapsed_seconds.toFixed(1) + 's' : '';
    if (elapsed) addStat('Elapsed', elapsed);
  }

  function renderEngines(engines) {
    var grid = document.getElementById('ce-engine-grid');
    if (!grid) return;
    while (grid.firstChild) grid.removeChild(grid.firstChild);

    engines.forEach(function (eng) {
      var card = document.createElement('div');
      card.className = 'engine-card';

      var title = document.createElement('div');
      title.className = 'engine-card-title';
      title.textContent = eng.engine.replace('_', ' ').toUpperCase();
      card.appendChild(title);

      if (!eng.available) {
        var na = document.createElement('div');
        na.className = 'engine-not-available';
        na.textContent = eng.note || 'Not available';
        card.appendChild(na);
      } else {
        var list = document.createElement('ol');
        list.className = 'top5-list';
        eng.top5.forEach(function (code, i) {
          var li = document.createElement('li');
          var num = document.createElement('span');
          num.className = 'rank-num';
          num.textContent = String(i + 1);
          var name = document.createElement('span');
          name.textContent = code;
          li.appendChild(num);
          li.appendChild(name);
          list.appendChild(li);
        });
        card.appendChild(list);
      }

      grid.appendChild(card);
    });
  }

  function run() {
    var btn = document.getElementById('ce-run-btn');
    if (btn) btn.disabled = true;
    setError(null);
    setLoading(true);
    hide(document.getElementById('ce-results'));

    var patient = buildPatient();
    var iters = parseInt(document.getElementById('ce-iter').value, 10) || 300;
    var payload = { patient: patient, iterations: iters };

    fetch(getBaseUrl() + '/validation/cross-engine', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
      .then(function (r) { return r.ok ? r.json() : r.json().then(function (e) { throw new Error(e.detail || r.status); }); })
      .then(function (data) {
        setLoading(false);
        renderStats(data);
        renderEngines(data.engines);
        show(document.getElementById('ce-results'));
      })
      .catch(function (err) {
        setLoading(false);
        setError('Error: ' + err.message);
      })
      .finally(function () {
        if (btn) btn.disabled = false;
      });
  }

  function init() {
    var btn = document.getElementById('ce-run-btn');
    if (btn) btn.addEventListener('click', run);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
