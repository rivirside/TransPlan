/**
 * Muted text must meet WCAG AA contrast against the surfaces it sits on.
 *
 * `--text-muted` aliased `--neutral-400` (#a8a198). Measured against the four
 * surfaces it actually renders on, that gives **2.26–2.56:1**; WCAG AA needs
 * 4.5 for text below 18.66px bold / 24px. Every muted string on the site was
 * below the bar, including — measured on validation.html — the footer's
 * medical disclaimer at **2.26:1 and 8px**.
 *
 * That disclaimer is worth naming twice: its PRINT version was dead earlier
 * in the same sweep (L-092, a `::after` orphaned by the Phase 2 rebuild). So
 * the sentence telling patients this is not medical advice had failed to
 * reach them in two different media, for different reasons.
 *
 * The fix is not `--neutral-400`, which is also a BORDER colour — darkening it
 * would restyle every border on the site. `--text-muted` now carries its own
 * value: #726d67 light, #948b7b dark. Both are the LIGHTEST value of the
 * existing hue that clears 4.5 on every surface, so the muted look survives.
 *
 * This test computes contrast from the stylesheet rather than a browser, so it
 * runs in CI and cannot be defeated by a cached stylesheet — which is exactly
 * what made the manual check unreliable while developing it.
 *
 * Known remaining and NOT covered here: `.val-tab` and some 7–9px footer text
 * still fail, and dark mode has separate failures (worst 1.03 on
 * `.nav-brand-text`). Those need colour decisions with wider blast radius than
 * one token — filed rather than guessed at.
 */
const fs = require('fs');
const path = require('path');

const CSS = fs.readFileSync(path.join(__dirname, '..', 'styles.css'), 'utf8');

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

function contrast(fg, bg) {
    const [a, b] = [luminance(fg), luminance(bg)].sort((x, y) => y - x);
    return (a + 0.05) / (b + 0.05);
}

/**
 * Read a custom property from a block, following ONE level of var()
 * indirection within that same block.
 *
 * Scoping matters: an earlier version searched the whole file, so asking for
 * --text-1 in light mode returned the DARK block's #f5f0ea and compared light
 * muted text against dark body text. The comparison was meaningless and the
 * test failed for the wrong reason.
 */
function token(name, blockStart) {
    const from = blockStart ? CSS.indexOf(blockStart) : CSS.indexOf(':root');
    if (from < 0) return null;
    const slice = CSS.slice(from, CSS.indexOf('\n}', from));
    const m = slice.match(new RegExp(`--${name}:\\s*([^;]+);`));
    if (!m) return null;
    const val = m[1].trim();
    if (val.startsWith('#')) return hexToRgb(val);
    const ref = val.match(/var\(\s*--([\w-]+)/);
    if (!ref) return null;
    const m2 = slice.match(new RegExp(`--${ref[1]}:\\s*(#[0-9a-fA-F]{3,8})`));
    return m2 ? hexToRgb(m2[1]) : null;
}

// Surfaces muted text renders on, measured from the running site.
const LIGHT_SURFACES = [[250, 249, 247], [255, 255, 255], [249, 250, 251], [245, 240, 234]];
const DARK_SURFACES = [[20, 18, 16], [26, 23, 16], [33, 30, 23], [42, 37, 32]];
const AA_NORMAL = 4.5;

describe('muted text meets WCAG AA', () => {
    test('the token is a literal, not an alias to a border colour', () => {
        // --neutral-400 doubles as a border colour; aliasing it is what made
        // muted text fail, and re-aliasing it would silently undo this.
        const m = CSS.match(/--text-muted:\s*([^;]+);/);
        expect(m).toBeTruthy();
        expect(m[1]).not.toMatch(/var\(--neutral-400\)/);
    });

    test.each(LIGHT_SURFACES)('light --text-muted on rgb(%i,%i,%i)', (r, g, b) => {
        const fg = token('text-muted');
        expect(fg).not.toBeNull();
        expect(contrast(fg, [r, g, b])).toBeGreaterThanOrEqual(AA_NORMAL);
    });

    test.each(DARK_SURFACES)('dark --text-muted on rgb(%i,%i,%i)', (r, g, b) => {
        const fg = token('text-muted', '[data-dark="true"] {');
        expect(fg).not.toBeNull();
        expect(contrast(fg, [r, g, b])).toBeGreaterThanOrEqual(AA_NORMAL);
    });

    test('the contrast maths is right (known pairs)', () => {
        // Guard the helper itself: a broken formula would pass everything.
        expect(contrast([0, 0, 0], [255, 255, 255])).toBeCloseTo(21, 1);
        expect(contrast([255, 255, 255], [255, 255, 255])).toBeCloseTo(1, 2);
        // The value this test exists to reject.
        expect(contrast(hexToRgb('#a8a198'), [245, 240, 234])).toBeLessThan(AA_NORMAL);
    });

    test('the muted colour stays visibly muted', () => {
        // A fix that just used the body text colour would pass contrast and
        // destroy the visual hierarchy the token exists for.
        const muted = token('text-muted');
        const body = token('text-1') || token('text');
        if (body) expect(luminance(muted)).toBeGreaterThan(luminance(body));
    });
});
