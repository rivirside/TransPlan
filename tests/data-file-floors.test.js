/**
 * Every per-center data file must have a never-shrink floor.
 *
 * The #444 sweep found seven data files whose only protection was that nobody
 * had run the wrong script yet. Fixing the seven is not the durable part —
 * the durable part is that the NEXT per-center file added to data/ cannot
 * arrive unfloored without this failing.
 *
 * The rule below is deliberately shaped around what the sweep actually found:
 * files keyed by SRTR center code. Those are the ones the model runs on, and
 * a partial one degrades quietly (a center missing from the map is a center
 * scored on national averages, per L-087) rather than crashing.
 */
const fs = require('fs');
const path = require('path');

const REPO = path.join(__dirname, '..');
const DATA = path.join(REPO, 'data');
const VALIDATOR = fs.readFileSync(path.join(REPO, 'scripts/validate-data.js'), 'utf8');

/** A container is "per-center" if its keys look like SRTR center codes. */
function perCenterContainers(obj) {
    const found = [];
    for (const [key, val] of Object.entries(obj || {})) {
        if (key.startsWith('_') || typeof val !== 'object' || val === null) continue;
        const keys = Object.keys(val);
        if (keys.length < 50) continue;
        const codeLike = keys.filter(k => /^[A-Z]{2}[A-Z0-9]{2}$/.test(k)).length;
        if (codeLike / keys.length > 0.9) found.push([key, keys.length]);
    }
    return found;
}

describe('per-center data files have never-shrink floors', () => {
    const files = fs.readdirSync(DATA).filter(f => f.endsWith('.json'));
    const perCenter = [];

    for (const f of files) {
        let parsed;
        try {
            parsed = JSON.parse(fs.readFileSync(path.join(DATA, f), 'utf8'));
        } catch {
            continue;
        }
        for (const [container, n] of perCenterContainers(parsed)) {
            perCenter.push({ file: f, container, n });
        }
    }

    test('the sweep still finds per-center files (the detector works)', () => {
        // If this drops to zero the loop below passes vacuously — the exact
        // "guard that cannot fail" shape this suite exists to prevent.
        expect(perCenter.length).toBeGreaterThanOrEqual(8);
    });

    test.each(perCenter.map(p => [p.file, p.container, p.n]))(
        '%s (%s, %i centers) is floored in validate-data.js',
        (file, container) => {
            expect(VALIDATOR).toContain(file);
            // The floor must name this container, not merely the file: several
            // of these hold more than one block, and flooring the wrong one
            // reads as coverage while protecting nothing.
            const idx = VALIDATOR.indexOf(`'${file}'`);
            const near = VALIDATOR.slice(Math.max(0, idx - 800), idx + 800);
            expect(
                near.includes(container) ||
                VALIDATOR.includes(`['${file}', '${container}'`)
            ).toBe(true);
        }
    );
});
