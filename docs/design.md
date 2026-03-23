# TransPlan - Design Document

> **Read this file in full when working on UI, UX, CSS, layout, or visual changes.**

## Design Philosophy

TransPlan is a medical information tool. The design prioritizes **clarity, trust, and accessibility** over flashiness. Users are transplant patients or caregivers making life-altering decisions - the interface should feel calm, authoritative, and easy to scan.

## Design System (Phase 7 — March 2026)

Single polished design. No themes. All visual properties in CSS custom properties in `:root` at the top of `styles.css`.

### Token Categories
- **Colors**: Indigo primary scale (`--color-primary-50` through `--color-primary-900`), violet accent scale, blue-gray neutrals
- **Spacing**: `--space-1` (4px) through `--space-10` (64px), 4px base grid
- **Shadows**: `--shadow-xs` through `--shadow-xl` (subtle depth, not dramatic)
- **Radii**: `--radius-xs` (4px), `--radius-sm` (6px), `--radius-md` (8px), `--radius-lg` (12px), `--radius-full` (pill)
- **Typography**: System font stack (`-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, ...`). Base size 15px (`--fs-base: 0.9375rem`). Scale from `--fs-xs` (0.75rem) through `--fs-4xl` (2.75rem)

### Dark Mode
Light mode is default. User can toggle via moon/sun button in nav. Stored in `localStorage('transplan-dark')`. Dark mode inverts neutral/surface/text tokens via `[data-dark="true"]` CSS. OS preference auto-detection disabled — explicit user toggle only.

## Layout Structure

### Landing Page (index.html)
```
[Nav]             - Sticky dark indigo bar: Logo | Simulator | Docs | Dark toggle
[Hero]            - Centered: headline, description, CTA button + ghost link
[Features]        - 3x2 card grid (icon + title inline, description below)
[How It Works]    - 4-step horizontal flow with numbered circles
[Data Trust]      - Centered: "Powered by Trusted Public Data" + 6 source badges
[CTA]             - "Ready to explore?" + Launch Simulator button
[Disclaimer]      - Yellow banner
[Footer]          - Disclaimer text + links + contact
```

### Simulator Page (simulator.html)
```
[Nav]             - Same as landing (Home active on landing, Simulator active here)
[App Layout]      - CSS Grid: 340px sidebar + 1fr main content
  [Sidebar]       - Sticky, scrollable:
    Disclaimer    - Compact one-liner with link
    Form          - 4 fieldsets, single-column layout
    Submit button - Full-width indigo
    Method link   - "How our algorithm works →"
  [Main Content]  - Scrollable:
    Empty state   - Heart icon + instructions (hidden after submit)
    Results       - Data freshness, tabs (Scores/Probs/Equity), map, city cards, charts
    Methodology   - Collapsed <details> at bottom
[Footer]          - Disclaimer
[Modals]          - City detail + comparison (unchanged)
```

Responsive: sidebar collapses to top panel at ≤1024px, single column at ≤768px with hamburger nav.

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

- **Font stack**: System fonts (`-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif`)
- **No custom fonts** — no Google Fonts dependency, fast loading, native feel
- **Base size**: 15px (`--fs-base: 0.9375rem`) — up from 13px in Phase 6
- **Scale**: `--fs-xs` (0.75rem) → `--fs-4xl` (2.75rem)
- **Line height**: 1.55 (body)
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
