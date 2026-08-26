#!/usr/bin/env node
/**
 * Verify every docs-site link in the app resolves to a real built page (#328).
 *
 * Two separate defects shipped to production because nothing checked this:
 *
 *   1. docusaurus.config.ts had `trailingSlash: false`, so the build emitted
 *      `architecture/overview.html` while Docusaurus itself emitted links to
 *      `/architecture/overview`. Vercel serves `dir/index.html` at `/dir/` but
 *      does NOT serve `page.html` at `/page`, so EVERY in-docs link 404'd —
 *      the docs site was unnavigable, not just the links from the landing page.
 *
 *   2. index.html linked to `architecture/scoring` and `architecture/equity`,
 *      neither of which has ever existed as a page.
 *
 * Run after `cd docs-site && npm run build`. Requires the build to be present;
 * exits 0 with a notice if it is not, so local runs without a build do not
 * fail spuriously (CI always builds first).
 */
const fs = require('fs');
const path = require('path');

const REPO = path.join(__dirname, '..');
const BUILD = path.join(REPO, 'docs-site', 'build');
const PREFIX = 'docs-site/build/';

if (!fs.existsSync(BUILD)) {
    console.log('docs-site/build not present — skipping (build it first).');
    process.exit(0);
}

/** Files that may contain links into the docs site. */
function sourceFiles() {
    const out = [];
    for (const entry of fs.readdirSync(REPO)) {
        if (entry.endsWith('.html')) out.push(path.join(REPO, entry));
    }
    for (const dir of ['components', 'shared', 'simulator', 'explorer', 'validation']) {
        const d = path.join(REPO, dir);
        if (!fs.existsSync(d)) continue;
        for (const entry of fs.readdirSync(d)) {
            if (entry.endsWith('.js') || entry.endsWith('.html')) {
                out.push(path.join(d, entry));
            }
        }
    }
    return out;
}

/**
 * Does this docs route exist in the build?
 * trailingSlash:true emits `route/index.html`; accept `route.html` too so the
 * check keeps working if that setting is ever revisited.
 */
function routeExists(route) {
    const clean = route.replace(/^\/+/, '').replace(/[?#].*$/, '').replace(/\/$/, '');
    if (clean === '') return fs.existsSync(path.join(BUILD, 'index.html'));
    // A link to an actual asset (has an extension) just needs the file.
    if (/\.[a-z0-9]+$/i.test(clean)) return fs.existsSync(path.join(BUILD, clean));
    return fs.existsSync(path.join(BUILD, clean, 'index.html')) ||
           fs.existsSync(path.join(BUILD, `${clean}.html`));
}

const problems = [];
let checked = 0;

for (const file of sourceFiles()) {
    const text = fs.readFileSync(file, 'utf8');
    const re = new RegExp(`["'](?:[^"']*?)${PREFIX.replace('/', '\\/')}([^"']*)["']`, 'g');
    let m;
    while ((m = re.exec(text)) !== null) {
        checked++;
        const route = m[1];
        if (!routeExists(route)) {
            problems.push(`${path.relative(REPO, file)} -> ${PREFIX}${route}`);
        }
    }
}

if (problems.length) {
    console.error(`\nBroken docs-site links (${problems.length} of ${checked}):\n`);
    for (const p of problems) console.error(`  ${p}`);
    console.error('\nEither the page does not exist, or the emitted route shape ' +
                  'no longer matches the link (check `trailingSlash` in ' +
                  'docs-site/docusaurus.config.ts).\n');
    process.exit(1);
}

console.log(`All ${checked} docs-site links resolve to built pages.`);
