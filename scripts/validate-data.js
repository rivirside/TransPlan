#!/usr/bin/env node
/**
 * Post-fetch data validation.
 * Checks: JSON syntax, expected schema, value ranges, per-center coverage floors, staleness.
 */

const fs = require('fs');
const path = require('path');
const { DATA_DIR } = require('./utils');  // (#293: CI no longer defends 22-city coverage)

const STALE_THRESHOLD_DAYS = 90;

let errors = [];
let warnings = [];

function addError(msg) {
    errors.push(msg);
    console.error(`[ERROR] ${msg}`);
}

function addWarning(msg) {
    warnings.push(msg);
    console.warn(`[WARN] ${msg}`);
}

function validateJSON(filename) {
    const filePath = path.join(DATA_DIR, filename);
    if (!fs.existsSync(filePath)) {
        addError(`Missing file: ${filename}`);
        return null;
    }

    try {
        const content = fs.readFileSync(filePath, 'utf-8');
        return JSON.parse(content);
    } catch (err) {
        addError(`Invalid JSON in ${filename}: ${err.message}`);
        return null;
    }
}

function checkValueRange(data, filename, min, max, skipKeys = ['_meta']) {
    for (const [key, value] of Object.entries(data)) {
        if (skipKeys.includes(key)) continue;
        if (typeof value === 'number') {
            if (value < min || value > max) {
                addWarning(`${filename}: ${key} = ${value} (expected ${min}-${max})`);
            }
        }
    }
}

function checkStaleness(data, filename) {
    const fetchedAt = data?._meta?.fetchedAt;
    if (!fetchedAt) {
        addWarning(`${filename} has no _meta.fetchedAt timestamp`);
        return;
    }

    const age = (Date.now() - new Date(fetchedAt).getTime()) / (1000 * 60 * 60 * 24);
    if (age > STALE_THRESHOLD_DAYS) {
        addWarning(`${filename} is ${Math.round(age)} days old (threshold: ${STALE_THRESHOLD_DAYS} days)`);
    }
}

function checkCoverageFloor(obj, filename, floor) {
    // Never-shrink guard (2026-08-05 incident class): a fetch that merges a
    // near-empty API result must FAIL validation, not pass vacuously.
    const n = Object.keys(obj || {}).filter(k => k !== '_meta').length;
    if (n < floor) {
        addError(`${filename}: only ${n} entries (never-shrink floor: ${floor})`);
    }
}

// === Run Validations ===

console.log('Validating TransPlan data files...\n');

// 1. Air Quality
const airQuality = validateJSON('air-quality.json');
if (airQuality) {
    checkStaleness(airQuality, 'air-quality.json');
    const { _meta, ...aqData } = airQuality;
    checkCoverageFloor(aqData, 'air-quality.json', 20);
    checkValueRange(aqData, 'air-quality.json', 0, 100);
}

// 2. Traffic Fatalities
const traffic = validateJSON('traffic-fatalities.json');
if (traffic) {
    checkStaleness(traffic, 'traffic-fatalities.json');
    checkCoverageFloor(traffic.traumaScores, 'traffic-fatalities.json (traumaScores)', 20);
    if (traffic.traumaScores) {
        checkValueRange(traffic.traumaScores, 'traffic-fatalities.json (traumaScores)', 0, 100);
    }
}

// 3. Health Demographics
const health = validateJSON('health-demographics.json');
if (health) {
    checkStaleness(health, 'health-demographics.json');
    const { _meta, ...hdData } = health;
    checkCoverageFloor(hdData, 'health-demographics.json', 20);
    for (const [city, metrics] of Object.entries(hdData)) {
        if (typeof metrics === 'object' && metrics !== null) {
            if (metrics.diabetesRate != null && (metrics.diabetesRate < 0 || metrics.diabetesRate > 30)) {
                addWarning(`health-demographics.json: ${city} diabetesRate = ${metrics.diabetesRate} (expected 0-30)`);
            }
            if (metrics.obesityRate != null && (metrics.obesityRate < 0 || metrics.obesityRate > 60)) {
                addWarning(`health-demographics.json: ${city} obesityRate = ${metrics.obesityRate} (expected 0-60)`);
            }
        }
    }
}

