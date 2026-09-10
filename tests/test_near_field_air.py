"""The inhalation route has a near field over the cabin and the table.

Behaviour and invariant tests for AERO-NEAR-01. The far field is the zone's
well-mixed aerosol pool exactly as before; the near field breathes a declared
share ``retained_fraction`` (kappa) of a co-located partner's aerosol at the
unit's own volume, and adjacent tables are a second ring at ``neighbour_table_
ratio`` (rho). kappa 0 is the pre-change route on the same code path. No golden
numbers: every expectation is a relation between runs of the same code, a
conservation law, an ordering, or a bound.
"""
from __future__ import annotations

import numpy as np
import pytest

from engines.infection_dynamics_bridge import (
    IllnessStatus,
    InfectionStatus,
    KorkinAgent,
)
from engines.transmission_core import (
    DEFAULT_NEAR_FIELD_NEIGHBOUR_TABLE_RATIO,
    DEFAULT_NEAR_FIELD_RETAINED_FRACTION,
    ContactTracingMatrix,
    TransmissionCore,
)
from orchestrator_init import assign_dining_parties

CABIN = "PC_D6_P_F"
DINING = "MainDining"
CABIN_VOLUME = 600.0
DINING_VOLUME = 1050.0
BERTH_M3 = 10.0
SEAT_M3 = 2.0


def _agent(aid: int, loc: str, infected: bool = False) -> KorkinAgent:
    a = KorkinAgent(
        agent_id=aid, role="passenger", immune=False,
        home_zone=CABIN, dining_zone=DINING,
        work_zone="Lounge", free_zone="Lounge",
        schedule=["home"] * 24,
    )
    if infected:
        a.infection_status = InfectionStatus.INFECTED
        a.illness_status = IllnessStatus.SYMPTOMATIC
        a.time_infected = 1
    a.current_location = loc
    return a


def _near_block(
    kappa: float | None,
    rho: float = 0.0,
    berth: float | None = BERTH_M3,
    seat: float | None = SEAT_M3,
) -> dict:
    if kappa is None:
        return {}
    block: dict = {"retained_fraction": kappa, "neighbour_table_ratio": rho}
    if berth is not None:
        block["cabin_berth_volume_m3"] = berth
    if seat is not None:
        block["table_seat_volume_m3"] = seat
    return {"near_field_air": block}


def _core(kappa: float | None, rho: float = 0.0, **geometry) -> TransmissionCore:
    core = TransmissionCore(
        rng=np.random.default_rng(7),
        zone_volumes={CABIN: CABIN_VOLUME, DINING: DINING_VOLUME},
        zone_types={CABIN: "Cabin_Corridor", DINING: "Dining"},
        cfg={"transmission": _near_block(kappa, rho, **geometry)},
    )
    core.initialize_zones([CABIN, DINING])
    return core


def _run(core: TransmissionCore, agents: list[KorkinAgent], zone: str) -> list[dict]:
    matrix, _ = core.execute_transmission(
        epoch=1, agents=agents, zone_pathogen_mass={zone: 0.0},
    )
    return matrix.droplet_exposures


def _dose(rows: list[dict], target: int) -> float:
    return next(r["dose"] for r in rows if r["target_id"] == target)


def _near(rows: list[dict], target: int) -> float:
    return next(r for r in rows if r["target_id"] == target).get("near_field_dose", 0.0)


def _cabin_scene() -> list[KorkinAgent]:
    """Shedder 1 berths with 2; 3 berths alone along the same corridor."""
    shedder, mate, stranger = (
        _agent(1, CABIN, infected=True), _agent(2, CABIN), _agent(3, CABIN),
    )
    shedder.cabin_mate_ids = frozenset({2})
    mate.cabin_mate_ids = frozenset({1})
    return [shedder, mate, stranger]


def _seat(agents: list[KorkinAgent], table_size: int = 2) -> None:
    for a in agents:
        a.current_location = DINING
        a.meal_seating = 0
    assign_dining_parties(
        agents,
        [{"name": DINING, "type": "Dining", "dining_service_type": "mdr",
          "dining_table_size": table_size}],
    )


