"""One draw, divided between the classes present.

Behaviour and invariant tests for CONTACT-SCALE-01: a target's contacts are
allocated over the classes in its pool as ``N_class ** (1 + phi)``, normalised,
so the number of contacts never changes and only their class composition does.
``contact_class_exponent`` is 0 by default, which is the uniform draw the model
has always made and the same code path. No golden numbers: every expectation is
a relation between runs of the same code, a conservation law, or a bound.
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
    CONTACT_CLASS_EXPONENT_BOUNDS,
    DEFAULT_CONTACT_CLASS_EXPONENT,
    TransmissionCore,
)

LOUNGE = "Lounge"


def _agent(aid: int, role: str, infected: bool = False) -> KorkinAgent:
    a = KorkinAgent(
        agent_id=aid, role=role, immune=False,
        home_zone="PC_D6", dining_zone="MainDining",
        work_zone=LOUNGE, free_zone=LOUNGE,
        schedule=["Free:Lounge"] * 24,
    )
    if infected:
        a.infection_status = InfectionStatus.INFECTED
        a.illness_status = IllnessStatus.SYMPTOMATIC
        a.time_infected = 1
    a.current_location = LOUNGE
    return a


def _core(phi: float | None, seed: int = 5) -> TransmissionCore:
    tx: dict[str, float] = {} if phi is None else {"contact_class_exponent": phi}
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes={LOUNGE: 3000.0},
        zone_types={LOUNGE: "Lounge"},
        cfg={"transmission": tx},
    )
    core.initialize_zones([LOUNGE])
    return core


def _room(n_passengers: int, n_crew: int) -> list[KorkinAgent]:
    """A room where every partner sheds, so who was met is what is recorded.

    Target 0 is a susceptible passenger; ids below 1000 are passengers and ids
    at or above 1000 are crew, so a sampled partner's class is its id band.
    """
    agents = [_agent(0, "passenger")]
    agents += [_agent(i, "passenger", infected=True) for i in range(1, n_passengers)]
    agents += [_agent(1000 + i, "crew", infected=True) for i in range(n_crew)]
    return agents


def _rows(core: TransmissionCore, agents: list[KorkinAgent], epochs: int) -> list[dict]:
    rows: list[dict] = []
    shedders = {a.agent_id for a in agents if a.is_infected}
    for epoch in range(1, epochs + 1):
        matrix, _ = core.execute_transmission(
            epoch=epoch, agents=agents,
            zone_pathogen_mass={LOUNGE: 0.0},
            quarantined_ids=set(),
        )
        rows.extend(matrix.shared_room_exposures)
        for a in agents:
            if a.agent_id not in shedders:
                a.infection_status = InfectionStatus.SUSCEPTIBLE
                a.illness_status = IllnessStatus.NOT_ILL
    return rows


def _crew_fraction(rows: list[dict], target: int) -> float:
    picked = [s for r in rows if r["target_id"] == target for s in r["source_ids"]]
    assert picked, "no partners sampled"
    return sum(1 for s in picked if s >= 1000) / len(picked)


class TestDeclaration:
    def test_default_is_the_frequency_dependent_model(self) -> None:
        assert DEFAULT_CONTACT_CLASS_EXPONENT == pytest.approx(0.0)
        assert _core(None).contact_class_exponent == pytest.approx(
            DEFAULT_CONTACT_CLASS_EXPONENT,
        )

    @pytest.mark.parametrize("phi", [-1.0, -0.25, 0.5, 1.0, 2.0])
    def test_a_declared_exponent_is_read(self, phi: float) -> None:
        assert _core(phi).contact_class_exponent == pytest.approx(phi)

    @pytest.mark.parametrize(
        "bad",
        [
            CONTACT_CLASS_EXPONENT_BOUNDS[0] - 0.1,
            CONTACT_CLASS_EXPONENT_BOUNDS[1] + 0.1,
            float("nan"),
            float("inf"),
        ],
    )
    def test_an_exponent_outside_the_declared_band_is_refused(self, bad: float) -> None:
        with pytest.raises(ValueError):
            _core(bad)


class TestDefaultIsUnchanged:
    def test_zero_takes_the_uniform_path(self) -> None:
        agents = _room(10, 10)
        assert _core(0.0)._pool_class_counts(agents, agents[0]) is None

    def test_zero_is_run_identical_to_an_absent_declaration(self) -> None:
        agents_a, agents_b = _room(8, 12), _room(8, 12)
        assert _rows(_core(None), agents_a, epochs=40) == _rows(
            _core(0.0), agents_b, epochs=40,
        )

    def test_one_class_present_is_identical_at_every_exponent(self) -> None:
        """A cabin, a crew mess: nothing to divide, so nothing changes."""
        baseline = _rows(_core(0.0), _room(14, 0), epochs=40)
        for phi in (-1.0, 0.75, 2.0):
            assert _rows(_core(phi), _room(14, 0), epochs=40) == baseline


class TestClassDirectedScaling:
    def test_the_exponent_grades_which_class_is_met(self) -> None:
        """Crew are the minority class here, so a rising exponent, which
        rewards the denser class, must direct fewer contacts at them."""
        fractions = [
            _crew_fraction(_rows(_core(phi), _room(40, 10), epochs=120), 0)
            for phi in (-1.0, 0.0, 1.0, 2.0)
        ]
        assert fractions == sorted(fractions, reverse=True)
        assert fractions[0] > fractions[-1]

    def test_a_negative_exponent_favours_the_sparse_class(self) -> None:
        under = _crew_fraction(_rows(_core(-1.0), _room(40, 10), epochs=120), 0)
        uniform = _crew_fraction(_rows(_core(0.0), _room(40, 10), epochs=120), 0)
        assert under > uniform

    def test_the_uniform_draw_is_the_class_share(self) -> None:
        rows = _rows(_core(0.0), _room(40, 10), epochs=120)
        assert _crew_fraction(rows, 0) == pytest.approx(10 / 49, abs=0.05)

    def test_every_class_present_can_still_be_met(self) -> None:
        for phi in (-1.5, 1.5):
            rows = _rows(_core(phi), _room(20, 10), epochs=200)
            fraction = _crew_fraction(rows, 0)
            assert 0.0 < fraction < 1.0


class TestInvariants:
    @pytest.mark.parametrize("phi", [-1.0, 0.0, 0.5, 2.0])
    def test_the_draw_is_who_not_how_many(self, phi: float) -> None:
        """Splitting a draw between classes never creates a contact, and
        removes one only when a class's own pool is smaller than its share."""
        rows = _rows(_core(phi), _room(40, 10), epochs=60)
        assert rows
        for r in rows:
            assert 0 <= r["n_contacts"] <= r["r0_draw"]

    @pytest.mark.parametrize("phi", [-1.0, 0.0, 0.5, 2.0])
    def test_contact_total_is_conserved_when_no_class_is_exhausted(
        self, phi: float,
    ) -> None:
        """Both classes here are far larger than any daily draw, so the
        renormalised allocation must hand back the whole draw."""
        rows = _rows(_core(phi), _room(200, 200), epochs=40)
        assert rows
        assert all(r["n_contacts"] == r["r0_draw"] for r in rows)

    @pytest.mark.parametrize("phi", [-1.0, 0.0, 0.5, 2.0])
    def test_doses_stay_finite_and_non_negative(self, phi: float) -> None:
        rows = _rows(_core(phi), _room(40, 10), epochs=60)
        assert rows
        for r in rows:
            assert np.isfinite(r["dose"])
            assert r["dose"] >= 0.0

    def test_partners_are_distinct_and_present(self) -> None:
        agents = _room(40, 10)
        present = {a.agent_id for a in agents}
        for r in _rows(_core(1.5), agents, epochs=60):
            picked = r["source_ids"]
            assert len(picked) == len(set(picked))
            assert set(picked) <= present - {r["target_id"]}

    def test_the_allocation_weights_sum_to_one(self) -> None:
        core = _core(1.7)
        weights = core._class_draw_weights({"passenger": 40, "crew": 10})
        assert sum(weights) == pytest.approx(1.0)
        assert all(w >= 0.0 for w in weights)

    def test_an_empty_pool_draws_nothing(self) -> None:
        core = _core(1.0)
        assert core._sample_partners_by_class([], {}, 5) == ([], 0)


