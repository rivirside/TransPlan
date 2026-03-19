#!/usr/bin/env node
/**
 * Fetch cause-of-death data for the organ donor availability model.
 *
 * Sources:
 *   1. data.cdc.gov "bi63-dtpu" — NCHS Leading Causes of Death (injury, heart, stroke)
 *   2. data.cdc.gov "xkb8-kh2a" — VSRR Provisional Drug Overdose Death Counts
 *   3. Anoxia-NOS: estimated from PMC10329409 (9.2% of donors nationally) +
 *      CDC drowning rate patterns by state. CDC WONDER has the ICD-10 level
 *      data (W65-W74, T71, T58, W75-W84) but has NO REST API; these estimates
 *      use published drowning death rate geographic patterns as a proxy.
 *
 * CDC WONDER has NO programmatic REST API, so we use the SODA API on data.cdc.gov.
 *
 * Output: data/cause-of-death-by-region.json
 *   - Preserves existing organRecoveryRates (from PMC10329409 + estimates)
 *   - Updates stateCauseOfDeathProportions for all 50 states + DC (5 categories)
 *   - Uses donor-eligibility calibration weights to convert general population
 *     mortality into organ-donor-relevant proportions
 *   - Anoxia-NOS allocated by state from estimated shares, other 4 categories
 *     scaled proportionally
 *
 * Auth: None required (public SODA endpoints)
 * Rate limit: Unauthenticated SODA = 1000 req/hr; we make ~3 requests total
 */

const { fetchWithRetry, updateMetadata, reportError, delay, DATA_DIR } = require('./utils');
const fs = require('fs');
const path = require('path');

// SODA API endpoints on data.cdc.gov
const LEADING_CAUSES_URL = 'https://data.cdc.gov/resource/bi63-dtpu.json';
const DRUG_OVERDOSE_URL = 'https://data.cdc.gov/resource/xkb8-kh2a.json';

// Donor-eligibility calibration weights:
// Fraction of general-population deaths in each CDC category that result in
// donor-eligible brain death. Fitted via Nelder-Mead optimization against
// 17 reference states with known donor COD distributions.
const DONOR_WEIGHTS = {
    trauma: 0.310,
    cardiovascular: 0.062,
    drug_intox: 0.721,
    stroke: 0.175
};

// Estimated anoxia-NOS donor shares by state.
// Anoxia-NOS = 9.2% of donors nationally (PMC10329409), primarily drowning (~45%),
// asphyxiation (~35%), and CO poisoning (~15%). State variation driven by drowning
// rates: coastal/warm states higher, cold inland states lower.
// CDC WONDER has ICD-10 level data but no REST API; these use published patterns.
// FIXME: Replace with CDC WONDER query if API becomes available (#14).
const STATE_ANOXIA_SHARES = {
    "Alabama": 0.10, "Alaska": 0.14, "Arizona": 0.10, "Arkansas": 0.10,
    "California": 0.09, "Colorado": 0.09, "Connecticut": 0.08,
    "Delaware": 0.09, "District of Columbia": 0.05, "Florida": 0.12,
    "Georgia": 0.10, "Hawaii": 0.13, "Idaho": 0.10, "Illinois": 0.08,
    "Indiana": 0.08, "Iowa": 0.07, "Kansas": 0.08, "Kentucky": 0.08,
    "Louisiana": 0.12, "Maine": 0.09, "Maryland": 0.09,
    "Massachusetts": 0.08, "Michigan": 0.09, "Minnesota": 0.09,
    "Mississippi": 0.11, "Missouri": 0.09, "Montana": 0.10,
    "Nebraska": 0.08, "Nevada": 0.10, "New Hampshire": 0.08,
    "New Jersey": 0.08, "New Mexico": 0.10, "New York": 0.07,
    "North Carolina": 0.10, "North Dakota": 0.08, "Ohio": 0.08,
    "Oklahoma": 0.10, "Oregon": 0.10, "Pennsylvania": 0.08,
    "Rhode Island": 0.06, "South Carolina": 0.10, "South Dakota": 0.08,
    "Tennessee": 0.10, "Texas": 0.10, "Utah": 0.08, "Vermont": 0.08,
    "Virginia": 0.10, "Washington": 0.10, "West Virginia": 0.07,
    "Wisconsin": 0.09, "Wyoming": 0.10,
};
const DEFAULT_ANOXIA_SHARE = 0.09; // National average fallback

