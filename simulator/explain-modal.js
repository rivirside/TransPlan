/**
 * Explain Calculations Modal
 *
 * Opens a modal showing the full provenance trail for a single center's score:
 * - Each of the 8 categories with sub-components, weights, sources, and formulas
 * - List of data files consulted
 * - Final weighted sum that produces the total score
 *
 * Fetches POST /score/explain on first open per patient profile and caches
 * the result keyed by a profile signature. Subsequent center detail clicks
 * use the cache.
 *
 * Globals required:
 *   - window.TransPlanAPI (api-client.js)
 */
(function () {
  'use strict';

  var BREAKDOWN_LABELS = {
    medicalCompatibility: 'Medical Compatibility',
    waitTime: 'Wait Time',
    donorAvailability: 'Donor Availability',
    hospitalQuality: 'Hospital Quality',
    geographic: 'Geographic',
    healthDemographics: 'Health Demographics',
    policy: 'Policy',
    socioeconomic: 'Socioeconomic'
  };

  // Provenance cache: { signature: { provenance: [...], fetchedAt: timestamp } }
  var _cache = {};
  var _activeModal = null;

  // ── Helpers ───────────────────────────────────────────────────────────

  function _el(tag, className, textContent) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (textContent != null) node.textContent = textContent;
    return node;
  }

  function _appendSpans(parent, items) {
    // items: [[text, className], ...]
    items.forEach(function (it) {
      var span = _el('span', it[1] || null, it[0]);
      parent.appendChild(span);
      parent.appendChild(document.createTextNode(' '));
    });
  }

  function _fmt(n, places) {
    if (n == null || isNaN(n)) return '—';
    return Number(n).toFixed(places == null ? 2 : places);
  }

  function _signatureFor(formData) {
    // Lightweight cache key — captures the inputs that affect scoring
    var parts = [
      formData.organ, formData.bloodType, formData.age, formData.sex,
      formData.urgency, formData.cpra || '', formData.meld || '', formData.las || '',
      formData.insurance || '', formData.adjustForCauseOfDeath ? '1' : '0'
    ];
    if (formData.weights) {
      var keys = Object.keys(formData.weights).sort();
      keys.forEach(function (k) { parts.push(k + ':' + formData.weights[k].toFixed(3)); });
    }
    return parts.join('|');
  }

  // ── Modal lifecycle ───────────────────────────────────────────────────

  function _closeModal() {
    if (_activeModal && _activeModal.parentNode) {
      _activeModal.parentNode.removeChild(_activeModal);
    }
    _activeModal = null;
    document.removeEventListener('keydown', _onKeyDown);
  }

  function _onKeyDown(e) {
    if (e.key === 'Escape') _closeModal();
  }

  function _buildModalShell(centerName, centerState) {
    var modal = _el('div', 'city-modal explain-modal');
    var backdrop = _el('div', 'city-modal-backdrop');
    backdrop.addEventListener('click', _closeModal);
    modal.appendChild(backdrop);

    var content = _el('div', 'city-modal-content city-modal--wide');
    modal.appendChild(content);

    var header = _el('div', 'city-modal-header');
    var titleWrap = _el('div');
    titleWrap.appendChild(_el('div', 'explain-modal-subtitle', 'Score calculation details'));
    titleWrap.appendChild(_el('h2', null, centerName));
    if (centerState) {
      titleWrap.appendChild(_el('div', 'state', centerState));
    }
    header.appendChild(titleWrap);

    var closeBtn = _el('button', 'city-modal-close', '×');
    closeBtn.setAttribute('aria-label', 'Close');
    closeBtn.addEventListener('click', _closeModal);
    header.appendChild(closeBtn);
    content.appendChild(header);

    var body = _el('div', 'city-modal-body explain-modal-body');
    content.appendChild(body);

    return { modal: modal, body: body };
  }

  function _renderLoading(body) {
    while (body.firstChild) body.removeChild(body.firstChild);
    var loading = _el('div', 'explain-loading');
    loading.appendChild(_el('div', 'explain-loading-spinner'));
    loading.appendChild(_el('p', null,
      'Fetching calculation provenance for all 248 centers (~1-2s)…'
    ));
    body.appendChild(loading);
  }

  function _renderError(body, msg) {
    while (body.firstChild) body.removeChild(body.firstChild);
    var err = _el('div', 'explain-error');
    err.appendChild(_el('p', null, msg));
    body.appendChild(err);
  }

  // ── Provenance rendering ──────────────────────────────────────────────

  function _renderCategory(cat) {
    var section = _el('section', 'explain-cat');

    var header = _el('div', 'explain-cat-header');
    header.appendChild(_el('h3', 'explain-cat-name',
      BREAKDOWN_LABELS[cat.category] || cat.category
    ));
    var math = _el('div', 'explain-cat-math');
    _appendSpans(math, [
      [_fmt(cat.score, 1), 'explain-score'],
      ['×', 'explain-times'],
      [_fmt(cat.weight * 100, 0) + '%', 'explain-weight'],
      ['=', 'explain-equals'],
      [_fmt(cat.contribution, 2), 'explain-contrib']
    ]);
    header.appendChild(math);
    section.appendChild(header);

    if (cat.notes) {
      section.appendChild(_el('div', 'explain-cat-notes', cat.notes));
    }

    if (cat.components && cat.components.length > 0) {
      var table = _el('table', 'explain-components-table');
      var thead = _el('thead');
      var hRow = _el('tr');
      ['Component', 'Value', 'Weight', 'Contribution', 'Source'].forEach(function (h) {
        hRow.appendChild(_el('th', null, h));
      });
      thead.appendChild(hRow);
      table.appendChild(thead);

      var tbody = _el('tbody');
      cat.components.forEach(function (c, idx) {
        var tr = _el('tr', 'explain-comp-row');

        // Name cell with info toggle if details exist
        var nameCell = _el('td', 'explain-comp-name');
        nameCell.appendChild(document.createTextNode(c.name));
        var detailsTr = null;
        if (c.details) {
          var toggle = _el('button', 'explain-detail-toggle', 'ⓘ');
          toggle.setAttribute('type', 'button');
          toggle.setAttribute('aria-label', 'Show details');
          toggle.setAttribute('aria-expanded', 'false');
          toggle.addEventListener('click', function (e) {
            e.stopPropagation();
            if (!detailsTr) return;
            var isOpen = detailsTr.classList.toggle('explain-detail-open');
            toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
            toggle.textContent = isOpen ? '▾' : 'ⓘ';
          });
          nameCell.appendChild(toggle);
        }
        tr.appendChild(nameCell);

        tr.appendChild(_el('td', 'explain-comp-value', _fmt(c.value, 2)));
        tr.appendChild(_el('td', 'explain-comp-weight',
          c.weight_within_category === 1
            ? '—'
            : _fmt(c.weight_within_category * 100, 0) + '%'
        ));
        tr.appendChild(_el('td', 'explain-comp-contrib',
          c.weight_within_category === 1 ? '—' : _fmt(c.contribution, 2)
        ));
        tr.appendChild(_el('td', 'explain-comp-source', c.source));
        tbody.appendChild(tr);

        // Add hidden details row right after
        if (c.details) {
          detailsTr = _el('tr', 'explain-detail-row');
          var detailsTd = _el('td');
          detailsTd.setAttribute('colspan', '5');
          detailsTd.appendChild(_renderDetailsPanel(c.details));
          detailsTr.appendChild(detailsTd);
          tbody.appendChild(detailsTr);
        }
      });
      table.appendChild(tbody);
      section.appendChild(table);
    }

    return section;
  }

  function _renderDetailsPanel(details) {
    var panel = _el('div', 'explain-detail-panel');

    if (details.summary) {
      panel.appendChild(_el('p', 'explain-detail-summary', details.summary));
    }

    if (details.lookup_table && details.lookup_table.length > 0) {
      var ltCaption = _el('h5', 'explain-detail-section-title', 'Lookup table');
      panel.appendChild(ltCaption);
      var ltTable = _el('table', 'explain-detail-lookup');
      var ltThead = _el('thead');
      var ltHead = _el('tr');
      ['', 'Score', 'Note'].forEach(function (h) {
        ltHead.appendChild(_el('th', null, h));
      });
      ltThead.appendChild(ltHead);
      ltTable.appendChild(ltThead);
      var ltBody = _el('tbody');
      details.lookup_table.forEach(function (row) {
        var ltr = _el('tr');
        if (row.highlighted) ltr.classList.add('explain-lookup-match');
        ltr.appendChild(_el('td', 'explain-lookup-label', row.label));
        var valueText = (row.value == null) ? '' : String(row.value);
        ltr.appendChild(_el('td', 'explain-lookup-value', valueText));
        ltr.appendChild(_el('td', 'explain-lookup-note', row.note || ''));
        ltBody.appendChild(ltr);
      });
      ltTable.appendChild(ltBody);
      panel.appendChild(ltTable);
    }

    if (details.formula) {
      var fCaption = _el('h5', 'explain-detail-section-title', 'Formula');
      panel.appendChild(fCaption);
      var pre = _el('pre', 'explain-detail-formula');
      pre.textContent = details.formula;
      panel.appendChild(pre);
    }

    if (details.notes) {
      var nCaption = _el('h5', 'explain-detail-section-title', 'Notes');
      panel.appendChild(nCaption);
      panel.appendChild(_el('p', 'explain-detail-notes', details.notes));
    }

    return panel;
  }

  function _renderProvenance(body, prov) {
    while (body.firstChild) body.removeChild(body.firstChild);

    // Summary header
    var summary = _el('div', 'explain-summary');
    var totalRow = _el('div', 'explain-summary-total');
    totalRow.appendChild(_el('span', 'explain-total-label', 'Total score'));
    totalRow.appendChild(_el('span', 'explain-total-value', _fmt(prov.total, 2)));
    totalRow.appendChild(_el('span', 'explain-total-max', '/ 100'));
    summary.appendChild(totalRow);
    summary.appendChild(_el('p', 'explain-summary-formula',
      'Total = Σ (category_score × category_weight), clamped to [0, 100]'
    ));
    body.appendChild(summary);

    // Categories
    prov.categories.forEach(function (cat) {
      body.appendChild(_renderCategory(cat));
    });

    // Data sources footer
    var footer = _el('div', 'explain-sources');
    footer.appendChild(_el('h4', null, 'Data sources consulted'));
    var srcList = _el('ul', 'explain-sources-list');
    prov.data_sources.forEach(function (s) {
      srcList.appendChild(_el('li', null, s));
    });
    footer.appendChild(srcList);
    body.appendChild(footer);

    // Reproducibility note
    var repro = _el('p', 'explain-repro-note');
    var strong = _el('strong', null, 'Note: ');
    repro.appendChild(strong);
    repro.appendChild(document.createTextNode(
      'all calculations are deterministic given the same patient inputs, ' +
      'weights, and data file versions. This trail can be regenerated at any time via '
    ));
    repro.appendChild(_el('code', null, 'POST /score/explain'));
    repro.appendChild(document.createTextNode('.'));
    body.appendChild(repro);
  }

  // ── Public entry point ────────────────────────────────────────────────

  async function showForCenter(centerCode, centerName, centerState, formData) {
    _closeModal();

    var shell = _buildModalShell(centerName, centerState);
    _activeModal = shell.modal;
    document.body.appendChild(shell.modal);
    document.addEventListener('keydown', _onKeyDown);

    var signature = _signatureFor(formData);
    var cached = _cache[signature];

    function findCenter(provArray) {
      for (var i = 0; i < provArray.length; i++) {
        if (provArray[i].code === centerCode) return provArray[i];
      }
      return null;
    }

    if (cached) {
      var p = findCenter(cached.provenance);
      if (p) {
        _renderProvenance(shell.body, p);
        return;
      }
    }

    if (!window.TransPlanAPI || typeof window.TransPlanAPI.scoreExplain !== 'function') {
      _renderError(shell.body,
        'Calculation details require the backend API. ' +
        'Run TransPlan locally with the FastAPI server to enable this feature.'
      );
      return;
    }

    _renderLoading(shell.body);
    try {
      var result = await window.TransPlanAPI.scoreExplain(formData, 248);
      if (!result || !result.provenance) {
        _renderError(shell.body,
          'Backend returned no provenance. The /score/explain endpoint may not be available ' +
          '(running an older deployment?).'
        );
        return;
      }
      _cache[signature] = { provenance: result.provenance, fetchedAt: Date.now() };
      var prov = findCenter(result.provenance);
      if (!prov) {
        _renderError(shell.body,
          'No provenance available for center ' + centerCode + '. ' +
          'It may not perform the selected organ.'
        );
        return;
      }
      _renderProvenance(shell.body, prov);
    } catch (err) {
      console.error('explain-modal fetch error:', err);
      _renderError(shell.body, 'Failed to load calculation details: ' + (err.message || err));
    }
  }

  function clearCache() {
    _cache = {};
  }

  // Expose
  window.ExplainModal = {
    showForCenter: showForCenter,
    clearCache: clearCache
  };
})();
