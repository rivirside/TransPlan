# Landing Page Follow-ups Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship 5 follow-up tasks from the landing page redesign: landing page polish, shared nav/footer JS, story step hyperlinks, Data Explorer page, and GitHub contribute link.

**Architecture:** Static HTML/CSS/JS site with Leaflet maps. No build system or framework. All JS is vanilla, loaded from `<script>` tags. CSS lives in `styles.css` (~4900 lines, scoped with body class selectors). Data is in JSON files under `data/`.

**Tech Stack:** HTML, CSS, vanilla JS, Leaflet, Leaflet.markercluster, topojson-client (all CDN)

**Spec:** `docs/superpowers/specs/2026-03-26-landing-followups-design.md`

---

## Chunk 1: Landing Page Polish + Story Hyperlinks

### Task 1: Nav Font Size Fix

**Files:**
- Modify: `styles.css:263-269` (`.nav-dropdown-item`)

- [ ] **Step 1: Fix dropdown item font size**

In `styles.css`, the `.nav-dropdown-item` has `font-size: var(--fs-sm, 0.875rem)` (line 268) while `.nav-link` inherits from parent (no explicit font-size). Remove the explicit `font-size` from `.nav-dropdown-item` so both use the same inherited size.

```css
/* In .nav-dropdown-item (line 263), remove the font-size line: */
.nav-dropdown-item {
  display: block;
  padding: var(--space-2, 8px) var(--space-4, 16px);
  color: var(--warm-muted, #888);
  text-decoration: none;
  /* font-size line removed */
  font-weight: 500;
  transition: background var(--transition-fast, 0.15s);
}
```

- [ ] **Step 2: Verify in browser**

Open `index.html` in browser. Hover over "Resources" dropdown. Confirm dropdown items and top-level nav links are now the same font size.

- [ ] **Step 3: Commit**

```bash
git add styles.css
git commit -m "fix: unify nav dropdown font size with top-level links"
```

---

### Task 2: Scroll Snap for Story Section

**Files:**
- Modify: `styles.css` (add scroll-snap rules near landing page section ~line 3920)

- [ ] **Step 1: Add scroll-snap CSS**

Add to `styles.css` after the `.landing-page` rule (line 3923):

```css
/* Gentle scroll snap -- proximity, not mandatory */
.landing-page {
  scroll-snap-type: y proximity;
  overflow-y: auto;
  height: 100vh;
}
.landing-page .story-section {
  scroll-snap-align: start;
}
```

- [ ] **Step 2: Verify chevron arrow targets story section**

In `index.html`, the scroll hint div has class `.scroll-hint`. Check if clicking the chevron scrolls to `.story-section`. If not already wired, the `landing-story.js` or inline JS should handle it. The current HTML (line 54-57) has:

```html
<div class="scroll-hint">
    <span>Scroll down to explore the data and learn more about the project</span>
    <div class="scroll-arrow"></div>
</div>
```

If no click handler exists, add one in `landing-story.js` at the end of the IIFE:

```javascript
var scrollHint = document.querySelector('.scroll-hint');
if (scrollHint) {
  scrollHint.style.cursor = 'pointer';
  scrollHint.addEventListener('click', function() {
    document.querySelector('.story-section').scrollIntoView({ behavior: 'smooth' });
  });
}
```

- [ ] **Step 3: Test scroll behavior**

Open `index.html`. Scroll slowly past the hero -- viewport should gently settle on the story section. Scroll fast -- should pass right through without getting stuck. Click the chevron arrow -- should smooth-scroll to the story section.

- [ ] **Step 4: Commit**

```bash
git add styles.css landing-story.js
git commit -m "feat: add scroll snap for story section, wire chevron click"
```

---

### Task 3: Full-Width Landing Layout

**Files:**
- Modify: `styles.css:4008-4015` (`.story-section` grid), `styles.css:3926-3928` (`.landing-hero`)

- [ ] **Step 1: Widen narrative panel on large screens**

In `styles.css`, add a media query after the `.story-section` rules (after line 4015):

```css
@media (min-width: 1400px) {
  .story-section {
    grid-template-columns: 500px 1fr;
  }
  .landing-hero {
    max-width: 960px;
  }
  .post-story-inner {
    max-width: 960px;
  }
  .landing-features {
    max-width: 960px;
  }
}
```

- [ ] **Step 2: Test at 100% zoom on wide monitor**

Open `index.html` at 100% zoom on a wide screen (>1400px). Verify:
- Narrative panel is wider (~500px)
- Map fills remaining space
- Hero, post-story CTA, and feature sections use wider max-width
- Nothing breaks at narrower widths

- [ ] **Step 3: Commit**

```bash
git add styles.css
git commit -m "fix: widen landing layout on large screens (>1400px)"
```

---

### Task 4: Hyperlink Story Steps

**Files:**
- Modify: `index.html:63-178` (story step content)
- Modify: `styles.css` (add `.narr-step a` styles)

- [ ] **Step 1: Add link styles to CSS**

Add after the `.narr-step.active` rule in `styles.css` (around line 4040):

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

- [ ] **Step 2: Add links to Step 1 (The Landscape)**

In `index.html` line 67, wrap "248 transplant programs" in a link. In the data-source div (line 69), wrap "SRTR" in a link.

```html
<!-- line 67: change -->
<p>Each marker is a hospital that performs organ transplants: kidneys, livers, hearts, lungs, pancreas, and intestine. Together they serve over 100,000 patients on the national waitlist.</p>
<!-- to: (wrap the first sentence subject) -->
<!-- No change to this paragraph -- "248 transplant programs" is in the h2, not in a wrappable context -->
```

Actually, the phrase "248 transplant programs" appears in the `<h2>` tag on line 66. Wrap it there:

```html
<h2><a href="centers.html" target="_blank" rel="noopener">248 transplant programs</a>. One country.</h2>
```

For the data source (line 69):
```html
<div class="data-source">Center data from <a href="https://www.srtr.org" target="_blank" rel="noopener"><strong>SRTR</strong></a> (Scientific Registry of Transplant Recipients)</div>
```

- [ ] **Step 3: Add links to Step 2 (The Problem)**

