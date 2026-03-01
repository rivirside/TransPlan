/**
 * TransPlan Data Loader
 *
 * Fetches JSON data files from the data/ directory at runtime.
 * Falls back to hardcoded defaults if any fetch fails.
 * Exposes loaded data on window.TransPlanData.
 * Shows a data freshness banner based on age of data.
 */

(function () {
    'use strict';

    const DATA_FILES = {
        airQuality: 'data/air-quality.json',
        trafficFatalities: 'data/traffic-fatalities.json',
        healthDemographics: 'data/health-demographics.json',
        hospitalQuality: 'data/hospital-quality.json',
        costOfLiving: 'data/cost-of-living.json',
        donorRegistration: 'data/donor-registration.json',
        metadata: 'data/metadata.json',
        // L-034: srtr-reports.json removed from runtime loading — data was never
        // read by algorithm.js (dead path). File kept as documentation artifact.
        climateScores: 'data/manual/climate-scores.json',
        policyTiers: 'data/manual/policy-tiers.json',
        socioeconomic: 'data/manual/socioeconomic.json'
    };

    // Hardcoded fallback defaults (copied from algorithm.js/script.js)
    const DEFAULTS = {
        airQuality: {
            "Pittsburgh": 68, "Baltimore": 62, "Philadelphia": 64, "New York": 58,
            "Minneapolis": 78, "Madison": 82, "Chicago": 61, "Cleveland": 65,
            "St. Louis": 66, "Indianapolis": 67, "Omaha": 74, "Rochester": 80,
            "Nashville": 69, "Durham": 71, "Miami": 65, "Dallas": 63,
            "Houston": 59, "Portland": 76, "Seattle": 77, "San Francisco": 68,
            "Los Angeles": 45, "Palo Alto": 72
        },
        trafficFatalities: {
            traumaScores: {
                "Los Angeles": 85, "Houston": 82, "Miami": 80, "Dallas": 78,
                "Nashville": 72, "Pittsburgh": 65, "Cleveland": 68,
                "Baltimore": 70, "Chicago": 75, "Philadelphia": 72, "Indianapolis": 70,
                "St. Louis": 72, "Minneapolis": 62, "Seattle": 58, "Portland": 60,
                "San Francisco": 65, "Rochester": 55, "Madison": 52, "Palo Alto": 62,
                "Durham": 68, "Omaha": 65, "New York": 70
            }
        },
        healthDemographics: {
            "Pittsburgh": { diabetesRate: 10.2, obesityRate: 31.5, ckdRate: 14.2, hypertensionRate: 32.1, smokingRate: 19.3 },
            "Baltimore": { diabetesRate: 11.8, obesityRate: 34.2, ckdRate: 15.8, hypertensionRate: 35.4, smokingRate: 17.9 },
            "Philadelphia": { diabetesRate: 11.4, obesityRate: 33.8, ckdRate: 15.2, hypertensionRate: 34.2, smokingRate: 18.5 },
            "New York": { diabetesRate: 10.9, obesityRate: 28.5, ckdRate: 14.5, hypertensionRate: 31.8, smokingRate: 14.2 },
            "Minneapolis": { diabetesRate: 8.1, obesityRate: 27.3, ckdRate: 12.4, hypertensionRate: 28.5, smokingRate: 15.8 },
            "Madison": { diabetesRate: 7.9, obesityRate: 26.8, ckdRate: 12.1, hypertensionRate: 27.9, smokingRate: 14.9 },
            "Chicago": { diabetesRate: 10.5, obesityRate: 32.1, ckdRate: 14.8, hypertensionRate: 33.2, smokingRate: 16.7 },
            "Cleveland": { diabetesRate: 11.2, obesityRate: 33.5, ckdRate: 15.3, hypertensionRate: 34.8, smokingRate: 20.1 },
            "St. Louis": { diabetesRate: 10.8, obesityRate: 32.7, ckdRate: 14.9, hypertensionRate: 33.9, smokingRate: 19.5 },
            "Indianapolis": { diabetesRate: 11.5, obesityRate: 34.8, ckdRate: 15.7, hypertensionRate: 35.2, smokingRate: 21.3 },
            "Omaha": { diabetesRate: 9.8, obesityRate: 31.2, ckdRate: 13.9, hypertensionRate: 31.5, smokingRate: 17.8 },
            "Rochester": { diabetesRate: 8.5, obesityRate: 28.9, ckdRate: 12.8, hypertensionRate: 29.3, smokingRate: 15.2 },
            "Nashville": { diabetesRate: 12.3, obesityRate: 36.2, ckdRate: 16.5, hypertensionRate: 37.1, smokingRate: 22.8 },
            "Durham": { diabetesRate: 11.1, obesityRate: 33.1, ckdRate: 15.1, hypertensionRate: 34.5, smokingRate: 18.9 },
            "Miami": { diabetesRate: 12.8, obesityRate: 32.5, ckdRate: 16.8, hypertensionRate: 36.2, smokingRate: 16.4 },
            "Dallas": { diabetesRate: 11.9, obesityRate: 33.9, ckdRate: 15.9, hypertensionRate: 35.8, smokingRate: 17.2 },
            "Houston": { diabetesRate: 12.5, obesityRate: 34.7, ckdRate: 16.3, hypertensionRate: 36.5, smokingRate: 16.8 },
            "Portland": { diabetesRate: 8.7, obesityRate: 29.1, ckdRate: 13.1, hypertensionRate: 29.8, smokingRate: 15.3 },
            "Seattle": { diabetesRate: 8.3, obesityRate: 27.8, ckdRate: 12.6, hypertensionRate: 28.9, smokingRate: 14.8 },
            "San Francisco": { diabetesRate: 8.9, obesityRate: 26.2, ckdRate: 13.3, hypertensionRate: 29.1, smokingRate: 13.5 },
            "Los Angeles": { diabetesRate: 10.3, obesityRate: 30.4, ckdRate: 14.6, hypertensionRate: 32.4, smokingRate: 14.9 },
            "Palo Alto": { diabetesRate: 7.8, obesityRate: 24.1, ckdRate: 11.9, hypertensionRate: 27.2, smokingRate: 11.8 }
        },
        costOfLiving: {
            "San Francisco": 191, "Palo Alto": 204, "New York": 187,
            "Los Angeles": 150, "Seattle": 145, "Baltimore": 89,
            "Pittsburgh": 85, "Minneapolis": 98, "Madison": 97,
            "Portland": 135, "Chicago": 102, "Philadelphia": 101,
            "Dallas": 92, "Houston": 90, "Miami": 112,
            "Nashville": 95, "Durham": 93, "Cleveland": 81,
            "St. Louis": 83, "Rochester": 91, "Omaha": 86,
            "Indianapolis": 87
        },
        climateScores: {
            "San Francisco": 92, "Los Angeles": 88, "Palo Alto": 91,
            "Miami": 75, "Seattle": 82, "Portland": 83,
            "Minneapolis": 62, "Madison": 64, "Rochester": 60,
            "Pittsburgh": 71, "Baltimore": 73, "Philadelphia": 72,
            "Chicago": 67, "Cleveland": 66, "St. Louis": 70,
            "Nashville": 78, "Durham": 77, "Dallas": 72,
            "Houston": 71, "New York": 70, "Omaha": 68,
            "Indianapolis": 69
        },
        donorRegistration: {
            stateRegistrationRates: {
                "Montana": 82, "Alaska": 75, "Minnesota": 68, "Oregon": 58,
                "Washington": 56, "Wisconsin": 54, "New York": 52, "Massachusetts": 51,
                "Pennsylvania": 42, "Ohio": 41, "Maryland": 40, "Illinois": 48,
                "California": 45, "North Carolina": 37, "Tennessee": 31,
                "Texas": 30, "Florida": 68, "Georgia": 28, "Indiana": 36,
                "Nebraska": 47, "Missouri": 32, "Iowa": 50
            },
            livingDonorProgramStrength: {
                "Minneapolis": 95, "Madison": 92, "Pittsburgh": 94,
                "Cleveland": 93, "Los Angeles": 91, "San Francisco": 90,
                "Baltimore": 89, "Rochester": 91, "Durham": 88,
                "Chicago": 86, "Houston": 87, "Palo Alto": 89,
                "Nashville": 84, "Philadelphia": 85, "St. Louis": 83,
                "Portland": 86, "Seattle": 87, "Dallas": 82,
                "Miami": 81, "New York": 84, "Omaha": 85,
                "Indianapolis": 80
            },
            populationFactors: {
                "New York": 100, "Los Angeles": 95, "Chicago": 90,
                "Houston": 88, "Philadelphia": 85, "San Francisco": 82,
                "Miami": 80, "Dallas": 85, "Baltimore": 75,
                "Pittsburgh": 68, "Cleveland": 70, "Minneapolis": 72,
                "Seattle": 74, "Nashville": 71, "Durham": 68,
                "St. Louis": 67, "Rochester": 60, "Madison": 62,
                "Portland": 70, "Palo Alto": 78, "Indianapolis": 69,
                "Omaha": 58
            }
        },
        hospitalQuality: {
            // L-010: Real volumes from SRTR Program-Specific Reports + center press releases (2023-2024)
            centerVolumes: {
                kidney: { "Pittsburgh": 350, "Minneapolis": 280, "Baltimore": 220, "Cleveland": 330, "Los Angeles": 324, "San Francisco": 325, "Rochester": 260, "Madison": 298, "Chicago": 343, "Philadelphia": 290, "Nashville": 374, "Durham": 250, "Houston": 287, "Dallas": 220, "Miami": 210, "Palo Alto": 200, "Portland": 200, "Seattle": 210, "St. Louis": 300, "New York": 339, "Omaha": 188, "Indianapolis": 280 },
                liver: { "Pittsburgh": 280, "Los Angeles": 136, "San Francisco": 280, "Baltimore": 100, "Cleveland": 258, "Rochester": 200, "Minneapolis": 180, "Dallas": 165, "Houston": 293, "Chicago": 150, "Philadelphia": 175, "Miami": 160, "Durham": 170, "Nashville": 208, "Madison": 112, "Palo Alto": 130, "Seattle": 120, "Portland": 90, "St. Louis": 150, "New York": 127, "Omaha": 150, "Indianapolis": 215 },
                heart: { "Cleveland": 67, "Nashville": 174, "Durham": 120, "Houston": 60, "Palo Alto": 85, "Los Angeles": 95, "Pittsburgh": 75, "Chicago": 37, "San Francisco": 80, "Baltimore": 20, "Minneapolis": 55, "Philadelphia": 65, "St. Louis": 50, "Rochester": 45, "Madison": 25, "Dallas": 55, "Seattle": 45, "Miami": 40, "Portland": 30, "New York": 77, "Omaha": 41, "Indianapolis": 35 },
                lung: { "Durham": 110, "Pittsburgh": 95, "St. Louis": 80, "Seattle": 55, "Philadelphia": 65, "Cleveland": 129, "Los Angeles": 88, "San Francisco": 95, "Nashville": 99, "Chicago": 97, "Houston": 90, "Baltimore": 25, "Minneapolis": 45, "Rochester": 40, "Palo Alto": 60, "Madison": 30, "Dallas": 40, "Portland": 35, "Miami": 30, "New York": 82, "Omaha": 17, "Indianapolis": 28 },
                pancreas: { "Minneapolis": 45, "Madison": 27, "Miami": 20, "San Francisco": 25, "Chicago": 18, "Pittsburgh": 22, "Cleveland": 15, "Los Angeles": 20, "Houston": 15, "Baltimore": 12, "Philadelphia": 15, "Durham": 10, "Rochester": 18, "Nashville": 12, "Dallas": 10, "Palo Alto": 12, "Seattle": 10, "St. Louis": 14, "Portland": 8, "New York": 15, "Omaha": 10, "Indianapolis": 30 },
                intestine: { "Pittsburgh": 25, "Omaha": 12, "Miami": 12, "Indianapolis": 10, "Los Angeles": 8, "Cleveland": 18, "New York": 7, "Chicago": 5 }
            },
            centerReputation: {
                "Pittsburgh": 100, "Cleveland": 98, "Baltimore": 97, "Rochester": 97,
                "Los Angeles": 95, "San Francisco": 94, "Minneapolis": 93, "Durham": 92,
                "Chicago": 90, "Houston": 89, "Palo Alto": 91, "Philadelphia": 88,
                "Nashville": 86, "Madison": 87, "Seattle": 88, "St. Louis": 85,
                "Dallas": 83, "Miami": 82, "Portland": 84, "Indianapolis": 81,
                "Omaha": 83, "New York": 92
            },
            specializations: {
                kidney: ["Cleveland", "Nashville", "St. Louis", "Madison", "San Francisco", "Chicago"],
                liver: ["Houston", "Cleveland", "San Francisco", "Pittsburgh", "Indianapolis", "Nashville"],
                heart: ["Nashville", "Durham", "Los Angeles", "Palo Alto", "San Francisco", "New York"],
                lung: ["Cleveland", "Durham", "Nashville", "Chicago", "San Francisco", "Pittsburgh"],
                pancreas: ["Minneapolis", "Indianapolis", "Madison", "San Francisco"],
                intestine: ["Pittsburgh", "Omaha", "Miami", "Cleveland"]
            },
            insuranceAcceptanceRates: {
                "Rochester": 99, "Cleveland": 98, "Baltimore": 97, "Pittsburgh": 97,
                "Minneapolis": 96, "Madison": 96, "Durham": 95, "Los Angeles": 94,
                "San Francisco": 94, "Chicago": 93, "Palo Alto": 94, "Houston": 92,
                "Nashville": 91, "Philadelphia": 93, "St. Louis": 92, "Seattle": 94,
                "Portland": 93, "Dallas": 90, "Miami": 89, "New York": 92,
                "Omaha": 95, "Indianapolis": 91
            }
        },
        policyTiers: {
            "California": 92, "Oregon": 100, "Washington": 90,
            "Minnesota": 90, "New York": 90, "Illinois": 90,
            "Pennsylvania": 88, "Ohio": 88, "Wisconsin": 88,
            "Massachusetts": 87, "Colorado": 86, "Maryland": 86,
            "North Carolina": 85, "Nebraska": 84, "Iowa": 83,
            "Michigan": 82, "New Jersey": 81, "Virginia": 80,
            "Tennessee": 75, "Texas": 75, "Florida": 74,
            "Indiana": 74, "Georgia": 73, "Missouri": 73,
            "Arizona": 72
        },
        socioeconomic: {
            "San Francisco": 95, "Palo Alto": 94, "Seattle": 92,
            "Minneapolis": 91, "Madison": 90, "Rochester": 89,
            "New York": 90, "Chicago": 87,
            "Los Angeles": 86, "Portland": 88,
            "Baltimore": 82, "Pittsburgh": 83, "Cleveland": 81,
            "Philadelphia": 84, "Nashville": 85, "Durham": 84,
            "Dallas": 83, "Houston": 82, "St. Louis": 80,
            "Miami": 79, "Indianapolis": 78, "Omaha": 82
        }
    };

    /**
     * Fetch a single JSON file, returning its parsed content or null on failure.
     */
    async function fetchJSON(url) {
        try {
            const response = await fetch(url);
            if (!response.ok) return null;
            return await response.json();
        } catch {
            return null;
        }
    }

    /**
     * Strip _meta from a loaded data object so it matches the shape of defaults.
     */
    function stripMeta(data) {
        if (!data || typeof data !== 'object') return data;
        const { _meta, ...rest } = data;
        return rest;
    }

    /**
     * Compute freshness status from a fetchedAt timestamp.
     * Returns 'fresh' (<30 days), 'stale' (30-90 days), or 'expired' (>90 days).
     */
    function getFreshness(fetchedAt) {
        if (!fetchedAt) return 'expired';
        const age = (Date.now() - new Date(fetchedAt).getTime()) / (1000 * 60 * 60 * 24);
        if (age < 30) return 'fresh';
        if (age < 90) return 'stale';
        return 'expired';
    }

    /**
     * Render the data freshness banner in the results section.
     */
    function renderFreshnessBanner(metadata, sourceStatuses) {
        const banner = document.getElementById('data-freshness-banner');
        if (!banner) return;

        const lastUpdate = metadata?.lastFullFetch
            ? new Date(metadata.lastFullFetch).toLocaleDateString('en-US', {
                year: 'numeric', month: 'long', day: 'numeric'
            })
            : 'Unknown';

        const overallFreshness = getFreshness(metadata?.lastFullFetch);
        const freshnessColors = { fresh: '#27ae60', stale: '#f39c12', expired: '#e74c3c' };
        const freshnessLabels = { fresh: 'Up to date', stale: 'Some data may be outdated', expired: 'Data may be outdated' };

        let sourceDots = '';
        if (metadata?.sources) {
            for (const [key, info] of Object.entries(metadata.sources)) {
                const status = getFreshness(info.fetchedAt);
                const color = freshnessColors[status];
                const label = key.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                sourceDots += `<span class="freshness-dot" style="color:${color}" title="${label}: ${info.source}">&#9679; ${label}</span> `;
            }
        }

        banner.innerHTML = `
            <div class="freshness-banner" style="border-left: 4px solid ${freshnessColors[overallFreshness]}">
                <div class="freshness-header">
                    <strong>Data last updated:</strong> ${lastUpdate}
                    <span class="freshness-status" style="color:${freshnessColors[overallFreshness]}">${freshnessLabels[overallFreshness]}</span>
                </div>
                <div class="freshness-sources">${sourceDots}</div>
            </div>
        `;
    }

    /**
     * Load all data files and expose on window.TransPlanData.
     * Returns a promise that resolves when all data is loaded (or fell back to defaults).
     */
    async function loadAllData() {
        const entries = Object.entries(DATA_FILES);
        const results = await Promise.allSettled(
            entries.map(([key, url]) => fetchJSON(url).then(data => [key, data]))
        );

        const loaded = {};
        const sourceStatuses = {};

        results.forEach((result, index) => {
            const [key] = entries[index];
            if (result.status === 'fulfilled' && result.value) {
                const [, data] = result.value;
                if (data) {
                    loaded[key] = stripMeta(data);
                    sourceStatuses[key] = 'loaded';
                } else {
                    loaded[key] = DEFAULTS[key] || null;
                    sourceStatuses[key] = 'fallback';
                }
            } else {
                // Promise rejected — fall back to default for this specific source
                loaded[key] = DEFAULTS[key] || null;
                sourceStatuses[key] = 'error';
            }
        });

        // Fill in any missing keys with defaults
        for (const key of Object.keys(DEFAULTS)) {
            if (!loaded[key]) {
                loaded[key] = DEFAULTS[key];
                sourceStatuses[key] = 'fallback';
            }
        }

        window.TransPlanData = loaded;
        window.TransPlanData._sourceStatuses = sourceStatuses;
        window.TransPlanData._loaded = true;

        // Render freshness banner
        renderFreshnessBanner(loaded.metadata, sourceStatuses);

        return loaded;
    }

    // Expose loadAllData globally
    window.loadAllData = loadAllData;

})();
