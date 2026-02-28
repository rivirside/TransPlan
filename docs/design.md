# TransPlan - Design Document

> **Read this file in full when working on UI, UX, CSS, layout, or visual changes.**

## Design Philosophy

TransPlan is a medical information tool. The design prioritizes **clarity, trust, and accessibility** over flashiness. Users are transplant patients or caregivers making life-altering decisions - the interface should feel calm, authoritative, and easy to scan.

## Layout Structure

The page is a single vertical scroll with distinct sections:

```
[Header]          - Title + tagline
[About]           - Brief info card
[Form]            - Health profile input (grid layout)
[Methodology]     - How the algorithm works (card grid + donut chart + example calc)
[Results]         - Hidden until form submit, then:
  [Freshness]     - Data freshness banner
  [Map]           - Leaflet interactive map + overlay controls
  [City Cards]    - Ranked cards with radar charts
  [Comparison]    - Grouped bar chart
  [Data Sources]  - Attribution
[Footer]          - Disclaimer
```

## Color Palette

| Role | Color | Hex | Usage |
|------|-------|-----|-------|
| Primary gradient start | Muted indigo | `#667eea` | Header, buttons, accents |
| Primary gradient end | Purple | `#764ba2` | Background gradient |
| Background | White | `#ffffff` | Main content area |
| Results background | Light gray | `#f8f9fa` | Results section bg |
| Text primary | Dark gray | `#333333` | Body text |
| Text secondary | Medium gray | `#555555` | Labels, descriptions |
| Good/positive | Green | `#27ae60` | High scores, fresh data |
| Moderate/warning | Amber | `#f39c12` | Mid scores, stale data |
| Poor/error | Red | `#e74c3c` | Low scores, expired data |
| Gold (rank 1) | Gold | `#ffd700` | First place border |
| Silver (rank 2) | Silver | `#c0c0c0` | Second place border |
| Bronze (rank 3) | Bronze | `#cd7f32` | Third place border |

## Typography

- **Font stack**: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif`
- **No custom fonts** - system fonts for fast loading and native feel
- **Header h1**: 3rem (2rem on mobile)
- **Body text**: default browser size (~16px)
- **Methodology note**: 0.9rem, lighter weight

## Component Details

### Form
- Grid layout: `auto-fit, minmax(250px, 1fr)` - responsive without media queries
- Required fields marked with `*` in labels
- Submit button: gradient background matching header, slight scale on hover
- All inputs have consistent border-radius: 8px

### City Cards
- Left border color by rank (gold/silver/bronze/purple)
- Hover: `translateX(5px)` slide animation
- Contains: header (city + rank badge), score, metrics grid, radar chart, factors list
- Score value is color-coded: green (>=90), amber (80-89), red (<80)
- Radar chart shows 8-axis breakdown at ~250px height

### Map
- Leaflet with OpenStreetMap tiles
- 600px height (400px on mobile)
- 10 toggle-able overlay layers (checkboxes)
- Map controls in a sidebar grid

### Charts (Chart.js)
- **Radar** (per card): 8 axes, blue fill, no legend, small font labels
- **Comparison bar**: grouped by city (top 10), 8 colored bars per city, legend at bottom
- **Donut**: methodology section, 8 segments matching scoring weights, legend at bottom
- Chart colors match `CHART_COLORS` array in charts.js

### Freshness Banner
- Colored left border (green/amber/red based on age)
- Shows last update date + per-source status dots
- Small font (0.75-0.9rem)

## Responsive Breakpoints

Single breakpoint at `768px`:
- Header shrinks to 2rem
- Form collapses to single column
- Map height reduces to 400px
- Overlay controls stack vertically

## Accessibility Notes

- Form fields have proper `<label>` elements with `for` attributes
- Required fields use HTML5 `required` attribute
- Color is not the sole indicator - text labels accompany colored values
- Map overlay toggles use native checkboxes

## CSS Organization (styles.css)

Sections in order:
1. Global reset + body
2. Container + header
3. Main layout
4. Info card
5. Form styling
6. Results section
7. City card styling
8. Score + metrics
9. Factors list
10. Data sources
11. Footer
12. Map styling
13. Methodology section
14. Freshness banner (new)
15. Chart containers (new)
16. Responsive media queries

## Things to Maintain

- Keep the system font stack - no external font dependencies
- Maintain the purple/indigo gradient identity
- Charts should use the `CHART_COLORS` array for consistency
- Rank colors (gold/silver/bronze) are meaningful - don't change arbitrarily
- Score color thresholds (90/80) are referenced in both JS and CSS
