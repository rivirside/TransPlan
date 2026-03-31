/**
 * validation/clinical-sensitivity.js — Tornado chart for clinical sensitivity.
 */
(function () {
  'use strict';

  function getBaseUrl() { return window.TransPlanBackend || ''; }

  function setLoading(on) {
    var el = document.getElementById('cs-loading');
    if (el) el.classList.toggle('visible', on);
  }
  function setError(msg) {
    var el = document.getElementById('cs-error');
    if (!el) return;
    if (msg) { el.textContent = msg; el.classList.add('visible'); }
    else { el.textContent = ''; el.classList.remove('visible'); }
  }
  function show(el) { if (el) el.style.display = ''; }
  function hide(el) { if (el) el.style.display = 'none'; }

  function drawTornado(impacts) {
    var area = document.getElementById('cs-chart-area');
    if (!area) return;
    while (area.firstChild) area.removeChild(area.firstChild);

    if (!impacts || impacts.length === 0) return;

    var W = 600, rowH = 36, pad = { top: 24, left: 160, right: 20, bottom: 20 };
    var H = pad.top + impacts.length * rowH + pad.bottom;
    var chartW = W - pad.left - pad.right;

    var ns = 'http://www.w3.org/2000/svg';
    var svg = document.createElementNS(ns, 'svg');
    svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
    svg.setAttribute('width', '100%');
    svg.setAttribute('height', H);
    svg.style.display = 'block';

    // Background
    var bg = document.createElementNS(ns, 'rect');
    bg.setAttribute('width', W); bg.setAttribute('height', H);
    bg.setAttribute('fill', 'var(--well-bg, #f9fafb)');
    svg.appendChild(bg);

    // Find data range
    var allP = impacts.map(function (imp) { return [imp.p24_at_low, imp.p24_at_high, imp.p24_baseline]; }).flat();
    var minP = Math.min.apply(null, allP);
    var maxP = Math.max.apply(null, allP);
    var range = maxP - minP || 0.01;

    function xScale(p) {
      return pad.left + ((p - minP) / range) * chartW;
    }

    // Baseline line
    var bx = xScale(impacts[0].p24_baseline);
    var baselineLine = document.createElementNS(ns, 'line');
    baselineLine.setAttribute('x1', bx); baselineLine.setAttribute('x2', bx);
    baselineLine.setAttribute('y1', pad.top); baselineLine.setAttribute('y2', H - pad.bottom);
    baselineLine.setAttribute('stroke', '#6b7280'); baselineLine.setAttribute('stroke-width', '1');
    baselineLine.setAttribute('stroke-dasharray', '4 3');
    svg.appendChild(baselineLine);

    // Title
    var titleEl = document.createElementNS(ns, 'text');
    titleEl.setAttribute('x', W / 2); titleEl.setAttribute('y', 14);
    titleEl.setAttribute('text-anchor', 'middle'); titleEl.setAttribute('font-size', '11');
    titleEl.setAttribute('font-weight', '600'); titleEl.setAttribute('fill', 'var(--text, #111827)');
    titleEl.textContent = 'Sensitivity Tornado (P24 impact per parameter)';
    svg.appendChild(titleEl);

    impacts.forEach(function (imp, i) {
      var y = pad.top + i * rowH;
      var barY = y + 4;
      var barH = rowH - 8;

      var xLow  = xScale(imp.p24_at_low);
      var xHigh = xScale(imp.p24_at_high);
      var xLeft = Math.min(xLow, xHigh);
      var barW  = Math.abs(xHigh - xLow);

      // Bar
      var rect = document.createElementNS(ns, 'rect');
      rect.setAttribute('x', xLeft); rect.setAttribute('y', barY);
      rect.setAttribute('width', Math.max(barW, 2)); rect.setAttribute('height', barH);
      rect.setAttribute('fill', 'var(--accent, #2563eb)'); rect.setAttribute('opacity', '0.7');
      svg.appendChild(rect);

      // Label
      var lbl = document.createElementNS(ns, 'text');
      lbl.setAttribute('x', pad.left - 6); lbl.setAttribute('y', barY + barH / 2 + 4);
      lbl.setAttribute('text-anchor', 'end'); lbl.setAttribute('font-size', '10');
      lbl.setAttribute('fill', 'var(--text, #111827)');
      lbl.textContent = imp.label;
      svg.appendChild(lbl);
    });

    area.appendChild(svg);
  }

  function renderTable(impacts) {
    var tbody = document.getElementById('cs-tbody');
    if (!tbody) return;
    while (tbody.firstChild) tbody.removeChild(tbody.firstChild);

    impacts.forEach(function (imp) {
      var impact = Math.abs(imp.p24_at_high - imp.p24_at_low);
      var tr = document.createElement('tr');

      var cells = [
        imp.label,
        imp.baseline_value.toFixed(1),
        imp.low_value.toFixed(1) + ' \u2192 ' + imp.high_value.toFixed(1),
        (imp.p24_at_low * 100).toFixed(1) + '% \u2192 ' + (imp.p24_at_high * 100).toFixed(1) + '%',
      ];
      cells.forEach(function (txt) {
        var td = document.createElement('td');
        td.textContent = txt;
        tr.appendChild(td);
      });

      var tdImpact = document.createElement('td');
      var badge = document.createElement('span');
      badge.className = 'badge ' + (impact > 0.1 ? 'badge-red' : impact > 0.05 ? 'badge-yellow' : 'badge-green');
      badge.textContent = (impact * 100).toFixed(1) + '%';
      tdImpact.appendChild(badge);
      tr.appendChild(tdImpact);

      tbody.appendChild(tr);
    });
  }

  function run() {
    var btn = document.getElementById('cs-run-btn');
    if (btn) btn.disabled = true;
    setError(null);
    setLoading(true);
    hide(document.getElementById('cs-results'));

    var organ = document.getElementById('cs-organ').value;
    var bt = document.getElementById('cs-bt').value;
    var age = parseInt(document.getElementById('cs-age').value, 10) || 45;
    var city = document.getElementById('cs-city').value || 'Nashville';
    var iters = parseInt(document.getElementById('cs-iter').value, 10) || 300;

    var params = new URLSearchParams({
      city: city,
      iterations: iters,
    });
    var patient = { organ: organ, blood_type: bt, age: age, sex: 'male', urgency: 2 };

    fetch(getBaseUrl() + '/validation/clinical-sensitivity?' + params.toString(), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patient),
    })
      .then(function (r) { return r.ok ? r.json() : r.json().then(function (e) { throw new Error(e.detail || r.status); }); })
      .then(function (data) {
        setLoading(false);
        drawTornado(data.impacts);
        renderTable(data.impacts);
        show(document.getElementById('cs-results'));
      })
      .catch(function (err) {
        setLoading(false);
        setError('Error: ' + err.message);
      })
      .finally(function () { if (btn) btn.disabled = false; });
  }

  function init() {
    var btn = document.getElementById('cs-run-btn');
    if (btn) btn.addEventListener('click', run);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