// Mapping from CDC cause_name values to our categories
const CAUSE_MAP = {
    'Unintentional injuries': 'trauma',
    'Heart disease': 'cardiovascular',
    'Stroke': 'stroke'
    // Drug overdose comes from the separate VSRR dataset
};

// Discover the most recent year with data instead of hardcoding.
// bi63-dtpu goes up to ~2017; try recent years first, fall back to older.
let TARGET_YEAR = null;

async function discoverTargetYear() {
    const currentYear = new Date().getFullYear();
    // CDC data typically lags 2-3 years; try from (current-2) down to 2017
    for (let y = currentYear - 2; y >= 2017; y--) {
        const testUrl = `${LEADING_CAUSES_URL}?$where=year='${y}' AND cause_name='Heart disease'&$limit=1&$select=year`;
        try {
            const resp = await fetchWithRetry(testUrl);
            const data = await resp.json();
            if (data.length > 0) {
                console.log(`  Most recent year with data: ${y}`);
                return String(y);
            }
        } catch {
            // continue to next year
        }
    }
    console.warn('  Could not discover year, defaulting to 2017');
    return '2017';
}

/**
 * Fetch leading causes of death (injury, heart, stroke) for all states.
 * Returns { stateName: { trauma: N, cardiovascular: N, stroke: N } }
 */
async function fetchLeadingCauses() {
    console.log('Fetching leading causes of death from NCHS dataset (bi63-dtpu)...');

    const results = {};
    const causesToFetch = Object.keys(CAUSE_MAP);

    for (const causeName of causesToFetch) {
        const category = CAUSE_MAP[causeName];
        const url = `${LEADING_CAUSES_URL}?$where=year='${TARGET_YEAR}' AND cause_name='${encodeURIComponent(causeName)}'&$limit=60&$select=state,deaths`;

        try {
            const response = await fetchWithRetry(url);
            const data = await response.json();

            for (const row of data) {
                const state = row.state;
                if (!state || state === 'United States') continue;

                if (!results[state]) results[state] = {};
                // deaths may have commas in the string
                const deaths = parseInt(String(row.deaths).replace(/,/g, ''), 10);
                if (!isNaN(deaths)) {
                    results[state][category] = deaths;
                }
            }

            console.log(`  ${causeName}: ${data.length} state rows`);
        } catch (err) {
            console.warn(`  Failed to fetch ${causeName}: ${err.message}`);
        }

        await delay(500); // Respect rate limits
    }

    return results;
}

/**
 * Fetch drug overdose death counts for all states.
 * Returns { stateName: count }
 */
async function fetchDrugOverdoses() {
    console.log('Fetching drug overdose data from VSRR dataset (xkb8-kh2a)...');

    // VSRR has rolling 12-month totals. Get "Number of Drug Overdose Deaths"
    // for the period ending December of TARGET_YEAR to align with leading causes.
    const url = `${DRUG_OVERDOSE_URL}?$where=year='${TARGET_YEAR}' AND month='December' AND indicator='Number of Drug Overdose Deaths'&$limit=60&$select=state_name,data_value`;

    const results = {};

    try {
        const response = await fetchWithRetry(url);
        const data = await response.json();

        for (const row of data) {
            const state = row.state_name;
            if (!state || state === 'United States') continue;

            const deaths = parseInt(String(row.data_value).replace(/,/g, ''), 10);
            if (!isNaN(deaths)) {
                results[state] = deaths;
            }
        }

        console.log(`  Drug overdose: ${Object.keys(results).length} states`);
    } catch (err) {
        console.warn(`  Failed to fetch drug overdose data: ${err.message}`);

        // Fallback: try next year's data (VSRR may have different coverage)
        const fallbackYear = String(Number(TARGET_YEAR) + 1);
        console.log(`  Trying ${fallbackYear} fallback...`);
        try {
            const fallbackUrl = `${DRUG_OVERDOSE_URL}?$where=year='${fallbackYear}' AND month='December' AND indicator='Number of Drug Overdose Deaths'&$limit=60&$select=state_name,data_value`;
            const response = await fetchWithRetry(fallbackUrl);
            const data = await response.json();

            for (const row of data) {
                const state = row.state_name;
                if (!state || state === 'United States') continue;
                const deaths = parseInt(String(row.data_value).replace(/,/g, ''), 10);
                if (!isNaN(deaths)) {
                    results[state] = deaths;
                }
            }
            console.log(`  Drug overdose (${fallbackYear} fallback): ${Object.keys(results).length} states`);
        } catch (err2) {
            console.warn(`  Fallback also failed: ${err2.message}`);
        }
    }

    return results;
}

