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

/**
 * #302: how old is the DATA, as opposed to how recently we ran a script?
 *
 * checkStaleness above reads _meta.fetchedAt, which answers the wrong
 * question in both directions. Measured 2026-08-27 on the shipped files:
 *
 *   cause-of-death-by-region.json  fetched 3 days ago  -> no warning,
 *                                  carrying CDC 2017 data
 *   donor-registration.json        "161 days old"      -> the data is
 *                                  from 2018, understated ~18x
 *
 * A file re-fetched weekly from a frozen upstream looks perpetually fresh.
 *
 * `atSourceCeiling` is the other half. A dataset at its publisher's ceiling
 * is not neglect and there is no action to take, so flagging it identically
 * to a refreshable file trains people to ignore the warnings that matter.
 * The ceiling must be RE-VERIFIED, not asserted: `ceilingCheckedOn` records
 * when someone last confirmed the upstream had published nothing newer, and
 * this warns once that claim goes stale.
 */
const VINTAGE_EXPECTATIONS = {
    'cause-of-death-by-region.json': {
        maxAgeYears: 3,
        atSourceCeiling: true,
        ceilingCheckedOn: '2026-08-27',
        why: 'NCHS bi63-dtpu is a closed 1999-2017 series; verified max(year)=2017 '
           + 'against the live API. No REST-accessible replacement carries '
           + 'state-level injury counts.',
    },
    'donor-registration.json': {
        maxAgeYears: 3,
        atSourceCeiling: false,
        why: 'Donate Life America publishes annually; the shipped values are 2018. '
           + 'Load-bearing: flattening state registration rates to the national '
           + 'mean leaves rho 0.9665 but changes the TOP-RANKED center and 6 of '
           + 'the top 10 (#302).',
    },
};

function checkVintage(data, filename) {
    const spec = VINTAGE_EXPECTATIONS[filename];
    if (!spec) return;

    const vintage = data?._meta?.vintage;
    if (typeof vintage !== 'number') {
        addWarning(`${filename}: no _meta.vintage — cannot tell how old the DATA is, `
                 + `only when it was last fetched`);
        return;
    }

    const age = new Date().getUTCFullYear() - vintage;
    if (age <= spec.maxAgeYears) return;

    if (spec.atSourceCeiling) {
        // Not neglect — but the claim has a shelf life of its own.
        const checked = Date.parse(spec.ceilingCheckedOn || '');
        const daysSince = (Date.now() - checked) / 86400000;
        if (!Number.isFinite(daysSince)) {
            addWarning(`${filename}: atSourceCeiling asserted with no ceilingCheckedOn date`);
        } else if (daysSince > 365) {
            addWarning(`${filename}: data is from ${vintage} and the "no newer release" `
                     + `claim was last verified ${Math.round(daysSince)} days ago — `
                     + `re-check the upstream. ${spec.why}`);
        }
        return;
    }

    addWarning(`${filename}: data is from ${vintage} (${age} years old, max ${spec.maxAgeYears}) `
             + `— refreshable, not at a source ceiling. ${spec.why}`);
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
    checkVintage(donor, 'donor-registration.json');
    checkCoverageFloor(donor.livingDonorProgramStrength, 'donor-registration.json (livingDonorProgramStrength)', 20);
    checkCoverageFloor(donor.stateRegistrationRates, 'donor-registration.json (stateRegistrationRates)', 50);
    if (donor.livingDonorProgramStrength) {
        checkValueRange(donor.livingDonorProgramStrength, 'donor-registration.json (livingDonorProgramStrength)', 0, 100);
    }
}

// 6b. Cause of Death by Region (#302: was not validated at all — no staleness
// check and no never-shrink floor, on an input that feeds donor availability)
const cod = validateJSON('cause-of-death-by-region.json');
if (cod) {
    checkStaleness(cod, 'cause-of-death-by-region.json');
    checkVintage(cod, 'cause-of-death-by-region.json');
    checkCoverageFloor(cod.stateCauseOfDeathProportions,
                       'cause-of-death-by-region.json (stateCauseOfDeathProportions)', 51);
    checkCoverageFloor(cod.organRecoveryRates,
                       'cause-of-death-by-region.json (organRecoveryRates)', 6);
}

