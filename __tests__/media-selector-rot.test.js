/** @jest-environment node */
/**
 * Stop `@media` selector rot from growing.
 *
 * #197 found the `@media print` block had **20 of 24 selectors dead** after
 * the Phase 2 rebuild renamed the results containers, and the dead
 * `::after` meant a printed page carried no medical disclaimer. That was
 * fixed. The generalisation was not: nothing checks whether any other
 * `@media` block's selectors still resolve.
 *
 * Auditing all 21 blocks found **55 of 196 selectors dead (28%)**, clustered
 * exactly where features were removed — `.what-if-*` (5/5), `.landing-*`
 * (26/49 in one block), `.data-header` (a page that no longer exists).
 *
 * These are NOT the print bug. A dead responsive rule does nothing where
 * nothing needs doing: it is bloat and a trap for someone editing a rule
 * that cannot fire, not lost content. So this ratchets rather than demands a
 * sweep — a mass deletion carries real risk (a class built by string
 * concatenation would look dead and not be), for little gain.
 *
 * If you legitimately remove dead rules, lower BASELINE_DEAD to match.
 */
const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');

const ROOT = path.join(__dirname, '..');

/**
 * Measured 2026-08-28 by this file's own detector. Lower it when rules are
 * cleaned up; never raise it.
 *
 * It must equal the CURRENT count exactly, not an approximation. The first
 * version used 58 (from a standalone audit script whose detector differed
 * slightly) against an actual 55, and the three selectors of slack meant
 * adding a dead rule passed. A ratchet with slack is not a ratchet — caught
 * by negative-testing it.
 */
const BASELINE_DEAD = 55;

function collectPresentTokens() {
  const present = new Set();
  for (const file of fs.readdirSync(ROOT).filter((f) => f.endsWith('.html'))) {
    const doc = new JSDOM(fs.readFileSync(path.join(ROOT, file), 'utf8')).window.document;
    doc.querySelectorAll('*').forEach((el) => {
      if (el.id) present.add('#' + el.id);
      if (el.className && typeof el.className === 'string') {
        el.className.trim().split(/\s+/).forEach((c) => c && present.add('.' + c));
      }
    });
  }
  return present;
}

/** Classes created at runtime never appear in the HTML, so scan the JS too. */
function collectJsSource() {
  const out = [];
  const walk = (dir) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      if (entry.name === 'node_modules' || entry.name.startsWith('.')) continue;
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) walk(full);
      else if (entry.name.endsWith('.js')) out.push(fs.readFileSync(full, 'utf8'));
    }
  };
  walk(ROOT);
  return out.join('\n');
}

function mediaBlocks(css) {
  const blocks = [];
  let i = 0;
  while ((i = css.indexOf('@media', i)) !== -1) {
    const open = css.indexOf('{', i);
    let depth = 0;
    let end = open;
    for (let j = open; j < css.length; j++) {
      if (css[j] === '{') depth++;
      else if (css[j] === '}' && --depth === 0) { end = j; break; }
    }
    blocks.push({ cond: css.slice(i, open).trim(), body: css.slice(open + 1, end) });
    i = end + 1;
  }
  return blocks;
}

function selectorsOf(body) {
  const out = new Set();
  body.replace(/\/\*[\s\S]*?\*\//g, '')
    .split('}')
    .map((chunk) => chunk.split('{')[0])
    .forEach((head) => head.split(',').forEach((sel) => {
      const s = sel.trim().replace(/::?[a-z-]+(\([^)]*\))?/g, '').trim();
      if (s && /^[.#a-zA-Z]/.test(s)) out.add(s);
    }));
  return [...out];
}

function deadSelectors() {
  const css = fs.readFileSync(path.join(ROOT, 'styles.css'), 'utf8');
  const present = collectPresentTokens();
  const js = collectJsSource();
  const dead = [];
  for (const block of mediaBlocks(css)) {
    for (const sel of selectorsOf(block.body)) {
      const parts = sel.split(/[\s>+~]+/).filter(Boolean);
      const missing = parts.some((p) => {
        const m = p.match(/^([.#][\w-]+)/);
        if (!m) return false;
        return !present.has(m[1]) && !js.includes(m[1].slice(1));
      });
      if (missing) dead.push(`${block.cond} → ${sel}`);
    }
  }
  return dead;
}

test('the audit finds selectors at all', () => {
  // Guard the guard: a parser that silently returns [] would make the
  // ratchet below pass forever.
  const css = fs.readFileSync(path.join(ROOT, 'styles.css'), 'utf8');
  const blocks = mediaBlocks(css);
  expect(blocks.length).toBeGreaterThan(10);
  const total = blocks.reduce((n, b) => n + selectorsOf(b.body).length, 0);
  expect(total).toBeGreaterThan(100);
});

test('@media selector rot does not grow', () => {
  const dead = deadSelectors();
  expect(dead.length).toBeLessThanOrEqual(BASELINE_DEAD);
});

test('the print block specifically stays clean', () => {
  // #197's fix. Print is the one block with no feedback loop -- a dead rule
  // there silently drops content rather than doing nothing -- so it is held
  // to zero rather than to the ratchet.
  const printDead = deadSelectors().filter((d) => d.startsWith('@media print'));
  expect(printDead).toEqual([]);
});
