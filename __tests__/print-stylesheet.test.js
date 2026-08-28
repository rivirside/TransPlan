/** @jest-environment jsdom */
/**
 * #197: the print stylesheet must target elements that exist.
 *
 * The Phase 2 rebuild renamed the simulator's results containers and the
 * `@media print` block never followed. Measured against the live DOM with
 * results rendered: **20 of 24 selectors matched nothing**. Every positive
 * rule was dead, including the one that matters — the "not a substitute for
 * medical advice" footer hangs off `.results-section::after`, and
 * `.results-section` had become `#sim-results-section`. Someone printing
 * their results to take to a care team got a page with no disclaimer.
 *
 * A dead hide-rule is invisible (the thing simply prints). A dead show-rule
 * or ::after is worse: the page silently loses content nobody notices is
 * missing, because almost nobody prints, and no test covered it.
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const CSS = fs.readFileSync(path.join(ROOT, 'styles.css'), 'utf8');
const HTML = fs.readFileSync(path.join(ROOT, 'simulator.html'), 'utf8');

/**
 * Selectors for elements that only exist after JS renders results. Each is
 * listed with the module that creates it, so "it's dynamic" has to be a
 * checkable claim rather than an escape hatch.
 */
const RENDERED_AT_RUNTIME = {
  '.results-table': 'simulator/results-table.js render()',
  '.rt-compare-cell': 'simulator/results-table.js _buildDataRow',
  '.compare-check': 'simulator/results-table.js _buildDataRow',
  '.rt-detail-row': 'simulator/results-table.js _buildDetailRow',
  '.results-pagination-btn': 'simulator/results-table.js _renderPaginationControls',
  '.results-pagination-info': 'simulator/results-table.js _renderPaginationControls',
  '.site-nav': 'components/site-chrome.js (injected nav)',
  '.site-footer': 'components/site-chrome.js (injected footer)',
};

function printBlock() {
  const start = CSS.indexOf('@media print');
  expect(start).toBeGreaterThan(-1);
  // Walk braces to find the matching close, so nested rules are included.
  let depth = 0;
  for (let i = CSS.indexOf('{', start); i < CSS.length; i++) {
    if (CSS[i] === '{') depth++;
    else if (CSS[i] === '}' && --depth === 0) return CSS.slice(start, i + 1);
  }
  throw new Error('unterminated @media print block');
}

/** Every simple selector mentioned inside the print block. */
function printSelectors() {
  const body = printBlock();
  const inner = body.slice(body.indexOf('{') + 1, body.lastIndexOf('}'));
  const out = new Set();
  // Strip comments and declaration bodies, keep selector lists.
  const cleaned = inner.replace(/\/\*[\s\S]*?\*\//g, '');
  const ruleHeads = cleaned.split('}').map(chunk => chunk.split('{')[0]);
  ruleHeads.forEach(head => {
    head.split(',').forEach(sel => {
      const s = sel.trim()
        .replace(/::?(after|before|first-line|marker)\b/g, '')
        .trim();
      if (s && /^[.#a-zA-Z]/.test(s)) out.add(s);
    });
  });
  return [...out];
}

beforeAll(() => {
  document.documentElement.innerHTML = HTML;
});

test('the parser finds a non-trivial set of selectors', () => {
  // Guard the guard: if the extractor silently returned [], every assertion
  // below would pass while checking nothing.
  const sels = printSelectors();
  expect(sels.length).toBeGreaterThan(10);
  expect(sels).toContain('#sim-results-section');
});

test('every print selector matches the page or is a declared runtime element', () => {
  const dead = [];
  printSelectors().forEach(sel => {
    if (sel === 'body') return;
    if (document.querySelector(sel)) return;
    // A descendant of a runtime element is itself runtime-only:
    // `.results-table tr` cannot exist before `.results-table` does.
    if (RENDERED_AT_RUNTIME[sel]) return;
    if (Object.keys(RENDERED_AT_RUNTIME).some(base => sel.startsWith(base + ' '))) return;
    dead.push(sel);
  });
  expect(dead).toEqual([]);
});

test('the runtime allowlist has no stale entries', () => {
  // An allowlist that outlives its selectors is how the original rot hid.
  const used = new Set(printSelectors());
  const unused = Object.keys(RENDERED_AT_RUNTIME).filter(
    base => !used.has(base) && ![...used].some(s => s.startsWith(base + ' ')));
  expect(unused).toEqual([]);
});

test('the medical disclaimer is anchored to an element that exists', () => {
  const body = printBlock();
  const match = body.match(/([#.][\w-]+)::after\s*\{[^}]*Not a substitute for medical advice/);
  expect(match).not.toBeNull();
  const anchor = match[1];
  expect(document.querySelector(anchor)).not.toBeNull();
});

test('the results container is shown, not just everything else hidden', () => {
  const body = printBlock();
  expect(body).toMatch(/#sim-results-section[\s\S]*?display:\s*block\s*!important/);
});

test('the interactive controls are hidden', () => {
  const body = printBlock();
  ['#sim-export-btn', '#sim-score-btn', '#sim-run-btn', '.sidebar'].forEach(sel => {
    expect(body).toContain(sel);
  });
});

test('the pagination COUNT survives even though its buttons do not', () => {
  // A printout of page 1 of 10 must not read as the complete list (#197).
  const body = printBlock();
  expect(body).toMatch(/\.results-pagination-info[\s\S]*?display:\s*inline\s*!important/);
  expect(body).toMatch(/\.results-pagination-btn[^{]*\{[^}]*display:\s*none/);
});
