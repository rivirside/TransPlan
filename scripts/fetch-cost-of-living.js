#!/usr/bin/env node
/**
 * Refresh cost-of-living data from BEA Regional Price Parities (#205, #234).
 *
 * Source: https://apps.bea.gov/regional/zip/MARPP.zip (MSA-level RPPs) and
 *         https://apps.bea.gov/regional/zip/SARPP.zip (state-level RPPs).
 *         Public bulk files — no API key required.
 *
 * Snapshot-first design: the committed data/cost-of-living.json is the source
 * of truth the app runs on. This script only *updates* the snapshot, and only
 * when the fresh download passes validation (see validateSnapshot). On any
 * fetch/parse/validation failure the existing snapshot is left untouched, so
 * the app never depends on the BEA endpoint being up or correct.
 *
 * Output shape (national average = 100 by construction):
 *   _meta:    { fetchedAt, source, vintage }
 *   msas:     { "<5-digit CBSA>": { name, rpp } }   ~380 metro areas
 *   states:   { "<2-letter abbr>": rpp }            50 states + DC
 *   nonmetroUS: rpp for the US nonmetropolitan portion (rural fallback)
 *   cities:   { "<city name>": rpp }                legacy 22-city block,
 *             derived from each city's MSA RPP (kept for validate-data.js
 *             coverage checks and any remaining city-keyed consumers)
 */

const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const { writeDataFile, updateMetadata, reportError } = require('./utils');

const SNAPSHOT_PATH = path.join(__dirname, '..', 'data', 'cost-of-living.json');

function readSnapshot() {
    try {
        return JSON.parse(fs.readFileSync(SNAPSHOT_PATH, 'utf-8'));
    } catch {
        return null;  // first run or unreadable — validation skips comparisons
    }
}

const BEA_MSA_ZIP = 'https://apps.bea.gov/regional/zip/MARPP.zip';
const BEA_STATE_ZIP = 'https://apps.bea.gov/regional/zip/SARPP.zip';

// Legacy 22-city block: city name → CBSA code (2023 OMB delineations).
// Palo Alto sits in the San Jose MSA (41940), not San Francisco.
const CITY_CBSA = {
    'New York': '35620', 'Los Angeles': '31080', 'Chicago': '16980',
    'Houston': '26420', 'Dallas': '19100', 'Philadelphia': '37980',
    'Miami': '33100', 'San Francisco': '41860', 'Seattle': '42660',
    'Minneapolis': '33460', 'St. Louis': '41180', 'Baltimore': '12580',
    'Cleveland': '17410', 'Madison': '31540', 'Rochester': '40340',
    'Durham': '20500', 'Nashville': '34980', 'Omaha': '36540',
    'Indianapolis': '26900', 'Palo Alto': '41940', 'Portland': '38900',
    'Pittsburgh': '38300'
};

const STATE_ABBR = {
    'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR',
    'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE',
    'District of Columbia': 'DC', 'Florida': 'FL', 'Georgia': 'GA', 'Hawaii': 'HI',
    'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA',
    'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME',
    'Maryland': 'MD', 'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN',
    'Mississippi': 'MS', 'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE',
    'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM',
    'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH',
    'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI',
    'South Carolina': 'SC', 'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX',
    'Utah': 'UT', 'Vermont': 'VT', 'Virginia': 'VA', 'Washington': 'WA',
    'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY'
};

// ── Minimal ZIP entry extraction (BEA files are ordinary deflate/stored) ──