def _dining_scene() -> list[KorkinAgent]:
    """Six diners at three tables of two, dealt in id order: shedder 1 sits
    with 2 (table 0); 3 and 4 are the neighbouring table; 5 and 6 are far."""
    agents = [_agent(1, DINING, infected=True)] + [
        _agent(i, DINING) for i in range(2, 7)
    ]
    _seat(agents)
    return agents


class TestDeclaration:
    def test_defaults_are_off(self) -> None:
        assert DEFAULT_NEAR_FIELD_RETAINED_FRACTION == pytest.approx(0.0)
        assert DEFAULT_NEAR_FIELD_NEIGHBOUR_TABLE_RATIO == pytest.approx(0.0)
        near = _core(None).near_field_air
        assert not near.active
        assert near.cabin_berth_volume_m3 is None
        assert near.table_seat_volume_m3 is None

    @pytest.mark.parametrize("kappa", [0.1, 0.5, 1.0])
    def test_a_declared_share_is_read(self, kappa: float) -> None:
        near = _core(kappa, rho=0.3).near_field_air
        assert near.active
        assert near.retained_fraction == pytest.approx(kappa)
        assert near.neighbour_table_ratio == pytest.approx(0.3)

    @pytest.mark.parametrize("bad", [-0.1, 1.1, float("nan"), float("inf")])
    def test_a_share_outside_the_unit_interval_is_refused(self, bad: float) -> None:
        with pytest.raises(ValueError):
            _core(bad)
        with pytest.raises(ValueError):
            _core(0.5, rho=bad)

    @pytest.mark.parametrize("geometry", [{"berth": None}, {"seat": None}])
    def test_an_active_near_field_must_declare_both_volumes(self, geometry: dict) -> None:
        with pytest.raises(ValueError, match="declared geometry"):
            _core(0.5, **geometry)

    def test_an_off_near_field_needs_no_geometry(self) -> None:
        assert not _core(0.0, berth=None, seat=None).near_field_air.active

    @pytest.mark.parametrize("bad", [0.0, -3.0, float("nan"), float("inf")])
    def test_a_non_positive_volume_is_refused(self, bad: float) -> None:
        with pytest.raises(ValueError):
            _core(0.5, berth=bad)

    def test_a_non_mapping_block_is_refused(self) -> None:
        with pytest.raises(ValueError):
            TransmissionCore(
                rng=np.random.default_rng(1),
                cfg={"transmission": {"near_field_air": 0.5}},
            )


class TestOffIsUnchanged:
    def test_absent_zero_and_geometry_only_agree_to_the_bit(self) -> None:
        rows = [
            _run(core, _cabin_scene(), CABIN)
            for core in (_core(None), _core(0.0), _core(0.0, berth=None, seat=None))
        ]
        assert rows[0] == rows[1] == rows[2]
        assert all("near_field_dose" not in r for r in rows[0])

    def test_off_does_not_consult_the_pathogen(self) -> None:
        core = _core(None)
        assert not core._near_field_admits({"airborne_emission_mode": "continuous_fraction"})
        assert not core._near_field_admits(None)


