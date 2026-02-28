#!/usr/bin/env node
/**
 * Fetch health demographics data from CDC SODA API.
 * Primary: data.cdc.gov SODA API
 * Fallback: CDC WONDER XML
 * Auth: None required
 * Format: JSON
 */

const { fetchWithRetry, writeDataFile, updateMetadata, reportError, CITIES, delay } = require('./utils');

// CDC SODA API endpoints
// BRFSS (Behavioral Risk Factor Surveillance System) data
const CDC_BRFSS_URL = 'https://data.cdc.gov/resource/dttw-5yxu.json';

// State abbreviation to full name mapping
const STATE_MAP = {};
CITIES.forEach(c => { STATE_MAP[c.stateAbbr] = c.state; });
const UNIQUE_STATES = [...new Set(CITIES.map(c => c.state))];

async function fetchHealthData() {
    console.log('Fetching health demographics from CDC SODA API...');

    const stateData = {};

    // Fetch diabetes, obesity, and related health indicators by state
    for (const state of UNIQUE_STATES) {
        try {
            // Diabetes prevalence
            const diabetesUrl = `${CDC_BRFSS_URL}?$where=locationdesc='${encodeURIComponent(state)}'&$limit=10&$order=year DESC`;
            const response = await fetchWithRetry(diabetesUrl);
            const data = await response.json();

            if (data && data.length > 0) {
                // Extract most recent year's data
                const latest = data[0];
                stateData[state] = {
                    diabetesRate: parseFloat(latest.data_value) || null,
                    year: latest.year
                };
            }

            await delay(500);
        } catch (err) {
            console.warn(`Failed to fetch CDC data for ${state}: ${err.message}`);
        }
    }

    // Build city-level health demographics
    const result = {};
    for (const cityInfo of CITIES) {
        const state = cityInfo.state;
        const sd = stateData[state];

        if (sd && sd.diabetesRate) {
            // Use state-level data as baseline, add city-level adjustments
            result[cityInfo.city] = {
                diabetesRate: sd.diabetesRate
            };
        }
    }

    if (Object.keys(result).length > 0) {
        writeDataFile('health-demographics.json', result, 'CDC SODA API (BRFSS)');
        updateMetadata('health-demographics', 'CDC SODA API');
        console.log(`Fetched health data for ${Object.keys(result).length} cities.`);
    } else {
        console.warn('No health demographics data retrieved. Seed data will be used.');
        updateMetadata('health-demographics', 'CDC SODA API', 'error');
    }
}

fetchHealthData().catch(err => {
    reportError('CDC SODA API', err);
    process.exit(1);
});
