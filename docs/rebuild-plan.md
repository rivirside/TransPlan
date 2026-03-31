# TransPlan Full Rebuild Plan

## Progress Summary (Updated March 30, 2026)

| Phase | Status | Commit | Notes |
|-------|--------|--------|-------|
| Phase 0: Seed & Reproducibility | ✅ Complete | `a75dd72` | Seed support in all simulation endpoints, RunArtifact export, frontend seed/export |
| Phase 1: Nav Restructure | ✅ Complete | `6749b10` | "For Patients" / "For Professionals" dropdowns, old URLs redirect |
| Phase 2: Simulator Rebuild | ✅ Complete | `6f99f07`, `792e1da`, `840e415` | 6 modules (map, tier-panel, form-helpers, results, results-table, index.js), simulator.html rewritten, scoring.py NameError fixed, DOMContentLoaded timing fixed |
| Phase 3: Page Merges | 🔲 Next | — | Centers (3→1), Explorer (2→1) |
| Phase 4: Model Validation | 🔲 Pending | — | New validation tool (7 sections) |
| Phase 5: Inter-tool Linking | 🔲 Pending | — | URL params + continue buttons (partially done in Phase 2) |
| Phase 6: Tier System | 🔲 Pending | — | Hide vs disable unavailable features |
| Phase 7: Cleanup & Polish | 🔲 Pending | — | Delete script.js, old pages, final QA |

## Context

TransPlan is a transplant center analysis tool (transplant.today) with a Python/FastAPI backend and vanilla JS frontend on Vercel. After 7 phases of development, the project needs a structural overhaul:

1. **Audience separation**: Patients get resources + data browsing; researchers get simulation tools. Not clinically validated yet.
2. **Simulator is broken**: 4889-line `script.js` monolith doing everything. Duplicates features that already have standalone pages.
3. **No reproducibility**: No seed parameter anywhere. Can't reproduce runs for validation or publication.
4. **No model validation tool**: Missing cross-engine comparison, temporal train/test, convergence diagnostics.
5. **Redundant pages**: Find Centers, Center Explorer, Wait Estimator overlap. Data Explorer and Spatial overlap.

---

## Phase 0: Seed Support & Reproducibility ✅ COMPLETE

**Why first:** Every subsequent phase depends on deterministic results.

### 0.1 Backend: Add `seed` to all simulation services

**`backend/models/schemas.py`**
- Add to PatientProfile or as standalone query params:
  - `seed: Optional[int] = Field(None, ge=0, le=2147483647)`
- Add to all result schemas (SimulationResult, SensitivityResult, EquityAnalysisResult, WhatIfResult, PolicyScenarioResult):
  - `seed_used: int`

**`backend/services/monte_carlo.py`**
- Add `seed: int | None = None` param to `simulate()`
- Line ~231: `seed = seed if seed is not None else int(np.random.default_rng().integers(0, 2**31)); rng = np.random.default_rng(seed)`
- Thread seed to `_bootstrap_ci()` (line ~192) — currently creates its own unseeded RNG
- Return `seed_used` in SimulationResult

**`backend/services/sensitivity.py`**
- Add `seed` param to `compute_sensitivity()`
- Line 109: use `np.random.default_rng(seed)` instead of unseeded
- Derive child seeds for each parameter sweep: `seed + i`

**`backend/services/equity.py`** — Add seed, thread to simulate calls
**`backend/services/what_if.py`** — Add seed, thread to simulate calls
**`backend/services/cross_validation.py`** — Add seed, thread child seeds to each engine
**`backend/services/brier_score.py`** — Add seed, thread to simulate call at line ~113

**All routers** (simulate.py, sensitivity.py, equity.py, what_if.py):
- Add `seed: int = Query(default=None, ge=0, le=2147483647)` query parameter
- Pass through to service, include `seed_used` in response

### 0.2 Backend: Export artifact schema

