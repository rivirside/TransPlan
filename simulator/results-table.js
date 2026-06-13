/**
 * simulator/results-table.js — Sortable results table with inline row expansion.
 *
 * Replaces city cards + results table from the old script.js.
 * Clicking a row expands an inline detail panel (no modal).
 *
 * Exports window.SimResultsTable with:
 *   render(container, results, options)
 *   sort(column, direction)
 *   getSelectedCenters()
 */
(function () {
  'use strict';

  // ── Constants ──────────────────────────────────────────────────────────────

  var MAX_COMPARE = 3;

  /** Column definitions: key, label, sortable, requiresSim, requiresHome */
  var COLUMNS = [
    { key: 'rank',       label: '#',           sortable: true,  requiresSim: false, requiresHome: false },
    { key: 'center',     label: 'Center',      sortable: true,  requiresSim: false, requiresHome: false },
    { key: 'score',      label: 'Score',       sortable: true,  requiresSim: false, requiresHome: false },
    { key: 'p24',        label: 'P(24mo)',     sortable: true,  requiresSim: true,  requiresHome: false },
    { key: 'medianWait', label: 'Median Wait', sortable: true,  requiresSim: true,  requiresHome: false },
    { key: 'distance',   label: 'Distance',    sortable: true,  requiresSim: false, requiresHome: true  },
    { key: 'compare',    label: '',             sortable: false, requiresSim: false, requiresHome: false }
  ];

  /** Score breakdown category labels (matches algorithm.js CATEGORY_LABELS) */
  var BREAKDOWN_LABELS = {
    medicalCompatibility: 'Medical Compatibility',
    waitTime:             'Wait Time',
    donorAvailability:    'Donor Availability',
    hospitalQuality:      'Hospital Quality',
    geographic:           'Geographic',
    healthDemographics:   'Health Demographics',
    policy:               'Policy',
    socioeconomic:        'Socioeconomic'
  };

  // ── Module state ───────────────────────────────────────────────────────────

  var _container = null;
  var _results = [];           // merged result rows
  var _options = {};           // { homeLocation }
  var _sortKey = 'rank';
  var _sortAsc = true;
  var _expandedCode = null;    // currently expanded row center code
  var _selectedCodes = [];     // compare selection (max 3)
  var _hasSim = false;
  var _hasHome = false;
  var _tableEl = null;
  var _tbodyEl = null;
  var _paginationEl = null;
  var _sorted = [];            // last sorted result array (for paging)
  var _page = 0;               // current 0-based page
  var _pageSize = 25;          // rows per page; 0 = show all (#221)

  // ── Public API ─────────────────────────────────────────────────────────────

  /**
   * Render the full results table into a container element.
   * @param {HTMLElement} container - Target element to render into
   * @param {Object} results - { scores, simulation, homeLocation }
   * @param {Object} [options] - Reserved for future use
   */
  function render(container, results, options) {
    _container = container;
    _options = options || {};
    _results = _mergeResults(results);
    _hasSim = !!(results.simulation && results.simulation.length > 0);
    _hasHome = !!(results.homeLocation && results.homeLocation.lat != null);
    if (_hasHome) {
      _options.homeLocation = results.homeLocation;
    }
    if (results.formData) {
      _options.formData = results.formData;
    }
    _expandedCode = null;

    // Clear container safely
    _container.textContent = '';

    // Build wrapper
    var wrapper = _createElement('div', 'results-table-wrapper');

    // Build table
    _tableEl = _createElement('table', 'results-table');
    _tableEl.setAttribute('role', 'grid');

    // Build thead
    var thead = _createElement('thead');
    var headerRow = _createElement('tr');

    _getVisibleColumns().forEach(function (col) {
      var th = _createElement('th');
      th.textContent = col.label;
      if (col.sortable) {
        th.setAttribute('data-sort', col.key);
        th.setAttribute('role', 'columnheader');
        th.setAttribute('aria-sort', 'none');
        th.style.cursor = 'pointer';

        var arrow = _createElement('span', 'sort-arrow');
        arrow.textContent = ' \u25B2';
        th.appendChild(arrow);

        th.addEventListener('click', function () {
          _handleHeaderClick(col.key);
        });
      }
      if (col.key === 'compare') {
        th.style.width = '40px';
        th.style.textAlign = 'center';
      }
      headerRow.appendChild(th);
    });

    thead.appendChild(headerRow);
    _tableEl.appendChild(thead);

    // Build tbody
    _tbodyEl = _createElement('tbody');
    _tableEl.appendChild(_tbodyEl);

    wrapper.appendChild(_tableEl);
    _container.appendChild(wrapper);

    // Pagination controls (rendered/updated by _renderPage) (#221)
    _paginationEl = _createElement('div', 'results-pagination');
    _container.appendChild(_paginationEl);

    // Initial sort and render rows
    _sortAndRender();
  }

  /**
   * Sort the table by a column.
   * @param {string} column - Column key
   * @param {string} [direction] - 'asc' or 'desc'; toggles if omitted
   */
  function sort(column, direction) {
    if (direction) {
      _sortKey = column;
      _sortAsc = direction === 'asc';
    } else {
      _handleHeaderClick(column);
      return;
    }
    _sortAndRender();
  }

  /**
   * Get array of selected center codes for comparison.
   * @returns {string[]}
   */
  function getSelectedCenters() {
    return _selectedCodes.slice();
  }

  // ── Data merging ───────────────────────────────────────────────────────────

  /**
   * Merge scores and simulation arrays into a unified row array.
   * Each row has all fields needed for display and sorting.
   */
  function _mergeResults(results) {
    var scores = results.scores || [];
    var simulation = results.simulation || [];

    // Build simulation lookup by center_code
    var simLookup = {};
    simulation.forEach(function (s) {
      var key = s.center_code || s.city;
      simLookup[key] = s;
    });

    return scores.map(function (sc) {
      var sim = simLookup[sc.code] || simLookup[sc.name] || null;
      return {
        code:     sc.code,
        name:     sc.name,
        state:    sc.state,
        stateAbbr: sc.state_abbr || '',
        lat:      sc.lat,
        lon:      sc.lon,
        score:    sc.total,
        breakdown: sc.breakdown || null,
        rank:     sc.rank,
        // Simulation fields (null if no sim data)
        p24:           sim ? sim.p_transplant_24mo : null,
        p6:            sim ? (sim.p_transplant_6mo || null) : null,
        p12:           sim ? (sim.p_transplant_12mo || null) : null,
        p36:           sim ? (sim.p_transplant_36mo || null) : null,
        ci95:          sim ? sim.confidence_interval_95 : null,
        medianWait:    sim ? sim.median_wait_months : null,
        competingRisks: sim ? sim.competing_risks : null,
        outcomes:      sim ? sim.outcomes : null,
        trends:        sim ? sim.trends : null
      };
    });
  }

  // ── Column helpers ─────────────────────────────────────────────────────────

  /** Return only the columns that should be visible given current data. */
  function _getVisibleColumns() {
    return COLUMNS.filter(function (col) {
      if (col.requiresSim && !_hasSim) return false;
      if (col.requiresHome && !_hasHome) return false;
      return true;
    });
  }

  // ── Sorting ────────────────────────────────────────────────────────────────

  function _handleHeaderClick(key) {
    if (_sortKey === key) {
      _sortAsc = !_sortAsc;
    } else {
      _sortKey = key;
      // Default ascending for most columns
      _sortAsc = true;
    }
    _sortAndRender();
  }

  /** Sort _results in place and re-render tbody rows. */
  function _sortAndRender() {
    var sorted = _results.slice();
    sorted.sort(function (a, b) {
      var va, vb;
      switch (_sortKey) {
        case 'rank':
          // Lower rank number = better = higher score
          va = a.rank; vb = b.rank;
          return _sortAsc ? va - vb : vb - va;

        case 'center':
          va = (a.name || '').toLowerCase();
          vb = (b.name || '').toLowerCase();
          return _sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);

        case 'score':
          va = a.score != null ? a.score : -1;
          vb = b.score != null ? b.score : -1;
          return _sortAsc ? va - vb : vb - va;

        case 'p24':
          va = a.p24 != null ? a.p24 : -1;
          vb = b.p24 != null ? b.p24 : -1;
          return _sortAsc ? va - vb : vb - va;

        case 'medianWait':
          // Sort by raw numeric months — fixes #208 item 1
          va = a.medianWait != null ? a.medianWait : Infinity;
          vb = b.medianWait != null ? b.medianWait : Infinity;
          return _sortAsc ? va - vb : vb - va;

        case 'distance':
          va = _computeDistance(a);
          vb = _computeDistance(b);
          return _sortAsc ? va - vb : vb - va;

        default:
          return 0;
      }
    });

    _sorted = sorted;
    _page = 0;            // reset to first page on (re)sort
    _renderPage();
    _updateSortIndicators();
  }

  /** Render the current page of sorted rows + the pagination controls (#221). */
  function _renderPage() {
    var total = _sorted.length;
    var pageSize = (_pageSize && _pageSize > 0) ? _pageSize : total;
    var pageCount = Math.max(1, Math.ceil(total / pageSize));
    if (_page >= pageCount) _page = pageCount - 1;
    if (_page < 0) _page = 0;
    var start = _page * pageSize;
    _renderRows(_sorted.slice(start, start + pageSize));
    _renderPaginationControls(total, pageSize, pageCount, start);
  }

  /** Build the prev/next/show-all pagination bar. */
  function _renderPaginationControls(total, pageSize, pageCount, start) {
    if (!_paginationEl) return;
    _paginationEl.textContent = '';
    // Nothing to page through — show a simple count.
    if (total <= 25 && _pageSize !== 0) {
      var count = _createElement('span', 'results-pagination-info');
      count.textContent = total + (total === 1 ? ' center' : ' centers');
      _paginationEl.appendChild(count);
      return;
    }

    var showingAll = (_pageSize === 0) || (pageCount === 1);
    var info = _createElement('span', 'results-pagination-info');
    if (showingAll) {
      info.textContent = 'Showing all ' + total + ' centers';
    } else {
      var end = Math.min(start + pageSize, total);
      info.textContent = 'Showing ' + (start + 1) + '–' + end + ' of ' + total +
        ' centers · page ' + (_page + 1) + ' of ' + pageCount;
    }
    _paginationEl.appendChild(info);

    if (!showingAll) {
      var prev = _createElement('button', 'results-pagination-btn');
      prev.type = 'button';
      prev.textContent = '‹ Prev';
      prev.disabled = _page === 0;
      prev.addEventListener('click', function () { _page--; _renderPage(); });
      _paginationEl.appendChild(prev);

      var next = _createElement('button', 'results-pagination-btn');
      next.type = 'button';
      next.textContent = 'Next ›';
      next.disabled = _page >= pageCount - 1;
      next.addEventListener('click', function () { _page++; _renderPage(); });
      _paginationEl.appendChild(next);
    }

    // Show-all / paginate toggle
    var toggle = _createElement('button', 'results-pagination-btn results-pagination-toggle');
    toggle.type = 'button';
    toggle.textContent = (_pageSize === 0) ? 'Paginate' : 'Show all';
    toggle.addEventListener('click', function () {
      _pageSize = (_pageSize === 0) ? 25 : 0;
      _page = 0;
      _renderPage();
    });
    _paginationEl.appendChild(toggle);
  }

  /** Compute distance in miles from homeLocation to a center. */
  function _computeDistance(row) {
    if (!_options.homeLocation || row.lat == null || row.lon == null) return 99999;
    if (window.TransPlanGeo && window.TransPlanGeo.haversineMiles) {
      return window.TransPlanGeo.haversineMiles(
        _options.homeLocation.lat, _options.homeLocation.lon,
        row.lat, row.lon
      );
    }
    return 99999;
  }

  /** Update header sort arrow indicators. */
  function _updateSortIndicators() {
    if (!_tableEl) return;
    var ths = _tableEl.querySelectorAll('thead th[data-sort]');
    for (var i = 0; i < ths.length; i++) {
      var th = ths[i];
      var key = th.getAttribute('data-sort');
      var arrow = th.querySelector('.sort-arrow');
      if (key === _sortKey) {
        th.classList.add('sort-active');
        if (arrow) arrow.textContent = _sortAsc ? ' \u25B2' : ' \u25BC';
        th.setAttribute('aria-sort', _sortAsc ? 'ascending' : 'descending');
      } else {
        th.classList.remove('sort-active');
        if (arrow) arrow.textContent = ' \u25B2';
        th.setAttribute('aria-sort', 'none');
      }
    }
  }

  // ── Row rendering ──────────────────────────────────────────────────────────

  /** Render all table body rows (data rows + any expanded detail row). */
  function _renderRows(sorted) {
    _tbodyEl.textContent = '';
    var visibleCols = _getVisibleColumns();

    sorted.forEach(function (row) {
      var tr = _buildDataRow(row, visibleCols);
      _tbodyEl.appendChild(tr);

      // If this row is expanded, insert the detail row right after
      if (_expandedCode === row.code) {
        var detailTr = _buildDetailRow(row, visibleCols.length);
        _tbodyEl.appendChild(detailTr);
      }
    });
  }

  /** Build a single data row <tr>. */
  function _buildDataRow(row, visibleCols) {
    var tr = _createElement('tr');
    tr.setAttribute('data-center', row.code);
    if (_expandedCode === row.code) {
      tr.classList.add('rt-row-expanded');
    }

    visibleCols.forEach(function (col) {
      var td = _createElement('td');

      switch (col.key) {
        case 'rank':
          td.className = 'rank-cell';
          if (row.rank <= 3) td.classList.add('rank-' + row.rank);
          td.textContent = row.rank;
          break;

        case 'center':
          td.className = 'city-cell';
          td.textContent = row.name;
          var stateSpan = _createElement('span', 'city-state');
          stateSpan.textContent = row.stateAbbr || row.state;
          td.appendChild(stateSpan);
          break;

        case 'score':
          td.className = 'score-cell metric-cell';
          if (row.score != null) {
            var scoreVal = row.score;
            td.classList.add(_scoreClass(scoreVal));
            // Score bar container
            var barWrap = _createElement('span', 'rt-score-bar-wrap');
            var barFill = _createElement('span', 'rt-score-bar-fill');
            barFill.style.width = Math.min(100, Math.max(0, scoreVal)) + '%';
            barWrap.appendChild(barFill);
            // Score number
            var scoreNum = _createElement('span', 'rt-score-num');
            scoreNum.textContent = scoreVal.toFixed(1);
            td.textContent = '';
            td.appendChild(scoreNum);
            td.appendChild(barWrap);
          } else {
            td.textContent = '\u2014';
          }
          break;

        case 'p24':
          td.className = 'metric-cell';
          if (row.p24 != null) {
            td.classList.add(_probClass(row.p24));
            td.textContent = _formatPct(row.p24);
            td.setAttribute('data-sort-value', row.p24);
          } else {
            td.textContent = '\u2014';
          }
          break;

        case 'medianWait':
          td.className = 'metric-cell';
          if (row.medianWait != null) {
            // Store raw months as data attribute for correct sorting (#208 fix)
            td.setAttribute('data-sort-value', row.medianWait);
            td.textContent = _formatWait(row.medianWait);
            td.classList.add(_waitClass(row.medianWait));
          } else {
            td.textContent = '\u2014';
          }
          break;

        case 'distance':
          td.className = 'metric-cell';
          var dist = _computeDistance(row);
          if (dist < 99999) {
            var distRounded = Math.round(dist);
            td.setAttribute('data-sort-value', distRounded);
            td.textContent = distRounded + ' mi';
            td.classList.add(distRounded < 200 ? 'good' : distRounded < 500 ? 'moderate' : 'poor');
          } else {
            td.textContent = '\u2014';
          }
          break;

        case 'compare':
          td.className = 'rt-compare-cell';
          td.style.textAlign = 'center';
          var label = _createElement('label', 'compare-check');
          var cb = _createElement('input');
          cb.type = 'checkbox';
          cb.checked = _selectedCodes.indexOf(row.code) !== -1;
          cb.setAttribute('aria-label', 'Compare ' + row.name);
          cb.addEventListener('change', function (e) {
            e.stopPropagation();
            _handleCompareToggle(row.code, cb);
          });
          // Prevent row click when clicking checkbox
          label.addEventListener('click', function (e) {
            e.stopPropagation();
          });
          label.appendChild(cb);
          td.appendChild(label);
          break;
      }

      tr.appendChild(td);
    });

    // Row click → expand/collapse
    tr.addEventListener('click', function () {
      _toggleExpansion(row.code);
    });

    // Row hover → dispatch custom event for map highlighting
    tr.addEventListener('mouseenter', function () {
      _dispatchHover(row.code);
    });
    tr.addEventListener('mouseleave', function () {
      _dispatchHover(null);
    });

    return tr;
  }

  // ── Inline expansion (detail panel) ────────────────────────────────────────

  /** Toggle row expansion. Only one row expanded at a time. */
  function _toggleExpansion(code) {
    if (_expandedCode === code) {
      _expandedCode = null;
    } else {
      _expandedCode = code;
    }
    _sortAndRender();
  }

  /** Build the expanded detail <tr> that spans all columns. */
  function _buildDetailRow(row, colSpan) {
    var tr = _createElement('tr', 'rt-detail-row');
    var td = _createElement('td');
    td.setAttribute('colspan', colSpan);

    var panel = _createElement('div', 'rt-detail-panel');

    // Close button
    var closeBtn = _createElement('button', 'rt-detail-close');
    closeBtn.textContent = '\u00D7';
    closeBtn.setAttribute('aria-label', 'Close details');
    closeBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      _expandedCode = null;
      _sortAndRender();
    });
    panel.appendChild(closeBtn);

    // Header
    var header = _createElement('div', 'rt-detail-header');
    var title = _createElement('h3', 'rt-detail-title');
    title.textContent = row.name;
    header.appendChild(title);
    if (row.stateAbbr || row.state) {
      var stateLabel = _createElement('span', 'rt-detail-state');
      stateLabel.textContent = row.state + (row.stateAbbr ? ' (' + row.stateAbbr + ')' : '');
      header.appendChild(stateLabel);
    }
    if (row.score != null) {
      var scoreBadge = _createElement('span', 'rt-detail-score');
      scoreBadge.textContent = row.score.toFixed(1) + ' / 100';
      header.appendChild(scoreBadge);
    }

    // "Show calculations" button — opens provenance modal
    if (window.ExplainModal && _options.formData) {
      var explainBtn = _createElement('button', 'rt-detail-explain-btn');
      explainBtn.textContent = 'Show calculations';
      explainBtn.setAttribute('type', 'button');
      explainBtn.setAttribute(
        'title',
        'See exactly how this score was computed: inputs, weights, and data sources'
      );
      explainBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        window.ExplainModal.showForCenter(
          row.code,
          row.name,
          row.state + (row.stateAbbr ? ' (' + row.stateAbbr + ')' : ''),
          _options.formData
        );
      });
      header.appendChild(explainBtn);
    }

    panel.appendChild(header);

    // Content grid: left = breakdown, right = simulation data
    var grid = _createElement('div', 'rt-detail-grid');

    // ── Left column: Score breakdown ──
    if (row.breakdown) {
      var breakdownSection = _createElement('div', 'rt-detail-section');
      var breakdownTitle = _createElement('h4', 'rt-detail-section-title');
      breakdownTitle.textContent = 'Score Breakdown';
      breakdownSection.appendChild(breakdownTitle);

      var breakdownKeys = Object.keys(BREAKDOWN_LABELS);
      breakdownKeys.forEach(function (key) {
        var raw = row.breakdown[key] || 0;
        var barRow = _createElement('div', 'rt-breakdown-row');

        var labelSpan = _createElement('span', 'rt-breakdown-label');
        labelSpan.textContent = BREAKDOWN_LABELS[key];
        barRow.appendChild(labelSpan);

        var valueSpan = _createElement('span', 'rt-breakdown-value');
        valueSpan.textContent = raw.toFixed(1);
        barRow.appendChild(valueSpan);

        var barTrack = _createElement('div', 'rt-breakdown-bar');
        var barFill = _createElement('div', 'rt-breakdown-bar-fill');
        barFill.style.width = Math.min(100, Math.max(0, raw)) + '%';
        // Color the bar based on score
        if (raw >= 70) {
          barFill.classList.add('rt-bar-good');
        } else if (raw >= 40) {
          barFill.classList.add('rt-bar-moderate');
        } else {
          barFill.classList.add('rt-bar-poor');
        }
        barTrack.appendChild(barFill);
        barRow.appendChild(barTrack);

        breakdownSection.appendChild(barRow);
      });

      grid.appendChild(breakdownSection);
    }

    // ── Right column: Simulation data ──
    if (row.p24 != null) {
      var simSection = _createElement('div', 'rt-detail-section');

      // Probability details
      var probTitle = _createElement('h4', 'rt-detail-section-title');
      probTitle.textContent = 'Transplant Probability';
      simSection.appendChild(probTitle);

      var probGrid = _createElement('div', 'rt-prob-grid');
      var timepoints = [
        ['6 mo',  row.p6],
        ['12 mo', row.p12],
        ['24 mo', row.p24],
        ['36 mo', row.p36]
      ];
      timepoints.forEach(function (tp) {
        if (tp[1] == null) return;
        var item = _createElement('div', 'rt-prob-item');
        var label = _createElement('div', 'rt-prob-label');
        label.textContent = tp[0];
        item.appendChild(label);
        var value = _createElement('div', 'rt-prob-value');
        value.textContent = _formatPct(tp[1]);
        value.classList.add(_probClass(tp[1]));
        item.appendChild(value);
        probGrid.appendChild(item);
      });

      // Median wait
      if (row.medianWait != null) {
        var waitItem = _createElement('div', 'rt-prob-item');
        var waitLabel = _createElement('div', 'rt-prob-label');
        waitLabel.textContent = 'Median Wait';
        waitItem.appendChild(waitLabel);
        var waitValue = _createElement('div', 'rt-prob-value');
        waitValue.textContent = _formatWait(row.medianWait);
        waitItem.appendChild(waitValue);
        probGrid.appendChild(waitItem);
      }

      simSection.appendChild(probGrid);

      // Confidence interval
      if (row.ci95 && row.ci95.length === 2) {
        var ciDiv = _createElement('div', 'rt-ci-text');
        ciDiv.textContent = '95% CI at 24 mo: ' + _formatPct(row.ci95[0]) + ' \u2013 ' + _formatPct(row.ci95[1]);
        simSection.appendChild(ciDiv);
      }

      // Competing risks bar
      if (row.competingRisks) {
        var riskWrapper = _createElement('div', 'rt-risk-section');
        var riskTitle = _createElement('h4', 'rt-detail-section-title');
        riskTitle.textContent = '24-Month Waitlist Outcomes';
        riskWrapper.appendChild(riskTitle);
        riskWrapper.appendChild(_buildCompetingRisksBar(row.competingRisks));
        simSection.appendChild(riskWrapper);
      }

      // Post-transplant outcomes
      if (row.outcomes) {
        var outcomeSection = _createElement('div', 'rt-outcome-section');
        var outcomeTitle = _createElement('h4', 'rt-detail-section-title');
        outcomeTitle.textContent = 'Post-Transplant Outcomes';
        outcomeSection.appendChild(outcomeTitle);
        outcomeSection.appendChild(_buildOutcomes(row.outcomes));
        simSection.appendChild(outcomeSection);
      }

      grid.appendChild(simSection);
    }

    panel.appendChild(grid);
    td.appendChild(panel);
    tr.appendChild(td);

    // Prevent row click on the detail row itself
    tr.addEventListener('click', function (e) {
      e.stopPropagation();
    });

    return tr;
  }

  // ── Competing risks bar ────────────────────────────────────────────────────

  function _buildCompetingRisksBar(cr) {
    var frag = document.createDocumentFragment();

    var bar = _createElement('div', 'prob-risks');
    var segments = [
      { value: cr.p_transplant_24mo || 0, color: '#27ae60' },
      { value: cr.p_still_waiting_24mo || 0, color: '#bdc3c7' },
      { value: cr.p_delisting_24mo || 0, color: '#e67e22' },
      { value: cr.p_mortality_24mo || 0, color: '#e74c3c' }
    ];

    segments.forEach(function (seg) {
      var div = _createElement('div');
      div.style.width = (seg.value * 100).toFixed(1) + '%';
      div.style.background = seg.color;
      div.style.height = '100%';
      div.style.borderRadius = 'var(--radius-full)';
      bar.appendChild(div);
    });
    frag.appendChild(bar);

    var legend = _createElement('div', 'prob-risk-legend');
    var legendItems = [
      ['risk-transplant', 'Transplant', cr.p_transplant_24mo || 0],
      ['risk-waiting',    'Waiting',    cr.p_still_waiting_24mo || 0],
      ['risk-delisted',   'Delisted',   cr.p_delisting_24mo || 0],
      ['risk-mortality',  'Mortality',  cr.p_mortality_24mo || 0]
    ];
    legendItems.forEach(function (item) {
      var span = _createElement('span', item[0]);
      span.textContent = item[1] + ' ' + _formatPct(item[2]);
      legend.appendChild(span);
    });
    frag.appendChild(legend);

    return frag;
  }

  // ── Outcomes section ───────────────────────────────────────────────────────

  function _buildOutcomes(outcomes) {
    var grid = _createElement('div', 'rt-outcome-grid');
    var items = [];

    if (outcomes.graft_survival_1yr != null) {
      items.push(['1yr Graft', _formatPct(outcomes.graft_survival_1yr)]);
    }
    if (outcomes.graft_survival_3yr != null) {
      items.push(['3yr Graft', _formatPct(outcomes.graft_survival_3yr)]);
    }
    if (outcomes.patient_survival_1yr != null) {
      items.push(['1yr Patient', _formatPct(outcomes.patient_survival_1yr)]);
    }
    if (outcomes.patient_survival_3yr != null) {
      items.push(['3yr Patient', _formatPct(outcomes.patient_survival_3yr)]);
    }
    if (outcomes.compound_success != null) {
      items.push(['Overall', _formatPct(outcomes.compound_success)]);
    }

    items.forEach(function (item) {
      var div = _createElement('div', 'rt-outcome-item');
      var label = _createElement('div', 'rt-outcome-label');
      label.textContent = item[0];
      div.appendChild(label);
      var value = _createElement('div', 'rt-outcome-value');
      value.textContent = item[1];
      div.appendChild(value);
      grid.appendChild(div);
    });

    return grid;
  }

  // ── Compare checkbox ───────────────────────────────────────────────────────

  function _handleCompareToggle(code, checkbox) {
    var idx = _selectedCodes.indexOf(code);
    if (checkbox.checked) {
      if (idx === -1) {
        if (_selectedCodes.length >= MAX_COMPARE) {
          // At max — uncheck and don't add
          checkbox.checked = false;
          return;
        }
        _selectedCodes.push(code);
      }
    } else {
      if (idx !== -1) {
        _selectedCodes.splice(idx, 1);
      }
    }
  }

  // ── Hover event dispatch ───────────────────────────────────────────────────

  function _dispatchHover(code) {
    var event;
    try {
      event = new CustomEvent('sim-center-hover', { detail: { code: code }, bubbles: true });
    } catch (e) {
      // IE11 fallback
      event = document.createEvent('CustomEvent');
      event.initCustomEvent('sim-center-hover', true, true, { code: code });
    }
    document.dispatchEvent(event);
  }

  // ── Formatting helpers ─────────────────────────────────────────────────────

  /** Format a probability (0-1) as a percentage string. */
  function _formatPct(v) {
    if (v == null) return '\u2014';
    return (v * 100).toFixed(1) + '%';
  }

  /**
   * Format a median wait time (in months) for display.
   * Converts to years if >= 24 months, otherwise shows months.
   */
  function _formatWait(months) {
    if (months == null) return '\u2014';
    if (months >= 24) {
      return (months / 12).toFixed(1) + ' yr';
    }
    return months.toFixed(1) + ' mo';
  }

  /** Return CSS class based on a score value (0-100). */
  function _scoreClass(val) {
    if (val >= 80) return 'good';
    if (val >= 60) return 'moderate';
    return 'poor';
  }

  /** Return CSS class for a probability value (0-1). */
  function _probClass(v) {
    if (v >= 0.5) return 'good';
    if (v >= 0.2) return 'moderate';
    return 'poor';
  }

  /** Return CSS class for a wait time in months. */
  function _waitClass(months) {
    if (months <= 6) return 'good';
    if (months <= 18) return 'moderate';
    return 'poor';
  }

  // ── DOM helpers ────────────────────────────────────────────────────────────

  /**
   * Safe element creation (no innerHTML with dynamic data).
   * @param {string} tag - Element tag name
   * @param {string} [className] - CSS class name(s)
   * @returns {HTMLElement}
   */
  function _createElement(tag, className) {
    var el = document.createElement(tag);
    if (className) el.className = className;
    return el;
  }

  // ── Expose public API ──────────────────────────────────────────────────────

  window.SimResultsTable = {
    render: render,
    sort: sort,
    getSelectedCenters: getSelectedCenters
  };

})();
