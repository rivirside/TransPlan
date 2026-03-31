/**
 * validation/convergence.js — MCMC convergence diagnostics (R-hat, ESS).
 */
(function () {
  'use strict';

  function getBaseUrl() { return window.TransPlanBackend || ''; }

  function setLoading(on) {
    var el = document.getElementById('cv-loading');
    if (el) el.classList.toggle('visible', on);
  }
  function setError(msg) {
    var el = document.getElementById('cv-error');
    if (!el) return;
    if (msg) { el.textContent = msg; el.classList.add('visible'); }
    else { el.textContent = ''; el.classList.remove('visible'); }
  }
  function show(el) { if (el) el.style.display = ''; }
  function hide(el) { if (el) el.style.display = 'none'; }

  function renderResults(data) {
    var statsRow = document.getElementById('cv-stats');
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

      if (data.available) {
        addStat('Max R-hat', isNaN(data.max_r_hat) ? '\u2014' : data.max_r_hat.toFixed(3), '< 1.01 = converged');
        addStat('Min ESS', isNaN(data.min_ess) ? '\u2014' : data.min_ess.toFixed(0), '> 400 recommended');
        addStat('Chains', String(data.n_chains));
        addStat('Draws', String(data.n_draws));
        addStat('Status', data.converged ? 'Converged' : 'Not converged');
      }
    }

    var content = document.getElementById('cv-content');
    if (!content) return;
    while (content.firstChild) content.removeChild(content.firstChild);

    if (!data.available) {
      var na = document.createElement('div');
      na.className = 'convergence-not-available';
      var msg = document.createElement('p');
      msg.textContent = data.notes[0] || 'MCMC trace not available.';
      na.appendChild(msg);
      if (data.notes[0] && data.notes[0].includes('fit-mcmc')) {
        var codeP = document.createElement('p');
        var code = document.createElement('code');
        code.textContent = 'python scripts/fit-mcmc-model.py --organ ' + data.organ;
        codeP.appendChild(code);
        na.appendChild(codeP);
      }
      content.appendChild(na);
      return;
    }

    if (data.parameters.length === 0) {
      var p = document.createElement('p');
      p.textContent = 'No parameters found in trace.';
      content.appendChild(p);
      return;
    }

    var table = document.createElement('table');
    table.className = 'val-table';

    var thead = document.createElement('thead');
    var headerRow = document.createElement('tr');
    ['Parameter', 'R-hat', 'ESS Bulk', 'ESS Tail', 'Autocorr (lag-1)'].forEach(function (h) {
      var th = document.createElement('th');
      th.textContent = h;
      headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    var tbody = document.createElement('tbody');
    data.parameters.forEach(function (param) {
      var tr = document.createElement('tr');

      var cells = [
        { text: param.name },
        {
          text: isNaN(param.r_hat) ? '\u2014' : param.r_hat.toFixed(3),
          badgeClass: isNaN(param.r_hat) ? '' : (param.r_hat < 1.01 ? 'badge-green' : 'badge-red'),
        },
        { text: isNaN(param.ess_bulk) ? '\u2014' : param.ess_bulk.toFixed(0) },
        { text: isNaN(param.ess_tail) ? '\u2014' : param.ess_tail.toFixed(0) },
        { text: isNaN(param.autocorr_lag1) ? '\u2014' : param.autocorr_lag1.toFixed(3) },
      ];

      cells.forEach(function (cell) {
        var td = document.createElement('td');
        if (cell.badgeClass) {
          var badge = document.createElement('span');
          badge.className = 'badge ' + cell.badgeClass;
          badge.textContent = cell.text;
          td.appendChild(badge);
        } else {
          td.textContent = cell.text;
        }
        tr.appendChild(td);
      });

      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    content.appendChild(table);

    if (data.notes && data.notes.length) {
      data.notes.forEach(function (note) {
        var noteEl = document.createElement('p');
        noteEl.style.cssText = 'margin-top:0.5rem;font-size:0.8rem;color:var(--text-muted,#6b7280)';
        noteEl.textContent = note;
        content.appendChild(noteEl);
      });
    }
  }

  function run() {
    var btn = document.getElementById('cv-run-btn');
    if (btn) btn.disabled = true;
    setError(null);
    setLoading(true);
    hide(document.getElementById('cv-results'));

    var organ = document.getElementById('cv-organ').value;

    fetch(getBaseUrl() + '/validation/convergence/' + organ)
      .then(function (r) { return r.ok ? r.json() : r.json().then(function (e) { throw new Error(e.detail || r.status); }); })
      .then(function (data) {
        setLoading(false);
        renderResults(data);
        show(document.getElementById('cv-results'));
      })
      .catch(function (err) {
        setLoading(false);
        setError('Error: ' + err.message);
      })
      .finally(function () { if (btn) btn.disabled = false; });
  }

  function init() {
    var btn = document.getElementById('cv-run-btn');
    if (btn) btn.addEventListener('click', run);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
