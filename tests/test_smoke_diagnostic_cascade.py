"""
test_smoke_diagnostic_cascade.py – End-to-end smoke with cascade enabled
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Runs ShipSimulation using dedicated Picard run specs that enable the
diagnostic cascade engine.  Validates that cascade telemetry is emitted
each epoch and that tier progression occurs under the default seed.
"""

from __future__ import annotations

import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from picard_framework import PicardRunSpec, ShipSimulation

CASCADE_SMOKE_SPECS: list[tuple[str, str]] = [
    (
        "picard_framework/runs/smoke_cascade_6epoch.json",
        "data/config/diagnostic_cascade.json",
    ),
    (
        "picard_framework/runs/smoke_cascade_multiplex_6epoch.json",
        "data/config/diagnostic_cascade_multiplex.json",
    ),
]

CASCADE_RESULT_KEYS = frozenset({
    "new_tier0_agents",
    "new_tier1_agents",
    "tier_advancements",
    "tests_ordered",
    "confinements_ordered",
    "wearable_offers",
    "fleet_sops_unlocked",
})


def _run_cascade_smoke(spec_rel: str) -> list[dict]:
    spec_path = os.path.join(REPO_ROOT, spec_rel)
    spec = PicardRunSpec.from_picard_json(REPO_ROOT, spec_path)
    assert spec.legacy_cfg.get("diagnostic_cascade", {}).get("enabled") is True

    sim = ShipSimulation(spec, display=False, repo_root=REPO_ROOT)
    result = sim.run()
    return result.history


@pytest.mark.timeout(120)
@pytest.mark.parametrize("spec_rel,cascade_config", CASCADE_SMOKE_SPECS)
def test_cascade_smoke_run_completes(spec_rel: str, cascade_config: str) -> None:
    """Cascade-enabled smoke run completes and records cascade telemetry."""
    history = _run_cascade_smoke(spec_rel)
    assert len(history) == 6

    spec = PicardRunSpec.from_picard_json(
        REPO_ROOT, os.path.join(REPO_ROOT, spec_rel),
    )
    assert spec.legacy_cfg["diagnostic_cascade"]["config_path"] == cascade_config

    for rec in history:
        assert rec["epoch"] >= 0
        cascade = rec.get("diagnostic_cascade")
        assert cascade is not None, f"epoch {rec['epoch']} missing diagnostic_cascade"
        assert CASCADE_RESULT_KEYS.issubset(cascade.keys())

    assert any(
        rec["diagnostic_cascade"].get("tier_advancements")
        or rec["diagnostic_cascade"].get("new_tier0_agents")
        or rec["diagnostic_cascade"].get("new_tier1_agents")
        for rec in history
    ), "expected at least one cascade entry or tier advancement"


@pytest.mark.timeout(120)
def test_cascade_smoke_standard_tier2_advancement_by_epoch_1() -> None:
    """Standard cascade smoke advances symptomatic agents to Tier 2 within epoch 1."""
    history = _run_cascade_smoke("picard_framework/runs/smoke_cascade_6epoch.json")
    epoch1 = history[1]["diagnostic_cascade"]
    tier2_plus = [
        adv for adv in epoch1.get("tier_advancements", [])
        if adv.get("to_tier", 0) >= 2
    ]
    assert tier2_plus, (
        "epoch 1 should advance at least one agent to Tier 2 with default seed"
    )


@pytest.mark.timeout(120)
def test_cascade_smoke_multiplex_config_and_tier1_panel() -> None:
    """Multiplex smoke spec loads multiplex cascade config with Tier-1 panel."""
    spec_path = os.path.join(
        REPO_ROOT, "picard_framework/runs/smoke_cascade_multiplex_6epoch.json",
    )
    spec = PicardRunSpec.from_picard_json(REPO_ROOT, spec_path)
    assert spec.legacy_cfg["diagnostic_cascade"]["config_path"] == (
        "data/config/diagnostic_cascade_multiplex.json"
    )

    from crusher_labs.diagnostic_cascade import build_cascade_engine

    engine = build_cascade_engine(spec.legacy_cfg, repo_root=REPO_ROOT)
    assert engine is not None
    assert engine.tiers[1].name == "Rapid Multiplex Panel"
    assert engine.tiers[1].tests == ["clinical_multiplex_panel"]
    assert "multiplex_panel_kits" in engine.tiers[1].cost_per_agent.get(
        "materials", {},
    )