In `index.html` line 85, data-source div:
```html
<div class="data-source">Wait data from <a href="https://optn.transplant.hrsa.gov" target="_blank" rel="noopener"><strong>OPTN</strong></a> (Organ Procurement and Transplantation Network)</div>
```

- [ ] **Step 4: Add links to Step 3 (Organ Supply)**

In `index.html` line 99, data-source div:
```html
<div class="data-source">Fatality data from <a href="https://www.nhtsa.gov" target="_blank" rel="noopener"><strong>NHTSA</strong></a> via CDC WISQARS</div>
```

- [ ] **Step 5: Add links to Step 4 (Donor Types)**

In `index.html` line 113, highlight div, wrap the key phrase:
```html
<div class="highlight">We model this by <a href="docs-site/build/architecture/data-pipeline" target="_blank" rel="noopener">weighting organ-specific donor rates per region</a>, not just raw fatality counts.</div>
```

In the data-source div (line 114):
```html
<div class="data-source">Donor type data from <a href="https://optn.transplant.hrsa.gov" target="_blank" rel="noopener"><strong>OPTN</strong></a> &amp; <a href="https://www.srtr.org" target="_blank" rel="noopener"><strong>SRTR</strong></a> program-specific reports</div>
```

- [ ] **Step 6: Add links to Step 5 (Donor Willingness)**

In `index.html` line 130, data-source div:
```html
<div class="data-source">Registration data from <a href="https://www.organdonor.gov" target="_blank" rel="noopener"><strong>HRSA</strong></a> / Donate Life America</div>
```

- [ ] **Step 7: Add links to Step 6 (The Methods)**

In `index.html` line 141, wrap heading:
```html
<h2><a href="docs-site/build/architecture/overview" target="_blank" rel="noopener">Monte Carlo simulation</a> with competing risks.</h2>
```

In the highlight div (line 144):
```html
<div class="highlight"><a href="data.html">What-if scenarios</a> let researchers adjust donor rates and wait-time multipliers to model how UNOS policy changes would shift transplant probabilities in real time.</div>
```

Note: "What-if scenarios" links to `data.html` (same tab, no target="_blank") since it's an internal page.

- [ ] **Step 8: Add links to Step 7 (The Composite)**

In `index.html` line 156, wrap the agency abbreviations:
```html
<p>transplant.today combines all of these layers into a composite suitability score: medical compatibility, wait times, donor availability, hospital quality (<a href="https://www.medicare.gov/care-compare" target="_blank" rel="noopener"><strong>CMS</strong></a>), logistics, health demographics (<a href="https://www.cdc.gov/places" target="_blank" rel="noopener"><strong>CDC</strong></a>), air quality (<a href="https://aqs.epa.gov" target="_blank" rel="noopener"><strong>EPA</strong></a>), and socioeconomic support (<a href="https://www.bls.gov" target="_blank" rel="noopener"><strong>BLS</strong></a>).</p>
```

- [ ] **Step 9: Add links to Step 8 (For Users)**

In `index.html` line 170-171, wrap tool names:
```html
<p><strong>For patients:</strong> the <a href="simulator.html">Simulator</a> gives you personalized center rankings with wait-time forecasts. The <a href="centers.html">Center Explorer</a> lets you compare programs side by side. No login, no cost.</p>
<p><strong>For researchers:</strong> the <a href="data.html">Data tab</a> exposes every layer as a toggleable overlay on the interactive map. Run what-if policy scenarios. Export results as CSV or JSON. Explore how allocation policies, donor registration drives, and infrastructure investments could reshape equitable access to transplantation.</p>
```

Note: Remove "or PDF" from the text since PDF export is deferred to v2.

- [ ] **Step 10: Verify all links in browser**

Open `index.html` and click through all 8 steps. Verify:
- Links are styled in accent color, no underline, underline on hover
- External links open in new tabs
- Internal links (`simulator.html`, `centers.html`, `data.html`) work (data.html will 404 until Task 3)
- No broken layouts from wrapping text in anchor tags

- [ ] **Step 11: Commit**

```bash
git add index.html styles.css
git commit -m "feat: add hyperlinks to story step key phrases and data sources"
```

---

## Chunk 2: Shared Nav/Footer Component

### Task 5: Create site-chrome.js

**Files:**
- Create: `components/site-chrome.js`

- [ ] **Step 1: Create components directory**

```bash
mkdir -p components
```

- [ ] **Step 2: Extract nav HTML template**

Read the current nav from `index.html` (lines 12-41). Use this as the template for `site-chrome.js`. The nav includes: brand logo/text, hamburger button, nav links (Simulator, Resources dropdown with 10 items, Data accent link, Docs external link).

Write `components/site-chrome.js` with the nav template as a string literal:

