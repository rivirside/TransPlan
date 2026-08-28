/**
 * Every file in data/ is either validated or explicitly exempt.
 *
 * The #444/#445 sweep found nine of data/'s 38 JSON files were never
 * mentioned in validate-data.js at all — including srtr-observed-rates.json,
 * the ground truth every calibration gate measures against, read by fifteen
 * modules.
 *
 * Fixing those nine is not the durable part. The durable part is that a NEW
 * data file cannot land without someone deciding which side of this line it
 * falls on. The exemption list below is the "decided not to" half, and it
 * carries reasons rather than just names, because an unexplained exemption
 * list becomes a place to hide things.
 */
const fs = require('fs');
const path = require('path');

const REPO = path.join(__dirname, '..');
const DATA = path.join(REPO, 'data');
const VALIDATOR = fs.readFileSync(path.join(REPO, 'scripts/validate-data.js'), 'utf8');

// Analysis OUTPUTS. A floor on a results file fails honest work: a sweep that
// legitimately explores a smaller grid would trip it, and the floor would get
// lowered until it meant nothing. Floor what the model reads, not what it
// writes.
const EXEMPT = {
    'horizon-alpha-fit.json': 'analysis output of run-horizon-extension.py',
    'horizon-extension-sweep.json': 'analysis output of run-horizon-extension.py',
};

describe('validate-data.js covers data/', () => {
    const files = fs.readdirSync(DATA).filter(f => f.endsWith('.json'));

    test('data/ is non-empty (the sweep below is not vacuous)', () => {
        expect(files.length).toBeGreaterThanOrEqual(30);
    });

    test.each(files)('%s is validated or exempt', (file) => {
        if (EXEMPT[file]) return;
        expect(VALIDATOR).toContain(file);
    });

    test('every exemption names a file that still exists', () => {
        // Otherwise the list silently accumulates dead entries and stops
        // being a record of decisions.
        for (const file of Object.keys(EXEMPT)) {
            expect(files).toContain(file);
        }
    });

    test('exemptions stay rare', () => {
        // Not a style rule: this is the pressure valve that would let the
        // whole check be neutralised one convenient addition at a time.
        expect(Object.keys(EXEMPT).length).toBeLessThanOrEqual(4);
    });
});