class TestPhiIsADesignArm:
    """The sweep plumbing: a design carries phi, and phi=0 writes nothing."""

    def _spec(self, phi: float) -> dict:
        from telemetry_buffer.observation_model.admissible_region import Design
        from telemetry_buffer.observation_model.bounded_screen import (
            build_run_spec,
        )
        design = Design(
            factor_set="expedition_sensitivity",
            platform="expedition_cruise_450",
            contact_class_exponent=phi,
        )
        units = [0.5] * len(design.factors)
        return build_run_spec(
            design.factors, units, seed=3, description="phi_probe",
            **design.run_kwargs(),
        )

    def test_the_control_arm_is_the_pre_change_spec(self) -> None:
        assert "transmission" not in self._spec(0.0)["config_overrides"]

    @pytest.mark.parametrize("phi", [-1.0, 0.5, 2.0])
    def test_a_swept_arm_writes_phi_and_only_phi(self, phi: float) -> None:
        control = self._spec(0.0)
        arm = self._spec(phi)
        overrides = dict(arm["config_overrides"])
        assert overrides.pop("transmission") == {"contact_class_exponent": phi}
        assert overrides == control["config_overrides"]
        assert {k: v for k, v in arm.items() if k != "config_overrides"} == {
            k: v for k, v in control.items() if k != "config_overrides"
        }

    def test_distinct_arms_are_distinct_specs(self) -> None:
        arms = [self._spec(phi)["config_overrides"] for phi in (-1.0, 0.5, 2.0)]
        assert len({repr(a) for a in arms}) == 3

    def test_the_gate_cli_parses_phi_and_the_shard_passes_it(self) -> None:
        from pathlib import Path

        from deploy.aws.bounded_design_entrypoint import (
            _region_argv,
            parse_args,
        )
        args = parse_args([
            "--design", "region", "--s3-prefix", "s3://b/p/",
            "--shard-count", "2", "--contact-class-exponent", "1.5",
        ])
        argv = _region_argv(args, 0, Path("/tmp/o.json"), Path("/tmp/r.jsonl"))
        i = argv.index("--contact-class-exponent")
        assert argv[i + 1] == "1.5"

    def test_the_arm_reaches_the_engine_through_the_merged_config(self) -> None:
        from picard_framework.run_spec import merge_config_overrides
        merged = merge_config_overrides(
            {"transmission": {"contact_mode": "per_partner_contact"}},
            self._spec(0.5)["config_overrides"],
        )
        assert merged["transmission"]["contact_mode"] == "per_partner_contact"
        core = TransmissionCore(
            cfg={"transmission": merged["transmission"]},
            rng=np.random.default_rng(1),
        )
        assert core.contact_class_exponent == pytest.approx(0.5)
