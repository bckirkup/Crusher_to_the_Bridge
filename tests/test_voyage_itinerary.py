"""Voyage itinerary layer — golden compatibility + effects sensitivity."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

from engines.voyage_itinerary import (  # noqa: E402
    apply_ashore_and_embarkation,
    apply_embarkation_surge_locations,
    load_voyage_config,
    merge_voyage_overrides,
    normalize_voyage_config,
    resolve_epoch_state,
    voyage_config_path_for_platform,
)
from orchestrator_init import (  # noqa: E402
    apply_voyage_dining_meal_weights,
    load_and_merge_voyage_config,
)


PLATFORMS = ("expedition_cruise_450", "classic_cruise_1900", "spirit_cruise_3000", "mega_cruise_5000")

GOLDEN_MEAL_WEIGHTS = {
    "expedition": {
        "breakfast": {"buffet": 0.0, "mdr": 0.85, "specialty": 0.0, "crew_mess": 0.15},
        "lunch": {"buffet": 0.0, "mdr": 0.70, "specialty": 0.0, "crew_mess": 0.30},
        "dinner": {"buffet": 0.0, "mdr": 0.90, "specialty": 0.05, "crew_mess": 0.05},
    },
    "classic": {
        "breakfast": {"buffet": 0.75, "mdr": 0.20, "specialty": 0.05},
        "lunch": {"buffet": 0.60, "mdr": 0.25, "specialty": 0.15},
        "dinner": {"buffet": 0.20, "mdr": 0.60, "specialty": 0.20},
    },
    "spirit": {
        "breakfast": {"buffet": 0.80, "mdr": 0.18, "specialty": 0.02},
        "lunch": {"buffet": 0.65, "mdr": 0.25, "specialty": 0.10},
        "dinner": {"buffet": 0.25, "mdr": 0.65, "specialty": 0.10},
    },
    "mega": {
        "breakfast": {"buffet": 0.70, "mdr": 0.15, "specialty": 0.15},
        "lunch": {"buffet": 0.50, "mdr": 0.20, "specialty": 0.30},
        "dinner": {"buffet": 0.20, "mdr": 0.45, "specialty": 0.35},
    },
}


def _sample_itinerary_cfg(*, effects_enabled: bool = True) -> dict:
    return normalize_voyage_config({
        "voyage": {
            "effects_enabled": effects_enabled,
            "total_epochs": 48,
            "epoch_duration_hours": 1,
            "itinerary": [
                {
                    "day": 1,
                    "type": "embarkation",
                    "port": "Home",
                    "embarkation_window_epochs": [10, 14],
                    "buffet_surge_fraction": 0.80,
                },
                {
                    "day": 2,
                    "type": "port_day",
                    "port": "Cozumel",
                    "disembark_fraction": 0.70,
                    "disembark_window_epochs": [8, 10],
                    "reembark_window_epochs": [16, 19],
                    "shore_infection_probability": 1.0,
                },
            ],
        },
    })


def test_missing_voyage_config_is_identity() -> None:
    cfg = load_voyage_config("/nonexistent/voyage_config.json")
    state = resolve_epoch_state(cfg, 5)
    assert state.effects_active is False
    assert state.day_type == "sea_day"
    assert state.contact_multiplier == 1.0
    assert state.dining_multiplier == {"breakfast": 1.0, "lunch": 1.0, "dinner": 1.0}


@pytest.mark.parametrize("platform_id", PLATFORMS)
def test_platform_voyage_config_effects_disabled(platform_id: str) -> None:
    path = voyage_config_path_for_platform(str(REPO_ROOT), platform_id)
    cfg = load_voyage_config(path)
    assert cfg["voyage"]["effects_enabled"] is False
    state = resolve_epoch_state(cfg, 30)
    assert state.effects_active is False
    assert state.day_type == "sea_day"


@pytest.mark.parametrize("platform_id,klass", [
    ("expedition_cruise_450", "expedition"),
    ("classic_cruise_1900", "classic"),
    ("spirit_cruise_3000", "spirit"),
    ("mega_cruise_5000", "mega"),
])
def test_platform_dining_meal_weights_golden(platform_id: str, klass: str) -> None:
    path = voyage_config_path_for_platform(str(REPO_ROOT), platform_id)
    cfg = load_voyage_config(path)
    assert cfg["platform_class"] == klass
    assert cfg["dining_meal_weights"] == GOLDEN_MEAL_WEIGHTS[klass]


def test_expedition_meal_weights_replace_yaml_buffet_defaults() -> None:
    voyage = load_voyage_config(
        voyage_config_path_for_platform(str(REPO_ROOT), "expedition_cruise_450"),
    )
    cfg = {
        "agent_behavior": {
            "dining_rotation_probability": 0.0,
            "dining_meal_weights": {
                "breakfast": {"buffet": 0.6, "mdr": 0.3, "specialty": 0.1},
                "lunch": {"buffet": 0.5, "mdr": 0.3, "specialty": 0.2},
                "dinner": {"buffet": 0.2, "mdr": 0.5, "specialty": 0.3},
            },
        },
    }
    merged = apply_voyage_dining_meal_weights(cfg, voyage)
    breakfast = merged["agent_behavior"]["dining_meal_weights"]["breakfast"]
    assert breakfast["buffet"] == 0.0
    assert breakfast["mdr"] == 0.85


def test_effects_off_ignores_configured_itinerary() -> None:
    cfg = _sample_itinerary_cfg(effects_enabled=False)
    # Epoch 9 = day1 hour 8 would be port/embark otherwise
    state = resolve_epoch_state(cfg, 9)
    assert state.effects_active is False
    assert state.day_type == "sea_day"
    assert state.contact_multiplier == 1.0


def test_port_day_windows_sensitivity() -> None:
    cfg = _sample_itinerary_cfg(effects_enabled=True)
    # Day 2 starts at epoch 25; epoch_of_day 8 → absolute epoch 33
    disembark = resolve_epoch_state(cfg, 33)
    assert disembark.effects_active is True
    assert disembark.day_type == "port_day"
    assert disembark.in_disembark_window is True
    assert disembark.contact_multiplier == pytest.approx(0.4)
    assert disembark.dining_multiplier["lunch"] == pytest.approx(0.3)
    assert disembark.shore_infection_probability == 1.0

    between = resolve_epoch_state(cfg, 37)  # epoch_of_day 12
    assert between.between_ashore_windows is True
    assert between.onboard_fraction == pytest.approx(0.3)

    reembark = resolve_epoch_state(cfg, 41)  # epoch_of_day 16
    assert reembark.in_reembark_window is True
    assert reembark.onboard_fraction == 1.0


def test_ashore_marking_and_clear() -> None:
    class Agent:
        def __init__(self, aid: int, role: str) -> None:
            self.agent_id = aid
            self.role = role
            self.ashore = False
            self.current_location = "Home"

    rng = np.random.default_rng(0)
    agents = [Agent(i, "passenger") for i in range(20)] + [Agent(100, "crew")]
    cfg = _sample_itinerary_cfg(effects_enabled=True)
    disembark = resolve_epoch_state(cfg, 33)
    apply_ashore_and_embarkation(agents, disembark, rng=rng)
    ashore_pax = sum(1 for a in agents if a.role == "passenger" and a.ashore)
    assert ashore_pax == 14  # 0.7 * 20
    assert agents[-1].ashore is False  # crew

    reembark = resolve_epoch_state(cfg, 41)
    apply_ashore_and_embarkation(agents, reembark, rng=rng)
    assert all(not a.ashore for a in agents)


def test_embarkation_surge_moves_passengers_to_dining() -> None:
    class Agent:
        def __init__(self, aid: int) -> None:
            self.agent_id = aid
            self.role = "passenger"
            self.ashore = False
            self.current_location = "Cabin"

    rng = np.random.default_rng(1)
    agents = [Agent(i) for i in range(50)]
    cfg = _sample_itinerary_cfg(effects_enabled=True)
    # Day1 embark window hour 10 → epoch 11
    embark = resolve_epoch_state(cfg, 11)
    assert embark.in_embarkation_window is True
    assert embark.buffet_surge_fraction == pytest.approx(0.8)
    catalog = [{"name": "BuffetLido", "service_type": "buffet"}]
    apply_embarkation_surge_locations(
        agents, embark, rng=rng, dining_catalog=catalog,
    )
    in_buffet = sum(1 for a in agents if a.current_location == "BuffetLido")
    assert in_buffet == 40


def test_shore_infection_probability_is_unwired_stub() -> None:
    """shore_infection_probability=1.0 must not introduce infections."""
    from picard_framework import PicardRunSpec, ShipSimulation

    # Tiny destroyer run with effects on + port day + shore_infection=1
    voyage_override = {
        "effects_enabled": True,
        "total_epochs": 12,
        "epoch_duration_hours": 1,
        "itinerary": [
            {
                "day": 1,
                "type": "port_day",
                "disembark_fraction": 0.5,
                "disembark_window_epochs": [0, 23],
                "reembark_window_epochs": [24, 24],
                "shore_infection_probability": 1.0,
            },
        ],
    }
    spec = PicardRunSpec.from_picard_json(
        str(REPO_ROOT),
        str(REPO_ROOT / "picard_framework" / "runs" / "smoke_2epoch.json"),
    )
    # Rebuild with voyage override + 6 epochs
    raw = json.loads(
        (REPO_ROOT / "picard_framework" / "runs" / "smoke_2epoch.json").read_text(),
    )
    raw = copy.deepcopy(raw)
    raw["run"]["num_epochs"] = 6
    raw["run"]["random_seed"] = 7
    raw.setdefault("config_overrides", {})["voyage"] = voyage_override
    tmp = REPO_ROOT / "telemetry_buffer" / "_tmp_voyage_shore_stub.json"
    tmp.write_text(json.dumps(raw), encoding="utf-8")
    try:
        spec = PicardRunSpec.from_picard_json(str(REPO_ROOT), str(tmp))
        sim = ShipSimulation(spec, display=False)
        sim.run(n_epochs=6)
        # Shore infection stub: no automatic new infections from shore alone.
        # Baseline may still have the initial seed infection(s).
        infected = [
            a for a in sim.engine.agents
            if a.is_infected
        ]
        # With shore_infection=1.0, if wired, nearly all ashore pax would infect.
        # Assert we did not mass-infect the population.
        assert len(infected) < len(sim.engine.agents) * 0.5
        hist = sim.state.simulation_history
        assert hist[0]["voyage_epoch"]["effects_active"] is True
        assert hist[0]["voyage_epoch"]["shore_infection_probability"] == 1.0
    finally:
        tmp.unlink(missing_ok=True)


def test_effects_flag_changes_ashore_counts() -> None:
    from picard_framework import PicardRunSpec, ShipSimulation

    def _run(effects: bool) -> int:
        raw = json.loads(
            (REPO_ROOT / "picard_framework" / "runs" / "smoke_2epoch.json").read_text(),
        )
        raw = copy.deepcopy(raw)
        raw["run"]["num_epochs"] = 4
        raw["run"]["random_seed"] = 11
        raw.setdefault("config_overrides", {})["voyage"] = {
            "effects_enabled": effects,
            "epoch_duration_hours": 1,
            "itinerary": [
                {
                    "day": 1,
                    "type": "port_day",
                    "disembark_fraction": 0.8,
                    "disembark_window_epochs": [0, 23],
                    "reembark_window_epochs": [24, 24],
                    "shore_infection_probability": 0.0,
                },
            ],
        }
        tmp = REPO_ROOT / "telemetry_buffer" / f"_tmp_voyage_flag_{int(effects)}.json"
        tmp.write_text(json.dumps(raw), encoding="utf-8")
        try:
            spec = PicardRunSpec.from_picard_json(str(REPO_ROOT), str(tmp))
            sim = ShipSimulation(spec, display=False)
            sim.run(n_epochs=2)
            return sum(1 for a in sim.engine.agents if getattr(a, "ashore", False))
        finally:
            tmp.unlink(missing_ok=True)

    assert _run(False) == 0
    assert _run(True) > 0


def test_flag_off_picard_fingerprint_stable() -> None:
    """effects_enabled false must not change infection outcomes vs no voyage override."""
    from picard_framework import PicardRunSpec, ShipSimulation

    def _fingerprint(with_voyage_block: bool) -> tuple:
        raw = json.loads(
            (REPO_ROOT / "picard_framework" / "runs" / "smoke_2epoch.json").read_text(),
        )
        raw = copy.deepcopy(raw)
        raw["run"]["num_epochs"] = 4
        raw["run"]["random_seed"] = 42
        if with_voyage_block:
            raw.setdefault("config_overrides", {})["voyage"] = {
                "effects_enabled": False,
                "itinerary": [
                    {
                        "day": 1,
                        "type": "port_day",
                        "disembark_fraction": 0.9,
                        "disembark_window_epochs": [0, 23],
                        "reembark_window_epochs": [24, 24],
                    },
                ],
            }
        tmp = REPO_ROOT / "telemetry_buffer" / f"_tmp_voyage_fp_{int(with_voyage_block)}.json"
        tmp.write_text(json.dumps(raw), encoding="utf-8")
        try:
            spec = PicardRunSpec.from_picard_json(str(REPO_ROOT), str(tmp))
            sim = ShipSimulation(spec, display=False)
            sim.run(n_epochs=4)
            infected = tuple(
                sorted(
                    a.agent_id for a in sim.engine.agents if a.is_infected
                ),
            )
            locs = tuple(
                sorted(
                    (a.agent_id, a.current_location) for a in sim.engine.agents
                ),
            )
            return infected, locs
        finally:
            tmp.unlink(missing_ok=True)

    assert _fingerprint(False) == _fingerprint(True)


def test_merge_voyage_overrides_deep() -> None:
    base = load_voyage_config(
        voyage_config_path_for_platform(str(REPO_ROOT), "mega_cruise_5000"),
    )
    merged = merge_voyage_overrides(base, {"effects_enabled": True, "itinerary": []})
    assert merged["voyage"]["effects_enabled"] is True
    assert merged["dining_meal_weights"]["breakfast"]["buffet"] == 0.70


def test_load_and_merge_from_cfg_platform_path() -> None:
    cfg = {
        "ship_graph": {
            "spatial_layout": "data/platforms/spirit_cruise_3000/spatial_layout.json",
        },
        "voyage": {"effects_enabled": False},
    }
    out = load_and_merge_voyage_config(cfg, repo_root=str(REPO_ROOT))
    assert out["platform_class"] == "spirit"
    assert out["voyage"]["effects_enabled"] is False
