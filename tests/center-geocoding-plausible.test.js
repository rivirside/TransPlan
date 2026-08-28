/**
 * Every center sits at real coordinates, in the state it claims.
 *
 * `scoring.py` resolves a center's position with `center.get("lat", 0)`. A
 * geocoding failure therefore does not raise — it places the hospital at
 * (0, 0) in the Gulf of Guinea and scores every distance and spatial layer
 * from there. All 248 currently geocode fine, so this guards a latent hazard
 * rather than a live bug.
 *
 * It is a plausible hazard, not a theoretical one: `srtr-all-centers.json` is
 * written by THREE scripts (extract-center-list, geocode-centers,
 * verify-geocoding), 133 of its 248 entries are plain unverified `nominatim`,
 * and until #445 the file had no floor at all. The entry-count floor added
 * there counts centers; it cannot see one that moved.
 *
 * State boxes are DERIVED from health-demographics-counties.json (3144
 * counties carrying lat/lon and state) rather than hand-written — no invented
 * constants, and the reference comes from a different pipeline than center
 * geocoding, so the two cannot fail together in the same way.
 */
const fs = require('fs');
const path = require('path');

const REPO = path.join(__dirname, '..');
const read = (p) => JSON.parse(fs.readFileSync(path.join(REPO, p), 'utf8'));

const CENTERS = read('data/srtr-all-centers.json').centers;
const COUNTIES = read('data/health-demographics-counties.json').counties;
const VALIDATOR = fs.readFileSync(
    path.join(REPO, 'scripts/validate-data.js'), 'utf8');

const MARGIN = 0.5;   // county centroids are not borders; ~55km of slack

function stateBoxes() {
    const boxes = {};
    for (const c of Object.values(COUNTIES)) {
        if (!c || !c.state || typeof c.lat !== 'number' || typeof c.lon !== 'number') continue;
        const b = boxes[c.state] || (boxes[c.state] = [90, -90, 180, -180]);
        b[0] = Math.min(b[0], c.lat); b[1] = Math.max(b[1], c.lat);
        b[2] = Math.min(b[2], c.lon); b[3] = Math.max(b[3], c.lon);
    }
    return boxes;
}

function offenders(centers, boxes) {
    const out = [];
    for (const [code, c] of Object.entries(centers)) {
        if (typeof c.lat !== 'number' || typeof c.lon !== 'number' || !c.lat || !c.lon) {
            out.push([code, 'no usable coordinates']); continue;
        }
        if (c.lat < 17 || c.lat > 72 || c.lon < -180 || c.lon > -64) {
            out.push([code, 'outside US bounds']); continue;
        }
        const b = boxes[c.state_abbr];
        if (!b) continue;      // Puerto Rico: no county rows to compare against
        if (c.lat < b[0] - MARGIN || c.lat > b[1] + MARGIN ||
            c.lon < b[2] - MARGIN || c.lon > b[3] + MARGIN) {
            out.push([code, `claims ${c.state_abbr} but falls outside it`]);
        }
    }
    return out;
}

describe('center coordinates are plausible', () => {
    const boxes = stateBoxes();

    test('the reference is usable (not a vacuous check)', () => {
        // If the county file shrank, every box would widen or vanish and the
        // comparison below would wave everything through.
        expect(Object.keys(boxes).length).toBeGreaterThanOrEqual(45);
        expect(Object.keys(CENTERS).length).toBeGreaterThanOrEqual(200);
    });

    test('no center has missing, zero, or out-of-range coordinates', () => {
        const bad = offenders(CENTERS, boxes)
            .filter(([, why]) => why !== 'claims');
        expect(bad).toEqual([]);
    });

    test('every center sits inside the state it claims', () => {
        expect(offenders(CENTERS, boxes)).toEqual([]);
    });

    test('the check catches a geocoding failure', () => {
        // Verified against three real failure modes rather than asserting the
        // clean result alone — a checker that reports zero is only reassuring
        // if zero is a finding.
        const zeroed = { ...CENTERS, PROBE: { ...Object.values(CENTERS)[0], lat: 0, lon: 0 } };
        expect(offenders(zeroed, boxes).length).toBeGreaterThan(0);

        const tx = Object.entries(CENTERS).find(([, c]) => c.state_abbr === 'TX');
        const moved = { ...CENTERS, [tx[0]]: { ...tx[1], lat: 44.8, lon: -68.8 } };
        expect(offenders(moved, boxes).map(o => o[0])).toContain(tx[0]);

        const [k, first] = Object.entries(CENTERS)[5];
        const flipped = { ...CENTERS, [k]: { ...first, lon: -first.lon } };
        expect(offenders(flipped, boxes).map(o => o[0])).toContain(k);
    });

    test('validate-data.js performs this check too', () => {
        // The Jest sweep and the CI data gate must not drift apart: this file
        // catches a bad commit, validate-data.js catches a bad data refresh.
        expect(VALIDATOR).toContain('has no usable');
        expect(VALIDATOR).toContain('falls outside that state');
        expect(VALIDATOR).toContain('health-demographics-counties.json');
    });
});
