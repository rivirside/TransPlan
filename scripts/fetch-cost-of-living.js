#!/usr/bin/env node
/**
 * Fetch cost of living data from BLS API v2.
 * Source: api.bls.gov/publicAPI/v2/
 * Auth: Free registration key (BLS_API_KEY env var)
 * Format: JSON
 */

const { fetchWithRetry, writeDataFile, updateMetadata, reportError, CITIES } = require('./utils');

const BLS_BASE = 'https://api.bls.gov/publicAPI/v2/timeseries/data/';

// BLS CPI-U series IDs for metro areas
// These are Consumer Price Index - All Urban Consumers series
const METRO_SERIES = {
    'New York': 'CUURS12ASA0',
    'Los Angeles': 'CUURS49ASA0',
    'Chicago': 'CUURS23ASA0',
    'Houston': 'CUURS37ASA0',
    'Dallas': 'CUURS37BSA0',
    'Philadelphia': 'CUURS12BSA0',
    'Miami': 'CUURS35ASA0',
    'San Francisco': 'CUURS49BSA0',
    'Seattle': 'CUURS49DSA0',
    'Minneapolis': 'CUURS24ASA0',
    'St. Louis': 'CUURS24BSA0',
    'Baltimore': 'CUURS35BSA0',
    'Pittsburgh': 'CUURS12DSA0',
    'Portland': 'CUURS49CSA0',
    'Cleveland': 'CUURS23BSA0'
};

// National average series for normalization
const NATIONAL_SERIES = 'CUSR0000SA0';

async function fetchCostOfLiving() {
    const apiKey = process.env.BLS_API_KEY;

    if (!apiKey) {
        console.warn('BLS_API_KEY not set. Using seed data.');
        updateMetadata('cost-of-living', 'BLS API (skipped - no key)', 'skipped');
        return;
    }

    console.log('Fetching cost of living data from BLS...');
    const year = new Date().getFullYear() - 1;

    const allSeries = [...Object.values(METRO_SERIES), NATIONAL_SERIES];

    try {
        const response = await fetchWithRetry(BLS_BASE, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                seriesid: allSeries,
                startyear: String(year),
                endyear: String(year),
                registrationkey: apiKey
            })
        });

        const data = await response.json();

        if (data.status !== 'REQUEST_SUCCEEDED' || !data.Results?.series) {
            throw new Error(`BLS API error: ${data.message || 'Unknown error'}`);
        }

        // Extract annual average values
        const seriesValues = {};
        for (const series of data.Results.series) {
            const annualData = series.data.find(d => d.period === 'M13') || series.data[0];
            if (annualData) {
                seriesValues[series.seriesID] = parseFloat(annualData.value);
            }
        }

        const nationalCPI = seriesValues[NATIONAL_SERIES];
        if (!nationalCPI) {
            throw new Error('Could not retrieve national CPI for normalization.');
        }

        // Compute cost of living index (national = 100)
        const result = {};
        for (const [city, seriesId] of Object.entries(METRO_SERIES)) {
            const cpi = seriesValues[seriesId];
            if (cpi) {
                result[city] = Math.round((cpi / nationalCPI) * 100);
            }
        }

        // Cities without direct BLS metro data - estimate from state/nearby
        const estimates = {
            'Madison': result['Minneapolis'] ? Math.round(result['Minneapolis'] * 0.99) : null,
            'Rochester': result['Minneapolis'] ? Math.round(result['Minneapolis'] * 0.93) : null,
            'Durham': result['Baltimore'] ? Math.round(result['Baltimore'] * 1.04) : null,
            'Nashville': result['Baltimore'] ? Math.round(result['Baltimore'] * 1.07) : null,
            'Omaha': result['Minneapolis'] ? Math.round(result['Minneapolis'] * 0.88) : null,
            'Indianapolis': result['Cleveland'] ? Math.round(result['Cleveland'] * 1.07) : null,
            'Palo Alto': result['San Francisco'] ? Math.round(result['San Francisco'] * 1.07) : null
        };

        for (const [city, val] of Object.entries(estimates)) {
            if (val && !result[city]) result[city] = val;
        }

        if (Object.keys(result).length > 0) {
            writeDataFile('cost-of-living.json', result, 'BLS API v2');
            updateMetadata('cost-of-living', 'BLS API');
            console.log(`Fetched cost of living for ${Object.keys(result).length} cities.`);
        } else {
            console.warn('No cost of living data retrieved.');
            updateMetadata('cost-of-living', 'BLS API', 'error');
        }
    } catch (err) {
        reportError('BLS API', err);
        updateMetadata('cost-of-living', 'BLS API', 'error');
    }
}

fetchCostOfLiving().catch(err => {
    reportError('BLS API', err);
    process.exit(1);
});
