/**
 * TransPlan Charts Module
 *
 * Provides Chart.js visualizations:
 * 1. Score Breakdown Radar Chart (per city card)
 * 2. City Comparison Grouped Bar Chart
 * 3. Category Weight Donut Chart (methodology section)
 * 4. Data Freshness Indicators
 */

(function () {
    'use strict';

    const CATEGORY_LABELS = [
        'Medical Compatibility',
        'Wait Time',
        'Donor Availability',
        'Hospital Quality',
        'Geographic',
        'Health Demographics',
        'Policy',
        'Socioeconomic'
    ];

    const CATEGORY_KEYS = [
        'medicalCompatibility',
        'waitTime',
        'donorAvailability',
        'hospitalQuality',
        'geographic',
        'healthDemographics',
        'policy',
        'socioeconomic'
    ];

    const DEFAULT_CATEGORY_WEIGHTS = [25, 20, 18, 15, 10, 7, 3, 2];

    /**
     * Get current category weights as integer percentages.
     * Uses custom weights from TransPlanWeights if available, otherwise defaults.
     */
    function getCategoryWeights() {
        var tw = window.TransPlanWeights;
        if (tw) {
            var custom = tw.getWeights();
            if (custom) {
                return CATEGORY_KEYS.map(function(k) { return Math.round(custom[k] * 100); });
            }
        }
        return DEFAULT_CATEGORY_WEIGHTS;
    }

    const CHART_COLORS = [
        '#667eea', '#764ba2', '#f093fb', '#f5576c',
        '#4facfe', '#00f2fe', '#43e97b', '#fa709a'
    ];

    const CITY_COLORS = [
        '#667eea', '#f5576c', '#43e97b', '#fa709a', '#4facfe',
        '#ffd700', '#ff6b6b', '#48dbfb', '#ff9ff3', '#54a0ff',
        '#5f27cd', '#01a3a4', '#f368e0', '#ff9f43', '#ee5a24',
        '#0abde3', '#10ac84', '#341f97', '#c44569', '#474787',
        '#aaa69d'
    ];

    // Store chart instances for cleanup
    const chartInstances = {};

    /**
     * Render the Category Weights Donut Chart in the methodology section.
     */
    function renderWeightsDonutChart() {
        const canvas = document.getElementById('weightsDonutChart');
        if (!canvas) return;
        if (typeof Chart === 'undefined') {
            const notice = document.createElement('p');
            notice.className = 'cdn-fallback-notice';
            notice.textContent = 'Chart unavailable \u2014 the charting library could not be loaded. Category weights are listed in the text above.';
            canvas.parentElement.replaceChildren(notice);
            return;
        }

        if (chartInstances.weightsDonut) {
            chartInstances.weightsDonut.destroy();
        }

        chartInstances.weightsDonut = new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: CATEGORY_LABELS,
                datasets: [{
                    data: getCategoryWeights(),
                    backgroundColor: CHART_COLORS,
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 12,
                            usePointStyle: true,
                            font: { size: 11 }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                return `${context.label}: ${context.raw}%`;
                            }
                        }
                    }
                }
            }
        });
    }

    /**
     * Create a radar chart for a city's score breakdown.
     * Called from displayResults for each city card.
     */
    function createRadarChart(canvasId, breakdown, cityName) {
        if (typeof Chart === 'undefined') return;
        const canvas = document.getElementById(canvasId);
        if (!canvas || !breakdown) return;

        const data = CATEGORY_KEYS.map(key => breakdown[key] || 0);

        if (chartInstances[canvasId]) {
            chartInstances[canvasId].destroy();
        }

        chartInstances[canvasId] = new Chart(canvas, {
            type: 'radar',
            data: {
                labels: CATEGORY_LABELS,
                datasets: [{
                    label: cityName,
                    data: data,
                    backgroundColor: 'rgba(102, 126, 234, 0.2)',
                    borderColor: '#667eea',
                    borderWidth: 2,
                    pointBackgroundColor: '#667eea',
                    pointBorderColor: '#fff',
                    pointRadius: 3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            stepSize: 20,
                            font: { size: 9 },
                            backdropColor: 'transparent'
                        },
                        pointLabels: {
                            font: { size: 9 }
                        },
                        grid: {
                            color: 'rgba(0,0,0,0.08)'
                        }
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                return `${context.label}: ${context.raw.toFixed(1)}`;
                            }
                        }
                    }
                }
            }
        });
    }

    /**
     * Create the city comparison grouped bar chart.
     */
    function createComparisonChart(cities) {
        const canvas = document.getElementById('comparisonChart');
        if (!canvas) return;
        if (typeof Chart === 'undefined') {
            const notice = document.createElement('p');
            notice.className = 'cdn-fallback-notice';
            notice.textContent = 'Charts unavailable \u2014 the charting library could not be loaded. Score breakdowns are shown on each city card above.';
            canvas.parentElement.replaceChildren(notice);
            return;
        }

        if (chartInstances.comparison) {
            chartInstances.comparison.destroy();
        }

        // Take top 10 cities max for readability
        const topCities = cities.slice(0, 10);
        const labels = topCities.map(c => c.city);

        // Show weighted contributions (score * weight/100) so bar heights
        // reflect actual impact on the final score, not raw category scores
        const currentWeights = getCategoryWeights();
        const datasets = CATEGORY_KEYS.map((key, i) => ({
            label: `${CATEGORY_LABELS[i]} (${currentWeights[i]}%)`,
            data: topCities.map(c => {
                const raw = c.scoreBreakdown?.[key] || 0;
                return raw * currentWeights[i] / 100;
            }),
            backgroundColor: CHART_COLORS[i],
            borderWidth: 0,
            borderRadius: 2
        }));

        chartInstances.comparison = new Chart(canvas, {
            type: 'bar',
            data: { labels, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        stacked: true,
                        ticks: {
                            font: { size: 10 },
                            maxRotation: 45
                        }
                    },
                    y: {
                        stacked: true,
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Weighted Score Contribution',
                            font: { size: 11 }
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 10,
                            usePointStyle: true,
                            font: { size: 10 }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const catIndex = context.datasetIndex;
                                const rawScore = context.raw * 100 / (getCategoryWeights()[catIndex] || 1);
                                return `${CATEGORY_LABELS[catIndex]}: ${rawScore.toFixed(0)}/100 (contributes ${context.raw.toFixed(1)} pts)`;
                            }
                        }
                    }
                }
            }
        });
    }

    // Get chart image as base64 PNG (for export)
    function getChartImage(id) {
        var chart = chartInstances[id];
        return chart ? chart.toBase64Image() : null;
    }

    function getChartIds() {
        return Object.keys(chartInstances);
    }

    /**
     * Update the donut chart with current weight values.
     * Called by weight-config.js after slider changes.
     */
    function updateWeightsDonut() {
        if (chartInstances.weightsDonut) {
            chartInstances.weightsDonut.data.datasets[0].data = getCategoryWeights();
            chartInstances.weightsDonut.update();
        }
    }

    // Expose functions globally
    window.TransPlanCharts = {
        renderWeightsDonutChart,
        createRadarChart,
        createComparisonChart,
        updateWeightsDonut: updateWeightsDonut,
        getChartImage: getChartImage,
        getChartIds: getChartIds
    };

    // Render donut chart on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', renderWeightsDonutChart);
    } else {
        renderWeightsDonutChart();
    }
})();
