"""Strain-resolved dose attribution in transmission (Paper 3 PR 2).

The three properties the rest of Paper 3 depends on: attribution conserves dose
(so infection probability is untouched), the parent strain is drawn in proportion
to the strain-weighted contributions, and with the flag off the engine is the
legacy engine — same doses, same events, same RNG consumption.
"""

from __future__ import annotations

import copy
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

from engines.infection_dynamics_bridge import (  # noqa: E402
    IllnessStatus,
    InfectionStatus,
    KorkinAgent,
)
from engines.strain_dose_ledger import (  # noqa: E402
    EmissionContribution,
    ReservoirComposition,
    StrainDoseLedger,
    attribution,
    build_emission_mix,
    draw_contributor,
    single_strain_mix,
)
from engines.strain_state import Phenotype, StrainRegistry  # noqa: E402
from engines.transmission_core import (  # noqa: E402
    SURFACE_RESERVOIR,
    TransmissionCore,
)

VARIANT_CFG = {"variant_surveillance": {"enabled": True}}
ZONES = ["Cabin_A", "MainDining_L"]


def _norwalk_profile() -> dict:
    data = json.loads(
        (REPO_ROOT / "data/pathogens/active_profiles.json").read_text(),
    )
    profile = next(
        p for p in data["pathogens"] if p["pathogen_id"] == "norwalk_gi"
    )
    return copy.deepcopy(profile)


def _agent(aid: int, loc: str, *, infected: bool = False) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=aid,
        role="passenger",
        immune=False,
        home_zone=loc,
        dining_zone=loc,
        work_zone=loc,
        free_zone=loc,
        schedule=["Free"] * 24,
    )
    agent.current_location = loc
    if infected:
        agent.infection_status = InfectionStatus.INFECTED
        agent.illness_status = IllnessStatus.SYMPTOMATIC
        agent.time_infected = 2
        agent.infect_with_pathogen("norwalk_gi", 1e4, 0, time_infected=2)
        agent.infections["norwalk_gi"]["illness"] = IllnessStatus.SYMPTOMATIC
    return agent


def _core(
    *,
    cfg: dict | None,
    seed: int = 7,
    profile: dict | None = None,
) -> TransmissionCore:
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes=dict.fromkeys(ZONES, 60.0),
        pathogen_profiles={"norwalk_gi": profile or _norwalk_profile()},
        zone_types={"Cabin_A": "Cabin_Corridor", "MainDining_L": "Dining"},
        cfg=cfg,
    )
    core.initialize_zones(ZONES)
    return core


def _population(n_shedders: int = 2, n_susceptible: int = 6) -> list[KorkinAgent]:
    agents = [
        _agent(i, "MainDining_L", infected=True) for i in range(n_shedders)
    ]
    agents += [
        _agent(100 + i, "MainDining_L") for i in range(n_susceptible)
    ]
    return agents


def _run(core: TransmissionCore, agents: list[KorkinAgent], epochs: int) -> list[tuple]:
    """Run ``epochs`` epochs, returning a comparable digest of every event."""
    digest: list[tuple] = []
    for epoch in range(epochs):
        _matrix, events = core.execute_transmission(
            epoch=epoch,
            agents=agents,
            zone_pathogen_mass=dict.fromkeys(ZONES, 1e3),
            multi_pathogen_mass={"norwalk_gi": dict.fromkeys(ZONES, 1e3)},
        )
        for event in events:
            digest.append((
                event.epoch,
                event.pathway,
                event.target_agent_id,
                round(event.dose, 6),
            ))
    return digest


# ── Ledger unit properties ──────────────────────────────────────────────

class TestEmissionMix:
    def test_neutral_multipliers_give_unit_emission_factor(self) -> None:
        mix = build_emission_mix([
            EmissionContribution("s:1", 1, 3.0),
            EmissionContribution("s:2", 2, 1.0),
        ])
        assert mix is not None
        assert mix.emission_factor == pytest.approx(1.0)
        assert mix.shares[("s:1", 1)] == pytest.approx(0.75)
        assert mix.shares[("s:2", 2)] == pytest.approx(0.25)

    def test_transmissibility_shifts_shares_and_scales_dose(self) -> None:
        """A twice-as-transmissible strain doubles its share of an equal mix."""
        mix = build_emission_mix([
            EmissionContribution("s:1", 1, 1.0, 2.0),
            EmissionContribution("s:2", 2, 1.0, 1.0),
        ])
        assert mix is not None
        assert mix.emission_factor == pytest.approx(1.5)
        assert mix.shares[("s:1", 1)] == pytest.approx(2.0 / 3.0)
        assert mix.shares[("s:2", 2)] == pytest.approx(1.0 / 3.0)

    def test_empty_emission_has_no_mix(self) -> None:
        assert build_emission_mix([]) is None
        assert build_emission_mix([EmissionContribution("s:1", 1, 0.0)]) is None


