(function() {
  'use strict';

  if (!document.getElementById('story-map')) return;

  fetch('data/srtr-all-centers.json')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      var centers = Object.values(data.centers || {});
      centers = centers.filter(function(c) { return c.lat && c.lon; });
      initStory(centers);
    })
    .catch(function(err) {
      console.warn('landing-story: could not load center data', err);
    });

  function hashCode(str) {
    var hash = 0;
    for (var i = 0; i < str.length; i++) {
      hash = ((hash << 5) - hash) + str.charCodeAt(i);
      hash |= 0;
    }
    return hash;
  }

  function initStory(centers) {
    var map = L.map('story-map', {
      scrollWheelZoom: false,
      zoomControl: true,
      attributionControl: true
    }).setView([39.5, -98.5], 4);

    setTimeout(function() { map.invalidateSize(); }, 100);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
      attribution: 'OpenStreetMap, CARTO',
      maxZoom: 18
    }).addTo(map);

    map.on('click', function() { map.scrollWheelZoom.enable(); });

    // Layer 0: Landscape - neutral dark dots
    var layerNeutral = L.layerGroup();
    centers.forEach(function(c) {
      L.circleMarker([c.lat, c.lon], {
        radius: 5,
        fillColor: '#2a2520',
        color: '#1a1510',
        weight: 1.5,
        opacity: 0.8,
        fillOpacity: 0.7
      }).addTo(layerNeutral);
    });

    // Layer 1: Problem - green-to-red based on deterministic hash
    var layerWait = L.layerGroup();
    centers.forEach(function(c) {
      var code = c.code || c.name || '';
      var h = hashCode(code);
      var wait = Math.abs(h % 100) / 100;
      // TODO: replace with real wait time data when available
      var r = Math.round(45 + wait * 190);
      var g = Math.round(158 - wait * 130);
      L.circleMarker([c.lat, c.lon], {
        radius: 6,
        fillColor: 'rgb(' + r + ',' + g + ',60)',
        color: 'rgb(' + r + ',' + g + ',60)',
        weight: 1,
        opacity: 0.9,
        fillOpacity: 0.75
      }).addTo(layerWait);
    });

    // Layer 2: Traffic - large semi-transparent red circles at high-fatality regions + small center dots
    var layerTraffic = L.layerGroup();
    var fatalityRegions = [
      { lat: 32, lon: -95, r: 220000 },
      { lat: 35, lon: -85, r: 200000 },
      { lat: 30, lon: -90, r: 180000 },
      { lat: 28, lon: -82, r: 160000 },
      { lat: 38, lon: -90, r: 150000 },
      { lat: 34, lon: -80, r: 140000 },
      { lat: 36, lon: -100, r: 170000 },
      { lat: 33, lon: -112, r: 120000 },
      { lat: 40, lon: -83, r: 130000 }
    ];
    fatalityRegions.forEach(function(region) {
      L.circle([region.lat, region.lon], {
        radius: region.r,
        fillColor: '#d93b3b',
        color: 'transparent',
        fillOpacity: 0.12
      }).addTo(layerTraffic);
    });
    centers.forEach(function(c) {
      L.circleMarker([c.lat, c.lon], {
        radius: 3,
        fillColor: '#444',
        color: 'transparent',
        fillOpacity: 0.5
      }).addTo(layerTraffic);
    });

    // Layer 3: Donor Type - two-color dots per center (brain death + cardiac death, deterministic sizes)
    var layerDonorType = L.layerGroup();
    centers.forEach(function(c) {
      var code = c.code || c.name || '';
      var h = Math.abs(hashCode(code));
      var brainSize = 3 + (h % 60) / 10;
      var cardiacSize = 2 + ((h >> 8) % 40) / 10;
      L.circleMarker([c.lat, c.lon], {
        radius: brainSize,
        fillColor: '#d93b3b',
        color: '#b02020',
        weight: 1,
        opacity: 0.7,
        fillOpacity: 0.5
      }).addTo(layerDonorType);
      L.circleMarker([c.lat + 0.3, c.lon + 0.3], {
        radius: cardiacSize,
        fillColor: '#e0a040',
        color: '#c08020',
        weight: 1,
        opacity: 0.7,
        fillOpacity: 0.5
      }).addTo(layerDonorType);
    });

    // Layer 4: Registration - large semi-transparent blue circles at high-registration regions + small center dots
    var layerRegistration = L.layerGroup();
    var registrationRegions = [
      { lat: 44, lon: -90, r: 220000 },
      { lat: 42, lon: -83, r: 190000 },
      { lat: 40, lon: -75, r: 170000 },
      { lat: 38, lon: -105, r: 160000 },
      { lat: 47, lon: -122, r: 150000 },
      { lat: 36, lon: -80, r: 140000 },
      { lat: 41, lon: -112, r: 130000 },
      { lat: 34, lon: -118, r: 160000 },
      { lat: 44, lon: -70, r: 110000 }
    ];
    registrationRegions.forEach(function(region) {
      L.circle([region.lat, region.lon], {
        radius: region.r,
        fillColor: '#3b82f6',
        color: 'transparent',
        fillOpacity: 0.12
      }).addTo(layerRegistration);
    });
    centers.forEach(function(c) {
      L.circleMarker([c.lat, c.lon], {
        radius: 3,
        fillColor: '#444',
        color: 'transparent',
        fillOpacity: 0.5
      }).addTo(layerRegistration);
    });

    // Layer 5: Methods - uniform accent-colored dots
    var layerMethods = L.layerGroup();
    centers.forEach(function(c) {
      L.circleMarker([c.lat, c.lon], {
        radius: 5,
        fillColor: '#c97c4a',
        color: '#a0603a',
        weight: 1.5,
        opacity: 0.7,
        fillOpacity: 0.5
      }).addTo(layerMethods);
    });

    // Layer 6: Composite - dots sized and colored by deterministic hash-based score
    var layerScore = L.layerGroup();
    centers.forEach(function(c) {
      var code = c.code || c.name || '';
      var h = Math.abs(hashCode(code));
      var score = 0.3 + (h % 70) / 100;
      var lightness = 38 + score * 24;
      L.circleMarker([c.lat, c.lon], {
        radius: 4 + score * 7,
        fillColor: 'hsl(24,75%,' + lightness + '%)',
        color: 'hsl(24,75%,' + lightness + '%)',
        weight: 1,
        opacity: 0.85,
        fillOpacity: 0.7
      }).addTo(layerScore);
    });

    // Layer 7: Explore - all centers in accent color
    var layerExplore = L.layerGroup();
    centers.forEach(function(c) {
      L.circleMarker([c.lat, c.lon], {
        radius: 5,
        fillColor: '#c97c4a',
        color: '#a0603a',
        weight: 1.5,
        opacity: 0.8,
        fillOpacity: 0.6
      }).addTo(layerExplore);
    });

    // Add initial layer
    layerNeutral.addTo(map);

    var allLayers = [layerNeutral, layerWait, layerTraffic, layerDonorType, layerRegistration, layerMethods, layerScore, layerExplore];
    var totalSteps = 8;

    // goStep function
    window.goStep = function(n) {
      var steps = document.querySelectorAll('.narr-step');
      for (var s = 0; s < steps.length; s++) {
        steps[s].classList.toggle('active', s === n);
      }
      allLayers.forEach(function(layer) { map.removeLayer(layer); });
      allLayers[n].addTo(map);
      for (var i = 0; i < totalSteps; i++) {
        var leg = document.getElementById('legend-' + i);
        if (leg) leg.classList.toggle('visible', i === n);
      }
      document.getElementById('progress-fill').style.width = (((n + 1) / totalSteps) * 100) + '%';
    };

    // Initialize progress bar
    document.getElementById('progress-fill').style.width = ((1 / totalSteps) * 100) + '%';
  }
})();
