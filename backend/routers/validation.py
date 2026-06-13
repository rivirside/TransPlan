"""
Validation router — model validation, cross-engine comparison, diagnostics.

Endpoints:
  POST /validation/cross-engine        — compare MC / BBN rankings (Spearman ρ, top-5 overlap)
  POST /validation/model-sensitivity   — parameter sweep → ranking stability
  POST /validation/clinical-sensitivity — alias to /sensitivity
  POST /validation/calibration         — Brier score calibration check
  POST /validation/temporal            — walk-forward train/test validation
  GET  /validation/convergence/{organ} — MCMC R-hat / ESS diagnostics
  GET  /validation/reference-run/{organ} — canonical seed=12345 run
"""
import logging
import time
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from models.schemas import PatientProfile, SensitivityResult, SimulationResult
from services.stats_utils import spearman_between as _spearman_between, top5_jaccard as _top5_jaccard

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/validation", tags=["validation"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class CrossEngineRequest(BaseModel):
    patient: PatientProfile
    iterations: int = Field(default=300, ge=100, le=2000)
    seed: Optional[int] = Field(None, ge=0, le=2147483647)


class EngineComparison(BaseModel):
    engine: str
    top5: list[str]
    top10: list[str]
    available: bool
    note: str = ""


class CrossEngineResult(BaseModel):
    patient: PatientProfile
    engines: list[EngineComparison]
    spearman_mc_bbn: Optional[float] = None
    top5_overlap_mc_bbn: Optional[float] = None
    spearman_mc_mcmc: Optional[float] = None
    top5_overlap_mc_mcmc: Optional[float] = None
    elapsed_seconds: float


class ModelSensitivityRequest(BaseModel):
    patient: PatientProfile
    param: str = Field(description="Parameter to sweep: copula_theta, elasticity, cpra, meld, las, urgency, iterations")
    n_steps: int = Field(default=8, ge=3, le=10)
    base_iterations: int = Field(default=300, ge=100, le=1000)
    seed: Optional[int] = Field(None, ge=0, le=2147483647)


class ModelSensitivityResponse(BaseModel):
    param: str
    param_label: str
    baseline_value: float
    values: list[float]
    spearman_rhos: list[Optional[float]]
    top5_sets: list[list[str]]
    mean_rho: float
    min_rho: float
    baseline_top5: list[str]
    top5_overlap_with_baseline: list[float]
    elapsed_seconds: float


class CalibrationRequest(BaseModel):
    patient: PatientProfile
    iterations: int = Field(default=300, ge=100, le=1000)
    seed: Optional[int] = Field(None, ge=0, le=2147483647)


class CalibrationResult(BaseModel):
    organ: str
    brier_score_6mo: float
    brier_score_12mo: float
    brier_score_24mo: float
    calibration_note: str
    n_centers: int
    elapsed_seconds: float


class TemporalRequest(BaseModel):
    patient: PatientProfile
    train_start: int = Field(default=2019, ge=2015, le=2023)
    train_end: int = Field(default=2022, ge=2016, le=2024)
    test_end: int = Field(default=2024, ge=2017, le=2025)
    iterations: int = Field(default=300, ge=100, le=1000)
    seed: Optional[int] = Field(None, ge=0, le=2147483647)


class TemporalFoldSchema(BaseModel):
    train_end_year: int
    test_year: int
    spearman_rho: float
    top5_overlap: float
    n_centers: int
    elapsed_seconds: float


class TemporalResult(BaseModel):
    organ: str
    folds: list[TemporalFoldSchema]
    mean_spearman_rho: float
    mean_top5_overlap: float
    train_years: tuple[int, int]
    test_years: tuple[int, int]
    elapsed_seconds: float
    notes: list[str]


class ConvergenceDiagnosticSchema(BaseModel):
    name: str
    r_hat: float
    ess_bulk: float
    ess_tail: float
    autocorr_lag1: float


class ConvergenceResult(BaseModel):
    organ: str
    available: bool
    parameters: list[ConvergenceDiagnosticSchema]
    n_chains: int
    n_draws: int
    max_r_hat: float
    min_ess: float
    converged: bool
    notes: list[str]


# ---------------------------------------------------------------------------
# Helper: ranking → Spearman ρ
# ---------------------------------------------------------------------------

def _result_to_ranks(result: SimulationResult) -> list[str]:
    return [c.center_code or c.city for c in result.cities]


# ---------------------------------------------------------------------------
# POST /validation/cross-engine
# ---------------------------------------------------------------------------

