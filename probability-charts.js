/**
 * TransPlan Phase 2 Probability Charts
 *
 * Provides Chart.js visualizations for Monte Carlo simulation results:
 * 1. CDF Curves — P(transplant) over time with 95% CI shading (top 5 cities)
 * 2. Competing Risks Stacked Bar — outcome breakdown at 24 months (top 10 cities)
 */
(function () {
  'use strict';

  var CITY_COLORS = [
    '#667eea', '#f5576c', '#43e97b', '#fa709a', '#4facfe'
  ];

  var RISK_COLORS = {
    transplant: '#27ae60',
    mortality: '#e74c3c',
    delisting: '#f39c12',
    waiting: '#bdc3c7'
  };

  // Chart instances for cleanup
  var instances = {};

  function destroyChart(id) {
    if (instances[id]) {
      instances[id].destroy();
      delete instances[id];
    }
  }

  /**
   * Render CDF curves for top N cities.
   * Shows P(transplant) at 0, 6, 12, 24, 36, 60 months with smooth interpolation.
   * Shaded 95% CI band for each city.
   *
   * @param {string} canvasId - Canvas element ID
   * @param {Array} cities - SimulationResult.cities (ranked)
   * @param {number} [topN=5] - Number of cities to plot
   */
  function renderCDFChart(canvasId, cities, topN) {
    var canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === 'undefined') return;

    destroyChart(canvasId);
    topN = topN || 5;

    var timePoints = [0, 6, 12, 24, 36];
    var datasets = [];
    var topCities = cities.slice(0, topN);

    topCities.forEach(function (city, i) {
      var color = CITY_COLORS[i % CITY_COLORS.length];
      var probs = [0, city.p_transplant_6mo, city.p_transplant_12mo,
                   city.p_transplant_24mo, city.p_transplant_36mo];

      // Main line
      datasets.push({
        label: city.city + ', ' + city.state,
        data: probs,
        borderColor: color,
        backgroundColor: 'transparent',
        borderWidth: 2.5,
        pointRadius: 4,
        pointBackgroundColor: color,
        tension: 0.3,
        order: 1
      });

      // CI band (shaded area between lower and upper bounds)
      // We only have CI for 24-month; estimate proportionally for other horizons
      if (city.confidence_interval_95) {
        var ci = city.confidence_interval_95;
        var ciWidth24 = (ci[1] - ci[0]) / 2;
        // Scale CI width proportionally to probability magnitude
        var ciData = probs.map(function (p, idx) {
          if (idx === 0) return [0, 0];
          var scale = p / (city.p_transplant_24mo || 1);
          var halfWidth = ciWidth24 * scale;
          return [Math.max(0, p - halfWidth), Math.min(1, p + halfWidth)];
        });

        datasets.push({
          label: city.city + ' 95% CI',
          data: ciData.map(function (d) { return d[1]; }),
          borderColor: 'transparent',
          backgroundColor: hexToRGBA(color, 0.12),
          fill: '+1',
          pointRadius: 0,
          tension: 0.3,
          order: 2
        });
        datasets.push({
          label: '_lower_' + city.city,
          data: ciData.map(function (d) { return d[0]; }),
          borderColor: 'transparent',
          backgroundColor: 'transparent',
          fill: false,
          pointRadius: 0,
          tension: 0.3,
          order: 2
        });
      }
    });

    instances[canvasId] = new Chart(canvas, {
      type: 'line',
      data: {
        labels: timePoints.map(function (t) { return t + ' mo'; }),
        datasets: datasets
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        plugins: {
          title: {
            display: true,
            text: 'Probability of Transplant Over Time',
            font: { size: 14, weight: '600' },
            color: '#2c3e50'
          },
          legend: {
            display: true,
            position: 'bottom',
            labels: {
              filter: function (item) {
                return !item.text.startsWith('_') && !item.text.includes('95% CI');
              },
              font: { size: 11 }
            }
          },
          tooltip: {
            callbacks: {
              label: function (ctx) {
                if (ctx.dataset.label.startsWith('_') || ctx.dataset.label.includes('95% CI')) return null;
                return ctx.dataset.label + ': ' + (ctx.parsed.y * 100).toFixed(1) + '%';
              }
            }
          }
        },
        scales: {
          x: {
            title: { display: true, text: 'Months on Waitlist', font: { size: 12 } },
            grid: { color: 'rgba(0,0,0,0.05)' }
          },
          y: {
            title: { display: true, text: 'P(Transplant)', font: { size: 12 } },
            min: 0,
            max: 1,
            ticks: {
              callback: function (v) { return (v * 100) + '%'; },
              stepSize: 0.2
            },
            grid: { color: 'rgba(0,0,0,0.05)' }
          }
        }
      }
    });
  }

  /**
   * Render competing risks stacked bar chart.
   * Shows 24-month outcome distribution for top N cities.
   *
   * @param {string} canvasId - Canvas element ID
   * @param {Array} cities - SimulationResult.cities (ranked)
   * @param {number} [topN=10] - Number of cities to plot
   */
  function renderCompetingRisksChart(canvasId, cities, topN) {
    var canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === 'undefined') return;

    destroyChart(canvasId);
    topN = topN || 10;

    var topCities = cities.slice(0, topN);
    var labels = topCities.map(function (c) { return c.city; });

    var transplantData = [];
    var mortalityData = [];
    var delistingData = [];
    var waitingData = [];

    topCities.forEach(function (city) {
      var cr = city.competing_risks || {};
      transplantData.push(cr.p_transplant_24mo || city.p_transplant_24mo || 0);
      mortalityData.push(cr.p_mortality_24mo || 0);
      delistingData.push(cr.p_delisting_24mo || 0);
      waitingData.push(cr.p_still_waiting_24mo || 0);
    });

    instances[canvasId] = new Chart(canvas, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Transplanted',
            data: transplantData,
            backgroundColor: RISK_COLORS.transplant,
            borderWidth: 0
          },
          {
            label: 'Still Waiting',
            data: waitingData,
            backgroundColor: RISK_COLORS.waiting,
            borderWidth: 0
          },
          {
            label: 'Delisted',
            data: delistingData,
            backgroundColor: RISK_COLORS.delisting,
            borderWidth: 0
          },
          {
            label: 'Mortality',
            data: mortalityData,
            backgroundColor: RISK_COLORS.mortality,
            borderWidth: 0
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y',
        plugins: {
          title: {
            display: true,
            text: '24-Month Waitlist Outcomes by City',
            font: { size: 14, weight: '600' },
            color: '#2c3e50'
          },
          legend: {
            position: 'bottom',
            labels: { font: { size: 11 } }
          },
          tooltip: {
            callbacks: {
              label: function (ctx) {
                return ctx.dataset.label + ': ' + (ctx.parsed.x * 100).toFixed(1) + '%';
              }
            }
          }
        },
        scales: {
          x: {
            stacked: true,
            min: 0,
            max: 1,
            ticks: {
              callback: function (v) { return (v * 100) + '%'; }
            },
            title: { display: true, text: 'Probability', font: { size: 12 } }
          },
          y: {
            stacked: true,
            grid: { display: false }
          }
        }
      }
    });
  }

  /**
   * Destroy all probability chart instances (called before re-render).
   */
  function destroyAll() {
    Object.keys(instances).forEach(function (id) {
      destroyChart(id);
    });
  }

  function hexToRGBA(hex, alpha) {
    var r = parseInt(hex.slice(1, 3), 16);
    var g = parseInt(hex.slice(3, 5), 16);
    var b = parseInt(hex.slice(5, 7), 16);
    return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
  }

  // Expose globally
  window.TransPlanProbCharts = {
    renderCDFChart: renderCDFChart,
    renderCompetingRisksChart: renderCompetingRisksChart,
    destroyAll: destroyAll
  };
})();