**New file: `backend/models/export_artifact.py`**
```python
class RunArtifact(BaseModel):
    version: str          # "2.0.0"
    tool: str             # "simulator" | "sensitivity" | "equity" | "scenarios" | "validation"
    timestamp: str        # ISO 8601
    seed_used: int
    patient: PatientProfile
    parameters: dict      # tool-specific (iterations, copula_theta, etc.)
    results: dict         # full result payload
    tier: str             # "web" | "local"
```

### 0.3 Frontend: Seed & export support

**`api-client.js`** — Add `seed` param to all simulation methods
**`export-handler.js`** — Add `exportRunArtifact(toolName, params, results, seedUsed)` function

### 0.4 Verification
- `POST /simulate` with `seed=42` twice → identical responses
- `seed_used` returned in all simulation responses
- Export artifact downloads with seed included

---

## Phase 1: Navigation Restructure ✅ COMPLETE

### 1.1 Rewrite `components/site-chrome.js`

**Current nav:** Simulator | Tools | Resources | Analysis | Data | Docs

**New nav:**
```
Logo | For Patients (dropdown) | For Professionals (dropdown)
```

**For Patients:**
- Centers → centers.html
- Compare Centers → compare.html
- Organ Guides → organ-guides.html
- Education → education.html
- FAQ → faq.html
- Checklist → checklist.html
- Support → support.html
- Give Back → advocacy.html

**For Professionals:**
- Simulator → simulator.html
- Scenario Lab → scenarios.html
- Equity Audit → equity.html
- Explorer → explorer.html (new merged page)
- Model Validation → validation.html (new page)
- Documentation → docs-site/build/
- API Reference → docs-site/build/api-reference/

### 1.2 Footer update
- Update "Explore" links to match new nav
- Keep 3-column layout, update disclaimer variants

### 1.3 Old URL redirects
- `find-centers.html` → `<meta refresh>` to `centers.html?mode=find`
- `wait-estimator.html` → redirect to `centers.html?mode=estimate`
- `data.html` → redirect to `explorer.html`
- `spatial.html` → redirect to `explorer.html?tab=spatial`

### 1.4 Verification
- Every page loads with new nav
- All links resolve correctly
- Mobile hamburger works
- Active link highlighting works

---

## Phase 2: Simulator Rebuild ✅ COMPLETE

### 2.1 Decompose script.js (4889 lines)

**Keep (extract to modules):**

| New Module | Source Lines | Lines | Purpose |
|-----------|-------------|-------|---------|
| `simulator/index.js` | New | ~100 | Entry point, wire form submit |
| `simulator/tier-panel.js` | 544-724 | ~180 | Tier config fetch, advanced param panel |
| `simulator/form-helpers.js` | 2217-2505 | ~150 | Home center dropdown, age multiplier |
| `simulator/results.js` | 2504-2655, 3181-3260 | ~200 | Orchestrator: calls /score and /simulate |
| `simulator/results-table.js` | 2909-3180 | ~400 | Sortable table + inline row expansion |
| `simulator/map.js` | From 725-area | ~200 | Center markers + home pin ONLY |
| `shared/geo-utils.js` | 2732-2775 | ~50 | Geocoding + haversine |
| `shared/continue-buttons.js` | New | ~80 | Inter-tool link buttons |

**Total: ~1360 lines**

**DELETE from simulator (moves elsewhere or removed):**
- Lines 1-543: Mock city data (496 lines of dead weight)
- Lines 725-2215: 10 map overlay layers + spatial heatmap (1490 lines → moves to Explorer)
- Lines 2766-2908: City cards (replaced by table rows with inline expansion)
- Lines 3261-4079: What-if sliders, policy scenarios, travel subsidy (already in scenarios.html)
- Lines 4080-4195: Equity view (already in equity.html)
- Lines 4194-4600: City detail modal (replaced by inline expansion)
- Lines 4591-4889: Compare modal/bar (compare is its own page)

**~3530 lines deleted**

### 2.2 New simulator.html layout