```javascript
(function() {
  'use strict';

  var NAV_HTML = ''
    + '<nav class="site-nav" aria-label="Site navigation">'
    + '  <div class="nav-inner">'
    + '    <a href="/" class="nav-brand">'
    + '      <span class="nav-brand-icon" aria-hidden="true">'
    + '        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>'
    + '      </span>'
    + '      <span class="nav-brand-text">transplant.today</span>'
    + '    </a>'
    + '    <button class="nav-toggle" aria-label="Toggle navigation" aria-expanded="false">'
    + '      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>'
    + '    </button>'
    + '    <div class="nav-links">'
    + '      <a href="simulator.html" class="nav-link">Simulator</a>'
    + '      <div class="nav-dropdown">'
    + '        <button class="nav-link nav-dropdown-trigger" aria-expanded="false" aria-haspopup="true">Resources <span class="dropdown-arrow" aria-hidden="true">&#9662;</span></button>'
    + '        <div class="nav-dropdown-menu" role="menu">'
    + '          <a href="find-centers.html" class="nav-dropdown-item" role="menuitem">Find My Centers</a>'
    + '          <a href="wait-estimator.html" class="nav-dropdown-item" role="menuitem">Wait Estimator</a>'
    + '          <a href="centers.html" class="nav-dropdown-item" role="menuitem">Center Explorer</a>'
    + '          <a href="compare.html" class="nav-dropdown-item" role="menuitem">Compare Centers</a>'
    + '          <a href="organ-guides.html" class="nav-dropdown-item" role="menuitem">Organ Guides</a>'
    + '          <a href="education.html" class="nav-dropdown-item" role="menuitem">Education</a>'
    + '          <a href="support.html" class="nav-dropdown-item" role="menuitem">Patient Support</a>'
    + '          <a href="advocacy.html" class="nav-dropdown-item" role="menuitem">Give Back</a>'
    + '          <a href="faq.html" class="nav-dropdown-item" role="menuitem">FAQ</a>'
    + '          <a href="checklist.html" class="nav-dropdown-item" role="menuitem">Checklist</a>'
    + '        </div>'
    + '      </div>'
    + '      <a href="data.html" class="nav-link nav-link-accent">Data</a>'
    + '      <a href="docs-site/build/" class="nav-link" target="_blank" rel="noopener">Docs</a>'
    + '    </div>'
    + '  </div>'
    + '</nav>';

  // Footer variant content
  var FOOTER_DISCLAIMER = {
    default: ''
      + '<p><strong>This tool is for educational and exploratory purposes only.</strong> transplant.today is not a medical device, does not provide medical advice, and cannot predict individual transplant outcomes.</p>'
      + '<p><strong>Scores are relative comparisons</strong> based on publicly available regional statistics. They are not clinical assessments.</p>'
      + '<p><strong>Always consult your transplant team</strong> and healthcare providers before making any decisions about where to list for a transplant.</p>',
    simulator: ''
      + '<p><strong>This tool is for educational and exploratory purposes only.</strong> transplant.today is not a medical device, does not provide medical advice, and cannot predict individual transplant outcomes.</p>'
      + '<p><strong>Scores are relative comparisons</strong> based on publicly available regional statistics. They are not clinical assessments.</p>'
      + '<p><strong>Simulation results are statistical estimates</strong>, not predictions. Actual outcomes depend on many factors not captured by this model, including evolving clinical protocols, organ quality, and patient-specific medical decisions.</p>'
      + '<p><strong>Wait time estimates</strong> are derived from historical OPTN data and adjusted by center-specific factors. They represent population-level medians, not individual guarantees.</p>'
      + '<p><strong>Always consult your transplant team</strong> and healthcare providers before making any decisions about where to list for a transplant.</p>',
    advocacy: ''
      + '<p><strong>This tool is for educational and exploratory purposes only.</strong> transplant.today is not a medical device and does not provide medical advice.</p>'
      + '<p><strong>transplant.today is not affiliated</strong> with any of the organizations listed on this page. Links are provided for informational purposes only.</p>'
  };

  var FOOTER_LINKS = {
    default: ''
      + '<a href="simulator.html">Simulator</a>'
      + '<a href="docs-site/build/" target="_blank" rel="noopener">Documentation</a>'
      + '<a href="https://github.com/rivirside/TransPlan" target="_blank" rel="noopener">GitHub</a>',
    simulator: ''
      + '<a href="/">Home</a>'
      + '<a href="docs-site/build/" target="_blank" rel="noopener">Documentation</a>'
      + '<a href="https://github.com/rivirside/TransPlan" target="_blank" rel="noopener">GitHub</a>'
  };

  function getFooterHTML(variant) {
    var disclaimer = FOOTER_DISCLAIMER[variant] || FOOTER_DISCLAIMER['default'];
    var links = FOOTER_LINKS[variant] || FOOTER_LINKS['default'];
    return ''
      + '<footer id="disclaimer-full" class="site-footer">'
      + '  <div class="footer-inner">'
      + '    <div class="footer-disclaimer">'
      + '      <h3>Disclaimer</h3>'
      + disclaimer
      + '    </div>'
      + '    <div class="footer-meta">'
      + '      <div class="footer-links">'
      + links
      + '      </div>'
      + '      <p class="footer-copy">transplant.today is under active development. Not affiliated with UNOS, OPTN, or any transplant center.</p>'
      + '      <p class="footer-copy">Contact: <a href="mailto:tomer@arizona.edu">tomer@arizona.edu</a></p>'
      + '    </div>'
      + '  </div>'
      + '</footer>';
  }

  function setActiveLink(navEl) {
    var path = window.location.pathname;
    var page = path.split('/').pop() || 'index.html';
    if (page === '' || page === '/') page = 'index.html';

    // Map page filenames to nav link hrefs
    var links = navEl.querySelectorAll('.nav-link, .nav-dropdown-item');
    links.forEach(function(link) {
      var href = link.getAttribute('href');
      if (!href) return;
      var linkPage = href.split('/').pop().split('#')[0].split('?')[0];
      if (linkPage === page) {
        if (link.classList.contains('nav-dropdown-item')) {
          link.classList.add('active');
        } else {
          link.classList.add('nav-link--active');
        }
      }
    });
  }

  function inject() {
    // Inject nav
    var navPlaceholder = document.getElementById('nav-placeholder');
    if (navPlaceholder) {
      navPlaceholder.outerHTML = NAV_HTML;
      var nav = document.querySelector('.site-nav');
      if (nav) setActiveLink(nav);
    }

    // Inject footer
    var footerPlaceholder = document.getElementById('footer-placeholder');
    if (footerPlaceholder) {
      var variant = footerPlaceholder.getAttribute('data-footer-variant') || 'default';
      footerPlaceholder.outerHTML = getFooterHTML(variant);
    }

    // Dispatch event for dark-mode.js
    document.dispatchEvent(new Event('nav-ready'));
  }

  // Run immediately (script is at end of body, DOM is available)
  inject();
})();
```

- [ ] **Step 3: Verify site-chrome.js loads correctly**

Create a minimal test: temporarily add `<div id="nav-placeholder"></div>` and `<script src="components/site-chrome.js"></script>` to one page (e.g. `faq.html`), removing its existing nav/footer. Open in browser and confirm nav and footer render correctly with the right active link highlighted.

- [ ] **Step 4: Commit**

```bash
git add components/site-chrome.js
git commit -m "feat: create shared nav/footer component (site-chrome.js)"
```

---

### Task 6: Update dark-mode.js for nav-ready Event

**Files:**
- Modify: `dark-mode.js:128-160`

