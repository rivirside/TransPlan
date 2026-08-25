#!/usr/bin/env node
/**
 * Post-fetch data validation.
 * Checks: JSON syntax, expected schema, value ranges, coverage of all 22 cities, staleness.
 */

const fs = require('fs');
const path = require('path');
const { CITIES, DATA_DIR } = require('./utils');

const CITY_NAMES = CITIES.map(c => c.city);
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

function checkCityCoverage(data, filename, skipKeys = ['_meta']) {
    const keys = Object.keys(data).filter(k => !skipKeys.includes(k));
    const missing = CITY_NAMES.filter(city => !keys.includes(city));
    if (missing.length > 0) {
        addWarning(`${filename} missing cities: ${missing.join(', ')}`);
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

// === Run Validations ===

console.log('Validating TransPlan data files...\n');

// 1. Air Quality
const airQuality = validateJSON('air-quality.json');
if (airQuality) {
    checkStaleness(airQuality, 'air-quality.json');
    const { _meta, ...aqData } = airQuality;
    checkCityCoverage(aqData, 'air-quality.json');
    checkValueRange(aqData, 'air-quality.json', 0, 100);
}

// 2. Traffic Fatalities
const traffic = validateJSON('traffic-fatalities.json');
if (traffic) {
    checkStaleness(traffic, 'traffic-fatalities.json');
    if (traffic.traumaScores) {
        checkCityCoverage(traffic.traumaScores, 'traffic-fatalities.json (traumaScores)');
        checkValueRange(traffic.traumaScores, 'traffic-fatalities.json (traumaScores)', 0, 100);
    }
}

// 3. Health Demographics
const health = validateJSON('health-demographics.json');
if (health) {
    checkStaleness(health, 'health-demographics.json');
    const { _meta, ...hdData } = health;
    checkCityCoverage(hdData, 'health-demographics.json');
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

// 4. Hospital Quality
const hospital = validateJSON('hospital-quality.json');
if (hospital) {
    checkStaleness(hospital, 'hospital-quality.json');
    if (hospital.centerReputation) {
        checkCityCoverage(hospital.centerReputation, 'hospital-quality.json (centerReputation)');
        checkValueRange(hospital.centerReputation, 'hospital-quality.json (centerReputation)', 50, 100);
    }
    if (hospital.centerVolumes) {
        for (const organ of ['kidney', 'liver', 'heart', 'lung', 'pancreas', 'intestine']) {
            if (hospital.centerVolumes[organ]) {
                checkCityCoverage(hospital.centerVolumes[organ], `hospital-quality.json (${organ} volumes)`);
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
    checkCityCoverage(costOfLiving.cities || {}, 'cost-of-living.json (legacy cities block)');
}

// 6. Donor Registration
const donor = validateJSON('donor-registration.json');
if (donor) {
    checkStaleness(donor, 'donor-registration.json');
    if (donor.livingDonorProgramStrength) {
        checkCityCoverage(donor.livingDonorProgramStrength, 'donor-registration.json (livingDonorProgramStrength)');
        checkValueRange(donor.livingDonorProgramStrength, 'donor-registration.json (livingDonorProgramStrength)', 0, 100);
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
const ptOutcomes = validateJSON('post-transplant-outcomes.json');
if (ptOutcomes && Object.keys(ptOutcomes.city_outcomes || {}).length === 0) {
    addError('post-transplant-outcomes.json: city_outcomes is empty');
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
for (const manualFile of ['manual/climate-scores.json', 'manual/policy-tiers.json', 'manual/socioeconomic.json']) {
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
