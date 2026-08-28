/**
 * The marker must say what actually happened, not a comfortable approximation.
 *
 * The per-row dagger (#227/#228) said, for every tag:
 *
 *     "...so the national average is used instead."
 *
 * That was true of the tags it was written for. It is NOT true of
 * `no_post_transplant_outcomes` (#447/L-099), where the model substitutes
 * **zero volume** — a much stronger claim about the center than an average,
 * and the reason those centers score exactly 46.8 on hospital quality.
 *
 * Caught by reading the rendered tooltip in a browser, not by a test: the
 * backend tagged the right 91 rows, the label existed, the dagger appeared,
 * and the sentence was wrong. "The national average is used" reads as
 * reassurance, so getting this wrong is worse than not disclosing at all.
 */
const fs = require('fs');
const path = require('path');

const SRC = fs.readFileSync(
    path.join(__dirname, '..', 'simulator/results-table.js'), 'utf8');

/** Reach the private builder by re-deriving it from source. */
function buildMessage(tags) {
    const mapOf = (name) => {
        const block = SRC.slice(SRC.indexOf(`var ${name} = {`));
        const out = {};
        for (const m of block.slice(0, block.indexOf('};'))
                .matchAll(/^\s*([a-z_]+):\s*'([^']+)'/gm)) out[m[1]] = m[2];
        return out;
    };
    const labels = mapOf('DQ_LABELS');
    const subs = mapOf('DQ_SUBSTITUTE');

    const join = (n) => n.length === 1 ? n[0]
        : n.slice(0, -1).join(', ') + ' and ' + n[n.length - 1];
    const order = [], byPhrase = {};
    tags.forEach(t => {
        if (!labels[t]) return;
        const phrase = subs[t] || 'a substitute value is used';
        if (!byPhrase[phrase]) { byPhrase[phrase] = []; order.push(phrase); }
        byPhrase[phrase].push(labels[t]);
    });
    let n = 0;
    const parts = order.map(phrase => {
        n += byPhrase[phrase].length;
        return 'has no published SRTR data for ' + join(byPhrase[phrase]) + ', so ' + phrase;
    });
    return 'Not center-specific: this center ' + parts.join('; and it ') +
        '. Its position here rests partly on ' +
        (n === 1 ? 'that substitute' : 'those substitutes') + '.';
}

describe('the per-row marker describes the real substitute', () => {
    test('the module still parses (fixture is not stale)', () => {
        expect(SRC).toContain('DQ_SUBSTITUTE');
        expect(SRC).toContain('_buildDataQualityFlag');
    });

    test('the shipped builder contains the clauses this test models', () => {
        // buildMessage() below re-derives the logic rather than calling the
        // real function, which the module does not export. That means it
        // could pass while the shipped code says something else, so anchor it
        // to the real source: both clause templates and the branch that
        // chooses between them must exist in _buildDataQualityFlag.
        const fn = SRC.slice(SRC.indexOf('function _buildDataQualityFlag'));
        const body = fn.slice(0, fn.indexOf('\n  }'));
        expect(SRC).toContain('the national average is used instead');
        expect(SRC).toContain('counts it as zero rather than estimating');
        expect(body).toContain('DQ_SUBSTITUTE');
        // BOTH forms, not either: a source anchor that accepts one of them
        // passes when the plurality branch is collapsed, and the test below
        // would not catch it because that one exercises this file's own
        // re-derivation. (It did exactly that on the first pass.)
        expect(body).toContain('that substitute');
        expect(body).toContain('those substitutes');
    });

    test('a zero substitute is never described as a national average', () => {
        const msg = buildMessage(['no_post_transplant_outcomes']);
        expect(msg).toContain('counts it as zero');
        expect(msg).not.toContain('national average');
    });

    test('an averaged substitute still says national average', () => {
        const msg = buildMessage(['wait_time_national_default']);
        expect(msg).toContain('national average');
        expect(msg).not.toContain('counts it as zero');
    });

    test('a row with both gets both clauses, each attached correctly', () => {
        const msg = buildMessage([
            'acceptance_rate_national_default', 'no_post_transplant_outcomes']);
        expect(msg).toContain('organ offer acceptance, so the national average');
        expect(msg).toContain('post-transplant volume and survival, so the model counts it as zero');
    });

    test('plurality of the closing clause matches the number of substitutes', () => {
        expect(buildMessage(['wait_time_national_default']))
            .toContain('rests partly on that substitute.');
        expect(buildMessage(['wait_time_national_default', 'no_post_transplant_outcomes']))
            .toContain('rests partly on those substitutes.');
    });

    test('no message ever renders undefined', () => {
        const labels = [...SRC.matchAll(/^\s*([a-z_]+):\s*'[^']+'/gm)].map(m => m[1]);
        for (const tag of labels) {
            expect(buildMessage([tag])).not.toContain('undefined');
        }
    });
});

describe('every tag declares its own substitute', () => {
    /**
     * The recurrence guard. "so the national average is used instead" was
     * generic and became false twice as tags arrived (#447 zero, #451 median).
     * A tag added without a DQ_SUBSTITUTE entry silently inherits a sentence
     * that may not describe it, so require the two maps to agree.
     */
    const mapKeys = (name) => {
        const block = SRC.slice(SRC.indexOf(`var ${name} = {`));
        return new Set([...block.slice(0, block.indexOf('};'))
            .matchAll(/^\s*([a-z_]+):/gm)].map(m => m[1]));
    };

    test('DQ_SUBSTITUTE covers every labelled tag', () => {
        const labels = mapKeys('DQ_LABELS');
        const subs = mapKeys('DQ_SUBSTITUTE');
        expect(labels.size).toBeGreaterThanOrEqual(6);
        expect([...labels].filter(t => !subs.has(t))).toEqual([]);
    });

    test('DQ_SUBSTITUTE has no entry for an unlabelled tag', () => {
        const labels = mapKeys('DQ_LABELS');
        expect([...mapKeys('DQ_SUBSTITUTE')].filter(t => !labels.has(t))).toEqual([]);
    });

    test('the two substitutes that are not national averages say so', () => {
        const msg = buildMessage(['no_post_transplant_outcomes']);
        expect(msg).not.toContain('national average');
        const msg2 = buildMessage(['living_donor_volume_substituted']);
        expect(msg2).not.toContain('national average');
        expect(msg2).toContain('median measured center');
    });
});
