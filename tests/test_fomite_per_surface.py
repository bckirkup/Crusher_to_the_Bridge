"""Behavioral guards for the per-item-class fomite arm (NORO-FOMITE-DISAGG-01).

The arm is default-off: the shipped ``pooled`` path must be bit-identical
whether the selector is absent or explicitly ``pooled``, and the arm's
``areal`` touch share over the ``shipped`` area basis must reproduce the
pooled arithmetic to floating-point tolerance with zero extra RNG draws.
Sensitivity-first per ci-test-design: graded responses on the item tables
and coverage, invariants on conservation and roll-up, config refusals --
no hash goldens.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import engines.fomite_surfaces as fomite_surfaces  # noqa: E402
import engines.transmission_core as transmission_core  # noqa: E402
from engines.infection_dynamics_bridge import (  # noqa: E402
    IllnessStatus,
    KorkinAgent,
)
from engines.sim_clock import HOURS, SimClock  # noqa: E402
from engines.transmission_core import (  # noqa: E402
    ContactTracingMatrix,
    TransmissionCore,
)
from tools.noro_diag import high_touch_area_envelope as htae  # noqa: E402

PATHOGEN = "test_pathogen"
POOLED: dict = {}
PER_SURFACE: dict = {"fomite_representation": "per_surface"}

ZONES = {
    "Cabin_A": "Cabin_Corridor",
    "Diner_A": "Dining",
    "Lounge_A": "Free",
    "Galley_M": "Free",
    "CrewMess_A": "Free",
    "Head_A": "Sanitary",
}

SANITARY_ZONES = {
    "TheaterLng": "Free",
    "PC_D5_P_F": "Cabin_Corridor",
    "HD_5T_M": "Sanitary",
    "HD_5T_F": "Sanitary",
}
SANITARY_FLOORS = {
    "HD_5T_M": 3 * transmission_core.SANITARY_FLOOR_AREA_M2_PER_WC,
    "HD_5T_F": 3 * transmission_core.SANITARY_FLOOR_AREA_M2_PER_WC,
}
SANITARY_MAP = {"TheaterLng": {"male": "HD_5T_M", "female": "HD_5T_F"}}

EPOCHS = 6


def _profile() -> dict:
    return {
        "shedding_curve_log10": [11.0] * 12,
        "asymptomatic_shedding_log10": [11.0] * 12,
        "symptom_onset_day": 0.0,
        "dose_response": {"model": "exponential", "k": 0.01},
        "hand_inactivation_rate_per_hour": 0.61,
        "hand_hygiene_rate_per_hour": 0.0,
    }


def _core(tx: dict, seed: int = 11) -> TransmissionCore:
    """A core spanning every zone class; Head_A declares two water closets."""
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes=dict.fromkeys(ZONES, 50.0),
        pathogen_profiles={PATHOGEN: _profile()},
        zone_types=dict(ZONES),
        zone_floor_areas={
            "Head_A": 2 * transmission_core.SANITARY_FLOOR_AREA_M2_PER_WC,
        },
        clock=SimClock(epoch_duration_hours=1.0, mode=HOURS),
        cfg={"transmission": tx},
    )
    core.initialize_zones(list(ZONES))
    return core


def _sanitary_core(tx: dict, seed: int = 11) -> TransmissionCore:
    merged = {"sanitary_visit_mode": "dwell_weighted", **tx}
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes=dict.fromkeys(SANITARY_ZONES, 50.0),
        pathogen_profiles={PATHOGEN: _profile()},
        zone_types=dict(SANITARY_ZONES),
        zone_floor_areas=dict(SANITARY_FLOORS),
        sanitary_zone_map=dict(SANITARY_MAP),
        clock=SimClock(epoch_duration_hours=1.0, mode=HOURS),
        cfg={"transmission": merged},
    )
    core.initialize_zones(list(SANITARY_ZONES))
    return core


def _agent(
    agent_id: int,
    zone: str,
    *,
    infected: bool = False,
    gender: str = "male",
) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=agent_id,
        role="passenger",
        immune=False,
        home_zone=zone,
        dining_zone=zone,
        work_zone=zone,
        free_zone=zone,
        schedule=["Free"] * 24,
        gender=gender,
    )
    agent.current_location = zone
    if infected:
        agent.infect_with_pathogen(PATHOGEN, 1.0, 0, time_infected=24)
        agent.infections[PATHOGEN]["illness"] = IllnessStatus.SYMPTOMATIC
    return agent


def _population() -> dict[str, list[KorkinAgent]]:
    """Two agents per zone, one shedding and one susceptible, same ids."""
    occupants: dict[str, list[KorkinAgent]] = {}
    for index, zone in enumerate(ZONES):
        shedder = _agent(10 * index, zone, infected=True)
        shedder.hand_load_by_pathogen[PATHOGEN] = 1e6
        susceptible = _agent(10 * index + 1, zone)
        occupants[zone] = [shedder, susceptible]
    return occupants


def _sanitary_population() -> dict[str, list[KorkinAgent]]:
    occupants: dict[str, list[KorkinAgent]] = {}
    visitors = []
    for i in range(1, 13):
        agent = _agent(
            i, "TheaterLng", gender=("female" if i % 2 else "male"),
        )
        # Home is the cabin block, so lounge visits resolve to the shared
        # heads in ``sanitary_zone_map`` instead of own fittings.
        agent.home_zone = "PC_D5_P_F"
        visitors.append(agent)
    occupants["TheaterLng"] = visitors
    for zone in ("PC_D5_P_F", "HD_5T_M", "HD_5T_F"):
        occupants[zone] = []
    return occupants


def _drive(
    core: TransmissionCore,
    zone_occupants: dict[str, list[KorkinAgent]],
    epochs: int = EPOCHS,
) -> list[dict]:
    """Run the fomite pathway plus surface decay/cleaning per epoch."""
    history = []
    for epoch in range(epochs):
        doses: dict[int, float] = {}
        matrix = ContactTracingMatrix(epoch=epoch)
        core._pathway_fomite(
            epoch,
            zone_occupants,
            doses,
            matrix,
            [],
            pathogen_id=PATHOGEN,
            profile=core.pathogen_profiles[PATHOGEN],
        )
        core._update_surface_pools(zone_occupants)
        core._update_prev_occupancy(zone_occupants)
        history.append(
            {
                "doses": dict(doses),
                "pools": {
                    zone: pools.get(zone)
                    for pools in core.surface_pools_by_pathogen.values()
                    for zone in pools
                },
                "cleanable": {
                    zone: pools.get(zone)
                    for pools in core.surface_pools_cleanable_by_pathogen.values()
                    for zone in pools
                },
                "areas": {
                    zone: core.zone_high_touch_area_cm2(zone)
                    for zone in zone_occupants
                },
                "rng": core.rng.bit_generator.state,
            }
        )
    return history


EMESIS_PROFILE = {
    **_profile(),
    "recovery_day": 5,
    "clinical_presentation": {
        "phases": [
            {
                "name": "acute",
                "dpi_min": 0,
                "dpi_max": 2,
                "features": ["vomiting"],
            }
        ],
    },
}


def _emitter(zone: str) -> KorkinAgent:
    agent = _agent(900, zone, infected=True)
    agent.infections[PATHOGEN]["onset_time_infected"] = 0
    agent.emesis_episode_schedule_by_pathogen[PATHOGEN] = [0.0]
    return agent


# ── selector identity ────────────────────────────────────────────────


def test_selector_absent_and_pooled_are_bit_identical_including_rng() -> None:
    absent = _core({}, seed=11)
    declared = _core({"fomite_representation": "pooled"}, seed=11)
    assert absent._per_surface is None
    assert declared._per_surface is None
    assert absent.fomite_representation == "pooled"
    assert declared.fomite_representation == "pooled"
    hist_absent = _drive(absent, _population())
    hist_declared = _drive(declared, _population())
    for step_a, step_b in zip(hist_absent, hist_declared):
        assert step_a == step_b
    assert absent.surface_pools_by_pathogen == declared.surface_pools_by_pathogen
    assert (
        absent.surface_pools_cleanable_by_pathogen
        == declared.surface_pools_cleanable_by_pathogen
    )


def test_identity_per_surface_areal_reproduces_pooled() -> None:
    # Cleaning cadence high enough to fire inside the six-epoch driver.
    cleaning = {"surface_cleaning": {"routine": {"events_per_day": 24.0}}}
    pooled = _core(dict(cleaning), seed=11)
    arm = _core({**cleaning, **PER_SURFACE}, seed=11)
    assert arm.fomite_representation == "per_surface"
    hist_pooled = _drive(pooled, _population())
    hist_arm = _drive(arm, _population())
    for pooled_step, arm_step in zip(hist_pooled, hist_arm):
        assert pooled_step["doses"].keys() == arm_step["doses"].keys()
        for agent_id, dose in pooled_step["doses"].items():
            assert dose == pytest.approx(arm_step["doses"][agent_id], rel=1e-9)
        for zone, mass in pooled_step["pools"].items():
            assert mass == pytest.approx(arm_step["pools"][zone], rel=1e-9)
        for zone, mass in pooled_step["cleanable"].items():
            assert mass == pytest.approx(arm_step["cleanable"][zone], rel=1e-9)
        assert pooled_step["areas"] == arm_step["areas"]
        assert pooled_step["rng"] == arm_step["rng"]  # no extra draws
    assert pooled._routine_cleaning_event_counts
    assert sum(dose for step in hist_arm for dose in step["doses"].values()) > 0.0


def test_identity_emesis_patch_area_matches_pooled() -> None:
    def _patches(core: TransmissionCore) -> list:
        agent = _emitter("Lounge_A")
        agent.clock = core.clock
        core._deposit_emesis(agent, PATHOGEN, "Lounge_A", 0, EMESIS_PROFILE)
        return core.emesis_patch_pools_by_pathogen[PATHOGEN]["Lounge_A"]

    pooled = _patches(_core(POOLED, seed=13))
    arm = _patches(_core(PER_SURFACE, seed=13))
    assert pooled
    assert len(pooled) == len(arm)
    for patch_pooled, patch_arm in zip(pooled, arm):
        assert patch_arm.high_touch_area_m2 == pytest.approx(
            patch_pooled.high_touch_area_m2, rel=1e-12,
        )
        assert patch_arm.mass == pytest.approx(patch_pooled.mass, rel=1e-12)


# ── conservation and uniformity ──────────────────────────────────────


def test_per_class_state_conserves_zone_total() -> None:
    core = _core(PER_SURFACE, seed=12)
    occupants = _population()
    for epoch in range(EPOCHS):
        doses: dict[int, float] = {}
        core._pathway_fomite(
            epoch,
            occupants,
            doses,
            ContactTracingMatrix(epoch=epoch),
            [],
            pathogen_id=PATHOGEN,
            profile=core.pathogen_profiles[PATHOGEN],
        )
        core._update_surface_pools(occupants)
        for zone, mass in core.surface_pools_by_pathogen.get(
            PATHOGEN, {},
        ).items():
            if mass <= 0.0:
                continue
            state = core.zone_item_class_state(zone, PATHOGEN)
            assert state
            assert sum(s["mass"] for s in state.values()) == pytest.approx(
                mass, rel=1e-9,
            )
            assert all(math.isfinite(s["mass"]) for s in state.values())
            assert all(s["mass"] >= 0.0 for s in state.values())
            assert all(
                math.isfinite(s["density_per_m2"]) for s in state.values()
            )
            assert all(s["density_per_m2"] >= 0.0 for s in state.values())
            shares = [s["touch_share"] for s in state.values()]
            assert sum(shares) == pytest.approx(1.0, rel=1e-12)
            assert all(0.0 <= share <= 1.0 for share in shares)
            assert sum(s["area_m2"] for s in state.values()) == pytest.approx(
                core._fomite_surface_area_pooled(zone), rel=1e-12,
            )


def test_areal_density_is_uniform_across_classes() -> None:
    core = _core(PER_SURFACE, seed=13)
    _drive(core, _population())
    for zone, mass in core.surface_pools_by_pathogen.get(PATHOGEN, {}).items():
        if mass <= 0.0:
            continue
        densities = [
            s["density_per_m2"]
            for s in core.zone_item_class_state(zone, PATHOGEN).values()
        ]
        assert densities
        for density in densities:
            assert density == pytest.approx(densities[0], rel=1e-9)


# ── graded sensitivity on the item tables ────────────────────────────


def test_class_count_perturbation_moves_that_class_density_and_rollup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    areas, shares, rollups, swab = [], [], [], []
    for count in (4, 8, 16):
        monkeypatch.setitem(
            fomite_surfaces.ZONE_ITEM_SETS["public"]["shared_fixed"],
            "door_lever",
            count,
        )
        core = _core({**PER_SURFACE, "fomite_area_basis": "derived"}, seed=17)
        core._deposit_surface_mass(PATHOGEN, "Lounge_A", 1e6)
        state = core.zone_item_class_state("Lounge_A", PATHOGEN)
        expected_total = sum(
            n * fomite_surfaces.ITEM_AREA_M2[c][0]
            for c, n in fomite_surfaces.unit_item_counts(
                "public", "shared", 1,
            ).items()
        )
        areas.append(state["door_lever"]["area_m2"])
        shares.append(state["door_lever"]["touch_share"])
        rollups.append(core._fomite_surface_area("Lounge_A"))
        swab.append(core.zone_high_touch_area_cm2("Lounge_A"))
        assert rollups[-1] == pytest.approx(expected_total, rel=1e-12)
        assert swab[-1] == pytest.approx(rollups[-1] * 1e4, rel=1e-15)
    assert areas == sorted(areas)
    assert shares == sorted(shares)
    assert rollups == sorted(rollups)
    assert swab == sorted(swab)
    assert areas[0] < areas[-1]


def test_class_area_perturbation_moves_density(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    densities, shares = [], []
    for area in (0.0008, 0.0016, 0.0032):
        monkeypatch.setitem(
            fomite_surfaces.ITEM_AREA_M2,
            "door_lever",
            (area, "qmra", "Weir 2016 aluminium fomite 15.8 cm2"),
        )
        core = _core({**PER_SURFACE, "fomite_area_basis": "derived"}, seed=17)
        core._deposit_surface_mass(PATHOGEN, "Lounge_A", 1e6)
        state = core.zone_item_class_state("Lounge_A", PATHOGEN)
        densities.append(state["door_lever"]["density_per_m2"])
        shares.append(state["door_lever"]["touch_share"])
        # density_c = share_c * M / (count * area) = M / total_area, so a
        # bigger door_lever area lowers its own density while raising its
        # mass share.
        assert state["door_lever"]["density_per_m2"] == pytest.approx(
            1e6 / core._fomite_surface_area("Lounge_A"), rel=1e-12,
        )
    assert densities == sorted(densities, reverse=True)
    assert densities[0] > densities[-1]
    assert shares == sorted(shares)


def test_derived_basis_rollup_differs_from_shipped_and_is_the_item_sum(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    derived = _core({**PER_SURFACE, "fomite_area_basis": "derived"}, seed=17)
    shipped = _core(PER_SURFACE, seed=17)
    for zone in ZONES:
        zone_class = derived._fomite_zone_class(zone)
        closets = 2 if zone == "Head_A" else 1
        expected = sum(
            n * fomite_surfaces.ITEM_AREA_M2[c][0]
            for c, n in fomite_surfaces.unit_item_counts(
                zone_class, "shared", closets,
            ).items()
        )
        assert derived._fomite_surface_area(zone) == pytest.approx(
            expected, rel=1e-12,
        )
        assert shipped._fomite_surface_area(zone) == pytest.approx(
            shipped._fomite_surface_area_pooled(zone), rel=1e-15,
        )

    single = TransmissionCore(
        rng=np.random.default_rng(17),
        zone_volumes={"Head_B": 50.0},
        pathogen_profiles={PATHOGEN: _profile()},
        zone_types={"Head_B": "Sanitary"},
        zone_floor_areas={
            "Head_B": transmission_core.SANITARY_FLOOR_AREA_M2_PER_WC,
        },
        clock=SimClock(epoch_duration_hours=1.0, mode=HOURS),
        cfg={
            "transmission": {
                **PER_SURFACE, "fomite_area_basis": "derived",
            },
        },
    )
    single.initialize_zones(["Head_B"])
    per_wc = sum(
        n * fomite_surfaces.ITEM_AREA_M2[c][0]
        for c, n in fomite_surfaces.unit_item_counts(
            "sanitary", "shared", 1,
        ).items()
    )
    assert single._fomite_surface_area("Head_B") == pytest.approx(
        per_wc, rel=1e-12,
    )
    assert derived._fomite_surface_area("Head_A") == pytest.approx(
        2 * per_wc, rel=1e-12,
    )


# ── cleaning coverage ────────────────────────────────────────────────


def test_per_class_cleaning_coverage_recovers_zone_mean() -> None:
    coverage_tx = {
        **PER_SURFACE,
        "surface_cleaning": {
            "routine_coverage_by_item_class": {"door_lever": 1.0},
        },
    }
    core = _core(coverage_tx, seed=19)
    plain = _core(PER_SURFACE, seed=19)
    core._deposit_surface_mass(PATHOGEN, "Lounge_A", 1e6)
    plain._deposit_surface_mass(PATHOGEN, "Lounge_A", 1e6)
    before = core.zone_item_class_state("Lounge_A", PATHOGEN)

    # With no per-class table the inventory's mean coverage is the zone's.
    inv = plain._per_surface.inventory("Lounge_A")
    assert inv is not None
    coverage, _ = plain._routine_cleaning_schedule("Lounge_A")
    assert inv.mean_coverage == pytest.approx(coverage, rel=0.0, abs=0.0)

    core._routine_cleaning_event("Lounge_A")
    plain._routine_cleaning_event("Lounge_A")
    after = core.zone_item_class_state("Lounge_A", PATHOGEN)
    lever_retention = (
        after["door_lever"]["mass"] / before["door_lever"]["mass"]
    )
    other_retentions = [
        after[c]["mass"] / before[c]["mass"]
        for c in after
        if c != "door_lever" and before[c]["mass"] > 0.0
    ]
    assert other_retentions
    assert all(lever_retention < r for r in other_retentions)
    total_after = core.surface_pools_by_pathogen[PATHOGEN]["Lounge_A"]
    total_before = sum(s["mass"] for s in before.values())
    total_retention = total_after / total_before
    assert lever_retention < total_retention < max(other_retentions)
    assert core._per_surface.cleanable_total(
        "Lounge_A", PATHOGEN,
    ) == pytest.approx(
        core.surface_pools_cleanable_by_pathogen[PATHOGEN]["Lounge_A"],
        rel=1e-9,
    )
    assert all(math.isfinite(s["mass"]) for s in after.values())
    assert all(s["mass"] >= 0.0 for s in after.values())


# ── config refusals and sanity checker ───────────────────────────────


def test_config_refusals() -> None:
    bad_shapes = [
        ({"fomite_representation": "blended"}, "fomite_representation"),
        ({**PER_SURFACE, "fomite_touch_share": "guess"}, "fomite_touch_share"),
        ({**PER_SURFACE, "fomite_area_basis": "x"}, "fomite_area_basis"),
        (
            {**PER_SURFACE, "fomite_touch_share_table": {"not_a_zone": {}}},
            "fomite_touch_share_table",
        ),
        (
            {
                **PER_SURFACE,
                "fomite_touch_share_table": {"cabin": {"not_an_item": 1.0}},
            },
            "fomite_touch_share_table",
        ),
        (
            {
                **PER_SURFACE,
                "fomite_touch_share_table": {
                    "cabin": {"door_lever": 0.4, "tap_set": 0.4},
                },
            },
            "fomite_touch_share_table",
        ),
        (
            {
                **PER_SURFACE,
                "fomite_touch_share_table": {"cabin": {"door_lever": -1.0}},
            },
            "fomite_touch_share_table",
        ),
        (
            {
                **PER_SURFACE,
                "surface_cleaning": {
                    "routine_coverage_by_item_class": {"door_lever": 1.5},
                },
            },
            "routine_coverage_by_item_class",
        ),
    ]
    for tx, key in bad_shapes:
        with pytest.raises(ValueError, match=key):
            _core(tx)


def test_declared_with_empty_table_falls_back_to_areal() -> None:
    declared = _core(
        {**PER_SURFACE, "fomite_touch_share": "declared"}, seed=11,
    )
    areal = _core(PER_SURFACE, seed=11)
    hist_declared = _drive(declared, _population())
    hist_areal = _drive(areal, _population())
    for step_d, step_a in zip(hist_declared, hist_areal):
        for zone, mass in step_d["pools"].items():
            assert mass == pytest.approx(step_a["pools"][zone], rel=1e-9)
        assert step_d["rng"] == step_a["rng"]


def test_sanitary_venue_pickup_runs_per_class() -> None:
    results = {}
    for label, tx in (("pooled", POOLED), ("arm", PER_SURFACE)):
        core = _sanitary_core(tx, seed=11)
        occupants = _sanitary_population()
        for venue in ("HD_5T_M", "HD_5T_F"):
            core._deposit_surface_mass(PATHOGEN, venue, 1e9)
        _drive(core, occupants)
        results[label] = (
            core.sanitary_telemetry["recipients"],
            core.sanitary_telemetry["dose_delivered"],
        )
    assert results["pooled"][0] > 0
    assert results["arm"][0] == results["pooled"][0]
    assert results["arm"][1] == pytest.approx(results["pooled"][1], rel=1e-9)


def test_sanity_checker_quiet_and_loud() -> None:
    from tools.sanity_checker import Report, _check_fomite_representation

    def errors(cfg: dict) -> list:
        report = Report()
        _check_fomite_representation(cfg, report)
        return report.errors

    assert not errors({"transmission": {}})
    assert not errors({"transmission": {"fomite_representation": "pooled"}})
    assert not errors({"transmission": PER_SURFACE})
    assert errors({"transmission": {"fomite_representation": "blended"}})
    assert errors(
        {
            "transmission": {
                **PER_SURFACE,
                "fomite_touch_share_table": {"cabin": {"door_lever": 0.5}},
            },
        },
    )


def test_envelope_tool_reexports_the_engine_tables() -> None:
    assert htae.ITEM_AREA_M2 is fomite_surfaces.ITEM_AREA_M2
    assert htae.ZONE_ITEM_SETS is fomite_surfaces.ZONE_ITEM_SETS