/**
 * Convert raw death counts to donor-eligible proportions using calibration weights.
 * Each state gets 5-category proportions that sum to 1.0.
 * Anoxia-NOS is allocated from estimated state shares, then the 4 CDC-fetched
 * categories are scaled down proportionally.
 */
function computeProportions(leadingCauses, drugOverdoses) {
    const proportions = {};

    for (const [state, counts] of Object.entries(leadingCauses)) {
        const overdoseCount = drugOverdoses[state] || 0;

        // Apply donor-eligibility weights to the 4 fetched categories
        const weighted = {
            trauma: (counts.trauma || 0) * DONOR_WEIGHTS.trauma,
            cardiovascular: (counts.cardiovascular || 0) * DONOR_WEIGHTS.cardiovascular,
            drug_intox: overdoseCount * DONOR_WEIGHTS.drug_intox,
            stroke: (counts.stroke || 0) * DONOR_WEIGHTS.stroke
        };

        const total = weighted.trauma + weighted.cardiovascular + weighted.drug_intox + weighted.stroke;

        if (total > 0) {
            // First compute 4-category proportions (sum to 1.0)
            const fourCat = {
                trauma: weighted.trauma / total,
                cardiovascular: weighted.cardiovascular / total,
                drug_intox: weighted.drug_intox / total,
                stroke: weighted.stroke / total
            };

            // Allocate anoxia share, scale other 4 down proportionally
            const anoxiaShare = STATE_ANOXIA_SHARES[state] || DEFAULT_ANOXIA_SHARE;
            const remaining = 1.0 - anoxiaShare;

            proportions[state] = {
                trauma: Math.round(fourCat.trauma * remaining * 100) / 100,
                cardiovascular: Math.round(fourCat.cardiovascular * remaining * 100) / 100,
                drug_intox: Math.round(fourCat.drug_intox * remaining * 100) / 100,
                stroke: Math.round(fourCat.stroke * remaining * 100) / 100,
                anoxia: anoxiaShare
            };

            // Ensure they sum to exactly 1.0 (adjust largest non-anoxia category)
            const sum = Object.values(proportions[state]).reduce((a, b) => a + b, 0);
            if (Math.abs(sum - 1.0) > 0.001) {
                const diff = Math.round((1.0 - sum) * 100) / 100;
                const cats = Object.entries(proportions[state])
                    .filter(([k]) => k !== 'anoxia')
                    .sort((a, b) => b[1] - a[1]);
                proportions[state][cats[0][0]] = Math.round((cats[0][1] + diff) * 100) / 100;
            }
        }
    }

    return proportions;
}

