/** @jest-environment jsdom */
/**
 * No inline event-handler attributes anywhere in the HTML (#250).
 *
 * 25 of them — 15 `onclick="goStep(N)"` on the landing stepper, 9
 * `onerror="window._cdnFailed.X=true"` CDN flags, and one
 * `onsubmit="return false;"` — were the binding constraint on a useful
 * Content-Security-Policy. Any one of them forces `script-src
 * 'unsafe-inline'`, which removes most of what a CSP is for, so counting them
 * down to zero is what makes 3c possible at all.
 *
 * The CDN flags could not simply move to `addEventListener` in a page module:
 * a resource error fires while the document is parsing, before those modules
 * run. `cdn-fallback.js` registers a CAPTURING listener first instead —
 * resource errors do not bubble, so the capture flag is load-bearing.
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const HANDLER = /\son(click|change|input|submit|load|error|keyup|keydown|focus|blur|mouseover|mouseout)\s*=\s*["']/i;

function htmlFiles() {
  const out = [];
  for (const e of fs.readdirSync(ROOT)) if (e.endsWith('.html')) out.push(e);
  for (const d of ['simulator', 'explorer', 'validation', 'components', 'shared']) {
    const dir = path.join(ROOT, d);
    if (!fs.existsSync(dir)) continue;
    for (const e of fs.readdirSync(dir)) if (e.endsWith('.html')) out.push(path.join(d, e));
  }
  return out;
}

test('the scan sees real pages — otherwise this passes vacuously', () => {
  const files = htmlFiles();
  expect(files.length).toBeGreaterThan(10);
  expect(files).toContain('index.html');
  expect(files).toContain('simulator.html');
});

test('no HTML file contains an inline event-handler attribute', () => {
  const offenders = [];
  for (const f of htmlFiles()) {
    const src = fs.readFileSync(path.join(ROOT, f), 'utf8');
    src.split('\n').forEach((line, i) => {
      if (HANDLER.test(line)) offenders.push(`${f}:${i + 1}: ${line.trim().slice(0, 80)}`);
    });
  }
  expect(offenders).toEqual([]);
});

test('cdn-fallback.js loads before any third-party tag on the pages that need it', () => {
  // Registering the listener after a CDN tag would be silently useless: the
  // error it exists to catch has already fired.
  for (const f of ['simulator.html', 'explorer.html']) {
    const src = fs.readFileSync(path.join(ROOT, f), 'utf8');
    // Match the actual <script> TAG, not the bare filename — the filename
    // also appears in an explanatory comment near the top of <head>, so a
    // substring search reported the comment's position and passed even with
    // the real tag moved below the CDN links. Found by negative-testing.
    const m = /<script[^>]*src=["'][^"']*cdn-fallback\.js["'][^>]*>/i.exec(src);
    expect(m).toBeTruthy();
    const fb = m.index;
    const firstCdn = Math.min(
      ...['https://unpkg.com', 'https://cdn.jsdelivr.net']
        .map(h => { const i = src.indexOf(h); return i === -1 ? Infinity : i; }));
    expect(fb).toBeLessThan(firstCdn);
  }
});

test('the fallback listener uses capture, without which it is inert', () => {
  const src = fs.readFileSync(path.join(ROOT, 'cdn-fallback.js'), 'utf8');
  // the listener body is long, so anchor on the closing argument rather
  // than trying to span it
  const i = src.indexOf("addEventListener('error'");
  expect(i).toBeGreaterThan(-1);
  const tail = src.slice(i);
  expect(tail).toMatch(/\}\s*,\s*true\s*\)/);
});

test('flag mapping prefers the most specific match', () => {
  // "leaflet.markercluster.js" also contains "leaflet"; a naive scan would
  // mislabel it and the wrong fallback would fire.
  const src = fs.readFileSync(path.join(ROOT, 'cdn-fallback.js'), 'utf8');
  window.eval(src);
  const f = window._cdnFallbackFlagFor;
  expect(f('https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js')).toBe('markerCluster');
  expect(f('https://unpkg.com/leaflet@1.9.4/dist/leaflet.js')).toBe('leaflet');
  expect(f('https://unpkg.com/leaflet@1.9.4/dist/leaflet.css')).toBe('leafletCss');
  expect(f('https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js')).toBe('leafletHeat');
  expect(f('https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js')).toBe('chartjs');
  expect(f('https://example.com/unknown-lib.js')).toBeNull();
});

test('the landing stepper is wired declaratively', () => {
  const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
  expect((html.match(/data-go-step=/g) || []).length).toBeGreaterThanOrEqual(14);
  const js = fs.readFileSync(path.join(ROOT, 'landing-story.js'), 'utf8');
  expect(js).toMatch(/data-go-step/);
  expect(js).toMatch(/data-scroll-to/);
});

// ── inline <script> blocks (#250, the other half of the CSP blocker) ────────

test('no HTML file contains an executable inline <script> block', () => {
  // 26 of these existed: 15 copies of the Vercel analytics stub, plus 11
  // page bodies totalling ~128KB. Together with the inline handlers they are
  // what forces script-src 'unsafe-inline'.
  //
  // Non-executable blocks (JSON-LD and similar) are exempt — a CSP does not
  // care about them.
  const offenders = [];
  for (const f of htmlFiles()) {
    const src = fs.readFileSync(path.join(ROOT, f), 'utf8');
    const re = /<script\b([^>]*)>([\s\S]*?)<\/script>/gi;
    let m;
    while ((m = re.exec(src)) !== null) {
      const attrs = m[1], body = m[2];
      if (/src=/i.test(attrs) || !body.trim()) continue;
      if (/type=["'](?!text\/javascript|application\/javascript)/i.test(attrs)) continue;
      offenders.push(`${f}: ${body.trim().slice(0, 60)}`);
    }
  }
  expect(offenders).toEqual([]);
});

test('the analytics stub is shared, not copy-pasted per page', () => {
  const stub = path.join(ROOT, 'pages', 'vercel-analytics-stub.js');
  expect(fs.existsSync(stub)).toBe(true);
  const users = htmlFiles().filter(f =>
    fs.readFileSync(path.join(ROOT, f), 'utf8').includes('vercel-analytics-stub.js'));
  expect(users.length).toBeGreaterThanOrEqual(15);
});

test('every referenced page-script exists and holds real code', () => {
  // A header comment with no body would mean the extraction silently dropped
  // the page's logic while still looking wired up.
  for (const f of htmlFiles()) {
    const src = fs.readFileSync(path.join(ROOT, f), 'utf8');
    for (const m of src.matchAll(/<script[^>]*src="(pages\/[^"]+)"/g)) {
      const p = path.join(ROOT, m[1]);
      expect(fs.existsSync(p)).toBe(true);
      const body = fs.readFileSync(p, 'utf8');
      const code = body.includes('*/') ? body.split('*/').slice(1).join('*/') : body;
      expect(code.trim().length).toBeGreaterThan(10);
    }
  }
});