```
┌──────────────────────────────────────────────────────┐
│ Patient Profile Form            │ Results Area        │
│ (via patient-form.js)          │                     │
│                                 │ [Sortable Table]    │
│ ▸ Simulation Settings           │  # Center  Score p24│
│   Inference: [Monte Carlo ▼]   │  1 UPMC    94  .82  │
│   Iterations: ───●── 1000      │  2 Mayo    91  .79  │
│   Copula: ☑                    │  > expanded detail  │
│   COD: ☐                       │  3 UCSF    89  .77  │
│                                 │                     │
│ ▸ Scoring Weights               │ [Map Companion]     │
│   Preset: [Balanced ▼]         │  • center markers   │
│   [per-category sliders]        │  ★ home location    │
│                                 │                     │
│ [Score Centers] [Run Simulation]│ [Charts]            │
│                                 │ [Continue to... btns]│
│                                 │ [Export Run]         │
└──────────────────────────────────────────────────────┘
```

**Two buttons:**
- "Score Centers" → `POST /score` → instant, fills table with 8-category scores
- "Run Simulation" → `POST /simulate` → adds probability columns (p6/p12/p24/p36, CI, median wait, competing risks)

**Click table row → inline expansion** (not a modal):
- Full score breakdown (8 categories with bars)
- Probability details + competing risks bar
- Post-transplant outcomes
- Historical trend sparkline

### 2.3 Extend patient-form.js for simulator

**`components/patient-form.js`** — Add options:
- `options.showHomeCenter: boolean` → adds home center dropdown
- `options.showInferenceMode: boolean` → adds engine selector
- `options.showAdvancedSettings: boolean` → adds iterations, copula theta, elasticity in collapsible
- Simulator passes these; analysis pages use simpler form

### 2.4 Wire URL params for inter-tool linking

**`components/patient-form.js`** — Add `populateFromURL()`:
- Reads `window.location.search`
- Maps URL params to form fields using canonical param names from url-sharing.js
- Triggers organ change event for conditional fields
- Returns true if params found

### 2.5 Verification
- Form renders with all fields
- "Score Centers" returns 248 rows, sortable
- "Run Simulation" adds probability columns, map updates
- Click row → inline expansion with full details
- No modals, no what-if/policy/equity tabs
- URL params pre-fill form
- Export Run downloads artifact JSON with seed
- "Continue to Scenario Lab / Equity Audit / Validation" buttons appear after results

---

## Phase 3: Page Merges

### 3.1 Centers page (merge find-centers + centers + wait-estimator)

**New `centers.html`** with mode switcher:

| Mode | Replaces | Behavior |
|------|----------|----------|
| Find (default) | find-centers.html | Location input + organ → distance-sorted centers |
| Browse | centers.html | Full 248-center list, search, organ filter, sort |
| Estimate | wait-estimator.html | Organ + center → wait time IQR range |

**URL:** `centers.html?mode=find&organ=kidney&zip=85721`

**New file: `centers-page.js`** (~500 lines)
- Mode switching via tabs/pills
- Calls existing `GET /centers`, `GET /centers/{code}`, `POST /score`
- Nominatim geocoding for Find mode (reuse from shared/geo-utils.js)

### 3.2 Explorer page (merge data.html + spatial.html)

**New `explorer.html`** with tabs:

| Tab | Replaces | Content |
|-----|----------|---------|
| Data Layers (default) | data.html | Multi-layer map, center dots, county health, policy overlays |
| Spatial Analysis | spatial.html | Interpolation surfaces, allocation circles, coordinate inspection |

**New files:**
- `explorer/index.js` (~100 lines) — tab switching, shared Leaflet map
- `explorer/data-layers.js` (~700 lines) — extracted from data-explorer.js + the 10 overlay layers from script.js
- `explorer/spatial-analysis.js` (~500 lines) — extracted from spatial.html inline scripts

### 3.3 Verification
- `centers.html` all 3 modes work, redirects from old URLs work
- `explorer.html` both tabs work, all layers toggle, spatial interpolation works

---