async function main() {
    console.log('=== Fetching Cause-of-Death Data for Organ Donor Model ===\n');

    // Discover latest available year
    TARGET_YEAR = await discoverTargetYear();
    console.log(`Using TARGET_YEAR = ${TARGET_YEAR}\n`);

    // Fetch both data sources
    const [leadingCauses, drugOverdoses] = await Promise.all([
        fetchLeadingCauses(),
        fetchDrugOverdoses()
    ]);

    const stateCount = Object.keys(leadingCauses).length;
    const overdoseCount = Object.keys(drugOverdoses).length;
    console.log(`\nRaw data: ${stateCount} states with leading causes, ${overdoseCount} with overdose data`);

    if (stateCount === 0) {
        console.error('No leading causes data retrieved. Aborting — seed data preserved.');
        updateMetadata('cause-of-death', 'CDC SODA API', 'error');
        process.exit(1);
    }

    // Compute donor-eligible proportions
    const proportions = computeProportions(leadingCauses, drugOverdoses);
    console.log(`Computed proportions for ${Object.keys(proportions).length} states`);

    // Read existing file to preserve organRecoveryRates and causeCategories
    const filePath = path.join(DATA_DIR, 'cause-of-death-by-region.json');
    let existing = {};
    try {
        existing = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
    } catch (e) {
        console.warn('No existing cause-of-death-by-region.json found; creating new.');
    }

    // Sort states alphabetically for consistent output
    const sortedProportions = {};
    for (const state of Object.keys(proportions).sort()) {
        sortedProportions[state] = proportions[state];
    }

    // Build output, preserving organRecoveryRates (not fetchable — from literature)
    const output = {
        _meta: {
            fetchedAt: new Date().toISOString(),
            source: `Organ recovery rates: PMC10329409 Table 2 (2023). State proportions: CDC ${TARGET_YEAR} mortality data (data.cdc.gov bi63-dtpu + xkb8-kh2a) with donor-eligibility calibration.`,
            notes: 'Intestine rates from OPTN 2023 OTPD ratio (intestine/pancreas=0.104) with COD-specific clinical adjustments (see GitHub #16). ' +
                   'Anoxia-NOS recovery rates estimated from PMC10329409 OR 0.848 vs trauma (see GitHub #14); state shares from CDC drowning rate patterns. ' +
                   'Proportions represent share of potential brain-dead donors by cause among donor-eligible deaths. ' +
                   `Calibration weights (trauma=${DONOR_WEIGHTS.trauma}, cardiovascular=${DONOR_WEIGHTS.cardiovascular}, ` +
                   `drug_intox=${DONOR_WEIGHTS.drug_intox}, stroke=${DONOR_WEIGHTS.stroke}) fitted via Nelder-Mead optimization.`,
            calibration: 'Weights represent fraction of general-population deaths in each category that result in donor-eligible brain death.'
        },
        organRecoveryRates: existing.organRecoveryRates || {
            heart:     { trauma: 0.488, cardiovascular: 0.151, drug_intox: 0.369, stroke: 0.157, anoxia: 0.39 },
            lung:      { trauma: 0.280, cardiovascular: 0.094, drug_intox: 0.204, stroke: 0.190, anoxia: 0.22 },
            liver:     { trauma: 0.797, cardiovascular: 0.654, drug_intox: 0.780, stroke: 0.737, anoxia: 0.74 },
            kidney:    { trauma: 0.896, cardiovascular: 0.686, drug_intox: 0.824, stroke: 0.668, anoxia: 0.82 },
            pancreas:  { trauma: 0.246, cardiovascular: 0.048, drug_intox: 0.095, stroke: 0.053, anoxia: 0.15 },
            intestine: { trauma: 0.030, cardiovascular: 0.003, drug_intox: 0.010, stroke: 0.004, anoxia: 0.02 }
        },
        stateCauseOfDeathProportions: sortedProportions,
        causeCategories: existing.causeCategories || {
            trauma: 'ICD-10 V01-Y34: Transport accidents, falls, assaults',
            cardiovascular: 'ICD-10 I21-I25: Acute MI, ischemic heart disease',
            drug_intox: 'ICD-10 T36-T50: Drug/substance poisoning (opioids, sedatives, stimulants)',
            stroke: 'ICD-10 I60-I69: Subarachnoid/intracerebral hemorrhage, cerebrovascular',
            anoxia: 'ICD-10 W65-W74, T71, T58, W75-W84: Drowning, asphyxiation, carbon monoxide, other oxygen deprivation (non-drug, non-cardiac)'
        }
    };

    fs.writeFileSync(filePath, JSON.stringify(output, null, 2) + '\n');
    console.log(`\nWrote ${filePath} (${Object.keys(sortedProportions).length} states)`);

    updateMetadata('cause-of-death', 'CDC SODA API (bi63-dtpu + xkb8-kh2a)');
    console.log('Done.');
}

main().catch(err => {
    reportError('CDC COD Data', err);
    process.exit(1);
});
