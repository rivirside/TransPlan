#!/usr/bin/env node
/**
 * Fetch health demographics data from CDC PLACES API (county-level).
 *
 * Primary source: data.cdc.gov/resource/swc5-untb.json
 *   (PLACES: Local Data for Better Health, County Data, 2025 release)
 *
 * Fallback source: data.cdc.gov/resource/d3i6-k6z5.json
 *   (PLACES: County Data GIS Friendly Format, 2024 release)
 *   Used when the primary dataset is missing a county (e.g., Pennsylvania
 *   counties are absent from the 2023 data year in the 2025 release).
 *
 * CKD source: data.cdc.gov/resource/duw2-7jbt.json
 *   (PLACES: Local Data for Better Health, County Data, 2022 release)
 *   The KIDNEY measureid was removed from the 2025 release; the 2022
 *   release is the latest that still carries it.
 *
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

// CDC PLACES County-Level Data (SODA API) — 2025 release (primary)
const CDC_PLACES_URL = 'https://data.cdc.gov/resource/swc5-untb.json';

// CDC PLACES County Data GIS Friendly — 2024 release (fallback for missing counties)
const CDC_PLACES_GIS_URL = 'https://data.cdc.gov/resource/d3i6-k6z5.json';

// CDC PLACES County Data — 2022 release (has KIDNEY measure, removed from 2025)
const CDC_PLACES_2022_URL = 'https://data.cdc.gov/resource/duw2-7jbt.json';

// Map CDC PLACES measure IDs to our field names (primary dataset, 2025 release)
// Note: KIDNEY was removed from the 2025 release; fetched separately from 2022 release
const MEASURES = {
    'DIABETES': 'diabetesRate',
    'OBESITY': 'obesityRate',
    'BPHIGH': 'hypertensionRate',
    'CSMOKING': 'smokingRate'
};

// Map GIS-friendly column names to our field names (fallback dataset)
const GIS_COLUMNS = {
    'diabetes_adjprev': 'diabetesRate',
    'obesity_adjprev': 'obesityRate',
    'bphigh_adjprev': 'hypertensionRate',
    'csmoking_adjprev': 'smokingRate'
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

/**
 * Fetch from primary dataset (swc5-untb, 2025 release).
 * Returns { diabetesRate, obesityRate, hypertensionRate, smokingRate } or null.
 */
async function fetchPrimary(locationId) {
    const measureList = Object.keys(MEASURES).map(m => `'${m}'`).join(',');
    const query = `$where=locationid='${locationId}' AND measureid in(${measureList}) AND data_value_type='Age-adjusted prevalence'&$select=measureid,data_value,year&$order=year DESC&$limit=50`;
    const url = `${CDC_PLACES_URL}?${query}`;
    const response = await fetchWithRetry(url);
    const data = await response.json();

    if (!data || data.length === 0) {
        return null;
    }

    const cityData = {};
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

    return Object.keys(cityData).length > 0 ? cityData : null;
}

/**
 * Fetch from GIS-friendly fallback dataset (d3i6-k6z5, 2024 release).
 * Uses wide-format columns (e.g., diabetes_adjprev) instead of measureid rows.
 * Returns { diabetesRate, obesityRate, hypertensionRate, smokingRate } or null.
 */
async function fetchGISFallback(locationId) {
    const columns = Object.keys(GIS_COLUMNS).join(',');
    const query = `$select=countyfips,${columns}&$where=countyfips='${locationId}'&$limit=1`;
    const url = `${CDC_PLACES_GIS_URL}?${query}`;
    const response = await fetchWithRetry(url);
    const data = await response.json();

    if (!data || data.length === 0) {
        return null;
    }

    const row = data[0];
    const cityData = {};
    for (const [col, fieldName] of Object.entries(GIS_COLUMNS)) {
        const val = parseFloat(row[col]);
        if (!isNaN(val)) {
            cityData[fieldName] = val;
        }
    }

    return Object.keys(cityData).length > 0 ? cityData : null;
}

/**
 * Fetch CKD (chronic kidney disease) rate from the 2022 release.
 * The KIDNEY measureid was removed from the 2025 release, so we query
 * the 2022 release (duw2-7jbt) which is the latest that still has it.
 * Returns ckdRate value or null.
 */
async function fetchCKDRate(locationId) {
    const query = `$where=locationid='${locationId}' AND measureid='KIDNEY' AND data_value_type='Age-adjusted prevalence'&$select=data_value,year&$order=year DESC&$limit=1`;
    const url = `${CDC_PLACES_2022_URL}?${query}`;
    const response = await fetchWithRetry(url);
    const data = await response.json();

    if (data && data.length > 0) {
        const val = parseFloat(data[0].data_value);
        if (!isNaN(val)) {
            return val;
        }
    }
    return null;
}

async function fetchHealthData() {
    console.log('Fetching health demographics from CDC PLACES API (county-level)...');
    console.log('  Primary: swc5-untb (2025 release, 4 measures)');
    console.log('  Fallback: d3i6-k6z5 (2024 GIS release, for missing counties)');
    console.log('  CKD: duw2-7jbt (2022 release, KIDNEY measure)');

    const result = {};

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
            // Try primary dataset first
            let cityData = await fetchPrimary(locationId);
            let source = 'primary';

            // Fall back to GIS-friendly dataset if primary returns nothing
            // (e.g., Pennsylvania counties missing from 2023 data year)
            if (!cityData) {
                await delay(200);
                cityData = await fetchGISFallback(locationId);
                source = 'GIS fallback';
            }

            if (cityData) {
                // Fetch CKD rate from 2022 release (KIDNEY removed from 2025)
                await delay(200);
                const ckdRate = await fetchCKDRate(locationId);
                if (ckdRate !== null) {
                    cityData.ckdRate = ckdRate;
                }

                const count = Object.keys(cityData).length;
                result[cityInfo.city] = cityData;
                console.log(`  ${cityInfo.city} (${locationId}): ${count}/5 indicators [${source}]`);
            } else {
                console.warn(`  ${cityInfo.city} (${locationId}): no data from primary or fallback`);
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
        mergeDataFile('health-demographics.json', result, 'CDC PLACES API (5 county-level indicators, multi-release)');
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
