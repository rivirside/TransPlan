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

    var exportData = {
      metadata: {
        tool: 'TransPlan',
        version: '0.3',
        exported_at: new Date().toISOString(),
        disclaimer: 'This data is for educational and exploratory purposes only. It does not predict actual transplant outcomes.'
      },
      patient_profile: R.getFormData(),
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
      { label: 'CSV (Spreadsheet)', action: exportCSV, icon: 'csv' },
      { label: 'JSON (Data)', action: exportJSON, icon: 'json' },
      { label: 'Chart Images (PNG)', action: exportAllCharts, icon: 'img' }
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
