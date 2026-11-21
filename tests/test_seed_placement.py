"""Declared seed placement (COVID-SEED-RING-01).

``initiation.explicit_seeds[].placement`` constrains the pool the seed
draws from — the declared boarding-window footprint of the index rather
than a draw over every eligible host. ``dining_service_type`` keeps hosts
whose assigned dining venue resolves to the declared service type, read
from the engine's zone catalog where one exists and from the venue-name
heuristic otherwise.

Sensitivity, invariants and validation only; no goldens.
"""

from __future__ import annotations

import numpy as np
import pytest

from engines.infection_dynamics_bridge import KorkinAgent
from engines.initiation import apply_explicit_seeds, resolve_initiation_plan
from engines.sim_clock import SimClock

PATHOGEN = "test_pathogen"
ZONE = "Test_Zone"


def _clock() -> SimClock:
    return SimClock(epoch_duration_hours=6.0, mode="hours")


def _agent(
    agent_id: int,
    *,
    role: str = "passenger",
    dining_zone: str = ZONE,
) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=agent_id,
        role=role,
        immune=False,
        home_zone=ZONE,
        dining_zone=dining_zone,
        work_zone=ZONE,
        free_zone=ZONE,
        schedule=["Free"] * 4,
    )
    agent.clock = _clock()
    agent.current_location = ZONE
    return agent


def _profile() -> dict:
    return {
        "shedding_curve_log10": [7.0] * 40,
        "asymptomatic_shedding_log10": [7.0] * 40,
        "symptom_onset_day": 0.0,
        "recovery_day": 1000.0,
        "airborne_half_life_hours": 24.0,
        "dose_response": {"model": "exponential", "k": 0.05},
    }


class _FakeEngine:
    def __init__(
        self,
        dining_zones: list[str] | None = None,
        zones: list[dict] | None = None,
    ) -> None:
        dining_zones = dining_zones or [ZONE] * 40
        self.agents = [
            _agent(i, dining_zone=dz) for i, dz in enumerate(dining_zones)
        ]
        self.clock = _clock()
        self.initiation_manifest: dict = {"mode": "legacy"}
        if zones is not None:
            self.zones = zones


def _plan(**seed_fields):
    seed = {"pathogen": PATHOGEN, "count": 1, "epoch": 0}
    seed.update(seed_fields)
    return resolve_initiation_plan(
        {"initiation": {"explicit_seeds": [seed]}}, {PATHOGEN: _profile()},
    )


class TestPlacementResolution:
    def test_no_placement_leaves_the_field_unset(self) -> None:
        assert _plan().seeds[0].placement_dining_service_type is None

    def test_declared_service_type_resolves(self) -> None:
        seed = _plan(
            placement={"dining_service_type": "buffet"},
        ).seeds[0]
        assert seed.placement_dining_service_type == "buffet"

    def test_non_mapping_placement_is_refused(self) -> None:
        with pytest.raises(ValueError, match="placement must be a mapping"):
            _plan(placement="buffet")

    def test_unknown_placement_key_is_refused(self) -> None:
        with pytest.raises(ValueError, match="not placement fields"):
            _plan(placement={"dining_service_type": "buffet", "deck": 14})

    @pytest.mark.parametrize("bad", [17, ""])
    def test_bad_service_type_is_refused(self, bad) -> None:
        with pytest.raises(ValueError, match="dining_service_type"):
            _plan(placement={"dining_service_type": bad})

    def test_null_service_type_removes_the_field(self) -> None:
        assert _plan(
            placement={"dining_service_type": None},
        ).seeds[0].placement_dining_service_type is None


class TestPlacementDraw:
    def test_only_matching_diners_are_seeded(self) -> None:
        # Name-heuristic fallback: no engine zone catalog.
        engine = _FakeEngine(
            dining_zones=["Windjammer", "MainDining_U"] * 20,
        )
        plan = _plan(
            count=4,
            placement={"dining_service_type": "buffet"},
        )
        records = apply_explicit_seeds(
            plan, engine, 0, np.random.default_rng(1),
            {PATHOGEN: _profile()},
        )
        seeded = [a for a in engine.agents if PATHOGEN in a.infections]
        assert len(seeded) == 4
        assert all(a.dining_zone == "Windjammer" for a in seeded)
        assert records[0]["placement"] == {"dining_service_type": "buffet"}

    def test_zone_catalog_wins_over_name_heuristic(self) -> None:
        # A venue named like a buffet but declared "specialty" in the
        # catalog does not count as the buffet footprint.
        engine = _FakeEngine(
            dining_zones=["The_Grill", "SitDown_Room"] * 20,
            zones=[
                {
                    "name": "The_Grill",
                    "type": "Dining",
                    "dining_service_type": "specialty",
                },
                {
                    "name": "SitDown_Room",
                    "type": "Dining",
                    "dining_service_type": "buffet",
                },
            ],
        )
        plan = _plan(
            count=4,
            placement={"dining_service_type": "buffet"},
        )
        apply_explicit_seeds(
            plan, engine, 0, np.random.default_rng(1),
            {PATHOGEN: _profile()},
        )
        seeded = [a for a in engine.agents if PATHOGEN in a.infections]
        assert len(seeded) == 4
        assert all(a.dining_zone == "SitDown_Room" for a in seeded)

    def test_empty_pool_is_refused(self) -> None:
        engine = _FakeEngine(dining_zones=["MainDining_U"] * 40)
        plan = _plan(placement={"dining_service_type": "buffet"})
        with pytest.raises(ValueError, match="empty seed pool"):
            apply_explicit_seeds(
                plan, engine, 0, np.random.default_rng(1),
                {PATHOGEN: _profile()},
            )

    def test_no_placement_draws_over_everything(self) -> None:
        engine = _FakeEngine(
            dining_zones=["Windjammer", "MainDining_U"] * 20,
        )
        plan = _plan(count=1)
        records = apply_explicit_seeds(
            plan, engine, 0, np.random.default_rng(1),
            {PATHOGEN: _profile()},
        )
        assert records[0]["placement"] is None
