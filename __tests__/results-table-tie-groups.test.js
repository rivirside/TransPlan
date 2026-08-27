/** @jest-environment jsdom */
/**
 * L-083: when more than one center could be ranked #1, say so.
 *
 * Measured: several centers' bootstrap rank intervals reach first place —
 * lung 3, heart 7, liver 7, kidney 10 — so "your best center" is not a
 * supportable claim, while the aggregate rank correlation (0.99) makes the
 * ranking look settled.
 *
 * Derived from the per-center intervals already fetched for #313. The
 * endpoint's own `tie_groups` were tried first and rejected: their overlap
 * test is transitive, so the leading group is EVERY center for every organ
 * measured (74/74 lung, 233/233 kidney). That is true in a chaining sense and
 * useless as a statement — which only showed up against real API data, not
 * against fixtures.
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');

beforeAll(() => {
  window.eval(fs.readFileSync(path.join(ROOT, 'simulator/results-table.js'), 'utf8'));
});

function makeScores(n) {
  return Array.from({ length: n }, (_, i) => ({
    code: 'C' + i, name: 'Center ' + i, state: 'TX', state_abbr: 'TX',
    rank: i + 1, total: 95 - i * 0.1, breakdown: {}, lat: 40, lon: -80,
  }));
}

/** intervals where the first `nContenders` centers all reach rank 1 */
function intervals(n, nContenders) {
  const out = {};
  for (let i = 0; i < n; i++) {
    out['C' + i] = i < nContenders
      ? { rank_lo: 1, rank_hi: 5 + i }
      : { rank_lo: i + 2, rank_hi: i + 5 };   // never reaches rank 1
  }
  return out;
}

function render(container, opts) {
  window.SimResultsTable.setRankIntervals((opts && opts.intervals) || null);
  window.SimResultsTable.render(container, {
    scores: makeScores((opts && opts.n) || 30), simulation: [], homeLocation: null,
  });
}

function fresh() {
  const c = document.createElement('div');
  document.body.appendChild(c);
  return c;
}

afterEach(() => { document.body.innerHTML = ''; });

test('announces how many centers could be #1', () => {
  const c = fresh();
  render(c, { intervals: intervals(30, 8) });
  const note = c.querySelector('.rank-tie-note');
  expect(note).toBeTruthy();
  expect(note.textContent).toMatch(/^8 centers could be ranked #1/);
});

test('stays silent when exactly one center reaches rank 1', () => {
  const c = fresh();
  render(c, { intervals: intervals(30, 1) });
  expect(c.querySelector('.rank-tie-note')).toBeFalsy();
});

test('stays silent when no intervals are available', () => {
  const c = fresh();
  expect(() => render(c, { intervals: null })).not.toThrow();
  expect(c.querySelector('.rank-tie-note')).toBeFalsy();
});

test('names the contenders so the claim is checkable', () => {
  const c = fresh();
  render(c, { intervals: intervals(30, 3) });
  const t = c.querySelector('.rank-tie-note').textContent;
  expect(t).toMatch(/Center 0/);
  expect(t).toMatch(/Center 2/);
});

test('truncates a long contender list instead of printing every name', () => {
  // Guards the failure that killed the first design: for kidney, 10 centers
  // reach rank 1, and an untruncated list of a transitive group would have
  // printed all 233.
  const c = fresh();
  render(c, { intervals: intervals(30, 12) });
  const t = c.querySelector('.rank-tie-note').textContent;
  expect(t).toMatch(/^12 centers could be ranked #1/);
  expect(t).toMatch(/and 6 more/);
  expect(t.length).toBeLessThan(400);
});

test('does not duplicate the note when the table is re-rendered', () => {
  const c = fresh();
  const iv = intervals(30, 4);
  render(c, { intervals: iv });
  render(c, { intervals: iv });
  expect(c.querySelectorAll('.rank-tie-note').length).toBe(1);
});