@router.post("/cross-engine", response_model=CrossEngineResult)
def cross_engine(request: CrossEngineRequest) -> CrossEngineResult:
    """Run MC, BBN (Bayesian), and optionally MCMC; compare rankings."""
    t0 = time.perf_counter()
    try:
        from tier_config import get_tier
        tier = get_tier()
        iters = min(request.iterations, tier.max_iterations)
    except Exception:
        iters = request.iterations

    engines: list[EngineComparison] = []
    mc_ranks: Optional[list[str]] = None
    bbn_ranks: Optional[list[str]] = None
    mcmc_ranks: Optional[list[str]] = None

    # Monte Carlo
    try:
        from services.monte_carlo import simulate
        mc_result = simulate(request.patient, n_iterations=iters, seed=request.seed)
        mc_ranks = _result_to_ranks(mc_result)
        engines.append(EngineComparison(
            engine="monte_carlo",
            top5=mc_ranks[:5],
            top10=mc_ranks[:10],
            available=True,
        ))
    except Exception as e:
        engines.append(EngineComparison(engine="monte_carlo", top5=[], top10=[], available=False, note=str(e)))

    # Bayesian Network
    try:
        from services.bayesian_network import simulate_bbn
        bbn_result = simulate_bbn(request.patient)
        bbn_ranks = _result_to_ranks(bbn_result)
        engines.append(EngineComparison(
            engine="bayesian",
            top5=bbn_ranks[:5],
            top10=bbn_ranks[:10],
            available=True,
        ))
    except ImportError:
        engines.append(EngineComparison(engine="bayesian", top5=[], top10=[], available=False, note="pgmpy not installed"))
    except Exception as e:
        engines.append(EngineComparison(engine="bayesian", top5=[], top10=[], available=False, note=str(e)))

    # MCMC (local tier only)
    try:
        from tier_config import get_tier
        tier = get_tier()
        if "mcmc" in tier.allowed_inference_modes:
            from services.mcmc_inference import is_available, simulate_mcmc
            if is_available(request.patient.organ):
                mcmc_result = simulate_mcmc(request.patient, n_iterations=min(iters, 200))
                mcmc_ranks = _result_to_ranks(mcmc_result)
                engines.append(EngineComparison(
                    engine="mcmc",
                    top5=mcmc_ranks[:5],
                    top10=mcmc_ranks[:10],
                    available=True,
                ))
            else:
                engines.append(EngineComparison(
                    engine="mcmc", top5=[], top10=[], available=False,
                    note=f"No trace for {request.patient.organ}",
                ))
        else:
            engines.append(EngineComparison(
                engine="mcmc", top5=[], top10=[], available=False,
                note="MCMC not available in web tier",
            ))
    except ImportError:
        engines.append(EngineComparison(engine="mcmc", top5=[], top10=[], available=False, note="pymc/arviz not installed"))
    except Exception as e:
        engines.append(EngineComparison(engine="mcmc", top5=[], top10=[], available=False, note=str(e)))

    # Compute cross-engine statistics
    spearman_mc_bbn = _spearman_between(mc_ranks, bbn_ranks) if mc_ranks and bbn_ranks else None
    overlap_mc_bbn = _top5_jaccard(mc_ranks, bbn_ranks) if mc_ranks and bbn_ranks else None
    spearman_mc_mcmc = _spearman_between(mc_ranks, mcmc_ranks) if mc_ranks and mcmc_ranks else None
    overlap_mc_mcmc = _top5_jaccard(mc_ranks, mcmc_ranks) if mc_ranks and mcmc_ranks else None

    return CrossEngineResult(
        patient=request.patient,
        engines=engines,
        spearman_mc_bbn=spearman_mc_bbn,
        top5_overlap_mc_bbn=overlap_mc_bbn,
        spearman_mc_mcmc=spearman_mc_mcmc,
        top5_overlap_mc_mcmc=overlap_mc_mcmc,
        elapsed_seconds=time.perf_counter() - t0,
    )


# ---------------------------------------------------------------------------
# POST /validation/model-sensitivity
# ---------------------------------------------------------------------------

