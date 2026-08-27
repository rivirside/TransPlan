/**
 * Extracted from equity.html (#250).
 *
 * Inline <script> blocks force script-src 'unsafe-inline', which removes
 * most of what a Content-Security-Policy is for. Behaviour is unchanged:
 * the file is loaded at the same position the block occupied, so execution
 * order and DOM readiness are the same.
 */
(function () {
        'use strict';

        // ── Inject patient form ──
        TransPlanPatientForm.inject('patient-form-container', { compact: true, showCopula: false, showCOD: false });
        TransPlanPatientForm.populateFromURL();
        if (window.SimTierPanel) SimTierPanel.init();

        // ── DOM refs ──
        var maxCentersSlider = document.getElementById('equityMaxCenters');
        var maxCentersVal = document.getElementById('equityMaxCentersVal');
        var runBtn = document.getElementById('eqRunBtn');
        var emptyState = document.getElementById('eqEmptyState');
        var loadingEl = document.getElementById('eqLoading');
        var errorEl = document.getElementById('eqError');
        var resultsEl = document.getElementById('eqResults');

        // ── Slider value displays ──
        maxCentersSlider.addEventListener('input', function () { maxCentersVal.textContent = this.value; });

        // ── Tier config ──
        var _tierConfig = null;

        function fetchTierConfig() {
            var apiBase = window.TransPlanAPI ? window.TransPlanAPI.getBaseUrl() : '';
            return fetch(apiBase + '/tier')
                .then(function (r) { return r.ok ? r.json() : null; })
                .then(function (data) {
                    if (!data) throw new Error('/tier returned no config');
                    _tierConfig = data;
                    _applyTierCaps();
                })
                .catch(function () {
                    // #350: this used to fall back to a hardcoded
                    // max_equity_centers of 30 while the web tier's real cap
                    // is 248, so a slow or failed /tier silently capped the
                    // analysis at an eighth of the centers and presented the
                    // truncated result as complete. Caps are enforced
                    // server-side regardless, so the honest client behaviour
                    // when the tier is unknown is to leave the authored
                    // control ranges alone and say the tier is unknown.
                    _tierConfig = null;
                    var badge = document.getElementById('eqTierBadge');
                    if (badge) {
                        badge.textContent = 'Tier unknown';
                        badge.className = 'tier-badge';
                        badge.title = 'Could not reach /tier — limits still ' +
                            'apply server-side.';
                    }
                });
        }

        function _applyTierCaps() {
            if (!_tierConfig) return;
            var caps = _tierConfig.caps;
            var badge = document.getElementById('eqTierBadge');
            if (badge) {
                badge.textContent = _tierConfig.name === 'local' ? 'Local' : 'Web';
                badge.className = 'tier-badge tier-' + _tierConfig.name;
            }
            _capSlider('equityMaxCenters', 'equityMaxCentersVal', caps.max_equity_centers);
        }

        function _capSlider(sliderId, valueId, maxVal) {
            var slider = document.getElementById(sliderId);
            if (!slider) return;
            slider.max = maxVal;
            if (parseInt(slider.value) > maxVal) slider.value = maxVal;
            var valueEl = document.getElementById(valueId);
            if (valueEl) valueEl.textContent = slider.value;
        }

        // ── Form validation — enable run button when required fields filled ──
        function checkFormReady() {
            var formData = TransPlanPatientForm.collectFormData();
            var ready = formData.organ && formData.bloodType && formData.age && formData.sex && formData.urgency;
            runBtn.disabled = !ready;
        }

        // Listen for changes in the patient form container
        var formContainer = document.getElementById('patient-form-container');
        formContainer.addEventListener('change', checkFormReady);
        formContainer.addEventListener('input', checkFormReady);
        // populateFromURL() runs above, BEFORE these listeners exist, so a
        // profile arriving by link never triggered them and the run button
        // stayed disabled on a fully populated form. Evaluate readiness once
        // now that the handler is wired.
        checkFormReady();

        // ── Sorting state ──
        var _sortCol = 'gini';
        var _sortAsc = true;
        var _tableData = [];

        // ── Run analysis ──
        runBtn.addEventListener('click', function () {
            runAnalysis();
        });

        // ── Bias audit (#254 endpoint, previously unreachable from the UI) ──
        var eqBiasBtn = document.getElementById('eqBiasBtn');
        if (eqBiasBtn) eqBiasBtn.addEventListener('click', runBiasAudit);

        function _num(v, digits) {
            return (typeof v === 'number' && isFinite(v)) ? v.toFixed(digits) : '—';
        }

        async function runBiasAudit() {
            var statusEl = document.getElementById('eqBiasStatus');
            var wrap = document.getElementById('eqBiasWrap');
            var body = document.getElementById('eqBiasBody');
            var formData = TransPlanPatientForm.collectFormData();

            if (!formData.organ || !formData.bloodType || !formData.age) {
                statusEl.textContent = 'Fill in the patient profile first.';
                return;
            }

            eqBiasBtn.disabled = true;
            statusEl.textContent = 'Running…';
            wrap.style.display = 'none';

            var result = null;
            try {
                result = await TransPlanAPI.biasAudit(
                    formData, parseInt(maxCentersSlider.value, 10));
            } catch (err) {
                // Without this the button stayed disabled and the status stuck
                // on "Running…" forever, which reads as a hang rather than a
                // failure.
                console.error('bias audit threw:', err);
            }

            eqBiasBtn.disabled = false;
            if (!result || !result.city_profiles) {
                statusEl.textContent = 'Bias audit failed — the backend may be unavailable.';
                return;
            }

            // Most-disparate centers first: that is what the panel is for.
            var profiles = result.city_profiles.slice().sort(function (a, b) {
                return (b.overall_disparity_ratio || 0) - (a.overall_disparity_ratio || 0);
            });

            while (body.firstChild) body.removeChild(body.firstChild);
            var dims = [
                ['Blood type', 'blood_type_disparity'],
                ['Age', 'age_disparity'],
                ['Sex', 'sex_disparity']
            ];
            profiles.forEach(function (p) {
                dims.forEach(function (pair, i) {
                    var d = p[pair[1]];
                    if (!d) return;
                    var tr = document.createElement('tr');
                    // Only label the center on its first row so the grouping reads.
                    var cells = [
                        i === 0 ? (p.city || p.center_name || p.center_code || '') : '',
                        pair[0],
                        (d.max_group || '') + ' (' + _num(d.max_p24, 3) + ')',
                        (d.min_group || '') + ' (' + _num(d.min_p24, 3) + ')',
                        _num(d.disparity_ratio, 3),
                        _num(d.absolute_gap, 3),
                        _num(d.cohens_d, 2)
                    ];
                    cells.forEach(function (text) {
                        var td = document.createElement('td');
                        td.textContent = text;
                        tr.appendChild(td);
                    });
                    body.appendChild(tr);
                });
            });

            statusEl.textContent = result.n_cities + ' centers × ' +
                result.n_profiles + ' demographic profiles. Ordered by overall ' +
                'disparity ratio, widest first.';
            wrap.style.display = '';
        }

        async function runAnalysis() {
            var formData = TransPlanPatientForm.collectFormData();
            var maxCenters = parseInt(maxCentersSlider.value);

            // Show loading, hide others
            emptyState.style.display = 'none';
            errorEl.className = 'eq-error';
            resultsEl.className = 'eq-results';
            loadingEl.className = 'eq-loading active';
            runBtn.disabled = true;

            try {
                var result = await TransPlanAPI.equityAnalysis(
                    formData, null, maxCenters);

                loadingEl.className = 'eq-loading';

                if (!result) {
                    errorEl.textContent = 'Analysis failed. The backend may be unavailable or timed out. Please try again with fewer iterations.';
                    errorEl.className = 'eq-error active';
                    runBtn.disabled = false;
                    return;
                }

                renderResults(result);
                resultsEl.className = 'eq-results active';

                // Continue buttons
                var contEl = document.getElementById('eq-continue-buttons');
                if (contEl && window.TransPlanContinue) {
                    var formData = TransPlanPatientForm.collectFormData();
                    TransPlanContinue.renderContinueButtons(contEl, 'equity', formData);
                }
            } catch (err) {
                loadingEl.className = 'eq-loading';
                errorEl.textContent = 'Unexpected error: ' + (err.message || 'Unknown');
                errorEl.className = 'eq-error active';
            }

            runBtn.disabled = false;
        }

        // ── Render results ──
        function renderResults(result) {
            // Summary cards
            document.getElementById('eqOverallGini').textContent = result.overall_gini !== undefined
                ? result.overall_gini.toFixed(4)
                : '--';
            document.getElementById('eqProfileCount').textContent = result.profiles_simulated || '--';
            document.getElementById('eqElapsed').textContent = result.elapsed_seconds !== undefined
                ? result.elapsed_seconds.toFixed(1)
                : '--';

            // Meta line
            var meta = document.getElementById('eqResultsMeta');
            meta.textContent = (result.organ ? result.organ.charAt(0).toUpperCase() + result.organ.slice(1) : 'Unknown organ')
                + ' | ' + (result.cities ? result.cities.length : 0) + ' centers analyzed';

            // Charts — use first city's dimension data for blood type & age charts
            var cities = result.cities || [];
            if (cities.length > 0 && cities[0].dimension_disparities) {
                var dims = cities[0].dimension_disparities;
                TransPlanEquityCharts.renderBloodTypeDisparityChart('bloodTypeChart', dims.blood_type);
                TransPlanEquityCharts.renderAgeDisparityChart('ageChart', dims.age_bracket);
            }
            TransPlanEquityCharts.renderGiniByCity('giniChart', cities);

            // Table data
            _tableData = cities.map(function (c) {
                return {
                    city: c.city || '',
                    state: c.state || '',
                    gini: c.gini_coefficient,
                    p24_lo: c.p24_range ? c.p24_range[0] : 0,
                    p24_hi: c.p24_range ? c.p24_range[1] : 0,
                    wait_lo: c.median_wait_range ? c.median_wait_range[0] : 0,
                    wait_hi: c.median_wait_range ? c.median_wait_range[1] : 0
                };
            });
            _sortCol = 'gini';
            _sortAsc = true;
            renderTable();

            // Disclaimers
            var disclaimerDiv = document.getElementById('eqDisclaimers');
            while (disclaimerDiv.firstChild) disclaimerDiv.removeChild(disclaimerDiv.firstChild);
            if (result.disclaimers && result.disclaimers.length) {
                result.disclaimers.forEach(function (d) {
                    var p = document.createElement('p');
                    p.textContent = d;
                    disclaimerDiv.appendChild(p);
                });
            }
        }

        // ── Sortable table ──
        function renderTable() {
            var sorted = _tableData.slice().sort(function (a, b) {
                var aVal = a[_sortCol];
                var bVal = b[_sortCol];
                if (typeof aVal === 'string') {
                    aVal = aVal.toLowerCase();
                    bVal = (bVal || '').toLowerCase();
                }
                if (aVal < bVal) return _sortAsc ? -1 : 1;
                if (aVal > bVal) return _sortAsc ? 1 : -1;
                return 0;
            });

            var tbody = document.getElementById('eqTableBody');
            while (tbody.firstChild) tbody.removeChild(tbody.firstChild);

            sorted.forEach(function (row) {
                var tr = document.createElement('tr');

                var tdCity = document.createElement('td');
                tdCity.textContent = row.city;
                tr.appendChild(tdCity);

                var tdState = document.createElement('td');
                tdState.textContent = row.state;
                tr.appendChild(tdState);

                var tdGini = document.createElement('td');
                var dot = document.createElement('span');
                dot.className = 'gini-dot ' + _giniDotClass(row.gini);
                tdGini.appendChild(dot);
                tdGini.appendChild(document.createTextNode(row.gini !== undefined ? row.gini.toFixed(4) : '--'));
                tr.appendChild(tdGini);

                var tdP24 = document.createElement('td');
                tdP24.textContent = (row.p24_lo * 100).toFixed(1) + '% - ' + (row.p24_hi * 100).toFixed(1) + '%';
                tr.appendChild(tdP24);

                var tdWait = document.createElement('td');
                tdWait.textContent = row.wait_lo.toFixed(1) + ' - ' + row.wait_hi.toFixed(1) + ' mo';
                tr.appendChild(tdWait);

                tbody.appendChild(tr);
            });

            // Update header sort arrows
            var ths = document.querySelectorAll('#eqTable th');
            ths.forEach(function (th) {
                var col = th.getAttribute('data-col');
                var arrow = th.querySelector('.sort-arrow');
                if (col === _sortCol) {
                    th.classList.add('sorted');
                    arrow.textContent = _sortAsc ? '\u25B2' : '\u25BC';
                } else {
                    th.classList.remove('sorted');
                    arrow.textContent = '\u25B2';
                }
            });
        }

        function _giniDotClass(g) {
            if (g < 0.15) return 'gini-green';
            if (g < 0.30) return 'gini-yellow';
            return 'gini-red';
        }

        // Table header click for sorting
        document.getElementById('eqTable').addEventListener('click', function (e) {
            var th = e.target.closest('th[data-col]');
            if (!th) return;
            var col = th.getAttribute('data-col');
            if (col === _sortCol) {
                _sortAsc = !_sortAsc;
            } else {
                _sortCol = col;
                _sortAsc = true;
            }
            renderTable();
        });

        // ── Init ──
        fetchTierConfig();

        // Dark mode hook for equity charts
        if (window.TransPlanEquityCharts && window.TransPlanEquityCharts.onDarkModeChange) {
            var observer = new MutationObserver(function () {
                var isDark = document.documentElement.getAttribute('data-dark') === 'true';
                TransPlanEquityCharts.onDarkModeChange(isDark);
            });
            observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-dark'] });
        }
    })();
