/** @jest-environment node */
/**
 * #162: the contact card must not promise a transplant-team page.
 *
 * The issue asks for a per-center staff directory. No structured source
 * exists, a scraped roster goes stale as people move on, and compiling named
 * clinicians across 248 institutions is an aggregation decision rather than a
 * scraping task — so the tool links out instead.
 *
 * The trap is in the wording. **167 of the 248 shipped URLs are a bare
 * hospital root**, not a transplant-program page. I originally proposed
 * labelling the link "Meet the transplant team", which would have sent two
 * thirds of readers to a homepage. Measuring the URLs before writing the
 * label is what caught it.
 *
 * So: label it for what it always is (a program website), keep the hostname
 * visible so the destination is not a mystery, and say plainly why no
 * directory is mirrored here.
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const PAGE = fs.readFileSync(path.join(ROOT, 'pages/center.page.js'), 'utf8');
const CONTACTS = JSON.parse(
  fs.readFileSync(path.join(ROOT, 'data/center-contacts.json'), 'utf8')).contacts;

/** URLs whose path is empty or a single character — a hospital home page. */
function bareRoots() {
  return Object.values(CONTACTS).filter((c) => {
    if (!c.website) return false;
    try {
      return new URL(c.website).pathname.replace(/\//g, '').length <= 1;
    } catch (e) { return false; }
  });
}

test('most shipped URLs really are bare hospital roots', () => {
  // The premise for the cautious wording. If the data ever becomes mostly
  // program-specific, a more specific label becomes honest and this test
  // should be revisited rather than silently kept.
  const roots = bareRoots().length;
  const total = Object.values(CONTACTS).filter((c) => c.website).length;
  expect(total).toBeGreaterThan(200);
  expect(roots).toBeGreaterThan(total * 0.5);
});

test('the link is labelled for what it is', () => {
  expect(PAGE).toContain("'Program website'");
});

test('it does not promise a team or staff page', () => {
  // The specific overclaim this guards against.
  const linkText = PAGE.match(/siteLink\.textContent = '([^']*)'/);
  expect(linkText).not.toBeNull();
  expect(linkText[1]).not.toMatch(/team|staff|physician|surgeon|meet/i);
});

test('the hostname stays visible', () => {
  // A label with no destination is its own kind of opaque.
  expect(PAGE).toMatch(/contact-host/);
  expect(PAGE).toMatch(/hostname\.replace/);
});

test('the card explains why no directory is mirrored', () => {
  expect(PAGE).toMatch(/contact-team-hint/);
  expect(PAGE).toMatch(/does\s*'\s*\+\s*'\s*not keep a directory|not keep a directory/);
});
