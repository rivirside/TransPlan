#!/usr/bin/env node
/**
 * Fetch air quality data from EPA AQS API.
 * Source: aqs.epa.gov/data/api/
 * Auth: Free email signup (EPA_EMAIL and EPA_API_KEY env vars)
 * Format: JSON
 *
 * L-015 fix: Uses proper EPA AQI breakpoint conversion for ozone AND PM2.5
 * instead of naive `100 - ppb`. Averages both pollutants for a composite score.
 * Score 0-100 where higher = better air quality (inverted from EPA AQI convention
 * where lower = better) to match our scoring system.
 */

const { fetchWithRetry, writeDataFile, updateMetadata, reportError, CITIES, delay } = require('./utils');

const AQS_BASE = 'https://aqs.epa.gov/data/api/annualData/byState';

// County FIPS for major cities (primary county)
const CITY_COUNTY_FIPS = {
    'Pittsburgh': '003',      // Allegheny County
    'Baltimore': '510',       // Baltimore City
    'Philadelphia': '101',    // Philadelphia County
    'New York': '061',        // New York County (Manhattan)
    'Minneapolis': '053',     // Hennepin County
    'Madison': '025',         // Dane County
    'Chicago': '031',         // Cook County
    'Cleveland': '035',       // Cuyahoga County
    'St. Louis': '510',       // St. Louis City
    'Indianapolis': '097',    // Marion County
    'Omaha': '055',           // Douglas County
    'Rochester': '109',       // Olmsted County
    'Nashville': '037',       // Davidson County
    'Durham': '063',          // Durham County
    'Miami': '086',           // Miami-Dade County
    'Dallas': '113',          // Dallas County
    'Houston': '201',         // Harris County
    'Portland': '051',        // Multnomah County
    'Seattle': '033',         // King County
    'San Francisco': '075',   // San Francisco County
    'Los Angeles': '037',     // Los Angeles County
    'Palo Alto': '085'        // Santa Clara County
};

// EPA AQI breakpoints for 8-hour ozone (ppm)
// Source: https://www.epa.gov/aqi/technical-assistance-document-reporting-daily-air-quality
function ozoneToAQI(ppm) {
    // Breakpoints: [low_conc, high_conc, low_aqi, high_aqi]
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
    return ppm > 0.200 ? 301 : 0; // Beyond scale
}

// EPA AQI breakpoints for PM2.5 annual mean (µg/m³)
// Using 24-hour breakpoints as proxy for annual means
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
    // AQI 0 → score 100 (perfect), AQI 50 → score 75 (good),
    // AQI 100 → score 50 (moderate), AQI 150 → score 25 (unhealthy sensitive),
    // AQI 200+ → score ~0
    return Math.max(0, Math.min(100, Math.round(100 - (aqi / 2))));
}

async function fetchAirQuality() {
    const email = process.env.EPA_EMAIL;
    const apiKey = process.env.EPA_API_KEY;

    if (!email || !apiKey) {
        console.warn('EPA_EMAIL and EPA_API_KEY not set. Using seed data.');
        updateMetadata('air-quality', 'EPA AQS (skipped - no credentials)', 'skipped');
        return;
    }

    console.log('Fetching air quality data from EPA AQS...');
    const year = new Date().getFullYear() - 1;

    const ozoneResults = {};  // city → AQI
    const pm25Results = {};   // city → AQI

    // Get unique state FIPS
    const statesFetched = new Set();

    // Fetch ozone data (param 44201)
    for (const cityInfo of CITIES) {
        const stateFips = cityInfo.stateFips;
        if (statesFetched.has(stateFips)) continue;
        statesFetched.add(stateFips);

        try {
            const url = `${AQS_BASE}?email=${encodeURIComponent(email)}&key=${encodeURIComponent(apiKey)}&param=44201&bdate=${year}0101&edate=${year}1231&state=${stateFips}`;
            const response = await fetchWithRetry(url);
            const data = await response.json();

            if (data.Data) {
                const byCounty = {};
                for (const record of data.Data) {
                    const county = record.county_code;
                    if (!byCounty[county]) byCounty[county] = [];
                    if (record.arithmetic_mean != null) {
                        byCounty[county].push(record.arithmetic_mean);
                    }
                }

                for (const c of CITIES.filter(c => c.stateFips === stateFips)) {
                    const countyFips = CITY_COUNTY_FIPS[c.city];
                    const readings = byCounty[countyFips];
                    if (readings && readings.length > 0) {
                        const avgPPM = readings.reduce((a, b) => a + b, 0) / readings.length;
                        ozoneResults[c.city] = ozoneToAQI(avgPPM);
                    }
                }
            }

            await delay(1000);
        } catch (err) {
            console.warn(`Failed to fetch ozone for state ${stateFips}: ${err.message}`);
        }
    }

    // Fetch PM2.5 data (param 88101)
    statesFetched.clear();
    for (const cityInfo of CITIES) {
        const stateFips = cityInfo.stateFips;
        if (statesFetched.has(stateFips)) continue;
        statesFetched.add(stateFips);

        try {
            const url = `${AQS_BASE}?email=${encodeURIComponent(email)}&key=${encodeURIComponent(apiKey)}&param=88101&bdate=${year}0101&edate=${year}1231&state=${stateFips}`;
            const response = await fetchWithRetry(url);
            const data = await response.json();

            if (data.Data) {
                const byCounty = {};
                for (const record of data.Data) {
                    const county = record.county_code;
                    if (!byCounty[county]) byCounty[county] = [];
                    if (record.arithmetic_mean != null) {
                        byCounty[county].push(record.arithmetic_mean);
                    }
                }

                for (const c of CITIES.filter(c => c.stateFips === stateFips)) {
                    const countyFips = CITY_COUNTY_FIPS[c.city];
                    const readings = byCounty[countyFips];
                    if (readings && readings.length > 0) {
                        const avgUGM3 = readings.reduce((a, b) => a + b, 0) / readings.length;
                        pm25Results[c.city] = pm25ToAQI(avgUGM3);
                    }
                }
            }

            await delay(1000);
        } catch (err) {
            console.warn(`Failed to fetch PM2.5 for state ${stateFips}: ${err.message}`);
        }
    }

    // Combine ozone and PM2.5 into a single score per city
    // Use the worse (higher AQI) of the two pollutants, per EPA convention
    const result = {};
    const allCities = new Set([...Object.keys(ozoneResults), ...Object.keys(pm25Results)]);

    for (const city of allCities) {
        const ozoneAQI = ozoneResults[city] ?? null;
        const pm25AQI = pm25Results[city] ?? null;

        let dominantAQI;
        if (ozoneAQI !== null && pm25AQI !== null) {
            dominantAQI = Math.max(ozoneAQI, pm25AQI); // Worst pollutant dominates
        } else {
            dominantAQI = ozoneAQI ?? pm25AQI;
        }

        if (dominantAQI !== null) {
            result[city] = aqiToScore(dominantAQI);
        }
    }

    if (Object.keys(result).length > 0) {
        writeDataFile('air-quality.json', result, 'EPA AQS API (ozone + PM2.5)');
        updateMetadata('air-quality', 'EPA AQS');
        console.log(`Fetched air quality for ${Object.keys(result).length} cities (ozone: ${Object.keys(ozoneResults).length}, PM2.5: ${Object.keys(pm25Results).length}).`);
    } else {
        console.warn('No air quality data retrieved.');
        updateMetadata('air-quality', 'EPA AQS', 'error');
    }
}

fetchAirQuality().catch(err => {
    reportError('EPA AQS', err);
    process.exit(1);
});
