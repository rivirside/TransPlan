#!/usr/bin/env node
/**
 * Fetch cost of living data from BLS API v2.
 * Source: api.bls.gov/publicAPI/v2/
 * Auth: Free registration key (BLS_API_KEY env var)
 * Format: JSON
 *
 * L-014 fix: Updated estimation ratios for cities without direct BLS data.
 * Nashville ratio corrected from 1.07x Baltimore to direct estimate based
 * on BLS South region data. Added comments explaining each estimation basis.
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
    'Cleveland': 'CUURS23BSA0'
    // NOTE: Portland (CUURS49ESA0) and Pittsburgh (CUURS12DSA0) use different
    // CPI base periods (Dec 2001 and Nov 1996 respectively) vs national
    // (1982-84=100), making direct ratio comparison invalid. They are
    // estimated from nearby metros in the estimates section below.
    // Previously Portland used CUURS49CSA0 which is actually Riverside, CA.
};

// National average series for normalization
const NATIONAL_SERIES = 'CUSR0000SA0';

async function fetchCostOfLiving() {
    const apiKey = process.env.BLS_API_KEY;

    if (!apiKey) {
        console.warn('BLS_API_KEY not set. Using seed data.');
        updateMetadata('cost-of-living', 'BLS API (skipped - no key)', 'skipped');
        if (process.env.CI) {
            console.error('ERROR: Missing credentials in CI environment. Set BLS_API_KEY.');
            process.exit(1);
        }
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

        // Cities without direct BLS metro data — estimate using regional
        // data and city-specific adjustments based on Census ACS median
        // household income ratios relative to nearest covered metro.
        //
        // L-014: Each estimate documented with reasoning and data source.
        const estimates = {
            // Madison, WI: College town, slightly below Minneapolis COL.
            // Census ACS 2023 median HHI: Madison $72k vs Minneapolis $73k (0.99x)
            'Madison': result['Minneapolis'] ? Math.round(result['Minneapolis'] * 0.99) : null,

            // Rochester, MN: Small city, well below Twin Cities metro.
            // Census ACS 2023 median HHI: Rochester $74k vs Minneapolis $73k but lower
            // housing costs. BLS Rochester-Austin MSA doesn't have CPI series.
            'Rochester': result['Minneapolis'] ? Math.round(result['Minneapolis'] * 0.90) : null,

            // Durham, NC: Research Triangle growth area. Higher than national avg.
            // Census ACS 2023 Durham $65k vs Baltimore $55k; Durham housing ~90% of Balt.
            // But Durham has seen rapid growth. Estimated slightly below Baltimore.
            'Durham': result['Baltimore'] ? Math.round(result['Baltimore'] * 0.96) : null,

            // Nashville, TN: Rapid post-2020 cost surge. Previously estimated at
            // 1.07x Baltimore which was too low.
            // Census ACS 2023 Nashville $67k; Zillow median rent ~$1,850/mo vs
            // Baltimore ~$1,600/mo. Nashville COL now ~105-110% of national average.
            // Using Houston as South proxy: Nashville ~1.10x Houston
            'Nashville': result['Houston'] ? Math.round(result['Houston'] * 1.10) : null,

            // Omaha, NE: Low-cost Midwest city.
            // Census ACS 2023 Omaha $69k vs Minneapolis $73k; housing significantly cheaper.
            'Omaha': result['Minneapolis'] ? Math.round(result['Minneapolis'] * 0.85) : null,

            // Indianapolis, IN: Below-average Midwest COL.
            // Census ACS 2023 Indianapolis $55k vs Cleveland $39k (different dynamics).
            // Use Chicago as proxy — Indianapolis is roughly 80% of Chicago COL.
            'Indianapolis': result['Chicago'] ? Math.round(result['Chicago'] * 0.80) : null,

            // Palo Alto, CA: Most expensive city in our set.
            // Zillow median home value ~$3.5M vs SF ~$1.4M. Palo Alto is within
            // the SF-Oakland-Hayward MSA but significantly more expensive due to
            // proximity to Stanford and tech HQs.
            'Palo Alto': result['San Francisco'] ? Math.round(result['San Francisco'] * 1.07) : null,

            // Portland, OR: BLS series CUURS49ESA0 uses Dec 2001 base period,
            // incompatible with 1982-84 national base. Estimated from Seattle.
            // BEA Regional Price Parity 2023: Portland ~95% of Seattle.
            'Portland': result['Seattle'] ? Math.round(result['Seattle'] * 0.95) : null,

            // Pittsburgh, PA: BLS series CUURS12DSA0 uses Nov 1996 base period,
            // incompatible with 1982-84 national base. Estimated from Philadelphia.
            // BEA Regional Price Parity 2023: Pittsburgh ~85% of Philadelphia.
            'Pittsburgh': result['Philadelphia'] ? Math.round(result['Philadelphia'] * 0.85) : null
        };

        for (const [city, val] of Object.entries(estimates)) {
            if (val && !result[city]) {
                result[city] = val;
                console.log(`  ${city}: estimated at ${val} (no direct BLS series)`);
            }
        }

        if (Object.keys(result).length > 0) {
            writeDataFile('cost-of-living.json', result, 'BLS API v2');
            updateMetadata('cost-of-living', 'BLS API');
            console.log(`Fetched cost of living for ${Object.keys(result).length} cities (${Object.keys(METRO_SERIES).length} direct, ${Object.keys(estimates).length} estimated).`);
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