// 6a1a. The remaining unfloored per-center files (#444 follow-up sweep).
// Each is written by a script with no write guard, and srtr-all-centers.json
// is written by THREE (extract-center-list, geocode-centers,
// verify-geocoding). It is the master center list; before this it appeared in
// validation only as the *denominator* of the trauma-scores check, so a
// shrink was caught incidentally, by a different file's assertion, and only
// while that other file stayed intact. That is coverage by coincidence.
for (const [file, container, floor] of [
    ['srtr-all-centers.json', 'centers', 200],
    ['opo-mapping.json', 'centerOpoMap', 200],
    ['acceptance-rates-centers.json', 'center_acceptance_factors', 180],
    ['center-contacts.json', 'contacts', 200],
]) {
    const d = validateJSON(file);
    if (d) {
        if (!d[container]) {
            addError(`${file}: container '${container}' missing`);
        } else {
            checkCoverageFloor(d[container], `${file} (${container})`, floor);
        }
    }
}

// 6a0. Center coordinates must be plausible, and in the state they claim.
//
// scoring.py resolves a center's position with `center.get("lat", 0)`, so a
// geocoding failure does not raise — it places the hospital at (0, 0) in the
// Gulf of Guinea and scores every distance and spatial layer from there. All
// 248 currently geocode fine, so this guards a latent hazard rather than a
// live bug: srtr-all-centers.json is written by THREE scripts
// (extract-center-list, geocode-centers, verify-geocoding), 133 of its
// entries are plain unverified `nominatim`, and until #445 it had no floor of
// any kind. The entry-count floor added there cannot see a coordinate that
// moved.
//
// State boxes are derived from health-demographics-counties.json (3144
// counties carrying lat/lon AND state) rather than hand-written, so there are
// no invented constants and the reference comes from a different pipeline
// than center geocoding. Verified against three real failure modes: zeroed
// coordinates, a Texas center placed in Maine, and a flipped longitude sign —
// all three caught, with no false positives on the shipped data.
const centersForGeo = validateJSON('srtr-all-centers.json');
const countiesForGeo = validateJSON('health-demographics-counties.json');
if (centersForGeo && countiesForGeo) {
    const boxes = {};
    for (const c of Object.values(countiesForGeo.counties || {})) {
        if (!c || !c.state || typeof c.lat !== 'number' || typeof c.lon !== 'number') continue;
        const b = boxes[c.state] || (boxes[c.state] = [90, -90, 180, -180]);
        b[0] = Math.min(b[0], c.lat); b[1] = Math.max(b[1], c.lat);
        b[2] = Math.min(b[2], c.lon); b[3] = Math.max(b[3], c.lon);
    }
    if (Object.keys(boxes).length < 45) {
        addError(`center geocoding check: only ${Object.keys(boxes).length} state boxes `
               + `derived from health-demographics-counties.json (expected >=45) — `
               + `the check below would pass without testing anything`);
    }
    // County centroids are not state borders, so allow ~55km of slack.
    const MARGIN = 0.5;
    for (const [code, c] of Object.entries(centersForGeo.centers || {})) {
        if (typeof c.lat !== 'number' || typeof c.lon !== 'number' || !c.lat || !c.lon) {
            addError(`srtr-all-centers.json: ${code} (${c.name || '?'}) has no usable `
                   + `coordinates (lat=${c.lat}, lon=${c.lon}) — scoring would place it `
                   + `at (0,0) and rank it from there`);
            continue;
        }
        if (c.lat < 17 || c.lat > 72 || c.lon < -180 || c.lon > -64) {
            addError(`srtr-all-centers.json: ${code} at (${c.lat}, ${c.lon}) is outside `
                   + `US/AK/HI/PR bounds`);
            continue;
        }
        // Puerto Rico has no rows in the county file; the bounds check above
        // is all such a center gets. Skipping silently rather than inventing
        // a bounding box for it.
        const b = boxes[c.state_abbr];
        if (!b) continue;
        if (c.lat < b[0] - MARGIN || c.lat > b[1] + MARGIN ||
            c.lon < b[2] - MARGIN || c.lon > b[3] + MARGIN) {
            addError(`srtr-all-centers.json: ${code} (${c.name || '?'}) claims `
                   + `${c.state_abbr} but (${c.lat}, ${c.lon}) falls outside that state — `
                   + `check scripts/geocode-centers.py`);
        }
    }
}

// 6a1-pre. The last of the unfloored files. Nine of data/'s 38 JSON files
// were never mentioned in this validator at all; these are the ones the
// sweep showed reach production or the frontend, plus two analysis inputs
// whose loss would silently weaken a validation rather than break it.
for (const [file, container, floor, why] of [
    ['health-demographics-counties.json', 'counties', 3000,
     'county health layer — read by 2 backend modules and 4 frontend files'],
    ['air-quality-monitors.json', 'monitors', 2000,
     'environmental layer for the spatial tab'],
    ['cbsa-centroids.json', 'cbsas', 350,
     'metro centroids — the spatial join falls back to nothing without them'],
    ['srtr-observed-rates-historical.json', 'releases', 10,
     'the temporal-validation input; a short series still fits a trend'],
]) {
    const d = validateJSON(file);
    if (d) {
        if (!d[container]) {
            addError(`${file}: container '${container}' missing (${why})`);
        } else {
            checkCoverageFloor(d[container], `${file} (${container})`, floor);
        }
    }
}

