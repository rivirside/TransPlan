/**
 * Every row-level provenance tag must have a front-end label.
 *
 * `results-table.js` builds the per-row dagger from `DQ_LABELS`, and skips any
 * tag it has no label for:
 *
 *     if (!DQ_LABELS[tag]) return;
 *
 * That is a safe fallback in the sense that nothing renders as "undefined" —
 * and a dangerous one in the sense that a tag the backend emits, describing a
 * substitution a patient is looking at, simply does not appear. The disclosure
 * is dropped silently at the last step.
 *
 * Found 2026-08-28 adding `no_post_transplant_outcomes` (#447): the backend
 * tagged all 91 affected center-organ pairs correctly, and the table would
 * have shown nothing, because the label map was a separate list nobody had to
 * update. Backend tests would have stayed green.
 */
const fs = require('fs');
const path = require('path');

const REPO = path.join(__dirname, '..');
const PROVENANCE = fs.readFileSync(
    path.join(REPO, 'backend/services/provenance.py'), 'utf8');
const TABLE = fs.readFileSync(
    path.join(REPO, 'simulator/results-table.js'), 'utf8');

/** Tag constants and their string values, read from the Python source. */
function backendTags() {
    const out = {};
    const re = /^TAG_([A-Z_]+)\s*=\s*"([a-z_]+)"/gm;
    let m;
    while ((m = re.exec(PROVENANCE)) !== null) out[`TAG_${m[1]}`] = m[2];
    return out;
}

/** The organ-level tags, which rows deliberately skip. */
function organLevelTags(tags) {
    const m = PROVENANCE.match(/ORGAN_LEVEL_TAGS\s*=\s*\(([^)]*)\)/);
    if (!m) return [];
    return m[1].split(',')
        .map(s => s.trim())
        .filter(Boolean)
        .map(name => tags[name])
        .filter(Boolean);
}

function labelledTags() {
    const block = TABLE.slice(TABLE.indexOf('var DQ_LABELS = {'));
    return new Set(
        [...block.slice(0, block.indexOf('};')).matchAll(/^\s*([a-z_]+):/gm)]
            .map(m => m[1])
    );
}

describe('DQ_LABELS covers every row-level tag', () => {
    const tags = backendTags();
    const organLevel = new Set(organLevelTags(tags));
    const rowLevel = Object.values(tags).filter(t => !organLevel.has(t));
    const labelled = labelledTags();

    test('the parsers found something (not vacuous)', () => {
        expect(Object.keys(tags).length).toBeGreaterThanOrEqual(6);
        expect(rowLevel.length).toBeGreaterThanOrEqual(5);
        expect(labelled.size).toBeGreaterThanOrEqual(5);
    });

    test.each(rowLevel)('%s has a front-end label', (tag) => {
        expect(labelled.has(tag)).toBe(true);
    });

    test('organ-level tags are NOT labelled', () => {
        // They have their own dedicated notes. A dagger on every row of an
        // organ says nothing about which row differs (#227/#228).
        for (const tag of organLevel) {
            expect(labelled.has(tag)).toBe(false);
        }
    });

    test('no label exists for a tag the backend does not emit', () => {
        const known = new Set(Object.values(tags));
        for (const tag of labelled) {
            expect(known.has(tag)).toBe(true);
        }
    });
});
