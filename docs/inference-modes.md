# Inference modes: what runs where, and what each one needs

**Closes #232.** Three engines answer the same question — "what is the probability of transplant at this center within 24 months?" — by different routes. Which are available depends on the deployment tier *and*, for MCMC, on a fitting step whose output is deliberately not in the repository.

## Availability

| mode | transplant.today (web) | fresh local clone | local, after fitting |
|---|---|---|---|
| `monte_carlo` | ✅ | ✅ | ✅ |
| `bayesian` (BBN) | ✅ | ✅ | ✅ |
| `mcmc` | ❌ tier-blocked | ❌ **no traces** | ✅ |

The web tier allows `("monte_carlo", "bayesian")`; local allows all three (`backend/tier_config.py`). Switch with:

```bash
TRANSPLAN_TIER=local uvicorn backend.main:app --port 8002 --reload
```

`GET /tier` returns the active caps, and `simulator/tier-panel.js` hides controls the tier does not allow — so a web visitor never sees an MCMC option that would fail.

## Dependencies

| mode | needs | shipped in `requirements.txt` (Vercel)? |
|---|---|---|
| `monte_carlo` | numpy, scipy | yes |
| `bayesian` | numpy only | yes |
| `mcmc` | pymc, arviz, **and** netCDF4 or h5netcdf | no — dev-only, in `backend/requirements.txt` |

**The BBN does not use pgmpy.** It runs on `backend/services/bbn_lite.py`, an in-house exact-inference engine over plain numpy arrays. #232 and several docstrings said otherwise; #401 corrected the docstrings and the `requirements.txt` comment records the substitution. If you are reading an older note that mentions pgmpy for the BBN, it is stale.

The netCDF backend is easy to miss: without it the MCMC test suites error while *looking* like a pymc version problem. `requirements.txt` in `backend/` carries it for that reason.

## Why a fresh clone cannot run MCMC

The posterior traces are **285 MB** — six organs at ~48 MB each — and `.gitignore:30` excludes `data/mcmc-traces/`. That is a deliberate choice, not an oversight: they are regenerable artifacts.

Generate them with:

```bash
python scripts/fit-mcmc-model.py --all --samples 2000 --chains 4
```

Runtimes from the script's own header (M1 Mac): `--quick` ~5 s per organ, default ~2–5 min per organ, `--all` ~15–30 min.

Until then the API answers clearly rather than failing obscurely — `POST /simulate?inference_mode=mcmc` returns **503** with the exact command to run:

> MCMC trace not available for kidney. Run scripts/fit-mcmc-model.py --organ kidney to generate it.

A missing pymc/arviz gives a different 503 naming the dependencies. Neither is a 500.

## Granularity

`bbn_granularity` selects the region resolution for the BBN and MCMC: `state` (51 regions) or `full` (per-center). Both tiers allow both. The 22-city `classic` mode was retired in #293 and its traces are no longer loaded.

MCMC falls back across granularities when the requested one has no trace — `_select_trace` tries the request, then `full`, then `state` — and the *actual* granularity used is what determines how centers map onto region effects (#207). This is why `find_fitted_granularity` exists: a bare default of `state` reported "no trace" for organs fitted only at `--granularity full`, which made the validation page disagree with a working `/simulate` (backlog K4).

## Choosing between them

`monte_carlo` is the default and the only engine with the full feature set — competing risks via the copula, acceptance thinning, score drift, trend projection. Both alternatives exist to cross-check it, not to replace it.

Known divergence to keep in mind: for pediatric candidates, all three restrict to centers with a pediatric program, but only Monte Carlo re-anchors the wait distribution to the observed pediatric rate. The BBN and MCMC return **adult numbers on a pediatric center list** (L-079 / #371), disclosed through the `pediatric_wait_model` provenance family rather than fixed.

## Keeping this page honest

`backend/tests/test_inference_mode_docs.py` checks this table against `tier_config.py`, so a tier change that is not reflected here fails CI. It is the same drift problem the `/tier` endpoint had before #350 — five caps existed in the dataclass and were never sent, and the frontend silently defaulted every time.