## Phase 4: Model Validation Tool (NEW)

### 4.1 Backend: New validation router

**New file: `backend/routers/validation.py`**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/validation/cross-engine` | POST | Run MC + BBN + MCMC, compare rankings |
| `/validation/model-sensitivity` | POST | Vary copula_theta/elasticity/iterations, check ranking stability |
| `/validation/clinical-sensitivity` | POST | Alias to existing /sensitivity (tornado chart) |
| `/validation/calibration` | POST | Brier score calibration check |
| `/validation/posterior-checks` | POST | MCMC posterior predictive checks |
| `/validation/convergence/{organ}` | GET | R-hat, ESS, MCMC diagnostics |
| `/validation/temporal` | POST | Temporal train/test split validation |
| `/validation/reference-run/{organ}` | GET | Canonical seed=12345 results for paper |

### 4.2 Backend: New services

**`backend/services/model_sensitivity.py`** (~150 lines)
- For given parameter + value range, run simulate() at each value
- Compute Spearman rank correlation between each run and baseline
- Return ranking stability metrics

**`backend/services/temporal_validation.py`** (~200 lines)
- Filter `srtr-historical.json` by year range
- Build wait-time distributions from filtered historical data
- Run simulation with historical distributions
- Compare predicted rankings against held-out test period
- Walk-forward validation: train on 2019-Y, test on Y+1, for each Y

**`backend/services/convergence.py`** (~100 lines)
- Load MCMC trace for organ (ArviZ NetCDF)
- Compute R-hat, ESS, autocorrelation
- Return convergence metrics

### 4.3 Backend: Temporal filtering in data_loader

**`backend/services/data_loader.py`** — Add method:
```python
def get_historical_data(self, organ, city, year_range=None):
    """Filter historical_trends by year range."""
