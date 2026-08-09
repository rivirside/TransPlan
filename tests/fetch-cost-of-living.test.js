/**
 * Tests for the BEA RPP cost-of-living fetch pipeline (#205) — specifically
 * the dead-data guards that protect the committed snapshot from being
 * overwritten by empty, truncated, or implausible API responses.
 */

const {
    parseRppCsv,
    buildSnapshot,
    validateSnapshot,
    CITY_CBSA,
} = require('../scripts/fetch-cost-of-living');

// ── Fixtures ──────────────────────────────────────────────────────────────

function beaCsv(rows) {
    const header = 'GeoFIPS,GeoName,Region,TableName,LineCode,IndustryClassification,Description,Unit,2023,2024';
    return [header, ...rows].join('\n');
}

const MSA_CSV = beaCsv([
    ' "00000","United States", ,MARPP,1,"...","RPPs: All items ","Index",100.000,100.000',
    ' "00999","United States (Nonmetropolitan Portion) *", ,MARPP,1,"...","RPPs: All items ","Index",88.3,88.7',
    ' "13820","Birmingham, AL (Metropolitan Statistical Area)", ,MARPP,1,"...","RPPs: All items ","Index",89.1,89.4',
    ' "13820","Birmingham, AL (Metropolitan Statistical Area)", ,MARPP,2,"...","RPPs: Goods ","Index",95.0,95.2',
    ' "35620","New York-Newark-Jersey City, NY-NJ", ,MARPP,1,"...","RPPs: All items ","Index",112.5,112.9',
    ' "99999","Stale Metro, XX", ,MARPP,1,"...","RPPs: All items ","Index",91.2,(NA)',
]);

const STATE_CSV = beaCsv([
    ' "00000","United States", ,SARPP,1,"...","RPPs: All items ","Index",100.000,100.000',
    ' "01000","Alabama",5,SARPP,1,"...","RPPs: All items ","Index",87.5,87.8',
    ' "36000","New York",1,SARPP,1,"...","RPPs: All items ","Index",108.9,109.2',
]);

// ── parseRppCsv ───────────────────────────────────────────────────────────

describe('parseRppCsv', () => {
    test('keeps only LineCode 1 (all-items) rows', () => {
        const { rows } = parseRppCsv(MSA_CSV);
        expect(rows['13820'].rpp).toBe(89.4); // not the Goods line (95.2)
    });

    test('uses the latest year with a numeric value', () => {
        const { rows, vintage } = parseRppCsv(MSA_CSV);
        expect(rows['99999'].rpp).toBe(91.2); // 2024 is (NA) → falls back to 2023
        expect(vintage).toBe(2024);
    });

    test('throws on a header without year columns', () => {
        expect(() => parseRppCsv('GeoFIPS,GeoName,LineCode\n"x","y","1"')).toThrow();
    });
});

// ── buildSnapshot ─────────────────────────────────────────────────────────

describe('buildSnapshot', () => {
    const snap = buildSnapshot(MSA_CSV, STATE_CSV, new Date('2026-08-09T00:00:00Z'));

    test('separates US anchor, nonmetro, and MSA rows', () => {
        expect(snap.msas['00000']).toBeUndefined();
        expect(snap.msas['00999']).toBeUndefined();
        expect(snap.nonmetroUS).toBe(88.7);
        expect(Object.keys(snap.msas)).toEqual(expect.arrayContaining(['13820', '35620', '99999']));
    });

    test('maps state names to abbreviations', () => {
        expect(snap.states).toEqual({ AL: 87.8, NY: 109.2 });
    });

    test('derives legacy city block from MSA values', () => {
        expect(snap.cities['New York']).toBe(113); // round(112.9)
    });

    test('stamps vintage and source metadata', () => {
        expect(snap._meta.vintage).toBe(2024);
        expect(snap._meta.source).toMatch(/BEA/);
    });
});

// ── validateSnapshot (the dead-data guards) ──────────────────────────────

describe('validateSnapshot', () => {
    function goodSnapshot() {
        const msas = {};
        for (let i = 0; i < 350; i++) {
            msas[String(10000 + i * 10)] = { name: `Metro ${i}`, rpp: 85 + (i % 30) };
        }
        const states = {};
        const abbrs = 'AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY'.split(' ');
        abbrs.forEach((a, i) => { states[a] = 85 + (i % 25); });
        const cities = {};
        Object.keys(CITY_CBSA).forEach((c, i) => { cities[c] = 90 + i; });
        return { vintage: 2024, msas, states, nonmetroUS: 88.7, cities };
    }

    test('accepts a plausible snapshot', () => {
        expect(validateSnapshot(goodSnapshot(), null)).toEqual([]);
    });

    test('rejects an empty/truncated MSA set (dead API)', () => {
        const s = goodSnapshot();
        s.msas = { '13820': { name: 'Birmingham', rpp: 89.4 } };
        expect(validateSnapshot(s, null).join()).toMatch(/MSAs/);
    });

    test('rejects missing states', () => {
        const s = goodSnapshot();
        s.states = { AL: 87.8 };
        expect(validateSnapshot(s, null).join()).toMatch(/states/);
    });

    test('rejects implausible values (unit change / garbage)', () => {
        const s = goodSnapshot();
        s.msas['10000'].rpp = 890; // e.g. API switched units
        expect(validateSnapshot(s, null).join()).toMatch(/outside/);
    });

    test('rejects vintage regression against the existing snapshot', () => {
        const s = goodSnapshot();
        s.vintage = 2020;
        const existing = { _meta: { vintage: 2024 }, msas: s.msas };
        expect(validateSnapshot(s, existing).join()).toMatch(/vintage regression/);
    });

    test('rejects coverage shrinkage vs the existing snapshot', () => {
        const existing = { _meta: { vintage: 2024 }, msas: goodSnapshot().msas };
        const s = goodSnapshot();
        for (const key of Object.keys(s.msas).slice(0, 100)) delete s.msas[key];
        expect(validateSnapshot(s, existing).join()).toMatch(/shrank/);
    });

    test('rejects wholesale value shifts vs the existing snapshot', () => {
        const existing = { _meta: { vintage: 2024 }, msas: goodSnapshot().msas };
        const s = goodSnapshot();
        for (const key of Object.keys(s.msas)) s.msas[key].rpp += 20;
        expect(validateSnapshot(s, existing).join()).toMatch(/median RPP change/);
    });

    test('tolerates a legacy-shape existing file (first migration run)', () => {
        const legacy = { _meta: {}, 'New York': 107, 'Chicago': 92 };
        expect(validateSnapshot(goodSnapshot(), legacy)).toEqual([]);
    });
});
