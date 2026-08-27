/**
 * Every third-party script and stylesheet must be version-pinned and
 * integrity-hashed (#250).
 *
 * Before this, 16 of 19 external resources had no `integrity`, and two pages
 * loaded `cdn.jsdelivr.net/npm/chart.js` **completely unversioned** — it
 * resolved to 4.5.1 with a 7-day cache while equity.html pinned 4.4.4, so the
 * same app ran two different versions and a 5.x release would have broken
 * those pages with no commit and no CI failure.
 *
 * That matters more here than on a typical site: this is patient-facing
 * decision support, and a CDN foothold or a hostile network would execute
 * arbitrary JavaScript in the page that renders centre recommendations.
 *
 * The check is static, and deliberately so — it must fail on the *next* CDN
 * tag someone adds, not only when a hash happens to be wrong at runtime.
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');

function htmlFiles() {
  const out = [];
  for (const entry of fs.readdirSync(ROOT)) {
    if (entry.endsWith('.html')) out.push(entry);
  }
  for (const dir of ['simulator', 'explorer', 'validation', 'shared', 'components']) {
    const d = path.join(ROOT, dir);
    if (!fs.existsSync(d)) continue;
    for (const e of fs.readdirSync(d)) if (e.endsWith('.html')) out.push(path.join(dir, e));
  }
  return out;
}

/** external <script src> and <link rel=stylesheet href> tags */
function externalTags() {
  const tags = [];
  for (const f of htmlFiles()) {
    const src = fs.readFileSync(path.join(ROOT, f), 'utf8');
    const re = /<(script|link)\b([^>]*)>/gi;
    let m;
    while ((m = re.exec(src)) !== null) {
      const tag = m[1].toLowerCase();
      const attrs = m[2];
      const url = /(?:src|href)=["'](https?:\/\/[^"']+)/i.exec(attrs);
      if (!url) continue;
      if (tag === 'link' && !/stylesheet/i.test(attrs)) continue;
      tags.push({ file: f, tag, attrs, url: url[1] });
    }
  }
  return tags;
}

test('the scan finds tags at all — otherwise every assertion is vacuous', () => {
  const tags = externalTags();
  expect(tags.length).toBeGreaterThan(10);
});

test('every external script and stylesheet carries an integrity hash', () => {
  const missing = externalTags()
    .filter(t => !/integrity=/i.test(t.attrs))
    .map(t => `${t.file}: ${t.url}`);
  expect(missing).toEqual([]);
});

test('integrity hashes are sha384 and look like base64', () => {
  for (const t of externalTags()) {
    const m = /integrity=["']([^"']+)["']/i.exec(t.attrs);
    expect(m).toBeTruthy();
    expect(m[1]).toMatch(/^sha(256|384|512)-[A-Za-z0-9+/]+=*$/);
  }
});

test('integrity is paired with crossorigin, or the browser ignores it', () => {
  // An integrity attribute without CORS is silently inert on a cross-origin
  // request — it looks protected and is not.
  const bad = externalTags()
    .filter(t => /integrity=/i.test(t.attrs) && !/crossorigin/i.test(t.attrs))
    .map(t => `${t.file}: ${t.url}`);
  expect(bad).toEqual([]);
});

test('no third-party URL floats on an unpinned or major-range version', () => {
  const offenders = [];
  for (const t of externalTags()) {
    const u = t.url;
    if (/cdn\.jsdelivr\.net\/npm\/[^@/]+(\/|$)/.test(u) && !/@\d/.test(u)) {
      offenders.push(`${t.file}: ${u} (no version at all)`);
      continue;
    }
    // unpkg/jsdelivr accept bare majors like @3 — those still float
    const ver = /@(\d+(?:\.\d+)*)/.exec(u);
    if (ver && ver[1].split('.').length < 3) {
      offenders.push(`${t.file}: ${u} (major range @${ver[1]} floats)`);
    }
  }
  expect(offenders).toEqual([]);
});

test('the same library is not loaded at two different versions', () => {
  const byLib = {};
  for (const t of externalTags()) {
    const m = /\/(?:npm\/)?([^/@]+)@([\d.]+)/.exec(t.url);
    if (!m) continue;
    (byLib[m[1]] = byLib[m[1]] || new Set()).add(m[2]);
  }
  const split = Object.entries(byLib)
    .filter(([, v]) => v.size > 1)
    .map(([k, v]) => `${k}: ${[...v].join(', ')}`);
  expect(split).toEqual([]);
});
