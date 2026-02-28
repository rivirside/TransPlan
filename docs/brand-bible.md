# TransPlan - Brand & Visual Identity Bible

> **Grep-searchable.** Reference when making visual, copy, or branding decisions.

## Brand Identity

### Name
**TransPlan** (also referred to as **TransplantMatch** in the HTML title and header). The canonical project name is TransPlan. The user-facing display name is "TransplantMatch."

### Tagline
"Optimize your transplant outcomes through data-driven location insights"

### Voice & Tone
- **Authoritative but not clinical** - we explain complex medical data in plain language
- **Supportive, not alarming** - users are in a vulnerable situation
- **Data-forward** - always show the evidence behind recommendations
- **Transparent** - methodology is visible, not a black box
- **No hype** - avoid superlatives, promises, or guarantees

### Disclaimer (required)
Always present in footer: "This tool provides informational insights only and should not replace consultation with your transplant team and healthcare providers. Actual transplant outcomes depend on many individual factors."

## Color System

### Primary Palette
| Name | Hex | RGB | Usage |
|------|-----|-----|-------|
| Indigo | `#667eea` | 102, 126, 234 | Primary accent, buttons, links, chart color 1 |
| Purple | `#764ba2` | 118, 75, 162 | Gradient end, chart color 2 |

### Background Gradient
```css
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
```
Used on: body, submit button, info card

### Semantic Colors
| Name | Hex | Meaning |
|------|-----|---------|
| Green | `#27ae60` | Good score (>=90), fresh data (<30 days), positive metric |
| Amber | `#f39c12` | Moderate score (80-89), stale data (30-90 days) |
| Red | `#e74c3c` | Poor score (<80), expired data (>90 days) |

### Rank Colors
| Rank | Color | Hex |
|------|-------|-----|
| #1 | Gold | `#ffd700` |
| #2 | Silver | `#c0c0c0` |
| #3 | Bronze | `#cd7f32` |
| #4+ | Indigo | `#667eea` |

### Chart Colors (8-color palette for scoring categories)
```javascript
['#667eea', '#764ba2', '#f093fb', '#f5576c',
 '#4facfe', '#00f2fe', '#43e97b', '#fa709a']
```
These map 1:1 to the 8 scoring categories in order.

### Neutrals
| Name | Hex | Usage |
|------|-----|-------|
| Near-black | `#333` | Primary text |
| Dark gray | `#555` | Secondary text, labels |
| Light gray | `#f8f9fa` | Results section background |
| White | `#fff` | Content areas, card backgrounds |
| Border | `#eee` | Subtle dividers |

## Typography

### Font Stack
```css
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
```
System fonts only. No external font dependencies. No Google Fonts.

### Scale
| Element | Size | Weight |
|---------|------|--------|
| Page title (h1) | 3rem (2rem mobile) | Bold |
| Section headings (h2) | ~1.5rem | Bold |
| Card headings (h3) | ~1.17rem | Bold |
| Sub-headings (h4) | ~1rem | Semi-bold |
| Body text | 1rem (16px) | Normal |
| Small text / notes | 0.9rem | Normal |
| Micro text (dots, labels) | 0.75rem | Normal |

## Spacing & Layout

### Container
- Max width: 1200px
- Padding: 20px
- Centered with `margin: 0 auto`

### Cards
- Padding: 25px
- Border-radius: 12px
- Box-shadow: `0 4px 15px rgba(0,0,0,0.1)`
- Hover: `translateX(5px)` + enhanced shadow

### Grid
- Form grid: `repeat(auto-fit, minmax(250px, 1fr))`
- Methodology grid: `repeat(auto-fit, minmax(300px, 1fr))`
- Metrics grid: `repeat(auto-fit, minmax(150px, 1fr))`

### Responsive
- Single breakpoint: `768px`
- Below 768px: single-column layouts, smaller headings, shorter map

## Iconography

Methodology cards use emoji as section icons:
| Category | Emoji |
|----------|-------|
| Medical Compatibility | :stethoscope: |
| Wait Time | :stopwatch: |
| Donor Availability | :anatomical_heart: |
| Hospital Quality | :hospital: |
| Geographic | :globe_showing_Europe-Africa: |
| Health Demographics | :bar_chart: |
| Policy & Legal | :balance_scale: |
| Socioeconomic | :handshake: |

No icon library is used. If icons are needed beyond methodology, prefer emoji or inline SVG.

## Map Styling

- Provider: OpenStreetMap tiles
- Default zoom: 4 (shows continental US)
- Center: 39.8283, -98.5795 (geographic center of US)
- Height: 600px desktop, 400px mobile
- Heatmap plugin: `leaflet.heat`

## Copy Guidelines

- Use "city" not "location" or "center" when referring to ranked results
- Use "score" not "rating" or "grade"
- Use "category" not "factor" or "dimension" when referring to the 8 scoring groups
- Spell out organ names (kidney, not KD)
- Use "Status 1-4" for urgency, matching UNOS terminology
- Always attribute data sources
