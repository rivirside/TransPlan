# TransPlan - Design Document

> **Read this file in full when working on UI, UX, CSS, layout, or visual changes.**

## Design Philosophy

TransPlan is a medical information tool. The design prioritizes **clarity, trust, and accessibility** over flashiness. Users are transplant patients or caregivers making life-altering decisions - the interface should feel calm, authoritative, and easy to scan.

## Design System

All visual properties are defined as CSS custom properties (design tokens) in `:root` at the top of `styles.css`. Always use tokens instead of hardcoded values.

### Token Categories
- **Colors**: `--color-primary`, `--text-1` through `--text-muted`, `--surface`, `--bg`, `--border`, `--success/warning/danger`
- **Spacing**: `--space-1` (4px) through `--space-10` (64px), 8px base grid
- **Shadows**: `--shadow-sm`, `--shadow-md`, `--shadow-lg`
- **Radii**: `--radius-sm` (6px), `--radius-md` (10px), `--radius-lg` (16px), `--radius-full` (pill)
- **Typography**: `--fs-xs` (0.75rem) through `--fs-3xl` (2.25rem), ~1.25 ratio

## Layout Structure

The page is a single vertical scroll with distinct sections:

```
[Header]          - Gradient header with curved bottom edge
[Main card]       - White floating card overlapping header
  [About]         - Info card with disclaimer banner
  [Form]          - Health profile input (fieldsets + grid)
  [Methodology]   - Accordion list + donut chart + example calc
  [Results]       - Hidden until form submit, then:
    [Freshness]   - Data freshness banner
    [Tabs]        - Location Scores / Simulation Probabilities toggle
    [Map]         - Leaflet interactive map + overlay controls
    [City Cards]  - Ranked cards with radar charts (scores tab)
    [Prob Cards]  - Probability cards with competing risks (prob tab)
    [Charts]      - Comparison bar / CDF curves / competing risks
    [Data Sources]- Attribution
[Footer]          - Disclaimer card
```

## Color Palette

| Role | Hex | CSS Token | Usage |
|------|-----|-----------|-------|
| Primary | `#5B6FE6` | `--color-primary` | Header gradient, buttons, accents |
| Primary dark | `#4A5BC7` | `--color-primary-dark` | Hover states |
| Primary light | `#E8ECFB` | `--color-primary-light` | Score backgrounds, tints |
| Accent | `#6B52AE` | `--color-accent` | Gradient end (header, submit btn) |
| Text primary | `#1A1D2E` | `--text-1` | Headings (15.5:1 contrast) |
| Text secondary | `#4A4F65` | `--text-2` | Body text (7.8:1) |
| Text tertiary | `#6B7185` | `--text-3` | Labels, captions (4.8:1) |
| Text muted | `#9CA3B5` | `--text-muted` | Placeholders, disabled |
| Surface | `#FFFFFF` | `--surface` | Cards, main content |
| Surface raised | `#F7F8FB` | `--surface-raised` | Metrics, results bg |
| Surface sunken | `#F0F2F7` | `--surface-sunken` | Methodology bg |
| Page bg | `#F4F5F9` | `--bg` | Body background |
| Border | `#E2E5ED` | `--border` | Dividers, card borders |
| Success | `#1D9E5C` | `--success` | Good metrics, fresh data |
| Warning | `#D4860A` | `--warning` | Moderate metrics, stale data |
| Danger | `#D93B3B` | `--danger` | Poor metrics, errors |
| Gold (rank 1) | `#E8B931` | — | First place border |
| Silver (rank 2) | `#A0A4AB` | — | Second place border |
| Bronze (rank 3) | `#C08B5C` | — | Third place border |

## Typography

- **Font stack**: System fonts only (`-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, ...`)
- **No custom fonts** - fast loading, native feel
- **Scale** (~1.25 ratio): `--fs-xs` (0.75rem) → `--fs-3xl` (2.25rem)
- **Anti-aliasing**: `-webkit-font-smoothing: antialiased`

## Component Details

