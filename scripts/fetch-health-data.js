#!/usr/bin/env node
/**
 * Fetch health demographics data from CDC PLACES API (county-level).
 * Source: data.cdc.gov/resource/swc5-untb.json (PLACES: County Data)
 * Auth: None required (public API)
 * Format: JSON
 *
 * Fetches 5 health indicators for each of the 22 transplant cities:
 *   diabetesRate, obesityRate, ckdRate, hypertensionRate, smokingRate
 *
 * Uses county FIPS codes (state FIPS + county FIPS = locationid) to query
 * county-level age-adjusted prevalence from CDC PLACES (based on BRFSS).
 */

const { fetchWithRetry, mergeDataFile, updateMetadata, reportError, CITIES, delay } = require('./utils');

// CDC PLACES County-Level Data (SODA API)
const CDC_PLACES_URL = 'https://data.cdc.gov/resource/swc5-untb.json';

// Map CDC PLACES measure IDs to our field names
const MEASURES = {
    'DIABETES': 'diabetesRate',
    'OBESITY': 'obesityRate',
    'KIDNEY': 'ckdRate',
    'BPHIGH': 'hypertensionRate',
    'CSMOKING': 'smokingRate'
};

// County FIPS for each transplant city (3-digit, zero-padded)
// Combined with state FIPS to form 5-digit locationid
const CITY_COUNTY_FIPS = {
    'Pittsburgh': '003',      // Allegheny County, PA
    'Baltimore': '510',       // Baltimore City, MD
    'Philadelphia': '101',    // Philadelphia County, PA
    'New York': '061',        // New York County (Manhattan), NY
    'Minneapolis': '053',     // Hennepin County, MN
    'Madison': '025',         // Dane County, WI
    'Chicago': '031',         // Cook County, IL
    'Cleveland': '035',       // Cuyahoga County, OH
    'St. Louis': '510',       // St. Louis City, MO
    'Indianapolis': '097',    // Marion County, IN
    'Omaha': '055',           // Douglas County, NE
    'Rochester': '109',       // Olmsted County, MN
    'Nashville': '037',       // Davidson County, TN
    'Durham': '063',          // Durham County, NC
    'Miami': '086',           // Miami-Dade County, FL
    'Dallas': '113',          // Dallas County, TX
    'Houston': '201',         // Harris County, TX
    'Portland': '051',        // Multnomah County, OR
    'Seattle': '033',         // King County, WA
    'San Francisco': '075',   // San Francisco County, CA
    'Los Angeles': '037',     // Los Angeles County, CA
    'Palo Alto': '085'        // Santa Clara County, CA
};

async function fetchHealthData() {
    console.log('Fetching health demographics from CDC PLACES API (county-level)...');

    const result = {};
    const measureList = Object.keys(MEASURES).map(m => `'${m}'`).join(',');

    for (const cityInfo of CITIES) {
        const countyFips = CITY_COUNTY_FIPS[cityInfo.city];
        const stateFips = cityInfo.stateFips;
        if (!countyFips || !stateFips) {
            console.warn(`  ${cityInfo.city}: no county FIPS mapping, skipping`);
            continue;
        }

        // Build 5-digit locationid: state FIPS (2) + county FIPS (3)
        const locationId = stateFips + countyFips;

        try {
            const query = `$where=locationid='${locationId}' AND measureid in(${measureList}) AND data_value_type='Age-adjusted prevalence'&$select=measureid,data_value,year&$order=year DESC&$limit=50`;
            const url = `${CDC_PLACES_URL}?${query}`;
            const response = await fetchWithRetry(url);
            const data = await response.json();

            if (data && data.length > 0) {
                const cityData = {};
                // Take the most recent value for each measure
                const seen = new Set();
                for (const row of data) {
                    const fieldName = MEASURES[row.measureid];
                    if (fieldName && !seen.has(fieldName)) {
                        const val = parseFloat(row.data_value);
                        if (!isNaN(val)) {
                            cityData[fieldName] = val;
                            seen.add(fieldName);
                        }
                    }
                }

                const count = Object.keys(cityData).length;
                if (count > 0) {
                    result[cityInfo.city] = cityData;
                    console.log(`  ${cityInfo.city} (${locationId}): ${count}/5 indicators`);
                } else {
                    console.warn(`  ${cityInfo.city} (${locationId}): no parseable values`);
                }
            } else {
                console.warn(`  ${cityInfo.city} (${locationId}): no data returned`);
            }

            await delay(300);  // Respectful rate limiting for CDC API
        } catch (err) {
            console.warn(`  ${cityInfo.city}: fetch failed — ${err.message}`);
        }
    }

    const cityCount = Object.keys(result).length;
    if (cityCount > 0) {
        // Deep merge: updates indicators per city while preserving any
        // additional fields not fetched by this script
        mergeDataFile('health-demographics.json', result, 'CDC PLACES API (5 county-level indicators)');
        updateMetadata('health-demographics', 'CDC PLACES API', 'fetched');
        console.log(`\nFetched health data for ${cityCount} cities.`);
    } else {
        console.warn('\nNo health demographics data retrieved. Seed data will be used.');
        updateMetadata('health-demographics', 'CDC PLACES API', 'error');
    }
}

fetchHealthData().catch(err => {
    reportError('CDC PLACES API', err);
    process.exit(1);
});
