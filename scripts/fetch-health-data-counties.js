#!/usr/bin/env node
/**
 * Fetch health demographics for ALL ~3,000 US counties from CDC PLACES API.
 * Source: data.cdc.gov/resource/swc5-untb.json (PLACES: County Data)
 * Auth: None required (public API)
 *
 * Phase 6B issue #126: Expands health data from 22 cities (~20 points)
 * to ~3,000 counties for dense spatial interpolation surfaces.
 *
 * Output: data/health-demographics-counties.json
 * Format: { counties: { "FIPS": { name, state, lat, lon, diabetesRate, ... } } }
 *
 * Note: CDC PLACES does not include a KIDNEY/CKD measure.
 * Only 4 of 5 indicators are available at county level.
 */

const { fetchWithRetry, writeDataFile, updateMetadata, reportError, delay } = require('./utils');

const CDC_PLACES_URL = 'https://data.cdc.gov/resource/swc5-untb.json';

// Map CDC PLACES measureid → our field names
// Note: KIDNEY is NOT available in CDC PLACES (only in seed data)
const MEASURES = {
    'DIABETES': 'diabetesRate',
    'OBESITY': 'obesityRate',
    'BPHIGH': 'hypertensionRate',
    'CSMOKING': 'smokingRate'
};

const MEASURE_LIST = Object.keys(MEASURES).map(m => `'${m}'`).join(',');
const PAGE_SIZE = 50000;

async function fetchAllCounties() {
    console.log('Fetching health demographics for ALL US counties from CDC PLACES...');
    console.log(`Measures: ${Object.keys(MEASURES).join(', ')}`);

    const counties = {};
    let offset = 0;
    let totalRows = 0;

    // Paginate through all results
    while (true) {
        const query = [
            `$where=measureid in(${MEASURE_LIST}) AND datavaluetypeid='AgeAdjPrv'`,
            `$select=locationid,locationname,stateabbr,measureid,data_value,geolocation`,
            `$order=locationid,measureid`,
            `$limit=${PAGE_SIZE}`,
            `$offset=${offset}`
        ].join('&');

        const url = `${CDC_PLACES_URL}?${query}`;
        console.log(`  Fetching page at offset ${offset}...`);

        let data;
        try {
            const response = await fetchWithRetry(url);
            data = await response.json();
        } catch (err) {
            console.error(`  Failed to fetch at offset ${offset}: ${err.message}`);
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
        console.log(`  Got ${data.length} rows (total: ${totalRows})`);

        if (data.length < PAGE_SIZE) break;
        offset += PAGE_SIZE;
        await delay(500);
    }

    // Filter out counties without coordinates (needed for spatial interpolation)
    const withCoords = {};
    let noCoords = 0;
    for (const [fips, county] of Object.entries(counties)) {
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
            `CDC PLACES API (${countyCount} counties, 4 indicators, age-adjusted prevalence)`
        );
        updateMetadata('health-demographics-counties', 'CDC PLACES API', 'fetched');
        console.log(`\nFetched health data for ${countyCount} counties (${noCoords} skipped — no coordinates).`);
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
