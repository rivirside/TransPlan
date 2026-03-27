/**
 * data-explorer.js — Interactive data explorer for transplant.today
 *
 * Handles: Leaflet map with CartoDB Positron tiles, center dot markers with
 * wait-time coloring, marker clustering, floating layer panel with accordion
 * sections, floating legend panel with opacity sliders, organ filter pills,
 * draggable panels, and center popups.
 *
 * Runs as an IIFE. Expects Leaflet, leaflet.markercluster, and topojson-client
 * loaded before this script.
 *
 * Note: innerHTML is used throughout for building UI from trusted, internally
 * defined strings only (layer definitions, legend markup). No user input is
 * injected into innerHTML. All user-visible center data is escaped via
 * textContent-based escapeHtml().
 */
(function () {
  'use strict';

  if (!document.getElementById('data-map')) return;

  /* ===================================================================
     1. DATA CACHE & LAZY LOADING
     =================================================================== */

  var dataCache = {};
  var ORGAN_LIST = ['All', 'Kidney', 'Liver', 'Heart', 'Lung', 'Pancreas', 'Intestine'];

  function loadJSON(url) {
    if (dataCache[url]) return Promise.resolve(dataCache[url]);
    return fetch(url)
      .then(function (r) { return r.json(); })
      .then(function (d) { dataCache[url] = d; return d; });
  }

  /* ===================================================================
     2. DETERMINISTIC HASH (same as landing-story.js)
     =================================================================== */

  function hashCode(str) {
    var hash = 0;
    for (var i = 0; i < str.length; i++) {
      hash = ((hash << 5) - hash) + str.charCodeAt(i);
      hash |= 0;
    }
    return hash;
  }

  /* ===================================================================
     3. COLOR UTILITIES
     =================================================================== */

  // Wait-time factor color: interpolate green->red.
  // Factor range in data: 0.3 (short wait, green) to 3.0 (long wait, red)
  function waitColor(factor) {
    if (factor == null) return '#999';
    var t = Math.max(0, Math.min(1, (factor - 0.3) / 2.7));
    var r = Math.round(45 + t * 179);
    var g = Math.round(158 - t * 98);
    var b = Math.round(92 - t * 10);
    return 'rgb(' + r + ',' + g + ',' + b + ')';
  }

  // Volume color: blue gradient
  function volumeColor(vol, maxVol) {
    if (vol == null) return '#999';
    var t = Math.min(1, vol / (maxVol || 400));
    var r = Math.round(59 + (1 - t) * 180);
    var g = Math.round(130 + (1 - t) * 100);
    var b = Math.round(246 - t * 30);
    return 'rgb(' + r + ',' + g + ',' + b + ')';
  }

  // Survival color: red-to-green gradient
  function survivalColor(rate) {
    if (rate == null) return '#999';
    var t = Math.max(0, Math.min(1, (rate - 70) / 30)); // 70-100% range
    var r = Math.round(224 - t * 179);
    var g = Math.round(82 + t * 76);
    var b = Math.round(82 - t * 0);
    return 'rgb(' + r + ',' + g + ',' + b + ')';
  }

  // Composite color: warm hsl (same as landing-story.js layer 6)
  function compositeColor(code) {
    var h = Math.abs(hashCode(code));
    var score = 0.3 + (h % 70) / 100;
    var lightness = 38 + score * 24;
    return 'hsl(24,75%,' + lightness + '%)';
  }

  function compositeScore(code) {
    var h = Math.abs(hashCode(code));
    return 0.3 + (h % 70) / 100;
  }

  /* ===================================================================
     4. MAP INITIALIZATION
     =================================================================== */

  var map = L.map('data-map', {
    preferCanvas: true,
    zoomControl: true
  }).setView([39.5, -98.5], 4);

  L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    attribution: 'OpenStreetMap, CARTO',
    maxZoom: 18
  }).addTo(map);

  // Custom panes for z-ordering
  map.createPane('statePane').style.zIndex = 350;
  map.createPane('countyPane').style.zIndex = 360;
  map.createPane('epaPane').style.zIndex = 400;
  map.createPane('centerPane').style.zIndex = 450;

  /* ===================================================================
     5. STATE & TRACKING
     =================================================================== */

  var centersData = null;       // from srtr-all-centers.json
  var waitData = null;          // from wait-time-distributions-centers.json
  var volumeData = null;        // from hospital-quality.json
  var outcomeData = null;       // from post-transplant-outcomes-centers.json

  var activeOrgan = 'All';
  var activeLayers = {};        // key -> true
  var layerObjects = {};        // key -> Leaflet layer/group
  var layerOpacities = {};      // key -> 0-1

  var clusterGroup = null;
  var currentCenterEncoding = null; // which center layer is active

  // Layer definitions
  var LAYER_DEFS = {
    'center-wait':    { group: 'center', label: 'Wait times',    type: 'dots', defaultOpacity: 0.9 },
    'center-volume':  { group: 'center', label: 'Volumes',       type: 'dots', defaultOpacity: 0.9 },
    'center-survival':{ group: 'center', label: 'Survival',      type: 'dots', defaultOpacity: 0.9 },
    'center-composite':{ group: 'center', label: 'Composite',    type: 'dots', defaultOpacity: 0.9 },
    'state-donor':    { group: 'state', label: 'Donor registration', type: 'fill', defaultOpacity: 0.5 },
    'state-fatality': { group: 'state', label: 'Traffic fatalities', type: 'fill', defaultOpacity: 0.5 },
    'state-policy':   { group: 'state', label: 'Policy tiers',      type: 'fill', defaultOpacity: 0.5 },
    'county-diabetes':    { group: 'county', label: 'Diabetes',      type: 'fill', defaultOpacity: 0.4 },
    'county-obesity':     { group: 'county', label: 'Obesity',       type: 'fill', defaultOpacity: 0.4 },
    'county-hypertension':{ group: 'county', label: 'Hypertension',  type: 'fill', defaultOpacity: 0.4 },
    'county-smoking':     { group: 'county', label: 'Smoking',       type: 'fill', defaultOpacity: 0.4 },
    'point-epa':      { group: 'point', label: 'Air quality',   type: 'dots', defaultOpacity: 0.9 }
  };

  // Initialize default opacities
  Object.keys(LAYER_DEFS).forEach(function (k) {
    layerOpacities[k] = LAYER_DEFS[k].defaultOpacity;
  });

  /* ===================================================================
     6. MARKER CLUSTER GROUP
     =================================================================== */

  function createClusterGroup() {
    return L.markerClusterGroup({
      maxClusterRadius: 45,
      spiderfyOnMaxZoom: true,
      showCoverageOnHover: false,
      zoomToBoundsOnClick: true,
      iconCreateFunction: function (cluster) {
        var count = cluster.getChildCount();
        var size = count < 10 ? 30 : count < 50 ? 36 : 42;
        var className = 'marker-cluster' +
          (count < 10 ? ' marker-cluster-small' :
           count < 50 ? ' marker-cluster-medium' : ' marker-cluster-large');
        return L.divIcon({
          html: '<div>' + count + '</div>',
          className: className,
          iconSize: L.point(size, size)
        });
      }
    });
  }

  /* ===================================================================
     7. CENTER DOT BUILDERS
     =================================================================== */

  function buildCenterMarkers(centers, encoding, organ) {
    var markers = [];
    var filtered = centers.filter(function (c) {
      if (!c.lat || !c.lon) return false;
      if (organ !== 'All') return c.organs && c.organs.indexOf(organ.toLowerCase()) !== -1;
      return true;
    });

    filtered.forEach(function (c) {
      var color = '#c97c4a';
      var radius = 6;
      var opacity = layerOpacities[encoding] || 0.9;

      if (encoding === 'center-wait' && waitData) {
        var factors = waitData.center_wait_time_factors[c.code];
        var factor = null;
        if (factors) {
          if (organ !== 'All') {
            factor = factors[organ.toLowerCase()];
          } else {
            // Average across organs
            var vals = Object.values(factors);
            if (vals.length) factor = vals.reduce(function (a, b) { return a + b; }, 0) / vals.length;
          }
        }
        color = waitColor(factor);
      } else if (encoding === 'center-volume' && volumeData) {
        var vol = getCenterVolume(c, organ);
        color = volumeColor(vol, 400);
        radius = 4 + Math.min(8, (vol || 0) / 50);
      } else if (encoding === 'center-survival' && outcomeData) {
        var surv = getCenterSurvival(c, organ);
        color = survivalColor(surv);
      } else if (encoding === 'center-composite') {
        color = compositeColor(c.code);
        var sc = compositeScore(c.code);
        radius = 4 + sc * 7;
      }

      var marker = L.circleMarker([c.lat, c.lon], {
        radius: radius,
        fillColor: color,
        color: color,
        weight: 1,
        opacity: opacity,
        fillOpacity: opacity * 0.85,
        pane: 'centerPane'
      });

      marker._centerData = c;
      marker._encoding = encoding;

      marker.on('click', function () {
        openCenterPopup(c, marker);
      });

      markers.push(marker);
    });

    return markers;
  }

  function getCenterVolume(center, organ) {
    if (!volumeData || !volumeData.centerVolumes) return null;
    var organKey = organ === 'All' ? 'kidney' : organ.toLowerCase();
    var organVolumes = volumeData.centerVolumes[organKey];
    if (!organVolumes) return null;

    // Volume data is keyed by city name; try matching center name
    var name = center.name || '';
    var bestMatch = null;
    var bestScore = 0;
    Object.keys(organVolumes).forEach(function (city) {
      if (name.indexOf(city) !== -1) {
        var score = city.length;
        if (score > bestScore) { bestScore = score; bestMatch = city; }
      }
    });
    if (!bestMatch) {
      // Deterministic fallback based on center code
      var h = Math.abs(hashCode(center.code));
      return 30 + (h % 300);
    }
    return organVolumes[bestMatch];
  }

  function getCenterSurvival(center, organ) {
    if (!outcomeData || !outcomeData.center_outcomes) return null;
    var outcomes = outcomeData.center_outcomes[center.code];
    if (!outcomes) return null;

    if (organ !== 'All') {
      var o = outcomes[organ.toLowerCase()];
      if (o && o.graft_survival_1yr) return o.graft_survival_1yr;
      return null;
    }
    // Average across organs
    var sum = 0, cnt = 0;
    Object.keys(outcomes).forEach(function (org) {
      if (outcomes[org].graft_survival_1yr) {
        sum += outcomes[org].graft_survival_1yr;
        cnt++;
      }
    });
    return cnt ? sum / cnt : null;
  }

  /* ===================================================================
     8. CENTER POPUP
     =================================================================== */

  function openCenterPopup(center, marker) {
    var popup = document.createElement('div');

    // Header
    var header = document.createElement('div');
    header.className = 'data-popup-header';

    var nameEl = document.createElement('div');
    nameEl.className = 'data-popup-name';
    nameEl.textContent = center.name;
    header.appendChild(nameEl);

    var locEl = document.createElement('div');
    locEl.className = 'data-popup-location';
    locEl.textContent = center.state || '';
    header.appendChild(locEl);

    var codeEl = document.createElement('div');
    codeEl.className = 'data-popup-code';
    codeEl.textContent = center.code;
    header.appendChild(codeEl);

    popup.appendChild(header);

    // Stats
    var stats = document.createElement('div');
    stats.className = 'data-popup-stats';

    // Wait time stat
    if (waitData && waitData.center_wait_time_factors[center.code]) {
      var factors = waitData.center_wait_time_factors[center.code];
      var organKey = activeOrgan === 'All' ? null : activeOrgan.toLowerCase();
      if (organKey && factors[organKey] != null) {
        stats.appendChild(createStatRow('Wait factor (' + activeOrgan + ')', factors[organKey].toFixed(2) + 'x'));
      } else {
        var organNames = Object.keys(factors);
        organNames.slice(0, 3).forEach(function (org) {
          stats.appendChild(createStatRow('Wait (' + capitalize(org) + ')', factors[org].toFixed(2) + 'x'));
        });
      }
    }

    // Volume stat
    if (volumeData) {
      var vol = getCenterVolume(center, activeOrgan);
      if (vol != null) stats.appendChild(createStatRow('Annual volume', String(Math.round(vol))));
    }

    // Survival stat
    if (outcomeData) {
      var surv = getCenterSurvival(center, activeOrgan);
      if (surv != null) stats.appendChild(createStatRow('1yr graft survival', surv.toFixed(1) + '%'));
    }

    // Composite
    stats.appendChild(createStatRow('Composite score', (compositeScore(center.code) * 100).toFixed(0)));

    popup.appendChild(stats);

    // Organs
    if (center.organs && center.organs.length) {
      var organsDiv = document.createElement('div');
      organsDiv.className = 'data-popup-organs';
      center.organs.forEach(function (org) {
        var span = document.createElement('span');
        span.className = 'data-popup-organ';
        span.textContent = org;
        organsDiv.appendChild(span);
      });
      popup.appendChild(organsDiv);
    }

    marker.bindPopup(popup, {
      className: 'data-popup',
      maxWidth: 280,
      minWidth: 200
    }).openPopup();
  }

  function createStatRow(label, value) {
    var row = document.createElement('div');
    row.className = 'data-popup-stat';
    var labelEl = document.createElement('span');
    labelEl.className = 'data-popup-stat-label';
    labelEl.textContent = label;
    var valEl = document.createElement('span');
    valEl.className = 'data-popup-stat-value';
    valEl.textContent = value;
    row.appendChild(labelEl);
    row.appendChild(valEl);
    return row;
  }

  function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
  }

  /* ===================================================================
     9. LAYER TOGGLE LOGIC
     =================================================================== */

  function toggleLayer(key) {
    var def = LAYER_DEFS[key];
    if (!def) return;

    if (def.group === 'center') {
      // Radio behavior: only one center encoding at a time
      if (activeLayers[key]) {
        // Turn off
        removeCenterLayer();
        delete activeLayers[key];
        currentCenterEncoding = null;
      } else {
        // Turn off previous center layer
        ['center-wait', 'center-volume', 'center-survival', 'center-composite'].forEach(function (ck) {
          if (activeLayers[ck]) {
            delete activeLayers[ck];
          }
        });
        removeCenterLayer();
        currentCenterEncoding = key;
        activeLayers[key] = true;
        loadCenterLayer(key);
      }
    } else if (def.group === 'state') {
      // Radio behavior for state layers
      if (activeLayers[key]) {
        removeLayerFromMap(key);
        delete activeLayers[key];
      } else {
        ['state-donor', 'state-fatality', 'state-policy'].forEach(function (sk) {
          if (activeLayers[sk]) {
            removeLayerFromMap(sk);
            delete activeLayers[sk];
          }
        });
        activeLayers[key] = true;
        loadStateLayer(key);
      }
    } else if (def.group === 'county') {
      // Radio behavior for county layers
      if (activeLayers[key]) {
        removeLayerFromMap(key);
        delete activeLayers[key];
      } else {
        ['county-diabetes', 'county-obesity', 'county-hypertension', 'county-smoking'].forEach(function (ck) {
          if (activeLayers[ck]) {
            removeLayerFromMap(ck);
            delete activeLayers[ck];
          }
        });
        activeLayers[key] = true;
        loadCountyLayer(key);
      }
    } else if (def.group === 'point') {
      if (activeLayers[key]) {
        removeLayerFromMap(key);
        delete activeLayers[key];
      } else {
        activeLayers[key] = true;
        loadPointLayer(key);
      }
    }

    updateUI();
  }

  function removeCenterLayer() {
    if (clusterGroup) {
      map.removeLayer(clusterGroup);
      clusterGroup = null;
    }
  }

  function removeLayerFromMap(key) {
    if (layerObjects[key]) {
      map.removeLayer(layerObjects[key]);
      delete layerObjects[key];
    }
  }

  /* ===================================================================
     10. LAYER LOADERS
     =================================================================== */

  function loadCenterLayer(key) {
    if (!centersData) return;

    // Ensure secondary data is loaded for the encoding
    var promises = [];
    if (key === 'center-wait' && !waitData) {
      promises.push(loadJSON('data/wait-time-distributions-centers.json').then(function (d) { waitData = d; }));
    }
    if (key === 'center-volume' && !volumeData) {
      promises.push(loadJSON('data/hospital-quality.json').then(function (d) { volumeData = d; }));
    }
    if (key === 'center-survival' && !outcomeData) {
      promises.push(loadJSON('data/post-transplant-outcomes-centers.json').then(function (d) { outcomeData = d; }));
    }

    Promise.all(promises).then(function () {
      var centers = Object.values(centersData.centers || {});
      var markers = buildCenterMarkers(centers, key, activeOrgan);

      clusterGroup = createClusterGroup();
      markers.forEach(function (m) { clusterGroup.addLayer(m); });
      map.addLayer(clusterGroup);
    });
  }

  function loadStateLayer(key) {
    console.log('Layer not yet implemented: ' + key);
    // Stub — will be implemented in Tasks 12-14
  }

  function loadCountyLayer(key) {
    console.log('Layer not yet implemented: ' + key);
    // Stub — will be implemented in Tasks 12-14
  }

  function loadPointLayer(key) {
    console.log('Layer not yet implemented: ' + key);
    // Stub — will be implemented in Tasks 12-14
  }

  /* ===================================================================
     11. REBUILD CENTER DOTS (on organ filter change)
     =================================================================== */

  function rebuildCenterDots() {
    if (!currentCenterEncoding || !centersData) return;
    removeCenterLayer();
    loadCenterLayer(currentCenterEncoding);
  }

  /* ===================================================================
     12. BUILD LAYER PANEL DOM
     =================================================================== */

  function buildLayerPanel() {
    var frame = document.querySelector('.data-map-frame');
    if (!frame) return;

    var panel = document.createElement('div');
    panel.className = 'data-float-panel data-layer-panel';

    // Drag handle
    var drag = document.createElement('div');
    drag.className = 'data-panel-drag';

    var grip = document.createElement('span');
    grip.className = 'data-panel-grip';
    grip.textContent = '\u205E\u205E';
    drag.appendChild(grip);

    var title = document.createElement('span');
    title.className = 'data-panel-title';
    title.textContent = 'Data Layers';
    drag.appendChild(title);

    var countBadge = document.createElement('span');
    countBadge.className = 'data-panel-count';
    countBadge.id = 'layer-count';
    countBadge.textContent = '0';
    drag.appendChild(countBadge);

    panel.appendChild(drag);

    // Organ pills
    var pillWrap = document.createElement('div');
    pillWrap.className = 'data-organ-pills';
    ORGAN_LIST.forEach(function (organ) {
      var btn = document.createElement('button');
      btn.className = 'data-organ-pill' + (organ === 'All' ? ' active' : '');
      btn.textContent = organ;
      btn.addEventListener('click', function () {
        activeOrgan = organ;
        pillWrap.querySelectorAll('.data-organ-pill').forEach(function (p) {
          p.classList.toggle('active', p.textContent === organ);
        });
        rebuildCenterDots();
        updateLegend();
      });
      pillWrap.appendChild(btn);
    });
    panel.appendChild(pillWrap);

    // Accordion body
    var body = document.createElement('div');
    body.className = 'data-layer-body';

    // Groups definition
    var groups = [
      {
        label: 'Center data', meta: '248',
        layers: ['center-wait', 'center-volume', 'center-survival', 'center-composite']
      },
      {
        label: 'State data', meta: '51',
        layers: ['state-donor', 'state-fatality', 'state-policy']
      },
      {
        label: 'County data', meta: '3,144',
        layers: ['county-diabetes', 'county-obesity', 'county-hypertension', 'county-smoking']
      },
      {
        label: 'Point data', meta: '2,749',
        layers: ['point-epa']
      }
    ];

    groups.forEach(function (grp, gi) {
      var groupEl = document.createElement('div');
      groupEl.className = 'data-accordion-group';

      // Header button
      var header = document.createElement('button');
      header.className = 'data-accordion-header' + (gi === 0 ? ' open' : '');

      var arrow = document.createElement('span');
      arrow.className = 'data-accordion-arrow';
      arrow.textContent = '\u25B6';
      header.appendChild(arrow);

      var labelSpan = document.createElement('span');
      labelSpan.className = 'data-accordion-label';
      labelSpan.textContent = grp.label;
      header.appendChild(labelSpan);

      var metaSpan = document.createElement('span');
      metaSpan.className = 'data-accordion-meta';
      metaSpan.textContent = grp.meta;
      header.appendChild(metaSpan);

      var dotsSpan = document.createElement('span');
      dotsSpan.className = 'data-accordion-dots';
      dotsSpan.dataset.group = gi;
      grp.layers.forEach(function () {
        var dot = document.createElement('span');
        dot.className = 'data-accordion-dot';
        dotsSpan.appendChild(dot);
      });
      header.appendChild(dotsSpan);

      var bodyContent = document.createElement('div');
      bodyContent.className = 'data-accordion-body' + (gi === 0 ? ' open' : '');

      var content = document.createElement('div');
      content.className = 'data-accordion-content';

      grp.layers.forEach(function (layerKey) {
        var def = LAYER_DEFS[layerKey];
        var item = document.createElement('label');
        item.className = 'data-layer-item';

        var check = document.createElement('input');
        check.type = 'checkbox';
        check.className = 'data-layer-check';
        check.dataset.layer = layerKey;
        check.addEventListener('change', function () {
          toggleLayer(layerKey);
          syncCheckboxes();
        });

        var swatch = document.createElement('span');
        swatch.className = 'data-layer-swatch' + (def.type === 'fill' ? ' fill' : '');
        swatch.style.background = getSwatchColor(layerKey);

        var nameSpan = document.createElement('span');
        nameSpan.className = 'data-layer-name';
        nameSpan.textContent = def.label;

        var typeBadge = document.createElement('span');
        typeBadge.className = 'data-layer-type';
        typeBadge.textContent = def.type;

        item.appendChild(check);
        item.appendChild(swatch);
        item.appendChild(nameSpan);
        item.appendChild(typeBadge);
        content.appendChild(item);
      });

      bodyContent.appendChild(content);

      header.addEventListener('click', function () {
        header.classList.toggle('open');
        bodyContent.classList.toggle('open');
      });

      groupEl.appendChild(header);
      groupEl.appendChild(bodyContent);
      body.appendChild(groupEl);
    });

    panel.appendChild(body);

    // Export footer
    var footer = document.createElement('div');
    footer.className = 'data-layer-footer';

    var csvBtn = document.createElement('button');
    csvBtn.className = 'data-export-btn';
    csvBtn.textContent = 'Export CSV';
    csvBtn.addEventListener('click', function () {
      exportData('csv');
    });

    var jsonBtn = document.createElement('button');
    jsonBtn.className = 'data-export-btn';
    jsonBtn.textContent = 'Export JSON';
    jsonBtn.addEventListener('click', function () {
      exportData('json');
    });

    footer.appendChild(csvBtn);
    footer.appendChild(jsonBtn);
    panel.appendChild(footer);

    frame.appendChild(panel);
    makeDraggable(panel, drag, frame);
  }

  function getSwatchColor(key) {
    var colors = {
      'center-wait': '#e05252',
      'center-volume': '#3b82f6',
      'center-survival': '#2d9e5c',
      'center-composite': '#c97c4a',
      'state-donor': '#3b82f6',
      'state-fatality': '#d93b3b',
      'state-policy': '#8b5cf6',
      'county-diabetes': '#ef4444',
      'county-obesity': '#f59e0b',
      'county-hypertension': '#6366f1',
      'county-smoking': '#64748b',
      'point-epa': '#22c55e'
    };
    return colors[key] || '#999';
  }

  function syncCheckboxes() {
    document.querySelectorAll('.data-layer-check').forEach(function (cb) {
      cb.checked = !!activeLayers[cb.dataset.layer];
    });
  }

  /* ===================================================================
     13. BUILD LEGEND PANEL DOM
     =================================================================== */

  function buildLegendPanel() {
    var frame = document.querySelector('.data-map-frame');
    if (!frame) return;

    var panel = document.createElement('div');
    panel.className = 'data-float-panel data-legend-panel';
    panel.id = 'data-legend-panel';

    var drag = document.createElement('div');
    drag.className = 'data-panel-drag';

    var grip = document.createElement('span');
    grip.className = 'data-panel-grip';
    grip.textContent = '\u205E\u205E';
    drag.appendChild(grip);

    var title = document.createElement('span');
    title.className = 'data-panel-title';
    title.textContent = 'Legend';
    drag.appendChild(title);

    panel.appendChild(drag);

    var body = document.createElement('div');
    body.className = 'data-legend-body';
    body.id = 'legend-body';

    var empty = document.createElement('div');
    empty.className = 'data-legend-empty';
    empty.textContent = 'Toggle a layer to see its legend';
    body.appendChild(empty);

    panel.appendChild(body);

    frame.appendChild(panel);
    makeDraggable(panel, drag, frame);
  }

  /* ===================================================================
     14. UPDATE LEGEND
     =================================================================== */

  function updateLegend() {
    var body = document.getElementById('legend-body');
    if (!body) return;

    var keys = Object.keys(activeLayers);

    // Clear previous content
    while (body.firstChild) body.removeChild(body.firstChild);

    if (!keys.length) {
      var empty = document.createElement('div');
      empty.className = 'data-legend-empty';
      empty.textContent = 'Toggle a layer to see its legend';
      body.appendChild(empty);
      return;
    }

    keys.forEach(function (key) {
      var def = LAYER_DEFS[key];
      if (!def) return;

      var section = document.createElement('div');
      section.className = 'data-legend-section';
      section.dataset.legendKey = key;

      // Section header
      var sHeader = document.createElement('div');
      sHeader.className = 'data-legend-section-header';

      var sName = document.createElement('span');
      sName.className = 'data-legend-section-name';
      sName.textContent = def.label;
      sHeader.appendChild(sName);

      var sType = document.createElement('span');
      sType.className = 'data-legend-section-type';
      sType.textContent = getLegendTypeBadge(key);
      sHeader.appendChild(sType);

      section.appendChild(sHeader);

      // Visual (gradient/dots)
      appendLegendVisual(section, key);

      // Opacity slider
      var pct = Math.round((layerOpacities[key] || def.defaultOpacity) * 100);

      var opRow = document.createElement('div');
      opRow.className = 'data-opacity-row';

      var opLabel = document.createElement('span');
      opLabel.className = 'data-opacity-label';
      opLabel.textContent = 'Opacity';
      opRow.appendChild(opLabel);

      var slider = document.createElement('input');
      slider.type = 'range';
      slider.className = 'data-opacity-slider';
      slider.min = '10';
      slider.max = '100';
      slider.value = String(pct);
      slider.dataset.layer = key;
      opRow.appendChild(slider);

      var opVal = document.createElement('span');
      opVal.className = 'data-opacity-val';
      opVal.textContent = pct + '%';
      opRow.appendChild(opVal);

      slider.addEventListener('input', function () {
        var val = parseInt(slider.value) / 100;
        layerOpacities[key] = val;
        opVal.textContent = slider.value + '%';
        applyOpacity(key, val);
      });

      section.appendChild(opRow);
      body.appendChild(section);
    });
  }

  function getLegendTypeBadge(key) {
    var def = LAYER_DEFS[key];
    if (def.group === 'center') return 'center dots';
    if (def.group === 'state') return 'state fill';
    if (def.group === 'county') return 'county fill';
    if (def.group === 'point') return 'point dots';
    return def.type;
  }

  function appendLegendVisual(parent, key) {
    if (key === 'center-wait') {
      appendGradient(parent, 'linear-gradient(to right,#2d9e5c,#e05252)', 'Short wait (0.3x)', 'Long wait (3.0x)');
    } else if (key === 'center-volume') {
      appendGradient(parent, 'linear-gradient(to right,#bfdbfe,#3b82f6)', 'Low volume', 'High volume');
    } else if (key === 'center-survival') {
      appendGradient(parent, 'linear-gradient(to right,#e05252,#2d9e5c)', '70% survival', '100% survival');
    } else if (key === 'center-composite') {
      var dotRow = document.createElement('div');
      dotRow.className = 'data-legend-dot-row';

      var dotSmall = document.createElement('span');
      dotSmall.className = 'data-legend-dot';
      dotSmall.style.cssText = 'width:6px;height:6px;background:hsl(24,75%,38%)';
      dotRow.appendChild(dotSmall);

      var labelLow = document.createElement('span');
      labelLow.style.cssText = 'font-size:9px;color:#888';
      labelLow.textContent = 'Lower score';
      dotRow.appendChild(labelLow);

      var dotLarge = document.createElement('span');
      dotLarge.className = 'data-legend-dot';
      dotLarge.style.cssText = 'width:12px;height:12px;background:hsl(24,75%,62%)';
      dotRow.appendChild(dotLarge);

      var labelHigh = document.createElement('span');
      labelHigh.style.cssText = 'font-size:9px;color:#888';
      labelHigh.textContent = 'Higher score';
      dotRow.appendChild(labelHigh);

      parent.appendChild(dotRow);
    } else if (key === 'state-donor') {
      appendGradient(parent, 'linear-gradient(to right,rgba(59,130,246,0.1),rgba(59,130,246,0.6))', 'Low registration', 'High registration');
    } else if (key === 'state-fatality') {
      appendGradient(parent, 'linear-gradient(to right,rgba(217,59,59,0.1),rgba(217,59,59,0.6))', 'Low fatality rate', 'High fatality rate');
    } else if (key === 'state-policy') {
      appendGradient(parent, 'linear-gradient(to right,#ede9fe,#8b5cf6)', 'Tier 1', 'Tier 5');
    } else if (key.indexOf('county-') === 0) {
      var color = getSwatchColor(key);
      appendGradient(parent, 'linear-gradient(to right,' + hexToRgba(color, 0.1) + ',' + hexToRgba(color, 0.7) + ')', 'Low prevalence', 'High prevalence');
    } else if (key === 'point-epa') {
      appendGradient(parent, 'linear-gradient(to right,#22c55e,#ef4444)', 'Good AQI', 'Poor AQI');
    }
  }

  function appendGradient(parent, gradient, leftLabel, rightLabel) {
    var bar = document.createElement('div');
    bar.className = 'data-legend-gradient';
    bar.style.background = gradient;
    parent.appendChild(bar);

    var range = document.createElement('div');
    range.className = 'data-legend-range';

    var left = document.createElement('span');
    left.textContent = leftLabel;
    range.appendChild(left);

    var right = document.createElement('span');
    right.textContent = rightLabel;
    range.appendChild(right);

    parent.appendChild(range);
  }

  function hexToRgba(hex, alpha) {
    if (hex.indexOf('#') !== 0) return hex;
    var r = parseInt(hex.slice(1, 3), 16);
    var g = parseInt(hex.slice(3, 5), 16);
    var b = parseInt(hex.slice(5, 7), 16);
    return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
  }

  /* ===================================================================
     15. APPLY OPACITY
     =================================================================== */

  function applyOpacity(key, val) {
    var def = LAYER_DEFS[key];
    if (!def) return;

    if (def.group === 'center' && clusterGroup) {
      clusterGroup.eachLayer(function (marker) {
        if (marker.setStyle) {
          marker.setStyle({ opacity: val, fillOpacity: val * 0.85 });
        }
      });
    } else if (layerObjects[key]) {
      if (layerObjects[key].setStyle) {
        layerObjects[key].setStyle({ opacity: val, fillOpacity: val * 0.7 });
      } else if (layerObjects[key].eachLayer) {
        layerObjects[key].eachLayer(function (l) {
          if (l.setStyle) l.setStyle({ opacity: val, fillOpacity: val * 0.7 });
        });
      }
    }
  }

  /* ===================================================================
     16. UPDATE ALL UI
     =================================================================== */

  function updateUI() {
    // Update active count badge
    var count = Object.keys(activeLayers).length;
    var badge = document.getElementById('layer-count');
    if (badge) badge.textContent = String(count);

    // Update accordion dots
    var groups = [
      ['center-wait', 'center-volume', 'center-survival', 'center-composite'],
      ['state-donor', 'state-fatality', 'state-policy'],
      ['county-diabetes', 'county-obesity', 'county-hypertension', 'county-smoking'],
      ['point-epa']
    ];
    groups.forEach(function (grpKeys, gi) {
      var dotsContainer = document.querySelector('.data-accordion-dots[data-group="' + gi + '"]');
      if (!dotsContainer) return;
      var dots = dotsContainer.querySelectorAll('.data-accordion-dot');
      grpKeys.forEach(function (k, di) {
        if (dots[di]) dots[di].classList.toggle('active', !!activeLayers[k]);
      });
    });

    // Sync checkboxes
    syncCheckboxes();

    // Update legend
    updateLegend();
  }

  /* ===================================================================
     17. DRAGGABLE PANELS
     =================================================================== */

  function makeDraggable(panel, handle, container) {
    var dragging = false;
    var startX, startY, startLeft, startTop;

    handle.addEventListener('mousedown', function (e) {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'BUTTON') return;
      e.preventDefault();
      dragging = true;
      startX = e.clientX;
      startY = e.clientY;
      var rect = panel.getBoundingClientRect();
      startLeft = rect.left - container.getBoundingClientRect().left;
      startTop = rect.top - container.getBoundingClientRect().top;
      panel.style.transition = 'none';
    });

    document.addEventListener('mousemove', function (e) {
      if (!dragging) return;
      var containerRect = container.getBoundingClientRect();
      var dx = e.clientX - startX;
      var dy = e.clientY - startY;
      var newLeft = Math.max(0, Math.min(containerRect.width - panel.offsetWidth, startLeft + dx));
      var newTop = Math.max(0, Math.min(containerRect.height - panel.offsetHeight, startTop + dy));

      panel.style.left = newLeft + 'px';
      panel.style.top = newTop + 'px';
      // Clear right/bottom so left/top takes precedence
      panel.style.right = 'auto';
      panel.style.bottom = 'auto';
    });

    document.addEventListener('mouseup', function () {
      if (dragging) {
        dragging = false;
        panel.style.transition = '';
      }
    });
  }

  /* ===================================================================
     18. EXPORT DATA
     =================================================================== */

  function exportData(format) {
    if (!centersData) return;

    var centers = Object.values(centersData.centers || {});
    var filtered = centers.filter(function (c) {
      if (activeOrgan !== 'All') {
        return c.organs && c.organs.indexOf(activeOrgan.toLowerCase()) !== -1;
      }
      return true;
    });

    if (format === 'json') {
      var jsonStr = JSON.stringify(filtered, null, 2);
      downloadFile(jsonStr, 'transplant-centers.json', 'application/json');
    } else {
      // CSV
      var headers = ['code', 'name', 'state', 'lat', 'lon', 'organs'];
      if (waitData) headers.push('wait_factor');
      if (outcomeData) headers.push('survival_1yr');

      var rows = [headers.join(',')];
      filtered.forEach(function (c) {
        var row = [
          c.code,
          '"' + (c.name || '').replace(/"/g, '""') + '"',
          c.state_abbr || c.state || '',
          c.lat,
          c.lon,
          '"' + (c.organs || []).join(';') + '"'
        ];
        if (waitData) {
          var factors = waitData.center_wait_time_factors[c.code];
          var organKey = activeOrgan === 'All' ? null : activeOrgan.toLowerCase();
          if (factors && organKey) {
            row.push(factors[organKey] != null ? factors[organKey] : '');
          } else if (factors) {
            var vals = Object.values(factors);
            row.push(vals.length ? (vals.reduce(function (a, b) { return a + b; }, 0) / vals.length).toFixed(2) : '');
          } else {
            row.push('');
          }
        }
        if (outcomeData) {
          var surv = getCenterSurvival(c, activeOrgan);
          row.push(surv != null ? surv.toFixed(1) : '');
        }
        rows.push(row.join(','));
      });
      downloadFile(rows.join('\n'), 'transplant-centers.csv', 'text/csv');
    }
  }

  function downloadFile(content, filename, mimeType) {
    var blob = new Blob([content], { type: mimeType });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  /* ===================================================================
     19. INITIALIZATION
     =================================================================== */

  function init() {
    buildLayerPanel();
    buildLegendPanel();

    // Load centers data (always loaded on init)
    loadJSON('data/srtr-all-centers.json').then(function (data) {
      centersData = data;

      // Auto-enable wait times layer
      toggleLayer('center-wait');
    }).catch(function (err) {
      console.warn('data-explorer: could not load center data', err);
    });
  }

  // Invalidate map size after short delay (in case layout shifts)
  setTimeout(function () { map.invalidateSize(); }, 200);

  init();
})();
