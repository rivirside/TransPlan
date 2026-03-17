/**
 * TransPlan — Export Handler
 *
 * Provides CSV, JSON, and chart PNG export capabilities.
 * Uses window.TransPlanResults for data and chart module getters for images.
 * No external dependencies — pure browser APIs.
 */
(function () {
  'use strict';

  // --- Helpers ---

  function downloadBlob(blob, filename) {
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  }

  function downloadText(text, filename, mimeType) {
    var blob = new Blob([text], { type: mimeType || 'text/plain' });
    downloadBlob(blob, filename);
  }

  function downloadBase64Image(base64, filename) {
    var a = document.createElement('a');
    a.href = base64;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }

  function timestamp() {
    return new Date().toISOString().slice(0, 19).replace(/[T:]/g, '-');
  }

  // --- CSV Export ---

  function escapeCsv(val) {
    if (val === null || val === undefined) return '';
    var str = String(val);
    if (str.indexOf(',') >= 0 || str.indexOf('"') >= 0 || str.indexOf('\n') >= 0) {
      return '"' + str.replace(/"/g, '""') + '"';
    }
    return str;
  }

  function buildScoresCSV(results, formData) {
    if (!results || !results.length) return null;

    var headers = [
      'Rank', 'City', 'State', 'Overall Score',
      'Medical Compatibility', 'Wait Time', 'Donor Availability',
      'Hospital Quality', 'Geographic', 'Health Demographics',
      'Policy', 'Socioeconomic'
    ];

    var rows = [headers.map(escapeCsv).join(',')];

    results.forEach(function (city, i) {
      rows.push([
        i + 1,
        city.city,
        city.state,
        (city.personalizedScore || 0).toFixed(1),
        (city.medicalCompatibility || 0).toFixed(1),
        (city.waitTime || 0).toFixed(1),
        (city.donorAvailability || 0).toFixed(1),
        (city.hospitalQuality || 0).toFixed(1),
        (city.geographic || 0).toFixed(1),
        (city.healthDemographics || 0).toFixed(1),
        (city.policy || 0).toFixed(1),
        (city.socioeconomic || 0).toFixed(1)
      ].map(escapeCsv).join(','));
    });

    return rows.join('\n');
  }

  function buildProbabilitiesCSV(simResult) {
    if (!simResult || !simResult.cities) return null;

    var headers = [
      'Rank', 'City', 'State',
      'P(Transplant 6mo)', 'P(Transplant 12mo)', 'P(Transplant 24mo)', 'P(Transplant 36mo)',
      'Median Wait (months)', 'CI 95% Low', 'CI 95% High',
      'P(Transplant)', 'P(Mortality)', 'P(Delisting)', 'P(Still Waiting)'
    ];

    var rows = [headers.map(escapeCsv).join(',')];

    simResult.cities.forEach(function (city, i) {
      var cr = city.competing_risks || {};
      var ci = city.confidence_interval_95 || [0, 0];
      rows.push([
        i + 1,
        city.city,
        city.state,
        (city.p_transplant_6mo || 0).toFixed(4),
        (city.p_transplant_12mo || 0).toFixed(4),
        (city.p_transplant_24mo || 0).toFixed(4),
        (city.p_transplant_36mo || 0).toFixed(4),
        (city.median_wait_months || 0).toFixed(1),
        (ci[0] || 0).toFixed(4),
        (ci[1] || 0).toFixed(4),
        (cr.p_transplant || 0).toFixed(4),
        (cr.p_mortality || 0).toFixed(4),
        (cr.p_delisting || 0).toFixed(4),
        (cr.p_still_waiting || 0).toFixed(4)
      ].map(escapeCsv).join(','));
    });

    return rows.join('\n');
  }

  function exportCSV() {
    var R = window.TransPlanResults;
    if (!R) return;

    var results = R.getResults();
    var simResult = R.getSimResult();
    var formData = R.getFormData();
    var ts = timestamp();

    // Export scores
    var scoresCsv = buildScoresCSV(results, formData);
    if (scoresCsv) {
      var meta = '# TransPlan Location Scores Export\n';
      if (formData) {
        meta += '# Organ: ' + (formData.organ || '') + ', Blood Type: ' + (formData.bloodType || '') +
                ', Age: ' + (formData.age || '') + ', Sex: ' + (formData.sex || '') + '\n';
        meta += '# Generated: ' + new Date().toISOString() + '\n';
        // Weight configuration (Phase 4 M1)
        if (window.TransPlanWeights) {
          var wp = window.TransPlanWeights.getPresetName();
          var wLabels = window.TransPlanWeights.CATEGORY_LABELS;
          var wKeys = window.TransPlanWeights.CATEGORY_KEYS;
          var wCustom = window.TransPlanWeights.getWeights();
          var wVals = wCustom || window.TransPlanWeights.DEFAULT_WEIGHTS;
          meta += '# Weights (' + wp + '): ' + wKeys.map(function(k) {
            return wLabels[k] + '=' + Math.round(wVals[k] * 100) + '%';
          }).join(', ') + '\n';
        }
      }
      downloadText(meta + scoresCsv, 'transplan-scores-' + ts + '.csv', 'text/csv');
    }

    // Export probabilities if available
    if (simResult) {
      var probCsv = buildProbabilitiesCSV(simResult);
      if (probCsv) {
        var probMeta = '# TransPlan Simulation Probabilities Export\n';
        probMeta += '# Iterations: ' + (simResult.iterations || 'N/A') + '\n';
        probMeta += '# Generated: ' + new Date().toISOString() + '\n';
        downloadText(probMeta + probCsv, 'transplan-probabilities-' + ts + '.csv', 'text/csv');
      }
    }
  }

  // --- JSON Export ---

  function exportJSON() {
    var R = window.TransPlanResults;
    if (!R) return;

    var weightConfig = null;
    if (window.TransPlanWeights) {
      var wCustom = window.TransPlanWeights.getWeights();
      var wVals = wCustom || window.TransPlanWeights.DEFAULT_WEIGHTS;
      var wObj = {};
      window.TransPlanWeights.CATEGORY_KEYS.forEach(function (k) {
        wObj[k] = wVals[k];
      });
      weightConfig = {
        preset: window.TransPlanWeights.getPresetName(),
        weights: wObj
      };
    }

    var exportData = {
      metadata: {
        tool: 'TransPlan',
        version: '0.4',
        exported_at: new Date().toISOString(),
        disclaimer: 'This data is for educational and exploratory purposes only. It does not predict actual transplant outcomes.'
      },
      patient_profile: R.getFormData(),
      weight_configuration: weightConfig,
      location_scores: R.getResults(),
      simulation: R.getSimResult(),
      equity_analysis: R.getEquityResult()
    };

    var json = JSON.stringify(exportData, null, 2);
    downloadText(json, 'transplan-results-' + timestamp() + '.json', 'application/json');
  }

  // --- Chart Image Export ---

  function exportChartPNG(moduleName, chartId, filename) {
    var mod = window[moduleName];
    if (!mod || !mod.getChartImage) return false;
    var base64 = mod.getChartImage(chartId);
    if (!base64) return false;
    downloadBase64Image(base64, filename || chartId + '.png');
    return true;
  }

  function exportAllCharts() {
    var ts = timestamp();
    var exported = 0;

    // Phase 1 charts
    if (window.TransPlanCharts && window.TransPlanCharts.getChartIds) {
      window.TransPlanCharts.getChartIds().forEach(function (id) {
        if (id === 'weightsDonut') return; // Skip methodology donut
        var img = window.TransPlanCharts.getChartImage(id);
        if (img) {
          downloadBase64Image(img, 'transplan-' + id + '-' + ts + '.png');
          exported++;
        }
      });
    }

    // Phase 2 charts
    if (window.TransPlanProbCharts && window.TransPlanProbCharts.getChartIds) {
      window.TransPlanProbCharts.getChartIds().forEach(function (id) {
        var img = window.TransPlanProbCharts.getChartImage(id);
        if (img) {
          downloadBase64Image(img, 'transplan-' + id + '-' + ts + '.png');
          exported++;
        }
      });
    }

    // Equity charts
    if (window.TransPlanEquityCharts && window.TransPlanEquityCharts.getChartIds) {
      window.TransPlanEquityCharts.getChartIds().forEach(function (id) {
        var img = window.TransPlanEquityCharts.getChartImage(id);
        if (img) {
          downloadBase64Image(img, 'transplan-' + id + '-' + ts + '.png');
          exported++;
        }
      });
    }

    return exported;
  }

  // --- PDF Report ---

  function sanitize(str) {
    if (str === null || str === undefined) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function exportPDF() {
    var R = window.TransPlanResults;
    if (!R) return;

    var results = R.getResults();
    var simResult = R.getSimResult();
    var formData = R.getFormData();
    var equityResult = R.getEquityResult();

    if (!results || !results.length) return;

    var ts = new Date().toLocaleString();
    var organ = formData ? sanitize(formData.organ || 'N/A') : 'N/A';
    var bloodType = formData ? sanitize(formData.bloodType || 'N/A') : 'N/A';
    var age = formData ? sanitize(String(formData.age || 'N/A')) : 'N/A';
    var sex = formData ? sanitize(formData.sex || 'N/A') : 'N/A';
    var urgency = formData ? sanitize(String(formData.urgency || 'N/A')) : 'N/A';

    // Build report document in a new window using DOM methods
    var win = window.open('', '_blank');
    if (!win) return;

    var doc = win.document;
    doc.open();
    doc.close();

    // Set title
    doc.title = 'TransPlan Report - ' + organ + ' - ' + ts;

    // Add style
    var style = doc.createElement('style');
    style.textContent = [
      'body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;',
      'max-width:800px;margin:0 auto;padding:40px 20px;color:#1a1d2e;font-size:11pt;line-height:1.5}',
      'h1{font-size:18pt;margin-bottom:4px}h2{font-size:14pt;margin-top:24px;border-bottom:2px solid #5b6fe6;padding-bottom:4px}',
      '.disclaimer{background:#fff3cd;border:1px solid #ffc107;border-radius:4px;padding:12px;margin:16px 0;font-size:9pt}',
      '.meta{color:#6b7185;font-size:9pt;margin-bottom:16px}',
      'table{width:100%;border-collapse:collapse;margin:12px 0;font-size:9pt}',
      'th,td{text-align:left;padding:6px 8px;border-bottom:1px solid #e2e5ed}',
      'th{background:#f4f5f9;font-weight:600;font-size:8pt;text-transform:uppercase;letter-spacing:0.03em}',
      'tr:nth-child(even){background:#fafbfc}',
      '.rank-1{font-weight:700;color:#d4a017}.rank-2{color:#6b7280}.rank-3{color:#a16330}',
      '.footer{margin-top:32px;padding-top:12px;border-top:1px solid #ccc;font-size:8pt;color:#999}',
      '.profile{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:8px 0}',
      '.profile-item{background:#f4f5f9;padding:8px;border-radius:4px}',
      '.profile-label{font-size:8pt;text-transform:uppercase;letter-spacing:0.04em;color:#6b7185}',
      '.profile-value{font-weight:600;font-size:11pt}',
      '@media print{body{padding:20px}@page{margin:0.75in}}'
    ].join('');
    doc.head.appendChild(style);

    function el(tag, attrs, textContent) {
      var e = doc.createElement(tag);
      if (attrs) Object.keys(attrs).forEach(function (k) {
        if (k === 'className') e.className = attrs[k];
        else e.setAttribute(k, attrs[k]);
      });
      if (textContent !== undefined) e.textContent = textContent;
      return e;
    }

    function appendTo(parent, tag, attrs, text) {
      var e = el(tag, attrs, text);
      parent.appendChild(e);
      return e;
    }

    var body = doc.body;

    // Header
    appendTo(body, 'h1', null, 'TransPlan Location Analysis Report');
    appendTo(body, 'p', { className: 'meta' }, 'Generated: ' + ts);

    // Disclaimer
    var disc = appendTo(body, 'div', { className: 'disclaimer' });
    var strong = doc.createElement('strong');
    strong.textContent = 'Important: ';
    disc.appendChild(strong);
    disc.appendChild(doc.createTextNode(
      'This report is for educational and exploratory purposes only. It does not predict actual transplant outcomes. ' +
      'Scores reflect regional data trends, not individual clinical assessments. Always consult your transplant team before making any decisions.'
    ));

    // Patient profile
    appendTo(body, 'h2', null, 'Patient Profile');
    var profile = appendTo(body, 'div', { className: 'profile' });
    var profileItems = [
      ['Organ', organ], ['Blood Type', bloodType], ['Age', age],
      ['Sex', sex], ['Urgency', 'Level ' + urgency]
    ];
    if (formData && formData.homeCenter) {
      profileItems.push(['Home Center', sanitize(formData.homeCenter)]);
    }
    profileItems.forEach(function (item) {
      var pi = appendTo(profile, 'div', { className: 'profile-item' });
      appendTo(pi, 'div', { className: 'profile-label' }, item[0]);
      appendTo(pi, 'div', { className: 'profile-value' }, item[1]);
    });

    // Scoring Weights (Phase 4 M1)
    if (window.TransPlanWeights) {
      appendTo(body, 'h2', null, 'Scoring Weights');
      var wpName = window.TransPlanWeights.getPresetName();
      appendTo(body, 'p', { className: 'meta' }, 'Preset: ' + wpName.charAt(0).toUpperCase() + wpName.slice(1));
      var wTable = appendTo(body, 'table');
      var wThead = appendTo(wTable, 'thead');
      var wHRow = appendTo(wThead, 'tr');
      ['Category', 'Weight'].forEach(function (h) { appendTo(wHRow, 'th', null, h); });
      var wTbody = appendTo(wTable, 'tbody');
      var wCustom = window.TransPlanWeights.getWeights();
      var wVals = wCustom || window.TransPlanWeights.DEFAULT_WEIGHTS;
      var wLabels = window.TransPlanWeights.CATEGORY_LABELS;
      window.TransPlanWeights.CATEGORY_KEYS.forEach(function (k) {
        var tr = appendTo(wTbody, 'tr');
        appendTo(tr, 'td', null, wLabels[k]);
        appendTo(tr, 'td', null, Math.round(wVals[k] * 100) + '%');
      });
    }

    // Location Scores table
    appendTo(body, 'h2', null, 'Location Scores');
    var scoreHeaders = ['#', 'City', 'Score', 'Med. Compat.', 'Wait Time', 'Donor Avail.', 'Hosp. Quality', 'Geographic'];
    var scoresTable = appendTo(body, 'table');
    var thead = appendTo(scoresTable, 'thead');
    var headerRow = appendTo(thead, 'tr');
    scoreHeaders.forEach(function (h) { appendTo(headerRow, 'th', null, h); });
    var tbody = appendTo(scoresTable, 'tbody');
    results.forEach(function (city, i) {
      var tr = appendTo(tbody, 'tr', i < 3 ? { className: 'rank-' + (i + 1) } : null);
      [
        i + 1,
        sanitize(city.city) + ', ' + sanitize(city.state),
        (city.personalizedScore || 0).toFixed(1),
        (city.medicalCompatibility || 0).toFixed(1),
        (city.waitTime || 0).toFixed(1),
        (city.donorAvailability || 0).toFixed(1),
        (city.hospitalQuality || 0).toFixed(1),
        (city.geographic || 0).toFixed(1)
      ].forEach(function (val) { appendTo(tr, 'td', null, String(val)); });
    });

    // Simulation Probabilities table
    if (simResult && simResult.cities) {
      appendTo(body, 'h2', null, 'Simulation Probabilities');
      appendTo(body, 'p', { className: 'meta' }, 'Monte Carlo simulation: ' + (simResult.iterations || 'N/A') + ' iterations');
      var probHeaders = ['#', 'City', 'P(6mo)', 'P(12mo)', 'P(24mo)', 'P(36mo)', 'Median Wait', 'P(Mortality)'];
      var probTable = appendTo(body, 'table');
      var pThead = appendTo(probTable, 'thead');
      var pHRow = appendTo(pThead, 'tr');
      probHeaders.forEach(function (h) { appendTo(pHRow, 'th', null, h); });
      var pTbody = appendTo(probTable, 'tbody');
      simResult.cities.forEach(function (city, i) {
        var cr = city.competing_risks || {};
        var tr = appendTo(pTbody, 'tr', i < 3 ? { className: 'rank-' + (i + 1) } : null);
        [
          i + 1,
          sanitize(city.city) + ', ' + sanitize(city.state),
          ((city.p_transplant_6mo || 0) * 100).toFixed(1) + '%',
          ((city.p_transplant_12mo || 0) * 100).toFixed(1) + '%',
          ((city.p_transplant_24mo || 0) * 100).toFixed(1) + '%',
          ((city.p_transplant_36mo || 0) * 100).toFixed(1) + '%',
          (city.median_wait_months || 0).toFixed(1) + ' mo',
          ((cr.p_mortality || 0) * 100).toFixed(1) + '%'
        ].forEach(function (val) { appendTo(tr, 'td', null, String(val)); });
      });
    }

    // Equity summary
    if (equityResult && equityResult.cities) {
      appendTo(body, 'h2', null, 'Equity Analysis Summary');
      appendTo(body, 'p', { className: 'meta' }, 'Overall Gini coefficient: ' + (equityResult.overall_gini || 0).toFixed(3));
      var eqTable = appendTo(body, 'table');
      var eThead = appendTo(eqTable, 'thead');
      var eHRow = appendTo(eThead, 'tr');
      ['#', 'City', 'Gini', 'P(24mo) Range'].forEach(function (h) { appendTo(eHRow, 'th', null, h); });
      var eTbody = appendTo(eqTable, 'tbody');
      equityResult.cities.forEach(function (city, i) {
        var range = city.p24_range || [0, 0];
        var tr = appendTo(eTbody, 'tr');
        [
          i + 1,
          sanitize(city.city) + ', ' + sanitize(city.state),
          (city.gini_coefficient || 0).toFixed(3),
          (range[0] * 100).toFixed(1) + '% - ' + (range[1] * 100).toFixed(1) + '%'
        ].forEach(function (val) { appendTo(tr, 'td', null, String(val)); });
      });
    }

    // Footer
    var footer = appendTo(body, 'div', { className: 'footer' });
    appendTo(footer, 'p', null, 'Generated by TransPlan on ' + ts + '.');
    appendTo(footer, 'p', null,
      'This report is for informational and educational purposes only. It is not a substitute ' +
      'for professional medical advice, diagnosis, or treatment. Data sources: SRTR, OPTN, CDC, EPA, BLS.');

    // Auto-trigger print (Save as PDF) after rendering
    setTimeout(function () { win.print(); }, 500);
  }

  // --- Export Menu UI ---

  function buildExportMenu() {
    if (document.getElementById('exportMenuBtn')) return;

    var printBtn = document.getElementById('printResults');
    if (!printBtn) return;
    var headerRow = printBtn.parentElement;
    if (!headerRow) return;

    // Wrapper for dropdown
    var wrapper = document.createElement('div');
    wrapper.className = 'export-menu-wrapper';
    wrapper.style.position = 'relative';

    var btn = document.createElement('button');
    btn.id = 'exportMenuBtn';
    btn.className = 'btn-export';
    btn.type = 'button';
    btn.setAttribute('aria-haspopup', 'true');
    btn.setAttribute('aria-expanded', 'false');

    var dlIcon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    dlIcon.setAttribute('width', '14');
    dlIcon.setAttribute('height', '14');
    dlIcon.setAttribute('viewBox', '0 0 24 24');
    dlIcon.setAttribute('fill', 'none');
    dlIcon.setAttribute('stroke', 'currentColor');
    dlIcon.setAttribute('stroke-width', '2');
    dlIcon.setAttribute('stroke-linecap', 'round');
    dlIcon.setAttribute('stroke-linejoin', 'round');
    var polyline = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
    polyline.setAttribute('points', '8 17 12 21 16 17');
    var line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', '12');
    line.setAttribute('y1', '12');
    line.setAttribute('x2', '12');
    line.setAttribute('y2', '21');
    var path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', 'M20.88 18.09A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.29');
    dlIcon.appendChild(path);
    dlIcon.appendChild(polyline);
    dlIcon.appendChild(line);

    var label = document.createTextNode(' Export');
    btn.appendChild(dlIcon);
    btn.appendChild(label);

    // Dropdown menu
    var menu = document.createElement('div');
    menu.className = 'export-dropdown';
    menu.setAttribute('role', 'menu');
    menu.style.display = 'none';

    var items = [
      { label: 'PDF Report', action: exportPDF },
      { label: 'CSV (Spreadsheet)', action: exportCSV },
      { label: 'JSON (Data)', action: exportJSON },
      { label: 'Chart Images (PNG)', action: exportAllCharts }
    ];

    items.forEach(function (item) {
      var menuItem = document.createElement('button');
      menuItem.className = 'export-dropdown-item';
      menuItem.setAttribute('role', 'menuitem');
      menuItem.type = 'button';
      menuItem.textContent = item.label;
      menuItem.addEventListener('click', function () {
        item.action();
        menu.style.display = 'none';
        btn.setAttribute('aria-expanded', 'false');
      });
      menu.appendChild(menuItem);
    });

    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      var open = menu.style.display !== 'none';
      menu.style.display = open ? 'none' : 'block';
      btn.setAttribute('aria-expanded', String(!open));
    });

    // Close on outside click
    document.addEventListener('click', function () {
      menu.style.display = 'none';
      btn.setAttribute('aria-expanded', 'false');
    });

    wrapper.appendChild(btn);
    wrapper.appendChild(menu);
    headerRow.insertBefore(wrapper, printBtn);
  }

  // --- Init: Hook into form submission ---

  function init() {
    var form = document.getElementById('transplantForm');
    if (!form) return;

    form.addEventListener('submit', function () {
      setTimeout(buildExportMenu, 200);
    });
  }

  // Expose for external use (PDF module uses these)
  window.TransPlanExport = {
    exportCSV: exportCSV,
    exportJSON: exportJSON,
    exportPDF: exportPDF,
    exportAllCharts: exportAllCharts,
    exportChartPNG: exportChartPNG,
    buildScoresCSV: buildScoresCSV,
    buildProbabilitiesCSV: buildProbabilitiesCSV
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
