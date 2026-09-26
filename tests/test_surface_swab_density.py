"""Surface-swab density channel: graded sensitivity, bounds, and invariants.

The repaired `surface_pool_density` arm swabs the deposited surface pool as
a per-cm² density over the zone's high-touch area, samples
`swab_area_cm2` of it, and applies Park 2015's per-swab copy LOD. These
tests grade the knobs (copies, area, swab area, surface class) and pin the
censoring contract — a below-LOD reading keeps its quantitative value.
"""

from __future__ import annotations

import math
from unittest.mock import MagicMock

import numpy as np
import pytest

from crusher_labs.observation_core import (
    SWAB_AREA_CM2,
    SWAB_LOD_COPIES_BY_SURFACE,
    SWAB_RECOVERY_EFFICIENCY_BOUNDS,
    TargetedSurfaceSwab,
)
from engines.transmission_core import (
    CABIN_COMPARTMENT_SEPARATOR,
    TransmissionCore,
)

ZONE = "Galley_M"
AREA_CM2 = 6.0 * 1.0e4  # HIGH_TOUCH_AREA_M2 order: a public space


def _swab(seed: int = 11) -> TargetedSurfaceSwab:
    return TargetedSurfaceSwab(rng=np.random.default_rng(seed))


def _numeric_fields(result: dict) -> list[float]:
    keys = (
        "surface_copies_total", "high_touch_area_cm2",
        "surface_density_copies_per_cm2", "swab_area_cm2",
        "sampled_copies", "actual_collection_efficiency",
        "recovered_copies", "lod_copies_per_swab",
        "background_fluorescence",
    )
    return [float(result[k]) for k in keys]


class TestGradedSensitivity:
    def test_recovered_copies_increase_and_ct_falls_with_pool(self) -> None:
        copies = [1e3, 1e5, 1e7]
        results = [
            _swab(seed=5).swab_surface(ZONE, c, AREA_CM2) for c in copies
        ]
        recovered = [r["recovered_copies"] for r in results]
        cts = [r["ct_value"] for r in results]
        assert recovered == sorted(recovered)
        assert max(recovered) / max(min(recovered), 1e-12) > 50.0
        assert cts == sorted(cts, reverse=True)
        assert cts[0] - cts[-1] > 5.0

    def test_recovery_is_bounded_by_sampled_copies(self) -> None:
        result = _swab(seed=5).swab_surface(ZONE, 1e9, AREA_CM2)
        assert result["recovered_copies"] <= result["sampled_copies"] * 1.05
        assert (
            SWAB_RECOVERY_EFFICIENCY_BOUNDS[0]
            <= result["actual_collection_efficiency"]
            <= SWAB_RECOVERY_EFFICIENCY_BOUNDS[1]
        )


class TestAreaSensitivity:
    def test_recovered_falls_as_inverse_area(self) -> None:
        # Same seed + careful technique: the efficiency draw is shared, so
        # recovered tracks sampled = copies * swab_area / area.
        areas = [3.0e4, 6.0e4, 1.2e5]
        results = [
            _swab(seed=5).swab_surface(ZONE, 1e8, a) for a in areas
        ]
        sampled = [r["sampled_copies"] for r in results]
        for a, s in zip(areas, sampled):
            assert s == pytest.approx(1e8 * SWAB_AREA_CM2 / a)
        assert sampled == sorted(sampled, reverse=True)
        recovered = [r["recovered_copies"] for r in results]
        # lognormal noise <= a few percent: the 2x area steps dominate.
        assert recovered[0] > recovered[1] * 1.5
        assert recovered[1] > recovered[2] * 1.5


class TestSwabAreaSensitivity:
    @pytest.mark.parametrize("area", [50.0, 100.0, 200.0])
    def test_sampled_copies_proportional_to_swab_area(
        self, area: float,
    ) -> None:
        instrument = TargetedSurfaceSwab(
            swab_area_cm2=area, rng=np.random.default_rng(5),
        )
        result = instrument.swab_surface(ZONE, 1e8, AREA_CM2)
        assert result["sampled_copies"] == pytest.approx(
            1e8 * area / AREA_CM2,
        )


