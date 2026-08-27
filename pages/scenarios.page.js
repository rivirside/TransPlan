/**
 * Extracted from scenarios.html (#250).
 *
 * Inline <script> blocks force script-src 'unsafe-inline', which removes
 * most of what a Content-Security-Policy is for. Behaviour is unchanged:
 * the file is loaded at the same position the block occupied, so execution
 * order and DOM readiness are the same.
 */
(function () {
        'use strict';

        // ── State ──
        var currentTab = 'whatif';
        var centersCache = {};
        var policyScenariosCache = {};
        var tierCaps = { max_whatif_iterations: 500 };
        var sortCol = null;
        var sortAsc = true;

        // ── DOM refs ──
        var centerSelect = document.getElementById('centerSelect');
        var centerHint = document.getElementById('centerHint');
        var donorMultSlider = document.getElementById('donorMultSlider');
        var donorMultVal = document.getElementById('donorMultVal');
        var waitMultSlider = document.getElementById('waitMultSlider');
        var waitMultVal = document.getElementById('waitMultVal');
        var whatifIterSlider = document.getElementById('whatifIterSlider');
        var whatifIterVal = document.getElementById('whatifIterVal');
        var policySelect = document.getElementById('policySelect');
        var policyDesc = document.getElementById('policyDesc');
        var policyIterSlider = document.getElementById('policyIterSlider');
        var policyIterVal = document.getElementById('policyIterVal');
        var subsidyIterSlider = document.getElementById('subsidyIterSlider');
        var subsidyIterVal = document.getElementById('subsidyIterVal');
        var runWhatIfBtn = document.getElementById('runWhatIf');
        var runPolicyBtn = document.getElementById('runPolicy');
        var runSubsidyBtn = document.getElementById('runSubsidy');
        var resultsArea = document.getElementById('resultsArea');

        // ── Init: inject patient form ──
        if (window.TransPlanPatientForm) {
            TransPlanPatientForm.inject('patient-form', { compact: true });
            TransPlanPatientForm.populateFromURL();
        }
        if (window.SimTierPanel) SimTierPanel.init();

        // ── Fetch tier config ──
        function fetchTierConfig() {
            var apiBase = window.TransPlanAPI ? window.TransPlanAPI.getBaseUrl() : '';
            fetch(apiBase + '/tier')
                .then(function (r) { return r.ok ? r.json() : null; })
                .then(function (data) {
                    if (data && data.caps) {
                        tierCaps = data.caps;
                    }
                    applyIterCaps();
                })
                .catch(function () { applyIterCaps(); });
        }

        function applyIterCaps() {
            var maxIter = tierCaps.max_whatif_iterations || 500;
            [whatifIterSlider, policyIterSlider, subsidyIterSlider].forEach(function (slider) {
                if (!slider) return;
                if (parseInt(slider.max, 10) > maxIter) slider.max = maxIter;
                if (parseInt(slider.value, 10) > maxIter) {
                    slider.value = maxIter;
                    var valEl = document.getElementById(slider.id.replace('Slider', 'Val'));
                    if (valEl) valEl.textContent = maxIter;
                }
            });
        }

        fetchTierConfig();

        // ── Slider value displays ──
        donorMultSlider.addEventListener('input', function () {
            donorMultVal.textContent = parseFloat(this.value).toFixed(1) + 'x';
        });
        waitMultSlider.addEventListener('input', function () {
            waitMultVal.textContent = parseFloat(this.value).toFixed(1) + 'x';
        });
        whatifIterSlider.addEventListener('input', function () {
            whatifIterVal.textContent = this.value;
        });
        policyIterSlider.addEventListener('input', function () {
            policyIterVal.textContent = this.value;
        });
        subsidyIterSlider.addEventListener('input', function () {
            subsidyIterVal.textContent = this.value;
        });

        // ── Tab switching ──
        document.querySelectorAll('.scenario-tab').forEach(function (btn) {
            btn.addEventListener('click', function () {
                document.querySelectorAll('.scenario-tab').forEach(function (t) { t.classList.remove('active'); });
                document.querySelectorAll('.scenario-panel').forEach(function (p) { p.classList.remove('active'); });
                btn.classList.add('active');
                var tab = btn.getAttribute('data-tab');
                currentTab = tab;
                var panel = document.getElementById('panel-' + tab);
                if (panel) panel.classList.add('active');
                updateRunButtons();
            });
        });

        // ── Organ change: load centers + policy scenarios ──
        function getOrgan() {
            var el = document.getElementById('pf-organ');
            return el ? el.value : '';
        }

        function watchOrganChange() {
            var organEl = document.getElementById('pf-organ');
            if (!organEl) return;
            organEl.addEventListener('change', function () {
                var organ = this.value;
                if (organ) {
                    loadCenters(organ);
                    loadPolicyScenarios(organ);
                } else {
                    centerSelect.textContent = '';
                    var defaultOpt = document.createElement('option');
                    defaultOpt.value = '';
                    defaultOpt.textContent = 'Select organ first...';
                    centerSelect.appendChild(defaultOpt);
                    centerSelect.disabled = true;
                    centerHint.textContent = 'Select an organ above to load centers';
                    policySelect.textContent = '';
                    var defaultPOpt = document.createElement('option');
                    defaultPOpt.value = '';
                    defaultPOpt.textContent = 'Select organ first...';
                    policySelect.appendChild(defaultPOpt);
                    policySelect.disabled = true;
                    policyDesc.textContent = '';
                }
                updateRunButtons();
            });
        }
        watchOrganChange();

        function loadCenters(organ) {
            if (centersCache[organ]) {
                populateCenters(centersCache[organ]);
                return;
            }
            centerSelect.textContent = '';
            var loadingOpt = document.createElement('option');
            loadingOpt.value = '';
            loadingOpt.textContent = 'Loading centers...';
            centerSelect.appendChild(loadingOpt);
            centerSelect.disabled = true;
            centerHint.textContent = 'Loading...';

            if (window.TransPlanAPI && window.TransPlanAPI.fetchCenters) {
                TransPlanAPI.fetchCenters({ organ: organ }).then(function (data) {
                    if (data && data.centers) {
                        centersCache[organ] = data.centers;
                        populateCenters(data.centers);
                    } else {
                        centerSelect.textContent = '';
                        var errOpt = document.createElement('option');
                        errOpt.value = '';
                        errOpt.textContent = 'No centers found';
                        centerSelect.appendChild(errOpt);
                        centerHint.textContent = 'Could not load centers';
                    }
                }).catch(function () {
                    centerSelect.textContent = '';
                    var errOpt = document.createElement('option');
                    errOpt.value = '';
                    errOpt.textContent = 'Error loading centers';
                    centerSelect.appendChild(errOpt);
                    centerHint.textContent = 'Backend may be unavailable';
                });
            }
        }

        function populateCenters(centers) {
            centerSelect.textContent = '';
            var placeholder = document.createElement('option');
            placeholder.value = '';
            placeholder.textContent = 'Choose a center...';
            centerSelect.appendChild(placeholder);
            centers.forEach(function (c) {
                var opt = document.createElement('option');
                // Value is the SRTR center code — /what-if and /policy-scenario
                // validate codes, not display names (#286).
                opt.value = c.code || c.city || c.name;
                var label = c.name || c.city || c.code;
                var st = c.state_abbr || c.state || '';
                opt.textContent = st ? (label + ', ' + st) : label;
                opt.setAttribute('data-label', label);
                centerSelect.appendChild(opt);
            });
            centerSelect.disabled = false;
            centerHint.textContent = centers.length + ' centers available';
            centerSelect.addEventListener('change', updateRunButtons);
            updateRunButtons();
        }

        function loadPolicyScenarios(organ) {
            if (policyScenariosCache[organ]) {
                populatePolicyScenarios(policyScenariosCache[organ]);
                return;
            }
            policySelect.textContent = '';
            var loadingOpt = document.createElement('option');
            loadingOpt.value = '';
            loadingOpt.textContent = 'Loading scenarios...';
            policySelect.appendChild(loadingOpt);
            policySelect.disabled = true;

            if (window.TransPlanAPI && window.TransPlanAPI.policyScenarios) {
                TransPlanAPI.policyScenarios(organ).then(function (scenarios) {
                    if (scenarios && scenarios.length > 0) {
                        policyScenariosCache[organ] = scenarios;
                        populatePolicyScenarios(scenarios);
                    } else {
                        policySelect.textContent = '';
                        var errOpt = document.createElement('option');
                        errOpt.value = '';
                        errOpt.textContent = 'No scenarios available';
                        policySelect.appendChild(errOpt);
                        policySelect.disabled = true;
                    }
                }).catch(function () {
                    policySelect.textContent = '';
                    var errOpt = document.createElement('option');
                    errOpt.value = '';
                    errOpt.textContent = 'Error loading scenarios';
                    policySelect.appendChild(errOpt);
                    policySelect.disabled = true;
                });
            }
        }

        function populatePolicyScenarios(scenarios) {
            policySelect.textContent = '';
            var placeholder = document.createElement('option');
            placeholder.value = '';
            placeholder.textContent = 'Choose a scenario...';
            policySelect.appendChild(placeholder);
            scenarios.forEach(function (s) {
                var opt = document.createElement('option');
                opt.value = s.id;
                opt.textContent = s.name;
                opt.setAttribute('data-desc', s.description || '');
                policySelect.appendChild(opt);
            });
            policySelect.disabled = false;

            policySelect.addEventListener('change', function () {
                var selected = policySelect.options[policySelect.selectedIndex];
                var desc = selected ? selected.getAttribute('data-desc') : '';
                policyDesc.textContent = desc || '';
                updateRunButtons();
            });
        }

        // ── Validate & enable run buttons ──
        function isFormValid() {
            var organ = getOrgan();
            var age = document.getElementById('pf-age');
            var sex = document.getElementById('pf-sex');
            var blood = document.getElementById('pf-bloodType');
            var urgency = document.getElementById('pf-urgency');
            return organ && age && age.value && sex && sex.value && blood && blood.value && urgency && urgency.value;
        }

        function updateRunButtons() {
            var valid = isFormValid();
            var hasCenter = centerSelect.value !== '';
            var hasScenario = policySelect.value !== '';

            runWhatIfBtn.disabled = !(valid && hasCenter);
            runPolicyBtn.disabled = !(valid && hasCenter && hasScenario);
            runSubsidyBtn.disabled = !valid;
        }

        // Watch form changes for button state
        document.addEventListener('change', function (e) {
            if (e.target.closest('#patient-form') || e.target.id === 'centerSelect' || e.target.id === 'policySelect') {
                updateRunButtons();
            }
        });
        document.addEventListener('input', function (e) {
            if (e.target.closest('#patient-form')) {
                updateRunButtons();
            }
        });

        // ── Utility: safe text node builder ──
        function escText(str) {
            return String(str);
        }

        function setText(el, text) {
            el.textContent = text;
        }

        function fmtPct(v) {
            return (v * 100).toFixed(1) + '%';
        }

        function fmtDelta(v) {
            var sign = v >= 0 ? '+' : '';
            return sign + (v * 100).toFixed(1) + ' pp';
        }

        function fmtDeltaPct(baseline, adjusted) {
            if (!baseline || baseline === 0) return '';
            var pct = ((adjusted - baseline) / baseline) * 100;
            var sign = pct >= 0 ? '+' : '';
            return sign + pct.toFixed(1) + '%';
        }

        function fmtWait(months) {
            return months.toFixed(1) + ' mo';
        }

        function fmtCI(ci) {
            if (!ci || ci.length < 2) return '';
            return '[' + fmtPct(ci[0]) + ', ' + fmtPct(ci[1]) + ']';
        }

        // ── DOM builder helpers ──
        function el(tag, className, textContent) {
            var node = document.createElement(tag);
            if (className) node.className = className;
            if (textContent !== undefined) node.textContent = textContent;
            return node;
        }

        function showLoading(msg) {
            resultsArea.textContent = '';
            var wrap = el('div', 'results-loading');
            var spinner = el('div', 'spinner');
            wrap.appendChild(spinner);
            var label = el('div', '', msg || 'Running analysis...');
            wrap.appendChild(label);
            resultsArea.appendChild(wrap);
        }

        function showError(msg) {
            resultsArea.textContent = '';
            var errDiv = el('div', 'results-error', msg);
            resultsArea.appendChild(errDiv);
        }

        // ── Run What-If ──
        function selectedCenter() {
            var opt = centerSelect.options[centerSelect.selectedIndex];
            return {
                code: centerSelect.value,
                label: (opt && opt.getAttribute('data-label')) || centerSelect.value
            };
        }

        runWhatIfBtn.addEventListener('click', function () {
            if (!isFormValid() || !centerSelect.value) return;
            var formData = TransPlanPatientForm.collectFormData('pf');
            var center = selectedCenter();
            var donorMult = parseFloat(donorMultSlider.value);
            var waitMult = parseFloat(waitMultSlider.value);
            var iters = parseInt(whatifIterSlider.value, 10);

            showLoading('Running what-if analysis...');
            runWhatIfBtn.disabled = true;

            TransPlanAPI.whatIf(formData, center, donorMult, waitMult, iters)
                .then(function (result) {
                    runWhatIfBtn.disabled = false;
                    updateRunButtons();
                    if (!result) {
                        showError('What-if analysis failed. The backend may be unavailable.');
                        return;
                    }
                    renderWhatIfResult(result);
                })
                .catch(function (err) {
                    runWhatIfBtn.disabled = false;
                    updateRunButtons();
                    showError('What-if analysis failed: ' + (err.message || 'Unknown error'));
                });
        });

        // ── Run Policy Scenario ──
        runPolicyBtn.addEventListener('click', function () {
            if (!isFormValid() || !centerSelect.value || !policySelect.value) return;
            var formData = TransPlanPatientForm.collectFormData('pf');
            var scenarioId = policySelect.value;
            var center = selectedCenter();
            var iters = parseInt(policyIterSlider.value, 10);

            showLoading('Running policy scenario analysis...');
            runPolicyBtn.disabled = true;

            TransPlanAPI.policyScenario(formData, scenarioId, center, iters)
                .then(function (result) {
                    runPolicyBtn.disabled = false;
                    updateRunButtons();
                    if (!result) {
                        showError('Policy scenario analysis failed. The backend may be unavailable.');
                        return;
                    }
                    renderPolicyResult(result);
                })
                .catch(function (err) {
                    runPolicyBtn.disabled = false;
                    updateRunButtons();
                    showError('Policy scenario analysis failed: ' + (err.message || 'Unknown error'));
                });
        });

        // ── Run Travel Subsidy ──
        runSubsidyBtn.addEventListener('click', function () {
            if (!isFormValid()) return;
            var formData = TransPlanPatientForm.collectFormData('pf');
            var iters = parseInt(subsidyIterSlider.value, 10);

            showLoading('Running travel subsidy analysis across all cities (this may take a moment)...');
            runSubsidyBtn.disabled = true;

            TransPlanAPI.travelSubsidyAnalysis(formData, [], iters)
                .then(function (result) {
                    runSubsidyBtn.disabled = false;
                    updateRunButtons();
                    if (!result) {
                        showError('Travel subsidy analysis failed. The backend may be unavailable.');
                        return;
                    }
                    renderSubsidyResult(result);
                })
                .catch(function (err) {
                    runSubsidyBtn.disabled = false;
                    updateRunButtons();
                    showError('Travel subsidy analysis failed: ' + (err.message || 'Unknown error'));
                });
        });

        // ── Build comparison card DOM ──
        function buildComparisonCard(title, p24, ci, medianWait) {
            var card = el('div', 'comparison-card');
            card.appendChild(el('h4', '', title));

            var row1 = el('div', 'stat-row');
            row1.appendChild(el('span', 'stat-label', 'P(24 mo)'));
            row1.appendChild(el('span', 'stat-value', fmtPct(p24)));
            card.appendChild(row1);

            var row2 = el('div', 'stat-row');
            row2.appendChild(el('span', 'stat-label', '95% CI'));
            row2.appendChild(el('span', 'stat-ci', fmtCI(ci)));
            card.appendChild(row2);

            var row3 = el('div', 'stat-row');
            row3.appendChild(el('span', 'stat-label', 'Median Wait'));
            row3.appendChild(el('span', 'stat-value', fmtWait(medianWait)));
            card.appendChild(row3);

            return card;
        }

        // ── Build bar chart DOM ──
        function buildBarChart(baseP24, adjP24, baseWait, adjWait) {
            var maxP = Math.max(baseP24, adjP24, 0.01);
            var maxW = Math.max(baseWait, adjWait, 1);
            var chart = el('div', 'bar-chart');

            function addBarGroup(value, maxVal, cssClass, valueText, labelText) {
                var group = el('div', 'bar-group');
                var wrapper = el('div', 'bar-wrapper');
                var bar = el('div', 'bar ' + cssClass);
                bar.style.height = Math.round((value / maxVal) * 140) + 'px';
                wrapper.appendChild(bar);
                group.appendChild(wrapper);
                group.appendChild(el('div', 'bar-value', valueText));
                group.appendChild(el('div', 'bar-label', labelText));
                return group;
            }

            chart.appendChild(addBarGroup(baseP24, maxP, 'baseline', fmtPct(baseP24), 'Baseline P24'));
            chart.appendChild(addBarGroup(adjP24, maxP, 'adjusted', fmtPct(adjP24), 'Adjusted P24'));
            chart.appendChild(addBarGroup(baseWait, maxW, 'baseline', fmtWait(baseWait), 'Baseline Wait'));
            chart.appendChild(addBarGroup(adjWait, maxW, 'adjusted', fmtWait(adjWait), 'Adjusted Wait'));

            return chart;
        }

        // ── Build delta card DOM ──
        function buildDeltaCard(deltaP24, baselineP24, adjustedP24) {
            var isPositive = deltaP24 >= 0;
            var card = el('div', 'delta-card ' + (isPositive ? 'positive' : 'negative'));

            card.appendChild(el('div', 'delta-value', fmtDelta(deltaP24)));
            card.appendChild(el('div', 'delta-label', 'Change in P(transplant within 24 months)'));
            card.appendChild(el('div', 'delta-pct', fmtDeltaPct(baselineP24, adjustedP24) + ' relative change'));

            return card;
        }

        // ── Render What-If result ──
        function renderWhatIfResult(r) {
            resultsArea.textContent = '';

            resultsArea.appendChild(el('h2', 'results-title', 'What-If Analysis: ' + r.city + ', ' + r.state));
            resultsArea.appendChild(el('div', 'results-subtitle', 'Donor rate ' + parseFloat(r.donor_rate_multiplier).toFixed(1) + 'x, Wait time ' + parseFloat(r.wait_time_multiplier).toFixed(1) + 'x'));

            resultsArea.appendChild(buildDeltaCard(r.delta_p24, r.baseline_p24, r.adjusted_p24));

            var grid = el('div', 'comparison-grid');
            grid.appendChild(buildComparisonCard('Baseline', r.baseline_p24, r.baseline_ci_95, r.baseline_median_wait));
            grid.appendChild(buildComparisonCard('Adjusted', r.adjusted_p24, r.adjusted_ci_95, r.adjusted_median_wait));
            resultsArea.appendChild(grid);

            resultsArea.appendChild(buildBarChart(r.baseline_p24, r.adjusted_p24, r.baseline_median_wait, r.adjusted_median_wait));

            resultsArea.appendChild(el('div', 'results-meta', r.iterations + ' iterations, ' + r.elapsed_seconds.toFixed(2) + 's'));

            // Continue buttons
            var contEl = document.getElementById('scen-continue-buttons');
            if (contEl && window.TransPlanContinue) {
                var fd = TransPlanPatientForm.collectFormData('pf');
                TransPlanContinue.renderContinueButtons(contEl, 'scenarios', fd);
            }
        }

        // ── Render Policy Scenario result ──
        function renderPolicyResult(r) {
            resultsArea.textContent = '';

            resultsArea.appendChild(el('h2', 'results-title', 'Policy Scenario: ' + r.city + ', ' + r.state));

            if (r.scenario) {
                var infoCard = el('div', 'scenario-info-card');
                infoCard.appendChild(el('h3', '', r.scenario.name || ''));
                infoCard.appendChild(el('p', '', r.scenario.description || ''));
                var mults = el('div', 'multipliers');
                mults.appendChild(el('span', '', 'Donor rate: ' + parseFloat(r.donor_rate_multiplier).toFixed(2) + 'x'));
                mults.appendChild(el('span', '', 'Wait time: ' + parseFloat(r.wait_time_multiplier).toFixed(2) + 'x'));
                infoCard.appendChild(mults);
                resultsArea.appendChild(infoCard);
            }

            resultsArea.appendChild(buildDeltaCard(r.delta_p24, r.baseline_p24, r.adjusted_p24));

            var grid = el('div', 'comparison-grid');
            grid.appendChild(buildComparisonCard('Baseline', r.baseline_p24, r.baseline_ci_95, r.baseline_median_wait));
            grid.appendChild(buildComparisonCard('With Policy', r.adjusted_p24, r.adjusted_ci_95, r.adjusted_median_wait));
            resultsArea.appendChild(grid);

            resultsArea.appendChild(buildBarChart(r.baseline_p24, r.adjusted_p24, r.baseline_median_wait, r.adjusted_median_wait));

            resultsArea.appendChild(el('div', 'results-meta', r.iterations + ' iterations, ' + r.elapsed_seconds.toFixed(2) + 's'));

            // Continue buttons
            var contEl = document.getElementById('scen-continue-buttons');
            if (contEl && window.TransPlanContinue) {
                var fd = TransPlanPatientForm.collectFormData('pf');
                TransPlanContinue.renderContinueButtons(contEl, 'scenarios', fd);
            }
        }

        // ── Render Travel Subsidy result ──
        function renderSubsidyResult(r) {
            resultsArea.textContent = '';

            var titleOrgan = r.organ.charAt(0).toUpperCase() + r.organ.slice(1);
            resultsArea.appendChild(el('h2', 'results-title', 'Travel Subsidy Analysis: ' + titleOrgan));
            resultsArea.appendChild(el('div', 'results-subtitle', r.total_cities + ' centers analyzed (closed-form, deterministic)'));

            // Tier summary cards
            var tierGrid = el('div', 'tier-grid');
            r.tiers.forEach(function (tier) {
                var card = el('div', 'tier-card');
                card.appendChild(el('h4', '', tier.label));

                function addTierStat(label, value, extraClass) {
                    var row = el('div', 'tier-stat');
                    row.appendChild(el('span', 't-label', label));
                    var valSpan = el('span', 't-value' + (extraClass ? ' ' + extraClass : ''), value);
                    row.appendChild(valSpan);
                    card.appendChild(row);
                }

                addTierStat('Avg Baseline P24', fmtPct(tier.system_avg_baseline_p24));
                addTierStat('Avg Adjusted P24', fmtPct(tier.system_avg_adjusted_p24));
                addTierStat('System Delta', fmtDelta(tier.system_delta_p24), tier.system_delta_p24 >= 0 ? 'positive' : 'negative');
                addTierStat('Avg Wait Change', fmtWait(tier.system_avg_adjusted_wait) + ' (from ' + fmtWait(tier.system_avg_baseline_wait) + ')', tier.system_avg_adjusted_wait <= tier.system_avg_baseline_wait ? 'positive' : 'negative');

                tierGrid.appendChild(card);
            });
            resultsArea.appendChild(tierGrid);

            // Per-city breakdown
            if (r.tiers.length > 0) {
                resultsArea.appendChild(el('h3', '', 'Per-Center Breakdown'));
                resultsArea.lastChild.style.cssText = 'font-size:var(--fs-md); font-weight:600; color:var(--text-1); margin-bottom:var(--space-3);';

                var selectWrap = document.createElement('div');
                selectWrap.style.marginBottom = 'var(--space-3)';
                var tierSelect = document.createElement('select');
                tierSelect.id = 'tierTableSelect';
                tierSelect.style.cssText = 'padding:0.4rem 0.6rem; border:1px solid var(--border); border-radius:var(--radius-sm); font-size:var(--fs-sm); background:var(--surface); color:var(--text-1);';
                r.tiers.forEach(function (tier, i) {
                    var opt = document.createElement('option');
                    opt.value = i;
                    opt.textContent = tier.label;
                    tierSelect.appendChild(opt);
                });
                selectWrap.appendChild(tierSelect);
                resultsArea.appendChild(selectWrap);

                r.tiers.forEach(function (tier, idx) {
                    var tableWrap = el('div', 'city-table-wrap tier-table');
                    tableWrap.id = 'tierTable-' + idx;
                    if (idx > 0) tableWrap.style.display = 'none';
                    tableWrap.appendChild(buildCityTable(tier.cities));
                    resultsArea.appendChild(tableWrap);
                });

                // Wire tier table toggle
                tierSelect.addEventListener('change', function () {
                    document.querySelectorAll('.tier-table').forEach(function (t) { t.style.display = 'none'; });
                    var target = document.getElementById('tierTable-' + tierSelect.value);
                    if (target) target.style.display = '';
                });
            }

            // Disclaimers
            if (r.disclaimers && r.disclaimers.length > 0) {
                var discDiv = el('div', 'scenario-disclaimer');
                discDiv.appendChild(el('strong', '', 'Disclaimers:'));
                var ul = document.createElement('ul');
                ul.style.cssText = 'margin:0.3rem 0 0 1rem; padding:0;';
                r.disclaimers.forEach(function (d) {
                    var li = document.createElement('li');
                    li.style.marginBottom = '0.2rem';
                    li.textContent = d;
                    ul.appendChild(li);
                });
                discDiv.appendChild(ul);
                resultsArea.appendChild(discDiv);
            }

            resultsArea.appendChild(el('div', 'results-meta', r.elapsed_seconds.toFixed(2) + 's total'));

            // Wire table sorting
            wireSorting();

            // Continue buttons
            var contEl = document.getElementById('scen-continue-buttons');
            if (contEl && window.TransPlanContinue) {
                var fd = TransPlanPatientForm.collectFormData('pf');
                TransPlanContinue.renderContinueButtons(contEl, 'scenarios', fd);
            }
        }

        function buildCityTable(cities) {
            var table = document.createElement('table');
            table.className = 'city-table';

            var thead = document.createElement('thead');
            var headerRow = document.createElement('tr');
            var columns = [
                { key: 'city', label: 'Center' },
                { key: 'state', label: 'State' },
                { key: 'baseline_p24', label: 'Baseline P24' },
                { key: 'adjusted_p24', label: 'Adjusted P24' },
                { key: 'delta_p24', label: 'Delta' },
                { key: 'baseline_median_wait', label: 'Base Wait' },
                { key: 'adjusted_median_wait', label: 'Adj Wait' }
            ];
            columns.forEach(function (col) {
                var th = document.createElement('th');
                th.setAttribute('data-sort', col.key);
                th.textContent = col.label + ' ';
                var arrow = el('span', 'sort-arrow');
                th.appendChild(arrow);
                headerRow.appendChild(th);
            });
            thead.appendChild(headerRow);
            table.appendChild(thead);

            var tbody = document.createElement('tbody');
            cities.forEach(function (c) {
                var tr = document.createElement('tr');
                var isPos = c.delta_p24 >= 0;

                var td1 = el('td', '', c.city);
                var td2 = el('td', '', c.state);
                var td3 = el('td', '', fmtPct(c.baseline_p24));
                var td4 = el('td', '', fmtPct(c.adjusted_p24));
                var td5 = el('td', '', fmtDelta(c.delta_p24));
                td5.style.color = isPos ? 'var(--success-600)' : 'var(--danger-600)';
                td5.style.fontWeight = '600';
                var td6 = el('td', '', fmtWait(c.baseline_median_wait));
                var td7 = el('td', '', fmtWait(c.adjusted_median_wait));

                tr.appendChild(td1);
                tr.appendChild(td2);
                tr.appendChild(td3);
                tr.appendChild(td4);
                tr.appendChild(td5);
                tr.appendChild(td6);
                tr.appendChild(td7);
                tbody.appendChild(tr);
            });
            table.appendChild(tbody);

            return table;
        }

        function wireSorting() {
            document.querySelectorAll('.city-table th[data-sort]').forEach(function (th) {
                th.addEventListener('click', function () {
                    var col = th.getAttribute('data-sort');
                    var table = th.closest('table');
                    if (!table) return;

                    var tbody = table.querySelector('tbody');
                    if (!tbody) return;

                    var rows = Array.prototype.slice.call(tbody.querySelectorAll('tr'));
                    var colIndex = Array.prototype.indexOf.call(th.parentNode.children, th);

                    if (sortCol === col) {
                        sortAsc = !sortAsc;
                    } else {
                        sortCol = col;
                        sortAsc = true;
                    }

                    table.querySelectorAll('.sort-arrow').forEach(function (a) { a.textContent = ''; });
                    th.querySelector('.sort-arrow').textContent = sortAsc ? ' \u25B2' : ' \u25BC';

                    rows.sort(function (a, b) {
                        var aText = a.children[colIndex].textContent.trim();
                        var bText = b.children[colIndex].textContent.trim();
                        var aNum = parseFloat(aText);
                        var bNum = parseFloat(bText);

                        if (!isNaN(aNum) && !isNaN(bNum)) {
                            return sortAsc ? aNum - bNum : bNum - aNum;
                        }
                        return sortAsc ? aText.localeCompare(bText) : bText.localeCompare(aText);
                    });

                    rows.forEach(function (row) { tbody.appendChild(row); });
                });
            });
        }
    })();