- [ ] **Step 1: Add nav-ready fallback listener**

In `dark-mode.js`, modify the `initNav` call at the bottom (lines 156-160). Add a fallback that listens for `nav-ready` if `.nav-links` isn't found on DOMContentLoaded:

```javascript
// Replace lines 156-160 with:
function tryInitNav() {
  if (document.querySelector('.nav-links')) {
    initNav();
  } else {
    // nav not yet injected (site-chrome.js hasn't run), listen for it
    document.addEventListener('nav-ready', initNav, { once: true });
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', tryInitNav);
} else {
  tryInitNav();
}
```

- [ ] **Step 2: Test dark mode toggle appears**

Open any page that uses site-chrome.js. Confirm the dark mode toggle (sun/moon icon) appears in the nav and clicking it toggles dark mode.

- [ ] **Step 3: Commit**

```bash
git add dark-mode.js
git commit -m "fix: dark-mode.js listens for nav-ready event from site-chrome.js"
```

---

### Task 7: Migrate All 13 Pages to site-chrome.js

**Files:**
- Modify: all 13 HTML files (replace nav + footer with placeholders, add script tag)

- [ ] **Step 1: Migrate index.html**

In `index.html`:
1. Replace lines 12-41 (the `<nav>...</nav>` block) with: `<div id="nav-placeholder"></div>`
2. Replace lines 330-347 (the `<footer>...</footer>` block) with: `<div id="footer-placeholder"></div>`
3. Add `<script src="components/site-chrome.js"></script>` before the other scripts at bottom (before `<script src="landing-story.js"></script>`)

- [ ] **Step 2: Verify index.html**

Open `index.html` in browser. Confirm nav renders with all links, dark mode toggle works, footer shows default 3-paragraph disclaimer. No visual difference from before.

- [ ] **Step 3: Migrate simulator.html**

Same replacement pattern. Footer placeholder gets: `<div id="footer-placeholder" data-footer-variant="simulator"></div>`

- [ ] **Step 4: Migrate advocacy.html**

Same pattern. Footer placeholder gets: `<div id="footer-placeholder" data-footer-variant="advocacy"></div>`

- [ ] **Step 5: Migrate remaining 10 pages**

Same pattern for: `centers.html`, `center.html`, `compare.html`, `find-centers.html`, `wait-estimator.html`, `organ-guides.html`, `education.html`, `support.html`, `faq.html`, `checklist.html`. All use default footer (no `data-footer-variant` attribute needed).

- [ ] **Step 6: Verify all pages**

Open each of the 13 pages. Confirm:
- Nav renders correctly with correct active link highlighted
- Footer renders with correct variant
- Dark mode toggle works
- Mobile hamburger menu works
- Resources dropdown works

- [ ] **Step 7: Commit**

```bash
git add *.html components/site-chrome.js
git commit -m "refactor: migrate all 13 pages to shared nav/footer component"
```

---

### Task 8: GitHub Contribute Link

**Files:**
- Modify: `index.html` (hero section)

- [ ] **Step 1: Add GitHub link to hero**

In `index.html`, the hero-note paragraph (line 50 after migration, content may shift). Add GitHub link:

```html
<p class="hero-note">This is an open-source project built on public data. If you're a developer, researcher, or transplant advocate, we'd love your help. <a href="https://github.com/rivirside/TransPlan" target="_blank" rel="noopener" style="color:var(--warm-accent);font-weight:600;text-decoration:none;">View on GitHub</a> or <a href="mailto:contact@rivir.social" style="color:var(--warm-accent);font-weight:600;text-decoration:none;">get in touch</a>.</p>
```

The GitHub link in the footer is already handled by `site-chrome.js` (added in Task 5).

- [ ] **Step 2: Verify**

