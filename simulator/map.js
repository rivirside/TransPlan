/**
 * SimMap — Minimal Leaflet map module for the TransPlan simulator.
 *
 * Shows ranked center markers and an optional home-location pin.
 * NO data overlay layers (those belong on the Explorer page).
 *
 * Expects the global `L` (Leaflet) to be loaded via CDN before this file runs.
 *
 * Usage:
 *   SimMap.init('map-container');
 *   SimMap.updateWithResults(rankedCenters, homeLocation);
 *   SimMap.highlightCenter('FLUF');
 *   const leafletMap = SimMap.getMap();
 */
;(function () {
    'use strict';

    // ── State ────────────────────────────────────────────────────────────
    var _map = null;
    var _markersLayer = null;
    var _homeMarkerLayer = null;
    // centerCode -> marker metadata lookup for highlight
    var _markerIndex = {};
    var _highlightedCode = null;

    // ── Constants ────────────────────────────────────────────────────────
    var TILE_URL =
        'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png';
    var TILE_ATTR =
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> ' +
        '&copy; <a href="https://carto.com/">CARTO</a>';

    var DEFAULT_CENTER = [39, -96];
    var DEFAULT_ZOOM = 4;

    var MARKER_SIZE = 30;
    var MARKER_SIZE_HIGHLIGHT = 38;
    var HOME_SIZE = 36;

    // Rank-based palette
    var COLOR_TOP5 = '#22c55e';   // green
    var COLOR_MID = '#3b82f6';    // blue  (ranks 6-20)
    var COLOR_TAIL = '#94a3b8';   // gray  (21+)
    var COLOR_HOME = '#ef4444';   // red for home pin

    // ── Helpers ──────────────────────────────────────────────────────────

    /**
     * Return a marker colour based on 1-indexed rank.
     */
    function colorForRank(rank) {
        if (rank <= 5) return COLOR_TOP5;
        if (rank <= 20) return COLOR_MID;
        return COLOR_TAIL;
    }

    /**
     * Build the inline-style string for a numbered circle marker.
     * All values are internal constants or sanitised numbers — no user strings.
     */
    function markerHtml(label, color, size, highlighted) {
        var border = highlighted ? '3px solid #0f172a' : '2px solid white';
        var shadow = highlighted
            ? '0 0 8px 2px rgba(59,130,246,0.55), 0 3px 8px rgba(0,0,0,0.35)'
            : '0 2px 6px rgba(0,0,0,0.3)';
        var fontSize = size >= 36 ? '15px' : '13px';

        return (
            '<div style="' +
                'background:' + color + ';' +
                'color:#fff;' +
                'width:' + size + 'px;' +
                'height:' + size + 'px;' +
                'border-radius:50%;' +
                'display:flex;' +
                'align-items:center;' +
                'justify-content:center;' +
                'font-weight:700;' +
                'font-size:' + fontSize + ';' +
                'border:' + border + ';' +
                'box-shadow:' + shadow + ';' +
                'transition:transform .15s ease;' +
            '">' + label + '</div>'
        );
    }

    /**
     * Build the HTML for the home / star marker.
     * Uses only hardcoded constants — safe for divIcon.
     */
    function homeMarkerHtml() {
        return (
            '<div style="' +
                'background:' + COLOR_HOME + ';' +
                'color:#fff;' +
                'width:' + HOME_SIZE + 'px;' +
                'height:' + HOME_SIZE + 'px;' +
                'border-radius:50%;' +
                'display:flex;' +
                'align-items:center;' +
                'justify-content:center;' +
                'font-size:18px;' +
                'border:3px solid #7f1d1d;' +
                'box-shadow:0 3px 10px rgba(0,0,0,0.4);' +
            '">&#9733;</div>'   // ★
        );
    }

    /**
     * Format a numeric score for display.
     */
    function fmt(val, decimals) {
        if (val == null) return 'N/A';
        return Number(val).toFixed(decimals == null ? 1 : decimals);
    }

    /**
     * Escape a string for safe inclusion inside an HTML attribute or text node.
     */
    function esc(str) {
        if (str == null) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    // ── Public API ───────────────────────────────────────────────────────

    /**
     * Initialise the Leaflet map inside the given container element.
     *
     * @param {string} containerId  DOM id of the map container div.
     * @returns {L.Map|null}        The Leaflet map instance, or null on failure.
     */
    function init(containerId) {
        if (typeof L === 'undefined') {
            var el = document.getElementById(containerId);
            if (el) {
                el.textContent = '';
                var notice = document.createElement('div');
                notice.style.cssText = 'padding:24px;text-align:center;color:#64748b';
                var strong = document.createElement('strong');
                strong.textContent = 'Map unavailable';
                notice.appendChild(strong);
                notice.appendChild(
                    document.createTextNode(' \u2014 Leaflet library not loaded.')
                );
                el.appendChild(notice);
                el.style.height = 'auto';
                el.style.minHeight = '80px';
            }
            return null;
        }

        _map = L.map(containerId, {
            zoomControl: true,
            scrollWheelZoom: true
        }).setView(DEFAULT_CENTER, DEFAULT_ZOOM);

        L.tileLayer(TILE_URL, {
            attribution: TILE_ATTR,
            maxZoom: 18,
            subdomains: 'abcd'
        }).addTo(_map);

        // Cluster center markers when the plugin is available (#223 — declutters
        // the 248-center map); gracefully fall back to a plain layer group if the
        // markercluster CDN script didn't load.
        _markersLayer = (typeof L.markerClusterGroup === 'function')
            ? L.markerClusterGroup({ maxClusterRadius: 45, spiderfyOnMaxZoom: true, chunkedLoading: true })
            : L.layerGroup();
        _markersLayer.addTo(_map);
        _homeMarkerLayer = L.layerGroup().addTo(_map);

        return _map;
    }

    /**
     * Clear all markers and plot ranked center results.
     *
     * Each item in `results` should have at minimum:
     *   { center_code, center_name, state, lat, lon, score }
     * Optional fields: rank, p24 (24-month survival), waitTime, city
     *
     * @param {Array}  results       Ranked center objects.
     * @param {Object} [homeLocation]  { lat, lon, label } for the user's home pin.
     */
    function updateWithResults(results, homeLocation) {
        if (!_map) return;

        // Reset
        _markersLayer.clearLayers();
        _homeMarkerLayer.clearLayers();
        _markerIndex = {};
        _highlightedCode = null;

        if (!results || results.length === 0) return;

        var bounds = [];

        results.forEach(function (center, idx) {
            var rank = center.rank || idx + 1;
            var lat = center.lat;
            var lon = center.lon;
            if (lat == null || lon == null) return;

            var coord = [lat, lon];
            bounds.push(coord);

            var color = colorForRank(rank);
            var icon = L.divIcon({
                className: 'sim-rank-marker',
                html: markerHtml(rank, color, MARKER_SIZE, false),
                iconSize: [MARKER_SIZE + 4, MARKER_SIZE + 4],
                iconAnchor: [(MARKER_SIZE + 4) / 2, (MARKER_SIZE + 4) / 2]
            });

            // Build popup content using escaped strings
            var name = esc(center.center_name || center.city || '');
            var state = esc(center.state || '');
            var popupParts = [
                '<strong>#' + rank + ' ' + name + '</strong>'
            ];
            if (state) popupParts.push(state);
            if (center.score != null) {
                popupParts.push('Score: <strong>' + fmt(center.score) + '</strong>');
            }
            if (center.p24 != null) {
                popupParts.push('24-mo survival: ' + fmt(center.p24, 1) + '%');
            }
            if (center.waitTime != null) {
                popupParts.push('Wait: ' + esc(center.waitTime));
            }

            var marker = L.marker(coord, {
                icon: icon,
                zIndexOffset: 500 - rank   // higher rank draws on top
            }).bindPopup(popupParts.join('<br>'));

            marker.addTo(_markersLayer);

            var code = center.center_code || center.city || ('center_' + idx);
            _markerIndex[code] = {
                marker: marker,
                coord: coord,
                rank: rank,
                color: color
            };
        });

        // Home location pin
        if (homeLocation && homeLocation.lat != null && homeLocation.lon != null) {
            var homeCoord = [homeLocation.lat, homeLocation.lon];
            bounds.push(homeCoord);

            var homeIcon = L.divIcon({
                className: 'sim-home-marker',
                html: homeMarkerHtml(),
                iconSize: [HOME_SIZE + 6, HOME_SIZE + 6],
                iconAnchor: [(HOME_SIZE + 6) / 2, (HOME_SIZE + 6) / 2]
            });

            L.marker(homeCoord, {
                icon: homeIcon,
                zIndexOffset: 1000
            })
                .bindPopup(
                    '<strong>Home Location</strong>' +
                    (homeLocation.label ? '<br>' + esc(homeLocation.label) : '')
                )
                .addTo(_homeMarkerLayer);
        }

        // Fit map to show all markers
        if (bounds.length > 0) {
            _map.fitBounds(bounds, { padding: [40, 40], maxZoom: 7 });
        }
    }

    /**
     * Highlight a single center marker (e.g. on table row hover).
     * Pass null / undefined to clear the highlight.
     *
     * @param {string|null} centerCode  The center_code to highlight.
     */
    function highlightCenter(centerCode) {
        // Restore previously highlighted marker to normal size
        if (_highlightedCode && _markerIndex[_highlightedCode]) {
            var prev = _markerIndex[_highlightedCode];
            prev.marker.setIcon(L.divIcon({
                className: 'sim-rank-marker',
                html: markerHtml(prev.rank, prev.color, MARKER_SIZE, false),
                iconSize: [MARKER_SIZE + 4, MARKER_SIZE + 4],
                iconAnchor: [(MARKER_SIZE + 4) / 2, (MARKER_SIZE + 4) / 2]
            }));
            prev.marker.setZIndexOffset(500 - prev.rank);
        }

        _highlightedCode = centerCode || null;

        // Apply highlight: larger size, dark border, glow shadow
        if (_highlightedCode && _markerIndex[_highlightedCode]) {
            var cur = _markerIndex[_highlightedCode];
            cur.marker.setIcon(L.divIcon({
                className: 'sim-rank-marker sim-rank-marker--active',
                html: markerHtml(cur.rank, cur.color, MARKER_SIZE_HIGHLIGHT, true),
                iconSize: [MARKER_SIZE_HIGHLIGHT + 4, MARKER_SIZE_HIGHLIGHT + 4],
                iconAnchor: [(MARKER_SIZE_HIGHLIGHT + 4) / 2, (MARKER_SIZE_HIGHLIGHT + 4) / 2]
            }));
            cur.marker.setZIndexOffset(1500);
        }
    }

    /**
     * Return the underlying Leaflet map instance (or null if not initialised).
     */
    function getMap() {
        return _map;
    }

    // ── Expose on window ─────────────────────────────────────────────────
    window.SimMap = {
        init: init,
        updateWithResults: updateWithResults,
        highlightCenter: highlightCenter,
        getMap: getMap
    };
})();
