/**
 * patient-form.js — Reusable patient profile form for analysis pages.
 *
 * Usage:
 *   <div id="patient-form"></div>
 *   <script src="components/patient-form.js"></script>
 *   <script>
 *     TransPlanPatientForm.inject('patient-form', { compact: true });
 *   </script>
 *
 * Security note: All HTML injected by this module is built from hardcoded
 * string literals and integer constants — no user-supplied or external data
 * is interpolated into the markup. This is safe against XSS.
 *
 * Exposes window.TransPlanPatientForm with inject() and collectFormData().
 */
(function () {
  'use strict';

  var ORGANS = [
    { value: 'kidney', label: 'Kidney' },
    { value: 'liver', label: 'Liver' },
    { value: 'heart', label: 'Heart' },
    { value: 'lung', label: 'Lung' },
    { value: 'pancreas', label: 'Pancreas' },
    { value: 'intestine', label: 'Intestine' }
  ];

  var BLOOD_TYPES = ['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-'];

  var URGENCY_LEVELS = [
    { value: '1', label: 'Critical (Status 1)' },
    { value: '2', label: 'High Priority (Status 2)' },
    { value: '3', label: 'Active (Status 3)' },
    { value: '4', label: 'Inactive (Status 4)' }
  ];

  function _buildSelect(id, label, options, required) {
    var req = required ? ' *' : '';
    var html = '<label for="' + id + '">' + label + req + '</label>';
    html += '<select id="' + id + '"' + (required ? ' required' : '') + '>';
    html += '<option value="">Select...</option>';
    for (var i = 0; i < options.length; i++) {
      var opt = typeof options[i] === 'string'
        ? { value: options[i], label: options[i] }
        : options[i];
      html += '<option value="' + opt.value + '">' + opt.label + '</option>';
    }
    html += '</select>';
    return '<div class="pf-field">' + html + '</div>';
  }

  function _buildNumber(id, label, min, max, placeholder, required) {
    var req = required ? ' *' : '';
    var html = '<label for="' + id + '">' + label + req + '</label>';
    html += '<input type="number" id="' + id + '" min="' + min + '" max="' + max + '"';
    html += ' placeholder="' + (placeholder || '') + '"' + (required ? ' required' : '') + '>';
    return '<div class="pf-field">' + html + '</div>';
  }

  function _buildRange(id, label, min, max, value, valueId) {
    var html = '<label for="' + id + '">' + label + ' <span class="pf-range-val" id="' + valueId + '">' + value + '</span></label>';
    html += '<input type="range" id="' + id + '" min="' + min + '" max="' + max + '" value="' + value + '">';
    return '<div class="pf-field">' + html + '</div>';
  }

  function _buildCheckbox(id, label) {
    var html = '<label class="pf-checkbox"><input type="checkbox" id="' + id + '"> ' + label + '</label>';
    return '<div class="pf-field">' + html + '</div>';
  }

  /**
   * Inject a patient profile form into a container element.
   *
   * All HTML is built from hardcoded literals (organ names, blood types, etc.)
   * — no user input is interpolated, so this is safe against XSS.
   *
   * @param {string} containerId - ID of the target container div
   * @param {object} [options] - Configuration options
   * @param {boolean} [options.compact=false] - Use compact layout
   * @param {boolean} [options.showCopula=true] - Show copula checkbox
   * @param {boolean} [options.showCOD=true] - Show cause-of-death checkbox
   * @param {string} [options.prefix='pf'] - ID prefix to avoid collisions
   */
  function inject(containerId, options) {
    var opts = Object.assign({
      compact: false,
      showCopula: true,
      showCOD: true,
      prefix: 'pf'
    }, options || {});

    var p = opts.prefix + '-';
    var container = document.getElementById(containerId);
    if (!container) return;

    var html = '<div class="pf-form' + (opts.compact ? ' pf-compact' : '') + '">';

    // Required fields
    html += '<div class="pf-section"><h4>Patient Profile</h4>';
    html += '<div class="pf-grid">';
    html += _buildSelect(p + 'organ', 'Organ', ORGANS, true);
    html += _buildSelect(p + 'bloodType', 'Blood Type', BLOOD_TYPES, true);
    html += _buildNumber(p + 'age', 'Age', 1, 120, 'Age', true);
    html += _buildSelect(p + 'sex', 'Sex', [{ value: 'male', label: 'Male' }, { value: 'female', label: 'Female' }], true);
    html += _buildSelect(p + 'urgency', 'Urgency', URGENCY_LEVELS, true);
    html += _buildSelect(p + 'insurance', 'Insurance', [
      { value: 'medicare', label: 'Medicare' },
      { value: 'medicaid', label: 'Medicaid' },
      { value: 'private', label: 'Private' },
      { value: 'none', label: 'Uninsured' }
    ], false);
    html += '</div>';

    // Organ-specific fields
    html += '<div id="' + p + 'clinicalFields">';
    html += '<div id="' + p + 'cpraRow" style="display:none">';
    html += _buildRange(p + 'cpra', 'cPRA (Sensitization)', 0, 100, 0, p + 'cpraVal');
    html += '</div>';
    html += '<div id="' + p + 'meldRow" style="display:none">';
    html += _buildNumber(p + 'meld', 'MELD Score', 6, 40, '6-40', false);
    html += '</div>';
    html += '<div id="' + p + 'lasRow" style="display:none">';
    html += _buildNumber(p + 'las', 'LAS', 0, 100, '0-100', false);
    html += '</div>';
    html += '</div>';

    // Optional demographics
    html += '<div class="pf-grid">';
    html += _buildNumber(p + 'weight', 'Weight (lbs)', 20, 800, 'Optional', false);
    html += _buildNumber(p + 'height', 'Height (in)', 20, 100, 'Optional', false);
    html += '</div>';

    // Flags
    if (opts.showCopula) {
      html += _buildCheckbox(p + 'useCopula', 'Correlated competing risks (copula)');
    }
    if (opts.showCOD) {
      html += _buildCheckbox(p + 'adjustCOD', 'Adjust for cause-of-death patterns');
    }

    html += '</div>'; // pf-section
    html += '</div>'; // pf-form

    // Safe: all HTML is from hardcoded string literals, not user input
    container.innerHTML = html;

    // Wire organ-specific field visibility
    var organSelect = document.getElementById(p + 'organ');
    if (organSelect) {
      organSelect.addEventListener('change', function () {
        var v = this.value;
        _toggle(p + 'cpraRow', v === 'kidney');
        _toggle(p + 'meldRow', v === 'liver');
        _toggle(p + 'lasRow', v === 'lung');
      });
    }

    // Wire cPRA slider value display
    var cpraSlider = document.getElementById(p + 'cpra');
    var cpraVal = document.getElementById(p + 'cpraVal');
    if (cpraSlider && cpraVal) {
      cpraSlider.addEventListener('input', function () { cpraVal.textContent = this.value + '%'; });
    }

    // Default copula to checked
    var copulaBox = document.getElementById(p + 'useCopula');
    if (copulaBox) copulaBox.checked = true;
  }

  function _toggle(id, show) {
    var el = document.getElementById(id);
    if (el) el.style.display = show ? '' : 'none';
  }

  /**
   * Collect form data from an injected patient form.
   * @param {string} [prefix='pf'] - ID prefix used during inject()
   * @returns {object} Form data object matching PatientProfile fields
   */
  function collectFormData(prefix) {
    var p = (prefix || 'pf') + '-';
    var data = {};

    data.organ = _val(p + 'organ');
    data.bloodType = _val(p + 'bloodType');
    data.age = _intVal(p + 'age');
    data.sex = _val(p + 'sex');
    data.urgency = _intVal(p + 'urgency');
    data.insurance = _val(p + 'insurance') || undefined;
    data.weight = _floatVal(p + 'weight') || undefined;
    data.height = _floatVal(p + 'height') || undefined;

    // Organ-specific
    if (data.organ === 'kidney') data.cpra = _intVal(p + 'cpra');
    if (data.organ === 'liver') data.meld = _intVal(p + 'meld') || undefined;
    if (data.organ === 'lung') data.las = _floatVal(p + 'las') || undefined;

    // Flags
    var copula = document.getElementById(p + 'useCopula');
    if (copula) data.useCopula = copula.checked;
    var cod = document.getElementById(p + 'adjustCOD');
    if (cod) data.adjustForCauseOfDeath = cod.checked;

    return data;
  }

  function _val(id) {
    var el = document.getElementById(id);
    return el ? el.value : '';
  }
  function _intVal(id) {
    var v = _val(id);
    return v ? parseInt(v, 10) : null;
  }
  function _floatVal(id) {
    var v = _val(id);
    return v ? parseFloat(v) : null;
  }

  /**
   * Populate form fields from URL query parameters.
   * Canonical URL params: organ, bt, age, sex, urg, cpra, meld, las, ins, cop, cod
   * @param {string} [prefix='pf'] - ID prefix used during inject()
   * @returns {boolean} true if any params were applied
   */
  function populateFromURL(prefix) {
    var params = new URLSearchParams(window.location.search);
    if (!params.toString()) return false;

    var p = (prefix || 'pf') + '-';
    var applied = false;

    function setVal(id, val) {
      if (val == null) return;
      var el = document.getElementById(id);
      if (el) { el.value = val; applied = true; }
    }

    function setChecked(id, val) {
      var el = document.getElementById(id);
      if (el) { el.checked = !!val; applied = true; }
    }

    setVal(p + 'organ', params.get('organ'));
    setVal(p + 'bloodType', params.get('bt'));
    setVal(p + 'age', params.get('age'));
    setVal(p + 'sex', params.get('sex'));
    setVal(p + 'urgency', params.get('urg'));
    setVal(p + 'insurance', params.get('ins'));

    var cpra = params.get('cpra');
    if (cpra != null) {
      setVal(p + 'cpra', cpra);
      var cpraVal = document.getElementById(p + 'cpraVal');
      if (cpraVal) cpraVal.textContent = cpra + '%';
    }

    setVal(p + 'meld', params.get('meld'));
    setVal(p + 'las', params.get('las'));

    if (params.get('cop') === '1') setChecked(p + 'useCopula', true);
    if (params.get('cod') === '1') setChecked(p + 'adjustCOD', true);

    // Trigger organ change to show conditional fields
    var organEl = document.getElementById(p + 'organ');
    if (organEl && organEl.value) {
      organEl.dispatchEvent(new Event('change'));
    }

    return applied;
  }

  // Expose globally
  window.TransPlanPatientForm = {
    inject: inject,
    collectFormData: collectFormData,
    populateFromURL: populateFromURL
  };
})();
