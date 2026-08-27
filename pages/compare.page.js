/**
 * Extracted from compare.html (#250).
 *
 * Inline <script> blocks force script-src 'unsafe-inline', which removes
 * most of what a Content-Security-Policy is for. Behaviour is unchanged:
 * the file is loaded at the same position the block occupied, so execution
 * order and DOM readiness are the same.
 */
(function() {
        'use strict';
        var MAX_CENTERS = 3;
        var allCentersList = [];
        var selectedCodes = [];
        var centerDataCache = {};

        var controlsEl = document.getElementById('controls');
        var gridEl = document.getElementById('compare-grid');
        var emptyState = document.getElementById('empty-state');

        async function loadCenterList() {
            try {
                var r = await fetch('/centers');
                if (r.ok) { var d = await r.json(); return d.centers || []; }
            } catch (e) {}
            try {
                var r2 = await fetch('data/srtr-all-centers.json');
                if (r2.ok) { var d2 = await r2.json(); return Object.values(d2.centers || {}); }
            } catch (e) {}
            return [];
        }

        async function loadCenterDetail(code) {
            if (centerDataCache[code]) return centerDataCache[code];
            try {
                var r = await fetch('/centers/' + encodeURIComponent(code));
                if (r.ok) { var data = await r.json(); centerDataCache[code] = data; return data; }
            } catch (e) {}
            return null;
        }

        function buildControls() {
            while (controlsEl.firstChild) controlsEl.removeChild(controlsEl.firstChild);
            for (var i = 0; i < MAX_CENTERS; i++) {
                var picker = document.createElement('div');
                picker.className = 'center-picker';
                var label = document.createElement('label');
                label.textContent = 'Center ' + (i + 1);
                picker.appendChild(label);
                var input = document.createElement('input');
                input.type = 'text';
                input.placeholder = 'Search by name or code...';
                input.setAttribute('data-slot', String(i));
                if (selectedCodes[i]) {
                    var match = allCentersList.find(function(c) { return c.code === selectedCodes[i]; });
                    if (match) input.value = match.name + ' (' + match.code + ')';
                }
                picker.appendChild(input);
                var list = document.createElement('div');
                list.className = 'autocomplete-list';
                picker.appendChild(list);
                setupAutocomplete(input, list, i);
                controlsEl.appendChild(picker);
            }

            var actions = document.createElement('div');
            actions.className = 'compare-actions';
            var shareBtn = document.createElement('button');
            shareBtn.type = 'button';
            shareBtn.textContent = 'Copy Link';
            shareBtn.addEventListener('click', function() {
                var url = window.location.origin + window.location.pathname + '?centers=' + selectedCodes.filter(Boolean).join(',');
                navigator.clipboard.writeText(url).then(function() {
                    shareBtn.textContent = 'Copied!';
                    setTimeout(function() { shareBtn.textContent = 'Copy Link'; }, 1500);
                });
            });
            actions.appendChild(shareBtn);
            var clearBtn = document.createElement('button');
            clearBtn.type = 'button';
            clearBtn.textContent = 'Clear All';
            clearBtn.addEventListener('click', function() {
                selectedCodes = [];
                updateURL();
                buildControls();
                renderComparison();
            });
            actions.appendChild(clearBtn);
            controlsEl.appendChild(actions);
        }

        function setupAutocomplete(input, listEl, slot) {
            var debounce = null;
            input.addEventListener('input', function() {
                clearTimeout(debounce);
                debounce = setTimeout(function() {
                    var q = input.value.trim().toLowerCase();
                    if (q.length < 2) { listEl.style.display = 'none'; return; }
                    var matches = allCentersList.filter(function(c) {
                        return (c.name || '').toLowerCase().indexOf(q) !== -1 ||
                               (c.code || '').toLowerCase().indexOf(q) !== -1 ||
                               (c.state || '').toLowerCase().indexOf(q) !== -1;
                    }).slice(0, 12);
                    while (listEl.firstChild) listEl.removeChild(listEl.firstChild);
                    if (!matches.length) { listEl.style.display = 'none'; return; }
                    matches.forEach(function(c) {
                        var item = document.createElement('div');
                        item.className = 'autocomplete-item';
                        var nameSpan = document.createElement('span');
                        nameSpan.textContent = c.name || 'Unknown';
                        item.appendChild(nameSpan);
                        item.appendChild(document.createTextNode(' '));
                        var metaSpan = document.createElement('small');
                        metaSpan.textContent = (c.state_abbr || '') + ' \u00b7 ' + (c.code || '');
                        item.appendChild(metaSpan);
                        item.addEventListener('mousedown', function(e) {
                            e.preventDefault();
                            selectedCodes[slot] = c.code;
                            input.value = c.name + ' (' + c.code + ')';
                            listEl.style.display = 'none';
                            updateURL();
                            renderComparison();
                        });
                        listEl.appendChild(item);
                    });
                    listEl.style.display = 'block';
                }, 150);
            });
            input.addEventListener('blur', function() { setTimeout(function() { listEl.style.display = 'none'; }, 200); });
        }

        function updateURL() {
            var codes = selectedCodes.filter(Boolean);
            var url = codes.length ? '?centers=' + codes.join(',') : window.location.pathname;
            history.replaceState(null, '', url);
        }

        function readURL() {
            var params = new URLSearchParams(window.location.search);
            var raw = params.get('centers');
            if (raw) return raw.split(',').filter(Boolean).slice(0, MAX_CENTERS);
            return [];
        }

        function makeRow(label, value) {
            var row = document.createElement('div');
            row.className = 'compare-row';
            var l = document.createElement('span');
            l.className = 'label';
            l.textContent = label;
            row.appendChild(l);
            var v = document.createElement('span');
            v.className = 'value';
            v.textContent = String(value);
            row.appendChild(v);
            return row;
        }

        async function renderComparison() {
            var codes = selectedCodes.filter(Boolean);
            while (gridEl.firstChild) gridEl.removeChild(gridEl.firstChild);
            if (!codes.length) {
                gridEl.appendChild(emptyState);
                gridEl.style.setProperty('--cols', '1');
                return;
            }
            gridEl.style.setProperty('--cols', String(codes.length));

            var results = await Promise.all(codes.map(function(code) { return loadCenterDetail(code); }));

            results.forEach(function(data, idx) {
                if (!data || !data.center) {
                    var errCol = document.createElement('div');
                    errCol.className = 'compare-col';
                    var errH = document.createElement('div');
                    errH.className = 'compare-col-header';
                    var errTitle = document.createElement('h2');
                    errTitle.textContent = 'Center not found: ' + codes[idx];
                    errH.appendChild(errTitle);
                    errCol.appendChild(errH);
                    gridEl.appendChild(errCol);
                    return;
                }

                var center = data.center;
                var col = document.createElement('div');
                col.className = 'compare-col';

                // Header
                var header = document.createElement('div');
                header.className = 'compare-col-header';
                var h2 = document.createElement('h2');
                h2.textContent = center.name || 'Unknown';
                var badge = document.createElement('span');
                badge.className = 'code-badge';
                badge.textContent = center.code;
                h2.appendChild(badge);
                header.appendChild(h2);
                var loc = document.createElement('div');
                loc.className = 'location';
                loc.textContent = center.state || center.state_abbr || '';
                header.appendChild(loc);
                col.appendChild(header);

                // Contact
                var contact = data.contact || {};
                if (contact.phone || contact.website) {
                    var cs = document.createElement('div');
                    cs.className = 'compare-section compare-contact';
                    var ch = document.createElement('h3');
                    ch.textContent = 'Contact';
                    cs.appendChild(ch);
                    if (contact.phone) {
                        var pd = document.createElement('div');
                        var pa = document.createElement('a');
                        pa.href = 'tel:+1' + contact.phone.replace(/\D/g, '');
                        pa.textContent = contact.phone;
                        pd.appendChild(pa);
                        cs.appendChild(pd);
                    }
                    if (contact.website) {
                        var wd = document.createElement('div');
                        var wa = document.createElement('a');
                        wa.href = contact.website;
                        wa.target = '_blank';
                        wa.rel = 'noopener noreferrer';
                        try { wa.textContent = new URL(contact.website).hostname.replace(/^www\./, ''); } catch (e) { wa.textContent = contact.website; }
                        wd.appendChild(wa);
                        cs.appendChild(wd);
                    }
                    col.appendChild(cs);
                }

                // Outcomes by organ
                var outcomes = data.outcomes || {};
                var organs = center.organs || [];
                if (organs.length) {
                    var os = document.createElement('div');
                    os.className = 'compare-section';
                    var oh = document.createElement('h3');
                    oh.textContent = 'Outcomes by Organ';
                    os.appendChild(oh);
                    organs.forEach(function(organ) {
                        var oc = outcomes[organ] || {};
                        var oLabel = organ.charAt(0).toUpperCase() + organ.slice(1);
                        var hdr = makeRow(oLabel, oc.n_1yr ? oc.n_1yr + '/yr' : '\u2014');
                        hdr.querySelector('.label').style.fontWeight = '600';
                        os.appendChild(hdr);
                        if (oc.graft_survival_1yr !== undefined) os.appendChild(makeRow('  1-yr graft', oc.graft_survival_1yr.toFixed(1) + '%'));
                        if (oc.patient_survival_1yr !== undefined) os.appendChild(makeRow('  1-yr patient', oc.patient_survival_1yr.toFixed(1) + '%'));
                        if (oc.graft_survival_3yr !== undefined) os.appendChild(makeRow('  3-yr graft', oc.graft_survival_3yr.toFixed(1) + '%'));
                    });
                    col.appendChild(os);
                }

                // Waitlist
                var waitlist = data.waitlist_overview || {};
                var wlOrgans = Object.keys(waitlist);
                if (wlOrgans.length) {
                    var ws = document.createElement('div');
                    ws.className = 'compare-section';
                    var wh = document.createElement('h3');
                    wh.textContent = 'Waitlist';
                    ws.appendChild(wh);
                    wlOrgans.forEach(function(organ) {
                        var w = waitlist[organ];
                        var oLabel = organ.charAt(0).toUpperCase() + organ.slice(1);
                        ws.appendChild(makeRow(oLabel + ' waiting', w.currently_waiting != null ? Number(w.currently_waiting).toLocaleString() : '\u2014'));
                        ws.appendChild(makeRow(oLabel + ' transplanted', ((w.transplanted_cadaveric || 0) + (w.transplanted_living || 0)).toLocaleString()));
                    });
                    col.appendChild(ws);
                }

                // Wait factors
                var wt = data.wait_time_factors || {};
                var wtOrgans = Object.keys(wt);
                if (wtOrgans.length) {
                    var wts = document.createElement('div');
                    wts.className = 'compare-section';
                    var wth = document.createElement('h3');
                    wth.textContent = 'Wait Factors';
                    wts.appendChild(wth);
                    wtOrgans.forEach(function(organ) {
                        wts.appendChild(makeRow(organ.charAt(0).toUpperCase() + organ.slice(1), parseFloat(wt[organ]).toFixed(2) + '\u00d7'));
                    });
                    col.appendChild(wts);
                }

                // Detail link
                var link = document.createElement('a');
                link.className = 'compare-link';
                link.href = 'center.html?code=' + encodeURIComponent(center.code);
                link.textContent = 'View Full Details \u2192';
                col.appendChild(link);

                gridEl.appendChild(col);
            });
        }

        // Init
        loadCenterList().then(function(centers) {
            allCentersList = centers.sort(function(a, b) { return (a.name || '').localeCompare(b.name || ''); });
            selectedCodes = readURL();
            buildControls();
            renderComparison();
        });
    })();
