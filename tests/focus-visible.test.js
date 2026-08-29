/**
 * Keyboard focus must be visible on every interactive element.
 *
 * WCAG 2.1 SC 2.4.7 (Focus Visible, Level AA). Measured from the CSSOM on the
 * running site: only two selectors carried any `:focus-visible` styling —
 * `.submit-btn` and `.btn-secondary` — and one `:focus` rule
 * (`.form-group input/select`) reached anything else.
 *
 * That left **59 of 80 form controls and ~70 of 73 buttons** with no visible
 * focus indicator at all:
 *
 *   validation.html   34 controls, 16 buttons   none
 *   scenarios.html     7 controls,  6 buttons   none
 *   centers.html       3 controls, 37 buttons   none
 *   explorer.html      4 controls,  8 buttons   none
 *   simulator.html     7 controls               (20 covered by .form-group)
 *
 * Three `outline: none` rules on `input[type="range"]` made it worse: they
 * strip the browser default in the BASE state, so sliders had nothing to fall
 * back on. Tabbing through the simulator's weight sliders gave no indication
 * of position.
 *
 * The fix is additive. `:focus-visible` matches keyboard focus only, so mouse
 * users see no change whatsoever, and existing higher-specificity focus styles
 * still win where they exist.
 *
 * Contrast note: the ring must also meet 3:1 against adjacent colour
 * (SC 1.4.11, non-text contrast), which is checked below rather than assumed.
 */
const fs = require('fs');
const path = require('path');

const REPO = path.join(__dirname, '..');
const RAW = fs.readFileSync(path.join(REPO, 'styles.css'), 'utf8');
// Strip comments before parsing selectors. A comment contains no braces, so
// `[^{}]+` in the rule regex happily swallows the one documenting a rule and
// reports it AS the selector -- which it did, hiding the very rule the
// comment explains.
const CSS = RAW.replace(/\/\*[\s\S]*?\*\//g, '');

function hexToRgb(hex) {
    const h = hex.trim().replace('#', '');
    const full = h.length === 3 ? h.split('').map(c => c + c).join('') : h;
    return [0, 2, 4].map(i => parseInt(full.slice(i, i + 2), 16));
}
function luminance([r, g, b]) {
    const [R, G, B] = [r, g, b].map(v => {
        v /= 255;
        return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * R + 0.7152 * G + 0.0722 * B;
}
function contrast(a, b) {
    const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
    return (hi + 0.05) / (lo + 0.05);
}

/** All selectors in the stylesheet carrying a :focus-visible outline. */
function focusVisibleRules() {
    const out = [];
    const re = /([^{}]+):focus-visible[^{]*\{([^}]*)\}/g;
    let m;
    while ((m = re.exec(CSS)) !== null) {
        if (/outline\s*:/.test(m[2]) && !/outline\s*:\s*(none|0)/.test(m[2])) {
            out.push({ selector: (m[1] + ':focus-visible').trim(), body: m[2] });
        }
    }
    return out;
}

describe('keyboard focus is visible', () => {
    const rules = focusVisibleRules();

    test('a global focus-visible rule exists', () => {
        expect(rules.length).toBeGreaterThan(0);
    });

    test.each(['a', 'button', 'input', 'select', 'textarea', '[tabindex]'])(
        '%s is covered by a focus-visible rule', (el) => {
            const covered = rules.some(r => {
                const sel = r.selector;
                // a bare element name, or inside a :is()/:where() list
                return new RegExp(`(^|[\\s,(])${el.replace(/[[\]]/g, '\\$&')}([\\s,):]|$)`)
                    .test(sel);
            });
            expect(covered).toBe(true);
        });

    test('range sliders are covered despite their base outline:none', () => {
        // Three rules strip the default outline on input[type=range] in the
        // base state. Without an explicit focus rule at sufficient
        // specificity, sliders stay invisible when focused.
        const stripped = (CSS.match(/input\[type="range"\][^{]*\{[^}]*outline:\s*(none|0)/g) || []).length;
        expect(stripped).toBeGreaterThan(0);   // premise: they still strip it
        const covered = rules.some(r => /range|input/.test(r.selector));
        expect(covered).toBe(true);
    });

    test('the ring colour meets 3:1 against the surfaces it appears on', () => {
        // SC 1.4.11 non-text contrast. Surfaces measured from the running site.
        const m = CSS.match(/--focus-ring:\s*(#[0-9a-fA-F]{3,8})/);
        expect(m).toBeTruthy();
        const ring = hexToRgb(m[1]);
        for (const bg of [[250, 249, 247], [255, 255, 255], [245, 240, 234]]) {
            expect(contrast(ring, bg)).toBeGreaterThanOrEqual(3);
        }
    });

    test('.form-group controls are covered too', () => {
        // Their existing treatment loses to nothing -- it IS the higher
        // specificity rule -- but what it supplies is a 1.05-1.20:1 ring and a
        // 1.27:1 border shift. The global rule must reach them.
        // Check the SELECTOR, not the substring: an earlier version tested
        // for the text ".form-group" and passed when the selector was mutated
        // to `.form-group input:not(*)`, which matches nothing.
        const selectors = rules.flatMap(r => r.selector.split(',').map(x => x.trim()));
        for (const want of ['.form-group input:focus-visible',
                            '.form-group select:focus-visible']) {
            expect(selectors).toContain(want);
        }
    });

    test('the contrast helper is right', () => {
        expect(contrast([0, 0, 0], [255, 255, 255])).toBeCloseTo(21, 1);
        expect(contrast([255, 255, 255], [255, 255, 255])).toBeCloseTo(1, 2);
    });

    test('focus styling is not applied on plain :focus for the global rule', () => {
        // Using :focus rather than :focus-visible would draw a ring on MOUSE
        // clicks too, which is why the browser default was suppressed in the
        // first place. Keep the fix invisible to mouse users.
        const global = rules.find(r => /:is\(|:where\(|button/.test(r.selector));
        expect(global).toBeTruthy();
        expect(global.selector).toContain(':focus-visible');
    });
});
