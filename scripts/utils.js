/**
 * Shared utilities for data fetch scripts.
 *
 * - Retry with exponential backoff
 * - Rate-limit-aware delays
 * - Structured error reporting
 * - JSON file writing with _meta
 */

const fs = require('fs');
const path = require('path');

const DATA_DIR = path.join(__dirname, '..', 'data');

/**
 * Fetch with retry and exponential backoff.
 * @param {string} url - URL to fetch
 * @param {object} options - fetch options
 * @param {number} maxRetries - max retry attempts
 * @returns {Promise<Response>}
 */
async function fetchWithRetry(url, options = {}, maxRetries = 3) {
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
        try {
            const response = await fetch(url, {
                ...options,
                signal: AbortSignal.timeout(30000)
            });

            if (response.status === 429) {
                const retryAfter = parseInt(response.headers.get('retry-after') || '60', 10);
                console.warn(`Rate limited. Waiting ${retryAfter}s before retry...`);
                await delay(retryAfter * 1000);
                continue;
            }

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return response;
        } catch (err) {
            if (attempt === maxRetries) {
                throw err;
            }
            const waitMs = Math.min(1000 * Math.pow(2, attempt), 30000);
            console.warn(`Attempt ${attempt + 1} failed: ${err.message}. Retrying in ${waitMs}ms...`);
            await delay(waitMs);
        }
    }
}

/**
 * Delay for a given number of milliseconds.
 */
function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Write JSON data to a file in the data/ directory with _meta.
 * @param {string} filename - File name (relative to data/)
 * @param {object} data - Data to write
 * @param {string} source - Source description for _meta
 */
function writeDataFile(filename, data, source) {
    const filePath = path.join(DATA_DIR, filename);
    const dir = path.dirname(filePath);

    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
    }

    const output = {
        _meta: {
            fetchedAt: new Date().toISOString(),
            source: source
        },
        ...data
    };

    fs.writeFileSync(filePath, JSON.stringify(output, null, 2) + '\n');
    console.log(`Wrote ${filePath}`);
}

/**
 * Deep merge two objects. For nested objects (like per-city health data),
 * merges inner keys rather than replacing the whole object.
 */
function deepMerge(target, source) {
    const result = { ...target };
    for (const [key, value] of Object.entries(source)) {
        if (
            value && typeof value === 'object' && !Array.isArray(value) &&
            result[key] && typeof result[key] === 'object' && !Array.isArray(result[key])
        ) {
            result[key] = deepMerge(result[key], value);
        } else {
            result[key] = value;
        }
    }
    return result;
}

/**
 * Merge new data into an existing JSON file, preserving keys not in newData.
 * Use this instead of writeDataFile when a fetch script only updates a subset
 * of keys in a multi-key file (e.g., hospital-quality.json has centerReputation,
 * centerVolumes, specializations, insuranceAcceptanceRates — fetching only
 * updates centerReputation while preserving the rest).
 *
 * @param {string} filename - File name (relative to data/)
 * @param {object} newData - New data to merge in
 * @param {string} source - Source description for _meta
 */
function mergeDataFile(filename, newData, source) {
    const filePath = path.join(DATA_DIR, filename);
    let existing = {};

    try {
        const raw = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
        delete raw._meta; // Strip old meta; writeDataFile adds fresh one
        existing = raw;
    } catch (e) {
        // File doesn't exist or is invalid JSON — start fresh
        console.log(`No existing ${filename} to merge into; creating new.`);
    }

    const merged = deepMerge(existing, newData);
    writeDataFile(filename, merged, source);
}

/**
 * Update metadata.json with the latest fetch timestamp for a source.
 * @param {string} sourceKey - Key in metadata.sources
 * @param {string} source - Source description
 * @param {string} status - Status (e.g., 'fetched', 'error')
 */
function updateMetadata(sourceKey, source, status = 'fetched') {
    const metaPath = path.join(DATA_DIR, 'metadata.json');
    let metadata = {};

    try {
        metadata = JSON.parse(fs.readFileSync(metaPath, 'utf-8'));
    } catch {
        metadata = { lastFullFetch: null, sources: {}, srtrReportHash: null };
    }

    if (!metadata.sources) metadata.sources = {};

    metadata.sources[sourceKey] = {
        fetchedAt: new Date().toISOString(),
        status,
        source
    };

    metadata.lastFullFetch = new Date().toISOString();

    fs.writeFileSync(metaPath, JSON.stringify(metadata, null, 2) + '\n');
}

/**
 * Report an error in a structured format for GitHub Actions.
 * @param {string} source - Source name
 * @param {Error} error - Error object
 */
function reportError(source, error) {
    console.error(`[ERROR] ${source}: ${error.message}`);
    if (process.env.GITHUB_ACTIONS) {
        console.error(`::error title=Fetch Failed: ${source}::${error.message}`);
    }
}

/**
 * The 22 TransPlan cities with their states and FIPS codes.
 */
const CITIES = [
    { city: 'Pittsburgh', state: 'Pennsylvania', stateAbbr: 'PA', stateFips: '42' },
    { city: 'Baltimore', state: 'Maryland', stateAbbr: 'MD', stateFips: '24' },
    { city: 'Philadelphia', state: 'Pennsylvania', stateAbbr: 'PA', stateFips: '42' },
    { city: 'New York', state: 'New York', stateAbbr: 'NY', stateFips: '36' },
    { city: 'Minneapolis', state: 'Minnesota', stateAbbr: 'MN', stateFips: '27' },
    { city: 'Madison', state: 'Wisconsin', stateAbbr: 'WI', stateFips: '55' },
    { city: 'Chicago', state: 'Illinois', stateAbbr: 'IL', stateFips: '17' },
    { city: 'Cleveland', state: 'Ohio', stateAbbr: 'OH', stateFips: '39' },
    { city: 'St. Louis', state: 'Missouri', stateAbbr: 'MO', stateFips: '29' },
    { city: 'Indianapolis', state: 'Indiana', stateAbbr: 'IN', stateFips: '18' },
    { city: 'Omaha', state: 'Nebraska', stateAbbr: 'NE', stateFips: '31' },
    { city: 'Rochester', state: 'Minnesota', stateAbbr: 'MN', stateFips: '27' },
    { city: 'Nashville', state: 'Tennessee', stateAbbr: 'TN', stateFips: '47' },
    { city: 'Durham', state: 'North Carolina', stateAbbr: 'NC', stateFips: '37' },
    { city: 'Miami', state: 'Florida', stateAbbr: 'FL', stateFips: '12' },
    { city: 'Dallas', state: 'Texas', stateAbbr: 'TX', stateFips: '48' },
    { city: 'Houston', state: 'Texas', stateAbbr: 'TX', stateFips: '48' },
    { city: 'Portland', state: 'Oregon', stateAbbr: 'OR', stateFips: '41' },
    { city: 'Seattle', state: 'Washington', stateAbbr: 'WA', stateFips: '53' },
    { city: 'San Francisco', state: 'California', stateAbbr: 'CA', stateFips: '06' },
    { city: 'Los Angeles', state: 'California', stateAbbr: 'CA', stateFips: '06' },
    { city: 'Palo Alto', state: 'California', stateAbbr: 'CA', stateFips: '06' }
];

module.exports = {
    fetchWithRetry,
    delay,
    writeDataFile,
    mergeDataFile,
    updateMetadata,
    reportError,
    CITIES,
    DATA_DIR
};
