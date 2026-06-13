/** @jest-environment jsdom */
const fs = require('fs');
const path = require('path');

beforeAll(() => {
  const code = fs.readFileSync(path.join(__dirname, '../equity-charts.js'), 'utf8');
  // eslint-disable-next-line no-eval
  window.eval(code);
});

function cities(n) {
  // ascending Gini
  return Array.from({ length: n }, (_, i) => ({ city: 'C' + i, gini_coefficient: i / n }));
}

test('caps to the top-N highest-disparity centers when over the limit (#222)', () => {
  const cap = window.TransPlanEquityCharts._capGiniBars;
  const r = cap(cities(248), 30);
  expect(r.shown.length).toBe(30);
  expect(r.omitted).toBe(218);
  // highest-Gini retained (input ascending → last element is max)
  expect(r.shown[r.shown.length - 1].gini_coefficient).toBeCloseTo(247 / 248);
  // lowest-Gini of the shown subset is the 218th (dropped the 218 most-equal)
  expect(r.shown[0].city).toBe('C218');
});

test('keeps everything when under the limit', () => {
  const cap = window.TransPlanEquityCharts._capGiniBars;
  const r = cap(cities(22), 30);
  expect(r.shown.length).toBe(22);
  expect(r.omitted).toBe(0);
});

test('handles empty/undefined safely', () => {
  const cap = window.TransPlanEquityCharts._capGiniBars;
  expect(cap([], 30)).toEqual({ shown: [], omitted: 0 });
  expect(cap(undefined, 30)).toEqual({ shown: [], omitted: 0 });
});
