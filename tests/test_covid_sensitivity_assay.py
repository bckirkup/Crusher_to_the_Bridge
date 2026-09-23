"""covid_sensitivity_assay_v1: the extended arm grammar and its design.

No hull runs here. The design loads and enumerates, the three new arm
override keys land in a real fit run-spec, and the cfg-level transmission
precedence is proven on a minimal Picard spec.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from picard_framework.covid_boarding_screen import (
    apply_arm_overrides,
    enumerate_cells,
    load_design,
)
from picard_framework.covid_theta_fit import (
    build_fit_run_spec,
    load_covid_profile,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DESIGN_PATH = (
    REPO_ROOT / "picard_framework/runs/covid_sensitivity_assay_v1_design.json"
)
THETA = 4.22e10


@pytest.fixture(scope="module")
def design():
    return load_design(str(DESIGN_PATH))


def _raw_spec():
    return build_fit_run_spec("diamond_princess_2020", THETA, 20200205)


# ── design + enumeration ──────────────────────────────────────────────────

def test_design_loads_the_declared_240_cells(design):
    cells = enumerate_cells(design)
    assert len(cells) == 240
    assert len({c.key for c in cells}) == 240
    assert all(c.theta == pytest.approx(THETA) for c in cells)
    assert design.arm_ids[0] == "A0_declared"
    assert design.arm_ids[-1] == "A11_arrest_bound"


def test_canary_rows_are_the_declared_index_ranges(design):
    cells = enumerate_cells(design)
    assert [c.index for c in cells if c.arm_id == "A0_declared"] == list(
        range(0, 20)
    )
    assert [c.index for c in cells if c.arm_id == "A11_arrest_bound"] == list(
        range(220, 240)
    )


def test_every_arm_override_uses_declared_keys(design):
    for arm in design.arms:
        assert arm["arm_id"]
        assert isinstance(arm.get("overrides", {}), dict)


# ── new arm keys reaching the run spec ────────────────────────────────────

def test_scheduled_protocol_window_retimes_the_order():
    raw = _raw_spec()
    apply_arm_overrides(
        raw,
        {"scheduled_protocol_window": {
            "protocol_id": "SOP-017", "start_day": 12, "end_day": 30,
        }},
        profile=load_covid_profile(),
    )
    entry = raw["config_overrides"]["scenario_schedule"]["protocols"][0]
    assert entry["protocol_id"] == "SOP-017"
    assert entry["start_day"] == 12
    assert entry["end_day"] == 30


def test_scheduled_protocol_window_raises_without_the_order():
    raw = _raw_spec()
    raw["config_overrides"]["scenario_schedule"]["protocols"] = []
    with pytest.raises(ValueError, match="no SOP-017"):
        apply_arm_overrides(
            raw,
            {"scheduled_protocol_window": {
                "protocol_id": "SOP-017", "start_day": 12, "end_day": 30,
            }},
            profile=load_covid_profile(),
        )


def test_infection_counters_land_without_dropping_ship_graph():
    raw = _raw_spec()
    before_graph = copy.deepcopy(raw["config_overrides"]["ship_graph"])
    counters = [
        {"counter_id": "passenger_reported_case_rate",
         "metric": "reported_case_rate",
         "filter": {"role_group": "passenger"},
         "threshold": 0.0004, "on_exceed": "confine_symptomatic"},
    ]
    apply_arm_overrides(
        raw, {"infection_counters": counters}, profile=load_covid_profile(),
    )
    graph = raw["config_overrides"]["ship_graph"]
    assert graph["infection_counters"] == counters
    for key in before_graph:
        assert key in graph, f"ship_graph.{key} dropped by the arm override"


def test_transmission_overrides_merge_not_replace():
    raw = _raw_spec()
    raw["config_overrides"].setdefault("transmission", {})[
        "sanitary_visit_mode"
    ] = "dwell_weighted"
    apply_arm_overrides(
        raw,
        {"transmission_overrides": {"confinement_isolation_factor": 0.0}},
        profile=load_covid_profile(),
    )
    tx = raw["config_overrides"]["transmission"]
    assert tx["confinement_isolation_factor"] == 0.0
    assert tx["sanitary_visit_mode"] == "dwell_weighted"


def test_combined_arm_applies_every_key():
    raw = _raw_spec()
    apply_arm_overrides(
        raw,
        {
            "scheduled_protocol_id": "SOP-017-ALLHANDS",
            "pathogen_pool_transport": "none",
            "scheduled_protocol_window": {
                "protocol_id": "SOP-017", "start_day": 12, "end_day": 30,
            },
            "transmission_overrides": {"confinement_isolation_factor": 0.0},
            "profile_route_efficiency_multipliers": {"direct_contact": 0.25},
            "infection_counters": [{
                "counter_id": "passenger_reported_case_rate",
                "metric": "reported_case_rate",
                "filter": {"role_group": "passenger"},
                "threshold": 0.0004, "on_exceed": "confine_symptomatic",
            }],
        },
        profile=load_covid_profile(),
    )
    entry = raw["config_overrides"]["scenario_schedule"]["protocols"][0]
    assert entry["protocol_id"] == "SOP-017-ALLHANDS"
    assert entry["start_day"] == 12
    counters = raw["config_overrides"]["ship_graph"]["infection_counters"]
    assert counters[0]["threshold"] == pytest.approx(0.0004)
    assert (
        raw["config_overrides"]["transmission"]["confinement_isolation_factor"]
        == 0.0
    )


def test_unknown_key_still_raises():
    raw = _raw_spec()
    with pytest.raises(ValueError, match="unknown arm override key"):
        apply_arm_overrides(
            raw, {"bogus_channel": 1}, profile=load_covid_profile(),
        )


# ── transmission cfg precedence at the engine ─────────────────────────────

def test_transmission_cfg_overrides_reach_the_core():
    from picard_framework.run_spec import PicardRunSpec
    from picard_framework.simulation.ship_simulation import ShipSimulation

    spec_path = REPO_ROOT / "picard_framework/runs/smoke_2epoch.json"
    raw = json.loads(spec_path.read_text(encoding="utf-8"))
    raw.setdefault("config_overrides", {})["transmission"] = {
        "confinement_isolation_factor": 0.0,
        "corridor_direct_contact_factor": 0.02,
    }
    spec = PicardRunSpec.from_picard_dict(str(REPO_ROOT), raw)
    sim = ShipSimulation(spec, display=False)
    sim.initialize()
    assert sim.tx_core.confinement_isolation_factor == 0.0
    assert sim.tx_core.corridor_direct_contact_factor == pytest.approx(0.02)


def test_platform_factor_survives_without_an_override():
    from picard_framework.run_spec import PicardRunSpec
    from picard_framework.simulation.ship_simulation import ShipSimulation

    spec = PicardRunSpec.from_picard_json(
        str(REPO_ROOT),
        str(REPO_ROOT / "picard_framework/runs/smoke_2epoch.json"),
    )
    sim = ShipSimulation(spec, display=False)
    sim.initialize()
    assert sim.tx_core.confinement_isolation_factor == pytest.approx(0.05)