class TestCabin:
    def test_the_cabin_mate_and_only_the_cabin_mate_takes_the_near_field(self) -> None:
        off = _run(_core(None), _cabin_scene(), CABIN)
        on = _run(_core(0.5), _cabin_scene(), CABIN)
        assert _dose(on, 2) > _dose(off, 2)
        assert _near(on, 2) > 0.0
        assert _dose(on, 3) == pytest.approx(_dose(off, 3))
        assert _near(on, 3) == pytest.approx(0.0)

    def test_the_far_field_is_still_there(self) -> None:
        off = _run(_core(None), _cabin_scene(), CABIN)
        on = _run(_core(0.5), _cabin_scene(), CABIN)
        for target in (2, 3):
            far_on = _dose(on, target) - _near(on, target)
            assert far_on == pytest.approx(_dose(off, target), abs=1e-4)
            assert far_on > 0.0

    def test_the_zone_pool_keeps_the_whole_emitted_mass(self) -> None:
        pools = []
        for core in (_core(None), _core(1.0)):
            _run(core, _cabin_scene(), CABIN)
            pools.append(core.aerosol_pools[CABIN])
        assert pools[0] == pytest.approx(pools[1])
        assert pools[0] > 0.0

    def test_the_near_field_grows_with_kappa(self) -> None:
        near = [_near(_run(_core(k), _cabin_scene(), CABIN), 2) for k in (0.2, 0.5, 1.0)]
        assert near[0] < near[1] < near[2]
        assert near[1] == pytest.approx(near[0] * 2.5, rel=1e-3)

    def test_the_near_field_shrinks_as_the_berth_grows_and_vanishes_at_the_room(self) -> None:
        room_share = CABIN_VOLUME / 2  # two berths fill the whole corridor
        near = [
            _near(_run(_core(0.5, berth=b), _cabin_scene(), CABIN), 2)
            for b in (5.0, 20.0, 80.0, room_share, 2 * room_share)
        ]
        assert near[0] > near[1] > near[2] > 0.0
        assert near[3] == pytest.approx(0.0)
        assert near[4] == pytest.approx(0.0)

    def test_the_near_field_is_the_concentration_excess_of_the_unit(self) -> None:
        """kappa=1 near-field dose / far-field dose == V_room / V_cabin - 1."""
        agents = _cabin_scene()
        rows = _run(_core(1.0), agents, CABIN)
        far = _dose(rows, 2) - _near(rows, 2)
        cabin_volume = BERTH_M3 * 2
        assert _near(rows, 2) / far == pytest.approx(CABIN_VOLUME / cabin_volume - 1, rel=1e-3)

    def test_cabin_mates_take_the_near_field_only_in_a_cabin_corridor(self) -> None:
        agents = _cabin_scene()
        for a in agents:
            a.current_location = DINING
        rows = _run(_core(0.5), agents, DINING)
        assert _near(rows, 2) == pytest.approx(0.0)

    def test_another_cabin_is_not_in_the_near_field(self) -> None:
        """A third berth's dose is unmoved by a shedder in a different cabin."""
        agents = _cabin_scene()
        agents.append(_agent(4, CABIN, infected=True))
        agents[2].cabin_mate_ids = frozenset({4})
        agents[3].cabin_mate_ids = frozenset({3})
        with_two = _run(_core(0.5), agents, CABIN)
        alone = _run(_core(0.5), _cabin_scene(), CABIN)
        # 2's near field is from 1 alone; 4 in another cabin adds only far field.
        assert _near(with_two, 2) == pytest.approx(_near(alone, 2), abs=1e-4)

    def test_direct_contact_count_is_untouched(self) -> None:
        counts = []
        for core in (_core(None), _core(1.0)):
            matrix, _ = core.execute_transmission(
                epoch=1, agents=_cabin_scene(), zone_pathogen_mass={CABIN: 0.0},
            )
            counts.append(len(matrix.shared_room_exposures))
        assert counts[0] == counts[1]


