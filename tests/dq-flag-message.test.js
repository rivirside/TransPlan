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
    const labels = {};
    const block = SRC.slice(SRC.indexOf('var DQ_LABELS = {'));
    for (const m of block.slice(0, block.indexOf('};')).matchAll(/^\s*([a-z_]+):\s*'([^']+)'/gm)) {
        labels[m[1]] = m[2];
    }
    const zeroList = JSON.parse(
        (SRC.match(/var ZERO_SUBSTITUTE_TAGS = (\[[^\]]*\])/) || [])[1]
            .replace(/'/g, '"'));

    const join = (n) => n.length === 1 ? n[0]
        : n.slice(0, -1).join(', ') + ' and ' + n[n.length - 1];
    const zeroed = [], averaged = [];
    tags.forEach(t => {
        if (!labels[t]) return;
        (zeroList.indexOf(t) === -1 ? averaged : zeroed).push(labels[t]);
    });
    const parts = [];
    if (averaged.length) {
        parts.push('has no published SRTR data for ' + join(averaged) +
                   ', so the national average is used instead');
    }
    if (zeroed.length) {
        parts.push('has no published SRTR ' + join(zeroed) +
                   ', which the model counts as zero rather than estimating');
    }
    const n = averaged.length + zeroed.length;
    return 'Not center-specific: this center ' + parts.join('; and it ') +
        '. Its position here rests partly on ' +
        (n === 1 ? 'that substitute' : 'those substitutes') + '.';
}

describe('the per-row marker describes the real substitute', () => {
    test('the module still parses (fixture is not stale)', () => {
        expect(SRC).toContain('ZERO_SUBSTITUTE_TAGS');
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
        expect(body).toContain('so the national average is used instead');
        expect(body).toContain('counts as zero rather than estimating');
        expect(body).toContain('ZERO_SUBSTITUTE_TAGS');
        // BOTH forms, not either: a source anchor that accepts one of them
        // passes when the plurality branch is collapsed, and the test below
        // would not catch it because that one exercises this file's own
        // re-derivation. (It did exactly that on the first pass.)
        expect(body).toContain('that substitute');
        expect(body).toContain('those substitutes');
    });

    test('a zero substitute is never described as a national average', () => {
        const msg = buildMessage(['no_post_transplant_outcomes']);
        expect(msg).toContain('counts as zero');
        expect(msg).not.toContain('national average');
    });

    test('an averaged substitute still says national average', () => {
        const msg = buildMessage(['wait_time_national_default']);
        expect(msg).toContain('national average');
        expect(msg).not.toContain('counts as zero');
    });

    test('a row with both gets both clauses, each attached correctly', () => {
        const msg = buildMessage([
            'acceptance_rate_national_default', 'no_post_transplant_outcomes']);
        expect(msg).toContain('organ offer acceptance, so the national average');
        expect(msg).toContain('post-transplant volume and survival, which the model counts as zero');
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
