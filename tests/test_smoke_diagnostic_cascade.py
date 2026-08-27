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

from decision_engine.actions import ActionEnvelope
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


def _run_cascade_smoke(
    spec_rel: str,
    *,
    prevalence_confinement: bool = False,
) -> list[dict]:
    spec_path = os.path.join(REPO_ROOT, spec_rel)
    spec = PicardRunSpec.from_picard_json(REPO_ROOT, spec_path)
    assert spec.legacy_cfg.get("diagnostic_cascade", {}).get("enabled") is True
    if prevalence_confinement:
        # This fixture deliberately pins prevalence-based confinement because
        # the shipped default now uses cumulative reported passenger cases.
        spec.legacy_cfg.setdefault("ship_graph", {})["infection_counters"] = [
            {
                "counter_id": "fixture_attack_rate",
                "label": "Fixture Attack Rate",
                "metric": "attack_rate",
                "filter": {},
                "threshold": 0.03,
                "on_exceed": "confine_symptomatic",
            },
        ]

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
def test_cascade_smoke_standard_clinical_progression() -> None:
    """Standard cascade smoke orders clinical tests under default seed."""
    spec_path = os.path.join(
        REPO_ROOT, "picard_framework/runs/smoke_cascade_6epoch.json",
    )
    spec = PicardRunSpec.from_picard_json(REPO_ROOT, spec_path)
    spec.num_epochs = 24
    sim = ShipSimulation(spec, display=False, repo_root=REPO_ROOT)
    sim.initialize()
    assert sim.state is not None
    assert sim.engine is not None
    symptomatic = next(
        agent for agent in sim.engine.agents
        if agent.is_symptomatic
    )
    agent_id = symptomatic.agent_id
    sim.state.quarantined_ids.discard(agent_id)
    sim.state.isolated_ids.discard(agent_id)
    sim.engine.quarantined_ids.discard(agent_id)
    sim.engine.isolated_ids.discard(agent_id)
    first_epoch = sim.step(ActionEnvelope(
        epoch=0,
        actions={
            "medical": [
                {"kind": "report_sick_call", "agent_id": agent_id},
            ],
        },
    ))
    history = [first_epoch.epoch_record]
    history.extend(sim.run().history[1:])
    assert any(
        rec["diagnostic_cascade"].get("tests_ordered")
        for rec in history
    ), "expected clinical tests ordered during cascade smoke run"
    assert any(
        rec["diagnostic_cascade"].get("new_tier0_agents")
        for rec in history
    ), "expected Tier-0 cascade entry during smoke run"
    assert history[-1]["summary"].get("quarantined", 0) > 0, (
        "expected confinement by end of cascade smoke run"
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
