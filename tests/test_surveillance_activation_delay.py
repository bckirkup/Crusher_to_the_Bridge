"""Tests for campaign T11 surveillance activation delay gating."""

from __future__ import annotations

import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from orchestrator_epoch import (  # noqa: E402
    inactive_syndromic_result,
    surveillance_activation_delay_epochs,
    surveillance_is_active,
)
from picard_framework import PicardRunSpec, ShipSimulation  # noqa: E402


def test_delay_reads_max_of_syndromic_and_cascade() -> None:
    assert surveillance_activation_delay_epochs({}) == 0
    assert surveillance_activation_delay_epochs(None) == 0
    assert surveillance_activation_delay_epochs({
        "syndromic": {"activation_delay_epochs": 24},
    }) == 24
    assert surveillance_activation_delay_epochs({
        "diagnostic_cascade": {"activation_delay_epochs": 72},
    }) == 72
    assert surveillance_activation_delay_epochs({
        "syndromic": {"activation_delay_epochs": 24},
        "diagnostic_cascade": {"activation_delay_epochs": 72},
    }) == 72
    assert surveillance_activation_delay_epochs({
        "syndromic": {"activation_delay_epochs": -3},
    }) == 0


def test_surveillance_is_active_is_0_based() -> None:
    cfg = {"syndromic": {"activation_delay_epochs": 3}}
    assert surveillance_is_active(0, cfg) is False
    assert surveillance_is_active(2, cfg) is False
    assert surveillance_is_active(3, cfg) is True
    assert surveillance_is_active(0, {"syndromic": {"activation_delay_epochs": 0}}) is True


def test_inactive_syndromic_result_is_empty() -> None:
    result = inactive_syndromic_result(5, n_agents=42)
    assert result["sick_call_agents"] == []
    assert result["sick_call_count"] == 0
    assert result["total_agents"] == 42
    assert result["activation_delayed"] is True
    assert result["epoch"] == 5


@pytest.mark.timeout(120)
def test_ship_simulation_suppresses_sick_calls_during_delay() -> None:
    """Delay=3 → epochs 0..2 silent; surveillance may open at epoch 3."""
    spec = PicardRunSpec.from_legacy_yaml(
        repo_root=REPO_ROOT,
        num_epochs=4,
    )
    spec.legacy_cfg.setdefault("syndromic", {})["activation_delay_epochs"] = 3
    spec.legacy_cfg.setdefault("diagnostic_cascade", {})["activation_delay_epochs"] = 3
    # Force plenty of sick-call signal once the gate opens.
    spec.legacy_cfg.setdefault("syndromic", {})["sick_call_probability"] = 1.0
    spec.legacy_cfg.setdefault("diagnostic_cascade", {})["enabled"] = True

    sim = ShipSimulation(spec, display=False, repo_root=REPO_ROOT)
    history = sim.run().history
    assert len(history) == 4

    delayed = [rec for rec in history if int(rec["epoch"]) < 3]
    assert len(delayed) == 3
    for rec in delayed:
        assert rec["summary"]["sick_call_count"] == 0
        cascade = rec.get("diagnostic_cascade")
        if cascade is not None:
            assert not (
                cascade.get("new_tier0_agents")
                or cascade.get("new_tier1_agents")
                or cascade.get("tier_advancements")
            )