Open `index.html`. Confirm "View on GitHub" link appears in the hero next to "get in touch". Confirm footer has GitHub link. Both open in new tabs.

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "feat: add GitHub contribute link to hero and footer"
```

---

## Chunk 3: Data Explorer Page - Foundation

### Task 9: Acquire TopoJSON Boundary Files

**Files:**
- Create: `data/geo/us-states.topojson`
- Create: `data/geo/us-counties.topojson`

- [ ] **Step 1: Download and simplify US state boundaries**

```bash
mkdir -p data/geo
# Download US states GeoJSON from Census Bureau (20m simplified version)
curl -L -o /tmp/us-states.json "https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json"
# This is already TopoJSON from us-atlas, copy directly
cp /tmp/us-states.json data/geo/us-states.topojson
```

- [ ] **Step 2: Download and simplify US county boundaries**

```bash
# Download US counties TopoJSON from us-atlas (pre-simplified)
curl -L -o data/geo/us-counties.topojson "https://cdn.jsdelivr.net/npm/us-atlas@3/counties-10m.json"
# Check file size (should be <2MB for 10m resolution)
ls -lh data/geo/us-counties.topojson
```

If the file is too large (>2MB), use mapshaper to simplify:
```bash
npx mapshaper data/geo/us-counties.topojson -simplify 20% -o data/geo/us-counties.topojson
```

- [ ] **Step 3: Verify files are valid**

```bash
# Quick validation -- check they parse as JSON and have topology
node -e "var t = require('./data/geo/us-states.topojson'); console.log('States:', Object.keys(t.objects));"
node -e "var t = require('./data/geo/us-counties.topojson'); console.log('Counties:', Object.keys(t.objects));"
```

- [ ] **Step 4: Commit**

```bash
git add data/geo/
git commit -m "data: add US state and county TopoJSON boundaries for choropleth layers"
```

---

### Task 10: Data Explorer Page Scaffold

**Files:**
- Create: `data.html`

- [ ] **Step 1: Create data.html with basic structure**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Data Explorer - transplant.today</title>
    <link rel="stylesheet" href="styles.css">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css">
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css">
    <script src="dark-mode.js"></script>
</head>
<body class="data-page">
    <div id="nav-placeholder"></div>

    <main>
        <div class="data-header">
            <h1>Data Explorer</h1>
            <p>Explore the public datasets that power transplant.today. Toggle layers to visualize wait times, donor supply, health demographics, and more across 248 transplant programs.</p>
        </div>

        <div class="data-map-section">
            <div class="data-map-frame">
                <div id="data-map"></div>
                <!-- Layer panel and legend panel injected by data-explorer.js -->
            </div>
        </div>

        <div class="data-sources">
            <h2>Data Sources</h2>
            <p class="data-sources-sub">All data is sourced from US federal agencies and research registries.</p>
            <div class="data-sources-grid">
                <a href="https://www.srtr.org" target="_blank" rel="noopener" class="data-source-card">
                    <h3><span class="source-badge srtr">SRTR</span> Scientific Registry of Transplant Recipients</h3>
                    <p>Center-level transplant volumes, program details, and post-transplant survival rates for all 248 US programs.</p>
                    <div class="source-meta"><span>248 centers &middot; Quarterly</span><span class="source-link">srtr.org &#8599;</span></div>
                </a>
                <a href="https://optn.transplant.hrsa.gov" target="_blank" rel="noopener" class="data-source-card">
                    <h3><span class="source-badge optn">OPTN</span> Organ Procurement and Transplantation Network</h3>
                    <p>Organ-specific wait times, competing risk probabilities, and OPO service area boundaries.</p>
                    <div class="source-meta"><span>51 OPOs &middot; Quarterly</span><span class="source-link">optn.transplant.hrsa.gov &#8599;</span></div>
                </a>
                <a href="https://www.cdc.gov/places" target="_blank" rel="noopener" class="data-source-card">
                    <h3><span class="source-badge cdc">CDC</span> Centers for Disease Control</h3>
                    <p>County-level health demographics: diabetes, obesity, hypertension, and chronic kidney disease prevalence.</p>
                    <div class="source-meta"><span>3,144 counties &middot; Annually</span><span class="source-link">cdc.gov/places &#8599;</span></div>
                </a>
                <a href="https://www.medicare.gov/care-compare" target="_blank" rel="noopener" class="data-source-card">
                    <h3><span class="source-badge cms">CMS</span> Medicare and Medicaid Services</h3>
                    <p>Hospital quality star ratings, patient safety indicators, and readmission rates.</p>
                    <div class="source-meta"><span>248 hospitals &middot; Quarterly</span><span class="source-link">medicare.gov &#8599;</span></div>
                </a>
                <a href="https://aqs.epa.gov" target="_blank" rel="noopener" class="data-source-card">
                    <h3><span class="source-badge epa">EPA</span> Environmental Protection Agency</h3>
                    <p>Air quality index readings from 2,749 monitoring stations.</p>
                    <div class="source-meta"><span>2,749 monitors &middot; Daily</span><span class="source-link">aqs.epa.gov &#8599;</span></div>
                </a>
                <a href="https://www.nhtsa.gov/research-data" target="_blank" rel="noopener" class="data-source-card">
                    <h3><span class="source-badge nhtsa">NHTSA</span> Highway Traffic Safety</h3>
                    <p>State-level motor vehicle fatality rates. A major source of donor organs via brain death.</p>
                    <div class="source-meta"><span>51 states &middot; Annually</span><span class="source-link">nhtsa.gov &#8599;</span></div>
                </a>
                <a href="https://www.organdonor.gov" target="_blank" rel="noopener" class="data-source-card">
                    <h3><span class="source-badge hrsa">HRSA</span> Health Resources and Services</h3>
                    <p>State-level organ donor registration rates.</p>
                    <div class="source-meta"><span>51 states &middot; Annually</span><span class="source-link">organdonor.gov &#8599;</span></div>
                </a>
                <a href="https://www.bls.gov" target="_blank" rel="noopener" class="data-source-card">
                    <h3><span class="source-badge bls">BLS</span> Bureau of Labor Statistics</h3>
                    <p>Regional cost of living indices.</p>
                    <div class="source-meta"><span>22 metros &middot; Biannually</span><span class="source-link">bls.gov &#8599;</span></div>
                </a>
            </div>
        </div>
    </main>

    <div id="footer-placeholder"></div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
    <script src="https://unpkg.com/topojson-client@3/dist/topojson-client.min.js"></script>
    <script src="components/site-chrome.js"></script>
    <script src="data-explorer.js"></script>
    <script src="donation-banner.js"></script>
    <script src="session.js"></script>
    <!-- Vercel Analytics -->
    <script>
      window.va = window.va || function () { (window.vaq = window.vaq || []).push(arguments); };
    </script>
    <script defer src="/_vercel/insights/script.js"></script>
</body>
</html>
```

- [ ] **Step 2: Add data page CSS to styles.css**

Add at the end of `styles.css` (before any closing comments), scoped under `.data-page`:

