/**
 * validation/model-sensitivity.js — Parameter sweep → ranking stability chart.
 */
(function () {
  'use strict';

  function getBaseUrl() { return window.TransPlanBackend || ''; }

  function setLoading(on) {
    var el = document.getElementById('ms-loading');
    if (el) el.classList.toggle('visible', on);
  }
  function setError(msg) {
    var el = document.getElementById('ms-error');
    if (!el) return;
    if (msg) { el.textContent = msg; el.classList.add('visible'); }
    else { el.textContent = ''; el.classList.remove('visible'); }
  }
  function show(el) { if (el) el.style.display = ''; }
  function hide(el) { if (el) el.style.display = 'none'; }

  function rhoClass(rho) {
    if (rho === null || rho === undefined) return 'badge-gray';
    if (rho >= 0.9) return 'badge-green';
    if (rho >= 0.7) return 'badge-yellow';
    return 'badge-red';
  }

  function drawChart(values, rhos, paramLabel) {
    var area = document.getElementById('ms-chart-area');
    if (!area) return;
    while (area.firstChild) area.removeChild(area.firstChild);

    // Simple SVG sparkline of spearman rhos
    var valid = rhos.filter(function (r) { return r !== null && r !== undefined; });
    if (valid.length < 2) return;

    var W = 600, H = 140, pad = 40;
    var ns = 'http://www.w3.org/2000/svg';
    var svg = document.createElementNS(ns, 'svg');
    svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
    svg.setAttribute('width', '100%');
    svg.setAttribute('height', '140');
    svg.style.display = 'block';

    // Background
    var bg = document.createElementNS(ns, 'rect');
    bg.setAttribute('width', W); bg.setAttribute('height', H);
    bg.setAttribute('fill', 'var(--well-bg, #f9fafb)');
    svg.appendChild(bg);

    // Reference line at rho=1
    var refLine = document.createElementNS(ns, 'line');
    refLine.setAttribute('x1', pad); refLine.setAttribute('x2', W - pad);
    refLine.setAttribute('y1', pad); refLine.setAttribute('y2', pad);
    refLine.setAttribute('stroke', '#86efac'); refLine.setAttribute('stroke-width', '1');
    refLine.setAttribute('stroke-dasharray', '4 4');
    svg.appendChild(refLine);

    // Y axis label rho=1
    var yLabel = document.createElementNS(ns, 'text');
    yLabel.setAttribute('x', pad - 4); yLabel.setAttribute('y', pad + 4);
    yLabel.setAttribute('text-anchor', 'end');
    yLabel.setAttribute('font-size', '10');
    yLabel.setAttribute('fill', 'var(--text-muted, #6b7280)');
    yLabel.textContent = '1.0';
    svg.appendChild(yLabel);

    // Y axis label rho=0
    var y0Label = document.createElementNS(ns, 'text');
    y0Label.setAttribute('x', pad - 4); y0Label.setAttribute('y', H - pad + 4);
    y0Label.setAttribute('text-anchor', 'end');
    y0Label.setAttribute('font-size', '10');
    y0Label.setAttribute('fill', 'var(--text-muted, #6b7280)');
    y0Label.textContent = '0';
    svg.appendChild(y0Label);

    // Points: rhos[0] is always null (first step), so index from 1
    var nonNullRhos = [];
    var nonNullIdx = [];
    rhos.forEach(function (r, i) {
      if (r !== null && r !== undefined) {
        nonNullRhos.push(r);
        nonNullIdx.push(i);
      }
    });

    var n = values.length;
    function xPos(i) { return pad + (i / (n - 1)) * (W - pad * 2); }
    function yPos(r) { return H - pad - (Math.max(0, Math.min(1, r))) * (H - pad * 2); }

    // Polyline
    var pts = nonNullIdx.map(function (i, j) { return xPos(i) + ',' + yPos(nonNullRhos[j]); }).join(' ');
    if (pts) {
      var polyline = document.createElementNS(ns, 'polyline');
      polyline.setAttribute('points', pts);
      polyline.setAttribute('fill', 'none');
      polyline.setAttribute('stroke', 'var(--accent, #2563eb)');
      polyline.setAttribute('stroke-width', '2');
      svg.appendChild(polyline);
    }

    // Dots
    nonNullIdx.forEach(function (idx, j) {
      var r = nonNullRhos[j];
      var circle = document.createElementNS(ns, 'circle');
      circle.setAttribute('cx', xPos(idx));
      circle.setAttribute('cy', yPos(r));
      circle.setAttribute('r', '4');
      circle.setAttribute('fill', r >= 0.9 ? '#22c55e' : r >= 0.7 ? '#eab308' : '#ef4444');
      svg.appendChild(circle);
    });

    // X axis value labels (show first, middle, last)
    [0, Math.floor(n / 2), n - 1].forEach(function (i) {
      var lbl = document.createElementNS(ns, 'text');
      lbl.setAttribute('x', xPos(i));
      lbl.setAttribute('y', H - pad + 16);
      lbl.setAttribute('text-anchor', 'middle');
      lbl.setAttribute('font-size', '9');
      lbl.setAttribute('fill', 'var(--text-muted, #6b7280)');
      lbl.textContent = typeof values[i] === 'number' ? values[i].toFixed(2) : values[i];
      svg.appendChild(lbl);
    });

    // Chart title
    var title = document.createElementNS(ns, 'text');
    title.setAttribute('x', W / 2); title.setAttribute('y', 14);
    title.setAttribute('text-anchor', 'middle');
    title.setAttribute('font-size', '11');
    title.setAttribute('font-weight', '600');
    title.setAttribute('fill', 'var(--text, #111827)');
    title.textContent = 'Spearman \u03c1 by ' + paramLabel + ' value';
    svg.appendChild(title);

    area.appendChild(svg);
  }

  function renderTable(data) {
    var tbody = document.getElementById('ms-tbody');
    if (!tbody) return;
    while (tbody.firstChild) tbody.removeChild(tbody.firstChild);

    data.values.forEach(function (val, i) {
      var tr = document.createElement('tr');

      var tdVal = document.createElement('td');
      tdVal.textContent = typeof val === 'number' ? val.toFixed(3) : val;
      tr.appendChild(tdVal);

      var tdRho = document.createElement('td');
      var rho = data.spearman_rhos[i];
      if (rho === null || rho === undefined) {
        tdRho.textContent = '\u2014';
      } else {
        var badge = document.createElement('span');
        badge.className = 'badge ' + (rho >= 0.9 ? 'badge-green' : rho >= 0.7 ? 'badge-yellow' : 'badge-red');
        badge.textContent = rho.toFixed(3);
        tdRho.appendChild(badge);
      }
      tr.appendChild(tdRho);

      var tdOverlap = document.createElement('td');
      var overlap = data.top5_overlap_with_baseline[i];
      tdOverlap.textContent = overlap !== undefined ? (overlap * 100).toFixed(0) + '%' : '\u2014';
      tr.appendChild(tdOverlap);

      var tdTop5 = document.createElement('td');
      tdTop5.textContent = (data.top5_sets[i] || []).join(', ');
      tr.appendChild(tdTop5);

      tbody.appendChild(tr);
    });
  }

  function renderStats(data) {
    var row = document.getElementById('ms-stats');
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

    addStat('Mean \u03c1', data.mean_rho.toFixed(3), 'avg stability');
    addStat('Min \u03c1', data.min_rho.toFixed(3), 'worst case');
    addStat('Baseline Top-5', data.baseline_top5.slice(0, 3).join(', '), 'first 3 shown');
  }

  function run() {
    var btn = document.getElementById('ms-run-btn');
    if (btn) btn.disabled = true;
    setError(null);
    setLoading(true);
    hide(document.getElementById('ms-results'));

    var organ = document.getElementById('ms-organ').value;
    var bt = document.getElementById('ms-bt').value;
    var param = document.getElementById('ms-param').value;
    var steps = parseInt(document.getElementById('ms-steps').value, 10) || 6;
    var iters = parseInt(document.getElementById('ms-iter').value, 10) || 200;

    var patient = { organ: organ, blood_type: bt, age: 45, sex: 'male', urgency: 2 };
    var payload = { patient: patient, param: param, n_steps: steps, base_iterations: iters };

    fetch(getBaseUrl() + '/validation/model-sensitivity', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
      .then(function (r) { return r.ok ? r.json() : r.json().then(function (e) { throw new Error(e.detail || r.status); }); })
      .then(function (data) {
        setLoading(false);
        renderStats(data);
        drawChart(data.values, data.spearman_rhos, data.param_label);
        renderTable(data);
        show(document.getElementById('ms-results'));
      })
      .catch(function (err) {
        setLoading(false);
        setError('Error: ' + err.message);
      })
      .finally(function () { if (btn) btn.disabled = false; });
  }

  function init() {
    var btn = document.getElementById('ms-run-btn');
    if (btn) btn.addEventListener('click', run);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
