/** @jest-environment jsdom */
const fs = require('fs');
const path = require('path');

beforeAll(() => {
  const code = fs.readFileSync(path.join(__dirname, '../simulator/results-table.js'), 'utf8');
  // Execute the IIFE in the jsdom window scope so window.SimResultsTable is defined.
  // eslint-disable-next-line no-eval
  window.eval(code);
});

function makeScores(n) {
  return Array.from({ length: n }, (_, i) => ({
    code: 'C' + i, name: 'Center ' + i, state: 'TX', state_abbr: 'TX',
    rank: i + 1, total: 95 - i * 0.1, breakdown: {}, lat: 40, lon: -80,
  }));
}

function dataRowCount(container) {
  // data rows have a data-code attr (detail rows don't); fall back to tbody tr count
  return container.querySelectorAll('tbody tr').length;
}

test('renders only the first page (<=25 rows) for 248 centers', () => {
  const c = document.createElement('div');
  document.body.appendChild(c);
  window.SimResultsTable.render(c, { scores: makeScores(248), simulation: [], homeLocation: null });
  expect(dataRowCount(c)).toBeLessThanOrEqual(25);
  expect(c.querySelector('.results-pagination')).toBeTruthy();
  expect(c.textContent).toMatch(/page 1 of/i);
});

test('Show all renders all 248 rows', () => {
  const c = document.createElement('div');
  document.body.appendChild(c);
  window.SimResultsTable.render(c, { scores: makeScores(248), simulation: [], homeLocation: null });
  const toggle = Array.from(c.querySelectorAll('button')).find(b => /show all/i.test(b.textContent));
  expect(toggle).toBeTruthy();
  toggle.click();
  expect(dataRowCount(c)).toBeGreaterThanOrEqual(248);
});

test('small result sets show no pager, just a count', () => {
  const c = document.createElement('div');
  document.body.appendChild(c);
  window.SimResultsTable.render(c, { scores: makeScores(8), simulation: [], homeLocation: null });
  expect(dataRowCount(c)).toBe(8);
  expect(c.textContent).toMatch(/8 centers/);
});
