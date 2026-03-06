#!/usr/bin/env node
/**
 * Fetch hospital quality data from CMS Provider Data API.
 * Source: data.cms.gov/provider-data/
 * Auth: None required
 * Format: JSON
 *
 * Uses multiple query strategies in case the API syntax changes.
 * Once a working strategy is found for the first city, it is reused
 * for all remaining cities to avoid retrying dead endpoints.
 *
 * FIXME: CMS dataset ID 'xubh-q36u' is for "Hospital General Information".
 * If this ID becomes invalid, check data.cms.gov/provider-data/ for the
 * current dataset ID, or use the CSV download endpoint as fallback:
 * https://data.cms.gov/provider-data/api/1/datastore/query/xubh-q36u/0/download?format=csv
 */

const { fetchWithRetry, mergeDataFile, updateMetadata, reportError, CITIES, delay } = require('./utils');

// CMS Provider Data API base
const CMS_DATASET_ID = 'xubh-q36u'; // FIXME: dataset ID may change if CMS reorganizes
const CMS_BASE = 'https://data.cms.gov/provider-data/api/1';

// Strategy 1: SQL-based query (most flexible, newer API)
function buildSqlUrl(city, stateAbbr) {
    const escapedCity = city.toUpperCase().replace(/'/g, "''");
    const query = encodeURIComponent(
        `SELECT facility_name, city, state, hospital_overall_rating ` +
        `FROM ${CMS_DATASET_ID} ` +
        `WHERE UPPER(city) = '${escapedCity}' AND state = '${stateAbbr}' ` +
        `LIMIT 50`
    );
    return `${CMS_BASE}/datastore/sql?query=[${query}]`;
}

// Strategy 2: New filter syntax (per CMS FAQ)
function buildFilterUrl(city, stateAbbr) {
    const cmsCity = encodeURIComponent(city.toUpperCase());
    return `${CMS_BASE}/datastore/query/${CMS_DATASET_ID}/0` +
        `?filter[conditions][0][property]=city&filter[conditions][0][value]=${cmsCity}` +
        `&filter[conditions][1][property]=state&filter[conditions][1][value]=${stateAbbr}` +
        `&limit=50`;
}

// Strategy 3: Legacy conditions syntax (original, may still work)
function buildLegacyUrl(city, stateAbbr) {
    const cmsCity = encodeURIComponent(city.toUpperCase());
    return `${CMS_BASE}/datastore/query/${CMS_DATASET_ID}/0` +
        `?conditions[0][property]=city&conditions[0][value]=${cmsCity}` +
        `&conditions[1][property]=state&conditions[1][value]=${stateAbbr}` +
        `&limit=50`;
}

const URL_STRATEGIES = [
    { name: 'SQL', build: buildSqlUrl },
    { name: 'filter', build: buildFilterUrl },
    { name: 'legacy', build: buildLegacyUrl }
];

/**
 * Extract hospital ratings from a CMS API response.
 * Handles both SQL (returns array) and query (returns { results: [...] }) formats.
 */
function extractRatings(data) {
    const results = Array.isArray(data) ? data : (data?.results || []);
    return results
        .map(h => parseInt(h.hospital_overall_rating))
        .filter(r => !isNaN(r) && r > 0);
}

async function fetchHospitalQuality() {
    console.log('Fetching hospital quality data from CMS...');

    const centerReputation = {};
    let workingStrategy = null;

    try {
        for (const cityInfo of CITIES) {
            const strategies = workingStrategy ? [workingStrategy] : URL_STRATEGIES;

            let fetched = false;
            for (const strategy of strategies) {
                if (fetched) break;
                try {
                    const url = strategy.build(cityInfo.city, cityInfo.stateAbbr);
                    const response = await fetchWithRetry(url);
                    const data = await response.json();

                    const ratings = extractRatings(data);
                    if (ratings.length > 0) {
                        const avgRating = ratings.reduce((a, b) => a + b, 0) / ratings.length;
                        // Scale 1-5 CMS rating to 75-100 reputation score
                        centerReputation[cityInfo.city] = Math.round(75 + (avgRating / 5) * 25);
                        if (!workingStrategy) {
                            console.log(`CMS API: '${strategy.name}' strategy succeeded.`);
                        }
                        workingStrategy = strategy;
                        fetched = true;
                    }
                } catch (err) {
                    // Strategy failed for this city; try next
                    if (!workingStrategy) {
                        console.warn(`CMS '${strategy.name}' strategy failed for ${cityInfo.city}: ${err.message}`);
                    }
                }
            }

            await delay(500);
        }

        const cityCount = Object.keys(centerReputation).length;
        if (cityCount > 0) {
            // L-031 fix: Use mergeDataFile to preserve existing keys (centerVolumes,
            // specializations, insuranceAcceptanceRates) that this script doesn't fetch.
            mergeDataFile('hospital-quality.json', { centerReputation }, 'CMS Provider Data API (centerReputation updated)');
            updateMetadata('hospital-quality', 'CMS Provider Data', 'fetched');
            console.log(`Fetched hospital data for ${cityCount} cities.`);
        } else {
            console.warn('No hospital quality data retrieved — seed data preserved.');
            updateMetadata('hospital-quality', 'CMS Provider Data', 'error');
        }
    } catch (err) {
        reportError('CMS Provider Data', err);
        updateMetadata('hospital-quality', 'CMS Provider Data', 'error');
    }
}

fetchHospitalQuality().catch(err => {
    reportError('CMS Provider Data', err);
    process.exit(1);
});