class TestTable:
    def test_tables_are_dealt_consecutive_indices(self) -> None:
        agents = _dining_scene()
        assert [a.dining_table_index for a in agents] == [0, 0, 1, 1, 2, 2]
        unseated = _agent(9, DINING)
        unseated.dining_zone = "Buffet"
        assign_dining_parties([unseated], [])
        assert unseated.dining_table_index == -1

    def test_two_rings_and_no_third(self) -> None:
        rows = _run(_core(0.5, rho=0.5), _dining_scene(), DINING)
        same, neighbour, far = _near(rows, 2), _near(rows, 3), _near(rows, 5)
        assert same > neighbour > far
        assert far == pytest.approx(0.0)
        assert _near(rows, 4) == pytest.approx(neighbour)

    def test_the_far_table_gets_the_far_field_the_room_always_had(self) -> None:
        off = _run(_core(None), _dining_scene(), DINING)
        on = _run(_core(0.5, rho=0.5), _dining_scene(), DINING)
        assert _dose(on, 5) == pytest.approx(_dose(off, 5))
        assert _dose(on, 5) > 0.0

    @pytest.mark.parametrize("rho", [0.0, 0.25, 0.5, 1.0])
    def test_the_neighbour_ring_is_rho_times_the_table(self, rho: float) -> None:
        rows = _run(_core(0.5, rho=rho), _dining_scene(), DINING)
        assert _near(rows, 3) == pytest.approx(rho * _near(rows, 2), abs=1e-4)
        assert _near(rows, 3) <= _near(rows, 2)

    def test_the_near_field_shrinks_with_a_larger_seat(self) -> None:
        near = [
            _near(_run(_core(0.5, seat=s), _dining_scene(), DINING), 2)
            for s in (1.0, 4.0, 16.0)
        ]
        assert near[0] > near[1] > near[2] > 0.0

    def test_a_table_party_out_of_its_venue_has_no_near_field(self) -> None:
        agents = _dining_scene()
        for a in agents:
            a.current_location = CABIN
        rows = _run(_core(0.5, rho=0.5), agents, CABIN)
        assert all(_near(rows, a.agent_id) == pytest.approx(0.0) for a in agents[1:])

    def test_a_neighbour_in_another_sitting_is_far_field(self) -> None:
        agents = _dining_scene()
        for a in agents[2:4]:
            a.meal_seating = 1
        rows = _run(_core(0.5, rho=1.0), agents, DINING)
        assert _near(rows, 3) == pytest.approx(0.0)
        assert _near(rows, 2) > 0.0


class TestPathogenGate:
    @pytest.fixture
    def core(self) -> TransmissionCore:
        return _core(0.5, rho=0.5)

    def test_continuous_emission_takes_the_near_field(self, core: TransmissionCore) -> None:
        assert core._near_field_admits({"airborne_emission_mode": "continuous_fraction"})
        assert core._near_field_admits({"airborne_emission_mode": "respiratory"})
        assert core._near_field_admits({})
        assert core._near_field_admits(None)

    def test_an_emesis_conditioned_arm_keeps_its_far_field(self, core: TransmissionCore) -> None:
        assert not core._near_field_admits({"airborne_emission_mode": "emesis_conditioned"})

    def test_the_gate_reaches_the_route(self) -> None:
        def rows(profile: dict) -> list[dict]:
            core = _core(0.5)
            agents = _cabin_scene()
            matrix = ContactTracingMatrix(epoch=1)
            core._pathway_droplet(
                1, {CABIN: agents}, {}, matrix, [], {},
                pathogen_id="_default", profile=profile,
            )
            return matrix.droplet_exposures

        gated = rows({"airborne_emission_mode": "emesis_conditioned"})
        open_ = rows({"airborne_emission_mode": "continuous_fraction"})
        assert _near(gated, 2) == pytest.approx(0.0)
        assert _near(open_, 2) > 0.0
        assert _dose(gated, 2) == pytest.approx(_dose(open_, 2) - _near(open_, 2), abs=1e-4)


