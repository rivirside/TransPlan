# TransPlan - Architecture Decision Records

> **Grep-searchable.** Only search this file when you need context on why a specific decision was made.

---

## ADR-001: Static Site with JSON Data Files

**Date:** 2026-02-28
**Status:** Accepted

**Context:** TransPlan needs real data but has no backend. Options: (a) build a server, (b) use a BaaS, (c) pre-fetch data via CI and serve as static JSON.

**Decision:** Option (c). GitHub Actions fetches data weekly, writes to `data/` as JSON, commits to repo. GitHub Pages serves the static site. Frontend loads JSON at runtime.

**Rationale:** Zero infrastructure cost, zero ops burden, data is version-controlled, site works offline with hardcoded fallbacks. No API keys exposed to the client.

**Consequences:** Data is at most 1 week old. Adding a new data source requires a new fetch script + workflow job. Cannot do real-time queries.

---

## ADR-002: Hardcoded Fallbacks in data-loader.js

**Date:** 2026-02-28
**Status:** Accepted

**Context:** JSON files might fail to load (network error, CORS on local file://, deleted files). Should the app crash or degrade?

**Decision:** `data-loader.js` contains complete hardcoded copies of all data as fallback defaults. If any JSON fetch fails, the app uses the hardcoded value for that source and continues.

**Rationale:** The app must always work. Medical tool users need reliability. Fallback data is better than no data.

**Consequences:** `data-loader.js` is large (~300 lines of defaults). Defaults can drift from fetched data over time. Need to periodically update defaults from the latest fetched data.

---

## ADR-003: Algorithm Bug Fixes - Additive Scoring

**Date:** 2026-02-28
**Status:** Accepted

**Context:** `calculateMedicalCompatibilityScore` started at `score = 100` and multiplied the first component (`score *= bloodType * 0.40`), then added the rest. This mixed multiplicative and additive math, producing wildly wrong results.

**Decision:** Changed to `score = 0` with all components purely additive: `score += component * weight`. Each component contributes its weighted share independently.

**Rationale:** Additive is mathematically correct for weighted averaging. All other scoring functions already used additive. The multiplicative approach was a bug, not a design choice.

---

## ADR-004: Remove Random Jitter from Scoring

**Date:** 2026-02-28
**Status:** Accepted

**Context:** `calculateComprehensiveScore` applied `totalScore *= (0.98 + Math.random() * 0.04)` to simulate "real-world uncertainty."

**Decision:** Removed entirely. Scores are now deterministic.

**Rationale:** This is a medical decision-support tool. Users comparing results need consistency. Non-determinism makes debugging impossible and erodes trust. If uncertainty communication is needed later, it should be shown as a confidence interval, not baked into the score.

---

## ADR-005: Score All 21 Cities Dynamically

**Date:** 2026-02-28
**Status:** Accepted

**Context:** Original `script.js` had hardcoded `cityData` with only 5 pre-selected cities per organ type. The algorithm existed but its results were ignored in favor of the mock data.

**Decision:** `calculateResults()` now iterates all 21 cities in `cityStateMap`, calls `calculateComprehensiveScore` for each, and ranks them dynamically. Mock `cityData` is only used as fallback if the algorithm is unavailable.

**Rationale:** The whole point of the algorithm is to personalize results. Showing the same 5 cities regardless of patient profile defeats the purpose.

**Consequences:** Results now change based on patient inputs (blood type, age, urgency, etc.). Some cities that were never shown before may now appear in top results.

---

## ADR-006: Chart.js via CDN

**Date:** 2026-02-28
**Status:** Accepted

**Context:** Need charts for score visualization. Options: (a) build custom SVG charts, (b) D3.js, (c) Chart.js via CDN.

**Decision:** Chart.js via `cdn.jsdelivr.net`. No build step, no bundler.

**Rationale:** Chart.js is lightweight (~60KB gzipped), has radar/bar/donut out of the box, and works well without a build system. D3 is overkill for 3 chart types. Custom SVG is too much effort.

**Consequences:** External CDN dependency. If CDN is down, charts don't render but the rest of the app works fine.

---

## ADR-007: Separate Fetch Jobs in GitHub Actions

**Date:** 2026-02-28
**Status:** Accepted

**Context:** The data pipeline fetches from 5+ APIs. Should they run as one job or separate jobs?

**Decision:** Each API source gets its own job in `fetch-data.yml`. A final `validate` job runs after all fetch jobs (`if: always()`).

**Rationale:** Isolated failures. If EPA is down, NHTSA data still gets updated. Each job commits independently. Easier to debug which source failed.

**Consequences:** More workflow YAML. Potential git conflicts if two jobs try to push simultaneously (mitigated by each writing different files).

---

## ADR-008: Documentation Tiers

**Date:** 2026-02-28
**Status:** Accepted

**Context:** Need project documentation that's useful for AI-assisted development across sessions.

**Decision:** Three tiers:
1. **Always-read**: `docs/status.md` - loaded every session
2. **Context-read**: `docs/design.md` - read in full when touching UI/CSS
3. **Grep-searchable**: `docs/adr-log.md`, `docs/roadmap.md`, `docs/brand-bible.md` - only searched

**Rationale:** Avoids context bloat. Status is short and always relevant. Design details only matter when doing design work. ADRs and roadmap are reference material, not active reading.
