/** @jest-environment node */
/**
 * No page may link to an HTML file that does not exist.
 *
 * Found via #183: the landing page linked to `data.html`, which was removed
 * in the Phase 3 page merge. A visitor clicking **"Data Explorer"** — the
 * headline call to action for the researcher audience — got a 404.
 *
 * One broken link across the whole site, and it was on the busiest page. It
 * survived because `check-docs-links.js` validates the *docs site* only;
 * nothing checked the app's own internal navigation.
 *
 * Same shape as the print stylesheet (#197) and the donation banner (#260):
 * a reference left dangling by a rename, silent because nothing looked.
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');

function pages() {
  return fs.readdirSync(ROOT).filter((f) => f.endsWith('.html'));
}

/** Local .html targets referenced by a page, ignoring anchors and externals. */
function localLinks(html) {
  const out = new Set();
  const re = /href="([^"]+\.html)(#[^"]*)?"/g;
  let m;
  while ((m = re.exec(html)) !== null) {
    const href = m[1];
    if (/^(https?:)?\/\//.test(href)) continue;   // external
    if (href.startsWith('docs-site/')) continue;  // covered by check-docs-links.js
    out.add(href);
  }
  return [...out];
}

test('every internal .html link resolves to a file that exists', () => {
  const broken = [];
  for (const page of pages()) {
    const html = fs.readFileSync(path.join(ROOT, page), 'utf8');
    for (const href of localLinks(html)) {
      const target = path.join(ROOT, href);
      if (!fs.existsSync(target)) broken.push(`${page} -> ${href}`);
    }
  }
  expect(broken).toEqual([]);
});

test('the check actually sees links', () => {
  // Guard the guard: a regex that stopped matching would make the test above
  // pass for any amount of rot.
  const index = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
  const links = localLinks(index);
  expect(links.length).toBeGreaterThan(5);
  expect(links).toContain('simulator.html');
});

test('the landing page points at pages that exist for both audiences', () => {
  // The specific regression: the researcher-facing call to action 404'd
  // while the patient-facing one worked, so the page looked fine.
  const index = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
  for (const href of ['simulator.html', 'explorer.html', 'scenarios.html']) {
    expect(index).toContain(`href="${href}"`);
    expect(fs.existsSync(path.join(ROOT, href))).toBe(true);
  }
  expect(index).not.toContain('href="data.html"');
});
