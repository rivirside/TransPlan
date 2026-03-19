#!/usr/bin/env node
/**
 * Fetch traffic fatality data.
 *
 * Primary: NHTSA FARS bulk CSV download (state-level fatality totals)
 * Source:  https://static.nhtsa.gov/nhtsa/downloads/FARS/{year}/National/FARS{year}NationalCSV.zip
 * Auth:    None required
 * Format:  ZIP containing CSV files
 *
 * The original FARS API (crashviewer.nhtsa.dot.gov) was retired in late 2025.
 * This script now downloads the annual FARS CSV bulk archive, extracts the
 * ACCIDENT.CSV file, and sums fatalities per state FIPS code.
 *
 * FARS data lags ~2 years: in 2026 the latest available year is 2023 or 2022.
 *
 * Fallback: If the bulk download fails, seed data is preserved via mergeDataFile.
 */

const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');
const os = require('os');
const { execFileSync } = require('child_process');
const { mergeDataFile, updateMetadata, reportError, CITIES } = require('./utils');

// State FIPS → abbreviation mapping
const FIPS_TO_ABBR = {};
CITIES.forEach(c => { FIPS_TO_ABBR[c.stateFips] = c.stateAbbr; });
const UNIQUE_STATES = [...new Set(CITIES.map(c => c.stateAbbr))];

// State populations (2023 Census estimates) for per-capita normalization
const STATE_POPULATIONS = {
    PA: 12972008, MD: 6180253, NY: 19677151, MN: 5717184,
    WI: 5910955, IL: 12582032, OH: 11756058, MO: 6196156,
    IN: 6876047, NE: 1978379, TN: 7126489, NC: 10835491,
    FL: 22610726, TX: 30503301, OR: 4233358, WA: 7812880,
    CA: 38965193
};

// State abbreviation → full name mapping
const ABBR_TO_STATE = {};
CITIES.forEach(c => { ABBR_TO_STATE[c.stateAbbr] = c.state; });

/**
 * Download a file from a URL, following redirects, and return the Buffer.
 */
function downloadBuffer(url, maxRedirects = 5) {
    return new Promise((resolve, reject) => {
        if (maxRedirects <= 0) return reject(new Error('Too many redirects'));
        const client = url.startsWith('https') ? https : http;
        client.get(url, { timeout: 120000 }, (res) => {
            if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
                return resolve(downloadBuffer(res.headers.location, maxRedirects - 1));
            }
            if (res.statusCode !== 200) {
                res.resume();
                return reject(new Error(`HTTP ${res.statusCode} for ${url}`));
            }
            const chunks = [];
            res.on('data', chunk => chunks.push(chunk));
            res.on('end', () => resolve(Buffer.concat(chunks)));
            res.on('error', reject);
        }).on('error', reject);
    });
}

/**
 * Parse a simple CSV line (no quoted fields in FARS ACCIDENT.CSV).
 */
function parseCSVLine(line) {
    return line.split(',').map(f => f.trim());
}

/**
 * Extract ACCIDENT.CSV from a FARS zip using the system unzip command
 * and sum FATALS grouped by STATE code.
 * Returns Map<stateAbbr, totalFatalities>.
 */
function parseFARSZip(zipBuffer) {
    const tmpZip = path.join(os.tmpdir(), `fars_${Date.now()}.zip`);
    const tmpDir = path.join(os.tmpdir(), `fars_${Date.now()}`);

    try {
        fs.writeFileSync(tmpZip, zipBuffer);
        fs.mkdirSync(tmpDir, { recursive: true });

        // Extract just ACCIDENT.CSV using execFileSync (no shell injection risk)
        try {
            execFileSync('unzip', ['-o', '-j', tmpZip, '*ACCIDENT*', '-d', tmpDir], { stdio: 'pipe' });
        } catch {
            execFileSync('unzip', ['-o', '-j', tmpZip, '*accident*', '-d', tmpDir], { stdio: 'pipe' });
        }

        const files = fs.readdirSync(tmpDir);
        const accFile = files.find(f => f.toUpperCase().includes('ACCIDENT'));
        if (!accFile) throw new Error('ACCIDENT.CSV not found after extraction');

        const csv = fs.readFileSync(path.join(tmpDir, accFile), 'utf8');
        return sumFatalitiesFromCSV(csv);
    } finally {
        // Cleanup
        try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch {}
        try { fs.unlinkSync(tmpZip); } catch {}
    }
}

