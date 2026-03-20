# Model Iteration Comparison Report

**Generated:** N/A
**Engine:** monte_carlo
**Snapshots compared:** 2

- **baseline** (`e382e58b2fec`, 2026-03-20)
- **copula-cod-on** (`e382e58b2fec`, 2026-03-20)

## Rank Stability Summary

| Profile | Kendall's τ | Spearman ρ | Top-5 Overlap | Biggest Mover |
|---------|------------|------------|---------------|---------------|
| heart/A+ | 0.671 | 0.853 | 3/5 | Indianapolis (7 pos) |
| intestine/A+ | 0.862 | 0.956 | 4/5 | Palo Alto (6 pos) |
| kidney/B+ | 0.766 | 0.923 | 4/5 | Palo Alto (6 pos) |
| kidney/O+ | 0.801 | 0.927 | 4/5 | Minneapolis (7 pos) |
| liver/A+ | 0.680 | 0.857 | 4/5 | Baltimore (7 pos) |
| liver/O- | 0.749 | 0.904 | 4/5 | Baltimore (8 pos) |
| lung/O+ | 0.558 | 0.720 | 3/5 | Omaha (10 pos) |
| pancreas/B+ | 0.827 | 0.955 | 4/5 | Miami (4 pos) |

## Probability Changes (p_transplant_24mo)

| Profile | Mean |Δ| | Max |Δ| | Direction | Max ↑ City | Max ↓ City |
|---------|---------|---------|-----------|------------|------------|
| heart/A+ | 0.0136 | 0.0360 | ↑ 0.0096 | Portland (+0.036) | Seattle (-0.018) |
| intestine/A+ | 0.0344 | 0.0840 | ↓ 0.0240 | Cleveland (+0.042) | Chicago (-0.084) |
| kidney/B+ | 0.0210 | 0.0440 | ↑ 0.0130 | Nashville (+0.044) | Palo Alto (-0.034) |
| kidney/O+ | 0.0214 | 0.0660 | ↓ 0.0072 | Minneapolis (+0.050) | Palo Alto (-0.066) |
| liver/A+ | 0.0260 | 0.0900 | ↑ 0.0173 | Houston (+0.090) | Madison (-0.022) |
| liver/O- | 0.0195 | 0.0740 | ↑ 0.0171 | Baltimore (+0.074) | Rochester (-0.012) |
| lung/O+ | 0.0101 | 0.0280 | ↑ 0.0050 | Palo Alto (+0.028) | Omaha (-0.014) |
| pancreas/B+ | 0.0309 | 0.0780 | ↓ 0.0011 | Seattle (+0.070) | Nashville (-0.078) |

## Assessment

Rankings are **moderately stable** (avg τ = 0.739). Some meaningful reordering occurred.

Mean probability shift: **0.0221** (2.21 percentage points).
