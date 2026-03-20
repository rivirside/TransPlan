#!/usr/bin/env node
/**
 * Fetch health demographics for ALL ~3,000 US counties from CDC PLACES API.
 *
 * Primary source: data.cdc.gov/resource/swc5-untb.json
 *   (PLACES: Local Data for Better Health, County Data, 2025 release)
 *
 * Fallback source: data.cdc.gov/resource/d3i6-k6z5.json
 *   (PLACES: County Data GIS Friendly Format, 2024 release)
 *   Used for counties missing from the 2023 data year in the primary dataset
 *   (e.g., all Pennsylvania counties have only 2022 screening data, not
 *   the 2023 health risk measures like DIABETES/OBESITY/BPHIGH/CSMOKING).
 *
 * Auth: None required (public API)
 *
 * Phase 6B issue #126: Expands health data from 22 cities (~20 points)
 * to ~3,000 counties for dense spatial interpolation surfaces.
 *
 * Output: data/health-demographics-counties.json
 * Format: { counties: { "FIPS": { name, state, lat, lon, diabetesRate, ... } } }
 *
 * Note: CDC PLACES does not include a KIDNEY/CKD measure in the 2025 release.
 * Only 4 of 5 indicators are available at county level.
 */

const { fetchWithRetry, writeDataFile, updateMetadata, reportError, delay } = require('./utils');

// CDC PLACES County-Level Data (SODA API) — 2025 release (primary)
const CDC_PLACES_URL = 'https://data.cdc.gov/resource/swc5-untb.json';

// CDC PLACES County Data GIS Friendly — 2024 release (fallback for missing counties)
const CDC_PLACES_GIS_URL = 'https://data.cdc.gov/resource/d3i6-k6z5.json';

// Map CDC PLACES measureid -> our field names
// Note: KIDNEY is NOT available in CDC PLACES 2025 release
const MEASURES = {
    'DIABETES': 'diabetesRate',
    'OBESITY': 'obesityRate',
    'BPHIGH': 'hypertensionRate',
    'CSMOKING': 'smokingRate'
};

// Map GIS-friendly column names -> our field names (fallback dataset)
const GIS_COLUMNS = {
    'diabetes_adjprev': 'diabetesRate',
    'obesity_adjprev': 'obesityRate',
    'bphigh_adjprev': 'hypertensionRate',
    'csmoking_adjprev': 'smokingRate'
};

const MEASURE_LIST = Object.keys(MEASURES).map(m => `'${m}'`).join(',');
const PAGE_SIZE = 50000;
const GIS_PAGE_SIZE = 50000;

/**
 * Fetch all counties from the primary dataset (swc5-untb, 2025 release).
 * Returns a map of FIPS -> county data objects.
 */
async function fetchPrimaryCounties() {
    console.log('  [Primary] Fetching from swc5-untb (2025 release)...');
    const counties = {};
    let offset = 0;
    let totalRows = 0;

    while (true) {
        const query = [
            `$where=measureid in(${MEASURE_LIST}) AND datavaluetypeid='AgeAdjPrv'`,
            `$select=locationid,locationname,stateabbr,measureid,data_value,geolocation`,
            `$order=locationid,measureid`,
            `$limit=${PAGE_SIZE}`,
            `$offset=${offset}`
        ].join('&');

        const url = `${CDC_PLACES_URL}?${query}`;
        console.log(`    Fetching page at offset ${offset}...`);

        let data;
        try {
            const response = await fetchWithRetry(url);
            data = await response.json();
        } catch (err) {
            console.error(`    Failed to fetch at offset ${offset}: ${err.message}`);
            break;
        }

        if (!data || data.length === 0) break;

        for (const row of data) {
            const fips = row.locationid;
            const fieldName = MEASURES[row.measureid];
            if (!fips || !fieldName) continue;

            const val = parseFloat(row.data_value);
            if (isNaN(val)) continue;

            if (!counties[fips]) {
                counties[fips] = {
                    name: row.locationname || '',
                    state: row.stateabbr || '',
                };

                // Extract lat/lon from geolocation GeoJSON Point
                // Format: {"type":"Point","coordinates":[-91.72, 33.59]}
                // Note: GeoJSON is [lon, lat], we store as lat, lon
                if (row.geolocation && row.geolocation.coordinates) {
                    counties[fips].lon = row.geolocation.coordinates[0];
                    counties[fips].lat = row.geolocation.coordinates[1];
                }
            }

            counties[fips][fieldName] = val;
        }

        totalRows += data.length;
        console.log(`    Got ${data.length} rows (total: ${totalRows})`);

        if (data.length < PAGE_SIZE) break;
        offset += PAGE_SIZE;
        await delay(500);
    }

    return { counties, totalRows };
}

/**
 * Identify which FIPS codes exist in the 2022 data but have no health risk
 * measures (they only have screening measures like COLON_SCREEN, DENTAL, etc.).
 * These are the counties we need to backfill from the GIS fallback.
 */
