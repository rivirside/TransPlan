"""Standardized export artifact for reproducible runs across all tools."""
from typing import Optional

from pydantic import BaseModel, Field

from models.schemas import PatientProfile


class RunArtifact(BaseModel):
    """Complete record of a simulation run for reproducibility and citation."""
    version: str = Field("2.0.0", description="TransPlan engine version")
    tool: str = Field(description="Tool that produced this artifact: simulator, sensitivity, equity, scenarios, validation")
    timestamp: str = Field(description="ISO 8601 timestamp of when the run completed")
    seed_used: int = Field(description="RNG seed used — rerun with this seed to reproduce results exactly")
    patient: PatientProfile
    parameters: dict = Field(description="Tool-specific parameters (iterations, copula_theta, etc.)")
    results: dict = Field(description="Full result payload from the tool")
    tier: str = Field("web", description="Tier that was active: web or local")
    inference_mode: Optional[str] = Field(None, description="Inference engine used (monte_carlo, bayesian, mcmc)")
