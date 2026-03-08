# TransPlan - Brand & Visual Identity Bible

> **Grep-searchable.** Reference when making visual, copy, or branding decisions.

## Brand Identity

### Name
**TransPlan** (also referred to as **TransplantMatch** in the HTML title and header). The canonical project name is TransPlan. The user-facing display name is "TransplantMatch."

### Tagline
"Explore transplant center locations with data-driven comparison tools"

### Voice & Tone
- **Authoritative but not clinical** - we explain complex medical data in plain language
- **Supportive, not alarming** - users are in a vulnerable situation
- **Data-forward** - always show the evidence behind recommendations
- **Transparent** - methodology is visible, not a black box
- **No hype** - avoid superlatives, promises, or guarantees

### Disclaimer (required)
Always present in footer: "This tool provides informational insights only and should not replace consultation with your transplant team and healthcare providers. Actual transplant outcomes depend on many individual factors."

## Color System

All colors are defined as CSS custom properties in `:root`. Use tokens, not hex values.

### Primary Palette
| Name | Hex | Token | Usage |
|------|-----|-------|-------|
| Primary | `#5B6FE6` | `--color-primary` | Buttons, accents, active states |
| Primary dark | `#4A5BC7` | `--color-primary-dark` | Hover states |
| Primary light | `#E8ECFB` | `--color-primary-light` | Tinted backgrounds |
| Accent | `#6B52AE` | `--color-accent` | Gradient end (header, submit) |

### Gradient
```css
background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
```
Used on: header only (+ submit button). Body uses flat `--bg` (#F4F5F9).

### Text Colors
| Name | Hex | Token | Contrast | Usage |
|------|-----|-------|----------|-------|
| Primary | `#1A1D2E` | `--text-1` | 15.5:1 | Headings |
| Secondary | `#4A4F65` | `--text-2` | 7.8:1 | Body text |
| Tertiary | `#6B7185` | `--text-3` | 4.8:1 | Labels, captions |
| Muted | `#9CA3B5` | `--text-muted` | — | Placeholders, disabled |

### Surface Colors
| Name | Hex | Token | Usage |
|------|-----|-------|-------|
| Surface | `#FFFFFF` | `--surface` | Cards, main content |
| Raised | `#F7F8FB` | `--surface-raised` | Metrics tiles, results bg |
| Sunken | `#F0F2F7` | `--surface-sunken` | Methodology section bg |
| Page bg | `#F4F5F9` | `--bg` | Body background |
| Border | `#E2E5ED` | `--border` | Dividers, input borders |

### Semantic Colors
| Name | Hex | Token | Meaning |
|------|-----|-------|---------|
| Success | `#1D9E5C` | `--success` | Good score (>=90), fresh data |
| Warning | `#D4860A` | `--warning` | Moderate score (80-89), stale data |
| Danger | `#D93B3B` | `--danger` | Poor score (<80), errors |

### Rank Colors
| Rank | Color | Hex |
|------|-------|-----|
| #1 | Gold | `#E8B931` |
| #2 | Silver | `#A0A4AB` |
| #3 | Bronze | `#C08B5C` |
| #4+ | Primary | `#5B6FE6` |

### Chart Colors (8-color palette for scoring categories)
```javascript
['#667eea', '#764ba2', '#f093fb', '#f5576c',
 '#4facfe', '#00f2fe', '#43e97b', '#fa709a']
```
These map 1:1 to the 8 scoring categories in order.

## Typography

### Font Stack
```css
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
```
System fonts only. No external font dependencies. No Google Fonts.

### Scale (~1.25 ratio)
| Token | Size | Usage |
|-------|------|-------|
| `--fs-xs` | 0.75rem | Micro labels, dots |
| `--fs-sm` | 0.8125rem | Small text, legends |
| `--fs-base` | 0.9375rem | Body text |
| `--fs-md` | 1rem | Inputs, tagline |
| `--fs-lg` | 1.125rem | Chart headings |
| `--fs-xl` | 1.375rem | Section headings, card titles |
| `--fs-2xl` | 1.75rem | Page section h2 |
| `--fs-3xl` | 2.25rem | Page title h1 |

## Spacing & Layout

### Spacing Scale (8px base)
```
--space-1: 4px    --space-6: 24px
--space-2: 8px    --space-7: 32px
--space-3: 12px   --space-8: 40px
--space-4: 16px   --space-9: 48px
--space-5: 20px   --space-10: 64px
```

### Shadows
| Token | Value | Usage |
|-------|-------|-------|
| `--shadow-sm` | `0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)` | Cards, inputs |
| `--shadow-md` | `0 4px 12px rgba(0,0,0,0.08)` | Hover states, map legend |
| `--shadow-lg` | `0 8px 24px rgba(0,0,0,0.10)` | Main card |

### Border Radius
| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm` | 6px | Inputs, metrics, banners |
| `--radius-md` | 10px | Cards, map section |
| `--radius-lg` | 16px | Main card, header curve |
| `--radius-full` | 9999px | Badges, pills |

### Container
- Max width: 1200px
- Padding: `--space-5` (20px)
- Centered with `margin: 0 auto`

### Responsive
- Two breakpoints: `768px` (tablet) and `480px` (mobile)
- Below 768px: single-column, smaller headings, shorter map
- Below 480px: tighter padding, stacked metrics, full-width tabs

## Iconography

Methodology section uses inline SVG icons (Lucide-style, `stroke="currentColor"`):

| Category | Icon |
|----------|------|
| Medical Compatibility | Stethoscope |
| Wait Time | Clock |
| Donor Availability | Heart |
| Hospital Quality | Building/Home |
| Geographic | Globe |
| Health Demographics | Activity/Pulse |
| Policy & Legal | Shield/Check |
| Socioeconomic | Users |

No icon library is used. Icons are inline SVGs for zero external dependencies.

## Map Styling

- Provider: OpenStreetMap tiles
- Default zoom: 4 (continental US)
- Center: 39.8283, -98.5795
- Height: 500px desktop, 400px tablet, 300px mobile
- Heatmap plugin: `leaflet.heat`

## Copy Guidelines

- Use "city" not "location" or "center" when referring to ranked results
- Use "score" not "rating" or "grade"
- Use "category" not "factor" or "dimension" when referring to the 8 scoring groups
- Spell out organ names (kidney, not KD)
- Use "Status 1-4" for urgency, matching UNOS terminology
- Always attribute data sources
