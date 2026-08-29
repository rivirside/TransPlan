/**
 * CLAUDE.md's architecture map must describe the repo that exists.
 *
 * That map is loaded into every session's context, so a wrong entry does not
 * just mislead a reader — it sends work to a path that isn't there. Checked
 * 2026-08-29:
 *
 *   api-client.js       listed under shared/   actually at the repo root
 *   export-handler.js   listed under shared/   actually at the repo root
 *   weight-config.js    listed under shared/   actually at the repo root
 *   data-loader.js      listed under shared/   does not exist anywhere
 *   seed-control.js     in shared/             not listed
 *
 * The `data-loader.js` entry is the one that matters most: it claims a
 * "Runtime JSON loader" module that nothing provides. Each consumer
 * (explorer/data-layers.js, model-card.js, weight-config.js) does its own
 * fetching, so a session told to use the shared loader would either hunt for
 * it or build a second one.
 *
 * This is the same class as the false data-source credits in #459 — a precise,
 * checkable claim that nothing checked — but on the document that shapes every
 * future session rather than a page users read.
 *
 * The test verifies paths resolve. It deliberately does NOT require the map to
 * list every file: a map is a summary, and demanding completeness would make
 * it churn on every new module. It only requires that what IS named exists.
 */
const fs = require('fs');
const path = require('path');

const REPO = path.join(__dirname, '..');
const CLAUDE = fs.readFileSync(path.join(REPO, 'CLAUDE.md'), 'utf8');

/** Pull (directory, filename) pairs out of the fenced architecture block. */
function mappedPaths() {
    const start = CLAUDE.indexOf('```\nbackend/');
    if (start < 0) return [];
    const block = CLAUDE.slice(start + 4, CLAUDE.indexOf('```', start + 4));

    const out = [];
    let dir = null;
    for (const line of block.split('\n')) {
        // "shared/    Cross-page utilities" OR a bare "components/" with no
        // description — the map uses both, and requiring a description made
        // components/site-chrome.js look like it lived under shared/.
        const asDir = line.match(/^([\w.-]+)\/(?:\s|$)/);
        if (asDir) { dir = asDir[1]; continue; }
        // "  routers/    ..."  — a nested directory, not a file
        if (/^\s{2,}[\w.-]+\/\s/.test(line)) continue;
        // "  index.js    Entry point"  — a file inside the current directory
        const asFile = line.match(/^\s{2,}([\w.-]+\.(?:js|py))\s/);
        if (asFile && dir) out.push(`${dir}/${asFile[1]}`);
        // "centers-page.js   ..."  — a root-level file, and also the
        // "shared/api-client.js  ..." form. An earlier version matched only
        // bare filenames, so a path written WITH a directory at the start of
        // a line was skipped entirely and never checked -- which let a
        // negative test putting api-client.js back under shared/ pass.
        const atRoot = line.match(/^([\w.-]+(?:\/[\w.-]+)*\.(?:js|py))\s/);
        if (atRoot) out.push(atRoot[1]);
    }
    return out;
}

describe("CLAUDE.md's architecture map", () => {
    const paths = mappedPaths();

    test('the map parses (not a vacuous check)', () => {
        expect(paths.length).toBeGreaterThanOrEqual(12);
        expect(paths).toContain('backend/main.py');
    });

    test.each(mappedPaths())('%s exists', (p) => {
        expect(fs.existsSync(path.join(REPO, p))).toBe(true);
    });

    test('no entry claims a module nothing provides', () => {
        // data-loader.js was listed as the "Runtime JSON loader" and did not
        // exist; each consumer fetches for itself. Guard the specific shape:
        // a listed .js under shared/ must actually be in shared/.
        const sharedEntries = paths.filter(p => p.startsWith('shared/'));
        for (const p of sharedEntries) {
            expect(fs.existsSync(path.join(REPO, p))).toBe(true);
        }
    });
});
