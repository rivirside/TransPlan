# Landing Page Follow-ups Design Spec

**Date:** 2026-03-26
**Scope:** 4 follow-up tasks from the landing page redesign

---

## Task 1: Hyperlink Story Steps

Add links to key phrases in the 8 scrollytelling steps. All links open in new tabs (`target="_blank" rel="noopener"`). Link styling: warm accent color (`#c97c4a`), no underline, underline on hover.

### Link mapping

| Step | Phrase | Target |
|------|--------|--------|
| 1 - Landscape | "248 transplant programs" | `centers.html` |
| 1 - Landscape | "SRTR" (data source) | `https://www.srtr.org` |
| 2 - Problem | "OPTN" (data source) | `https://optn.transplant.hrsa.gov` |
| 3 - Organ Supply | "NHTSA" (data source) | `https://www.nhtsa.gov` |
| 4 - Donor Types | "organ-specific donor rates per region" | `docs-site/build/` |
| 4 - Donor Types | "OPTN" and "SRTR" (data source) | respective sites |
| 5 - Registration | "HRSA" (data source) | `https://www.organdonor.gov` |
| 6 - Methods | "Monte Carlo simulation" (heading) | `docs-site/build/` |
| 6 - Methods | "What-if scenarios" (highlight) | `data.html` |
| 7 - Composite | "CMS" | `https://www.medicare.gov/care-compare` |
| 7 - Composite | "CDC" | `https://www.cdc.gov/places` |
| 7 - Composite | "EPA" | `https://aqs.epa.gov` |
| 7 - Composite | "BLS" | `https://www.bls.gov` |
| 8 - For Users | "Simulator" | `simulator.html` |
| 8 - For Users | "Center Explorer" | `centers.html` |
| 8 - For Users | "Data tab" | `data.html` |

### Style

```css
.narr-step a {
  color: var(--warm-accent);
  text-decoration: none;
  font-weight: 600;
}
.narr-step a:hover {
  text-decoration: underline;
}
```

---

## Task 2: Shared Nav/Footer JS Component

Extract duplicated nav and footer HTML from all 13 pages into a single JavaScript file.

### Approach: Inline JS template

Create `components/site-chrome.js` containing nav and footer HTML as template literals. On DOMContentLoaded, inject into placeholder elements.

### How it works

1. Each HTML page replaces its `<nav>` with `<div id="nav-placeholder"></div>` and its `<footer>` with `<div id="footer-placeholder"></div>`
2. Each page adds `<script src="components/site-chrome.js"></script>` before the closing `</body>`
3. `site-chrome.js` detects the current page from `window.location.pathname` and sets `nav-link--active` on the correct link
4. Footer variants handled via `data-footer-variant` attribute on the placeholder:
   - Default: standard 3-paragraph disclaimer (most pages)
   - `simulator`: extended 5-paragraph disclaimer with limitations detail
   - `advocacy`: custom non-affiliation disclaimer
5. Dark mode toggle, hamburger menu, and dropdown behavior preserved in the same file
6. Mobile nav toggle logic included

### Files affected

All 13 HTML pages: `index.html`, `simulator.html`, `centers.html`, `center.html`, `compare.html`, `find-centers.html`, `wait-estimator.html`, `organ-guides.html`, `education.html`, `support.html`, `advocacy.html`, `faq.html`, `checklist.html`

Plus the new `data.html` from Task 3.

### New file

- `components/site-chrome.js` - nav + footer templates + injection logic + mobile toggle + dropdown

---

## Task 3: Data Explorer Page (`data.html`)

A data exploration page for visualizing the public datasets that power the project. Layout C: contained map with floating panels and data provenance section below.

### Page structure

```
[Nav - from site-chrome.js]
[Page header: "Data Explorer" + description]
[Map frame (rounded, 660px, 48px side padding)]
  [Floating layer panel - top-left, draggable]
  [Floating legend panel - bottom-right, draggable]
[Data Sources section - 8 provenance cards]
[Footer - from site-chrome.js]
```

### Map

- Leaflet with CartoDB Positron tiles
- Sepia CSS filter matching landing page
- All 248 centers from `data/srtr-all-centers.json`
- Scroll-wheel zoom enabled within map frame
- 48px side padding prevents accidental zoom when scrolling past

### Marker clustering (Leaflet.markercluster)

When zoomed out, nearby centers merge into numbered cluster circles:
- Cluster circles show the count of centers in the group
- **Cluster color is neutral** (e.g. muted brown/gray) and distinct from any data-encoding color scale, so clusters are never confused with data values
- Clicking a cluster zooms in or spiderfies to reveal individual markers
- Individual (unclustered) markers show their data-encoded color/size normally
- Cluster boundaries update as layers change (e.g. filtering by organ type may reduce cluster counts)

### Floating layer panel (top-left)

Draggable via grip handle in title bar. Accordion sections with checkboxes:

**Organ filter pills** at top: All, Kidney, Liver, Heart, Lung, Pancreas, Intestine. Filters which organ's data is shown for organ-specific layers (wait times, volumes, survival).

**Center data (248 programs)** - rendered as circle markers (dots):
- Wait times (color gradient green-to-red) - source: `wait-time-distributions-centers.json`
- Transplant volumes (dot size) - source: `hospital-quality.json`
- Survival outcomes (color gradient amber-to-green) - source: `post-transplant-outcomes-centers.json`
- Composite score (size + opacity) - source: computed from pipeline

