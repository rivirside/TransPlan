/**
 * explorer/spatial-analysis.js — Spatial Analysis tab module.
 *
 * Renders an interpolated heatmap (RBF/IDW) of transplant data layers,
 * click-to-inspect, allocation circles, and distance scoring.
 *
 * Extracted from the inline script in spatial.html and converted to an
 * IIFE module that exposes window.TransPlanSpatial = { init }.
 *
 * Expected element IDs (same as original spatial.html):
 *   sidebar, sidebarToggle, layerSelect, organFilter,
 *   resolutionSlider, resolutionValue, loadBtn, allocCheck,
 *   scoreCard, inspectPanel, inspectClose, mapLoading,
 *   sidebarStatus, tierBadge, tierCaps, spatial-map
 */
(function () {
  'use strict';

  // ── API base ────────────────────────────────────────────────────────────────
  function getApiBase() {
    return (window.TransPlanAPI && window.TransPlanAPI.getBaseUrl)
      ? window.TransPlanAPI.getBaseUrl()
      : '';
  }

  // ── State ───────────────────────────────────────────────────────────────────
  var map = null;
  var heatLayer = null;
  var allocCircles = [];
  var centerMarkers = [];
  var selectedLayer = '';
  var selectedMethod = 'rbf';
  var resolution = 30;
  var maxResolution = 100;
  var tierConfig = null;

  // DOM refs — populated during init()
  var sidebar, sidebarToggle, layerSelect, organFilter;
  var resSlider, resValue, loadBtn, allocCheck;
  var scoreCard, inspectPanel, inspectClose, mapLoading;
  var sidebarStatus, tierBadge, tierCaps;

  // ── DOM helpers ─────────────────────────────────────────────────────────────

  function el(id) {
    return document.getElementById(id);
  }

  /** Safely clear all children of a DOM node. */
  function clearChildren(node) {
    while (node.firstChild) node.removeChild(node.firstChild);
  }

  // ── Initialize map ──────────────────────────────────────────────────────────

  function initMap() {
    if (typeof L === 'undefined') {
      setStatus('Leaflet library failed to load. Check your connection.', true);
      return;
    }

    map = L.map('spatial-map', {
      zoomControl: true
    }).setView([39.8, -98.5], 4);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: 'OpenStreetMap',
      maxZoom: 18
    }).addTo(map);

    // Click-to-inspect
    map.on('click', onMapClick);
  }

  // ── Sidebar toggle ──────────────────────────────────────────────────────────

  function bindSidebarToggle() {
    sidebarToggle.addEventListener('click', function () {
      var isCollapsed = sidebar.classList.toggle('collapsed');
      sidebarToggle.textContent = isCollapsed ? '\u25B6' : '\u25C0';
      // Invalidate map size after sidebar animation
      setTimeout(function () {
        if (map) map.invalidateSize();
      }, 300);
    });
  }

  // ── Load layers ─────────────────────────────────────────────────────────────

  function loadLayers() {
    var apiBase = getApiBase();
    fetch(apiBase + '/spatial-layers')
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) {
        var layers = data.layers || [];
        populateLayerSelect(layers);
        loadBtn.disabled = false;
        setStatus('');
      })
      .catch(function () {
        setStatus('Could not load layers. Is the backend running?', true);
        // Populate with known defaults so page is still usable
        populateLayerSelect(getDefaultLayers());
        loadBtn.disabled = false;
      });
  }

  function getDefaultLayers() {
    return [
      'air_quality', 'cost_of_living',
      'health_diabetesRate', 'health_obesityRate', 'health_smokingRate',
      'health_ckdRate', 'health_hypertensionRate',
      'wait_time_factor_kidney', 'mortality_factor_kidney', 'graft_survival_kidney',
      'wait_time_factor_liver', 'mortality_factor_liver', 'graft_survival_liver',
      'wait_time_factor_heart', 'mortality_factor_heart', 'graft_survival_heart',
      'wait_time_factor_lung', 'mortality_factor_lung', 'graft_survival_lung'
    ];
  }

  function populateLayerSelect(layers) {
    clearChildren(layerSelect);

    // Group layers
    var groups = {
      'General': [],
      'Health': [],
      'Kidney': [],
      'Liver': [],
      'Heart': [],
      'Lung': [],
      'Pancreas': [],
      'Intestine': [],
      'Other': []
    };

    layers.forEach(function (name) {
      if (name === 'air_quality' || name === 'cost_of_living') {
        groups['General'].push(name);
      } else if (name.indexOf('health_') === 0) {
        groups['Health'].push(name);
      } else if (name.indexOf('kidney') !== -1) {
        groups['Kidney'].push(name);
      } else if (name.indexOf('liver') !== -1) {
        groups['Liver'].push(name);
      } else if (name.indexOf('heart') !== -1) {
        groups['Heart'].push(name);
      } else if (name.indexOf('lung') !== -1) {
        groups['Lung'].push(name);
      } else if (name.indexOf('pancreas') !== -1) {
        groups['Pancreas'].push(name);
      } else if (name.indexOf('intestine') !== -1) {
        groups['Intestine'].push(name);
      } else {
        groups['Other'].push(name);
      }
    });

    var first = true;
    Object.keys(groups).forEach(function (groupName) {
      var items = groups[groupName];
      if (items.length === 0) return;

      var optgroup = document.createElement('optgroup');
      optgroup.label = groupName;

      items.forEach(function (layerName) {
        var opt = document.createElement('option');
        opt.value = layerName;
        opt.textContent = formatLayerName(layerName);
        if (first) {
          opt.selected = true;
          selectedLayer = layerName;
          first = false;
        }
        optgroup.appendChild(opt);
      });

      layerSelect.appendChild(optgroup);
    });
  }

  function formatLayerName(name) {
    // Convert snake_case to readable
    return name
      .replace(/_/g, ' ')
      .replace(/\b\w/g, function (c) { return c.toUpperCase(); })
      .replace(/Ckd/g, 'CKD');
  }

  // ── Organ filter ────────────────────────────────────────────────────────────

  function bindOrganFilter() {
    organFilter.addEventListener('change', function () {
      // When organ changes, update the layer dropdown to show matching organ layers
      var organ = organFilter.value;
      var opts = layerSelect.querySelectorAll('option');
      // Auto-select the wait_time_factor layer for the new organ if current is organ-specific
      if (selectedLayer && (selectedLayer.indexOf('_kidney') !== -1 ||
          selectedLayer.indexOf('_liver') !== -1 ||
          selectedLayer.indexOf('_heart') !== -1 ||
          selectedLayer.indexOf('_lung') !== -1 ||
          selectedLayer.indexOf('_pancreas') !== -1 ||
          selectedLayer.indexOf('_intestine') !== -1)) {
        var base = selectedLayer.replace(/_kidney|_liver|_heart|_lung|_pancreas|_intestine/g, '');
        var target = base + '_' + organ;
        for (var i = 0; i < opts.length; i++) {
          if (opts[i].value === target) {
            layerSelect.value = target;
            selectedLayer = target;
            break;
          }
        }
      }
    });
  }

  // ── Layer select ────────────────────────────────────────────────────────────

  function bindLayerSelect() {
    layerSelect.addEventListener('change', function () {
      selectedLayer = layerSelect.value;
    });
  }

  // ── Method toggles ──────────────────────────────────────────────────────────

  function bindMethodToggles() {
    var methodBtns = document.querySelectorAll('.method-btn');
    methodBtns.forEach(function (btn) {
      btn.addEventListener('click', function () {
        methodBtns.forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
        selectedMethod = btn.getAttribute('data-method');
      });
    });
  }

  // ── Resolution slider ───────────────────────────────────────────────────────

  function bindResolutionSlider() {
    resSlider.addEventListener('input', function () {
      resolution = parseInt(resSlider.value, 10);
      resValue.textContent = resolution;
    });
  }

  // ── Load heatmap ────────────────────────────────────────────────────────────

  function bindLoadButton() {
    loadBtn.addEventListener('click', loadHeatmap);
  }

  function loadHeatmap() {
    if (!selectedLayer) {
      setStatus('Please select a layer.', true);
      return;
    }

    loadBtn.disabled = true;
    mapLoading.classList.add('visible');
    setStatus('');

    var apiBase = getApiBase();
    var url = apiBase + '/spatial-grid?layer=' + encodeURIComponent(selectedLayer) +
      '&resolution=' + resolution +
      '&method=' + encodeURIComponent(selectedMethod);

    fetch(url)
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) {
        // Remove old heat layer
        if (heatLayer) {
          map.removeLayer(heatLayer);
          heatLayer = null;
        }

        var points = data.points || [];
        if (points.length === 0) {
          setStatus('No data points returned for this layer.', true);
          return;
        }

        heatLayer = L.heatLayer(points, {
          radius: 25,
          blur: 15,
          maxZoom: 10,
          max: 1.0,
          gradient: {
            0.0: '#f7e8d0',
            0.25: '#f0cdb0',
            0.5: '#d6925e',
            0.75: '#c97c4a',
            1.0: '#7d4b2d'
          }
        }).addTo(map);

        var range = data.value_range || {};
        setStatus(formatLayerName(selectedLayer) + ' loaded. Range: ' +
          (range.min !== undefined ? range.min.toFixed(1) : '?') + ' \u2013 ' +
          (range.max !== undefined ? range.max.toFixed(1) : '?'));
      })
      .catch(function (err) {
        setStatus('Failed to load heatmap: ' + err.message, true);
      })
      .finally(function () {
        loadBtn.disabled = false;
        mapLoading.classList.remove('visible');
      });
  }

  // ── Click-to-inspect ────────────────────────────────────────────────────────

  function onMapClick(e) {
    var lat = e.latlng.lat;
    var lon = e.latlng.lng;

    // Bounds check for CONUS
    if (lat < 24 || lat > 50 || lon < -125 || lon > -66) return;

    if (!selectedLayer) return;

    var apiBase = getApiBase();
    var url = apiBase + '/interpolated-value?lat=' + lat.toFixed(4) +
      '&lon=' + lon.toFixed(4) +
      '&layer=' + encodeURIComponent(selectedLayer) +
      '&method=' + encodeURIComponent(selectedMethod);

    fetch(url)
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) {
        showInspectPanel(data, lat, lon);

        // Show popup on map using safe DOM construction
        var stats = data.stats || {};
        var popupEl = document.createElement('div');

        var title = document.createElement('strong');
        title.textContent = formatLayerName(data.layer || selectedLayer);
        popupEl.appendChild(title);

        popupEl.appendChild(document.createElement('br'));

        var valText = document.createTextNode(
          'Value: ' + (data.value !== undefined ? data.value.toFixed(3) : 'N/A')
        );
        popupEl.appendChild(valText);

        popupEl.appendChild(document.createElement('br'));

        var rangeText = document.createTextNode(
          'Range: ' + (stats.min !== undefined ? stats.min.toFixed(1) : '?') +
          ' \u2013 ' + (stats.max !== undefined ? stats.max.toFixed(1) : '?')
        );
        popupEl.appendChild(rangeText);

        L.popup()
          .setLatLng(e.latlng)
          .setContent(popupEl)
          .openOn(map);

        // If allocation circles checked, draw them
        if (allocCheck.checked) {
          loadAllocationCircles(lat, lon);
        }

        // Load distance score
        loadDistanceScore(lat, lon);
      })
      .catch(function () {
        // Silently fail — user clicked outside data range
      });
  }

  function showInspectPanel(data, lat, lon) {
    var stats = data.stats || {};
    el('inspectLayer').textContent = formatLayerName(data.layer || selectedLayer);
    el('inspectCoords').textContent = lat.toFixed(4) + ', ' + lon.toFixed(4);
    el('inspectValue').textContent = data.value !== undefined ? data.value.toFixed(3) : 'N/A';

    var statsEl = el('inspectStats');
    clearChildren(statsEl);
    statsEl.appendChild(document.createTextNode(
      'Min: ' + (stats.min !== undefined ? stats.min.toFixed(2) : '?') +
      ' \u00B7 Max: ' + (stats.max !== undefined ? stats.max.toFixed(2) : '?') +
      ' \u00B7 Mean: ' + (stats.mean !== undefined ? stats.mean.toFixed(2) : '?') +
      ' \u00B7 Std: ' + (stats.std !== undefined ? stats.std.toFixed(2) : '?')
    ));

    inspectPanel.classList.add('visible');
  }

  function bindInspectClose() {
    inspectClose.addEventListener('click', function () {
      inspectPanel.classList.remove('visible');
    });
  }

  // ── Allocation circles ──────────────────────────────────────────────────────

  function clearAllocCircles() {
    allocCircles.forEach(function (c) {
      map.removeLayer(c);
    });
    allocCircles = [];
  }

  function loadAllocationCircles(lat, lon) {
    clearAllocCircles();

    var apiBase = getApiBase();
    var organ = organFilter.value;
    var url = apiBase + '/allocation-circles?lat=' + lat.toFixed(4) +
      '&lon=' + lon.toFixed(4) +
      '&organ=' + encodeURIComponent(organ);

    fetch(url)
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) {
        // 250nm circle (~463km)
        var circle250 = L.circle([lat, lon], {
          radius: 463000,
          color: '#c97c4a',
          fill: false,
          weight: 2,
          opacity: 0.8
        }).addTo(map);

        var count250 = (data.circles_250nm || {}).center_count || 0;
        circle250.bindTooltip('250nm: ' + count250 + ' centers', { permanent: false });
        allocCircles.push(circle250);

        // 500nm circle (~926km)
        var circle500 = L.circle([lat, lon], {
          radius: 926000,
          color: '#c97c4a',
          fill: false,
          weight: 1,
          opacity: 0.6,
          dashArray: '5,5'
        }).addTo(map);

        var count500 = (data.circles_500nm || {}).center_count || 0;
        circle500.bindTooltip('500nm: ' + count500 + ' centers', { permanent: false });
        allocCircles.push(circle500);

        // Add markers for centers within circles
        var centers250 = (data.circles_250nm || {}).centers || [];
        var centers500 = (data.circles_500nm || {}).centers || [];
        var allCenters = centers250.concat(centers500);

        // Remove old center markers
        centerMarkers.forEach(function (m) { map.removeLayer(m); });
        centerMarkers = [];

        var seen = {};
        allCenters.forEach(function (c) {
          var key = c.lat + ',' + c.lon;
          if (seen[key]) return;
          seen[key] = true;

          if (c.lat && c.lon) {
            var marker = L.circleMarker([c.lat, c.lon], {
              radius: 5,
              fillColor: '#c97c4a',
              color: '#7d4b2d',
              weight: 1,
              fillOpacity: 0.8
            }).addTo(map);

            var name = c.name || c.code || 'Center';
            marker.bindPopup(name);
            centerMarkers.push(marker);
          }
        });
      })
      .catch(function (err) {
        setStatus('Allocation circles: ' + err.message, true);
      });
  }

  // ── Distance score ──────────────────────────────────────────────────────────

  function loadDistanceScore(lat, lon) {
    var apiBase = getApiBase();
    var organ = organFilter.value;
    var url = apiBase + '/distance-score?lat=' + lat.toFixed(4) +
      '&lon=' + lon.toFixed(4) +
      '&organ=' + encodeURIComponent(organ);

    fetch(url)
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) {
        el('scoreComposite').textContent =
          data.composite_score !== undefined ? data.composite_score.toFixed(1) : '--';
        el('scoreProximity').textContent =
          data.proximity_score !== undefined ? data.proximity_score.toFixed(1) : '--';
        el('scoreCompetition').textContent =
          data.competition_score !== undefined ? data.competition_score.toFixed(1) : '--';
        el('scoreDonorPool').textContent =
          data.donor_pool_score !== undefined ? data.donor_pool_score.toFixed(1) : '--';
        scoreCard.classList.add('visible');
      })
      .catch(function () {
        scoreCard.classList.remove('visible');
      });
  }

  // ── Allocation checkbox ─────────────────────────────────────────────────────

  function bindAllocCheckbox() {
    allocCheck.addEventListener('change', function () {
      if (!allocCheck.checked) {
        clearAllocCircles();
        centerMarkers.forEach(function (m) { map.removeLayer(m); });
        centerMarkers = [];
      }
    });
  }

  // ── Tier config ─────────────────────────────────────────────────────────────

  function fetchTierConfig() {
    var apiBase = getApiBase();
    fetch(apiBase + '/tier')
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        tierConfig = data || defaultWebTier();
        applyTierCaps();
      })
      .catch(function () {
        tierConfig = defaultWebTier();
        applyTierCaps();
      });
  }

  function defaultWebTier() {
    return {
      name: 'web',
      caps: {
        max_spatial_resolution: 30
      }
    };
  }

  function applyTierCaps() {
    if (!tierConfig) return;
    var caps = tierConfig.caps || {};

    // Badge
    tierBadge.textContent = tierConfig.name === 'local' ? 'Local' : 'Web';
    tierBadge.className = 'tier-badge tier-' + tierConfig.name;

    // Cap resolution
    maxResolution = caps.max_spatial_resolution || 100;
    resSlider.max = maxResolution;
    if (resolution > maxResolution) {
      resolution = maxResolution;
      resSlider.value = resolution;
      resValue.textContent = resolution;
    }

    tierCaps.textContent = 'Max resolution: ' + maxResolution;
  }

  // ── Status ──────────────────────────────────────────────────────────────────

  function setStatus(msg, isError) {
    sidebarStatus.textContent = msg;
    if (isError) {
      sidebarStatus.classList.add('error');
    } else {
      sidebarStatus.classList.remove('error');
    }
  }

  // ── Public init ─────────────────────────────────────────────────────────────

  function init() {
    // Guard: only run if the spatial map container exists
    if (!document.getElementById('spatial-map')) return;

    // Populate DOM refs
    sidebar       = el('sidebar');
    sidebarToggle = el('sidebarToggle');
    layerSelect   = el('layerSelect');
    organFilter   = el('organFilter');
    resSlider     = el('resolutionSlider');
    resValue      = el('resolutionValue');
    loadBtn       = el('loadBtn');
    allocCheck    = el('allocCheck');
    scoreCard     = el('scoreCard');
    inspectPanel  = el('inspectPanel');
    inspectClose  = el('inspectClose');
    mapLoading    = el('mapLoading');
    sidebarStatus = el('sidebarStatus');
    tierBadge     = el('tierBadge');
    tierCaps      = el('tierCaps');

    // Bind event listeners
    bindSidebarToggle();
    bindOrganFilter();
    bindLayerSelect();
    bindMethodToggles();
    bindResolutionSlider();
    bindLoadButton();
    bindInspectClose();
    bindAllocCheckbox();

    // Bootstrap
    initMap();
    loadLayers();
    fetchTierConfig();
  }

  // ── Export ───────────────────────────────────────────────────────────────────

  window.TransPlanSpatial = { init: init };
})();