```css
/* ===================================================================
   DATA EXPLORER PAGE
   Scoped under .data-page to avoid conflicts.
   =================================================================== */

.data-page {
  background: var(--warm-bg, #faf9f7);
  color: var(--warm-text, #1a1a1a);
}

/* --- Header --- */
.data-header {
  max-width: 1200px;
  margin: 0 auto;
  padding: 32px 48px 20px;
}
.data-header h1 {
  font-size: 26px;
  font-weight: 700;
  margin-bottom: 6px;
}
.data-header p {
  font-size: 15px;
  color: #666;
  line-height: 1.6;
  max-width: 680px;
}

/* --- Map frame --- */
.data-map-section {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 48px;
}
.data-map-frame {
  background: white;
  border: 1px solid var(--warm-border, #e8e4dc);
  border-radius: 14px;
  overflow: hidden;
  height: 660px;
  position: relative;
}
.data-map-frame .leaflet-container {
  border-radius: 14px;
}
.data-page .leaflet-tile {
  filter: saturate(0.3) sepia(0.15);
}

/* --- Marker cluster overrides (neutral color) --- */
.data-page .marker-cluster {
  background: rgba(139, 123, 107, 0.3);
}
.data-page .marker-cluster div {
  background: rgba(139, 123, 107, 0.6);
  color: white;
  font-weight: 700;
  font-size: 12px;
}

/* --- Floating panel base --- */
.data-float-panel {
  position: absolute;
  z-index: 1000;
  background: rgba(250, 249, 247, 0.97);
  border: 1px solid var(--warm-border, #e8e4dc);
  border-radius: 12px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: #d0c8bc transparent;
}

/* Layer panel */
.data-layer-panel {
  top: 14px;
  left: 14px;
  width: 264px;
  max-height: calc(100% - 28px);
}

/* Legend panel */
.data-legend-panel {
  bottom: 14px;
  right: 14px;
  width: 240px;
  max-height: 400px;
}

/* Drag handle */
.drag-handle {
  cursor: grab;
  display: flex;
  align-items: center;
  gap: 6px;
}
.drag-handle:active { cursor: grabbing; }
.drag-dots {
  color: #c0b8ac;
  font-size: 10px;
  letter-spacing: 1px;
}

/* Panel header */
.data-panel-header {
  padding: 14px 16px 0;
  position: sticky;
  top: 0;
  z-index: 2;
  background: inherit;
  border-radius: 12px 12px 0 0;
}
.data-panel-title {
  color: var(--warm-accent, #c97c4a);
  font-weight: 700;
  font-size: 14px;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.data-active-count {
  background: var(--warm-accent, #c97c4a);
  color: white;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 10px;
}

/* Organ pills */
.data-organ-pills {
  display: flex;
  gap: 4px;
  margin-bottom: 12px;
  flex-wrap: wrap;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--warm-border, #e8e4dc);
}
.data-organ-pill {
  padding: 4px 10px;
  border-radius: 14px;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid var(--warm-border, #e8e4dc);
  background: white;
  color: #666;
  transition: all 0.15s;
  user-select: none;
}
.data-organ-pill.active {
  background: var(--warm-accent, #c97c4a);
  color: white;
  border-color: var(--warm-accent, #c97c4a);
}
.data-organ-pill:hover:not(.active) {
  border-color: var(--warm-accent, #c97c4a);
  color: var(--warm-accent, #c97c4a);
}

/* Accordion */
.data-accordion-group {
  border-bottom: 1px solid #f0ece6;
}
.data-accordion-group:last-of-type { border-bottom: none; }
.data-accordion-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  cursor: pointer;
  user-select: none;
}
.data-accordion-header:hover { background: #f5f1ec; }
.data-accordion-arrow {
  color: #8b7b6b;
  font-size: 10px;
  transition: transform 0.2s;
}
.data-accordion-group.open .data-accordion-arrow {
  transform: rotate(90deg);
}
.data-accordion-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 1px;
  font-weight: 600;
  color: #8b7b6b;
}
.data-accordion-count {
  font-size: 10px;
  color: #b0a090;
  margin-left: auto;
}
.data-accordion-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--warm-accent, #c97c4a);
  margin-left: 4px;
  display: none;
}
.data-accordion-group.has-active .data-accordion-dot { display: block; }
.data-accordion-body {
  overflow: hidden;
  max-height: 0;
  transition: max-height 0.25s ease-out;
}
.data-accordion-group.open .data-accordion-body { max-height: 400px; }
.data-accordion-content { padding: 0 16px 10px; }

/* Layer items */
.data-layer-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 8px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  user-select: none;
}
.data-layer-item:hover { background: #f0ece6; }
.data-layer-swatch {
  width: 12px;
  height: 12px;
  border-radius: 3px;
  flex-shrink: 0;
}
.data-layer-swatch.circle { border-radius: 50%; }
.data-layer-check {
  width: 16px;
  height: 16px;
  border: 2px solid #d0c8bc;
  border-radius: 4px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.data-layer-item.active .data-layer-check {
  background: var(--warm-accent, #c97c4a);
  border-color: var(--warm-accent, #c97c4a);
}
.data-layer-item.active .data-layer-check::after {
  content: '\2713';
  color: white;
  font-size: 10px;
  font-weight: 700;
}
.data-layer-meta {
  color: #8b7b6b;
  font-size: 11px;
  margin-left: auto;
}
.data-layer-type {
  font-size: 9px;
  color: #b0a090;
  padding: 1px 5px;
  background: #f5f1ec;
  border-radius: 3px;
  margin-left: 4px;
}

/* Panel footer */
.data-panel-footer {
  padding: 10px 16px 14px;
  border-top: 1px solid var(--warm-border, #e8e4dc);
  display: flex;
  gap: 6px;
}
.data-export-btn {
  padding: 5px 12px;
  border-radius: 5px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid var(--warm-border, #e8e4dc);
  background: white;
  color: #666;
}
.data-export-btn:hover {
  border-color: var(--warm-accent, #c97c4a);
  color: var(--warm-accent, #c97c4a);
}

/* Legend styles */
.data-legend-header {
  padding: 10px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.data-legend-title { font-size: 12px; font-weight: 700; }
.data-legend-body { padding: 0 14px 12px; }
.data-legend-section {
  margin-bottom: 14px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f0ece6;
}
.data-legend-section:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}
.data-legend-section-title {
  font-size: 11px;
  font-weight: 600;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.data-legend-viz-type {
  font-size: 9px;
  color: #8b7b6b;
  background: #f0ece6;
  padding: 1px 5px;
  border-radius: 3px;
}
.data-legend-gradient {
  height: 10px;
  border-radius: 3px;
  width: 100%;
  margin-bottom: 4px;
}
.data-legend-range {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: #8b7b6b;
}
.data-legend-dot-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: #444;
  padding: 2px 0;
}
.data-legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 1.5px solid white;
  box-shadow: 0 0 0 1px rgba(0,0,0,0.1);
  flex-shrink: 0;
}
.data-opacity-control {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
}
.data-opacity-label {
  font-size: 10px;
  color: #8b7b6b;
  white-space: nowrap;
}
.data-opacity-slider {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 4px;
  border-radius: 2px;
  background: #e8e4dc;
  outline: none;
}
.data-opacity-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--warm-accent, #c97c4a);
  cursor: pointer;
  border: 2px solid white;
  box-shadow: 0 1px 4px rgba(0,0,0,0.15);
}
.data-opacity-val {
  font-size: 10px;
  color: var(--warm-accent, #c97c4a);
  font-weight: 600;
  min-width: 28px;
  text-align: right;
}

/* --- Data Sources section --- */
.data-sources {
  max-width: 1200px;
  margin: 0 auto;
  padding: 40px 48px 60px;
}
.data-sources h2 { font-size: 20px; margin-bottom: 4px; }
.data-sources-sub { color: #8b7b6b; font-size: 14px; margin-bottom: 24px; }
.data-sources-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 14px;
}
.data-source-card {
  background: white;
  border: 1px solid var(--warm-border, #e8e4dc);
  border-radius: 10px;
  padding: 16px;
  text-decoration: none;
  color: inherit;
  display: block;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.data-source-card:hover {
  border-color: var(--warm-accent, #c97c4a);
  box-shadow: 0 2px 12px rgba(201,124,74,0.1);
}
.data-source-card h3 {
  font-size: 14px;
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.source-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 10px;
  text-transform: uppercase;
  flex-shrink: 0;
}
.source-badge.srtr { background: #fef3c7; color: #92400e; }
.source-badge.optn { background: #dbeafe; color: #1e40af; }
.source-badge.cdc { background: #d1fae5; color: #065f46; }
.source-badge.cms { background: #ede9fe; color: #5b21b6; }
.source-badge.epa { background: #cffafe; color: #155e75; }
.source-badge.nhtsa { background: #fee2e2; color: #991b1b; }
.source-badge.hrsa { background: #e0e7ff; color: #3730a3; }
.source-badge.bls { background: #fce7f3; color: #9d174d; }
.data-source-card p {
  font-size: 13px;
  color: #666;
  line-height: 1.5;
  margin-top: 4px;
}
.source-meta {
  font-size: 11px;
  color: #8b7b6b;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #f0ece6;
  display: flex;
  justify-content: space-between;
}
.source-link {
  color: var(--warm-accent, #c97c4a);
  font-weight: 600;
}

/* --- Leaflet popup overrides --- */
.data-page .leaflet-popup-content-wrapper { border-radius: 10px; }
.data-page .leaflet-popup-content { margin: 12px 16px; font-family: inherit; }
.data-popup-name { font-weight: 700; font-size: 14px; margin-bottom: 2px; }
.data-popup-loc { color: #8b7b6b; font-size: 12px; margin-bottom: 8px; }
.data-popup-stat {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 3px 0;
  border-bottom: 1px solid #f0ece6;
  font-size: 12px;
}
.data-popup-stat:last-child { border: none; }
.data-popup-val { font-weight: 600; color: var(--warm-accent, #c97c4a); }

/* --- Dark mode --- */
[data-dark="true"] .data-page {
  background: #1a1710;
  color: #e8e4dc;
}
[data-dark="true"] .data-map-frame {
  background: #232019;
  border-color: #2a2520;
}
[data-dark="true"] .data-float-panel {
  background: rgba(35, 32, 25, 0.97);
  border-color: #2a2520;
}
[data-dark="true"] .data-source-card {
  background: #232019;
  border-color: #2a2520;
}
[data-dark="true"] .data-header p { color: #a09080; }
```

