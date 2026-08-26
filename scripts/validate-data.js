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
    // #335: every BBN age group must resolve to a multiplier. Losing '0-17'
    // would not crash — age_to_group would return a group the table lacks and
    // the CPT builder's `.get(..., 1.0)` default would silently apply 1.0 to
    // every child, wiping out the 3.0x pediatric heart hazard.
    const AGE_GROUPS = ['0-17', '18-34', '35-49', '50-64', '65+'];
    const globalAges = competingRisks.age_mortality_multipliers || {};
    for (const g of AGE_GROUPS) {
        const v = globalAges[g];
        if (typeof v !== 'number' || !(v > 0 && v < 20)) {
            addError(`competing-risks.json: age_mortality_multipliers['${g}'] = ${v} (expected a positive number < 20)`);
        }
    }
    for (const [organ, block] of Object.entries(competingRisks.age_organ_overrides || {})) {
        if (organ.startsWith('_')) continue;
        for (const [g, v] of Object.entries(block)) {
            if (g.startsWith('_')) continue;
            if (!AGE_GROUPS.includes(g)) {
                addError(`competing-risks.json: age_organ_overrides.${organ} has unknown age group '${g}'`);
            } else if (typeof v !== 'number' || !(v > 0 && v < 20)) {
                addError(`competing-risks.json: age_organ_overrides.${organ}['${g}'] = ${v} implausible`);
            }
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

// === Waitlist composition (#337) — equity cell weights ===
// If this file is lost or truncated, equity silently falls back to
// general-population weights, which understate type B on the kidney waitlist
// — the group facing the longest waits. A quiet fallback would look like a
// working analysis, so fail loudly instead.
const waitlistComp = validateJSON('waitlist-composition.json');
if (waitlistComp) {
    const organs = Object.keys(waitlistComp).filter(k => k !== '_meta');
    if (organs.length < 4) {
        addError(`waitlist-composition.json: only ${organs.length} organs (floor: 4)`);
    }
    for (const organ of organs) {
        const rec = waitlistComp[organ] || {};
        for (const dim of ['age_brackets', 'sex', 'abo_group', 'blood_type']) {
            const dist = rec[dim];
            if (!dist || !Object.keys(dist).length) {
                addError(`waitlist-composition.json: ${organ}.${dim} missing`);
                continue;
            }
            const total = Object.values(dist).reduce((a, b) => a + b, 0);
            if (Math.abs(total - 1) > 0.02) {
                addError(`waitlist-composition.json: ${organ}.${dim} sums to ` +
                         `${total.toFixed(4)}, not 1.0`);
            }
        }
        if (!(rec.n_listed > 0)) {
            addError(`waitlist-composition.json: ${organ}.n_listed = ${rec.n_listed}`);
        }
    }
}

// === County population (#336) — denominator for per-capita work ===
// Nothing in the repo had population at any geography before this; three
// separate issues (#336 county trauma, #113 coverage, #267 2SFCA) depend on
// it, so a silently-truncated fetch would corrupt all three at once.
const countyPop = validateJSON('county-population.json');
if (countyPop) {
    const counties = countyPop.counties || {};
    const n = Object.keys(counties).length;
    if (n < 3000) {
        addError(`county-population.json: only ${n} counties (never-shrink floor: 3000)`);
    }
    let total = 0;
    let bad = 0;
    for (const [fips, rec] of Object.entries(counties)) {
        if (!/^\d{5}$/.test(fips)) {
            addError(`county-population.json: '${fips}' is not a 5-digit FIPS code`);
            break;
        }
        const pop = rec && rec.population;
        if (typeof pop !== 'number' || pop < 1 || pop > 15000000) {
            if (bad++ === 0) {
                addError(`county-population.json: ${fips} population = ${pop} implausible`);
            }
        } else {
            total += pop;
        }
    }
    // The US population is ~335-345M. A total far outside that means the wrong
    // column was read or state rows leaked in as counties.
    if (total < 300000000 || total > 380000000) {
        addError(`county-population.json: national total ${total} outside 300-380M — ` +
                 `wrong column, or state rows counted as counties?`);
    }
}

// === Published validation artifacts must be dated (#328) ===
// Everything under docs-site/static/data/ is served publicly and read by the
// model card. Only 4 of 21 files carried a timestamp, so a reader could not
// tell whether a reported correlation reflected current data. They were
// backfilled; this keeps a regenerated file from silently dropping its stamp
// again. Generators should build `_meta` via scripts/artifact_meta.py.
const artifactDir = path.join(__dirname, '..', 'docs-site', 'static', 'data');
if (fs.existsSync(artifactDir)) {
    for (const name of fs.readdirSync(artifactDir)) {
        if (!name.endsWith('.json')) continue;
        let doc;
        try {
            doc = JSON.parse(fs.readFileSync(path.join(artifactDir, name), 'utf8'));
        } catch (e) {
            addError(`docs-site/static/data/${name}: invalid JSON (${e.message})`);
            continue;
        }
        const stamp = doc && doc._meta && doc._meta.generated;
        if (!stamp) {
            addError(`docs-site/static/data/${name}: no _meta.generated — ` +
                     `stamp it via scripts/artifact_meta.py, or run ` +
                     `scripts/backfill-artifact-meta.py`);
        } else if (isNaN(Date.parse(stamp))) {
            addError(`docs-site/static/data/${name}: _meta.generated ` +
                     `"${stamp}" is not a parseable date`);
        }
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