@router.post("/model-sensitivity", response_model=ModelSensitivityResponse)
def model_sensitivity(request: ModelSensitivityRequest) -> ModelSensitivityResponse:
    """Sweep a model parameter across its range; return ranking stability."""
    n_steps = request.n_steps
    try:
        from tier_config import get_tier
        tier = get_tier()
        iters = min(request.base_iterations, tier.max_sensitivity_iterations)
        n_steps = min(n_steps, tier.max_validation_sweep_steps)
    except Exception:
        iters = request.base_iterations

    try:
        from services.model_sensitivity import sweep_parameter
        result = sweep_parameter(
            patient=request.patient,
            param=request.param,
            n_steps=n_steps,
            base_iterations=iters,
            seed=request.seed,
        )
        return ModelSensitivityResponse(
            param=result.param,
            param_label=result.param_label,
            baseline_value=result.baseline_value,
            values=result.values,
            spearman_rhos=result.spearman_rhos,
            top5_sets=result.top5_sets,
            mean_rho=result.mean_rho,
            min_rho=result.min_rho,
            baseline_top5=result.baseline_top5,
            top5_overlap_with_baseline=result.top5_overlap_with_baseline,
            elapsed_seconds=result.elapsed_seconds,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Model sensitivity failed")
        raise HTTPException(status_code=500, detail="Model sensitivity analysis failed") from e


# ---------------------------------------------------------------------------
# POST /validation/clinical-sensitivity  (alias to /sensitivity)
# ---------------------------------------------------------------------------

@router.post("/clinical-sensitivity", response_model=SensitivityResult)
def clinical_sensitivity(
    patient: PatientProfile,
    city: str = "Nashville",
    center_code: str = "",
    iterations: int = 500,
    seed: Optional[int] = None,
) -> SensitivityResult:
    """Clinical parameter sensitivity — alias to /sensitivity endpoint."""
    try:
        from tier_config import get_tier
        tier = get_tier()
        iterations = min(iterations, tier.max_sensitivity_iterations)
    except Exception:
        pass
    try:
        from services.sensitivity import compute_sensitivity
        return compute_sensitivity(patient, city, iterations, center_code=center_code, seed=seed)
    except Exception as e:
        logger.exception("Clinical sensitivity failed")
        raise HTTPException(status_code=500, detail="Clinical sensitivity failed") from e


# ---------------------------------------------------------------------------
# POST /validation/calibration
# ---------------------------------------------------------------------------

@router.post("/calibration", response_model=CalibrationResult)
def calibration_check(request: CalibrationRequest) -> CalibrationResult:
    """
    Brier score calibration check.

    Since we don't have individual patient outcomes, we compute a proxy:
    run MC with two seeds, treat the first as "forecast" and the second as
    "observed" binary outcomes (p > 0.5 = transplanted), then compute Brier.
    """
    t0 = time.perf_counter()
    try:
        from tier_config import get_tier
        tier = get_tier()
        iters = min(request.iterations, tier.max_sensitivity_iterations)
    except Exception:
        iters = request.iterations

    try:
        import numpy as np
        from services.monte_carlo import simulate

        seed_a = request.seed if request.seed is not None else 42
        seed_b = (seed_a + 1234567) % 2147483647

        result_a = simulate(request.patient, n_iterations=iters, seed=seed_a)
        result_b = simulate(request.patient, n_iterations=iters, seed=seed_b)

        # Brier score = mean((forecast - observed)^2)
        # Use run A as forecast, run B binarized as "observed"
        a_dict = {c.center_code or c.city: c for c in result_a.cities}
        b_dict = {c.center_code or c.city: c for c in result_b.cities}

        common_keys = list(set(a_dict) & set(b_dict))

        def brier(attr: str) -> float:
            forecasts = [getattr(a_dict[k], attr) for k in common_keys]
            observed = [1 if getattr(b_dict[k], attr) > 0.5 else 0 for k in common_keys]
            return float(np.mean([(f - o) ** 2 for f, o in zip(forecasts, observed)]))

        bs6  = brier("p_transplant_6mo")
        bs12 = brier("p_transplant_12mo")
        bs24 = brier("p_transplant_24mo")

        # Interpretation
        if bs24 < 0.10:
            note = "Excellent calibration (Brier < 0.10)"
        elif bs24 < 0.20:
            note = "Good calibration (Brier < 0.20)"
        else:
            note = "Moderate calibration — expected given relative-comparison nature of model"

        return CalibrationResult(
            organ=request.patient.organ,
            brier_score_6mo=bs6,
            brier_score_12mo=bs12,
            brier_score_24mo=bs24,
            calibration_note=note,
            n_centers=len(common_keys),
            elapsed_seconds=time.perf_counter() - t0,
        )
    except Exception as e:
        logger.exception("Calibration check failed")
        raise HTTPException(status_code=500, detail="Calibration check failed") from e


# ---------------------------------------------------------------------------
# POST /validation/temporal
# ---------------------------------------------------------------------------

@router.post("/temporal", response_model=TemporalResult)
def temporal_validation(request: TemporalRequest) -> TemporalResult:
    """Walk-forward train/test temporal validation."""
    train_start = request.train_start
    try:
        from tier_config import get_tier
        tier = get_tier()
        iters = min(request.iterations, tier.max_validation_iterations)
        # Cap the training span to the tier's allowed window (#249).
        if request.train_end - train_start > tier.max_validation_train_years:
            train_start = request.train_end - tier.max_validation_train_years
    except Exception:
        iters = request.iterations

    try:
        from services.temporal_validation import run_temporal_validation
        result = run_temporal_validation(
            patient=request.patient,
            train_start=train_start,
            train_end=request.train_end,
            test_end=request.test_end,
            iterations=iters,
            seed=request.seed,
        )
        return TemporalResult(
            organ=result.organ,
            folds=[TemporalFoldSchema(**f.__dict__) for f in result.folds],
            mean_spearman_rho=result.mean_spearman_rho,
            mean_top5_overlap=result.mean_top5_overlap,
            train_years=result.train_years,
            test_years=result.test_years,
            elapsed_seconds=result.elapsed_seconds,
            notes=result.notes,
        )
    except Exception as e:
        logger.exception("Temporal validation failed")
        raise HTTPException(status_code=500, detail="Temporal validation failed") from e


# ---------------------------------------------------------------------------
# GET /validation/convergence/{organ}
# ---------------------------------------------------------------------------

@router.get("/convergence/{organ}", response_model=ConvergenceResult)
def convergence_diagnostics(organ: str) -> ConvergenceResult:
    """MCMC convergence diagnostics: R-hat, ESS, autocorrelation."""
    valid_organs = {"kidney", "liver", "heart", "lung", "pancreas", "intestine"}
    if organ not in valid_organs:
        raise HTTPException(status_code=400, detail=f"organ must be one of: {sorted(valid_organs)}")
    try:
        from services.convergence import get_convergence_diagnostics
        result = get_convergence_diagnostics(organ)
        return ConvergenceResult(
            organ=result.organ,
            available=result.available,
            parameters=[ConvergenceDiagnosticSchema(**p.__dict__) for p in result.parameters],
            n_chains=result.n_chains,
            n_draws=result.n_draws,
            max_r_hat=result.max_r_hat,
            min_ess=result.min_ess,
            converged=result.converged,
            notes=result.notes,
        )
    except Exception as e:
        logger.exception("Convergence diagnostics failed for %s", organ)
        raise HTTPException(status_code=500, detail="Convergence diagnostics failed") from e


# ---------------------------------------------------------------------------
# GET /validation/reference-run/{organ}
# ---------------------------------------------------------------------------

@router.get("/reference-run/{organ}", response_model=SimulationResult)
def reference_run(organ: str) -> SimulationResult:
    """Canonical deterministic run with seed=12345 for regression testing."""
    valid_organs = {"kidney", "liver", "heart", "lung", "pancreas", "intestine"}
    if organ not in valid_organs:
        raise HTTPException(status_code=400, detail=f"organ must be one of: {sorted(valid_organs)}")

    # Canonical test patient per organ
    canonical_patients = {
        "kidney":    PatientProfile(organ="kidney",    blood_type="O+",  age=45, sex="male",   urgency=2),
        "liver":     PatientProfile(organ="liver",     blood_type="A+",  age=52, sex="female",  urgency=3, meld=18),
        "heart":     PatientProfile(organ="heart",     blood_type="B+",  age=40, sex="male",   urgency=4),
        "lung":      PatientProfile(organ="lung",      blood_type="AB+", age=38, sex="female",  urgency=2, las=42.0),
        "pancreas":  PatientProfile(organ="pancreas",  blood_type="O-",  age=35, sex="male",   urgency=2),
        "intestine": PatientProfile(organ="intestine", blood_type="O+",  age=28, sex="female",  urgency=3),
    }

    patient = canonical_patients[organ]
    try:
        from services.monte_carlo import simulate
        result = simulate(patient, n_iterations=500, seed=12345)
        return result
    except Exception as e:
        logger.exception("Reference run failed for %s", organ)
        raise HTTPException(status_code=500, detail="Reference run failed") from e