class TestNearFieldIsADesignArm:
    """The sweep plumbing: a design carries kappa, and kappa=0 writes nothing."""

    def _spec(self, kappa: float, rho: float = 0.5) -> dict:
        from telemetry_buffer.observation_model.admissible_region import Design
        from telemetry_buffer.observation_model.bounded_screen import build_run_spec
        design = Design(
            factor_set="expedition_sensitivity",
            platform="expedition_cruise_450",
            near_field_retained_fraction=kappa,
            near_field_neighbour_table_ratio=rho,
            near_field_cabin_berth_volume_m3=BERTH_M3,
            near_field_table_seat_volume_m3=SEAT_M3,
        )
        units = [0.5] * len(design.factors)
        return build_run_spec(
            design.factors, units, seed=3, description="near_field_probe",
            **design.run_kwargs(),
        )

    def test_the_control_arm_is_the_pre_change_spec(self) -> None:
        assert "transmission" not in self._spec(0.0)["config_overrides"]

    @pytest.mark.parametrize("kappa", [0.1, 0.5, 1.0])
    def test_a_swept_arm_writes_the_near_field_and_nothing_else(self, kappa: float) -> None:
        control = self._spec(0.0)
        arm = self._spec(kappa)
        overrides = dict(arm["config_overrides"])
        assert overrides.pop("transmission") == {"near_field_air": {
            "retained_fraction": kappa,
            "neighbour_table_ratio": 0.5,
            "cabin_berth_volume_m3": BERTH_M3,
            "table_seat_volume_m3": SEAT_M3,
        }}
        assert overrides == control["config_overrides"]

    def test_distinct_arms_are_distinct_specs(self) -> None:
        arms = [repr(self._spec(k)["config_overrides"]) for k in (0.1, 0.5, 1.0)]
        assert len(set(arms)) == 3

    def test_the_gate_cli_parses_the_arm_and_the_shard_passes_it(self) -> None:
        from pathlib import Path

        from deploy.aws.bounded_design_entrypoint import _region_argv, parse_args
        args = parse_args([
            "--design", "region", "--s3-prefix", "s3://b/p/", "--shard-count", "2",
            "--near-field-retained-fraction", "0.4",
            "--near-field-neighbour-table-ratio", "0.3",
            "--near-field-cabin-berth-volume-m3", "9.5",
            "--near-field-table-seat-volume-m3", "1.5",
        ])
        argv = _region_argv(args, 0, Path("/tmp/o.json"), Path("/tmp/r.jsonl"))
        for flag, value in (
            ("--near-field-retained-fraction", "0.4"),
            ("--near-field-neighbour-table-ratio", "0.3"),
            ("--near-field-cabin-berth-volume-m3", "9.5"),
            ("--near-field-table-seat-volume-m3", "1.5"),
        ):
            assert argv[argv.index(flag) + 1] == value

    def test_an_undeclared_volume_is_not_passed(self) -> None:
        from pathlib import Path

        from deploy.aws.bounded_design_entrypoint import _region_argv, parse_args
        args = parse_args([
            "--design", "region", "--s3-prefix", "s3://b/p/", "--shard-count", "2",
        ])
        argv = _region_argv(args, 0, Path("/tmp/o.json"), Path("/tmp/r.jsonl"))
        assert "--near-field-cabin-berth-volume-m3" not in argv
        assert argv[argv.index("--near-field-retained-fraction") + 1] == "0"

    def test_the_arm_reaches_the_engine_through_the_merged_config(self) -> None:
        from picard_framework.run_spec import merge_config_overrides
        merged = merge_config_overrides(
            {"transmission": {"contact_mode": "per_partner_contact"}},
            self._spec(0.4)["config_overrides"],
        )
        assert merged["transmission"]["contact_mode"] == "per_partner_contact"
        core = TransmissionCore(
            cfg={"transmission": merged["transmission"]},
            rng=np.random.default_rng(1),
        )
        assert core.near_field_air.retained_fraction == pytest.approx(0.4)
        assert core.near_field_air.cabin_berth_volume_m3 == pytest.approx(BERTH_M3)


class TestBounds:
    @pytest.mark.parametrize("kappa,berth", [(1.0, 0.01), (1e-9, 1e6), (1.0, 1e9)])
    def test_doses_stay_finite_and_non_negative_at_the_edges(self, kappa: float, berth: float) -> None:
        rows = _run(_core(kappa, berth=berth), _cabin_scene(), CABIN)
        for r in rows:
            assert np.isfinite(r["dose"])
            assert r["dose"] >= 0.0
            assert r.get("near_field_dose", 0.0) >= 0.0
