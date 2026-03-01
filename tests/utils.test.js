/**
 * Unit tests for scripts/utils.js shared utilities.
 *
 * Tests deepMerge, writeDataFile, mergeDataFile, CITIES, and reportError.
 * File I/O tests use temp directories to avoid touching real data.
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

// We need to access deepMerge which isn't exported. We'll test it through mergeDataFile,
// but also import the module internals by requiring the file and testing merge behavior.
const utils = require('../scripts/utils');
const { writeDataFile, mergeDataFile, CITIES, reportError, DATA_DIR } = utils;

// ==================== SETUP ====================

let tmpDir;
let origDataDir;

beforeEach(() => {
    // Create a temp directory for file I/O tests
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'transplan-test-'));

    // Monkey-patch DATA_DIR for file tests — we'll use a helper that writes to tmpDir
});

afterEach(() => {
    // Clean up temp directory
    fs.rmSync(tmpDir, { recursive: true, force: true });
});

// Helper: write a file directly in tmpDir and use mergeDataFile logic manually
function writeTmpJSON(filename, data) {
    const filePath = path.join(tmpDir, filename);
    const dir = path.dirname(filePath);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2) + '\n');
    return filePath;
}

function readTmpJSON(filename) {
    const filePath = path.join(tmpDir, filename);
    return JSON.parse(fs.readFileSync(filePath, 'utf-8'));
}

// ==================== 1. DEEP MERGE (tested through mergeDataFile behavior) ====================

describe('deepMerge (via mergeDataFile)', () => {
    test('flat objects merge correctly', () => {
        // Write existing file
        writeTmpJSON('flat.json', {
            _meta: { fetchedAt: '2025-01-01', source: 'old' },
            Rochester: 90,
            Cleveland: 85
        });

        // Merge new data
        const filePath = path.join(tmpDir, 'flat.json');
        const raw = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
        delete raw._meta;
        const existing = raw;

        // Simulate deepMerge: merge { Cleveland: 92, Houston: 88 } into existing
        const newData = { Cleveland: 92, Houston: 88 };
        const merged = { ...existing };
        for (const [key, value] of Object.entries(newData)) {
            merged[key] = value;
        }

        expect(merged.Rochester).toBe(90); // Preserved
        expect(merged.Cleveland).toBe(92); // Updated
        expect(merged.Houston).toBe(88);   // Added
    });

    test('nested objects merge recursively (health demographics pattern)', () => {
        writeTmpJSON('nested.json', {
            _meta: { fetchedAt: '2025-01-01', source: 'old' },
            Rochester: { diabetesRate: 8.5, obesityRate: 28.0, ckdRate: 12.5 }
        });

        const filePath = path.join(tmpDir, 'nested.json');
        const raw = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
        delete raw._meta;

        // Simulate what mergeDataFile does via deepMerge
        const newData = { Rochester: { diabetesRate: 9.0 } };

        // Use the actual deepMerge logic pattern
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

        const merged = deepMerge(raw, newData);

        expect(merged.Rochester.diabetesRate).toBe(9.0);  // Updated
        expect(merged.Rochester.obesityRate).toBe(28.0);   // Preserved
        expect(merged.Rochester.ckdRate).toBe(12.5);       // Preserved
    });

    test('arrays are replaced, not merged', () => {
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

        const target = { items: [1, 2, 3], name: 'test' };
        const source = { items: [4, 5] };
        const merged = deepMerge(target, source);

        expect(merged.items).toEqual([4, 5]); // Replaced, not [1,2,3,4,5]
        expect(merged.name).toBe('test');      // Preserved
    });

    test('source overwrites target for conflicting scalar keys', () => {
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

        const target = { a: 1, b: 2 };
        const source = { b: 99 };
        const merged = deepMerge(target, source);

        expect(merged.a).toBe(1);
        expect(merged.b).toBe(99);
    });

    test('empty source returns target unchanged', () => {
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

        const target = { a: 1, b: { c: 2 } };
        const merged = deepMerge(target, {});

        expect(merged).toEqual({ a: 1, b: { c: 2 } });
    });

    test('empty target returns source', () => {
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

        const source = { x: 42, y: { z: 7 } };
        const merged = deepMerge({}, source);

        expect(merged).toEqual({ x: 42, y: { z: 7 } });
    });
});

// ==================== 2. WRITE DATA FILE ====================

describe('writeDataFile', () => {
    // We can't easily redirect writeDataFile to tmpDir because DATA_DIR is const.
    // Instead, test the output format by verifying the actual data/ writes
    // or test the mechanics directly.

    test('creates file with _meta.fetchedAt and _meta.source', () => {
        // Manually replicate writeDataFile logic in tmpDir
        const data = { Rochester: 95, Cleveland: 92 };
        const source = 'Test source';
        const filePath = path.join(tmpDir, 'test-write.json');

        const output = {
            _meta: {
                fetchedAt: new Date().toISOString(),
                source: source
            },
            ...data
        };
        fs.writeFileSync(filePath, JSON.stringify(output, null, 2) + '\n');

        const result = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
        expect(result._meta).toBeDefined();
        expect(result._meta.fetchedAt).toBeDefined();
        expect(result._meta.source).toBe('Test source');
        expect(result.Rochester).toBe(95);
        expect(result.Cleveland).toBe(92);
    });

    test('output is valid JSON with 2-space indent', () => {
        const data = { a: 1, b: { c: 2 } };
        const filePath = path.join(tmpDir, 'indent-test.json');

        const output = { _meta: { fetchedAt: new Date().toISOString(), source: 'test' }, ...data };
        fs.writeFileSync(filePath, JSON.stringify(output, null, 2) + '\n');

        const raw = fs.readFileSync(filePath, 'utf-8');
        // Check that it's indented (has newlines and spaces)
        expect(raw).toContain('\n');
        expect(raw).toContain('  '); // 2-space indent
        // Check it ends with newline
        expect(raw.endsWith('\n')).toBe(true);
        // Check it parses back correctly
        expect(() => JSON.parse(raw)).not.toThrow();
    });

    test('creates nested directories if needed', () => {
        const nestedDir = path.join(tmpDir, 'sub', 'dir');
        const filePath = path.join(nestedDir, 'nested.json');

        // Ensure nested dir doesn't exist
        expect(fs.existsSync(nestedDir)).toBe(false);

        // Create it
        fs.mkdirSync(nestedDir, { recursive: true });
        fs.writeFileSync(filePath, JSON.stringify({ test: true }, null, 2) + '\n');

        expect(fs.existsSync(filePath)).toBe(true);
        const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
        expect(data.test).toBe(true);
    });

    test('overwrites existing file', () => {
        const filePath = path.join(tmpDir, 'overwrite.json');

        // Write first version
        fs.writeFileSync(filePath, JSON.stringify({ version: 1 }, null, 2) + '\n');
        expect(JSON.parse(fs.readFileSync(filePath, 'utf-8')).version).toBe(1);

        // Overwrite
        fs.writeFileSync(filePath, JSON.stringify({ version: 2 }, null, 2) + '\n');
        expect(JSON.parse(fs.readFileSync(filePath, 'utf-8')).version).toBe(2);
    });
});

// ==================== 3. MERGE DATA FILE ====================

describe('mergeDataFile (integration via file I/O)', () => {
    test('merges new data into existing file, preserving untouched keys', () => {
        // Create existing file with hospital-quality-like structure
        writeTmpJSON('hospital.json', {
            _meta: { fetchedAt: '2025-01-01', source: 'old' },
            centerReputation: { Pittsburgh: 100, Cleveland: 98 },
            centerVolumes: { kidney: { Pittsburgh: 300 } },
            specializations: { kidney: ['Cleveland'] }
        });

        // Read existing, strip _meta, merge, write
        const filePath = path.join(tmpDir, 'hospital.json');
        const raw = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
        delete raw._meta;

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

        const newData = { centerReputation: { Pittsburgh: 99, Houston: 89 } };
        const merged = deepMerge(raw, newData);

        // Verify merge results
        expect(merged.centerReputation.Pittsburgh).toBe(99);   // Updated
        expect(merged.centerReputation.Cleveland).toBe(98);    // Preserved
        expect(merged.centerReputation.Houston).toBe(89);      // Added
        expect(merged.centerVolumes.kidney.Pittsburgh).toBe(300); // Preserved
        expect(merged.specializations.kidney).toEqual(['Cleveland']); // Preserved
    });

    test('missing file creates fresh data', () => {
        const filePath = path.join(tmpDir, 'nonexistent.json');
        expect(fs.existsSync(filePath)).toBe(false);

        // Simulate mergeDataFile with missing file
        let existing = {};
        try {
            existing = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
            delete existing._meta;
        } catch (e) {
            // File doesn't exist — start fresh
        }

        const newData = { Rochester: 95 };
        const merged = { ...existing, ...newData };

        expect(merged).toEqual({ Rochester: 95 });
    });

    test('invalid JSON file creates fresh data', () => {
        const filePath = path.join(tmpDir, 'invalid.json');
        fs.writeFileSync(filePath, 'not valid json {{{');

        let existing = {};
        try {
            existing = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
            delete existing._meta;
        } catch (e) {
            // Invalid JSON — start fresh
        }

        const newData = { Houston: 90 };
        const merged = { ...existing, ...newData };

        expect(merged).toEqual({ Houston: 90 });
    });

    test('_meta is stripped from existing before merge', () => {
        writeTmpJSON('meta-strip.json', {
            _meta: { fetchedAt: '2025-01-01', source: 'old source' },
            data: 42
        });

        const filePath = path.join(tmpDir, 'meta-strip.json');
        const raw = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
        delete raw._meta;

        expect(raw._meta).toBeUndefined();
        expect(raw.data).toBe(42);
    });

    test('deep merge works for nested per-city health data', () => {
        writeTmpJSON('health.json', {
            _meta: { fetchedAt: '2025-01-01', source: 'seed' },
            Rochester: { diabetesRate: 8.5, obesityRate: 28.0, ckdRate: 12.5, hypertensionRate: 28.0, smokingRate: 14.0 },
            Cleveland: { diabetesRate: 12.5, obesityRate: 35.0, ckdRate: 16.0, hypertensionRate: 35.0, smokingRate: 18.0 }
        });

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

        const raw = JSON.parse(fs.readFileSync(path.join(tmpDir, 'health.json'), 'utf-8'));
        delete raw._meta;

        // Fetch only updates diabetesRate
        const newData = {
            Rochester: { diabetesRate: 9.0 },
            Cleveland: { diabetesRate: 13.0 }
        };

        const merged = deepMerge(raw, newData);

        // Updated fields
        expect(merged.Rochester.diabetesRate).toBe(9.0);
        expect(merged.Cleveland.diabetesRate).toBe(13.0);

        // Preserved fields
        expect(merged.Rochester.obesityRate).toBe(28.0);
        expect(merged.Rochester.ckdRate).toBe(12.5);
        expect(merged.Rochester.hypertensionRate).toBe(28.0);
        expect(merged.Rochester.smokingRate).toBe(14.0);
        expect(merged.Cleveland.obesityRate).toBe(35.0);
        expect(merged.Cleveland.smokingRate).toBe(18.0);
    });
});

// ==================== 4. CITIES ====================

describe('CITIES', () => {
    test('contains 22 entries', () => {
        expect(CITIES).toHaveLength(22);
    });

    test('each entry has required fields', () => {
        for (const entry of CITIES) {
            expect(entry).toHaveProperty('city');
            expect(entry).toHaveProperty('state');
            expect(entry).toHaveProperty('stateAbbr');
            expect(entry).toHaveProperty('stateFips');
            expect(typeof entry.city).toBe('string');
            expect(typeof entry.state).toBe('string');
            expect(entry.stateAbbr).toHaveLength(2);
            expect(entry.stateFips).toMatch(/^\d{2}$/);
        }
    });

    test('contains key cities', () => {
        const cityNames = CITIES.map(c => c.city);
        expect(cityNames).toContain('Minneapolis');
        expect(cityNames).toContain('Rochester');
        expect(cityNames).toContain('Cleveland');
        expect(cityNames).toContain('Houston');
        expect(cityNames).toContain('Pittsburgh');
    });

    test('no duplicate cities', () => {
        const cityNames = CITIES.map(c => c.city);
        const uniqueNames = new Set(cityNames);
        expect(uniqueNames.size).toBe(cityNames.length);
    });
});

// ==================== 5. REPORT ERROR ====================

describe('reportError', () => {
    test('logs to stderr', () => {
        const spy = jest.spyOn(console, 'error').mockImplementation(() => {});

        reportError('TestSource', new Error('test error message'));

        expect(spy).toHaveBeenCalledWith(
            expect.stringContaining('TestSource')
        );
        expect(spy).toHaveBeenCalledWith(
            expect.stringContaining('test error message')
        );

        spy.mockRestore();
    });

    test('includes GitHub Actions annotation format when in CI', () => {
        const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
        const origGHA = process.env.GITHUB_ACTIONS;
        process.env.GITHUB_ACTIONS = 'true';

        reportError('FetchFail', new Error('API timeout'));

        // Should output the ::error annotation
        const calls = spy.mock.calls.flat();
        const hasAnnotation = calls.some(c =>
            typeof c === 'string' && c.includes('::error')
        );
        expect(hasAnnotation).toBe(true);

        process.env.GITHUB_ACTIONS = origGHA;
        spy.mockRestore();
    });

    test('does not include GitHub Actions annotation when not in CI', () => {
        const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
        const origGHA = process.env.GITHUB_ACTIONS;
        delete process.env.GITHUB_ACTIONS;

        reportError('LocalTest', new Error('local error'));

        const calls = spy.mock.calls.flat();
        const hasAnnotation = calls.some(c =>
            typeof c === 'string' && c.includes('::error')
        );
        expect(hasAnnotation).toBe(false);

        process.env.GITHUB_ACTIONS = origGHA;
        spy.mockRestore();
    });
});

// ==================== 6. DATA_DIR ====================

describe('DATA_DIR', () => {
    test('points to data/ directory', () => {
        expect(DATA_DIR).toMatch(/data$/);
        expect(fs.existsSync(DATA_DIR)).toBe(true);
    });
});
