/**
 * Every page offers a way past the navigation, and names its main region.
 *
 * WCAG 2.1 SC 2.4.1 (Bypass Blocks) is Level **A** — a higher bar than the AA
 * items fixed alongside it. There was no skip link anywhere on the site, so a
 * keyboard user tabbed through the whole two-column mega-nav on every page
 * before reaching content. On centers.html that is 37 buttons.
 *
 * Four pages also had no main landmark at all (equity, model-card, scenarios,
 * validation), and none of the thirteen that did carried an id — so even
 * adding a skip link would have had nothing to point at.
 *
 * The four are fixed with `role="main"` on the existing layout container
 * rather than by wrapping content in a new <main>. Same result for assistive
 * technology, no structural edit to a working page.
 *
 * The skip link is injected by site-chrome.js alongside the nav it skips, so
 * a new page cannot get one without the other.
 */
const fs = require('fs');
const path = require('path');

const REPO = path.join(__dirname, '..');
const PAGES = fs.readdirSync(REPO).filter(f => f.endsWith('.html'));
const CHROME = fs.readFileSync(path.join(REPO, 'components/site-chrome.js'), 'utf8');
const CSS = fs.readFileSync(path.join(REPO, 'styles.css'), 'utf8')
    .replace(/\/\*[\s\S]*?\*\//g, '');

const TARGET = 'main-content';

describe('bypass blocks (WCAG 2.4.1, Level A)', () => {
    test('the sweep sees the pages', () => {
        expect(PAGES.length).toBeGreaterThanOrEqual(10);
    });

    test('site chrome injects a skip link', () => {
        expect(CHROME).toMatch(/skip/i);
        expect(CHROME).toContain(`#${TARGET}`);
    });

    test('the skip link is the first thing in the tab order', () => {
        // It must precede the nav it exists to skip; otherwise it is useless.
        const skip = CHROME.search(/skip-link/i);
        const nav = CHROME.search(/<nav/i);
        expect(skip).toBeGreaterThan(-1);
        expect(nav).toBeGreaterThan(-1);
        expect(skip).toBeLessThan(nav);
    });

    test('the skip link is visible when focused', () => {
        // A skip link hidden with display:none is unreachable; it must be
        // off-screen but focusable, and must appear on focus.
        expect(CSS).toMatch(/\.skip-link\b/);
        const block = CSS.slice(CSS.indexOf('.skip-link'));
        const focused = block.slice(0, block.indexOf('}', block.indexOf(':focus')) + 1);
        expect(focused).toMatch(/:focus/);
        expect(block.slice(0, block.indexOf('}'))).not.toMatch(/display:\s*none/);
    });

    test.each(PAGES)('%s names a main region with the skip target id', (page) => {
        const html = fs.readFileSync(path.join(REPO, page), 'utf8');
        const hasMain = /<main\b/.test(html) || /role="main"/.test(html);
        expect(hasMain).toBe(true);
        expect(html).toMatch(new RegExp(`id="${TARGET}"`));
    });

    test.each(PAGES)('%s main target is focusable', (page) => {
        // Without tabindex="-1" the skip link changes the hash and scrolls,
        // but focus stays in the nav -- so the next Tab continues from the
        // link the user just tried to escape. Verified in a browser: before
        // this, activating the link left document.activeElement on BODY.
        const html = fs.readFileSync(path.join(REPO, page), 'utf8');
        const m = html.match(new RegExp(`<[^>]*id="${TARGET}"[^>]*>`));
        expect(m).toBeTruthy();
        expect(m[0]).toMatch(/tabindex="-1"/);
    });

    test.each(PAGES)('%s has exactly one main region', (page) => {
        const html = fs.readFileSync(path.join(REPO, page), 'utf8');
        const count = (html.match(/<main\b/g) || []).length
            + (html.match(/role="main"/g) || []).length;
        expect(count).toBe(1);
    });
});
