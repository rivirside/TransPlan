#!/usr/bin/env node
/**
 * Fetch traffic fatality data from NHTSA FARS CrashAPI.
 * Source: crashviewer.nhtsa.dot.gov/CrashAPI
 * Auth: None required
 * Format: JSON
 *
 * L-016 fix: Uses per-capita normalization (per 100k population) instead of
 * dividing by 500 and capping at 2.0, which made all large states identical.
 */

const { fetchWithRetry, mergeDataFile, updateMetadata, reportError, CITIES } = require('./utils');

const FARS_BASE = 'https://crashviewer.nhtsa.dot.gov/CrashAPI/crashes/GetCrashesByLocation';

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
    const year = new Date().getFullYear() - 2; // FARS data typically 2 years behind

    const stateFatalityRates = {};
    const traumaScores = {};

    for (const stateAbbr of UNIQUE_STATES) {
        try {
            const url = `${FARS_BASE}?fromCaseYear=${year}&toCaseYear=${year}&state=${STATE_FIPS[stateAbbr]}&format=json`;
            const response = await fetchWithRetry(url);
            const data = await response.json();

            // L-016: Sum actual FATALS field from crash records instead of using array length
            const crashes = data?.Results?.[0] || [];
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
        } catch (err) {
            console.warn(`Failed to fetch FARS data for ${stateAbbr}: ${err.message}`);
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
    if (Object.keys(stateFatalityRates).length > 0) {
        const output = { stateFatalityRates, traumaScores };
        mergeDataFile('traffic-fatalities.json', output, 'NHTSA FARS CrashAPI');
    } else {
        console.warn('No FARS data retrieved — seed data preserved.');
    }
    updateMetadata('traffic-fatalities', 'NHTSA FARS');

    console.log(`Fetched fatality data for ${Object.keys(stateFatalityRates).length} states.`);
}

fetchStateFatalities().catch(err => {
    reportError('NHTSA FARS', err);
    process.exit(1);
});
