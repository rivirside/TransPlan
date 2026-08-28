/**
 * Extracted from center.html (#250).
 *
 * Inline <script> blocks force script-src 'unsafe-inline', which removes
 * most of what a Content-Security-Policy is for. Behaviour is unchanged:
 * the file is loaded at the same position the block occupied, so execution
 * order and DOM readiness are the same.
 */
(function() {
        'use strict';

        var detailContainer = document.getElementById('center-detail');
        var loadingState = document.getElementById('loading-state');

        // --- Parse center code from URL ---
        var params = new URLSearchParams(window.location.search);
        var centerCode = params.get('code');

        if (!centerCode) {
            showError('No center code specified', 'Please provide a center code in the URL (e.g., center.html?code=ALUA).');
            return;
        }

        // --- Data loading ---
        async function loadCenterDetail(code) {
            // Try API
            try {
                var resp = await fetch('/centers/' + encodeURIComponent(code));
                if (resp.ok) return await resp.json();
            } catch (e) {}
            // Fallback: load from static JSON
            try {
                var resp = await fetch('data/srtr-all-centers.json');
                if (resp.ok) {
                    var data = await resp.json();
                    var center = data.centers[code];
                    if (center) return { center: center, contact: {}, contact_live: false, wait_time_factors: {}, competing_risks: {}, outcomes: {}, nearby_centers: [], srtr_url: 'https://www.srtr.org/interactive-report?center=' + code + '&type=TX1&organ=KI' };
                }
            } catch (e) {}
            return null;
        }

        // --- Error display ---
        function showError(title, message) {
            while (detailContainer.firstChild) {
                detailContainer.removeChild(detailContainer.firstChild);
            }
            var errorDiv = document.createElement('div');
            errorDiv.className = 'error-state';

            var h2 = document.createElement('h2');
            h2.textContent = title;
            errorDiv.appendChild(h2);

            var p = document.createElement('p');
            p.textContent = message;
            errorDiv.appendChild(p);

            var link = document.createElement('a');
            link.href = 'centers.html';
            link.textContent = 'Back to Center Explorer';
            errorDiv.appendChild(link);

            detailContainer.appendChild(errorDiv);
        }

        // --- Make a section-card collapsible ---
        function makeCollapsible(card, defaultOpen, previewText) {
            var h2 = card.querySelector('h2');
            if (!h2) return;

            // Wrap everything after h2 in .section-body
            var body = document.createElement('div');
            body.className = 'section-body';
            while (h2.nextSibling) body.appendChild(h2.nextSibling);
            card.appendChild(body);

            // Wrap h2's text content + optional preview in a title group
            var titleGroup = document.createElement('span');
            titleGroup.className = 'section-title-group';
            while (h2.firstChild) titleGroup.appendChild(h2.firstChild);
            h2.appendChild(titleGroup);

            if (previewText) {
                var preview = document.createElement('span');
                preview.className = 'section-preview';
                preview.textContent = previewText;
                titleGroup.appendChild(preview);
            }

            // Add toggle indicator
            var toggle = document.createElement('span');
            toggle.className = 'section-toggle';
            toggle.textContent = defaultOpen ? '\u2212' : '+';
            h2.appendChild(toggle);

            if (!defaultOpen) card.classList.add('collapsed');

            h2.addEventListener('click', function() {
                var nowCollapsed = card.classList.toggle('collapsed');
                toggle.textContent = nowCollapsed ? '+' : '\u2212';
            });
        }

        // --- Format factor value with color class ---
        function formatFactor(value, label) {
            if (value === undefined || value === null) return null;
            var num = parseFloat(value);
            if (isNaN(num)) return null;

            var span = document.createElement('span');
            var text = num.toFixed(2) + '\u00d7';
            span.textContent = text;

            span.className = 'factor-neutral';

            return span;
        }

        // --- Format performance rating ---
        function formatRating(rating) {
            if (!rating) return null;
            var span = document.createElement('span');
            var cleanRating = rating.replace(/_/g, ' ');
            span.className = 'rating-badge rating-badge--' + rating;
            span.textContent = cleanRating;
            return span;
        }

        // --- Build header section (includes inline action links) ---
        function buildHeader(data) {
            var center = data.center;
            var header = document.createElement('div');
            header.className = 'center-header';

            var h1 = document.createElement('h1');
            h1.textContent = center.name || 'Unknown Center';
            header.appendChild(h1);

            var loc = document.createElement('div');
            loc.className = 'center-location';
            var parts = [];
            if (center.city) parts.push(center.city);
            if (center.state) parts.push(center.state);
            else if (center.state_abbr) parts.push(center.state_abbr);
            loc.appendChild(document.createTextNode(parts.length > 0 ? parts.join(', ') : 'Location unavailable'));
            if (center.code) {
                var codeTag = document.createElement('span');
                codeTag.style.cssText = 'font-size:0.72rem;font-family:monospace;background:var(--surface-raised,#f3f4f6);border:1px solid var(--border,#e5e7eb);border-radius:2px;padding:0.05rem 0.35rem;margin-left:0.5rem;color:var(--text-muted,#6b7280);vertical-align:middle;';
                codeTag.textContent = center.code;
                loc.appendChild(codeTag);
            }
            header.appendChild(loc);

            var badges = document.createElement('div');
            badges.className = 'center-badges';
            (center.organs || []).forEach(function(organ) {
                var badge = document.createElement('span');
                badge.className = 'organ-badge organ-badge--' + organ;
                badge.textContent = organ;
                badges.appendChild(badge);
            });
            header.appendChild(badges);

            // Inline action links
            var actions = document.createElement('div');
            actions.className = 'center-actions';

            var backLink = document.createElement('a');
            backLink.className = 'quick-link';
            backLink.href = 'centers.html';
            backLink.textContent = '\u2190 Center Explorer';
            actions.appendChild(backLink);

            var srtrLink = document.createElement('a');
            srtrLink.className = 'quick-link';
            srtrLink.href = data.srtr_url || ('https://www.srtr.org/interactive-report?center=' + centerCode + '&type=TX1&organ=KI');
            srtrLink.target = '_blank';
            srtrLink.rel = 'noopener';
            srtrLink.textContent = '\u2197 View on SRTR';
            actions.appendChild(srtrLink);

            var simLink = document.createElement('a');
            simLink.className = 'quick-link';
            var city = center.city || '';
            simLink.href = 'simulator.html' + (city ? '?homeCenter=' + encodeURIComponent(city) : '');
            simLink.textContent = '\u2696 Compare in Simulator';
            actions.appendChild(simLink);

            header.appendChild(actions);
            return header;
        }

        // --- Build combined contact + map section ---
        function buildContactAndMap(data, center) {
            var contact = data.contact || {};
            var live = data.contact_live !== false;

            var addressParts = [];
            if (contact.address) addressParts.push(contact.address);
            var cityState = [contact.city, contact.state].filter(Boolean).join(', ');
            if (cityState) addressParts.push(cityState);
            if (contact.zip) addressParts[addressParts.length - 1] += ' ' + contact.zip;
            var fullAddress = addressParts.join('\n');

            var card = document.createElement('div');
            card.className = 'section-card';

            var h2 = document.createElement('h2');
            h2.textContent = 'Contact & Location';
            card.appendChild(h2);

            var grid = document.createElement('div');
            grid.className = 'contact-map-grid';

            // --- Left: contact info ---
            var left = document.createElement('div');

            var rows = document.createElement('div');
            rows.className = 'contact-rows';

            function addRow(icon, content) {
                var row = document.createElement('div');
                row.className = 'contact-row';
                var iconEl = document.createElement('span');
                iconEl.className = 'contact-icon';
                iconEl.setAttribute('aria-hidden', 'true');
                iconEl.textContent = icon;
                row.appendChild(iconEl);
                var val = document.createElement('div');
                val.className = 'contact-value';
                val.appendChild(content);
                row.appendChild(val);
                rows.appendChild(row);
            }

            if (fullAddress) {
                var addrEl = document.createElement('span');
                fullAddress.split('\n').forEach(function(line, i) {
                    if (i > 0) addrEl.appendChild(document.createElement('br'));
                    addrEl.appendChild(document.createTextNode(line));
                });
                addRow('\u25BE', addrEl);
            }
            if (contact.phone) {
                var phoneLink = document.createElement('a');
                phoneLink.href = 'tel:+1' + contact.phone.replace(/\D/g, '');
                phoneLink.textContent = contact.phone;
                addRow('\u2706', phoneLink);
            }
            if (contact.website) {
                // #162: a bare hostname tells a patient nothing about what is
                // on the other end. Label it, but do NOT promise a team page:
                // 167 of the 248 URLs are a bare hospital root, not a
                // transplant-program page, so "meet the team" would send two
                // thirds of readers to a homepage.
                var siteWrap = document.createElement('span');
                var siteLink = document.createElement('a');
                siteLink.href = contact.website;
                siteLink.target = '_blank';
                siteLink.rel = 'noopener noreferrer';
                siteLink.textContent = 'Program website';
                siteWrap.appendChild(siteLink);
                var host = document.createElement('span');
                host.className = 'contact-host';
                try {
                    host.textContent = ' ' + new URL(contact.website).hostname.replace(/^www\./, '');
                } catch (e) { host.textContent = ' ' + contact.website; }
                siteWrap.appendChild(host);
                addRow('\u25A1', siteWrap);
            }

            // #162: patients ask who they would be working with. Each program
            // publishes its own staff list; this tool deliberately does not
            // mirror one, because a scraped roster goes stale as people move
            // on and a stale name is worse than none.
            var teamHint = document.createElement('p');
            teamHint.className = 'contact-team-hint';
            teamHint.textContent = 'Surgeons, coordinators and other staff are '
                + 'listed on the program\u2019s own site \u2014 this tool does '
                + 'not keep a directory, so nothing here goes out of date when '
                + 'someone moves on.';
            rows.appendChild(teamHint);

            left.appendChild(rows);

            if (!live) {
                var stale = document.createElement('div');
                stale.className = 'contact-stale';
                stale.style.marginTop = '0.75rem';
                stale.textContent = 'Live data fetch failed \u2014 cached data may be out of date.';
                left.appendChild(stale);
            }

            grid.appendChild(left);

            // --- Right: map ---
            var mapDiv = document.createElement('div');
            mapDiv.className = 'map-container';
            mapDiv.id = 'center-map';
            grid.appendChild(mapDiv);

            card.appendChild(grid);

            setTimeout(function() {
                var lat = center.lat;
                var lon = center.lon;
                if (lat && lon) {
                    var map = L.map('center-map').setView([lat, lon], 12);
                    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                        attribution: '&copy; OpenStreetMap contributors',
                        maxZoom: 18
                    }).addTo(map);
                    L.marker([lat, lon]).addTo(map)
                        .bindPopup(center.name || 'Transplant Center')
                        .openPopup();
                } else {
                    mapDiv.style.display = 'flex';
                    mapDiv.style.alignItems = 'center';
                    mapDiv.style.justifyContent = 'center';
                    mapDiv.style.background = 'var(--surface-sunken, #f1f3f7)';
                    var noMap = document.createElement('span');
                    noMap.className = 'no-data';
                    noMap.textContent = 'No coordinates available for this center.';
                    mapDiv.appendChild(noMap);
                }
            }, 0);

            var contactCity = contact.city || '';
            var preview = [contactCity, center.state_abbr || center.state].filter(Boolean).join(', ');
            makeCollapsible(card, true, 'Address, phone, website, and interactive map');
            return card;
        }

        // --- Build organ programs table ---
        function buildProgramsTable(data) {
            var card = document.createElement('div');
            card.className = 'section-card';

            var h2 = document.createElement('h2');
            h2.textContent = 'Organ Programs';
            card.appendChild(h2);

            var organs = data.center.organs || [];
            if (organs.length === 0) {
                var noData = document.createElement('p');
                noData.className = 'no-data';
                noData.textContent = 'No organ program data available.';
                card.appendChild(noData);
                return card;
            }

            var table = document.createElement('table');
            table.className = 'programs-table';

            // Header
            var thead = document.createElement('thead');
            var headerRow = document.createElement('tr');
            var headers = ['Organ', 'Wait', 'Mortality', 'Delisting', '1-yr Graft', '1-yr Patient', '3-yr Graft', '3-yr Patient', 'HR [95% CI]', 'Vol./yr'];
            headers.forEach(function(text) {
                var th = document.createElement('th');
                th.textContent = text;
                headerRow.appendChild(th);
            });
            thead.appendChild(headerRow);
            table.appendChild(thead);

            // Body
            var tbody = document.createElement('tbody');
            var waitFactors = data.wait_time_factors || {};
            var riskFactors = data.competing_risks || {};
            var outcomes = data.outcomes || {};

            organs.forEach(function(organ) {
                var row = document.createElement('tr');

                // Organ name with color dot
                var organTd = document.createElement('td');
                var organName = document.createElement('span');
                organName.className = 'organ-name';
                var dot = document.createElement('span');
                dot.className = 'organ-dot organ-dot--' + organ;
                organName.appendChild(dot);
                var nameText = document.createTextNode(organ);
                organName.appendChild(nameText);
                organTd.appendChild(organName);
                row.appendChild(organTd);

                // Wait time factor
                var waitTd = document.createElement('td');
                var waitVal = waitFactors[organ];
                var waitSpan = formatFactor(waitVal, 'wait');
                if (waitSpan) {
                    waitTd.appendChild(waitSpan);
                } else {
                    var noWait = document.createElement('span');
                    noWait.className = 'no-data';
                    noWait.textContent = '\u2014';
                    waitTd.appendChild(noWait);
                }
                row.appendChild(waitTd);

                // Mortality factor
                var mortTd = document.createElement('td');
                var organRisk = riskFactors[organ] || {};
                var mortSpan = formatFactor(organRisk.mortality_factor, 'mortality');
                if (mortSpan) {
                    mortTd.appendChild(mortSpan);
                } else {
                    var noMort = document.createElement('span');
                    noMort.className = 'no-data';
                    noMort.textContent = '\u2014';
                    mortTd.appendChild(noMort);
                }
                row.appendChild(mortTd);

                // Delisting factor
                var delistTd = document.createElement('td');
                var delistSpan = formatFactor(organRisk.delisting_factor, 'delisting');
                if (delistSpan) {
                    delistTd.appendChild(delistSpan);
                } else {
                    var noDelist = document.createElement('span');
                    noDelist.className = 'no-data';
                    noDelist.textContent = '\u2014';
                    delistTd.appendChild(noDelist);
                }
                row.appendChild(delistTd);

                // 1-yr graft survival
                var organOutcome = outcomes[organ] || {};
                var graft1Td = document.createElement('td');
                graft1Td.textContent = organOutcome.graft_survival_1yr !== undefined ? organOutcome.graft_survival_1yr.toFixed(1) + '%' : '\u2014';
                row.appendChild(graft1Td);

                // 1-yr patient survival
                var pat1Td = document.createElement('td');
                pat1Td.textContent = organOutcome.patient_survival_1yr !== undefined ? organOutcome.patient_survival_1yr.toFixed(1) + '%' : '\u2014';
                row.appendChild(pat1Td);

                // 3-yr graft survival
                var graft3Td = document.createElement('td');
                graft3Td.textContent = organOutcome.graft_survival_3yr !== undefined ? organOutcome.graft_survival_3yr.toFixed(1) + '%' : '\u2014';
                row.appendChild(graft3Td);

                // 3-yr patient survival
                var pat3Td = document.createElement('td');
                pat3Td.textContent = organOutcome.patient_survival_3yr !== undefined ? organOutcome.patient_survival_3yr.toFixed(1) + '%' : '\u2014';
                row.appendChild(pat3Td);

                // Hazard ratio with 95% CI
                var hrTd = document.createElement('td');
                hrTd.style.cssText = 'font-variant-numeric:tabular-nums;white-space:nowrap;';
                if (organOutcome.graft_hr_1yr !== undefined) {
                    var hrText = organOutcome.graft_hr_1yr.toFixed(2);
                    if (organOutcome.graft_hr_1yr_ci) {
                        hrText += ' [' + organOutcome.graft_hr_1yr_ci[0].toFixed(2) + '\u2013' + organOutcome.graft_hr_1yr_ci[1].toFixed(2) + ']';
                    }
                    hrTd.textContent = hrText;
                } else {
                    hrTd.textContent = '\u2014';
                }
                row.appendChild(hrTd);

                // Annual volume
                var volTd = document.createElement('td');
                if (organOutcome.n_1yr !== undefined) {
                    var volSpan = document.createElement('span');
                    volSpan.style.fontVariantNumeric = 'tabular-nums';
                    volSpan.textContent = organOutcome.n_1yr.toLocaleString();
                    volTd.appendChild(volSpan);
                } else {
                    var noVol = document.createElement('span');
                    noVol.className = 'no-data';
                    noVol.textContent = '\u2014';
                    volTd.appendChild(noVol);
                }
                row.appendChild(volTd);

                tbody.appendChild(row);
            });

            table.appendChild(tbody);
            var scrollWrap = document.createElement('div');
            scrollWrap.className = 'table-scroll';
            scrollWrap.appendChild(table);
            card.appendChild(scrollWrap);
            var organPreview = organs.map(function(o) { return o.charAt(0).toUpperCase() + o.slice(1); }).join(' · ');
            makeCollapsible(card, true, 'Survival rates, wait times, and transplant volume by organ');
            return card;
        }

        // --- Build waitlist card ---
        function buildWaitlistCard(data) {
            var waitlist = data.waitlist_overview || {};
            var organs = Object.keys(waitlist);
            if (organs.length === 0) return null;

            var card = document.createElement('div');
            card.className = 'section-card';

            var h2 = document.createElement('h2');
            h2.textContent = 'Waitlist Activity';
            card.appendChild(h2);

            // Organ selector
            var select = document.createElement('select');
            select.className = 'waitlist-organ-select';
            organs.forEach(function(organ) {
                var opt = document.createElement('option');
                opt.value = organ;
                opt.textContent = organ.charAt(0).toUpperCase() + organ.slice(1);
                select.appendChild(opt);
            });
            card.appendChild(select);

            // Stats grid (updated on select change)
            var grid = document.createElement('div');
            grid.className = 'waitlist-grid';
            card.appendChild(grid);

            function renderGrid(organ) {
                while (grid.firstChild) grid.removeChild(grid.firstChild);
                var w = waitlist[organ] || {};
                var stats = [
                    { value: w.currently_waiting, label: 'Currently waiting' },
                    { value: w.added_last_year, label: 'Added last year' },
                    { value: w.transplanted_cadaveric, label: 'Transplanted (deceased donor)' },
                    { value: w.transplanted_living, label: 'Transplanted (living donor)' },
                    { value: w.removed_died, label: 'Died while waiting' },
                    { value: w.removed_deteriorated, label: 'Removed (too ill)' },
                ];
                stats.forEach(function(s) {
                    if (s.value === undefined || s.value === null) return;
                    var stat = document.createElement('div');
                    stat.className = 'waitlist-stat';
                    var val = document.createElement('div');
                    val.className = 'waitlist-stat-value';
                    val.textContent = Number(s.value).toLocaleString();
                    stat.appendChild(val);
                    var lbl = document.createElement('div');
                    lbl.className = 'waitlist-stat-label';
                    lbl.textContent = s.label;
                    stat.appendChild(lbl);
                    grid.appendChild(stat);
                });
            }

            renderGrid(organs[0]);
            select.addEventListener('change', function() { renderGrid(select.value); });

            var firstOrganData = waitlist[organs[0]] || {};
            var waitingCount = firstOrganData.currently_waiting;
            var firstOrganName = organs[0].charAt(0).toUpperCase() + organs[0].slice(1);
            var wlPreview = firstOrganName + (waitingCount != null ? ' · ' + waitingCount.toLocaleString() + ' waiting' : '');
            makeCollapsible(card, true, 'Patients waiting, added, transplanted, and removed by organ');
            return card;
        }


        // --- Build nearby centers list ---
        function buildNearbyCenters(nearbyCenters) {
            var card = document.createElement('div');
            card.className = 'section-card';

            var h2 = document.createElement('h2');
            h2.textContent = 'Nearby Centers';
            card.appendChild(h2);

            if (!nearbyCenters || nearbyCenters.length === 0) {
                var noData = document.createElement('p');
                noData.className = 'no-data';
                noData.textContent = 'No nearby centers found within radius.';
                card.appendChild(noData);
                return card;
            }

            var list = document.createElement('ul');
            list.className = 'nearby-list';

            var displayCount = Math.min(nearbyCenters.length, 10);
            for (var i = 0; i < displayCount; i++) {
                var nc = nearbyCenters[i];

                var item = document.createElement('li');
                item.className = 'nearby-item';

                var info = document.createElement('div');
                info.className = 'nearby-info';

                var nameLink = document.createElement('a');
                nameLink.className = 'nearby-name';
                nameLink.href = 'center.html?code=' + encodeURIComponent(nc.code || '');
                nameLink.textContent = nc.name || 'Unknown';
                nameLink.title = nc.name || '';
                info.appendChild(nameLink);

                var meta = document.createElement('div');
                meta.className = 'nearby-meta';
                var metaParts = [];
                if (nc.state_abbr) metaParts.push(nc.state_abbr);
                var organCount = (nc.organs || []).length;
                if (organCount > 0) metaParts.push(organCount + ' organ program' + (organCount !== 1 ? 's' : ''));
                meta.textContent = metaParts.join(' \u00B7 ');
                info.appendChild(meta);

                item.appendChild(info);

                var dist = document.createElement('div');
                dist.className = 'nearby-distance';
                if (nc.distance_miles !== undefined) {
                    dist.textContent = nc.distance_miles + ' mi';
                }
                item.appendChild(dist);

                list.appendChild(item);
            }

            card.appendChild(list);
            makeCollapsible(card, true, 'Other transplant programs within 250 miles');
            return card;
        }

        // --- Render the page ---
        function render(data) {
            while (detailContainer.firstChild) {
                detailContainer.removeChild(detailContainer.firstChild);
            }

            var center = data.center;

            // Update page title
            document.title = 'transplant.today - ' + (center.name || centerCode);

            // Header (includes inline action links)
            detailContainer.appendChild(buildHeader(data));

            // Single column — order: Programs, Waitlist, Contact+Map, Nearby
            detailContainer.appendChild(buildProgramsTable(data));
            var waitlistCard = buildWaitlistCard(data);
            if (waitlistCard) detailContainer.appendChild(waitlistCard);
            detailContainer.appendChild(buildContactAndMap(data, center));
            detailContainer.appendChild(buildLocationDelta(center));
            detailContainer.appendChild(buildNearbyCenters(data.nearby_centers));
        }


        /**
         * #350: GET /location-delta had no caller anywhere in the app, so the
         * "how does this area compare to where I live?" question it answers
         * was unreachable. Relocating for a transplant is a real decision, and
         * these are the environmental factors a patient would actually weigh.
         */
        function buildLocationDelta(center) {
            var card = document.createElement('div');
            card.className = 'section-card';

            var h = document.createElement('h2');
            h.textContent = 'Compared to where you live';
            card.appendChild(h);

            if (!center.lat || !center.lon) {
                var na = document.createElement('p');
                na.className = 'no-data';
                na.textContent = 'This center has no mapped coordinates, so a ' +
                    'location comparison is not available.';
                card.appendChild(na);
                makeCollapsible(card, true, 'Air quality, cost of living, and population health');
                return card;
            }

            var intro = document.createElement('p');
            intro.className = 'muted';
            intro.textContent = 'Enter a ZIP code or city to compare the area ' +
                'around this center with your own on air quality, cost of ' +
                'living, and population health. These are interpolated ' +
                'surfaces, so treat them as regional context rather than ' +
                'precise local measurements.';
            card.appendChild(intro);

            var row = document.createElement('div');
            row.style.cssText = 'display:flex; gap:0.5rem; align-items:center; flex-wrap:wrap; margin:0.6rem 0';
            var input = document.createElement('input');
            input.type = 'text';
            input.id = 'ld-home';
            input.placeholder = 'ZIP or city, e.g. 64108 or Kansas City, MO';
            input.style.cssText = 'flex:1; min-width:220px; padding:0.4rem 0.55rem';
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'btn-secondary';
            btn.textContent = 'Compare';
            var status = document.createElement('span');
            status.id = 'ld-status';
            status.className = 'muted';
            status.style.fontSize = '0.85rem';
            row.appendChild(input);
            row.appendChild(btn);
            row.appendChild(status);
            card.appendChild(row);

            var wrap = document.createElement('div');
            wrap.id = 'ld-results';
            wrap.style.display = 'none';
            card.appendChild(wrap);

            function labelFor(layer) {
                var map = {
                    air_quality: 'Air quality',
                    cost_of_living: 'Cost of living',
                    health_diabetesRate: 'Diabetes rate',
                    health_obesityRate: 'Obesity rate',
                    health_ckdRate: 'Chronic kidney disease rate',
                    health_hypertensionRate: 'Hypertension rate',
                    health_smokingRate: 'Smoking rate'
                };
                return map[layer] || layer.replace(/_/g, ' ');
            }

            function run() {
                var query = (input.value || '').trim();
                if (!query) { status.textContent = 'Enter a ZIP code or city first.'; return; }
                btn.disabled = true;
                status.textContent = 'Locating…';
                wrap.style.display = 'none';

                var geo = window.TransPlanGeo && window.TransPlanGeo.geocodeLocation
                    ? window.TransPlanGeo.geocodeLocation(query)
                    : Promise.reject(new Error('Geocoding is unavailable.'));

                geo.then(function (loc) {
                    // geocodeLocation resolves to null rather than rejecting
                    // when nothing matches, so a null check is the real guard.
                    if (!loc || typeof loc.lat !== 'number') {
                        throw new Error('Could not find that location.');
                    }
                    // The interpolation surfaces cover CONUS only; outside it
                    // the endpoint 422s, which would surface as a bare HTTP
                    // error rather than an explanation.
                    if (loc.lat < 24 || loc.lat > 50 || loc.lon < -125 || loc.lon > -66) {
                        throw new Error('Comparison covers the continental US only.');
                    }
                    // The CENTER must be in range too. A Hawaii or Puerto Rico
                    // center made the endpoint 422 and surfaced as a bare
                    // "HTTP 422" instead of the explanation written above.
                    if (center.lat < 24 || center.lat > 50 ||
                        center.lon < -125 || center.lon > -66) {
                        throw new Error('This center is outside the continental ' +
                            'US, which the comparison layers do not cover.');
                    }
                    status.textContent = 'Comparing…';
                    var base = window.TransPlanAPI ? TransPlanAPI.getBaseUrl() : '';
                    var url = base + '/location-delta?home_lat=' + loc.lat.toFixed(4) +
                        '&home_lon=' + loc.lon.toFixed(4) +
                        '&center_lat=' + center.lat +
                        '&center_lon=' + center.lon;
                    return fetch(url).then(function (r) {
                        if (!r.ok) throw new Error('HTTP ' + r.status);
                        return r.json();
                    });
                }).then(function (result) {
                    while (wrap.firstChild) wrap.removeChild(wrap.firstChild);
                    var table = document.createElement('table');
                    table.className = 'detail-table';
                    var thead = document.createElement('thead');
                    var htr = document.createElement('tr');
                    ['Factor', 'Your area', 'Center area', 'Difference'].forEach(function (t) {
                        var th = document.createElement('th');
                        th.textContent = t;
                        htr.appendChild(th);
                    });
                    thead.appendChild(htr);
                    table.appendChild(thead);

                    var tbody = document.createElement('tbody');
                    Object.keys(result.deltas || {}).forEach(function (layer) {
                        var d = result.deltas[layer];
                        if (!d) return;
                        var tr = document.createElement('tr');
                        [labelFor(layer), d.home.toFixed(1), d.center.toFixed(1),
                         (d.delta > 0 ? '+' : '') + d.delta.toFixed(1)
                        ].forEach(function (text) {
                            var td = document.createElement('td');
                            td.textContent = text;
                            tr.appendChild(td);
                        });
                        tbody.appendChild(tr);
                    });
                    table.appendChild(tbody);
                    wrap.appendChild(table);

                    var note = document.createElement('p');
                    note.className = 'no-data';
                    note.style.fontSize = '0.8rem';
                    note.textContent = 'Higher is better for air quality; for the ' +
                        'health rates and cost of living, lower is better. ' +
                        'Values are interpolated between measured points, so ' +
                        'nearby locations will read similarly.';
                    wrap.appendChild(note);

                    status.textContent = '';
                    wrap.style.display = '';
                }).catch(function (err) {
                    status.textContent = err.message || 'Comparison failed.';
                }).then(function () {
                    btn.disabled = false;
                });
            }

            btn.addEventListener('click', run);
            input.addEventListener('keydown', function (e) {
                // Guard on btn.disabled: repeated Enter otherwise fired
                // concurrent /location-delta requests that could resolve out
                // of order and render a stale comparison.
                if (e.key === 'Enter' && !btn.disabled) run();
            });
            makeCollapsible(card, true, 'Air quality, cost of living, and population health');
            return card;
        }

        // --- Init ---
        loadCenterDetail(centerCode).then(function(data) {
            if (!data || !data.center) {
                showError('Center Not Found', 'No transplant center found with code "' + centerCode + '".');
                return;
            }
            render(data);
        }).catch(function(err) {
            showError('Error Loading Data', 'Something went wrong while loading center data. Please try again.');
        });
    })();
