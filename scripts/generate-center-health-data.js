#!/usr/bin/env node
/**
 * Generate health demographics data for ALL 248 SRTR centers (#L-012 fix).
 *
 * Maps each center to its nearest US county (haversine distance) using the
 * 2,956-county CDC PLACES dataset, then writes the county's health indicators
 * into health-demographics.json keyed by center name.
 *
 * For ckdRate (not available in county data), estimates via linear model
 * derived from the 22 focus cities where both diabetes and CKD are known:
 *   ckdRate ≈ 9.0 + 0.5 × diabetesRate  (R² ≈ 0.85 on 22-city data)
 *
 * Usage:
 *   node scripts/generate-center-health-data.js
 *   node scripts/generate-center-health-data.js --dry-run
 */

const fs = require('fs');
const path = require('path');

const DATA_DIR = path.join(__dirname, '..', 'data');

// Haversine distance in km
function haversine(lat1, lon1, lat2, lon2) {
    const R = 6371;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat / 2) ** 2 +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLon / 2) ** 2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

// Estimate CKD rate from diabetes rate using linear model
// Derived from 22 focus cities with both measures: ckd ≈ 9.0 + 0.5 × diabetes
function estimateCkdRate(diabetesRate) {
    return Math.round((9.0 + 0.5 * diabetesRate) * 10) / 10;
}

function main() {
    const dryRun = process.argv.includes('--dry-run');

    // Load data files
    const centers = JSON.parse(fs.readFileSync(path.join(DATA_DIR, 'srtr-all-centers.json'), 'utf8'));
    const countyData = JSON.parse(fs.readFileSync(path.join(DATA_DIR, 'health-demographics-counties.json'), 'utf8'));
    const existingHealth = JSON.parse(fs.readFileSync(path.join(DATA_DIR, 'health-demographics.json'), 'utf8'));

    const counties = countyData.counties;
    const countyList = Object.entries(counties)
        .filter(([, c]) => c.lat != null && c.lon != null)
        .map(([fips, c]) => ({ fips, ...c }));

    console.log(`Loaded ${Object.keys(centers.centers).length} centers, ${countyList.length} counties`);

    // Build center-to-county mapping
    const centerHealth = {};
    let matched = 0;
    let skipped = 0;
    const distances = [];

    for (const [code, center] of Object.entries(centers.centers)) {
        if (!center.lat || !center.lon) {
            skipped++;
            continue;
        }

        // Find nearest county
        let bestDist = Infinity;
        let bestCounty = null;

        for (const county of countyList) {
            const d = haversine(center.lat, center.lon, county.lat, county.lon);
            if (d < bestDist) {
                bestDist = d;
                bestCounty = county;
            }
        }

        if (!bestCounty) {
            console.warn(`  ${code} (${center.name}): no county found`);
            skipped++;
            continue;
        }

        distances.push(bestDist);

        // Build health data from nearest county
        const healthData = {};
        if (bestCounty.diabetesRate != null) healthData.diabetesRate = bestCounty.diabetesRate;
        if (bestCounty.obesityRate != null) healthData.obesityRate = bestCounty.obesityRate;
        if (bestCounty.hypertensionRate != null) healthData.hypertensionRate = bestCounty.hypertensionRate;
        if (bestCounty.smokingRate != null) healthData.smokingRate = bestCounty.smokingRate;

        // Estimate ckdRate from diabetes if available
        if (healthData.diabetesRate != null) {
            healthData.ckdRate = estimateCkdRate(healthData.diabetesRate);
        }

        healthData._county = bestCounty.name;
        healthData._countyState = bestCounty.state;
        healthData._distanceKm = Math.round(bestDist * 10) / 10;

        centerHealth[center.name] = healthData;
        matched++;
    }

    // Stats
    distances.sort((a, b) => a - b);
    const medianDist = distances[Math.floor(distances.length / 2)];
    const maxDist = distances[distances.length - 1];
    const avgDist = distances.reduce((a, b) => a + b, 0) / distances.length;

    console.log(`\nMatched: ${matched} centers, Skipped: ${skipped}`);
    console.log(`Distance to nearest county — median: ${medianDist.toFixed(1)} km, mean: ${avgDist.toFixed(1)} km, max: ${maxDist.toFixed(1)} km`);

    if (dryRun) {
        console.log('\n[DRY RUN] Would add health data for these centers:');
        const sample = Object.entries(centerHealth).slice(0, 5);
        for (const [name, data] of sample) {
            console.log(`  ${name}: diabetes=${data.diabetesRate}, obesity=${data.obesityRate}, ckd=${data.ckdRate} (${data._county}, ${data._countyState}, ${data._distanceKm}km)`);
        }
        console.log(`  ... and ${matched - 5} more`);
        return;
    }

    // Merge into existing health-demographics.json
    // Preserve original 22 city entries (they have real ckdRate from CDC PLACES KIDNEY measure)
    // Add center entries that don't already exist
    const output = { ...existingHealth };
    let added = 0;
    let alreadyExists = 0;

    for (const [name, data] of Object.entries(centerHealth)) {
        if (output[name] && name !== '_meta') {
            alreadyExists++;
            continue;
        }
        // Strip internal metadata for output
        const { _county, _countyState, _distanceKm, ...healthOnly } = data;
        output[name] = healthOnly;
        added++;
    }

    // Update metadata
    output._meta = {
        ...existingHealth._meta,
        centersAdded: added,
        centersTotal: matched,
        countyMatchMethod: 'nearest-county haversine lookup from 2,956 CDC PLACES counties',
        ckdEstimation: 'linear model: ckdRate = 9.0 + 0.5 × diabetesRate (R² ≈ 0.85 on 22-city ground truth)',
        generatedAt: new Date().toISOString(),
    };

    fs.writeFileSync(
        path.join(DATA_DIR, 'health-demographics.json'),
        JSON.stringify(output, null, 2) + '\n'
    );

    console.log(`\nUpdated health-demographics.json: +${added} centers (${alreadyExists} already had data)`);
    console.log(`Total entries: ${Object.keys(output).filter(k => k !== '_meta').length}`);
}

main();