```

**`backend/services/distributions.py`** — Add optional `year_range` param to `get_wait_time_distribution()`:
- When provided, derive log-normal params from historical data for that period
- Otherwise use current snapshot (backward compatible)

### 4.4 Backend: Registration

**`backend/main.py`** — Register validation router
**`vercel.json`** — Add `{ "source": "/validation/:path*", "destination": "/api/index" }`
**`backend/tier_config.py`** — Add validation caps (web: 300 iterations, 3 train years; local: uncapped)

### 4.5 Frontend: validation.html

**New page with 7 sections (tabs or scrollable):**

| Section | JS File | Lines | Key UI |
|---------|---------|-------|--------|
| Cross-Engine Comparison | `validation/cross-engine.js` | ~300 | Patient form → side-by-side MC/BBN/MCMC table, Spearman badges, scatter plot |
| Model Sensitivity | `validation/model-sensitivity.js` | ~250 | Param selector + range → Spearman vs param value chart, ranking tables |
| Clinical Sensitivity | `validation/clinical-sensitivity.js` | ~150 | Patient form + center → tornado chart (reuses sensitivity logic) |
| Calibration | `validation/calibration.js` | ~200 | Organ selector → Brier score badge, predicted vs analytical scatter |
| Temporal Validation | `validation/temporal.js` | ~250 | Train/test year pickers → walk-forward Spearman chart, comparison table |
| Convergence | `validation/convergence.js` | ~150 | Organ selector → R-hat table, ESS table |
| Reference Results | `validation/reference.js` | ~100 | Organ selector → cached seed=12345 results, "Copy Citation" button |

**`validation/index.js`** (~200 lines) — Tab navigation

**`api-client.js`** — Add methods: `crossEngine()`, `modelSensitivity()`, `calibration()`, `temporalValidation()`, `convergence()`, `referenceRun()`

### 4.6 Verification
- Cross-engine: kidney O+ shows MC/BBN side-by-side with Spearman rho
- Model sensitivity: copula_theta [0.5, 1.0, 1.5, 2.0] shows ranking stability
- Temporal: trains on 2019-2023, tests on 2024-2025
- Reference run with seed=12345 is deterministic
- All endpoints respect tier caps

---

## Phase 5: Inter-Tool Linking

### 5.1 URL param standard

Canonical encoding (already in url-sharing.js, standardize):
```
?organ=kidney&bt=O%2B&age=45&sex=male&urg=2&cpra=30&cop=1&cod=0&im=monte_carlo
```

### 5.2 patient-form.js reads URL params on every page

Add `TransPlanPatientForm.populateFromURL()` — reads search params, fills form, triggers conditional fields. Every tool page calls this on load.

### 5.3 "Continue to..." buttons

**`shared/continue-buttons.js`** (~80 lines):
- `renderContinueButtons(container, currentTool, formData)`
- Builds links to other tools with patient profile encoded in URL params

| From | Buttons |
|------|---------|
| Simulator | Scenario Lab, Equity Audit, Model Validation, Sensitivity |
| Sensitivity | Simulator, Scenario Lab |
| Equity | Simulator, Compare Centers |
| Scenario Lab | Simulator, Sensitivity |
| Validation | Simulator |

### 5.4 Verification
- Simulator results → click "Scenario Lab" → navigates with profile pre-filled
- URL with patient params → any tool page auto-fills form

---

## Phase 6: Tier System — Hide vs Disable

### 6.1 Hide unavailable features (don't show disabled)

On web tier:
- **Hide entirely:** MCMC inference option, copula_theta slider, elasticity slider, "full" BBN granularity
- **Cap silently:** Iterations max 1000, equity max 30 centers
- **No "requires local install" messages** — features just don't appear

On local tier:
- All controls visible and functional

### 6.2 Apply to all tool pages
Each page fetches `GET /tier` and hides features accordingly.

---

## Phase 7: Page Cleanup & Polish

### 7.1 Analysis pages (already standalone)
- `sensitivity.html` — Ensure uses patient-form.js, add seed support, export button, continue buttons
- `scenarios.html` — Add seed support, export button, continue buttons
- `equity.html` — Add seed support, export button, continue buttons

### 7.2 Center detail page
- `center.html` — Add "Simulate at this center" button → links to simulator with home_center pre-filled

### 7.3 Delete legacy code
- Delete `script.js` after all modules extracted
- Delete `find-centers.html`, `wait-estimator.html`, `data.html`, `spatial.html` (replaced by redirects)

---

## Implementation Order & Dependencies

```
Phase 0 (Seed) ──────────────────────────────┐
    │                                         │
    ├──→ Phase 1 (Nav)                        │
    │        │                                │
    │        ├──→ Phase 2 (Simulator Rebuild)  │
    │        │        │                       │
    │        │        ├──→ Phase 3 (Merges)   │
    │        │                                │
    │        └──→ Phase 4 (Validation) ←──────┘
    │                 │
    └──→ Phase 5 (Linking) ←── depends on 2, 3, 4
              │
              └──→ Phase 6 (Tier) ──→ Phase 7 (Cleanup)
