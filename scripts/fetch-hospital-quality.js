#!/usr/bin/env node
/**
 * Fetch hospital quality data from CMS Provider Data API.
 * Source: data.cms.gov/provider-data/
 * Auth: None required
 * Format: JSON
 */

const { fetchWithRetry, writeDataFile, updateMetadata, reportError, CITIES, delay } = require('./utils');

// CMS Hospital General Information dataset
const CMS_HOSPITALS_URL = 'https://data.cms.gov/provider-data/api/1/datastore/query/xubh-q36u/0';

// Map our cities to CMS city names (CMS uses uppercase)
const CITY_CMS_NAMES = {};
CITIES.forEach(c => {
    CITY_CMS_NAMES[c.city] = c.city.toUpperCase();
});

async function fetchHospitalQuality() {
    console.log('Fetching hospital quality data from CMS...');

    const centerReputation = {};

    try {
        // Fetch hospital ratings for cities with transplant centers
        for (const cityInfo of CITIES) {
            const cmsCity = CITY_CMS_NAMES[cityInfo.city];
            const url = `${CMS_HOSPITALS_URL}?conditions[0][property]=city&conditions[0][value]=${encodeURIComponent(cmsCity)}&conditions[1][property]=state&conditions[1][value]=${cityInfo.stateAbbr}&limit=50`;

            try {
                const response = await fetchWithRetry(url);
                const data = await response.json();

                if (data.results && data.results.length > 0) {
                    // Find hospitals with highest ratings
                    const ratings = data.results
                        .map(h => parseInt(h.hospital_overall_rating))
                        .filter(r => !isNaN(r) && r > 0);

                    if (ratings.length > 0) {
                        const avgRating = ratings.reduce((a, b) => a + b, 0) / ratings.length;
                        // Scale 1-5 CMS rating to 75-100 reputation score
                        centerReputation[cityInfo.city] = Math.round(75 + (avgRating / 5) * 25);
                    }
                }

                await delay(500);
            } catch (err) {
                console.warn(`Failed to fetch CMS data for ${cityInfo.city}: ${err.message}`);
            }
        }

        if (Object.keys(centerReputation).length > 0) {
            writeDataFile('hospital-quality.json', { centerReputation }, 'CMS Provider Data API');
            updateMetadata('hospital-quality', 'CMS Provider Data');
            console.log(`Fetched hospital data for ${Object.keys(centerReputation).length} cities.`);
        } else {
            console.warn('No hospital quality data retrieved.');
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