- [ ] **Step 3: Verify page renders**

Open `data.html` in browser. Confirm:
- Nav and footer render via site-chrome.js with "Data" link highlighted
- Page header shows title and description
- Map frame is visible (empty map area for now)
- Data sources cards render below with correct badges and hover effects
- Dark mode works

- [ ] **Step 4: Commit**

```bash
git add data.html styles.css
git commit -m "feat: scaffold data.html page with header, map frame, and source cards"
```

---

### Task 11: Data Explorer JS - Map + Center Dots

**Files:**
- Create: `data-explorer.js`

This task creates the main JavaScript file with: map init, center data loading, center dot layer with wait-time coloring, marker clustering, center popups, and the layer/legend panel DOM.

Due to the size of this file, the implementer should reference the brainstorming mockups in `.superpowers/brainstorm/89739-1774555430/data-page-draggable.html` for the exact panel HTML structure and interactions.

- [ ] **Step 1: Create data-explorer.js with map initialization**

Create `data-explorer.js` as an IIFE. Initialize the Leaflet map with CartoDB Positron tiles, canvas renderer, centered on US. Load center data from `data/srtr-all-centers.json`.

Key implementation points:
- Map: `L.map('data-map', { preferCanvas: true, zoomControl: true }).setView([39.5, -98.5], 4)`
- Tiles: `https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png`
- MarkerClusterGroup with neutral cluster styling (override `iconCreateFunction`)
- Wait-time color function: green (#2d9e5c) to red (#e05252) based on center wait factor
- Center popup with name, location, SRTR code, and active layer stats

- [ ] **Step 2: Build layer panel DOM**

Programmatically create the floating layer panel with:
- Drag handle in title bar
- Organ filter pills (All, Kidney, Liver, Heart, Lung, Pancreas, Intestine)
- 4 accordion groups (Center, State, County, Point) with layer items
- Each layer item: checkbox, color swatch, name, type badge, source label
- Export buttons in footer
- Insert into `.data-map-frame`

- [ ] **Step 3: Build legend panel DOM**

Create the floating legend panel with:
- Drag handle
- Dynamic legend sections (one per active layer)
- Each section: gradient/dot scale, value range, opacity slider
- Insert into `.data-map-frame`

- [ ] **Step 4: Wire layer toggles**

- Checkbox click toggles layer on/off
- Radio behavior within center-dot group (one color + one size encoding)
- Radio behavior within state fill group
- Radio behavior within county fill group
- Active count badge updates
- Accordion dot indicator updates
- Legend panel updates (show/hide legend sections for active layers)

- [ ] **Step 5: Wire organ filter pills**

- Click pill to filter center data by organ type
- Centers not offering the selected organ are hidden
- "All" shows all 248 centers
- Update cluster group

- [ ] **Step 6: Implement draggable panels**

- Mousedown on drag handle starts drag
- Mousemove updates panel position (clamped to map frame bounds)
- Mouseup ends drag
- Both panels independently draggable

- [ ] **Step 7: Verify map with center dots**

Open `data.html`. Confirm:
- Map renders with CartoDB tiles and sepia filter
- 248 centers shown as colored dots (green-to-red by wait time)
- Nearby centers cluster into neutral-colored numbered circles
- Clicking a center shows popup with stats
- Layer panel toggles work (checkboxes, radio behavior)
- Legend updates when layers toggle
- Organ pills filter centers
- Panels are draggable

- [ ] **Step 8: Commit**

```bash
git add data-explorer.js
git commit -m "feat: data explorer map with center dots, clustering, layer panel, and legend"
```

---

## Chunk 4: Data Explorer - Choropleth Layers + Export

### Task 12: State Choropleth Layers

**Files:**
- Modify: `data-explorer.js` (add state layer logic)

- [ ] **Step 1: Add state choropleth rendering**

Add functions to `data-explorer.js`:
- `loadStatesGeo()`: fetch `data/geo/us-states.topojson`, convert with `topojson.feature()`, cache
- `renderStateChoropleth(dataFile, colorScale, property)`: load data file on demand, join with state geometry by FIPS/state code, render as L.geoJSON with stepped color fill
- Wire to layer toggle for: donor registration, traffic fatalities, policy tiers
- Add to map at z-index below center dots (use `map.getPane('overlayPane')` or create custom pane)
- Opacity slider in legend controls layer opacity via `layer.setStyle({ fillOpacity: value })`

- [ ] **Step 2: Define color scales**

Discrete stepped scales for each state layer:
- Donor registration: 5 blue buckets from #dbeafe to #3b82f6
- Traffic fatalities: 6 red buckets from #fecaca to #991b1b (matching existing simulator map)
- Policy tiers: 5 green buckets from #d1fae5 to #065f46

- [ ] **Step 3: Verify state layers**

Toggle each state layer. Confirm:
- States fill with correct colors
- Only one state layer at a time (radio behavior)
- Opacity slider works
- Legend shows stepped color scale
- Center dots remain visible on top

- [ ] **Step 4: Commit**

```bash
git add data-explorer.js
git commit -m "feat: state choropleth layers (donor registration, fatalities, policy tiers)"
```

---

### Task 13: County Choropleth Layers

**Files:**
- Modify: `data-explorer.js`

- [ ] **Step 1: Add county choropleth rendering**

Same pattern as state, but:
- `loadCountiesGeo()`: fetch `data/geo/us-counties.topojson`, convert, cache
- Join with `health-demographics-counties.json` by FIPS code
- 4 layers: diabetes, obesity, hypertension, smoking
- Render below state layer in z-order (create `countyPane` with zIndex 350)
- Default opacity 40%

- [ ] **Step 2: Verify county layers**

Toggle a county layer + a state layer simultaneously. Confirm:
- Both render without obscuring each other
- Opacity sliders work independently
- Radio within county group
- Center dots visible on top of both fills

- [ ] **Step 3: Commit**

```bash
git add data-explorer.js
git commit -m "feat: county choropleth layers (diabetes, obesity, hypertension, smoking)"
```

---

### Task 14: EPA Monitor Layer

**Files:**
- Modify: `data-explorer.js`

- [ ] **Step 1: Add EPA layer**

- Load `data/air-quality-monitors.json` on demand
- Render 2,749 monitors as small circle markers (radius 3-4)
- Color: cyan (#06b6d4) variants by AQI bucket (good/moderate/poor)
- Add to separate cluster group or directly (2,749 points is fine with canvas renderer)
- Z-index above county fill, below center dots

- [ ] **Step 2: Verify**

Toggle EPA layer. Confirm monitors render across the US, don't obscure center dots, opacity slider works.

- [ ] **Step 3: Commit**

```bash
git add data-explorer.js
git commit -m "feat: EPA air quality monitor layer (2,749 points)"
```

---

### Task 15: Export Functionality

**Files:**
- Modify: `data-explorer.js`

- [ ] **Step 1: Implement CSV export**

When "CSV" button clicked:
- Collect center data for all currently active center layers, filtered by selected organ
- Build CSV with columns: center_name, city, state, srtr_code, lat, lon, + one column per active layer
- Trigger download via Blob + URL.createObjectURL

- [ ] **Step 2: Implement JSON export**

Same data, exported as JSON array of objects.

- [ ] **Step 3: Verify exports**

Toggle some layers, filter by organ, click CSV and JSON. Open downloaded files and verify data is correct and filtered.

- [ ] **Step 4: Commit**

```bash
git add data-explorer.js
git commit -m "feat: CSV and JSON export for center data"
```

---

### Task 16: Mobile Responsive

**Files:**
- Modify: `styles.css` (add data page mobile breakpoints)

- [ ] **Step 1: Add mobile styles**

```css
@media (max-width: 768px) {
  .data-header { padding: 24px 20px 16px; }
  .data-header h1 { font-size: 22px; }
  .data-map-section { padding: 0 16px; }
  .data-map-frame { height: 400px; }
  .data-layer-panel {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    top: auto;
    width: 100%;
    max-height: 50vh;
    border-radius: 14px 14px 0 0;
    z-index: 1100;
  }
  .data-legend-panel {
    display: none; /* legend in bottom sheet on mobile, or hidden */
  }
  .data-sources { padding: 24px 20px 40px; }
  .data-sources-grid { grid-template-columns: 1fr; }
}
```

- [ ] **Step 2: Test on mobile viewport**

Resize browser to 375px wide. Confirm map, panels, and source cards work.

- [ ] **Step 3: Commit**

```bash
git add styles.css
git commit -m "feat: data explorer mobile responsive layout"
```

---

### Task 17: Final Verification

- [ ] **Step 1: Full page test**

Open `data.html` and verify the complete flow:
- Map loads with 248 clustered center dots
- Layer panel: toggle each layer, radio behavior works
- Legend updates dynamically with opacity sliders
- Organ pills filter centers
- State + county choropleth stacking works
- EPA monitors render
- Export CSV/JSON works
- Panels are draggable
- Center popups show correct data
- Dark mode works
- Mobile layout works
- Data source cards link to correct URLs

- [ ] **Step 2: Test all other pages still work**

Quick check: `index.html`, `simulator.html`, `centers.html` all load correctly with shared nav/footer.

- [ ] **Step 3: Update sitemap.xml**

Add `data.html` to `sitemap.xml`.

- [ ] **Step 4: Final commit**

```bash
git add sitemap.xml
git commit -m "chore: add data.html to sitemap"
```
