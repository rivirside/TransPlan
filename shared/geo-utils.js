/**
 * shared/geo-utils.js — Geocoding and distance utilities.
 * Used by simulator, centers page, and other tools.
 */
(function () {
  'use strict';

  /**
   * Geocode a location string using Nominatim (US only).
   * @param {string} query - Address or place name
   * @returns {Promise<{lat: number, lon: number, display: string}|null>}
   */
  async function geocodeLocation(query) {
    try {
      var url = 'https://nominatim.openstreetmap.org/search?q=' +
        encodeURIComponent(query + ', USA') +
        '&format=json&limit=1&countrycodes=us';
      var response = await fetch(url, {
        headers: { 'User-Agent': 'TransPlan/2.0' },
        signal: AbortSignal.timeout(5000)
      });
      var data = await response.json();
      if (data && data.length > 0) {
        return {
          lat: parseFloat(data[0].lat),
          lon: parseFloat(data[0].lon),
          display: data[0].display_name.split(',').slice(0, 2).join(',')
        };
      }
    } catch (e) {
      console.warn('Geocoding failed:', e.message);
    }
    return null;
  }

  /**
   * Haversine distance between two points in miles.
   * @param {number} lat1
   * @param {number} lon1
   * @param {number} lat2
   * @param {number} lon2
   * @returns {number} Distance in miles
   */
  function haversineMiles(lat1, lon1, lat2, lon2) {
    var R = 3959;
    var dLat = (lat2 - lat1) * Math.PI / 180;
    var dLon = (lon2 - lon1) * Math.PI / 180;
    var a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }

  window.TransPlanGeo = {
    geocodeLocation: geocodeLocation,
    haversineMiles: haversineMiles
  };
})();
