/**
 * The competing-risk outcome must not be labelled "Delisted" (F16).
 *
 * The state bundles three SRTR exits — REMDET (condition worsened), REMREC
 * (condition IMPROVED) and REFTX (refused transplant). Calling that "Delisted"
 * tells a candidate they have an X% chance of a bad outcome when part of that
 * probability is "you got better and no longer need a transplant".
 *
 * `bbn_parameterizer.py` already claimed in a docstring that "the UI labels
 * this state 'removed without transplant (other causes)'". It did not — the
 * legend, the chart and the CSV export all said "Delisted". A documentation
 * claim contradicted by the code, which is the same shape as the pgmpy error
 * messages in #401.
 *
 * The internal field names (p_delisting_24mo, COMPETING_OUTCOME_STATES) are
 * deliberately NOT renamed: they are an API contract, and churning them would
 * be a much larger change for no gain to a reader. Only what a user sees.
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const read = f => fs.readFileSync(path.join(ROOT, f), 'utf8');

const USER_FACING = [
  'simulator/results-table.js',
  'probability-charts.js',
  'export-handler.js',
];

test('no user-facing string calls the outcome "Delisted"', () => {
  const offenders = [];
  for (const f of USER_FACING) {
    const src = read(f);
    src.split('\n').forEach((line, i) => {
      const t = line.trim();
      // Skip comments. An explanation of WHY the old label was wrong has to be
      // able to quote it — the first version of this test flagged its own
      // rationale, the same comment-vs-code confusion that tripped the
      // cdn-fallback ordering check in #407.
      if (t.startsWith('//') || t.startsWith('*') || t.startsWith('/*')) return;
      // a quoted label, not a field name like p_delisting_24mo
      if (/["'][^"']*\bDelist(ed|ing)\b[^"']*["']/.test(line) &&
          !/p_delisting|delisting_factor|RISK_COLORS/.test(line)) {
        offenders.push(`${f}:${i + 1}: ${t.slice(0, 70)}`);
      }
    });
  }
  expect(offenders).toEqual([]);
});

test('the replacement label says removal, not delisting', () => {
  const table = read('simulator/results-table.js');
  expect(table).toMatch(/Removed \(other\)/);
  const chart = read('probability-charts.js');
  expect(chart).toMatch(/Removed \(other\)/);
});

test('the legend explains what the bundle contains', () => {
  // "Removed (other)" alone is not self-explanatory; a reader needs to know
  // improvement is in there, or the relabel just trades one confusion for another.
  const table = read('simulator/results-table.js');
  expect(table).toMatch(/improved/i);
  expect(table).toMatch(/worsened|refused/i);
});

test('the CSV header matches what the UI shows', () => {
  const exp = read('export-handler.js');
  expect(exp).toMatch(/P\(Removed other\)/);
  expect(exp).not.toMatch(/P\(Delisting\)/);
});

test('internal field names are left alone', () => {
  // Renaming the API contract is out of scope; this pins that decision so a
  // later reader does not "finish the job" and break consumers.
  expect(read('simulator/results-table.js')).toMatch(/p_delisting_24mo/);
  expect(read('export-handler.js')).toMatch(/p_delisting/);
});
