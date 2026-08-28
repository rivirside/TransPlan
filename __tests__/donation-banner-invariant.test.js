/** @jest-environment node */
/**
 * #260: the donation banner must be either fully off or fully on.
 *
 * It was half-on. `donation-banner.js` returns on line 11 — disabled pending
 * #179, which needs a donation account the project does not have — while
 * **14 pages still fetched its 5.4 KB** to run nothing.
 *
 * Removing the tags fixes that, but creates the opposite hazard: whoever
 * implements #179 deletes the early `return`, sees nothing happen, and has no
 * clue the tags are gone. Both halves have to move together, so this asserts
 * exactly that.
 *
 * The pairing matters more than either half. A feature that is disabled in
 * two places, where turning on one does nothing visible, is the kind of thing
 * that gets debugged for an hour.
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const SCRIPT = path.join(ROOT, 'donation-banner.js');

function pagesLoadingIt() {
  return fs.readdirSync(ROOT)
    .filter((f) => f.endsWith('.html'))
    .filter((f) => fs.readFileSync(path.join(ROOT, f), 'utf8')
      .includes('donation-banner.js'));
}

/** True when the script short-circuits before rendering anything. */
function isDisabled(src) {
  const body = src.slice(src.indexOf("'use strict'"));
  const ret = body.indexOf('\n    return;');
  if (ret === -1) return false;
  // A bare `return;` at function top level, before any DOM work.
  const before = body.slice(0, ret);
  return !/document\.|appendChild|innerHTML/.test(before);
}

test('the script and the pages agree about whether the banner is on', () => {
  const src = fs.readFileSync(SCRIPT, 'utf8');
  const disabled = isDisabled(src);
  const pages = pagesLoadingIt();

  if (disabled) {
    expect(pages).toEqual([]);
  } else {
    // Re-enabled: it has to actually be loaded somewhere, or nothing shows.
    expect(pages.length).toBeGreaterThan(0);
  }
});

test('the detector is not vacuous', () => {
  // Guard the guard: if isDisabled() always returned true, the assertion
  // above would pass for any state of the pages.
  const src = fs.readFileSync(SCRIPT, 'utf8');
  expect(isDisabled(src)).toBe(true);          // current, deliberate state
  expect(isDisabled(src.replace('\n    return;', '\n    // enabled'))).toBe(false);
});

test('the script explains what re-enabling requires', () => {
  // The tags are gone, so the only place a future reader learns they must be
  // restored is this file.
  const src = fs.readFileSync(SCRIPT, 'utf8');
  expect(src).toMatch(/NOT CURRENTLY LOADED/i);
  expect(src).toContain('#179');
  expect(src).toMatch(/add .*script src="donation-banner\.js"/i);
});
