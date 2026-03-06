#!/usr/bin/env node
/**
 * Fetch traffic fatality data from NHTSA FARS API.
 * Source: crashviewer.nhtsa.dot.gov
 * Auth: None required
 * Format: JSON
 *
 * FIXME: The original CrashAPI/crashes/GetCrashesByLocation endpoint returns 403
 * since ~2025. Switched to GetFARSData endpoint. If this also fails, the entire
 * NHTSA FARS API may be permanently retired. Alternative: download CSV files from
 * nhtsa.gov/file-downloads/fars and process locally.
 *
 * L-016 fix: Uses per-capita normalization (per 100k population) instead of
 * dividing by 500 and capping at 2.0, which made all large states identical.
 */

const { fetchWithRetry, mergeDataFile, updateMetadata, reportError, CITIES } = require('./utils');

// FIXME: If GetFARSData also returns 403, try nhtsa.gov/file-downloads/fars CSV bulk data
const FARS_BASE = 'https://crashviewer.nhtsa.dot.gov/FARSData/GetFARSData';

// Map state abbreviations to FARS state codes
const STATE_FIPS = {};
CITIES.forEach(c => { STATE_FIPS[c.stateAbbr] = c.stateFips; });

// State populations (2023 Census estimates) for per-capita normalization
const STATE_POPULATIONS = {
    PA: 12972008, MD: 6180253, NY: 19677151, MN: 5717184,
    WI: 5910955, IL: 12582032, OH: 11756058, MO: 6196156,
    IN: 6876047, NE: 1978379, TN: 7126489, NC: 10835491,
    FL: 22610726, TX: 30503301, OR: 4233358, WA: 7812880,
    CA: 38965193
};

// Get unique states from our cities list
const UNIQUE_STATES = [...new Set(CITIES.map(c => c.stateAbbr))];

async function fetchStateFatalities() {
    console.log('Fetching traffic fatality data from NHTSA FARS...');
    const currentYear = new Date().getFullYear();
    // FARS data lags ~2 years; try year-2, fall back to year-3
    const yearsToTry = [currentYear - 2, currentYear - 3];

    const stateFatalityRates = {};
    const traumaScores = {};

    for (const stateAbbr of UNIQUE_STATES) {
        let fetched = false;
        for (const year of yearsToTry) {
            if (fetched) break;
            try {
                const url = `${FARS_BASE}?dataset=Accident&FromYear=${year}&ToYear=${year}&State=${STATE_FIPS[stateAbbr]}&format=json`;
                const response = await fetchWithRetry(url);
                const data = await response.json();

                // GetFARSData returns { Results: [...crash records...] }
                const crashes = Array.isArray(data?.Results) ? data.Results :
                                Array.isArray(data?.Results?.[0]) ? data.Results[0] : [];

                if (crashes.length === 0) continue; // Try next year

                // L-016: Sum actual FATALS field from crash records
                let totalFatalities = 0;
                for (const crash of crashes) {
                    totalFatalities += Number(crash.FATALS || crash.fatals || 1);
                }

                // Per-capita rate: fatalities per 100k population
                const population = STATE_POPULATIONS[stateAbbr] || 5000000;
                const ratePer100k = (totalFatalities / population) * 100000;

                const fullState = CITIES.find(c => c.stateAbbr === stateAbbr)?.state;
                if (fullState) {
                    stateFatalityRates[fullState] = parseFloat(ratePer100k.toFixed(2));
                }
                fetched = true;
            } catch (err) {
                console.warn(`Failed to fetch FARS data for ${stateAbbr} (${year}): ${err.message}`);
            }
        }
    }

    // Compute trauma scores per city (normalized 0-100 scale from per-capita rates)
    // US average is ~12-13 per 100k; range is roughly 5-25 per 100k
    for (const { city, stateAbbr } of CITIES) {
        const fullState = CITIES.find(c => c.stateAbbr === stateAbbr)?.state;
        const ratePer100k = stateFatalityRates[fullState] || 12;
        // Scale: 5 per 100k → score 25, 12 per 100k → score 50, 25 per 100k → score 100
        const score = Math.min(100, Math.max(0, Math.round((ratePer100k / 25) * 100)));
        traumaScores[city] = score;
    }

    // Only merge if we actually fetched some data; skip write if API was completely unreachable
    // to avoid overwriting seed data with empty/fallback values
    const stateCount = Object.keys(stateFatalityRates).length;
    if (stateCount > 0) {
        const output = { stateFatalityRates, traumaScores };
        mergeDataFile('traffic-fatalities.json', output, 'NHTSA FARS GetFARSData');
        updateMetadata('traffic-fatalities', 'NHTSA FARS', 'fetched');
    } else {
        console.warn('No FARS data retrieved — seed data preserved.');
        updateMetadata('traffic-fatalities', 'NHTSA FARS', 'error');
    }

    console.log(`Fetched fatality data for ${stateCount} states.`);
}

fetchStateFatalities().catch(err => {
    reportError('NHTSA FARS', err);
    process.exit(1);
});