// srtr-center-mapping.json drives the city-level parse in
// parse-srtr-reports.py. It is legacy (22 cities, retiring under #285) but it
// is still an INPUT, and losing it would degrade a parse rather than fail it.
const centerMapping = validateJSON('srtr-center-mapping.json');
if (centerMapping) {
    const n = Object.keys(centerMapping.cities || {}).length;
    if (n < 20) {
        addError(`srtr-center-mapping.json: only ${n} cities (floor: 20) — `
               + `parse-srtr-reports.py maps centers to cities through this`);
    }
}

// Deliberately NOT floored: horizon-alpha-fit.json and
// horizon-extension-sweep.json. Both are analysis OUTPUTS, not inputs — a
// sweep that legitimately explores a smaller grid would trip a floor, so one
// here would fail honest work and get raised until it meant nothing. The
// distinction worth keeping: floor what the model READS, not what it writes.

// offer-acceptance-panel.json is keyed by organ, not center, so the
// center-code detector in tests/data-file-floors.test.js does not see it.
const panel = validateJSON('offer-acceptance-panel.json');
if (panel) {
    const n = Object.keys(panel.panel || {}).length;
    if (n < 5) {
        addError(`offer-acceptance-panel.json: only ${n} organs in the panel (floor: 5)`);
    }
}

// 6a1a-0. srtr-observed-rates.json — the calibration GROUND TRUTH, and the
// one file where a silent shrink is worse than a crash.
//
// run-center-calibration.py joins predictions against it with
// `obs = observed.get(code); if not obs: continue` — a center missing here is
// skipped, not flagged. So a truncated file does not fail calibration; it
// makes calibration agree with itself over a handful of centers and report a
// perfectly respectable rho. `matched_centers` is printed in the report and
// asserted nowhere. Fifteen modules read this file, including data_loader and
// bbn_parameterizer in production.
//
// This is the "gates lie in specific ways" case from CLAUDE.md, one level
// down: not a gate blind to the change, but a gate whose reference data can
// quietly shrink underneath it.
const observedRates = validateJSON('srtr-observed-rates.json');
if (observedRates) {
    for (const [organ, floor] of [
        ['kidney', 200], ['liver', 130], ['heart', 130],
        ['lung', 65], ['pancreas', 70], ['intestine', 14],
    ]) {
        const block = observedRates[organ];
        if (!block || !block.centers) {
            addError(`srtr-observed-rates.json: organ '${organ}' missing its centers block `
                   + `— calibration for it would silently match zero centers`);
            continue;
        }
        checkCoverageFloor(block.centers, `srtr-observed-rates.json (${organ}.centers)`, floor);
        const rated = Object.values(block.centers)
            .filter(c => c && c.transplant_rate !== null && c.transplant_rate !== undefined).length;
        if (rated < floor) {
            addError(`srtr-observed-rates.json: only ${rated} ${organ} centers carry a `
                   + `transplant_rate (floor: ${floor}) — the rest are skipped by the join, `
                   + `so calibration would quietly run on a subset`);
        }
    }
}

// 6a1a-ii. The rest of what the sweep turned up. Two partial-coverage cases,
// which are the more instructive ones: opo-mapping.json had a floor on none
// of its five containers, and srtr-tiers-centers.json was floored on kidney
// alone (#320) while its five other organs went unchecked — a floor on one
// organ reads, at a glance, as a floor on the file.
//
// Floors sit near 90% of current coverage, rounded down. They exist to catch
// a collapse, not to freeze the data: SRTR organ coverage genuinely drifts by
// a few centers per release, and a floor set at exactly today's count would
// fail the next legitimate refresh and get raised without being read.
for (const [file, container, floor] of [
    ['center-cbsa-map.json', 'centers', 200],
    ['opo-mapping.json', 'opos', 50],
    ['opo-mapping.json', 'centerOpoDetails', 200],
    ['opo-mapping.json', 'opoCenterCounts', 50],
    ['opo-mapping.json', 'countyToOpo', 3000],
]) {
    const d = validateJSON(file);
    if (d) {
        if (!d[container]) {
            addError(`${file}: container '${container}' missing`);
        } else {
            checkCoverageFloor(d[container], `${file} (${container})`, floor);
        }
    }
}

