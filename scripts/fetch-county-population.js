#!/usr/bin/env node
/**
 * fetch-county-population.js — county population from the Census Bureau (#336).
 *
 * The repository had NO population data at any geography. That is a hard
 * blocker for three separate pieces of work, all of which need a denominator:
 *
 *   #336  county-level trauma rates (currently state-level per-capita only)
 *   #113  "% of US population within N hours of a transplant center"
 *   #267  2SFCA accessibility, whose demand side is population
 *
 * Source: the Census Bureau's county population estimates CSV. The ACS API
 * would need an API key; this static file does not, which keeps the pipeline
 * runnable in CI without a secret.
 *
 * Follows the house pattern from fetch-climate-centers.py: a raw cache, a
 * derived product with full `_meta`, a never-shrink guard, and a plausibility
 * gate (the 2026-08-05 incident rule — a fetch that returns near-empty must
 * FAIL rather than overwrite good data with a shell).
 */
const fs = require('fs');
const path = require('path');
const https = require('https');

const REPO = path.join(__dirname, '..');
const RAW_DIR = path.join(REPO, 'data', 'census-raw');
const RAW_FILE = path.join(RAW_DIR, 'co-est-alldata.csv');
const OUT_FILE = path.join(REPO, 'data', 'county-population.json');
const COUNTY_FILE = path.join(REPO, 'data', 'health-demographics-counties.json');

const SOURCE_URL =
  'https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/counties/totals/co-est2024-alldata.csv';
const POP_COLUMN = 'POPESTIMATE2024';

// Never-shrink floor. There are 3,144 county-equivalents; anything far below
// this means a truncated download or a changed layout, not a real change.
const MIN_COUNTIES = 3000;
// A county population outside this band is a parse error, not a small county.
const MIN_POP = 1;
const MAX_POP = 15000000;   // Los Angeles County is ~9.6M

function download(url) {
  return new Promise((resolve, reject) => {
    https.get(url, (res) => {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        res.resume();
        return resolve(download(res.headers.location));
      }
      if (res.statusCode !== 200) {
        res.resume();
        return reject(new Error(`HTTP ${res.statusCode} for ${url}`));
      }
      let body = '';
      res.setEncoding('latin1');   // Census CSVs are not UTF-8 (e.g. Doña Ana)
      res.on('data', (chunk) => { body += chunk; });
      res.on('end', () => resolve(body));
    }).on('error', reject);
  });
}

/** Minimal CSV row splitter that respects double-quoted fields. */
function splitRow(line) {
  const out = [];
  let cur = '';
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') {
      if (inQuotes && line[i + 1] === '"') { cur += '"'; i++; }
      else inQuotes = !inQuotes;
    } else if (ch === ',' && !inQuotes) {
      out.push(cur); cur = '';
    } else {
      cur += ch;
    }
  }
  out.push(cur);
  return out;
}

function parse(csv) {
  const lines = csv.split(/\r?\n/).filter((l) => l.trim().length);
  if (!lines.length) throw new Error('empty CSV');
  const header = splitRow(lines[0]);
  const idx = {};
  ['SUMLEV', 'STATE', 'COUNTY', 'STNAME', 'CTYNAME', POP_COLUMN].forEach((name) => {
    const i = header.indexOf(name);
    if (i === -1) throw new Error(`column ${name} missing — Census layout changed?`);
    idx[name] = i;
  });

  const counties = {};
  let skipped = 0;
  for (let i = 1; i < lines.length; i++) {
    const row = splitRow(lines[i]);
    // SUMLEV 040 rows are state totals; 050 rows are the counties we want.
    if (row[idx.SUMLEV] !== '050') continue;
    const fips = row[idx.STATE] + row[idx.COUNTY];
    const pop = parseInt(row[idx[POP_COLUMN]], 10);
    if (!Number.isFinite(pop) || pop < MIN_POP || pop > MAX_POP) {
      skipped++;
      continue;
    }
    counties[fips] = {
      name: row[idx.CTYNAME],
      state: row[idx.STNAME],
      population: pop,
    };
  }
  return { counties, skipped };
}

function loadExisting() {
  if (!fs.existsSync(OUT_FILE)) return null;
  try {
    return JSON.parse(fs.readFileSync(OUT_FILE, 'utf8'));
  } catch {
    return null;
  }
}

async function main() {
  console.log(`Fetching ${SOURCE_URL} …`);
  const csv = await download(SOURCE_URL);

  fs.mkdirSync(RAW_DIR, { recursive: true });
  fs.writeFileSync(RAW_FILE, csv, 'latin1');
  console.log(`raw cache: ${path.relative(REPO, RAW_FILE)} (${csv.length} bytes)`);

  const { counties, skipped } = parse(csv);
  const n = Object.keys(counties).length;
  console.log(`parsed ${n} counties (${skipped} rows skipped as implausible)`);

  // Quality gate — refuse to write a shell over good data.
  if (n < MIN_COUNTIES) {
    console.error(`ERROR: only ${n} counties (floor ${MIN_COUNTIES}). Refusing to write.`);
    process.exit(1);
  }
  const existing = loadExisting();
  const prevN = existing ? Object.keys(existing.counties || {}).length : 0;
  if (prevN && n < prevN * 0.95) {
    console.error(`ERROR: ${n} counties vs ${prevN} previously — never-shrink guard. ` +
                  `Refusing to write.`);
    process.exit(1);
  }

  // Report join coverage against the centroid file the spatial work uses; a
  // silent mismatch here would quietly drop counties from any per-capita rate.
  let joinNote = null;
  if (fs.existsSync(COUNTY_FILE)) {
    try {
      const centroids = JSON.parse(fs.readFileSync(COUNTY_FILE, 'utf8')).counties || {};
      const centroidFips = Object.keys(centroids);
      const matched = centroidFips.filter((f) => counties[f]).length;
      joinNote = `${matched}/${centroidFips.length} counties in ` +
                 `health-demographics-counties.json have a population`;
      console.log(joinNote);
      if (centroidFips.length && matched < centroidFips.length * 0.95) {
        console.error(`ERROR: only ${matched} of ${centroidFips.length} centroid ` +
                      `counties matched — FIPS format mismatch?`);
        process.exit(1);
      }
    } catch (e) {
      console.warn(`could not check join coverage: ${e.message}`);
    }
  }

  const total = Object.values(counties).reduce((a, c) => a + c.population, 0);
  const output = {
    _meta: {
      source: 'US Census Bureau, County Population Totals',
      url: SOURCE_URL,
      column: POP_COLUMN,
      script: 'scripts/fetch-county-population.js',
      fetchedAt: new Date().toISOString().replace(/\.\d+Z$/, 'Z'),
      method: 'Vintage 2024 county population estimates, keyed by 5-digit FIPS ' +
              '(STATE + COUNTY), matching data/health-demographics-counties.json.',
      notes: joinNote,
      national_total: total,
      county_count: n,
    },
    counties,
  };
  fs.writeFileSync(OUT_FILE, JSON.stringify(output, null, 1) + '\n');
  console.log(`wrote ${path.relative(REPO, OUT_FILE)} — ${n} counties, ` +
              `national total ${total.toLocaleString()}`);
}

main().catch((e) => {
  console.error(`FAILED: ${e.message}`);
  process.exit(1);
});