function unzipEntry(buf, namePattern) {
    // Read via the central directory (correct sizes even when entries use
    // streaming data descriptors, which BEA's zips do).
    let eocd = -1;
    for (let i = buf.length - 22; i >= Math.max(0, buf.length - 22 - 65535); i--) {
        if (buf.readUInt32LE(i) === 0x06054b50) { eocd = i; break; }
    }
    if (eocd < 0) throw new Error('Not a zip file (no end-of-central-directory record)');

    const count = buf.readUInt16LE(eocd + 10);
    let off = buf.readUInt32LE(eocd + 16);  // central directory start
    for (let n = 0; n < count; n++) {
        if (buf.readUInt32LE(off) !== 0x02014b50) throw new Error('Corrupt central directory');
        const method = buf.readUInt16LE(off + 10);
        const compSize = buf.readUInt32LE(off + 20);
        const nameLen = buf.readUInt16LE(off + 28);
        const extraLen = buf.readUInt16LE(off + 30);
        const commentLen = buf.readUInt16LE(off + 32);
        const localOff = buf.readUInt32LE(off + 42);
        const name = buf.toString('utf8', off + 46, off + 46 + nameLen);
        if (namePattern.test(name)) {
            // Local header's own name/extra lengths may differ from the CD's
            const lNameLen = buf.readUInt16LE(localOff + 26);
            const lExtraLen = buf.readUInt16LE(localOff + 28);
            const dataStart = localOff + 30 + lNameLen + lExtraLen;
            const raw = buf.subarray(dataStart, dataStart + compSize);
            if (method === 0) return raw.toString('utf8');
            if (method === 8) return zlib.inflateRawSync(raw).toString('utf8');
            throw new Error(`Unsupported zip compression method ${method} for ${name}`);
        }
        off += 46 + nameLen + extraLen + commentLen;
    }
    throw new Error(`No entry matching ${namePattern} found in zip`);
}

// ── CSV parsing (BEA regional CSVs: quoted GeoFIPS, year columns) ─────────

function parseCsvLine(line) {
    const fields = [];
    let cur = '', inQuotes = false;
    for (let i = 0; i < line.length; i++) {
        const ch = line[i];
        if (inQuotes) {
            if (ch === '"') inQuotes = false;
            else cur += ch;
        } else if (ch === '"') {
            inQuotes = true;
        } else if (ch === ',') {
            fields.push(cur.trim());
            cur = '';
        } else {
            cur += ch;
        }
    }
    fields.push(cur.trim());
    return fields;
}

/**
 * Parse a BEA RPP CSV, keeping LineCode 1 ("RPPs: All items") rows.
 * Returns { rows: {geoFips: {name, rpp}}, vintage } using the latest year
 * column that holds a numeric value for each row.
 */
function parseRppCsv(text) {
    const lines = text.split('\n').filter(l => l.trim());
    const header = parseCsvLine(lines[0]);
    const yearCols = header
        .map((h, i) => ({ year: parseInt(h, 10), i }))
        .filter(c => c.year >= 2000 && c.year <= 2100);
    if (!yearCols.length) throw new Error('No year columns in BEA CSV header');

    const iFips = header.indexOf('GeoFIPS');
    const iName = header.indexOf('GeoName');
    const iLine = header.indexOf('LineCode');
    if (iFips < 0 || iName < 0 || iLine < 0) throw new Error('Unexpected BEA CSV header');

    const rows = {};
    let vintage = 0;
    for (const line of lines.slice(1)) {
        const f = parseCsvLine(line);
        if (f[iLine] !== '1') continue;  // All-items RPP only
        for (let c = yearCols.length - 1; c >= 0; c--) {
            const val = parseFloat(f[yearCols[c].i]);
            if (Number.isFinite(val)) {
                rows[f[iFips]] = { name: f[iName], rpp: Math.round(val * 10) / 10 };
                vintage = Math.max(vintage, yearCols[c].year);
                break;
            }
        }
    }
    return { rows, vintage };
}

// ── Snapshot assembly ─────────────────────────────────────────────────────

function buildSnapshot(msaCsvText, stateCsvText, now = new Date()) {
    const msa = parseRppCsv(msaCsvText);
    const state = parseRppCsv(stateCsvText);

    const msas = {};
    let nonmetroUS = null;
    for (const [fips, row] of Object.entries(msa.rows)) {
        if (fips === '00000') continue;                    // US anchor (=100)
        if (fips === '00999') { nonmetroUS = row.rpp; continue; }
        // Strip BEA footnote markers like " *" from names
        msas[fips] = { name: row.name.replace(/\s*\*$/, ''), rpp: row.rpp };
    }

    const states = {};
    for (const [fips, row] of Object.entries(state.rows)) {
        if (fips === '00000') continue;
        const abbr = STATE_ABBR[row.name.trim()];
        if (abbr) states[abbr] = row.rpp;
    }

    const cities = {};
    for (const [city, cbsa] of Object.entries(CITY_CBSA)) {
        if (msas[cbsa]) cities[city] = Math.round(msas[cbsa].rpp);
    }

    const vintage = Math.max(msa.vintage, state.vintage);
    return {
        _meta: {
            fetchedAt: now.toISOString(),
            source: 'BEA Regional Price Parities (MARPP/SARPP bulk files)',
            vintage
        },
        vintage,
        msas,
        states,
        nonmetroUS,
        cities
    };
}