// 5. Cost of Living (BEA RPP shape: {msas, states, nonmetroUS, cities} — #205)
const costOfLiving = validateJSON('cost-of-living.json');
if (costOfLiving) {
    checkStaleness(costOfLiving, 'cost-of-living.json');
    const nMsas = Object.keys(costOfLiving.msas || {}).length;
    const nStates = Object.keys(costOfLiving.states || {}).length;
    if (nMsas < 300) {
        addWarning(`cost-of-living.json: only ${nMsas} MSAs (expected ≥300)`);
    }
    if (nStates < 51) {
        addWarning(`cost-of-living.json: only ${nStates} states (expected 50+DC)`);
    }
    const rppValues = {};
    for (const [cbsa, m] of Object.entries(costOfLiving.msas || {})) rppValues[cbsa] = m.rpp;
    Object.assign(rppValues, costOfLiving.states || {});
    checkValueRange(rppValues, 'cost-of-living.json (RPPs)', 60, 160);
}

// 6. Donor Registration
const donor = validateJSON('donor-registration.json');
if (donor) {
    checkStaleness(donor, 'donor-registration.json');
    checkCoverageFloor(donor.livingDonorProgramStrength, 'donor-registration.json (livingDonorProgramStrength)', 20);
    if (donor.livingDonorProgramStrength) {
        checkValueRange(donor.livingDonorProgramStrength, 'donor-registration.json (livingDonorProgramStrength)', 0, 100);
    }
}

// 6a2. Manual age-multiplier blocks in competing-risks.json (ERROR: the #104
// rewrite silently dropped these, killing the BBN age edge + MCMC inference
// age modulation — never again)
const competingRisks = validateJSON('competing-risks.json');
if (competingRisks) {
    for (const key of ['age_mortality_multipliers', 'age_organ_overrides']) {
        if (!competingRisks[key] || Object.keys(competingRisks[key]).length < 2) {
            addError(`competing-risks.json: manual block '${key}' missing or gutted`);
        }
    }
}

// 6a3. Shared state-population table (#339) — both per-capita pipelines
// read it; losing states silently skews trauma/traffic normalization
const statePops = validateJSON('manual/state-populations.json');
if (statePops) {
    const n = Object.keys(statePops.populations || {}).length;
    if (n < 51) addError(`state-populations.json: only ${n} states (expected >= 51)`);
    for (const [st, pop] of Object.entries(statePops.populations || {})) {
        if (typeof pop !== 'number' || pop < 400000 || pop > 45000000) {
            addError(`state-populations.json: ${st} = ${pop} implausible`);
        }
    }
}

// 6a4. Offer-acceptance ratios + SRTR tiers (#320) — never-shrink floors
const oarr = validateJSON('offer-acceptance-centers.json');
if (oarr) {
    const nk = Object.keys(oarr.kidney?.centers || {}).length;
    if (nk < 180) addError(`offer-acceptance-centers.json: only ${nk} kidney centers (expected >= 180)`);
}
const tiers = validateJSON('srtr-tiers-centers.json');
if (tiers) {
    const nk = Object.keys(tiers.kidney || {}).length;
    if (nk < 190) addError(`srtr-tiers-centers.json: only ${nk} kidney centers (expected >= 190)`);
}

