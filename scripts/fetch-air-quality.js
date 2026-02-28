#!/usr/bin/env node
/**
 * Fetch air quality data from EPA AQS API.
 * Source: aqs.epa.gov/data/api/
 * Auth: Free email signup (EPA_EMAIL and EPA_API_KEY env vars)
 * Format: JSON
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
    const result = {};

    // Get unique state FIPS
    const statesFetched = new Set();

    for (const cityInfo of CITIES) {
        const stateFips = cityInfo.stateFips;
        if (statesFetched.has(stateFips)) continue;
        statesFetched.add(stateFips);

        try {
            const url = `${AQS_BASE}?email=${encodeURIComponent(email)}&key=${encodeURIComponent(apiKey)}&param=44201&bdate=${year}0101&edate=${year}1231&state=${stateFips}`;
            const response = await fetchWithRetry(url);
            const data = await response.json();

            if (data.Data) {
                // Group by county and compute average AQI
                const byCounty = {};
                for (const record of data.Data) {
                    const county = record.county_code;
                    if (!byCounty[county]) byCounty[county] = [];
                    if (record.arithmetic_mean != null) {
                        byCounty[county].push(record.arithmetic_mean);
                    }
                }

                // Map cities in this state to their AQI
                for (const c of CITIES.filter(c => c.stateFips === stateFips)) {
                    const countyFips = CITY_COUNTY_FIPS[c.city];
                    const readings = byCounty[countyFips];
                    if (readings && readings.length > 0) {
                        const avgPPB = readings.reduce((a, b) => a + b, 0) / readings.length;
                        // Convert ozone ppb to an AQI-like score (0-100, higher is better)
                        const aqiScore = Math.round(Math.max(0, Math.min(100, 100 - avgPPB)));
                        result[c.city] = aqiScore;
                    }
                }
            }

            await delay(1000); // Rate limit
        } catch (err) {
            console.warn(`Failed to fetch AQI for state ${stateFips}: ${err.message}`);
        }
    }

    if (Object.keys(result).length > 0) {
        writeDataFile('air-quality.json', result, 'EPA AQS API');
        updateMetadata('air-quality', 'EPA AQS');
        console.log(`Fetched air quality for ${Object.keys(result).length} cities.`);
    } else {
        console.warn('No air quality data retrieved.');
        updateMetadata('air-quality', 'EPA AQS', 'error');
    }
}

fetchAirQuality().catch(err => {
    reportError('EPA AQS', err);
    process.exit(1);
});
