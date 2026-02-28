#!/usr/bin/env node
/**
 * Post-fetch data validation.
 * Checks: JSON syntax, expected schema, value ranges, coverage of all 21 cities, staleness.
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
    checkStaleness(airQuality);
    const { _meta, ...aqData } = airQuality;
    checkCityCoverage(aqData, 'air-quality.json');
    checkValueRange(aqData, 'air-quality.json', 0, 100);
}

// 2. Traffic Fatalities
const traffic = validateJSON('traffic-fatalities.json');
if (traffic) {
    checkStaleness(traffic);
    if (traffic.traumaScores) {
        checkCityCoverage(traffic.traumaScores, 'traffic-fatalities.json (traumaScores)');
        checkValueRange(traffic.traumaScores, 'traffic-fatalities.json (traumaScores)', 0, 100);
    }
}

// 3. Health Demographics
const health = validateJSON('health-demographics.json');
if (health) {
    checkStaleness(health);
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
    checkStaleness(hospital);
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

// 5. Cost of Living
const costOfLiving = validateJSON('cost-of-living.json');
if (costOfLiving) {
    checkStaleness(costOfLiving);
    const { _meta, ...colData } = costOfLiving;
    checkCityCoverage(colData, 'cost-of-living.json');
    checkValueRange(colData, 'cost-of-living.json', 50, 300);
}

// 6. Donor Registration
const donor = validateJSON('donor-registration.json');
if (donor) {
    checkStaleness(donor);
    if (donor.livingDonorProgramStrength) {
        checkCityCoverage(donor.livingDonorProgramStrength, 'donor-registration.json (livingDonorProgramStrength)');
        checkValueRange(donor.livingDonorProgramStrength, 'donor-registration.json (livingDonorProgramStrength)', 0, 100);
    }
}

// 7. Manual files
for (const manualFile of ['manual/climate-scores.json', 'manual/policy-tiers.json', 'manual/socioeconomic.json']) {
    const data = validateJSON(manualFile);
    if (data) {
        checkStaleness(data);
    }
}

// 8. Metadata
const metadata = validateJSON('metadata.json');
if (metadata) {
    if (!metadata.sources) {
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