```

**Parallel opportunities:** Phase 1 + Phase 4 backend can run in parallel. Phase 2 + Phase 4 frontend can overlap once Phase 1 is done.

---

## New Files Summary

### Backend (7 new files, 16 modified)

| Action | File | Lines |
|--------|------|-------|
| Create | `backend/models/export_artifact.py` | ~30 |
| Create | `backend/routers/validation.py` | ~300 |
| Create | `backend/services/model_sensitivity.py` | ~150 |
| Create | `backend/services/temporal_validation.py` | ~200 |
| Create | `backend/services/convergence.py` | ~100 |
| Modify | `backend/models/schemas.py` | Add seed fields |
| Modify | `backend/services/monte_carlo.py` | Add seed param |
| Modify | `backend/services/sensitivity.py` | Add seed param |
| Modify | `backend/services/equity.py` | Add seed param |
| Modify | `backend/services/what_if.py` | Add seed param |
| Modify | `backend/services/cross_validation.py` | Add seed, expose |
| Modify | `backend/services/brier_score.py` | Add seed param |
| Modify | `backend/services/data_loader.py` | Add temporal filtering |
| Modify | `backend/services/distributions.py` | Add year_range param |
| Modify | `backend/routers/simulate.py` | Add seed query param |
| Modify | `backend/routers/sensitivity.py` | Add seed |
| Modify | `backend/routers/equity.py` | Add seed |
| Modify | `backend/routers/what_if.py` | Add seed |
| Modify | `backend/routers/api_v1.py` | Register validation |
| Modify | `backend/main.py` | Register validation router |
| Modify | `backend/tier_config.py` | Validation caps |
| Modify | `vercel.json` | Validation rewrites |

### Frontend (19 new files, 10 modified, 1 deleted)

| Action | File | Lines |
|--------|------|-------|
| Create | `simulator/index.js` | ~100 |
| Create | `simulator/tier-panel.js` | ~180 |
| Create | `simulator/form-helpers.js` | ~150 |
| Create | `simulator/results.js` | ~200 |
| Create | `simulator/results-table.js` | ~400 |
| Create | `simulator/map.js` | ~200 |
| Create | `explorer.html` | HTML |
| Create | `explorer/index.js` | ~100 |
| Create | `explorer/data-layers.js` | ~700 |
| Create | `explorer/spatial-analysis.js` | ~500 |
| Create | `centers-page.js` | ~500 |
| Create | `validation.html` | HTML |
| Create | `validation/index.js` | ~200 |
| Create | `validation/cross-engine.js` | ~300 |
| Create | `validation/model-sensitivity.js` | ~250 |
| Create | `validation/clinical-sensitivity.js` | ~150 |
| Create | `validation/calibration.js` | ~200 |
| Create | `validation/temporal.js` | ~250 |
| Create | `validation/convergence.js` | ~150 |
| Create | `validation/reference.js` | ~100 |
| Create | `shared/geo-utils.js` | ~50 |
| Create | `shared/continue-buttons.js` | ~80 |
| Modify | `components/site-chrome.js` | Nav rewrite |
| Modify | `components/patient-form.js` | URL params, extra fields |
| Modify | `api-client.js` | Seed + validation methods |
| Modify | `url-sharing.js` | Prefix-aware |
| Modify | `export-handler.js` | Artifact export |
| Modify | `simulator.html` | Complete rewrite |
| Modify | `centers.html` | Merged page |
| Modify | `sensitivity.html` | Seed, export, links |
| Modify | `scenarios.html` | Seed, export, links |
| Modify | `equity.html` | Seed, export, links |
| Delete | `script.js` | Replaced by modules |

### Redirects (keep old files, add meta refresh)
- `find-centers.html` → `centers.html?mode=find`
- `wait-estimator.html` → `centers.html?mode=estimate`
- `data.html` → `explorer.html`
- `spatial.html` → `explorer.html?tab=spatial`

---

## Verification Plan

### Per-Phase (run after each phase)
- Existing pytest suite passes (594+ tests)
- Existing Jest suite passes (112 tests)
- All pages load without console errors
- Vercel deployment succeeds

### End-to-End (after all phases)
1. **Simulator flow:** Fill form → Score → Simulate → click row → see details → Export Run → verify seed in artifact
2. **Inter-tool flow:** Simulator → click "Scenario Lab" → profile pre-filled → run scenario → click "Equity Audit" → profile carried
3. **Validation flow:** Cross-engine comparison → verify MC/BBN agree → Model sensitivity → verify rankings stable → Temporal → verify train/test split metrics
4. **Reproducibility:** Run simulation with seed=42, export. Run again with seed=42, export. Diff = zero.
5. **Patient flow:** Centers page Find mode → Compare → Center detail → educational pages
6. **Tier gating:** Deploy to Vercel → MCMC/copula_theta/elasticity hidden. Run locally → all visible.
7. **Redirects:** Old URLs (find-centers.html, wait-estimator.html, data.html, spatial.html) redirect correctly
8. **Mobile:** All pages responsive, hamburger nav works