/**
 * Parse ACCIDENT.CSV and sum FATALS grouped by STATE code.
 */
function sumFatalitiesFromCSV(csv) {
    const lines = csv.split('\n').filter(l => l.trim());
    if (lines.length < 2) throw new Error('ACCIDENT.CSV is empty');

    const headers = parseCSVLine(lines[0]).map(h => h.toUpperCase());
    const stateIdx = headers.indexOf('STATE');
    const fatalsIdx = headers.indexOf('FATALS');

    if (stateIdx === -1 || fatalsIdx === -1) {
        throw new Error(`Missing columns: STATE=${stateIdx}, FATALS=${fatalsIdx}. Headers: ${headers.slice(0, 10).join(',')}`);
    }

    const stateTotals = new Map();
    for (let i = 1; i < lines.length; i++) {
        const fields = parseCSVLine(lines[i]);
        if (fields.length <= Math.max(stateIdx, fatalsIdx)) continue;

        // STATE is FIPS code (e.g., 42 for PA), zero-pad to 2 digits
        const stateFips = fields[stateIdx].padStart(2, '0');
        const fatals = parseInt(fields[fatalsIdx]) || 0;
        const abbr = FIPS_TO_ABBR[stateFips];

        if (abbr && UNIQUE_STATES.includes(abbr)) {
            stateTotals.set(abbr, (stateTotals.get(abbr) || 0) + fatals);
        }
    }

    return stateTotals;
}

async function fetchStateFatalities() {
    console.log('Fetching traffic fatality data from NHTSA FARS bulk CSV...');
    const currentYear = new Date().getFullYear();
    // FARS data lags ~2 years; try year-2 first, then year-3
    const yearsToTry = [currentYear - 2, currentYear - 3];

    let stateFatalities = null;
    let successYear = null;

    for (const year of yearsToTry) {
        const url = `https://static.nhtsa.gov/nhtsa/downloads/FARS/${year}/National/FARS${year}NationalCSV.zip`;
        console.log(`  Trying FARS ${year}: ${url}`);

        try {
            const zipBuffer = await downloadBuffer(url);
            console.log(`  Downloaded ${(zipBuffer.length / 1024 / 1024).toFixed(1)} MB zip`);

            stateFatalities = parseFARSZip(zipBuffer);
            successYear = year;
            console.log(`  Parsed ${stateFatalities.size} states from FARS ${year}`);
            break;
        } catch (err) {
            console.warn(`  FARS ${year} failed: ${err.message}`);
        }
    }

    if (!stateFatalities || stateFatalities.size === 0) {
        console.warn('No FARS data retrieved — seed data preserved.');
        updateMetadata('traffic-fatalities', 'NHTSA FARS CSV', 'error');
        return;
    }

    // Compute per-capita rates and trauma scores
    const stateFatalityRates = {};
    const traumaScores = {};

    for (const [abbr, fatals] of stateFatalities) {
        const pop = STATE_POPULATIONS[abbr] || 5000000;
        const ratePer100k = (fatals / pop) * 100000;
        const fullState = ABBR_TO_STATE[abbr];
        if (fullState) {
            stateFatalityRates[fullState] = parseFloat(ratePer100k.toFixed(2));
        }
    }

    // Compute trauma scores per city
    // US average is ~12-13 per 100k; range is roughly 5-25 per 100k
    for (const { city, stateAbbr } of CITIES) {
        const fullState = ABBR_TO_STATE[stateAbbr];
        const ratePer100k = stateFatalityRates[fullState] || 12;
        const score = Math.min(100, Math.max(0, Math.round((ratePer100k / 25) * 100)));
        traumaScores[city] = score;
    }

    const stateCount = Object.keys(stateFatalityRates).length;
    const output = { stateFatalityRates, traumaScores };
    mergeDataFile('traffic-fatalities.json', output, `NHTSA FARS ${successYear} CSV bulk download`);
    updateMetadata('traffic-fatalities', 'NHTSA FARS CSV', 'fetched');
    console.log(`Fetched fatality data for ${stateCount} states (FARS ${successYear}).`);
}

fetchStateFatalities().catch(err => {
    reportError('NHTSA FARS CSV', err);
    process.exit(1);
});