class TestLimitOfDetection:
    def test_just_below_lod_is_censored_not_zeroed(self) -> None:
        lod = SWAB_LOD_COPIES_BY_SURFACE["nonporous_hard"]
        # Density scaled so sampled copies sit just under the LOD even at
        # perfect recovery: area large enough that sampled < lod.
        area = 1e6 * SWAB_AREA_CM2 / (lod * 0.5)
        result = _swab(seed=5).swab_surface(ZONE, 1e6, area)
        assert result["sampled_copies"] < lod
        assert result["recovered_copies"] > 0.0
        assert result["detected"] is False
        assert result["censored_below_lod"] is True

    def test_above_lod_detects(self) -> None:
        result = _swab(seed=5).swab_surface(ZONE, 1e9, AREA_CM2)
        assert result["detected"] is True
        assert result["censored_below_lod"] is False

    def test_toilet_seat_requires_more_copies_than_hard(self) -> None:
        # Midpoint density: above the hard-surface LOD, below toilet-seat.
        lod_h = SWAB_LOD_COPIES_BY_SURFACE["nonporous_hard"]
        lod_t = SWAB_LOD_COPIES_BY_SURFACE["toilet_seat"]
        target = math.sqrt(lod_h * lod_t)  # geometric midpoint
        copies = target / 0.35 * AREA_CM2 / SWAB_AREA_CM2 * 1.5
        hard = _swab(seed=5).swab_surface(ZONE, copies, AREA_CM2)
        seat = _swab(seed=5).swab_surface(ZONE, copies, AREA_CM2, surface_class="toilet_seat")
        assert hard["detected"] is True
        assert seat["detected"] is False
        assert seat["censored_below_lod"] is True
        assert seat["lod_copies_per_swab"] > hard["lod_copies_per_swab"]


class TestBoundaries:
    @pytest.mark.parametrize(
        "copies,area",
        [(0.0, AREA_CM2), (1e6, 0.0), (1e6, -5.0), (1e6, math.inf), (1e6, math.nan)],
    )
    def test_zero_and_nonfinite_inputs(self, copies: float, area: float) -> None:
        result = _swab(seed=5).swab_surface(ZONE, copies, area)
        assert result["recovered_copies"] == pytest.approx(0.0)
        assert result["ct_value"] is None
        assert result["detected"] is False
        assert result["censored_below_lod"] is False
        for value in _numeric_fields(result):
            assert math.isfinite(value)
            assert value >= 0.0


class TestInvariants:
    def test_randomized_sweep_stays_in_bounds(self) -> None:
        rng = np.random.default_rng(77)
        for _ in range(30):
            copies = float(rng.uniform(0.0, 1e9))
            area = float(rng.uniform(1e3, 1e6))
            instrument = TargetedSurfaceSwab(
                rng=np.random.default_rng(int(rng.integers(1, 1e6))),
            )
            result = instrument.swab_surface(ZONE, copies, area)
            cap = copies * SWAB_AREA_CM2 / area if area > 0 else 0.0
            assert result["sampled_copies"] <= cap * 1.001
            assert result["recovered_copies"] <= result["sampled_copies"] * 1.05
            for value in _numeric_fields(result):
                assert math.isfinite(value)
                assert value >= 0.0

    def test_legacy_aliases_present(self) -> None:
        result = _swab(seed=5).swab_surface(ZONE, 1e8, AREA_CM2)
        assert result["recovered_mass"] == result["recovered_copies"]
        assert result["surface_mass"] == result["surface_copies_total"]


class TestZoneBatch:
    def test_surface_zones_filters_targets_and_carries_classes(self) -> None:
        instrument = _swab(seed=5)
        results = instrument.swab_surface_zones(
            {"Galley_M": 1e9, "Head_1": 1e9, "Pool": 1e9},
            {"Galley_M": AREA_CM2, "Head_1": 5.0e4, "Pool": AREA_CM2},
            target_zones=["Head_1"],
            surface_classes={"Head_1": "toilet_seat"},
            copies_by_pathogen={"norwalk_gi": {"Head_1": 1e9}},
        )
        assert list(results) == ["Head_1"]
        row = results["Head_1"]
        assert row["surface_class"] == "toilet_seat"
        assert row["copies_by_pathogen"] == {"norwalk_gi": 1e9}
        assert row["lod_copies_per_swab"] == SWAB_LOD_COPIES_BY_SURFACE["toilet_seat"]


def _obs_mock() -> MagicMock:
    obs = MagicMock()
    obs.turnaround = None
    obs.lab_notebook_enabled = False
    obs.air_sniffer.sample_all_zones.return_value = {}
    obs.surface_swab.swab_zones.return_value = {}
    obs.surface_swab.swab_surface_zones.return_value = {}
    obs.wastewater_seq.sample_all_zones.return_value = {}
    return obs


