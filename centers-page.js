/**
 * centers-page.js — Unified centers page with Find / Browse / Estimate modes.
 * Merges find-centers.html, centers.html, and wait-estimator.html into one tabbed page.
 */
(function () {
  'use strict';

  // ── State ──
  var allCenters = [];
  var waitFactors = {};
  var outcomes = {};
  var distData = {};
  var userLat = null;
  var userLon = null;
  var currentMode = 'find';

  // Find mode state
  var findOrgan = null;
  var findBlood = null;

  // Browse mode state
  var activeOrgans = new Set();
  var currentSort = 'name';

  // Estimate mode state
  var estOrgan = null;
  var estBlood = null;

  // ── DOM refs ──
  var tabBtns, modePanels;

  // Find mode
  var findZip, findLocateBtn, findLocationStatus, findOrganPills, findBloodPills, findBtn, findResults;

  // Browse mode
  var browseSearch, browseSort, browseFilterChips, browseZip, browseLocateBtn, browseLocationStatus;
  var browseInfo, browseGrid;

  // Estimate mode
  var estOrganPills, estBloodPills, estBtn, estResult;

  // ══════════════════════════════════════════════════════════
  // ── Data Loading ──
  // ══════════════════════════════════════════════════════════

  async function loadAllData() {
    // Centers: try API first, then JSON fallback
    try {
      var resp = await fetch('/centers');
      if (resp.ok) {
        var d = await resp.json();
        allCenters = d.centers || [];
      } else { throw new Error('API failed'); }
    } catch (e) {
      try {
        var r = await fetch('data/srtr-all-centers.json');
        var d2 = await r.json();
        allCenters = Object.values(d2.centers || {});
      } catch (e2) { allCenters = []; }
    }

    // Wait factors
    try {
      var r2 = await fetch('data/wait-time-distributions-centers.json');
      var wt = await r2.json();
      waitFactors = wt.center_wait_time_factors || {};
    } catch (e) { waitFactors = {}; }

    // Outcomes
    try {
      var r3 = await fetch('data/post-transplant-outcomes-centers.json');
      var oc = await r3.json();
      outcomes = oc.center_outcomes || {};
    } catch (e) { outcomes = {}; }

    // National distributions (for estimate mode)
    try {
      var r4 = await fetch('data/wait-time-distributions.json');
      distData = await r4.json();
    } catch (e) { distData = {}; }
  }

  // ══════════════════════════════════════════════════════════
  // ── Helpers ──
  // ══════════════════════════════════════════════════════════

  function clearChildren(el) {
    while (el.firstChild) el.removeChild(el.firstChild);
  }

  function capitalize(s) {
    return s ? s.charAt(0).toUpperCase() + s.slice(1) : '';
  }

  function formatMonths(m) {
    if (m < 1) return Math.round(m * 30) + ' days';
    if (m < 12) return Math.round(m) + ' mo';
    var years = Math.floor(m / 12);
    var months = Math.round(m % 12);
    if (months === 0) return years + ' yr';
    return years + ' yr ' + months + ' mo';
  }

  function addBd(container, label, value) {
    var item = document.createElement('div');
    item.className = 'bd-item';
    var l = document.createElement('span');
    l.className = 'bd-label';
    l.textContent = label + ': ';
    item.appendChild(l);
    var v = document.createElement('span');
    v.className = 'bd-val';
    v.textContent = value;
    item.appendChild(v);
    container.appendChild(item);
  }

  async function geocodeZip(zip) {
    if (window.TransPlanGeo) {
      return TransPlanGeo.geocodeLocation(zip);
    }
    var url = 'https://nominatim.openstreetmap.org/search?postalcode=' + encodeURIComponent(zip) + '&country=US&format=json&limit=1';
    var r = await fetch(url, { headers: { 'User-Agent': 'TransPlan/2.0' } });
    if (!r.ok) return null;
    var results = await r.json();
    if (!results.length) return null;
    return { lat: parseFloat(results[0].lat), lon: parseFloat(results[0].lon) };
  }

  // ══════════════════════════════════════════════════════════
  // ── Tab / Mode Switching ──
  // ══════════════════════════════════════════════════════════

  function switchMode(mode) {
    currentMode = mode;
    tabBtns.forEach(function (btn) {
      btn.classList.toggle('active', btn.getAttribute('data-mode') === mode);
    });
    modePanels.forEach(function (panel) {
      panel.style.display = panel.id === mode + '-panel' ? '' : 'none';
    });

    // Re-render browse when switching to it (data may have loaded after init)
    if (mode === 'browse' && allCenters.length > 0) {
      renderBrowseCenters();
    }

    var url = new URL(window.location);
    url.searchParams.set('mode', mode);
    history.replaceState(null, '', url);
  }

  // ══════════════════════════════════════════════════════════
  // ── FIND MODE ──
  // ══════════════════════════════════════════════════════════

  function initFindMode() {
    findZip = document.getElementById('find-zip');
    findLocateBtn = document.getElementById('find-locate-btn');
    findLocationStatus = document.getElementById('find-location-status');
    findOrganPills = document.getElementById('find-organ-pills');
    findBloodPills = document.getElementById('find-blood-pills');
    findBtn = document.getElementById('find-btn');
    findResults = document.getElementById('find-results');

    findZip.addEventListener('input', function () {
      var zip = findZip.value.trim();
      if (zip.length === 5 && /^\d{5}$/.test(zip)) {
        findLocationStatus.textContent = 'Looking up...';
        geocodeZip(zip).then(function (coords) {
          if (coords) {
            userLat = coords.lat; userLon = coords.lon;
            findLocationStatus.textContent = 'Location set';
            updateFindBtn();
          } else {
            findLocationStatus.textContent = 'Zip not found';
          }
        }).catch(function () { findLocationStatus.textContent = 'Lookup failed'; });
      }
    });

    findLocateBtn.addEventListener('click', function () {
      if (!navigator.geolocation) { findLocationStatus.textContent = 'Not supported'; return; }
      findLocationStatus.textContent = 'Getting location...';
      navigator.geolocation.getCurrentPosition(function (pos) {
        userLat = pos.coords.latitude; userLon = pos.coords.longitude;
        findLocationStatus.textContent = 'Location set';
        findZip.value = '';
        updateFindBtn();
      }, function () { findLocationStatus.textContent = 'Location denied'; }, { timeout: 10000 });
    });

    findOrganPills.addEventListener('click', function (e) {
      var pill = e.target.closest('.organ-pill');
      if (!pill) return;
      findOrganPills.querySelectorAll('.organ-pill').forEach(function (p) { p.classList.remove('active'); });
      pill.classList.add('active');
      findOrgan = pill.getAttribute('data-organ');
      updateFindBtn();
    });

    findBloodPills.addEventListener('click', function (e) {
      var pill = e.target.closest('.blood-pill');
      if (!pill) return;
      var wasActive = pill.classList.contains('active');
      findBloodPills.querySelectorAll('.blood-pill').forEach(function (p) { p.classList.remove('active'); });
      if (!wasActive) {
        pill.classList.add('active');
        findBlood = pill.getAttribute('data-blood');
      } else {
        findBlood = null;
      }
    });

    findBtn.addEventListener('click', runFindCenters);
  }

  function updateFindBtn() {
    findBtn.disabled = !(userLat !== null && findOrgan);
  }

  function scoreCenter(center, organ) {
    var code = center.code;
    var dist = (center.lat && center.lon && userLat !== null)
      ? TransPlanGeo.haversineMiles(userLat, userLon, center.lat, center.lon) : 9999;

    var distScore = Math.max(0, 100 - (dist / 5));

    var wf = (waitFactors[code] || {})[organ];
    var waitScore = wf !== undefined ? Math.max(0, Math.min(100, 100 - (wf * 30))) : 50;

    var oc = (outcomes[code] || {})[organ] || {};
    var survScore = oc.graft_survival_1yr !== undefined ? oc.graft_survival_1yr : 50;

    var vol = oc.n_1yr || 0;
    var volScore = vol > 0 ? Math.min(100, Math.log(vol + 1) * 15) : 0;

    var composite = distScore * 0.30 + survScore * 0.30 + waitScore * 0.20 + volScore * 0.20;

    return {
      center: center, distance: dist,
      distScore: distScore, waitFactor: wf, waitScore: waitScore,
      survival: oc.graft_survival_1yr, survScore: survScore,
      volume: vol, volScore: volScore, composite: composite
    };
  }

  function runFindCenters() {
    if (!userLat || !findOrgan) return;

    var candidates = allCenters.filter(function (c) {
      return (c.organs || []).indexOf(findOrgan) !== -1;
    });

    var scored = candidates.map(function (c) { return scoreCenter(c, findOrgan); });
    scored.sort(function (a, b) { return b.composite - a.composite; });

    renderFindResults(scored.slice(0, 20), candidates.length);
  }

  function renderFindResults(results, totalCandidates) {
    findResults.style.display = 'block';
    clearChildren(findResults);

    var header = document.createElement('div');
    header.className = 'results-header';
    var h2 = document.createElement('h2');
    h2.textContent = 'Your Top Centers for ' + capitalize(findOrgan);
    header.appendChild(h2);
    var count = document.createElement('span');
    count.className = 'results-count';
    count.textContent = 'Showing top ' + results.length + ' of ' + totalCandidates + ' ' + findOrgan + ' programs';
    header.appendChild(count);
    findResults.appendChild(header);

    results.forEach(function (r, i) {
      var card = document.createElement('div');
      card.className = 'result-card';

      var rank = document.createElement('div');
      rank.className = 'result-rank ' + (i < 3 ? 'top3' : 'other');
      rank.textContent = String(i + 1);
      card.appendChild(rank);

      var info = document.createElement('div');
      info.className = 'result-info';
      var name = document.createElement('h3');
      name.textContent = r.center.name || 'Unknown';
      info.appendChild(name);

      var meta = document.createElement('div');
      meta.className = 'result-meta';
      var distSpan = document.createElement('span');
      distSpan.textContent = Math.round(r.distance) + ' mi';
      meta.appendChild(distSpan);
      var stateSpan = document.createElement('span');
      stateSpan.textContent = r.center.state || r.center.state_abbr || '';
      meta.appendChild(stateSpan);
      info.appendChild(meta);

      var scores = document.createElement('div');
      scores.className = 'result-scores';
      if (r.survival !== undefined) addScoreBadge(scores, '1-yr graft', r.survival.toFixed(1) + '%');
      if (r.waitFactor !== undefined) addScoreBadge(scores, 'wait factor', r.waitFactor.toFixed(2) + '\u00d7');
      if (r.volume > 0) addScoreBadge(scores, 'vol/yr', String(r.volume));
      info.appendChild(scores);
      card.appendChild(info);

      var linkDiv = document.createElement('div');
      linkDiv.className = 'result-link';
      var a = document.createElement('a');
      a.href = 'center.html?code=' + encodeURIComponent(r.center.code);
      a.textContent = 'Details \u2192';
      linkDiv.appendChild(a);
      card.appendChild(linkDiv);

      findResults.appendChild(card);
    });

    findResults.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function addScoreBadge(container, label, value) {
    var s = document.createElement('div');
    s.className = 'result-score';
    var v = document.createElement('span');
    v.className = 'val';
    v.textContent = value;
    s.appendChild(v);
    s.appendChild(document.createTextNode(label));
    container.appendChild(s);
  }

  // ══════════════════════════════════════════════════════════
  // ── BROWSE MODE ──
  // ══════════════════════════════════════════════════════════

  function initBrowseMode() {
    browseSearch = document.getElementById('browse-search');
    browseSort = document.getElementById('browse-sort');
    browseFilterChips = document.getElementById('browse-filter-chips');
    browseZip = document.getElementById('browse-zip');
    browseLocateBtn = document.getElementById('browse-locate-btn');
    browseLocationStatus = document.getElementById('browse-location-status');
    browseInfo = document.getElementById('browse-info');
    browseGrid = document.getElementById('browse-grid');

    browseSearch.addEventListener('keyup', renderBrowseCenters);

    browseSort.addEventListener('change', function () {
      currentSort = browseSort.value;
      renderBrowseCenters();
    });

    browseFilterChips.addEventListener('click', function (e) {
      var chip = e.target.closest('.filter-chip');
      if (!chip) return;
      var organ = chip.getAttribute('data-organ');
      if (!organ) return;
      if (activeOrgans.has(organ)) {
        activeOrgans.delete(organ);
        chip.classList.remove('active');
      } else {
        activeOrgans.add(organ);
        chip.classList.add('active');
      }
      renderBrowseCenters();
    });

    browseZip.addEventListener('input', function () {
      var zip = browseZip.value.trim();
      if (zip.length === 5 && /^\d{5}$/.test(zip)) {
        browseLocationStatus.textContent = 'Looking up...';
        geocodeZip(zip).then(function (coords) {
          if (coords) {
            userLat = coords.lat; userLon = coords.lon;
            currentSort = 'distance'; browseSort.value = 'distance';
            browseLocationStatus.textContent = 'Sorted by distance';
            renderBrowseCenters();
          } else {
            browseLocationStatus.textContent = 'Zip not found';
          }
        }).catch(function () { browseLocationStatus.textContent = 'Lookup failed'; });
      } else if (zip.length === 0) {
        userLat = null; userLon = null;
        browseLocationStatus.textContent = '';
        if (currentSort === 'distance') { currentSort = 'name'; browseSort.value = 'name'; }
        renderBrowseCenters();
      }
    });

    browseLocateBtn.addEventListener('click', function () {
      if (!navigator.geolocation) { browseLocationStatus.textContent = 'Not supported'; return; }
      browseLocationStatus.textContent = 'Getting location...';
      navigator.geolocation.getCurrentPosition(function (pos) {
        userLat = pos.coords.latitude; userLon = pos.coords.longitude;
        currentSort = 'distance'; browseSort.value = 'distance';
        browseLocationStatus.textContent = 'Sorted by distance';
        browseZip.value = '';
        renderBrowseCenters();
      }, function () { browseLocationStatus.textContent = 'Location denied'; }, { timeout: 10000 });
    });

    renderBrowseCenters();
  }

  function getFilteredCenters() {
    var query = browseSearch.value.trim().toLowerCase();
    var filtered = allCenters.filter(function (c) {
      if (query) {
        var name = (c.name || '').toLowerCase();
        var city = (c.city || '').toLowerCase();
        var state = (c.state || '').toLowerCase();
        var stateAbbr = (c.state_abbr || '').toLowerCase();
        if (name.indexOf(query) === -1 && city.indexOf(query) === -1 &&
            state.indexOf(query) === -1 && stateAbbr.indexOf(query) === -1) {
          return false;
        }
      }
      if (activeOrgans.size > 0) {
        var organs = c.organs || [];
        var hasAny = false;
        activeOrgans.forEach(function (o) {
          if (organs.indexOf(o) !== -1) hasAny = true;
        });
        if (!hasAny) return false;
      }
      return true;
    });

    if (userLat !== null && userLon !== null) {
      filtered.forEach(function (c) {
        c._distance = (c.lat && c.lon) ? TransPlanGeo.haversineMiles(userLat, userLon, c.lat, c.lon) : Infinity;
      });
    } else {
      filtered.forEach(function (c) { c._distance = undefined; });
    }

    filtered.sort(function (a, b) {
      if (currentSort === 'distance' && userLat !== null) {
        return (a._distance || Infinity) - (b._distance || Infinity);
      } else if (currentSort === 'name') {
        return (a.name || '').localeCompare(b.name || '');
      } else if (currentSort === 'state') {
        var s = (a.state || '').localeCompare(b.state || '');
        return s !== 0 ? s : (a.name || '').localeCompare(b.name || '');
      } else if (currentSort === 'programs') {
        return (b.organs || []).length - (a.organs || []).length;
      }
      return 0;
    });
    return filtered;
  }

  function renderBrowseCenters() {
    var filtered = getFilteredCenters();
    browseInfo.textContent = 'Showing ' + filtered.length + ' of ' + allCenters.length + ' centers';
    clearChildren(browseGrid);

    if (filtered.length === 0) {
      var noResults = document.createElement('div');
      noResults.className = 'no-results';
      var icon = document.createElement('div');
      icon.className = 'no-results-icon';
      icon.textContent = '\uD83D\uDD0D';
      noResults.appendChild(icon);
      var msg = document.createElement('p');
      msg.textContent = 'No centers match your search. Try adjusting your filters.';
      noResults.appendChild(msg);
      browseGrid.appendChild(noResults);
      return;
    }

    filtered.forEach(function (center) {
      var card = document.createElement('div');
      card.className = 'center-card';

      var nameEl = document.createElement('div');
      nameEl.className = 'center-card-name';
      nameEl.textContent = center.name || 'Unknown Center';
      card.appendChild(nameEl);

      var locEl = document.createElement('div');
      locEl.className = 'center-card-location';
      var parts = [];
      if (center.city) parts.push(center.city);
      if (center.state) parts.push(center.state);
      else if (center.state_abbr) parts.push(center.state_abbr);
      locEl.textContent = parts.join(', ') || 'Location unavailable';
      card.appendChild(locEl);

      if (center._distance !== undefined && center._distance !== Infinity) {
        var distEl = document.createElement('div');
        distEl.className = 'center-card-distance';
        distEl.textContent = Math.round(center._distance) + ' mi away';
        card.appendChild(distEl);
      }

      var organsEl = document.createElement('div');
      organsEl.className = 'center-card-organs';
      (center.organs || []).forEach(function (organ) {
        var badge = document.createElement('span');
        badge.className = 'organ-badge organ-badge--' + organ;
        badge.textContent = organ;
        organsEl.appendChild(badge);
      });
      card.appendChild(organsEl);

      var link = document.createElement('a');
      link.className = 'center-card-link';
      link.href = 'center.html?code=' + encodeURIComponent(center.code || '');
      link.textContent = 'View Details ';
      var arrow = document.createElement('span');
      arrow.setAttribute('aria-hidden', 'true');
      arrow.textContent = '\u2192';
      link.appendChild(arrow);
      card.appendChild(link);

      browseGrid.appendChild(card);
    });
  }

  // ══════════════════════════════════════════════════════════
  // ── ESTIMATE MODE ──
  // ══════════════════════════════════════════════════════════

  function initEstimateMode() {
    estOrganPills = document.getElementById('est-organ-pills');
    estBloodPills = document.getElementById('est-blood-pills');
    estBtn = document.getElementById('est-btn');
    estResult = document.getElementById('est-result');

    estOrganPills.addEventListener('click', function (e) {
      var p = e.target.closest('.pill');
      if (!p) return;
      estOrganPills.querySelectorAll('.pill').forEach(function (x) { x.classList.remove('active'); });
      p.classList.add('active');
      estOrgan = p.getAttribute('data-organ');
      updateEstBtn();
    });

    estBloodPills.addEventListener('click', function (e) {
      var p = e.target.closest('.pill');
      if (!p) return;
      estBloodPills.querySelectorAll('.pill').forEach(function (x) { x.classList.remove('active'); });
      p.classList.add('active');
      estBlood = p.getAttribute('data-blood');
      updateEstBtn();
    });

    estBtn.addEventListener('click', runEstimate);
  }

  function updateEstBtn() {
    estBtn.disabled = !(estOrgan && estBlood);
  }

  function runEstimate() {
    if (!estOrgan || !estBlood) return;

    var fallbacks = {
      pancreas: { national_median_months: 12, log_sigma: 1.2, blood_type_multipliers: {} },
      intestine: { national_median_months: 6, log_sigma: 1.3, blood_type_multipliers: {} }
    };
    var organData = distData[estOrgan] || fallbacks[estOrgan];
    if (!organData) { estResult.style.display = 'none'; return; }

    var nationalMedian = organData.national_median_months;
    var btMultiplier = (organData.blood_type_multipliers || {})[estBlood] || 1.0;
    var estimatedMedian = nationalMedian * btMultiplier;

    var sigma = organData.log_sigma || 1.2;
    var mu = Math.log(estimatedMedian);
    var p25 = Math.exp(mu - 0.674 * sigma);
    var p75 = Math.exp(mu + 0.674 * sigma);

    renderEstimateResult(estOrgan, estBlood, estimatedMedian, p25, p75, nationalMedian, btMultiplier);
  }

  function renderEstimateResult(organ, blood, median, low, high, natMedian, btMult) {
    estResult.style.display = 'block';
    clearChildren(estResult);

    var card = document.createElement('div');
    card.className = 'est-result-card';

    var organLabel = document.createElement('div');
    organLabel.className = 'est-result-organ';
    organLabel.textContent = capitalize(organ) + ' Transplant \u00b7 Blood Type ' + blood;
    card.appendChild(organLabel);

    var range = document.createElement('div');
    range.className = 'est-result-range';
    range.textContent = formatMonths(low) + ' \u2013 ' + formatMonths(high);
    card.appendChild(range);

    var label = document.createElement('div');
    label.className = 'est-result-label';
    label.textContent = 'Estimated wait time range (25th\u201375th percentile)';
    card.appendChild(label);

    var breakdown = document.createElement('div');
    breakdown.className = 'est-breakdown';
    addBd(breakdown, 'National median', formatMonths(natMedian));
    addBd(breakdown, 'Blood type effect', btMult < 1 ? 'Shorter (' + btMult.toFixed(2) + '\u00d7)' : btMult > 1 ? 'Longer (' + btMult.toFixed(2) + '\u00d7)' : 'Average');
    addBd(breakdown, 'Your estimated median', formatMonths(median));
    addBd(breakdown, 'Range (IQR)', formatMonths(low) + ' \u2013 ' + formatMonths(high));
    card.appendChild(breakdown);

    var note = document.createElement('div');
    note.className = 'est-result-note';
    note.textContent = 'This estimate is based on national SRTR data and does not account for your specific region, medical urgency, sensitization (cPRA), or center-specific factors. For a center-specific estimate with Monte Carlo simulation, use the full Simulator.';
    card.appendChild(note);

    var actions = document.createElement('div');
    actions.className = 'est-result-actions';
    var simLink = document.createElement('a');
    simLink.href = 'simulator.html';
    simLink.textContent = 'Run Full Simulation';
    actions.appendChild(simLink);
    var findLink = document.createElement('a');
    findLink.href = 'centers.html?mode=find';
    findLink.textContent = 'Find Centers Near Me';
    actions.appendChild(findLink);
    card.appendChild(actions);

    estResult.appendChild(card);
    estResult.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  // ══════════════════════════════════════════════════════════
  // ── URL Param Handling ──
  // ══════════════════════════════════════════════════════════

  function parseURLParams() {
    var params = new URLSearchParams(window.location.search);
    var mode = params.get('mode');
    if (mode && ['find', 'browse', 'estimate'].indexOf(mode) !== -1) {
      currentMode = mode;
    }
    return {
      mode: currentMode,
      organ: params.get('organ'),
      zip: params.get('zip'),
      bt: params.get('bt')
    };
  }

  function applyURLParams(urlParams) {
    if (urlParams.organ) {
      if (currentMode === 'find' && findOrganPills) {
        var pill = findOrganPills.querySelector('[data-organ="' + urlParams.organ + '"]');
        if (pill) pill.click();
      } else if (currentMode === 'estimate' && estOrganPills) {
        var pill = estOrganPills.querySelector('[data-organ="' + urlParams.organ + '"]');
        if (pill) pill.click();
      }
    }

    if (urlParams.zip && currentMode === 'find' && findZip) {
      findZip.value = urlParams.zip;
      findZip.dispatchEvent(new Event('input'));
    }

    if (urlParams.bt) {
      if (currentMode === 'find' && findBloodPills) {
        var pill = findBloodPills.querySelector('[data-blood="' + urlParams.bt + '"]');
        if (pill) pill.click();
      } else if (currentMode === 'estimate' && estBloodPills) {
        var pill = estBloodPills.querySelector('[data-blood="' + urlParams.bt + '"]');
        if (pill) pill.click();
      }
    }
  }

  // ══════════════════════════════════════════════════════════
  // ── Init ──
  // ══════════════════════════════════════════════════════════

  function init() {
    var urlParams = parseURLParams();

    tabBtns = Array.from(document.querySelectorAll('.mode-tab'));
    modePanels = Array.from(document.querySelectorAll('.mode-panel'));

    tabBtns.forEach(function (btn) {
      btn.addEventListener('click', function () {
        switchMode(btn.getAttribute('data-mode'));
      });
    });

    initFindMode();
    initBrowseMode();
    initEstimateMode();

    switchMode(currentMode);

    loadAllData().then(function () {
      applyURLParams(urlParams);
      if (currentMode === 'browse') {
        renderBrowseCenters();
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  window.TransPlanCenters = { switchMode: switchMode };
})();
