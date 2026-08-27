/** @jest-environment jsdom */
/**
 * L-084 disclosure: a category whose sub-score is identical at every center
 * cannot reorder the list, so its slider must say so.
 *
 * The flag is read from the published measurement rather than hardcoded, so
 * that if `medicalCompatibility` is ever made center-specific (#390) and the
 * artifact is regenerated, the note disappears on its own instead of becoming
 * a false statement. These tests pin that wiring — including the cases where
 * the note must NOT appear, which is the half that would otherwise rot.
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');

function artifact(overrides) {
  // Two organs, so "inert everywhere" is a real conjunction rather than a
  // single lookup that happens to be true.
  const cats = (inertMedical, inertWait) => ({
    medicalCompatibility: { weight: 0.25, inert: inertMedical, rank_driving_share: inertMedical ? 0 : 0.3 },
    waitTime: { weight: 0.20, inert: !!inertWait, rank_driving_share: 0.5 },
    donorAvailability: { weight: 0.18, inert: false, rank_driving_share: 0.13 },
    hospitalQuality: { weight: 0.15, inert: false, rank_driving_share: 0.21 },
    geographic: { weight: 0.10, inert: false, rank_driving_share: 0.06 },
    healthDemographics: { weight: 0.07, inert: false, rank_driving_share: 0.06 },
    policy: { weight: 0.03, inert: false, rank_driving_share: 0.02 },
    socioeconomic: { weight: 0.02, inert: false, rank_driving_share: 0.01 }
  });
  const base = {
    organs: {
      kidney: { categories: cats(true, false), inert_weight_mass: 0.25 },
      liver: { categories: cats(true, false), inert_weight_mass: 0.25 }
    }
  };
  return Object.assign(base, overrides || {});
}

function boot(fetchImpl) {
  document.body.innerHTML = '<div id="weightsSliders"></div>';
  global.fetch = fetchImpl;
  window.fetch = fetchImpl;
  jest.resetModules();
  const constants = fs.readFileSync(path.join(ROOT, 'scoring-constants.js'), 'utf8');
  const config = fs.readFileSync(path.join(ROOT, 'weight-config.js'), 'utf8');
  window.eval(constants);
  window.eval(config);
  // Let the annotation promise chain settle.
  return new Promise((resolve) => setTimeout(resolve, 0));
}

const ok = (doc) => () => Promise.resolve({ ok: true, json: () => Promise.resolve(doc) });

function noteFor(key) {
  const row = document.querySelector('.weight-slider-row[data-key="' + key + '"]');
  return row && row.querySelector('.weight-inert-note');
}

test('flags the category that is inert in every organ', async () => {
  await boot(ok(artifact()));
  const note = noteFor('medicalCompatibility');
  expect(note).toBeTruthy();
  expect(note.textContent).toMatch(/does not affect ranking/i);
  expect(
    document.querySelector('.weight-slider-row[data-key="medicalCompatibility"]')
      .classList.contains('weight-row-inert')
  ).toBe(true);
});

test('leaves every varying category unannotated', async () => {
  await boot(ok(artifact()));
  ['waitTime', 'donorAvailability', 'hospitalQuality', 'geographic',
   'healthDemographics', 'policy', 'socioeconomic'].forEach((k) => {
    expect(noteFor(k)).toBeFalsy();
  });
});

test('does NOT flag a category that is inert for only some organs', async () => {
  // The weights panel is not organ-scoped, so a category that matters for even
  // one organ must not be labelled dead. This is the assertion that keeps the
  // disclosure from over-claiming.
  const doc = artifact();
  doc.organs.liver.categories.waitTime.inert = true;   // inert for liver only
  await boot(ok(doc));
  expect(noteFor('waitTime')).toBeFalsy();
  expect(noteFor('medicalCompatibility')).toBeTruthy();  // still inert in both
});

test('drops the note once the category starts varying (#390 fixed)', async () => {
  const doc = artifact();
  doc.organs.kidney.categories.medicalCompatibility.inert = false;
  await boot(ok(doc));
  expect(noteFor('medicalCompatibility')).toBeFalsy();
});

test('the slider stays usable — the note is disclosure, not a disable', async () => {
  await boot(ok(artifact()));
  const slider = document.getElementById('weight-medicalCompatibility');
  expect(slider).toBeTruthy();
  expect(slider.disabled).toBe(false);
});

test('a missing or failed artifact leaves the panel intact', async () => {
  await boot(() => Promise.resolve({ ok: false, status: 404 }));
  expect(document.querySelectorAll('.weight-slider-row').length).toBe(8);
  expect(noteFor('medicalCompatibility')).toBeFalsy();

  await boot(() => Promise.reject(new Error('offline')));
  expect(document.querySelectorAll('.weight-slider-row').length).toBe(8);
});

test('does not double-annotate if the panel is rebuilt', async () => {
  await boot(ok(artifact()));
  const row = document.querySelector('.weight-slider-row[data-key="medicalCompatibility"]');
  expect(row.querySelectorAll('.weight-inert-note').length).toBe(1);
});
