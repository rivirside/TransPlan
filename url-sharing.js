/**
 * TransPlan — URL Sharing
 *
 * Encodes form state into URL query parameters for shareable links.
 * On page load, restores form state from URL and auto-submits.
 * Adds a "Share Results" button that copies the URL to clipboard.
 */
(function () {
  'use strict';

  // Map form field IDs to URL param names (short but readable)
  var PARAM_MAP = {
    organ:               'organ',
    bloodType:           'bt',
    age:                 'age',
    sex:                 'sex',
    urgency:             'urg',
    weight:              'wt',
    height:              'ht',
    insurance:           'ins',
    cpra:                'cpra',
    meld:                'meld',
    las:                 'las',
    homeCenter:          'hc',
    adjustCauseOfDeath:  'cod',
    inferenceMode:       'im'
  };

  // Reverse map: URL param → field ID
  var REVERSE_MAP = {};
  Object.keys(PARAM_MAP).forEach(function (fieldId) {
    REVERSE_MAP[PARAM_MAP[fieldId]] = fieldId;
  });

  /**
   * Read current form state and encode as URLSearchParams string.
   */
  function encodeFormState() {
    var params = new URLSearchParams();
    var fields = {
      organ:              document.getElementById('organ'),
      bloodType:          document.getElementById('bloodType'),
      age:                document.getElementById('age'),
      sex:                document.getElementById('sex'),
      urgency:            document.getElementById('urgency'),
      weight:             document.getElementById('weight'),
      height:             document.getElementById('height'),
      insurance:          document.getElementById('insurance'),
      cpra:               document.getElementById('cpra'),
      meld:               document.getElementById('meld'),
      las:                document.getElementById('las'),
      homeCenter:         document.getElementById('homeCenter'),
      adjustCauseOfDeath: document.getElementById('adjustCauseOfDeath'),
      inferenceMode:      document.getElementById('inferenceMode')
    };

    Object.keys(fields).forEach(function (fieldId) {
      var el = fields[fieldId];
      if (!el) return;
      var paramName = PARAM_MAP[fieldId];
      var value;

      if (el.type === 'checkbox') {
        if (el.checked) params.set(paramName, '1');
        return;
      }

      value = el.value;
      // Skip empty/default values
      if (!value || value === '' || value === '0') return;
      params.set(paramName, value);
    });

    // Scoring weights (Phase 4 M1)
    if (window.TransPlanWeights) {
      var wts = window.TransPlanWeights.toParamString();
      if (wts) {
        params.set('wts', wts);
        params.set('wp', window.TransPlanWeights.getPresetName());
      }
    }

    return params.toString();
  }

  /**
   * Restore form state from URL query parameters.
   * Returns true if any parameters were found.
   */
  function restoreFromURL() {
    var params = new URLSearchParams(window.location.search);
    if (params.toString() === '') return false;

    var restored = false;

    params.forEach(function (value, paramName) {
      var fieldId = REVERSE_MAP[paramName];
      if (!fieldId) return;

      var el = document.getElementById(fieldId);
      if (!el) return;

      if (el.type === 'checkbox') {
        el.checked = value === '1' || value === 'true';
      } else if (el.type === 'range') {
        el.value = value;
        // Update range output display
        var output = document.getElementById(fieldId + '-output');
        if (output) output.textContent = value + '%';
      } else {
        el.value = value;
      }
      restored = true;
    });

    // If organ was set, trigger its change event to show conditional fields
    if (params.has('organ')) {
      var organEl = document.getElementById('organ');
      if (organEl) organEl.dispatchEvent(new Event('change'));
    }

    // Restore scoring weights (Phase 4 M1)
    if (params.has('wts') && window.TransPlanWeights) {
      window.TransPlanWeights.setWeightsFromString(params.get('wts'));
      // Expand the details element so user can see custom weights
      var details = document.getElementById('weightsDetails');
      if (details) details.open = true;
      restored = true;
    }

    return restored;
  }

  /**
   * Update the browser URL with current form state (without reload).
   */
  function updateURL() {
    var queryString = encodeFormState();
    var newURL = window.location.pathname;
    if (queryString) newURL += '?' + queryString;
    window.history.replaceState(null, '', newURL);
  }

  /**
   * Build the share button and insert it into the results section.
   */
  function buildShareButton() {
    // Check if already built
    if (document.getElementById('shareResultsBtn')) return;

    // Insert next to the print button in the results header row
    var printBtn = document.getElementById('printResults');
    if (!printBtn) return;
    var headerRow = printBtn.parentElement;
    if (!headerRow) return;

    var btn = document.createElement('button');
    btn.id = 'shareResultsBtn';
    btn.className = 'share-results-btn';
    btn.type = 'button';
    btn.setAttribute('aria-label', 'Copy shareable link to clipboard');

    var linkIcon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    linkIcon.setAttribute('width', '14');
    linkIcon.setAttribute('height', '14');
    linkIcon.setAttribute('viewBox', '0 0 24 24');
    linkIcon.setAttribute('fill', 'none');
    linkIcon.setAttribute('stroke', 'currentColor');
    linkIcon.setAttribute('stroke-width', '2');
    linkIcon.setAttribute('stroke-linecap', 'round');
    linkIcon.setAttribute('stroke-linejoin', 'round');
    var path1 = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path1.setAttribute('d', 'M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71');
    var path2 = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path2.setAttribute('d', 'M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71');
    linkIcon.appendChild(path1);
    linkIcon.appendChild(path2);

    var label = document.createElement('span');
    label.textContent = 'Share Results';

    btn.appendChild(linkIcon);
    btn.appendChild(label);

    btn.addEventListener('click', function () {
      updateURL();
      var url = window.location.href;

      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(function () {
          showCopiedFeedback(btn);
        }, function () {
          fallbackCopy(url, btn);
        });
      } else {
        fallbackCopy(url, btn);
      }
    });

    // Insert before the print button
    headerRow.insertBefore(btn, printBtn);
  }

  function fallbackCopy(text, btn) {
    var textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.cssText = 'position:fixed;left:-9999px;';
    document.body.appendChild(textarea);
    textarea.select();
    try {
      document.execCommand('copy');
      showCopiedFeedback(btn);
    } catch (e) {
      // If copy fails, select the URL in the address bar
      window.prompt('Copy this link:', text);
    }
    document.body.removeChild(textarea);
  }

  function showCopiedFeedback(btn) {
    var span = btn.querySelector('span');
    var original = span.textContent;
    span.textContent = 'Link Copied!';
    btn.classList.add('share-results-btn--copied');
    setTimeout(function () {
      span.textContent = original;
      btn.classList.remove('share-results-btn--copied');
    }, 2000);
  }

  /**
   * Hook into form submission to update URL and show share button.
   */
  function init() {
    var form = document.getElementById('transplantForm');
    if (!form) return;

    // Restore form state from URL on load
    var hadParams = restoreFromURL();

    // After form submit, update URL and add share button
    form.addEventListener('submit', function () {
      // Delay to let results render first
      setTimeout(function () {
        updateURL();
        buildShareButton();
      }, 100);
    });

    // Auto-submit if URL had parameters
    if (hadParams) {
      // Small delay to let conditional fields render
      setTimeout(function () {
        form.dispatchEvent(new Event('submit', { cancelable: true }));
      }, 200);
    }
  }

  // Expose for external use
  window.TransPlanSharing = {
    encodeFormState: encodeFormState,
    restoreFromURL: restoreFromURL,
    updateURL: updateURL
  };

  // Init on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
