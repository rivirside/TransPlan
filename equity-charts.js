/**
 * TransPlan Phase 3 M4 — Equity Analysis Charts
 *
 * Provides Chart.js visualizations for demographic equity analysis:
 * 1. Blood Type Disparity — bar chart, 8 blood types, avg p24 y-axis
 * 2. Age Bracket Disparity — bar chart, 3 age brackets
 * 3. Gini by City — horizontal bar, 22 cities sorted by Gini, green/yellow/red
 */
(function () {
  'use strict';

  // Chart instances for cleanup
  var instances = {};

  function destroyChart(id) {
    if (instances[id]) {
      instances[id].destroy();
      delete instances[id];
    }
  }

  /**
   * Color for a Gini value: green (<0.15), yellow (0.15-0.3), red (>0.3).
   */
  function giniColor(g, alpha) {
    alpha = alpha || 1;
    if (g < 0.15) return 'rgba(29, 158, 92, ' + alpha + ')';   // success green
    if (g < 0.30) return 'rgba(212, 134, 10, ' + alpha + ')';  // warning amber
    return 'rgba(217, 59, 59, ' + alpha + ')';                  // danger red
  }

  /**
   * Render blood type disparity bar chart.
   * Shows average p24 for each of the 8 blood types.
   *
   * @param {string} canvasId - Canvas element ID
   * @param {Array} dimensionData - Array of {value, p24, median_wait} for blood_type dimension
   */
  function renderBloodTypeDisparityChart(canvasId, dimensionData) {
    var canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === 'undefined') return;
    if (!dimensionData || !dimensionData.length) return;

    destroyChart(canvasId);

    var labels = dimensionData.map(function (d) { return d.value; });
    var p24Values = dimensionData.map(function (d) { return d.p24; });

    // Color gradient: higher p24 = greener, lower = more red
    var maxP24 = Math.max.apply(null, p24Values);
    var minP24 = Math.min.apply(null, p24Values);
    var range = maxP24 - minP24 || 1;
    var barColors = p24Values.map(function (p) {
      var ratio = (p - minP24) / range;
      // Interpolate from danger (low) through warning to success (high)
      if (ratio < 0.5) {
        var t = ratio * 2;
        return 'rgba(' + Math.round(217 - 5 * t) + ',' + Math.round(59 + 75 * t) + ',' + Math.round(59 - 49 * t) + ', 0.75)';
      } else {
        var t2 = (ratio - 0.5) * 2;
        return 'rgba(' + Math.round(212 - 183 * t2) + ',' + Math.round(134 + 24 * t2) + ',' + Math.round(10 + 82 * t2) + ', 0.75)';
      }
    });

    instances[canvasId] = new Chart(canvas, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'P(Transplant 24mo)',
          data: p24Values,
          backgroundColor: barColors,
          borderColor: barColors.map(function (c) { return c.replace(/[\d.]+\)$/, '1)'); }),
          borderWidth: 1,
          borderRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (ctx) {
                var entry = dimensionData[ctx.dataIndex];
                return [
                  'P(24mo): ' + (entry.p24 * 100).toFixed(1) + '%',
                  'Median wait: ' + entry.median_wait.toFixed(1) + ' months'
                ];
              }
            }
          }
        },
        scales: {
          y: {
            min: 0,
            max: 1,
            ticks: {
              callback: function (v) { return (v * 100).toFixed(0) + '%'; },
              font: { size: 11 }
            },
            title: {
              display: true,
              text: 'P(Transplant 24mo)',
              font: { size: 11 }
            },
            grid: { color: 'rgba(0,0,0,0.05)' }
          },
          x: {
            ticks: { font: { size: 11 } },
            grid: { display: false }
          }
        }
      }
    });
  }

  /**
   * Render age bracket disparity bar chart.
   * Shows average p24 for each of the 3 age brackets.
   *
   * @param {string} canvasId - Canvas element ID
   * @param {Array} dimensionData - Array of {value, p24, median_wait} for age_bracket dimension
   */
  function renderAgeDisparityChart(canvasId, dimensionData) {
    var canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === 'undefined') return;
    if (!dimensionData || !dimensionData.length) return;

    destroyChart(canvasId);

    var labels = dimensionData.map(function (d) { return d.value; });
    var p24Values = dimensionData.map(function (d) { return d.p24; });

    var maxP24 = Math.max.apply(null, p24Values);
    var minP24 = Math.min.apply(null, p24Values);
    var range = maxP24 - minP24 || 1;
    var barColors = p24Values.map(function (p) {
      var ratio = (p - minP24) / range;
      if (ratio < 0.5) {
        var t = ratio * 2;
        return 'rgba(' + Math.round(217 - 5 * t) + ',' + Math.round(59 + 75 * t) + ',' + Math.round(59 - 49 * t) + ', 0.75)';
      } else {
        var t2 = (ratio - 0.5) * 2;
        return 'rgba(' + Math.round(212 - 183 * t2) + ',' + Math.round(134 + 24 * t2) + ',' + Math.round(10 + 82 * t2) + ', 0.75)';
      }
    });

    instances[canvasId] = new Chart(canvas, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'P(Transplant 24mo)',
          data: p24Values,
          backgroundColor: barColors,
          borderColor: barColors.map(function (c) { return c.replace(/[\d.]+\)$/, '1)'); }),
          borderWidth: 1,
          borderRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (ctx) {
                var entry = dimensionData[ctx.dataIndex];
                return [
                  'P(24mo): ' + (entry.p24 * 100).toFixed(1) + '%',
                  'Median wait: ' + entry.median_wait.toFixed(1) + ' months'
                ];
              }
            }
          }
        },
        scales: {
          y: {
            min: 0,
            max: 1,
            ticks: {
              callback: function (v) { return (v * 100).toFixed(0) + '%'; },
              font: { size: 11 }
            },
            title: {
              display: true,
              text: 'P(Transplant 24mo)',
              font: { size: 11 }
            },
            grid: { color: 'rgba(0,0,0,0.05)' }
          },
          x: {
            ticks: { font: { size: 11 } },
            grid: { display: false }
          }
        }
      }
    });
  }

  /**
   * Render Gini coefficient by city as horizontal bar chart.
   * Cities sorted by Gini ascending. Color-coded green/yellow/red.
   *
   * @param {string} canvasId - Canvas element ID
   * @param {Array} cities - Array of CityEquity objects (already sorted by Gini ascending)
   */
  function renderGiniByCity(canvasId, cities) {
    var canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === 'undefined') return;
    if (!cities || !cities.length) return;

    destroyChart(canvasId);

    var labels = cities.map(function (c) { return c.city; });
    var giniValues = cities.map(function (c) { return c.gini_coefficient; });
    var barColors = giniValues.map(function (g) { return giniColor(g, 0.75); });
    var borderColors = giniValues.map(function (g) { return giniColor(g, 1); });

    instances[canvasId] = new Chart(canvas, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Gini Coefficient',
          data: giniValues,
          backgroundColor: barColors,
          borderColor: borderColors,
          borderWidth: 1,
          borderRadius: 3
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (ctx) {
                var city = cities[ctx.dataIndex];
                return [
                  'Gini: ' + city.gini_coefficient.toFixed(4),
                  'P24 range: ' + (city.p24_range[0] * 100).toFixed(1) + '% – ' + (city.p24_range[1] * 100).toFixed(1) + '%',
                  'Wait range: ' + city.median_wait_range[0].toFixed(1) + ' – ' + city.median_wait_range[1].toFixed(1) + ' months'
                ];
              }
            }
          }
        },
        scales: {
          x: {
            min: 0,
            suggestedMax: 0.5,
            ticks: {
              callback: function (v) { return v.toFixed(2); },
              font: { size: 11 }
            },
            title: {
              display: true,
              text: 'Gini Coefficient (0 = equal, 1 = unequal)',
              font: { size: 11 }
            },
            grid: { color: 'rgba(0,0,0,0.06)' }
          },
          y: {
            ticks: { font: { size: 11 } },
            grid: { display: false }
          }
        }
      }
    });
  }

  /**
   * Destroy all equity chart instances (called before re-render).
   */
  function destroyAll() {
    Object.keys(instances).forEach(function (id) {
      destroyChart(id);
    });
  }

  function getChartImage(id) {
    var chart = instances[id];
    return chart ? chart.toBase64Image() : null;
  }

  function getChartIds() {
    return Object.keys(instances);
  }

  // Expose globally
  window.TransPlanEquityCharts = {
    renderBloodTypeDisparityChart: renderBloodTypeDisparityChart,
    renderAgeDisparityChart: renderAgeDisparityChart,
    renderGiniByCity: renderGiniByCity,
    destroyAll: destroyAll,
    getChartImage: getChartImage,
    getChartIds: getChartIds
  };
})();