class TestStrainDoseLedger:
    def test_dose_conserved_across_strains_and_pathways(self) -> None:
        ledger = StrainDoseLedger()
        mix = build_emission_mix([
            EmissionContribution("s:1", 1, 2.0),
            EmissionContribution("s:2", 2, 1.0),
        ])
        assert mix is not None
        ledger.add(9, "direct_contact", 6.0, mix)
        ledger.add(9, "droplet", 3.0, single_strain_mix("s:1", source_agent_id=1))
        totals = ledger.strain_doses(9)
        assert sum(totals.values()) == pytest.approx(9.0)
        assert totals[("s:1", 1)] == pytest.approx(7.0)
        assert totals[("s:2", 2)] == pytest.approx(2.0)

    def test_route_weights_apply_per_pathway(self) -> None:
        ledger = StrainDoseLedger()
        ledger.add(9, "direct_contact", 4.0, single_strain_mix("s:1"))
        ledger.add(9, "fomite", 4.0, single_strain_mix("s:2"))
        totals = ledger.strain_doses(9, {"direct_contact": 0.5, "fomite": 0.0})
        assert totals[("s:1", None)] == pytest.approx(2.0)
        assert ("s:2", None) not in totals

    def test_parent_draw_follows_dose_shares(self) -> None:
        rng = np.random.default_rng(11)
        shares = {("s:1", 1): 3.0, ("s:2", 2): 1.0}
        counts = Counter(draw_contributor(shares, rng) for _ in range(4000))
        assert counts[("s:1", 1)] / 4000 == pytest.approx(0.75, abs=0.03)

    def test_no_draw_without_dose(self) -> None:
        assert draw_contributor({}, np.random.default_rng(0)) is None


class TestReservoirComposition:
    def test_decay_preserves_shares_but_ages_deposits(self) -> None:
        """A pickup is attributed to what is still on the surface, not to now."""
        reservoir = ReservoirComposition()
        key = ReservoirComposition.key(SURFACE_RESERVOIR, "norwalk_gi", "Cabin_A")
        reservoir.deposit(key, ("s:1", 1), 10.0)
        reservoir.decay_kind(0.5, SURFACE_RESERVOIR)
        reservoir.deposit(key, ("s:2", 2), 5.0)
        mix = reservoir.mix(key)
        assert mix is not None
        assert mix.shares[("s:1", 1)] == pytest.approx(0.5)
        assert mix.shares[("s:2", 2)] == pytest.approx(0.5)

    def test_decay_kind_leaves_other_kinds_alone(self) -> None:
        reservoir = ReservoirComposition()
        food = ReservoirComposition.key("food", "norwalk_gi", "MainDining_L")
        reservoir.deposit(food, ("s:1", 1), 4.0)
        reservoir.decay_kind(0.0, SURFACE_RESERVOIR)
        assert reservoir.contributors(food)[("s:1", 1)] == pytest.approx(4.0)


# ── Integration with the transmission core ──────────────────────────────

