/**
 * #224: touch targets must clear the WCAG 2.5.8 AA minimum of 24x24.
 *
 * Measured at 375x812 with a full 233-center result set: 31 of 48 interactive
 * elements were below it — the eight weight sliders at 153x**6**, the mobile
 * nav toggle at 30x34, checkboxes at 34x18, footer links at 335x11. After the
 * fix, 1 of 51 remains and it is the documented inline exemption.
 *
 * This is a static check on the stylesheet rather than a rendered measurement,
 * because jsdom does no CSS layout — the rendered numbers above came from a
 * real browser at a coarse-pointer viewport. What this guards is the specific
 * rules being present, so a later edit cannot quietly drop them.
 */
const fs = require('fs');
const path = require('path');

const CSS = fs.readFileSync(path.join(__dirname, '..', 'styles.css'), 'utf8');

/** the declaration block for a selector, or null */
function block(selector) {
  const i = CSS.indexOf(selector + ' {');
  if (i === -1) return null;
  const open = CSS.indexOf('{', i);
  const close = CSS.indexOf('}', open);
  return CSS.slice(open + 1, close);
}

function px(decl, prop) {
  if (!decl) return null;
  const m = decl.match(new RegExp(prop + '\\s*:\\s*(\\d+)px'));
  return m ? parseInt(m[1], 10) : null;
}

test('the weight slider has a 24px hit box, not the original 6px', () => {
  const b = block('.weight-slider');
  expect(b).toBeTruthy();
  expect(px(b, 'height')).toBeGreaterThanOrEqual(24);
});

test('the weight slider keeps a thin VISIBLE track despite the taller box', () => {
  // Without appearance:none the browser draws its own control and ignores the
  // track rules, so a 24px box would render as a thick bar. Both halves are
  // required: the reset AND an explicit track height.
  const b = block('.weight-slider');
  expect(b).toMatch(/appearance:\s*none/);
  for (const sel of ['.weight-slider::-webkit-slider-runnable-track',
                     '.weight-slider::-moz-range-track']) {
    const t = block(sel);
    expect(t).toBeTruthy();
    expect(px(t, 'height')).toBeLessThanOrEqual(8);
  }
});

test('the slider thumb is centred on the thin track', () => {
  const thumb = block('.weight-slider::-webkit-slider-thumb');
  const track = block('.weight-slider::-webkit-slider-runnable-track');
  const th = px(thumb, 'height');
  const tr = px(track, 'height');
  const margin = (thumb.match(/margin-top:\s*(-?\d+)px/) || [])[1];
  expect(th).toBeGreaterThan(tr);
  // a thumb taller than its track must be pulled up by half the difference
  expect(Number(margin)).toBe(-Math.round((th - tr) / 2));
});

test('the mobile nav toggle clears 44x44', () => {
  const b = block('.nav-toggle');
  expect(px(b, 'min-width')).toBeGreaterThanOrEqual(44);
  expect(px(b, 'min-height')).toBeGreaterThanOrEqual(44);
});

test('coarse-pointer floors exist for links and checkboxes', () => {
  expect(CSS).toMatch(/@media\s*\(pointer:\s*coarse\)/);
  const i = CSS.indexOf('@media (pointer: coarse)');
  const scoped = CSS.slice(i, i + 1200);
  expect(scoped).toMatch(/input\[type="checkbox"\]/);
  expect(scoped).toMatch(/\.nav-brand/);
  expect(scoped).toMatch(/min-height:\s*24px/);
});

test('the enlargements are scoped so desktop density is untouched', () => {
  // The link/checkbox floors must stay inside the coarse-pointer query. The
  // slider and nav-toggle fixes are unconditional on purpose: they change hit
  // area without changing how anything looks.
  const i = CSS.indexOf('@media (pointer: coarse)');
  expect(i).toBeGreaterThan(-1);
  const before = CSS.slice(0, i);
  expect(before).not.toMatch(/\.footer-cols a\s*\{[^}]*min-height/);
});
