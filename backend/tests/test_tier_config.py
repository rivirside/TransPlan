"""Tests for tier config and enforcement."""
import os
import pytest
from tier_config import get_tier, WEB_TIER, LOCAL_TIER, TierConfig


def test_default_tier_is_web():
    os.environ.pop("TRANSPLAN_TIER", None)
    assert get_tier().name == "web"


def test_local_tier():
    os.environ["TRANSPLAN_TIER"] = "local"
    try:
        assert get_tier().name == "local"
        assert get_tier().max_iterations == 10000
    finally:
        os.environ.pop("TRANSPLAN_TIER", None)


def test_web_tier_caps():
    tier = WEB_TIER
    assert tier.max_iterations == 1000
    assert "mcmc" not in tier.allowed_inference_modes
    assert "full" not in tier.allowed_bbn_granularity
    assert tier.copula_theta_locked is True
    assert tier.elasticity_locked is True


def test_local_tier_caps():
    tier = LOCAL_TIER
    assert tier.max_iterations == 10000
    assert "mcmc" in tier.allowed_inference_modes
    assert "full" in tier.allowed_bbn_granularity
    assert tier.copula_theta_locked is False
    assert tier.elasticity_locked is False


def test_unknown_tier_defaults_to_web():
    os.environ["TRANSPLAN_TIER"] = "premium"
    try:
        assert get_tier().name == "web"
    finally:
        os.environ.pop("TRANSPLAN_TIER", None)


def test_tier_config_is_frozen():
    with pytest.raises(Exception):
        WEB_TIER.name = "hacked"
