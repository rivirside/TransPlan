#!/usr/bin/env node
/**
 * Fetch traffic fatality data from NHTSA FARS CrashAPI.
 * Source: crashviewer.nhtsa.dot.gov/CrashAPI
 * Auth: None required
 * Format: JSON
 */

const { fetchWithRetry, writeDataFile, updateMetadata, reportError, CITIES } = require('./utils');

const FARS_BASE = 'https://crashviewer.nhtsa.dot.gov/CrashAPI/crashes/GetCrashesByLocation';

// Map state abbreviations to FARS state codes
const STATE_FIPS = {};
CITIES.forEach(c => { STATE_FIPS[c.stateAbbr] = c.stateFips; });

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

            const totalFatalities = data?.Results?.[0]?.length || 0;
            // Normalize to a per-100k rate approximation
            const rate = Math.min(2.0, totalFatalities / 500);
            const fullState = CITIES.find(c => c.stateAbbr === stateAbbr)?.state;
            if (fullState) {
                stateFatalityRates[fullState] = parseFloat(rate.toFixed(2));
            }
        } catch (err) {
            console.warn(`Failed to fetch FARS data for ${stateAbbr}: ${err.message}`);
        }
    }

    // Compute trauma scores per city (higher traffic = more deceased donors)
    for (const { city, stateAbbr } of CITIES) {
        const fullState = CITIES.find(c => c.stateAbbr === stateAbbr)?.state;
        const rate = stateFatalityRates[fullState] || 1.0;
        traumaScores[city] = Math.round(Math.min(100, rate * 50));
    }

    const output = { stateFatalityRates, traumaScores };
    writeDataFile('traffic-fatalities.json', output, 'NHTSA FARS CrashAPI');
    updateMetadata('traffic-fatalities', 'NHTSA FARS');

    console.log(`Fetched fatality data for ${Object.keys(stateFatalityRates).length} states.`);
}

fetchStateFatalities().catch(err => {
    reportError('NHTSA FARS', err);
    process.exit(1);
});