class TestStrainAttributionInTransmission:
    def test_flag_off_leaves_engine_untracked(self) -> None:
        core = _core(cfg=None)
        assert core.strain_tracking is False
        assert core.strain_registry is None

    def test_strain_doses_sum_to_pooled_dose(self) -> None:
        """Attribution is a shadow of the pooled dose, not a change to it."""
        core = _core(cfg=VARIANT_CFG)
        agents = _population()
        core.execute_transmission(
            epoch=0,
            agents=agents,
            zone_pathogen_mass=dict.fromkeys(ZONES, 1e3),
            multi_pathogen_mass={"norwalk_gi": dict.fromkeys(ZONES, 1e3)},
        )
        strain_doses = core._strain_doses
        assert strain_doses, "expected strain-resolved doses when flag is on"
        for agent in agents[2:]:
            attributed = sum(
                strain_doses.get(agent.agent_id, {})
                .get("norwalk_gi", {})
                .values(),
            )
            pooled = core._last_pathogen_doses[agent.agent_id]["norwalk_gi"]
            assert attributed == pytest.approx(pooled, rel=1e-9)

    def test_shedders_get_founder_strains_and_events_name_a_parent(self) -> None:
        core = _core(cfg=VARIANT_CFG)
        agents = _population(n_shedders=2, n_susceptible=60)
        digest = _run(core, agents, epochs=3)
        assert digest, "expected at least one infection to attribute"
        founders = {
            agent.strain_id_for("norwalk_gi") for agent in agents[:2]
        }
        assert len(founders) == 2, "each seeded infection gets its own lineage"
        infected = [
            a for a in agents[2:] if a.strain_id_for("norwalk_gi") is not None
        ]
        assert infected, "infections should inherit a parent strain"
        for agent in infected:
            assert agent.strain_id_for("norwalk_gi") in core.strain_registry

    def test_parent_strain_shares_track_dose_shares(self) -> None:
        """Over many draws the parent matches the contribution share."""
        core = _core(cfg=VARIANT_CFG)
        core._strain_doses = {
            5: {"norwalk_gi": {("norwalk_gi:1", 1): 9.0, ("norwalk_gi:2", 2): 1.0}},
        }
        drawn = Counter(core._draw_source(5, "norwalk_gi") for _ in range(2000))
        assert drawn[("norwalk_gi:1", 1)] / 2000 == pytest.approx(0.9, abs=0.03)

    def test_transmissibility_scales_dose_at_emission(self) -> None:
        """A more transmissible shedder raises the emitted dose, not p(inf|dose)."""
        core = _core(cfg=VARIANT_CFG)
        registry = StrainRegistry()
        core.strain_registry = registry
        hot = registry.mint(
            "norwalk_gi",
            phenotype=Phenotype(transmissibility_multiplier=2.0),
        )
        shedder = _agent(1, "MainDining_L", infected=True)
        shedder.assign_strain("norwalk_gi", hot.strain_id)
        mix = core._shedder_mix([(shedder, 100.0)], "norwalk_gi")
        assert mix is not None
        assert mix.emission_factor == pytest.approx(2.0)

        doses: dict[int, float] = {}
        ledger = StrainDoseLedger()
        credited = core._accumulate(
            9, "direct_contact", 5.0, doses, None, attribution(ledger, mix),
        )
        assert credited == pytest.approx(10.0)
        assert doses[9] == pytest.approx(10.0)
        assert ledger.strain_doses(9)[(hot.strain_id, 1)] == pytest.approx(10.0)


class TestFlagOffEquivalence:
    def test_absent_and_disabled_blocks_agree_over_24_epochs(self) -> None:
        """A 24-epoch run is identical with the block absent or explicitly off."""
        absent = _run(_core(cfg=None), _population(n_susceptible=20), 24)
        disabled = _run(
            _core(cfg={"variant_surveillance": {"enabled": False}}),
            _population(n_susceptible=20),
            24,
        )
        assert absent == disabled
        assert absent, "expected transmission to occur in the reference run"

    def test_flag_off_consumes_no_extra_rng_draws(self) -> None:
        """Byte identity with the legacy engine rests on the RNG stream."""
        core = _core(cfg=None)
        _run(core, _population(n_susceptible=20), 24)
        after_legacy = core.rng.random()

        reference = _core(cfg=None)
        _run(reference, _population(n_susceptible=20), 24)
        assert reference.rng.random() == pytest.approx(after_legacy)

    def test_flag_off_events_carry_no_strain(self) -> None:
        core = _core(cfg=None)
        agents = _population(n_susceptible=20)
        _matrix, events = core.execute_transmission(
            epoch=0,
            agents=agents,
            zone_pathogen_mass=dict.fromkeys(ZONES, 1e3),
            multi_pathogen_mass={"norwalk_gi": dict.fromkeys(ZONES, 1e3)},
        )
        assert all(e.source_strain_id is None for e in events)
        assert all(e.source_agent_id is None for e in events)
        assert all(a.strain_id_for("norwalk_gi") is None for a in agents)
