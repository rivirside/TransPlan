#!/usr/bin/env node
/**
 * Fetch per-monitor air quality data from EPA AQS API with coordinates.
 * Source: aqs.epa.gov/data/api/annualData/byState
 * Auth: EPA_EMAIL and EPA_API_KEY env vars
 *
 * Phase 6B issue #125: Expands air quality from 22 city aggregates (~20 points)
 * to per-monitor lat/lon + readings (~2,000-4,000 points) for dense spatial
 * interpolation surfaces.
 *
 * Output: data/air-quality-monitors.json
 * Format: { monitors: [ { lat, lon, score, aqi, pollutant, state, ... }, ... ] }
 *
 * Fetches all 50 states + DC for full CONUS coverage.
 */

const { fetchWithRetry, writeDataFile, updateMetadata, reportError, delay } = require('./utils');

const AQS_BASE = 'https://aqs.epa.gov/data/api/annualData/byState';

// All 50 states + DC FIPS codes
const ALL_STATE_FIPS = [
    '01', '02', '04', '05', '06', '08', '09', '10', '11', '12',
    '13', '15', '16', '17', '18', '19', '20', '21', '22', '23',
    '24', '25', '26', '27', '28', '29', '30', '31', '32', '33',
    '34', '35', '36', '37', '38', '39', '40', '41', '42', '44',
    '45', '46', '47', '48', '49', '50', '51', '53', '54', '55', '56'
];

// EPA AQI breakpoints for 8-hour ozone (ppm)
function ozoneToAQI(ppm) {
    const breakpoints = [
        [0.000, 0.054, 0, 50],
        [0.055, 0.070, 51, 100],
        [0.071, 0.085, 101, 150],
        [0.086, 0.105, 151, 200],
        [0.106, 0.200, 201, 300]
    ];
    for (const [cLow, cHigh, aqiLow, aqiHigh] of breakpoints) {
        if (ppm >= cLow && ppm <= cHigh) {
            return Math.round(((aqiHigh - aqiLow) / (cHigh - cLow)) * (ppm - cLow) + aqiLow);
        }
    }
    return ppm > 0.200 ? 301 : 0;
}

// EPA AQI breakpoints for PM2.5 annual mean (µg/m³)
function pm25ToAQI(ugm3) {
    const breakpoints = [
        [0.0, 9.0, 0, 50],
        [9.1, 35.4, 51, 100],
        [35.5, 55.4, 101, 150],
        [55.5, 125.4, 151, 200],
        [125.5, 225.4, 201, 300]
    ];
    for (const [cLow, cHigh, aqiLow, aqiHigh] of breakpoints) {
        if (ugm3 >= cLow && ugm3 <= cHigh) {
            return Math.round(((aqiHigh - aqiLow) / (cHigh - cLow)) * (ugm3 - cLow) + aqiLow);
        }
    }
    return ugm3 > 225.4 ? 301 : 0;
}

// Convert EPA AQI (0-500, lower=better) to our score (0-100, higher=better)
function aqiToScore(aqi) {
    return Math.max(0, Math.min(100, Math.round(100 - (aqi / 2))));
}

async function fetchMonitorData() {
    const email = process.env.EPA_EMAIL;
    const apiKey = process.env.EPA_API_KEY;

    if (!email || !apiKey) {
        console.warn('EPA_EMAIL and EPA_API_KEY not set. Skipping monitor-level fetch.');
        updateMetadata('air-quality-monitors', 'EPA AQS (skipped - no credentials)', 'skipped');
        if (process.env.CI) {
            console.error('ERROR: Missing credentials in CI environment.');
            process.exit(1);
        }
        return;
    }

    console.log('Fetching per-monitor air quality data from EPA AQS...');
    const year = new Date().getFullYear() - 1;

    const monitors = [];
    const seen = new Set(); // Deduplicate by monitor+pollutant

    // Fetch both ozone (44201) and PM2.5 (88101) for all states
    const pollutants = [
        { param: '44201', name: 'ozone', toAQI: ozoneToAQI },
        { param: '88101', name: 'pm25', toAQI: pm25ToAQI }
    ];

    for (const pollutant of pollutants) {
        console.log(`\n  Fetching ${pollutant.name} monitors...`);
        let stateCount = 0;

        for (const stateFips of ALL_STATE_FIPS) {
            try {
                const url = `${AQS_BASE}?email=${encodeURIComponent(email)}&key=${encodeURIComponent(apiKey)}&param=${pollutant.param}&bdate=${year}0101&edate=${year}1231&state=${stateFips}`;
                const response = await fetchWithRetry(url);
                const data = await response.json();

                if (data.Data && data.Data.length > 0) {
                    // Group records by monitor (state-county-site-poc)
                    const byMonitor = {};
                    for (const record of data.Data) {
                        if (record.latitude == null || record.longitude == null) continue;
                        if (record.arithmetic_mean == null) continue;

                        const monitorId = `${record.state_code}-${record.county_code}-${record.site_number}-${record.poc}`;
                        if (!byMonitor[monitorId]) {
                            byMonitor[monitorId] = {
                                lat: parseFloat(record.latitude),
                                lon: parseFloat(record.longitude),
                                state: record.state || '',
                                city: record.city || '',
                                name: record.local_site_name || '',
                                readings: []
                            };
                        }
                        byMonitor[monitorId].readings.push(record.arithmetic_mean);
                    }

                    // Average readings per monitor and compute AQI/score
                    for (const [monitorId, info] of Object.entries(byMonitor)) {
                        const key = `${monitorId}-${pollutant.name}`;
                        if (seen.has(key)) continue;
                        seen.add(key);

                        const avg = info.readings.reduce((a, b) => a + b, 0) / info.readings.length;
                        const aqi = pollutant.toAQI(avg);
                        const score = aqiToScore(aqi);

                        monitors.push({
                            lat: info.lat,
                            lon: info.lon,
                            score,
                            aqi,
                            pollutant: pollutant.name,
                            state: info.state,
                            value: Math.round(avg * 10000) / 10000
                        });
                    }

                    stateCount++;
                }

                await delay(1200); // Respectful rate limiting
            } catch (err) {
                console.warn(`    State ${stateFips}: ${err.message}`);
            }
        }
        console.log(`  ${pollutant.name}: ${stateCount} states with data`);
    }

    if (monitors.length > 0) {
        writeDataFile('air-quality-monitors.json',
            { monitors },
            `EPA AQS API (${monitors.length} monitors, ozone + PM2.5, all states)`
        );
        updateMetadata('air-quality-monitors', 'EPA AQS (per-monitor)', 'fetched');
        console.log(`\nFetched ${monitors.length} monitor readings across all states.`);
    } else {
        console.warn('\nNo monitor data retrieved.');
        updateMetadata('air-quality-monitors', 'EPA AQS (per-monitor)', 'error');
    }
}

fetchMonitorData().catch(err => {
    reportError('EPA AQS (monitors)', err);
    process.exit(1);
});
