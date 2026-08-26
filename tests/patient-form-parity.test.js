/** @jest-environment jsdom */
/**
 * The shared patient form feeds equity, sensitivity and scenarios. Fields it
 * fails to render or collect are silently dropped from all three at once
 * (#350), so parity with the simulator's own collection is worth pinning.
 */
const fs = require('fs');
const path = require('path');

beforeAll(() => {
  const code = fs.readFileSync(
    path.join(__dirname, '../components/patient-form.js'), 'utf8');
  // eslint-disable-next-line no-eval
  window.eval(code);
});

function renderForm(prefix) {
  document.body.innerHTML = '<div id="host"></div>';
  window.TransPlanPatientForm.inject('host', {
    compact: true, showCopula: false, showCOD: false, prefix: prefix || 'pf',
  });
}

function setValue(id, value) {
  const el = document.getElementById(id);
  if (!el) throw new Error(`no element #${id}`);
  el.value = value;
  el.dispatchEvent(new Event('input', { bubbles: true }));
  el.dispatchEvent(new Event('change', { bubbles: true }));
}

function visible(id) {
  const el = document.getElementById(id);
  return el ? el.style.display !== 'none' : false;
}

describe('clinical score fields', () => {
  beforeEach(() => renderForm());

  test('liver under 12 shows PELD, not MELD', () => {
    setValue('pf-organ', 'liver');
    setValue('pf-age', '8');
    expect(visible('pf-peldRow')).toBe(true);
    expect(visible('pf-meldRow')).toBe(false);
  });

  test('adult liver shows MELD, not PELD', () => {
    setValue('pf-organ', 'liver');
    setValue('pf-age', '45');
    expect(visible('pf-meldRow')).toBe(true);
    expect(visible('pf-peldRow')).toBe(false);
  });

  test('the MELD/PELD split follows age, not just organ', () => {
    setValue('pf-organ', 'liver');
    setValue('pf-age', '11');
    expect(visible('pf-peldRow')).toBe(true);
    setValue('pf-age', '12');
    expect(visible('pf-peldRow')).toBe(false);
    expect(visible('pf-meldRow')).toBe(true);
  });

  test('lung shows both CAS and the legacy LAS', () => {
    setValue('pf-organ', 'lung');
    expect(visible('pf-casRow')).toBe(true);
    expect(visible('pf-lasRow')).toBe(true);
  });
});

describe('collectFormData', () => {
  beforeEach(() => {
    renderForm();
    setValue('pf-bloodType', 'O+');
    setValue('pf-sex', 'male');
    setValue('pf-urgency', '2');
  });

  test('collects CAS for lung', () => {
    setValue('pf-organ', 'lung');
    setValue('pf-age', '55');
    setValue('pf-cas', '38.5');
    expect(window.TransPlanPatientForm.collectFormData().cas).toBe(38.5);
  });

  test('collects months already waiting', () => {
    setValue('pf-organ', 'kidney');
    setValue('pf-age', '45');
    setValue('pf-monthsWaiting', '14');
    expect(window.TransPlanPatientForm.collectFormData().monthsWaiting).toBe(14);
  });

  test('a negative PELD survives collection', () => {
    // PELD can legitimately be negative, so a `|| undefined` guard would
    // silently discard real scores. Zero has the same problem.
    setValue('pf-organ', 'liver');
    setValue('pf-age', '5');
    setValue('pf-peld', '-4');
    expect(window.TransPlanPatientForm.collectFormData().peld).toBe(-4);
    setValue('pf-peld', '0');
    expect(window.TransPlanPatientForm.collectFormData().peld).toBe(0);
  });

  test('zero months waiting is kept, not dropped', () => {
    setValue('pf-organ', 'kidney');
    setValue('pf-age', '45');
    setValue('pf-monthsWaiting', '0');
    expect(window.TransPlanPatientForm.collectFormData().monthsWaiting).toBe(0);
  });

  test('omitted optional fields stay absent', () => {
    setValue('pf-organ', 'kidney');
    setValue('pf-age', '45');
    const data = window.TransPlanPatientForm.collectFormData();
    expect(data.monthsWaiting).toBeUndefined();
    expect(data.peld).toBeUndefined();
  });
});

describe('pediatric notice', () => {
  beforeEach(() => renderForm());

  test('appears for a child and hides for an adult', () => {
    setValue('pf-organ', 'kidney');
    setValue('pf-age', '8');
    expect(visible('pf-pediatricNote')).toBe(true);
    setValue('pf-age', '45');
    expect(visible('pf-pediatricNote')).toBe(false);
  });
});

describe('populateFromURL', () => {
  test('URL params fire listeners so dependent rows sync', () => {
    // Assigning .value does not fire input/change, so before #350 a profile
    // arriving by link left every dependent control out of sync.
    renderForm();
    window.history.pushState({}, '', '?organ=liver&bt=O%2B&age=8&sex=female&urg=2');
    window.TransPlanPatientForm.populateFromURL();
    expect(document.getElementById('pf-organ').value).toBe('liver');
    expect(visible('pf-peldRow')).toBe(true);
    expect(visible('pf-pediatricNote')).toBe(true);
  });
});
