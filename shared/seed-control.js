/**
 * seed-control.js — one reusable seed input for every stochastic tool (#350).
 *
 * Every stochastic endpoint accepts a `seed` and echoes back `seed_used`, and
 * the papers claim runs are fully reproducible. But no page ever exposed a
 * way to SET one: the simulator displayed the seed it happened to get, and
 * equity, sensitivity and scenarios did not mention seeds at all. So the
 * reproducibility guarantee existed in the API and was unreachable from the
 * app — you could see which seed you got, but never ask for it again.
 *
 * Usage:
 *   TransPlanSeed.inject('containerId');          // renders input + display
 *   var seed = TransPlanSeed.getSeed('containerId');  // int, or null for auto
 *   TransPlanSeed.setUsedSeed('containerId', result.seed_used);
 */
(function () {
  'use strict';

  var PREFIX = 'tps-';

  function _ids(containerId) {
    return {
      input: PREFIX + containerId + '-input',
      used: PREFIX + containerId + '-used',
      reuse: PREFIX + containerId + '-reuse',
    };
  }

  /**
   * Render the control into a container.
   * @param {string} containerId
   * @param {object} [opts] - {label} overrides the field label.
   */
  function inject(containerId, opts) {
    var container = document.getElementById(containerId);
    if (!container) return;
    var o = opts || {};
    var id = _ids(containerId);

    while (container.firstChild) container.removeChild(container.firstChild);

    var wrap = document.createElement('div');
    wrap.className = 'tps-wrap';
    wrap.style.cssText = 'display:flex; align-items:center; gap:0.5rem; flex-wrap:wrap;';

    var label = document.createElement('label');
    label.setAttribute('for', id.input);
    label.textContent = o.label || 'Random seed';
    label.style.cssText = 'font-size:0.85rem;';

    var input = document.createElement('input');
    input.type = 'number';
    input.id = id.input;
    input.min = '0';
    input.step = '1';
    input.placeholder = 'auto';
    input.style.cssText = 'width:130px;';
    input.title = 'Leave blank for a fresh random run. Enter a seed to ' +
      'reproduce a previous run exactly.';

    var used = document.createElement('span');
    used.id = id.used;
    used.style.cssText = 'font-size:0.82rem; opacity:0.85;';

    var reuse = document.createElement('button');
    reuse.type = 'button';
    reuse.id = id.reuse;
    reuse.textContent = 'Reuse';
    reuse.style.cssText = 'font-size:0.78rem; padding:0.15rem 0.5rem; display:none;';
    reuse.title = 'Copy the seed of the last run into the field so the next ' +
      'run reproduces it.';
    reuse.addEventListener('click', function () {
      if (reuse.dataset.seed) input.value = reuse.dataset.seed;
    });

    wrap.appendChild(label);
    wrap.appendChild(input);
    wrap.appendChild(used);
    wrap.appendChild(reuse);
    container.appendChild(wrap);
  }

  /**
   * The seed to send, or null for "let the server pick".
   *
   * Returns null rather than 0 for an empty field: 0 is a VALID seed, so
   * coercing blank to 0 would silently pin every "auto" run to the same
   * stream.
   */
  function getSeed(containerId) {
    var el = document.getElementById(_ids(containerId).input);
    if (!el) return null;
    var raw = (el.value || '').trim();
    if (raw === '') return null;
    var n = parseInt(raw, 10);
    return (isNaN(n) || n < 0) ? null : n;
  }

  /** Show the seed a run actually used and enable the reuse button. */
  function setUsedSeed(containerId, seed) {
    var id = _ids(containerId);
    var used = document.getElementById(id.used);
    var reuse = document.getElementById(id.reuse);
    if (!used) return;
    if (seed === null || seed === undefined) {
      used.textContent = '';
      if (reuse) reuse.style.display = 'none';
      return;
    }
    used.textContent = 'Last run used seed ' + seed;
    if (reuse) {
      reuse.dataset.seed = String(seed);
      reuse.style.display = '';
    }
  }

  window.TransPlanSeed = {
    inject: inject,
    getSeed: getSeed,
    setUsedSeed: setUsedSeed,
  };
})();