### Header
- Gradient: `135deg, --color-primary → --color-accent`
- Curved bottom via `::after` pseudo-element (body bg + rounded top corners)
- Main card overlaps header by 40px for depth effect
- No text-shadow; negative letter-spacing on h1

### Form
- Two `<fieldset>` groups: "Required Information" + "Optional Details"
- Small uppercase `<legend>` labels with bottom border
- Grid: `auto-fit, minmax(250px, 1fr)` — responsive without media queries
- Focus rings: 3px blue glow (`box-shadow: 0 0 0 3px rgba(91,111,230,0.15)`)
- Submit button: `max-width: 400px`, centered, gradient background

### Methodology Section
- **Accordion** using native `<details>/<summary>` (no JS needed)
- Each row: SVG icon + title + weight bar + percentage + chevron
- Click to expand/collapse factor details
- SVG icons: Lucide-style line icons with `stroke="currentColor"`
- Weight bar: 4px height, fills proportionally to percentage

### City Cards
- Left border: 4px colored by rank (gold/silver/bronze/primary)
- Hover: `translateY(-2px)` lift + enhanced shadow
- Uppercase small labels with letter-spacing for dashboard feel
- Rank badge: solid primary color pill (not gradient)
- Score, metrics grid, radar chart, factors list inside

### Probability Cards
- Same visual treatment as city cards (consistent design language)
- Metrics grid with rounded background tiles
- Competing risks horizontal bar (6px height)
- Risk legend with colored dots

### Results Tabs
- Toggle: solid active color (`--color-primary`), not gradient
- 1.5px border, rounded corners
- Tabs: "Location Scores" and "Simulation Probabilities"

### Factors Lists
- Small 5px green dots instead of text checkmarks

### Map
- 500px height desktop, 400px tablet, 300px mobile
- Cleaner overlay toggles with `accent-color` checkboxes
- Collapsible overlay controls on mobile

### Charts (Chart.js)
- Radar (per card): 8 axes, 250px max height
- Comparison bar: grouped by city, 8 colored bars
- Donut: methodology weights
- CDF curves: probability over time (top 5 cities)
- Competing risks: stacked horizontal bar (top 10 cities)

## Responsive Breakpoints

Two breakpoints:

**768px (tablet):**
- Header shrinks to `--fs-2xl`
- Form collapses to single column
- Weight bars hidden in accordion
- Map: 400px height
- Overlay controls stack vertically + collapsible

**480px (mobile):**
- Header shrinks to `--fs-xl`
- Tighter padding (--space-5 for sections)
- Metrics stack to single column
- Map: 300px height
- Tabs stretch full width

## Session UI (Local Only)

When running locally via `start.command`, a session bar appears at the bottom:

- **Position**: Fixed bottom, full width, z-index 10000
- **Background**: `rgba(26, 29, 46, 0.94)` with `backdrop-filter: blur(10px)`
- **Left**: Green dot (8px, `#4ade80`) + "Local session active"
- **Right**: Red "End Session" button
- **Source**: `session.js` (creates DOM elements dynamically)

## CSS Organization (styles.css)

Sections in order:
1. Design tokens (`:root`)
2. Reset + base (body, container)
3. Header (gradient + curve)
4. Main card
5. Info card + disclaimer banners
6. Form (fieldsets, grid, inputs, range, submit)
7. Methodology (accordion + legacy grid fallback)
8. Calculation + methodology footer
9. Freshness banner
10. Spinner
11. Results section + tabs
12. Map + overlay controls
13. City cards + metrics + factors
14. Probability cards + risk bars
15. Charts
16. Data sources
17. Footer + disclaimer
18. CDN fallback
19. Session bar
20. Responsive: 768px
21. Responsive: 480px

## Things to Maintain

- Always use design tokens — never hardcode colors, spacing, or radii
- Keep system font stack — no external font dependencies
- Maintain the indigo/purple gradient identity (header + submit button only)
- Rank colors (gold/silver/bronze) are meaningful — don't change arbitrarily
- All text must meet WCAG AA contrast (4.5:1 minimum)
- Preserve all CSS class names used by script.js, charts.js, probability-charts.js, session.js