async function findMissingCountyFips(existingFips) {
    console.log('  [Gap Detection] Checking for counties with only screening data...');

    // Query distinct locationids from 2022 data (the ones with only 5 screening measures)
    const query = [
        `$select=distinct locationid`,
        `$where=year='2022'`,
        `$limit=50000`
    ].join('&');

    const url = `${CDC_PLACES_URL}?${query}`;
    try {
        const response = await fetchWithRetry(url);
        const data = await response.json();

        if (!data || data.length === 0) return [];

        // Find FIPS that are in 2022 data but NOT in our primary results
        const missing = [];
        for (const row of data) {
            const fips = row.locationid;
            if (fips && !existingFips.has(fips)) {
                missing.push(fips);
            }
        }

        console.log(`    Found ${missing.length} counties missing from primary results`);
        return missing;
    } catch (err) {
        console.warn(`    Gap detection failed: ${err.message}`);
        return [];
    }
}

/**
 * Fetch missing counties from the GIS-friendly fallback dataset (d3i6-k6z5).
 * Uses wide-format columns and paginates to get all missing counties.
 */
async function fetchGISFallbackCounties(missingFips) {
    if (missingFips.length === 0) return {};

    console.log(`  [GIS Fallback] Fetching ${missingFips.length} missing counties from d3i6-k6z5 (2024 release)...`);
    const counties = {};
    const gisColumns = Object.keys(GIS_COLUMNS).join(',');

    // Build FIPS set for fast lookup
    const missingSet = new Set(missingFips);

    // Paginate through the entire GIS dataset and filter client-side
    // (The GIS dataset has one row per county, so ~3,200 total rows)
    let offset = 0;
    let totalRows = 0;

    while (true) {
        const query = [
            `$select=countyfips,countyname,stateabbr,${gisColumns},geolocation`,
            `$order=countyfips`,
            `$limit=${GIS_PAGE_SIZE}`,
            `$offset=${offset}`
        ].join('&');

        const url = `${CDC_PLACES_GIS_URL}?${query}`;
        console.log(`    Fetching GIS page at offset ${offset}...`);

        let data;
        try {
            const response = await fetchWithRetry(url);
            data = await response.json();
        } catch (err) {
            console.error(`    GIS fallback failed at offset ${offset}: ${err.message}`);
            break;
        }

        if (!data || data.length === 0) break;

        for (const row of data) {
            const fips = row.countyfips;
            if (!fips || !missingSet.has(fips)) continue;

            const countyData = {
                name: row.countyname || '',
                state: row.stateabbr || '',
            };

            // Extract lat/lon from geolocation
            if (row.geolocation && row.geolocation.coordinates) {
                countyData.lon = row.geolocation.coordinates[0];
                countyData.lat = row.geolocation.coordinates[1];
            }

            let hasData = false;
            for (const [col, fieldName] of Object.entries(GIS_COLUMNS)) {
                const val = parseFloat(row[col]);
                if (!isNaN(val)) {
                    countyData[fieldName] = val;
                    hasData = true;
                }
            }

            if (hasData) {
                counties[fips] = countyData;
            }
        }

        totalRows += data.length;

        if (data.length < GIS_PAGE_SIZE) break;
        offset += GIS_PAGE_SIZE;
        await delay(500);
    }

    console.log(`    Recovered ${Object.keys(counties).length} counties from GIS fallback`);
    return counties;
}

async function fetchAllCounties() {
    console.log('Fetching health demographics for ALL US counties from CDC PLACES...');
    console.log(`Measures: ${Object.keys(MEASURES).join(', ')}`);

    // Step 1: Fetch from primary dataset
    const { counties: primaryCounties, totalRows } = await fetchPrimaryCounties();
    const primaryCount = Object.keys(primaryCounties).length;
    console.log(`  [Primary] ${primaryCount} counties with health risk data`);

    // Step 2: Find counties that exist in 2022 data but have no risk measures
    const primaryFips = new Set(Object.keys(primaryCounties));
    await delay(500);
    const missingFips = await findMissingCountyFips(primaryFips);

    // Step 3: Backfill from GIS-friendly dataset
    let fallbackCounties = {};
    if (missingFips.length > 0) {
        await delay(500);
        fallbackCounties = await fetchGISFallbackCounties(missingFips);
    }

    // Step 4: Merge primary + fallback
    const allCounties = { ...primaryCounties, ...fallbackCounties };
    const fallbackCount = Object.keys(fallbackCounties).length;

    // Filter out counties without coordinates (needed for spatial interpolation)
    const withCoords = {};
    let noCoords = 0;
    for (const [fips, county] of Object.entries(allCounties)) {
        if (county.lat != null && county.lon != null) {
            withCoords[fips] = county;
        } else {
            noCoords++;
        }
    }

    const countyCount = Object.keys(withCoords).length;
    if (countyCount > 0) {
        writeDataFile('health-demographics-counties.json',
            { counties: withCoords },
            `CDC PLACES API (${countyCount} counties: ${primaryCount} primary + ${fallbackCount} GIS fallback, 4 indicators, age-adjusted prevalence)`
        );
        updateMetadata('health-demographics-counties', 'CDC PLACES API', 'fetched');
        console.log(`\nFetched health data for ${countyCount} counties (${fallbackCount} from GIS fallback, ${noCoords} skipped — no coordinates).`);
        console.log(`Total rows processed: ${totalRows}`);
    } else {
        console.warn('\nNo county health data retrieved.');
        updateMetadata('health-demographics-counties', 'CDC PLACES API', 'error');
    }
}

fetchAllCounties().catch(err => {
    reportError('CDC PLACES (counties)', err);
    process.exit(1);
});
