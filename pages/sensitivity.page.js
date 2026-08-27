/**
 * Extracted from sensitivity.html (#250).
 *
 * Inline <script> blocks force script-src 'unsafe-inline', which removes
 * most of what a Content-Security-Policy is for. Behaviour is unchanged:
 * the file is loaded at the same position the block occupied, so execution
 * order and DOM readiness are the same.
 */
(function () {
        'use strict';

        // ── State ──
        var allCenters = [];
        var tierConfig = null;
        var isRunning = false;

        if (window.TransPlanSeed) TransPlanSeed.inject('sensSeedControl');

        // ── DOM refs ──
        var centerFilter = document.getElementById('centerFilter');
        var centerPicker = document.getElementById('centerPicker');
        var sensIters = document.getElementById('sensIters');
        var sensItersVal = document.getElementById('sensItersVal');
        var sensRunBtn = document.getElementById('sensRunBtn');
        var sensStatus = document.getElementById('sensStatus');
        var sensResults = document.getElementById('sensResults');
        var sensEmpty = document.getElementById('sensEmpty');
        var baselineValue = document.getElementById('baselineValue');
        var baselineSub = document.getElementById('baselineSub');
        var impactBody = document.getElementById('impactBody');
        var sensElapsed = document.getElementById('sensElapsed');
        var sensTierBadge = document.getElementById('sensTierBadge');
        var sensTierCaps = document.getElementById('sensTierCaps');

        // ── Inject patient form ──
        TransPlanPatientForm.inject('patient-form', { compact: true });
        TransPlanPatientForm.populateFromURL();
        if (window.SimTierPanel) SimTierPanel.init();

        // ── Iterations slider ──
        sensIters.addEventListener('input', function () {
            sensItersVal.textContent = this.value;
        });

        // ── Center picker: update on organ change ──
        var organSelect = document.getElementById('pf-organ');
        if (organSelect) {
            organSelect.addEventListener('change', function () {
                loadCentersForOrgan(this.value);
                updateRunBtn();
            });
        }

        function loadCentersForOrgan(organ) {
            if (!organ) {
                clearCenterPicker('Select organ first...');
                allCenters = [];
                centerFilter.value = '';
                return;
            }
            var apiBase = window.TransPlanAPI ? TransPlanAPI.getBaseUrl() : '';
            fetch(apiBase + '/centers?organ=' + encodeURIComponent(organ))
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    allCenters = data.centers || [];
                    renderCenterOptions(allCenters);
                    centerFilter.value = '';
                })
                .catch(function () {
                    clearCenterPicker('Failed to load centers');
                    allCenters = [];
                });
        }

        function clearCenterPicker(text) {
            while (centerPicker.firstChild) centerPicker.removeChild(centerPicker.firstChild);
            var opt = document.createElement('option');
            opt.value = '';
            opt.textContent = text;
            centerPicker.appendChild(opt);
        }

        function renderCenterOptions(centers) {
            while (centerPicker.firstChild) centerPicker.removeChild(centerPicker.firstChild);
            var placeholder = document.createElement('option');
            placeholder.value = '';
            placeholder.textContent = 'Select center...';
            centerPicker.appendChild(placeholder);

            centers.forEach(function (c) {
                var opt = document.createElement('option');
                opt.value = c.code;
                opt.textContent = c.name + ' (' + (c.state_abbr || c.state || '') + ')';
                centerPicker.appendChild(opt);
            });
        }

        // ── Filter-as-you-type ──
        centerFilter.addEventListener('input', function () {
            var q = this.value.toLowerCase().trim();
            if (!q) {
                renderCenterOptions(allCenters);
                return;
            }
            var filtered = allCenters.filter(function (c) {
                var text = (c.name + ' ' + (c.state_abbr || '') + ' ' + (c.state || '') + ' ' + c.code).toLowerCase();
                return text.indexOf(q) !== -1;
            });
            renderCenterOptions(filtered);
        });

        // ── Update run button state ──
        centerPicker.addEventListener('change', updateRunBtn);

        function updateRunBtn() {
            var formData = TransPlanPatientForm.collectFormData();
            var hasRequired = formData.organ && formData.bloodType && formData.age && formData.sex && formData.urgency;
            var hasCenter = centerPicker.value !== '';
            sensRunBtn.disabled = !(hasRequired && hasCenter) || isRunning;
        }

        // Watch all form fields for changes
        document.getElementById('patient-form').addEventListener('change', updateRunBtn);
        document.getElementById('patient-form').addEventListener('input', updateRunBtn);

        // ── Run sensitivity analysis ──
        sensRunBtn.addEventListener('click', runAnalysis);

        async function runAnalysis() {
            if (isRunning) return;

            var formData = TransPlanPatientForm.collectFormData();
            var centerCode = centerPicker.value;
            var iterations = parseInt(sensIters.value, 10);

            if (!formData.organ || !formData.bloodType || !formData.age || !formData.sex || !formData.urgency) {
                setStatus('Please fill in all required patient fields.', true);
                return;
            }
            if (!centerCode) {
                setStatus('Please select a transplant center.', true);
                return;
            }

            isRunning = true;
            sensRunBtn.disabled = true;
            sensRunBtn.textContent = 'Running...';
            setStatus('Running sensitivity analysis (' + iterations + ' iterations)...');

            try {
                var apiBase = window.TransPlanAPI ? TransPlanAPI.getBaseUrl() : '';
                var body = {
                    patient: TransPlanAPI.normalizeFormData(formData),
                    city: getCenterCity(centerCode),
                    center_code: centerCode,
                    iterations: iterations
                };
                // #350: sensitivity IS stochastic (verified: same seed gives
                // identical impacts, no seed gives different ones), so a seed
                // control here is meaningful — unlike equity, which is exact.
                var seed = window.TransPlanSeed
                    ? TransPlanSeed.getSeed('sensSeedControl') : null;
                if (seed !== null) body.seed = seed;

                var response = await fetch(apiBase + '/sensitivity', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body)
                });

                if (!response.ok) {
                    var errText = '';
                    try { var errData = await response.json(); errText = errData.detail || ''; } catch (e) {}
                    throw new Error('API error ' + response.status + (errText ? ': ' + errText : ''));
                }

                var result = await response.json();
                if (window.TransPlanSeed) {
                    TransPlanSeed.setUsedSeed('sensSeedControl', result.seed_used);
                }
                renderResults(result);
                setStatus('');
            } catch (err) {
                setStatus('Analysis failed: ' + err.message, true);
                console.warn('Sensitivity analysis error:', err);
            } finally {
                isRunning = false;
                sensRunBtn.disabled = false;
                sensRunBtn.textContent = 'Run Sensitivity Analysis';
                updateRunBtn();
            }
        }

        function getCenterCity(code) {
            for (var i = 0; i < allCenters.length; i++) {
                if (allCenters[i].code === code) {
                    return allCenters[i].city || allCenters[i].name || code;
                }
            }
            return code;
        }

        // ── Render results ──
        function renderResults(result) {
            sensEmpty.style.display = 'none';
            sensResults.classList.add('visible');

            // Baseline p24
            var baseline = (result.impacts && result.impacts.length > 0)
                ? result.impacts[0].p24_baseline : 0;
            baselineValue.textContent = (baseline * 100).toFixed(1) + '%';
            baselineSub.textContent = result.city + (result.center_code ? ' (' + result.center_code + ')' : '') +
                ' \u00b7 ' + result.iterations + ' iterations';

            // Tornado chart
            TransPlanProbCharts.renderTornadoChart('tornadoChart', result);

            // Impact table
            renderImpactTable(result.impacts || []);

            // Elapsed
            if (result.elapsed_seconds !== undefined) {
                sensElapsed.textContent = 'Completed in ' + result.elapsed_seconds.toFixed(2) + 's';
            }

            // Continue buttons
            var contEl = document.getElementById('sens-continue-buttons');
            if (contEl && window.TransPlanContinue) {
                var formData = TransPlanPatientForm.collectFormData();
                TransPlanContinue.renderContinueButtons(contEl, 'sensitivity', formData);
            }

            sensResults.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }

        function renderImpactTable(impacts) {
            while (impactBody.firstChild) impactBody.removeChild(impactBody.firstChild);

            impacts.forEach(function (imp) {
                var tr = document.createElement('tr');

                // Parameter name
                var tdParam = document.createElement('td');
                tdParam.className = 'impact-param';
                tdParam.textContent = imp.label;
                tr.appendChild(tdParam);

                // Baseline value
                var tdBaseline = document.createElement('td');
                tdBaseline.textContent = formatParamValue(imp.baseline_value);
                tr.appendChild(tdBaseline);

                // Low value
                var tdLow = document.createElement('td');
                tdLow.textContent = formatParamValue(imp.low_value);
                tr.appendChild(tdLow);

                // P24 at low
                var tdP24Low = document.createElement('td');
                tdP24Low.textContent = pct(imp.p24_at_low);
                tr.appendChild(tdP24Low);

                // High value
                var tdHigh = document.createElement('td');
                tdHigh.textContent = formatParamValue(imp.high_value);
                tr.appendChild(tdHigh);

                // P24 at high
                var tdP24High = document.createElement('td');
                tdP24High.textContent = pct(imp.p24_at_high);
                tr.appendChild(tdP24High);

                // Impact (absolute delta)
                var delta = Math.abs(imp.p24_at_high - imp.p24_at_low);
                var tdDelta = document.createElement('td');
                tdDelta.className = 'impact-delta';
                tdDelta.textContent = '\u00b1' + pct(delta / 2);

                if (delta > 0.15) {
                    tdDelta.classList.add('negative');
                } else if (delta > 0.06) {
                    tdDelta.classList.add('positive');
                }
                tr.appendChild(tdDelta);

                impactBody.appendChild(tr);
            });
        }

        function formatParamValue(val) {
            if (val === null || val === undefined) return '--';
            if (Number.isInteger(val)) return String(val);
            return val.toFixed(2);
        }

        function pct(val) {
            return (val * 100).toFixed(1) + '%';
        }

        function setStatus(msg, isError) {
            sensStatus.textContent = msg;
            sensStatus.className = 'sens-status' + (isError ? ' error' : '');
        }

        // ── Tier config ──
        function loadTierConfig() {
            var apiBase = window.TransPlanAPI ? TransPlanAPI.getBaseUrl() : '';
            fetch(apiBase + '/tier')
                .then(function (r) { return r.ok ? r.json() : null; })
                .then(function (data) {
                    if (!data) throw new Error('/tier returned no config');
                    tierConfig = data;
                    applyTierCaps();
                })
                .catch(function () {
                    // #350: a local copy of the tier caps drifts from
                    // backend/tier_config.py with nothing to catch it (the
                    // equity page's copy had gone stale by 8x). Caps are
                    // enforced server-side, so when /tier is unreachable the
                    // honest thing is to leave the authored control ranges
                    // alone rather than invent a limit.
                    tierConfig = null;
                    sensTierBadge.textContent = 'Tier unknown';
                    sensTierBadge.className = 'tier-badge';
                    sensTierBadge.title = 'Could not reach /tier — limits ' +
                        'still apply server-side.';
                });
        }

        function applyTierCaps() {
            if (!tierConfig) return;
            var caps = tierConfig.caps || {};

            // Badge
            sensTierBadge.textContent = tierConfig.name === 'local' ? 'Local' : 'Web';
            sensTierBadge.className = 'tier-badge tier-' + tierConfig.name;

            // Cap iterations slider
            var maxIter = caps.max_sensitivity_iterations || 500;
            sensIters.max = maxIter;
            if (parseInt(sensIters.value, 10) > maxIter) {
                sensIters.value = maxIter;
                sensItersVal.textContent = String(maxIter);
            }

            sensTierCaps.textContent = 'Max ' + maxIter + ' iterations';
        }

        // ── Init ──
        loadTierConfig();
        updateRunBtn();
    })();