def _core_with_pool() -> TransmissionCore:
    cabin = f"Corridor_A{CABIN_COMPARTMENT_SEPARATOR}1"
    zone_types = {
        "Galley_M": "Dining",
        "Head_1": "Sanitary",
        "Corridor_A": "Cabin_Corridor",
    }
    core = TransmissionCore(
        rng=np.random.default_rng(9),
        zone_volumes={"Galley_M": 80.0, "Head_1": 3.0, "Corridor_A": 60.0},
        pathogen_profiles={"norwalk_gi": {}},
        zone_types=zone_types,
        zone_floor_areas={"Galley_M": 40.0, "Head_1": 8.0, "Corridor_A": 30.0},
    )
    core.initialize_zones(["Galley_M", "Head_1", "Corridor_A"])
    core.surface_pools["Galley_M"] = 5.0e4
    core.surface_pools["Head_1"] = 2.0e4
    core.surface_pools[cabin] = 7.0e3
    core.surface_pools_by_pathogen["norwalk_gi"] = {
        "Galley_M": 5.0e4, "Head_1": 2.0e4, cabin: 7.0e3,
    }
    return core


class TestOrchestratorSourceWiring:
    def _run(self, cfg: dict, obs: MagicMock) -> dict:
        from orchestrator_epoch import ZoneContext, run_observation_sampling

        core = _core_with_pool()
        engine = MagicMock()
        engine.get_pathogen_zone_mass.return_value = {}
        swab = run_observation_sampling(
            epoch=1,
            obs=obs,
            agents=[],
            spaces={"Galley_M": {"pathogen_mass": 1.0}},
            zones=ZoneContext(
                zone_names=["Galley_M", "Head_1", "Corridor_A"],
                zone_volumes={
                    "Galley_M": 80.0, "Head_1": 3.0, "Corridor_A": 60.0,
                },
                zone_microflora_shifts={},
                high_traffic=["Galley_M", "Head_1"],
            ),
            trigger_status="LOCKDOWN",
            syn_result={"sick_call_agents": []},
            engine=engine,
            pathogen_profiles={"norwalk_gi": {}},
            cfg=cfg,
            tx_core=core,
        ).swab
        return core, swab

    def test_default_mode_uses_surface_pool_density(self) -> None:
        obs = _obs_mock()
        self._run({"observation": {"enabled": True}}, obs)
        obs.surface_swab.swab_surface_zones.assert_called_once()
        obs.surface_swab.swab_zones.assert_not_called()

    def test_legacy_mode_uses_airborne_fraction(self) -> None:
        obs = _obs_mock()
        self._run(
            {
                "observation": {
                    "enabled": True,
                    "surface_swab_source": "airborne_fraction",
                },
            },
            obs,
        )
        obs.surface_swab.swab_zones.assert_called_once()
        obs.surface_swab.swab_surface_zones.assert_not_called()
        # Legacy feed: surface input = 0.4 x airborne pool.
        zone_surface = obs.surface_swab.swab_zones.call_args.args[0]
        assert zone_surface["Galley_M"] == pytest.approx(0.4)

    def test_repaired_mode_reads_surface_pool(self) -> None:
        obs = _obs_mock()
        core, _ = self._run(
            {
                "observation": {
                    "enabled": True,
                    "surface_swab_source": "surface_pool_density",
                },
            },
            obs,
        )
        obs.surface_swab.swab_surface_zones.assert_called_once()
        obs.surface_swab.swab_zones.assert_not_called()
        args = obs.surface_swab.swab_surface_zones.call_args
        zone_copies = args.args[0]
        assert zone_copies["Galley_M"] == pytest.approx(5.0e4)
        assert zone_copies["Head_1"] == pytest.approx(2.0e4)
        areas = args.args[1]
        assert areas["Galley_M"] == pytest.approx(
            core.zone_high_touch_area_cm2("Galley_M")
        )
        assert areas["Head_1"] == pytest.approx(
            core.zone_high_touch_area_cm2("Head_1")
        )
        classes = args.kwargs["surface_classes"]
        assert classes["Head_1"] == "toilet_seat"
        assert classes["Galley_M"] == "nonporous_hard"

    def test_compartment_deposit_pools_into_the_corridor_block(self) -> None:
        obs = _obs_mock()
        self._run(
            {
                "observation": {
                    "enabled": True,
                    "surface_swab_source": "surface_pool_density",
                },
            },
            obs,
        )
        args = obs.surface_swab.swab_surface_zones.call_args
        zone_copies = args.args[0]
        # The cabin-compartment deposit (7.0e3) rolls up into its parent
        # block's total — a stateroom emesis event is swabbable.
        assert zone_copies["Corridor_A"] == pytest.approx(7.0e3)
        by_pid = args.kwargs["copies_by_pathogen"]
        assert by_pid["norwalk_gi"]["Corridor_A"] == pytest.approx(7.0e3)
