/**
 * TransPlan — Configurable Scoring Weights (Phase 4 M1)
 *
 * IIFE module providing weight presets, slider UI, auto-normalization,
 * and re-score triggering. Exposes window.TransPlanWeights API.
 *
 * Weights are a frontend concern — they affect Phase 1 Location Scores only.
 * Backend receives custom_weights for export round-tripping but does not
 * alter Monte Carlo simulation rankings.
 */
(function () {
  'use strict';

  // ==================== CONSTANTS ====================

  var DEFAULT_WEIGHTS = {
    medicalCompatibility: 0.25,
    waitTime: 0.20,
    donorAvailability: 0.18,
    hospitalQuality: 0.15,
    geographic: 0.10,
    healthDemographics: 0.07,
    policy: 0.03,
    socioeconomic: 0.02
  };

  var CATEGORY_LABELS = {
    medicalCompatibility: 'Medical Compatibility',
    waitTime: 'Wait Time',
    donorAvailability: 'Donor Availability',
    hospitalQuality: 'Hospital Quality',
    geographic: 'Geographic',
    healthDemographics: 'Health Demographics',
    policy: 'Policy',
    socioeconomic: 'Socioeconomic'
  };

  var CATEGORY_KEYS = [
    'medicalCompatibility', 'waitTime', 'donorAvailability', 'hospitalQuality',
    'geographic', 'healthDemographics', 'policy', 'socioeconomic'
  ];

  var WEIGHT_PRESETS = {
    balanced: {
      label: 'Balanced (Default)',
      weights: DEFAULT_WEIGHTS
    },
    clinical: {
      label: 'Clinical Focus',
      weights: {
        medicalCompatibility: 0.35, waitTime: 0.15, donorAvailability: 0.10,
        hospitalQuality: 0.25, geographic: 0.05, healthDemographics: 0.05,
        policy: 0.03, socioeconomic: 0.02
      }
    },
    speed: {
      label: 'Speed Priority',
      weights: {
        medicalCompatibility: 0.15, waitTime: 0.30, donorAvailability: 0.25,
        hospitalQuality: 0.10, geographic: 0.08, healthDemographics: 0.05,
        policy: 0.05, socioeconomic: 0.02
      }
    },
    qol: {
      label: 'Quality of Life',
      weights: {
        medicalCompatibility: 0.15, waitTime: 0.15, donorAvailability: 0.10,
        hospitalQuality: 0.10, geographic: 0.20, healthDemographics: 0.10,
        policy: 0.05, socioeconomic: 0.15
      }
    }
  };

  // ==================== STATE ====================

  var _currentPreset = 'balanced';
  var _locked = {};           // { categoryKey: true } for locked sliders
  var _reScoreCallback = null; // set by script.js
  var _debounceTimer = null;

  // ==================== SLIDER UI ====================

  function buildSliderRow(key) {
    var pct = Math.round(DEFAULT_WEIGHTS[key] * 100);

    var row = document.createElement('div');
    row.className = 'weight-slider-row';
    row.dataset.key = key;

    // Label
    var label = document.createElement('label');
    label.className = 'weight-slider-label';
    label.textContent = CATEGORY_LABELS[key];
    label.setAttribute('for', 'weight-' + key);

    // Slider
    var slider = document.createElement('input');
    slider.type = 'range';
    slider.id = 'weight-' + key;
    slider.className = 'weight-slider';
    slider.min = '0';
    slider.max = '100';
    slider.step = '1';
    slider.value = String(pct);
    slider.setAttribute('aria-label', CATEGORY_LABELS[key] + ' weight');

    // Value display
    var valDisplay = document.createElement('span');
    valDisplay.className = 'weight-value';
    valDisplay.id = 'weight-val-' + key;
    valDisplay.textContent = pct + '%';

    // Lock checkbox
    var lockLabel = document.createElement('label');
    lockLabel.className = 'weight-lock-label';
    lockLabel.title = 'Lock this weight from auto-adjustment';
    var lockCb = document.createElement('input');
    lockCb.type = 'checkbox';
    lockCb.className = 'weight-lock';
    lockCb.id = 'weight-lock-' + key;
    lockCb.setAttribute('aria-label', 'Lock ' + CATEGORY_LABELS[key]);
    var lockIcon = document.createElement('span');
    lockIcon.className = 'weight-lock-icon';
    lockIcon.textContent = '\uD83D\uDD13'; // unlock icon
    lockLabel.appendChild(lockCb);
    lockLabel.appendChild(lockIcon);

    lockCb.addEventListener('change', function () {
      _locked[key] = lockCb.checked;
      lockIcon.textContent = lockCb.checked ? '\uD83D\uDD12' : '\uD83D\uDD13';
    });

    slider.addEventListener('input', function () {
      normalizeWeights(key);
      detectPresetOrCustom();
      triggerReScore();
    });

    row.appendChild(label);
    row.appendChild(slider);
    row.appendChild(valDisplay);
    row.appendChild(lockLabel);
    return row;
  }

  function initWeightSliders() {
    var container = document.getElementById('weightsSliders');
    if (!container) return;

    // Clear container using DOM methods
    while (container.firstChild) {
      container.removeChild(container.firstChild);
    }

    CATEGORY_KEYS.forEach(function (key) {
      container.appendChild(buildSliderRow(key));
    });

    // Wire preset dropdown
    var presetSelect = document.getElementById('weightPreset');
    if (presetSelect) {
      presetSelect.addEventListener('change', function () {
        setPreset(presetSelect.value);
      });
    }
  }

  // ==================== NORMALIZATION ====================

  function normalizeWeights(changedKey) {
    var changedSlider = document.getElementById('weight-' + changedKey);
    if (!changedSlider) return;

    var changedVal = parseInt(changedSlider.value, 10);

    // Collect unlocked keys (excluding the one being changed)
    var unlocked = CATEGORY_KEYS.filter(function (k) {
      return k !== changedKey && !_locked[k];
    });

    if (unlocked.length === 0) {
      // All others locked — just update display, sum may drift
      updateDisplay(changedKey, changedVal);
      updateSumDisplay();
      return;
    }

    // Current values of unlocked sliders
    var unlockedTotal = 0;
    unlocked.forEach(function (k) {
      unlockedTotal += parseInt(document.getElementById('weight-' + k).value, 10);
    });

    // Locked sliders total (excluding changed)
    var lockedTotal = 0;
    CATEGORY_KEYS.forEach(function (k) {
      if (k !== changedKey && _locked[k]) {
        lockedTotal += parseInt(document.getElementById('weight-' + k).value, 10);
      }
    });

    var targetUnlocked = 100 - changedVal - lockedTotal;
    if (targetUnlocked < 0) targetUnlocked = 0;

    // Distribute proportionally
    if (unlockedTotal > 0) {
      var remainder = targetUnlocked;
      var assigned = [];
      unlocked.forEach(function (k, i) {
        var oldVal = parseInt(document.getElementById('weight-' + k).value, 10);
        var ratio = oldVal / unlockedTotal;
        if (i < unlocked.length - 1) {
          var newVal = Math.round(ratio * targetUnlocked);
          newVal = Math.max(0, Math.min(100, newVal));
          assigned.push({ key: k, val: newVal });
          remainder -= newVal;
        } else {
          // Last slider absorbs rounding remainder
          var lastVal = Math.max(0, Math.min(100, remainder));
          assigned.push({ key: k, val: lastVal });
        }
      });
      assigned.forEach(function (a) {
        document.getElementById('weight-' + a.key).value = String(a.val);
        updateDisplay(a.key, a.val);
      });
    } else {
      // All unlocked are at 0 — distribute evenly
      var each = Math.floor(targetUnlocked / unlocked.length);
      var leftover = targetUnlocked - each * unlocked.length;
      unlocked.forEach(function (k, i) {
        var v = each + (i < leftover ? 1 : 0);
        document.getElementById('weight-' + k).value = String(v);
        updateDisplay(k, v);
      });
    }

    updateDisplay(changedKey, changedVal);
    updateSumDisplay();
  }

  function updateDisplay(key, pct) {
    var el = document.getElementById('weight-val-' + key);
    if (el) el.textContent = pct + '%';
  }

  function updateSumDisplay() {
    var sum = 0;
    CATEGORY_KEYS.forEach(function (k) {
      sum += parseInt(document.getElementById('weight-' + k).value, 10);
    });
    var el = document.getElementById('weightsSumDisplay');
    if (el) {
      el.textContent = sum + '%';
      el.classList.toggle('weights-sum-ok', sum === 100);
      el.classList.toggle('weights-sum-err', sum !== 100);
    }
  }

  // ==================== PRESETS ====================

  function setPreset(name) {
    var preset = WEIGHT_PRESETS[name];
    if (!preset) return;

    _currentPreset = name;

    // Unlock all sliders when switching presets
    _locked = {};
    CATEGORY_KEYS.forEach(function (k) {
      var lockCb = document.getElementById('weight-lock-' + k);
      if (lockCb) {
        lockCb.checked = false;
        var icon = lockCb.parentElement.querySelector('.weight-lock-icon');
        if (icon) icon.textContent = '\uD83D\uDD13';
      }
    });

    // Set slider values
    CATEGORY_KEYS.forEach(function (k) {
      var pct = Math.round(preset.weights[k] * 100);
      var slider = document.getElementById('weight-' + k);
      if (slider) slider.value = String(pct);
      updateDisplay(k, pct);
    });

    updateSumDisplay();

    // Update dropdown
    var select = document.getElementById('weightPreset');
    if (select) select.value = name;

    triggerReScore();
  }

  function detectPresetOrCustom() {
    var current = getWeightsAsIntegers();
    for (var name in WEIGHT_PRESETS) {
      var preset = WEIGHT_PRESETS[name];
      var match = CATEGORY_KEYS.every(function (k) {
        return current[k] === Math.round(preset.weights[k] * 100);
      });
      if (match) {
        _currentPreset = name;
        var sel = document.getElementById('weightPreset');
        if (sel) sel.value = name;
        return;
      }
    }
    // No preset matched — custom mode
    _currentPreset = 'custom';
    var sel = document.getElementById('weightPreset');
    if (sel) sel.value = 'custom';
  }

  // ==================== GETTERS ====================

  function getWeightsAsIntegers() {
    var result = {};
    CATEGORY_KEYS.forEach(function (k) {
      var el = document.getElementById('weight-' + k);
      result[k] = el ? parseInt(el.value, 10) : Math.round(DEFAULT_WEIGHTS[k] * 100);
    });
    return result;
  }

  /**
   * Returns custom weights as decimal fractions { medicalCompatibility: 0.25, ... }
   * Returns null if weights match the balanced defaults (optimization for URL/API).
   */
  function getWeights() {
    var ints = getWeightsAsIntegers();
    var isDefault = CATEGORY_KEYS.every(function (k) {
      return ints[k] === Math.round(DEFAULT_WEIGHTS[k] * 100);
    });
    if (isDefault) return null;

    var result = {};
    CATEGORY_KEYS.forEach(function (k) { result[k] = ints[k] / 100; });
    return result;
  }

  function getPresetName() {
    return _currentPreset;
  }

  // ==================== RE-SCORE TRIGGER ====================

  function triggerReScore() {
    if (_debounceTimer) clearTimeout(_debounceTimer);
    _debounceTimer = setTimeout(function () {
      if (typeof _reScoreCallback === 'function') {
        _reScoreCallback();
      }
    }, 150);
  }

  function onReScore(callback) {
    _reScoreCallback = callback;
  }

  // ==================== PROGRAMMATIC SETTERS ====================

  /**
   * Set weights from external source (URL restore, API response).
   * @param {Object} weights - { medicalCompatibility: 0.25, ... } as decimals
   */
  function setWeightsFromObject(weights) {
    if (!weights || typeof weights !== 'object') return;
    CATEGORY_KEYS.forEach(function (k) {
      if (typeof weights[k] === 'number') {
        var pct = Math.round(weights[k] * 100);
        var slider = document.getElementById('weight-' + k);
        if (slider) slider.value = String(pct);
        updateDisplay(k, pct);
      }
    });
    updateSumDisplay();
    detectPresetOrCustom();
  }

  /**
   * Set weights from comma-separated integer string (URL param format).
   * Order matches CATEGORY_KEYS.
   * @param {string} str - e.g. "25,20,18,15,10,7,3,2"
   */
  function setWeightsFromString(str) {
    if (!str || typeof str !== 'string') return;
    var parts = str.split(',');
    if (parts.length !== 8) return;

    var weights = {};
    CATEGORY_KEYS.forEach(function (k, i) {
      var val = parseInt(parts[i], 10);
      if (!isNaN(val)) weights[k] = val / 100;
    });
    setWeightsFromObject(weights);
  }

  /**
   * Serialize current weights as comma-separated integer string.
   * Returns null if weights match defaults.
   */
  function toParamString() {
    var w = getWeights();
    if (!w) return null;
    return CATEGORY_KEYS.map(function (k) {
      return Math.round(w[k] * 100);
    }).join(',');
  }

  // ==================== INIT ====================

  function init() {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', initWeightSliders);
    } else {
      initWeightSliders();
    }
  }

  init();

  // ==================== PUBLIC API ====================

  window.TransPlanWeights = {
    getWeights: getWeights,
    getPresetName: getPresetName,
    setPreset: setPreset,
    setWeightsFromObject: setWeightsFromObject,
    setWeightsFromString: setWeightsFromString,
    toParamString: toParamString,
    onReScore: onReScore,
    WEIGHT_PRESETS: WEIGHT_PRESETS,
    DEFAULT_WEIGHTS: DEFAULT_WEIGHTS,
    CATEGORY_KEYS: CATEGORY_KEYS,
    CATEGORY_LABELS: CATEGORY_LABELS
  };

})();
