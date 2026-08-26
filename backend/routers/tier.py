"""GET /tier -- returns active tier caps for frontend control gating."""
import dataclasses

from fastapi import APIRouter

from tier_config import get_tier

router = APIRouter()

# `name` identifies the tier; every other field IS a cap.
_NON_CAP_FIELDS = {"name"}


@router.get("/tier")
def get_tier_config():
    """Serialize every cap the tier defines.

    This used to hand-list the caps, and it had drifted: five fields
    (max_rank_stability_boot, max_validation_iterations,
    max_validation_sweep_steps, max_validation_train_years,
    max_score_explain_limit) existed in TierConfig but were never sent.
    simulator/tier-panel.js already read caps.max_validation_iterations and
    silently fell back to a default every time, so the validation page's
    iteration control was never actually tier-gated.

    Deriving the payload from the dataclass means adding a cap to
    TierConfig ships it, instead of requiring a matching edit here that
    nothing enforces.
    """
    tier = get_tier()
    caps = {}
    for field in dataclasses.fields(tier):
        if field.name in _NON_CAP_FIELDS:
            continue
        value = getattr(tier, field.name)
        # Tuples are JSON arrays; everything else is already serializable.
        caps[field.name] = list(value) if isinstance(value, tuple) else value
    return {"name": tier.name, "caps": caps}
