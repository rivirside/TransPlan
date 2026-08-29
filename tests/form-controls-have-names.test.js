/**
 * Every form control must have an accessible name.
 *
 * A screen reader announces a control by its accessible name. Without one it
 * says "combo box" or "edit text" and nothing else — the user has no way to
 * know that the select they just landed on chooses the organ.
 *
 * #224 fixed tap-target sizes. Nothing had checked naming, and 45 controls
 * across five pages had none:
 *
 *   validation.html   34   <label>Organ</label> then <select id="ce-organ">
 *                          — a label with no `for` that does not wrap the
 *                          control is visually a label and programmatically
 *                          not one
 *   scenarios.html     7   <select id="centerSelect"> under an <h3>, no label
 *   sensitivity.html   2
 *   centers.html       1   <label>Your Location</label> then a <div> holding
 *                          the input; only a `placeholder`, which disappears
 *                          on input and is not a name
 *   equity.html        1
 *
 * This matters more here than on an average site: the people using a
 * transplant decision tool skew older and are frequently unwell, so
 * screen-reader and voice-control use is not a rare edge case.
 *
 * WCAG 2.1 SC 1.3.1 (Info and Relationships) and 4.1.2 (Name, Role, Value).
 *
 * A name may come from any of: <label for>, a wrapping <label>, aria-label,
 * aria-labelledby, or title. Placeholder deliberately does NOT count.
 */
const fs = require('fs');
const path = require('path');

const REPO = path.join(__dirname, '..');
const PAGES = fs.readdirSync(REPO).filter(f => f.endsWith('.html'));

/** Controls on a page that have no accessible name. */
function unnamed(html) {
    const forTargets = new Set(
        [...html.matchAll(/<label\b[^>]*\bfor="([^"]+)"/g)].map(m => m[1]));

    // Ids of controls sitting inside a <label> that has no `for`.
    const wrapped = new Set();
    for (const m of html.matchAll(/<label\b(?![^>]*\bfor=)[^>]*>([\s\S]*?)<\/label>/g)) {
        for (const inner of m[1].matchAll(/id="([^"]+)"/g)) wrapped.add(inner[1]);
    }

    const out = [];
    for (const m of html.matchAll(/<(input|select|textarea)\b([^>]*)>/g)) {
        const attrs = m[2];
        if (/type="(hidden|submit|button|image)"/.test(attrs)) continue;
        if (/aria-label=|aria-labelledby=|\btitle="/.test(attrs)) continue;
        const id = (attrs.match(/id="([^"]+)"/) || [])[1];
        if (id && (forTargets.has(id) || wrapped.has(id))) continue;
        out.push(id || `<${m[1]} with no id>`);
    }
    return out;
}

describe('every form control has an accessible name', () => {
    test('the scan finds controls at all (not vacuous)', () => {
        const total = PAGES.reduce(
            (n, p) => n + (fs.readFileSync(path.join(REPO, p), 'utf8')
                .match(/<(input|select|textarea)\b/g) || []).length, 0);
        expect(total).toBeGreaterThanOrEqual(40);
    });

    test.each(PAGES)('%s', (page) => {
        const html = fs.readFileSync(path.join(REPO, page), 'utf8');
        expect(unnamed(html)).toEqual([]);
    });

    test('placeholder alone is not accepted as a name', () => {
        // Pin the rule itself: a checker that counted placeholder would have
        // passed centers.html's zip input, which is exactly the control a
        // screen-reader user most needs named.
        const probe = '<input type="text" id="p" placeholder="Zip code">';
        expect(unnamed(probe)).toEqual(['p']);
    });

    test('a wrapping label counts', () => {
        const probe = '<label>Organ <select id="s"><option>a</option></select></label>';
        expect(unnamed(probe)).toEqual([]);
    });

    test('a for/id pair counts', () => {
        expect(unnamed('<label for="s">Organ</label><select id="s"></select>'))
            .toEqual([]);
    });

    test('a label with neither for nor wrapping does NOT count', () => {
        // The exact shape that made 34 validation.html controls anonymous.
        expect(unnamed('<label>Organ</label><select id="s"></select>'))
            .toEqual(['s']);
    });
});