**Constraint:** Radio behavior within center-dot group. Only one color encoding and one size encoding active at a time (max 2 dimensions: size + color).

**State data (51 states)** - rendered as choropleth fill with discrete color buckets (stepped scale, not continuous gradient, for readability):
- Donor registration rates (blue stepped scale) - source: `donor-registration.json`
- Traffic fatality rates (red stepped scale) - source: `traffic-fatalities.json`
- Policy tier scores (green stepped scale) - source: `manual/policy-tiers.json`

**Constraint:** Radio behavior. One state fill layer at a time.

**County data (3,144 counties)** - rendered as choropleth fill:
- Diabetes rate (indigo gradient) - source: `health-demographics-counties.json`
- Obesity rate (violet gradient) - source: `health-demographics-counties.json`
- Hypertension rate (purple gradient) - source: `health-demographics-counties.json`
- Smoking rate (light purple gradient) - source: `health-demographics-counties.json`

**Constraint:** Radio behavior. One county fill layer at a time.

**Cross-level stacking:** One state fill + one county fill allowed simultaneously. County renders on top with lower default opacity. Opacity sliders in legend panel let users tune the blending.

**Point data (2,749 monitors)** - rendered as small circle markers:
- EPA air quality (cyan, sized by AQI) - source: `air-quality-monitors.json`

**Export buttons:** CSV and JSON for currently visible/filtered data.

### Floating legend panel (bottom-right)

Draggable via grip handle. Shows legends only for currently active layers. Each legend entry includes:

- Layer name + visualization type badge ("center dots", "state fill", "county fill", "monitor dots")
- Color gradient or dot-size scale showing what colors/sizes mean
- Value range with units (e.g. "8 mo" to "11 yr")
- **Opacity slider** per layer:
  - Dot layers default to 90% opacity
  - State fill layers default to 50% opacity
  - County fill layers default to 40% opacity

Legend updates dynamically as layers are toggled on/off.

### Center popups

Click any center dot to see a Leaflet popup with:
- Center name, city/state, SRTR code
- Stats for active layers (e.g. wait time, volume, survival rate, composite score)
- Values shown in warm accent color

### Data Sources section (below map)

Grid of 8 cards, each linking to the official data source (`target="_blank"`):

| Badge | Source | Link |
|-------|--------|------|
| SRTR | Scientific Registry of Transplant Recipients | srtr.org |
| OPTN | Organ Procurement and Transplantation Network | optn.transplant.hrsa.gov |
| CDC | Centers for Disease Control (PLACES) | cdc.gov/places |
| CMS | Medicare and Medicaid Services | medicare.gov/care-compare |
| EPA | Environmental Protection Agency | aqs.epa.gov |
| NHTSA | Highway Traffic Safety | nhtsa.gov/research-data |
| HRSA | Health Resources and Services | organdonor.gov |
| BLS | Bureau of Labor Statistics | bls.gov |

Cards have hover effect (accent border + subtle shadow). Each shows: source name, description, data count, update frequency, and external link indicator.

### Required new data files

State and county choropleth rendering requires GeoJSON boundary files:
- `data/geo/us-states.geojson` - US state boundaries
- `data/geo/us-counties.geojson` - US county boundaries (can use simplified/topojson for performance)

### New files

- `data.html` - page markup (uses site-chrome.js for nav/footer)
- `data-explorer.js` - map initialization, layer management, legend updates, drag logic, export
- `data-explorer.css` or styles added to `styles.css` under `.data-page` scope

### v2 enhancements (deferred)

- Glyph mode toggle: cross-shaped markers encoding 4 dimensions (2 per axis), with `?` help button explaining dot vs glyph mode
- Patterned choropleths: dot-density or hatching overlays for conflict-free multi-level stacking
- What-if scenario sliders: policy-level parameter adjustments (donor rate multiplier, wait-time multiplier)
- PDF export

---

## Task 4: GitHub Contribute Link

### Changes

1. **Hero section** (`index.html`): Add explicit GitHub repo link next to the existing `mailto:contact@rivir.social` link. Text: "View on GitHub" with link to repo URL. Styled same as the email link (accent color, no underline).

2. **Footer** (in `components/site-chrome.js`): Add "GitHub" link to `footer-links` div alongside Simulator and Documentation links.

3. **Verify once repo is public:** The links won't work until the repo is made public. Add the links now pointing to the expected URL; they'll activate when the repo goes public.

---

## Style notes (all tasks)

- No em dashes in copy
- `.landing-page` class on body of index.html scopes landing-specific styles
- Warm palette: `#faf9f7` bg, `#c97c4a` accent, `#e8e4dc` borders
- Dark mode: `#1a1710` bg, `#2a2520` borders (to be applied to data page too)
- Mobile breakpoints: 1024px, 768px, 480px
- Data page floating panels collapse to bottom sheet on mobile (below 768px)

---

## Implementation order

1. **Task 2** (shared nav/footer) - do first, eliminates duplication before creating data.html
2. **Task 1** (hyperlink story steps) - quick, independent
3. **Task 3** (data explorer page) - largest task, depends on task 2 for nav/footer
4. **Task 4** (GitHub link) - trivial, do alongside task 2 or 3