const srtrTiers = validateJSON('srtr-tiers-centers.json');
if (srtrTiers) {
    for (const [organ, floor] of [
        ['kidney', 210], ['liver', 130], ['heart', 130],
        ['lung', 65], ['pancreas', 95], ['intestine', 15],
    ]) {
        if (!srtrTiers[organ]) {
            addError(`srtr-tiers-centers.json: organ block '${organ}' missing`);
        } else {
            checkCoverageFloor(srtrTiers[organ], `srtr-tiers-centers.json (${organ})`, floor);
        }
    }
}

// 6a1b. Center-level SRTR files — never-shrink floors (#444 follow-up).
// These are the files data_loader actually loads and the model runs on, and
// until now NOTHING protected them: parse-srtr-reports.py wrote all four with
// a bare open(), and validate-data.js had floors on the small legacy 22-city
// aggregates beside them but none on these. The write guard is the first line;
// this is the second, and it is the one that runs in CI on every push.
for (const [file, container, floor] of [
    ['competing-risks-centers.json', 'center_adjustments', 200],
    ['wait-time-distributions-centers.json', 'center_wait_time_factors', 200],
    ['post-transplant-outcomes-centers.json', 'center_outcomes', 200],
]) {
    const d = validateJSON(file);
    if (d) {
        if (!d[container]) {
            addError(`${file}: container '${container}' missing`);
        } else {
            checkCoverageFloor(d[container], `${file} (${container})`, floor);
        }
    }
}

// srtr-historical.json's coverage dimension is RELEASES, not centers: a parse
// run without srtr-raw/historical/ still appends the current release, so it
// yields a structurally valid 1-release file. An entry-count floor cannot see
// that — the 22 city blocks survive intact while 14 years of history vanish.
const srtrHist = validateJSON('srtr-historical.json');
if (srtrHist) {
    const releases = (srtrHist._meta || {}).releases;
    if (!Array.isArray(releases) || releases.length < 10) {
        addError(`srtr-historical.json: only ${Array.isArray(releases) ? releases.length : 0} `
               + `SRTR releases (never-shrink floor: 10) — the trend line shown for every `
               + `center is built from these`);
    }
    if (((srtrHist._meta || {}).source || '').includes('Synthetic')) {
        addError('srtr-historical.json: source is SYNTHETIC — every center trend is fabricated. '
               + 'Restore from git; scripts/generate-srtr-historical.py must not have run.');
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

// === County trauma scores (#336) ===
// These feed the scoring trauma surface in preference to the state scores.
// A truncated file would silently fall back to state resolution, which looks
// like a working analysis, so check shape and scale explicitly.
const countyTrauma = validateJSON('trauma-scores-counties.json');
if (countyTrauma) {
    const centerScores = countyTrauma.center_scores || {};
    const countyScores = countyTrauma.county_scores || {};
    const atCounty = Object.values(centerScores)
        .filter(r => r && r.resolution === 'county').length;
    if (atCounty < 200) {
        addError(`trauma-scores-counties.json: only ${atCounty} centers at county ` +
                 `resolution (floor: 200) — centroid matching may be failing`);
    }
    if (Object.keys(countyScores).length < 3000) {
        addError(`trauma-scores-counties.json: only ` +
                 `${Object.keys(countyScores).length} counties (floor: 3000)`);
    }
    const vals = Object.values(countyScores).map(r => r && r.score)
        .filter(v => typeof v === 'number');
    if (vals.length) {
        const top = Math.max(...vals);
        if (Math.abs(top - 100) > 0.51) {
            addError(`trauma-scores-counties.json: top score ${top} — scores must ` +
                     `be normalized so the highest county is 100`);
        }
        if (Math.min(...vals) < 0) {
            addError('trauma-scores-counties.json: negative score present');
        }
    }
    for (const [code, rec] of Object.entries(centerScores)) {
        if (rec && rec.resolution === 'county' && rec.match_distance_miles > 60) {
            addError(`trauma-scores-counties.json: ${code} matched a county ` +
                     `centroid ${rec.match_distance_miles} mi away`);
            break;
        }
    }
    // Every center must be accounted for — scored, on the state fallback, or
    // explicitly listed as unscorable. The first version silently dropped the
    // two Puerto Rico programs and reported 246 with nothing saying why.
    const meta = countyTrauma._meta || {};
    const accounted = (meta.centers_county_resolution || 0) +
                      (meta.centers_state_fallback || 0) +
                      (meta.centers_unscorable || []).length;
    const allCenters = validateJSON('srtr-all-centers.json');
    if (allCenters) {
        const total = Object.keys(allCenters.centers || {}).length;
        if (accounted !== total) {
            addError(`trauma-scores-counties.json: ${accounted} of ${total} ` +
                     `centers accounted for — some were dropped silently`);
        }
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
