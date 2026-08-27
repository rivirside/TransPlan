/** @jest-environment jsdom */
/**
 * #227/#228: mark the rows whose position rests on national averages.
 *
 * The response-level note has said "N of M centers use partial national-
 * default inputs" since #219, but not which — and measured on the shipped
 * data that matters most exactly where the reader has least to fall back on:
 * for pancreas 10 of the top 10 scored centers are degraded, for intestine
 * 6 of 10. For intestine the aggregate reads "16 of 21", which tells someone
 * reading ten rows essentially nothing.
 *
 * The backend half (tag scoping, and the pin that organ-wide tags really are
 * center-invariant) is in backend/tests/test_per_center_provenance.py.
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');

beforeAll(() => {
  window.eval(fs.readFileSync(path.join(ROOT, 'simulator/results-table.js'), 'utf8'));
});

function scores(specs) {
  return specs.map((s, i) => ({
    code: 'C' + i, name: s.name || 'Center ' + i, state: 'TX', state_abbr: 'TX',
    rank: i + 1, total: 95 - i, breakdown: {}, lat: 40, lon: -80,
    data_quality: s.dq || null,
  }));
}

function render(specs, simulation) {
  const c = document.createElement('div');
  document.body.appendChild(c);
  window.SimResultsTable.setRankIntervals(null);
  window.SimResultsTable.render(c, {
    scores: scores(specs), simulation: simulation || [], homeLocation: null,
  });
  return c;
}

function flags(container) {
  return Array.from(container.querySelectorAll('.rt-dq-flag'));
}

test('a center with degraded inputs is marked, a clean one is not', () => {
  const c = render([
    { name: 'Clean Center' },
    { name: 'Degraded Center', dq: ['no_observed_outcomes'] },
  ]);
  const rows = c.querySelectorAll('tbody tr');
  expect(rows[0].querySelectorAll('.rt-dq-flag')).toHaveLength(0);
  expect(rows[1].querySelectorAll('.rt-dq-flag')).toHaveLength(1);
});

test('the marker names the missing input in plain language, not tag names', () => {
  const c = render([{ dq: ['acceptance_rate_national_default'] }]);
  const title = flags(c)[0].title;
  expect(title).toContain('organ offer acceptance');
  expect(title).not.toContain('_');           // no raw tag leaked through
  expect(title).toMatch(/national average/i);
});

test('multiple degraded inputs are listed together', () => {
  const c = render([{ dq: ['no_observed_outcomes', 'acceptance_rate_national_default'] }]);
  const title = flags(c)[0].title;
  expect(title).toContain('observed transplant outcomes');
  expect(title).toContain('organ offer acceptance');
  expect(title).toContain(' and ');
});

test('the marker is reachable without a mouse', () => {
  const c = render([{ dq: ['wait_time_national_default'] }]);
  // A title attribute alone never reaches a screen reader.
  expect(flags(c)[0].getAttribute('aria-label')).toBe(flags(c)[0].title);
});

test('simulation-only degradations mark the row too', () => {
  // competing_risks_national_default is excluded from SCORING tags — it is
  // not a scoring input — so it can only arrive on the simulation side. This
  // is the pancreas/intestine case that the measurement found.
  const c = render(
    [{ name: 'Sim Degraded' }],
    [{ center_code: 'C0', p_transplant_24mo: 0.5, median_wait_months: 12,
       confidence_interval_95: [0.4, 0.6],
       data_quality: ['competing_risks_national_default'] }]
  );
  expect(flags(c)).toHaveLength(1);
  expect(flags(c)[0].title).toContain('waitlist outcome risks');
});

test('tags present in both engines are named once', () => {
  const c = render(
    [{ dq: ['no_observed_outcomes'] }],
    [{ center_code: 'C0', p_transplant_24mo: 0.5, median_wait_months: 12,
       confidence_interval_95: [0.4, 0.6],
       data_quality: ['no_observed_outcomes', 'competing_risks_national_default'] }]
  );
  const title = flags(c)[0].title;
  expect(title.match(/observed transplant outcomes/g)).toHaveLength(1);
});

test('an organ-wide or unknown tag does not produce a marker', () => {
  // wait_median_reconstructed is true of EVERY pancreas center, so a badge on
  // all 99 rows would distinguish nothing; it has its own note above the
  // table. An unrecognized tag must never render as a raw identifier.
  const c = render([
    { dq: ['wait_median_reconstructed'] },
    { dq: ['some_future_tag_nobody_labelled'] },
  ]);
  expect(flags(c)).toHaveLength(0);
});

test('an empty tag array is not a marker', () => {
  const c = render([{ dq: [] }]);
  expect(flags(c)).toHaveLength(0);
});