/**
 * Dead-data guards: return a list of problems (empty = valid).
 * `existing` is the current snapshot (may be the legacy 22-city shape).
 */
function validateSnapshot(next, existing) {
    const problems = [];
    const nMsas = Object.keys(next.msas || {}).length;
    const nStates = Object.keys(next.states || {}).length;

    if (nMsas < 300) problems.push(`only ${nMsas} MSAs (expected ≥300)`);
    if (nStates < 51) problems.push(`only ${nStates} states (expected 50+DC)`);
    if (!next.nonmetroUS) problems.push('missing US nonmetro RPP');
    if (Object.keys(next.cities || {}).length < 20) {
        problems.push(`legacy city block has ${Object.keys(next.cities || {}).length} cities (expected ≥20)`);
    }

    const allValues = [
        ...Object.values(next.msas || {}).map(m => m.rpp),
        ...Object.values(next.states || {})
    ];
    const outOfRange = allValues.filter(v => !(v >= 60 && v <= 160));
    if (outOfRange.length) problems.push(`${outOfRange.length} RPP values outside [60, 160]`);

    if (existing && typeof existing === 'object') {
        const prevVintage = existing._meta?.vintage ?? existing.vintage;
        if (prevVintage && next.vintage < prevVintage) {
            problems.push(`vintage regression: ${next.vintage} < existing ${prevVintage}`);
        }
        const prevMsas = existing.msas || {};
        const nPrev = Object.keys(prevMsas).length;
        if (nPrev > 0) {
            if (nMsas < nPrev * 0.9) {
                problems.push(`MSA coverage shrank ${nPrev} → ${nMsas} (>10%)`);
            }
            const deltas = Object.keys(prevMsas)
                .filter(g => next.msas[g])
                .map(g => Math.abs(next.msas[g].rpp - prevMsas[g].rpp))
                .sort((a, b) => a - b);
            if (deltas.length) {
                const median = deltas[Math.floor(deltas.length / 2)];
                // RPPs are stable year-over-year; a big median shift means bad data
                if (median > 5) problems.push(`median RPP change ${median.toFixed(1)} > 5 vs existing snapshot`);
            }
        }
    }
    return problems;
}

// ── Main ──────────────────────────────────────────────────────────────────

async function download(url) {
    const resp = await fetch(url, { signal: AbortSignal.timeout(120000) });
    if (!resp.ok) throw new Error(`HTTP ${resp.status} for ${url}`);
    return Buffer.from(await resp.arrayBuffer());
}

async function fetchCostOfLiving() {
    console.log('Fetching BEA Regional Price Parities (no key required)...');
    const [msaZip, stateZip] = await Promise.all([download(BEA_MSA_ZIP), download(BEA_STATE_ZIP)]);

    // Match by prefix — the year range in the filename advances each release.
    const msaCsv = unzipEntry(msaZip, /^MARPP_MSA_.*\.csv$/);
    const stateCsv = unzipEntry(stateZip, /^SARPP_STATE_.*\.csv$/);

    const existing = readSnapshot();
    const snapshot = buildSnapshot(msaCsv, stateCsv);
    const problems = validateSnapshot(snapshot, existing);

    if (problems.length) {
        // Keep the committed snapshot — never overwrite with suspect data.
        console.error('Refusing to update cost-of-living.json:');
        problems.forEach(p => console.error(`  - ${p}`));
        updateMetadata('cost-of-living', 'BEA RPP (rejected by validation)', 'error');
        process.exit(1);
    }

    const { _meta, ...payload } = snapshot;
    writeDataFile('cost-of-living.json', { _meta, ...payload }, _meta.source);
    updateMetadata('cost-of-living', 'BEA RPP bulk files');
    console.log(
        `Updated cost-of-living.json: ${Object.keys(snapshot.msas).length} MSAs, ` +
        `${Object.keys(snapshot.states).length} states, vintage ${snapshot.vintage}.`
    );
}

if (require.main === module) {
    fetchCostOfLiving().catch(err => {
        reportError('BEA RPP', err);
        updateMetadata('cost-of-living', 'BEA RPP', 'error');
        process.exit(1);
    });
}

module.exports = { parseRppCsv, buildSnapshot, validateSnapshot, unzipEntry, CITY_CBSA };
