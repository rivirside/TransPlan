#!/usr/bin/env node
/**
 * Fetch cause-of-death data for the organ donor availability model.
 *
 * Sources:
 *   1. data.cdc.gov "bi63-dtpu" — NCHS Leading Causes of Death (injury, heart, stroke)
 *   2. data.cdc.gov "xkb8-kh2a" — VSRR Provisional Drug Overdose Death Counts
 *
 * CDC WONDER has NO programmatic REST API, so we use the SODA API on data.cdc.gov.
 *
 * Output: data/cause-of-death-by-region.json
 *   - Preserves existing organRecoveryRates (from PMC10329409, not fetchable)
 *   - Updates stateCauseOfDeathProportions for all 50 states + DC
 *   - Uses donor-eligibility calibration weights to convert general population
 *     mortality into organ-donor-relevant proportions
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

// Mapping from CDC cause_name values to our categories
const CAUSE_MAP = {
    'Unintentional injuries': 'trauma',
    'Heart disease': 'cardiovascular',
    'Stroke': 'stroke'
    // Drug overdose comes from the separate VSRR dataset
};

// Target the most recent year available in bi63-dtpu (2017 is the latest)
const TARGET_YEAR = '2017';

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
    // for the period ending December 2017 to align with leading causes data.
    // The indicator we want is "Number of Drug Overdose Deaths"
    const url = `${DRUG_OVERDOSE_URL}?$where=year='2017' AND month='December' AND indicator='Number of Drug Overdose Deaths'&$limit=60&$select=state_name,data_value`;

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

        // Fallback: try 2018 data
        console.log('  Trying 2018 fallback...');
        try {
            const fallbackUrl = `${DRUG_OVERDOSE_URL}?$where=year='2018' AND month='December' AND indicator='Number of Drug Overdose Deaths'&$limit=60&$select=state_name,data_value`;
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
            console.log(`  Drug overdose (2018 fallback): ${Object.keys(results).length} states`);
        } catch (err2) {
            console.warn(`  Fallback also failed: ${err2.message}`);
        }
    }

    return results;
}

/**
 * Convert raw death counts to donor-eligible proportions using calibration weights.
 * Each state gets proportions that sum to 1.0.
 */
function computeProportions(leadingCauses, drugOverdoses) {
    const proportions = {};

    for (const [state, counts] of Object.entries(leadingCauses)) {
        const overdoseCount = drugOverdoses[state] || 0;

        // Apply donor-eligibility weights
        const weighted = {
            trauma: (counts.trauma || 0) * DONOR_WEIGHTS.trauma,
            cardiovascular: (counts.cardiovascular || 0) * DONOR_WEIGHTS.cardiovascular,
            drug_intox: overdoseCount * DONOR_WEIGHTS.drug_intox,
            stroke: (counts.stroke || 0) * DONOR_WEIGHTS.stroke
        };

        const total = weighted.trauma + weighted.cardiovascular + weighted.drug_intox + weighted.stroke;

        if (total > 0) {
            proportions[state] = {
                trauma: Math.round((weighted.trauma / total) * 100) / 100,
                cardiovascular: Math.round((weighted.cardiovascular / total) * 100) / 100,
                drug_intox: Math.round((weighted.drug_intox / total) * 100) / 100,
                stroke: Math.round((weighted.stroke / total) * 100) / 100
            };

            // Ensure they sum to exactly 1.0 (adjust largest category for rounding)
            const sum = proportions[state].trauma + proportions[state].cardiovascular +
                        proportions[state].drug_intox + proportions[state].stroke;
            if (sum !== 1.0) {
                const diff = 1.0 - sum;
                // Find the largest category and adjust it
                const cats = Object.entries(proportions[state]);
                cats.sort((a, b) => b[1] - a[1]);
                proportions[state][cats[0][0]] = Math.round((cats[0][1] + diff) * 100) / 100;
            }
        }
    }

    return proportions;
}

async function main() {
    console.log('=== Fetching Cause-of-Death Data for Organ Donor Model ===\n');

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
            notes: 'Intestine uses pancreas rates as proxy (PMC10329409 has no intestine data). ' +
                   'Proportions represent share of potential brain-dead donors by cause among donor-eligible deaths. ' +
                   `Calibration weights (trauma=${DONOR_WEIGHTS.trauma}, cardiovascular=${DONOR_WEIGHTS.cardiovascular}, ` +
                   `drug_intox=${DONOR_WEIGHTS.drug_intox}, stroke=${DONOR_WEIGHTS.stroke}) fitted via Nelder-Mead optimization.`,
            calibration: 'Weights represent fraction of general-population deaths in each category that result in donor-eligible brain death.'
        },
        organRecoveryRates: existing.organRecoveryRates || {
            heart:     { trauma: 0.488, cardiovascular: 0.151, drug_intox: 0.369, stroke: 0.157 },
            lung:      { trauma: 0.280, cardiovascular: 0.094, drug_intox: 0.204, stroke: 0.190 },
            liver:     { trauma: 0.797, cardiovascular: 0.654, drug_intox: 0.780, stroke: 0.737 },
            kidney:    { trauma: 0.896, cardiovascular: 0.686, drug_intox: 0.824, stroke: 0.668 },
            pancreas:  { trauma: 0.246, cardiovascular: 0.048, drug_intox: 0.095, stroke: 0.053 },
            intestine: { trauma: 0.246, cardiovascular: 0.048, drug_intox: 0.095, stroke: 0.053 }
        },
        stateCauseOfDeathProportions: sortedProportions,
        causeCategories: existing.causeCategories || {
            trauma: 'ICD-10 V01-Y34: Transport accidents, falls, assaults',
            cardiovascular: 'ICD-10 I21-I25: Acute MI, ischemic heart disease',
            drug_intox: 'ICD-10 T36-T50: Drug/substance poisoning (opioids, sedatives, stimulants)',
            stroke: 'ICD-10 I60-I69: Subarachnoid/intracerebral hemorrhage, cerebrovascular'
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