// 6a5. Pediatric per-center data (#335) — never-shrink floors + the unit
// trap guard (rates are per person-year, not percentages)
const peds = validateJSON('pediatric-centers.json');
if (peds) {
    const nk = Object.keys(peds.kidney?.centers || {}).length;
    if (nk < 95) addError(`pediatric-centers.json: only ${nk} kidney programs (expected >= 95)`);
    for (const organ of ['kidney', 'liver', 'heart', 'lung']) {
        const block = peds[organ];
        if (!block) continue;
        for (const [code, rec] of Object.entries(block.centers || {})) {
            if (rec.transplant_rate >= 10) {
                addError(`pediatric-centers.json: ${organ}/${code} rate ${rec.transplant_rate} — rates are per PERSON-YEAR, a value >=10 means a units error or missing exposure floor`);
            }
        }
        const cal = block.calibration;
        if (cal && !(cal.k > 0.2 && cal.k < 5 && cal.median_abs_error < 0.15)) {
            addError(`pediatric-centers.json: ${organ} calibration implausible: ${JSON.stringify(cal)}`);
        }
    }
}

// 6b. SRTR-derived model files — every organ block must be present (ERROR,
// not warning: the 2026-08-05 workflow run wrote organ-less shells over
// these because data/srtr-raw/ is absent in CI; see parse-srtr-reports.py
// _write_guarded). Losing an organ block silently degrades the simulator.
const ORGANS = ['kidney', 'liver', 'heart', 'lung', 'pancreas', 'intestine'];
for (const srtrFile of ['wait-time-distributions.json', 'competing-risks.json', 'post-transplant-outcomes.json']) {
    const data = validateJSON(srtrFile);
    if (data) {
        const missing = ORGANS.filter(o => !data[o] || typeof data[o] !== 'object');
        if (missing.length) {
            addError(`${srtrFile}: missing organ blocks: ${missing.join(', ')}`);
        }
    }
}

// 6d. Per-center climate/trauma layers (#289/#290) — never-shrink guards
for (const [file, key, minN] of [['climate-scores-centers.json', 'centers', 240],
                                 ['trauma-scores-centers.json', 'centers', 240]]) {
    const data = validateJSON(file);
    if (data) {
        const n = Object.keys(data[key] || {}).length;
        if (n < minN) {
            addError(`${file}: only ${n} centers (expected >= ${minN})`);
        }
    }
}

// 6e. Per-center living-donor scores (#292)
const livingDonors = validateJSON('living-donor-centers.json');
if (livingDonors) {
    const nk = Object.keys(livingDonors.scores?.kidney || {}).length;
    if (nk < 180) addError(`living-donor-centers.json: only ${nk} kidney centers (expected >= 180)`);
    const nl = Object.keys(livingDonors.scores?.liver || {}).length;
    if (nl < 45) addError(`living-donor-centers.json: only ${nl} liver centers (expected >= 45)`);
}

// 6c. Per-center trend series (#288) — never-shrink guard: generated from the
// 15-release SRTR archive, must keep covering the center population.
const centerTrends = validateJSON('srtr-trends-centers.json');
if (centerTrends) {
    const n = Object.keys(centerTrends.centers || {}).length;
    if (n < 200) {
        addError(`srtr-trends-centers.json: only ${n} centers (expected >= 200) — regenerate with scripts/generate-center-trends.py`);
    }
}

// 7. Manual files
for (const manualFile of ['manual/climate-scores.json', 'manual/policy-tiers.json']) {
    const data = validateJSON(manualFile);
    if (data) {
        checkStaleness(data, manualFile);
    }
}

// 8. Metadata (optional — gitignored, only present after local fetch)
const metadataPath = path.join(DATA_DIR, 'metadata.json');
if (fs.existsSync(metadataPath)) {
    const metadata = validateJSON('metadata.json');
    if (metadata && !metadata.sources) {
        addWarning('metadata.json has no sources object');
    }
}

// === Report Results ===

console.log('\n=== Validation Summary ===');
console.log(`Errors:   ${errors.length}`);
console.log(`Warnings: ${warnings.length}`);

if (errors.length > 0) {
    console.error('\nErrors:');
    errors.forEach(e => console.error(`  - ${e}`));
}

if (warnings.length > 0) {
    console.warn('\nWarnings:');
    warnings.forEach(w => console.warn(`  - ${w}`));
}

if (errors.length > 0) {
    process.exit(1);
}

console.log('\nValidation passed.');
