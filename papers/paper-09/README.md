# Paper 09: Reproducibility and Transparency in Stochastic Clinical Decision Support — Lessons from TransPlan

## Status: 📝 Not Started

## Summary

A perspective/commentary piece arguing that stochastic clinical decision support tools should adopt three practices: (1) seed parametrization for exact reproducibility, (2) run artifact export for auditability, and (3) multi-engine cross-validation for robustness. Uses TransPlan as a case study demonstrating all three.

## Paper Type
**Perspective/commentary** — short opinion piece (2000-2500 words) with TransPlan as illustrative example. Minimal data, mostly argumentation. The shortest and easiest paper in the portfolio.

## Target Venues (ranked)

| Venue | IF | Fit | Page Limit | Acceptance Rate | Notes |
|-------|-----|-----|------------|-----------------|-------|
| **JAMIA** (Perspective) | 7.9 | ⭐⭐⭐ | 2500 words | ~25% | Has a "Perspective" article type. Perfect fit. |
| **BMJ Health & Care Informatics** | 3.6 | ⭐⭐⭐ | 3000 words | ~30% | Open access. Informatics perspectives welcome. |
| **npj Digital Medicine** | 15.2 | ⭐⭐ | 3000 words | ~10% | High impact but very competitive. |
| **JMIR** | 7.1 | ⭐⭐ | Viewpoint: 2500 words | ~35% | "Viewpoint" article type. Fast review. |
| **J Clinical Epidemiology** | 8.2 | ⭐⭐ | Commentary: 1500 words | ~20% | Methods reproducibility angle. |

**Recommended:** JAMIA (Perspective) — they publish reproducibility pieces regularly. Fallback: BMJ Health & Care Informatics.

## Likelihood of Acceptance
**High (65%)** — Reproducibility in healthcare AI is a pressing concern. Short format means faster writing and review. JAMIA explicitly welcomes Perspective pieces on informatics methodology.

## Effort Required
🟢 **Low** — Pure writing exercise. No new code or analysis needed. Use TransPlan as the running example to illustrate principles.

### What exists already
- Seed parametrization: all stochastic endpoints accept `seed` parameter, return `seed_used`
- Run artifact export: `shared/export-handler.js` exports PDF/CSV/JSON/RunArtifact with seed
- Cross-engine validation: three engines (MC, BBN, MCMC) with cross-validation metrics
- Reference runs: canonical seed=12345 for regression testing
- 700+ automated tests ensuring reproducibility

### What needs to be done
- [ ] Literature review: reproducibility crises in clinical AI (survey existing papers)
- [ ] Draft argument structure (three pillars framework)
- [ ] Write manuscript (~2200 words)
- [ ] One illustrative figure (TransPlan reproducibility architecture)

## Suggested Structure

1. **The Problem** (400 words)
   - Stochastic clinical tools produce different results on each run
   - Patients sharing results with clinicians can't reproduce them
   - Regulatory bodies (FDA, EMA) increasingly require reproducibility
   - Current state: most clinical AI tools don't expose seeds or artifacts

2. **Three Pillars of Stochastic Reproducibility** (1200 words)
   - **Pillar 1: Seed Parametrization** (400 words)
     - Every stochastic call accepts optional seed
     - If None, system generates and returns seed_used
     - URL parameter propagation: ?seed=12345 reproduces exact run
     - Reference runs (canonical seed) for regression testing
     - TransPlan example: /simulate?seed=12345 returns identical results anywhere

   - **Pillar 2: Run Artifact Export** (400 words)
     - Every analysis exportable as JSON artifact with full metadata
     - Includes: seed, parameters, results, timestamps, model version
     - Enables: sharing with clinicians, longitudinal comparison, audit trail
     - TransPlan example: RunArtifact export includes seed + all parameters

   - **Pillar 3: Multi-Engine Cross-Validation** (400 words)
     - Same inputs → multiple inference methods → compare rankings
     - Agreement builds confidence; disagreement flags uncertainty
     - Not ensemble (averaging) but validation (checking)
     - TransPlan example: MC vs BBN vs MCMC with Spearman ρ monitoring

3. **Implementation Recommendations** (400 words)
   - Practical guidance for developers of clinical decision tools
   - Cost: seed parametrization is near-zero effort
   - Artifact export adds ~100 lines of code
   - Cross-validation requires multiple models (harder, but gold standard)
   - Regulatory angle: FDA guidance on AI/ML reproducibility

4. **Conclusion** (200 words)
   - Call to action: adopt these three pillars
   - Link to open-source TransPlan as reference implementation

## Key Figure
1. Architecture diagram: seed → simulation → artifact → cross-validation loop

## No Tables Required
(Commentary format — keep it lightweight)

## Notes
- This is the fastest paper to write and submit
- Can be drafted in 1-2 days
- Pairs well with Paper 01 (tools paper) — submit simultaneously or sequentially
- If JAMIA accepts Paper 01, this Perspective benefits from the same venue awareness
