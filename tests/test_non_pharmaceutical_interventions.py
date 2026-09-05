"""Tests for the formal_spec_v2 3.7 NPI dose-reduction interface.

Behaviour under test, in the order the interface is used: what a config
block resolves to, what it refuses, what a host ends up carrying, and what
the transmission core does to a dose because of it.
"""
from __future__ import annotations

import numpy as np
import pytest

from engines.infection_dynamics_bridge import KorkinAgent
from engines.non_pharmaceutical_interventions import (
    NPI_ROUTE_KEYS,
    NpiMeasure,
    assign_host_npi,
    effective_multiplier,
    resolve_npi,
)
from engines.transmission_core import (
    DEFAULT_ROUTE_EFFICIENCY,
    PATHWAY_EFFICIENCY_KEYS,
    TransmissionCore,
)

REL = 1e-12


def _measure_block(
    *,
    multipliers: dict[str, float] | None = None,
    coverage: dict[str, float] | None = None,
    compliance: float | None = None,
) -> dict[str, object]:
    block: dict[str, object] = {
        "source": "test fixture, not a sourced magnitude",
        "coverage_by_role": (
            {"passenger": 1.0, "crew": 1.0} if coverage is None else coverage
        ),
        "reference_multipliers": (
            {"fomite": 0.5} if multipliers is None else multipliers
        ),
    }
    if compliance is not None:
        block["compliance"] = compliance
    return block


def _cfg(**measures: dict[str, object]) -> dict[str, object]:
    return {"non_pharmaceutical_interventions": dict(measures)}


def _agent(role: str = "passenger", agent_id: int = 1) -> KorkinAgent:
    return KorkinAgent(
        agent_id=agent_id,
        role=role,
        immune=False,
        home_zone="cabin",
        dining_zone="dining",
        work_zone="public",
        free_zone="public",
        schedule=["cabin"],
    )


# ── The route vocabulary is the engine's, not a parallel one ─────────────

def test_route_keys_are_exactly_the_engine_efficiency_keys() -> None:
    assert NPI_ROUTE_KEYS == frozenset(DEFAULT_ROUTE_EFFICIENCY)


def test_route_keys_cover_every_pathway_the_engine_attributes_dose_to() -> None:
    assert set(PATHWAY_EFFICIENCY_KEYS.values()) <= NPI_ROUTE_KEYS


# ── Resolution: absent means absent ─────────────────────────────────────

def test_no_block_resolves_to_no_measures() -> None:
    assert resolve_npi({}) == {}
    assert resolve_npi(None) == {}


def test_declared_measure_keeps_its_name_and_source() -> None:
    measures = resolve_npi(_cfg(buffet_prompt=_measure_block()))
    assert set(measures) == {"buffet_prompt"}
    assert measures["buffet_prompt"].source


def test_a_measure_without_a_source_is_refused() -> None:
    block = _measure_block()
    del block["source"]
    with pytest.raises(ValueError, match="source is required"):
        resolve_npi(_cfg(buffet_prompt=block))


def test_an_unknown_route_is_refused_rather_than_silently_inert() -> None:
    block = _measure_block(multipliers={"fomites": 0.5})
    with pytest.raises(ValueError, match="unknown routes"):
        resolve_npi(_cfg(buffet_prompt=block))


@pytest.mark.parametrize("bad", [-0.1, 1.5, float("nan"), float("inf")])
def test_a_multiplier_outside_the_unit_interval_is_refused(bad: float) -> None:
    with pytest.raises(ValueError, match="surviving fraction"):
        resolve_npi(_cfg(m=_measure_block(multipliers={"fomite": bad})))


@pytest.mark.parametrize("bad", [-0.1, 1.5, float("nan")])
def test_a_coverage_outside_the_unit_interval_is_refused(bad: float) -> None:
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        resolve_npi(_cfg(m=_measure_block(coverage={"passenger": bad})))


@pytest.mark.parametrize("bad", [-0.1, 1.5, float("nan")])
def test_a_compliance_outside_the_unit_interval_is_refused(bad: float) -> None:
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        resolve_npi(_cfg(m=_measure_block(compliance=bad)))


def test_an_empty_coverage_map_is_refused() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        resolve_npi(_cfg(m=_measure_block(coverage={})))


def test_an_empty_multiplier_map_is_refused() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        resolve_npi(_cfg(m=_measure_block(multipliers={})))


def test_a_non_mapping_block_is_refused() -> None:
    with pytest.raises(ValueError, match="must be a mapping"):
        resolve_npi({"non_pharmaceutical_interventions": {"m": 0.5}})


# ── Compliance interpolation ────────────────────────────────────────────

def test_full_compliance_gives_the_reference_efficacy() -> None:
    assert effective_multiplier(0.3, 1.0) == pytest.approx(0.3, rel=REL)


def test_zero_compliance_gives_identity() -> None:
    assert effective_multiplier(0.3, 0.0) == pytest.approx(1.0, rel=REL)


@pytest.mark.parametrize(
    ("compliance", "expected"),
    [(0.0, 1.0), (0.25, 0.825), (0.5, 0.65), (0.75, 0.475), (1.0, 0.3)],
)
def test_compliance_moves_the_multiplier_monotonically(
    compliance: float, expected: float,
) -> None:
    assert effective_multiplier(0.3, compliance) == pytest.approx(
        expected, rel=1e-9,
    )


def test_compliance_is_graded_and_ordered_across_five_values() -> None:
    values = [
        resolve_npi(
            _cfg(m=_measure_block(multipliers={"fomite": 0.2}, compliance=c)),
        )["m"].route_multipliers()["fomite"]
        for c in (0.0, 0.2, 0.5, 0.8, 1.0)
    ]
    assert values == sorted(values, reverse=True)
    assert values[0] - values[-1] == pytest.approx(0.8, rel=1e-9)


# ── Host assignment ─────────────────────────────────────────────────────

def test_a_host_with_no_measures_carries_no_multipliers() -> None:
    agent = _agent()
    assign_host_npi([agent], {}, np.random.default_rng(0))
    assert agent.dose_reduction_multipliers == {}
    assert agent.npi_measures == ()


def test_full_coverage_reaches_every_host_of_that_role() -> None:
    agents = [_agent(agent_id=i) for i in range(20)]
    measures = resolve_npi(_cfg(m=_measure_block(coverage={"passenger": 1.0})))
    assign_host_npi(agents, measures, np.random.default_rng(0))
    assert all(a.npi_measures == ("m",) for a in agents)


def test_zero_coverage_reaches_nobody_and_consumes_no_draw() -> None:
    agents = [_agent(agent_id=i) for i in range(20)]
    measures = resolve_npi(_cfg(m=_measure_block(coverage={"passenger": 0.0})))
    rng = np.random.default_rng(0)
    assign_host_npi(agents, measures, rng)
    assert all(a.npi_measures == () for a in agents)
    assert rng.random() == np.random.default_rng(0).random()


def test_a_role_absent_from_the_coverage_map_is_uncovered() -> None:
    crew = _agent(role="crew", agent_id=2)
    measures = resolve_npi(_cfg(m=_measure_block(coverage={"passenger": 1.0})))
    assign_host_npi([crew], measures, np.random.default_rng(0))
    assert crew.npi_measures == ()


def test_partial_coverage_reaches_some_hosts_and_not_others() -> None:
    agents = [_agent(agent_id=i) for i in range(200)]
    measures = resolve_npi(_cfg(m=_measure_block(coverage={"passenger": 0.5})))
    assign_host_npi(agents, measures, np.random.default_rng(11))
    reached = sum(1 for a in agents if a.npi_measures)
    assert 0 < reached < len(agents)


@pytest.mark.parametrize("coverage", [0.1, 0.4, 0.7, 0.95])
def test_reached_share_tracks_declared_coverage(coverage: float) -> None:
    agents = [_agent(agent_id=i) for i in range(400)]
    measures = resolve_npi(
        _cfg(m=_measure_block(coverage={"passenger": coverage})),
    )
    assign_host_npi(agents, measures, np.random.default_rng(7))
    share = sum(1 for a in agents if a.npi_measures) / len(agents)
    assert share == pytest.approx(coverage, abs=0.08)


def test_two_measures_on_one_route_compose_multiplicatively() -> None:
    measures = resolve_npi(
        _cfg(
            a=_measure_block(multipliers={"fomite": 0.5}),
            b=_measure_block(multipliers={"fomite": 0.4}),
        ),
    )
    agent = _agent()
    assign_host_npi([agent], measures, np.random.default_rng(0))
    assert agent.npi_measures == ("a", "b")
    assert agent.dose_reduction_multipliers["fomite"] == pytest.approx(
        0.2, rel=1e-9,
    )


def test_a_route_no_measure_names_is_unreduced() -> None:
    agent = _agent()
    measures = resolve_npi(_cfg(m=_measure_block(multipliers={"fomite": 0.5})))
    assign_host_npi([agent], measures, np.random.default_rng(0))
    assert "droplet" not in agent.dose_reduction_multipliers
    assert agent.dose_reduction_multipliers["fomite"] == pytest.approx(0.5)
    doses = {agent.agent_id: 100.0}
    TransmissionCore._apply_npi_dose_reduction(
        {agent.agent_id: agent.dose_reduction_multipliers},
        doses,
        {agent.agent_id: {"droplet": 100.0}},
    )
    assert doses[agent.agent_id] == pytest.approx(100.0, rel=REL)


# ── What the engine does with it ────────────────────────────────────────

def test_no_host_state_leaves_every_dose_untouched() -> None:
    doses = {1: 100.0}
    pathways = {1: {"fomite": 60.0, "droplet": 40.0}}
    TransmissionCore._apply_npi_dose_reduction({}, doses, pathways)
    assert doses == {1: 100.0}
    assert pathways == {1: {"fomite": 60.0, "droplet": 40.0}}


def test_reduction_hits_the_named_route_only() -> None:
    doses = {1: 100.0}
    pathways = {1: {"fomite": 60.0, "droplet": 40.0}}
    TransmissionCore._apply_npi_dose_reduction(
        {1: {"fomite": 0.25}}, doses, pathways,
    )
    assert pathways[1]["fomite"] == pytest.approx(15.0, rel=REL)
    assert pathways[1]["droplet"] == pytest.approx(40.0, rel=REL)


def test_the_aggregate_dose_is_the_sum_of_the_reduced_routes() -> None:
    doses = {1: 100.0}
    pathways = {1: {"fomite": 60.0, "droplet": 40.0}}
    TransmissionCore._apply_npi_dose_reduction(
        {1: {"fomite": 0.25, "droplet": 0.5}}, doses, pathways,
    )
    assert doses[1] == pytest.approx(sum(pathways[1].values()), rel=REL)
    assert doses[1] == pytest.approx(35.0, rel=REL)


def test_one_host_s_measures_do_not_touch_another_host() -> None:
    doses = {1: 100.0, 2: 100.0}
    pathways = {1: {"fomite": 100.0}, 2: {"fomite": 100.0}}
    TransmissionCore._apply_npi_dose_reduction(
        {1: {"fomite": 0.1}}, doses, pathways,
    )
    assert doses[1] == pytest.approx(10.0, rel=REL)
    assert doses[2] == pytest.approx(100.0, rel=REL)


def test_the_engine_maps_pathway_names_onto_route_keys() -> None:
    doses = {1: 0.0}
    pathways = {1: {"food": 100.0, "environmental": 100.0}}
    TransmissionCore._apply_npi_dose_reduction(
        {1: {"food_contamination": 0.5, "environmental_source": 0.25}},
        doses,
        pathways,
    )
    assert pathways[1]["food"] == pytest.approx(50.0, rel=REL)
    assert pathways[1]["environmental"] == pytest.approx(25.0, rel=REL)


@pytest.mark.parametrize("multiplier", [0.0, 0.25, 0.5, 0.75, 1.0])
def test_dose_is_graded_and_monotone_in_the_multiplier(
    multiplier: float,
) -> None:
    doses = {1: 100.0}
    pathways = {1: {"fomite": 100.0}}
    TransmissionCore._apply_npi_dose_reduction(
        {1: {"fomite": multiplier}}, doses, pathways,
    )
    assert doses[1] == pytest.approx(100.0 * multiplier, rel=REL)


def test_a_zero_multiplier_blocks_the_route_entirely() -> None:
    doses = {1: 100.0}
    pathways = {1: {"fomite": 100.0, "droplet": 5.0}}
    TransmissionCore._apply_npi_dose_reduction(
        {1: {"fomite": 0.0}}, doses, pathways,
    )
    assert pathways[1]["fomite"] == pytest.approx(0.0, abs=0.0)
    assert doses[1] == pytest.approx(5.0, rel=REL)


def test_reduced_doses_stay_finite_and_non_negative() -> None:
    doses = {1: 1e12}
    pathways = {1: {"fomite": 1e12, "droplet": 0.0}}
    TransmissionCore._apply_npi_dose_reduction(
        {1: {"fomite": 0.3, "droplet": 0.3}}, doses, pathways,
    )
    assert np.isfinite(doses[1])
    assert doses[1] >= 0.0
    assert all(np.isfinite(v) for v in pathways[1].values())
    assert all(v >= 0.0 for v in pathways[1].values())


def test_npi_and_route_efficiency_multiply_and_neither_absorbs_the_other() -> None:
    core = TransmissionCore.__new__(TransmissionCore)
    profile = {"route_efficiency_multipliers": {"fomite": 0.5}}
    doses = {1: 100.0}
    pathways = {1: {"fomite": 100.0}}
    core._apply_route_efficiencies(profile, doses, pathways)
    assert doses[1] == pytest.approx(50.0, rel=REL)
    TransmissionCore._apply_npi_dose_reduction(
        {1: {"fomite": 0.4}}, doses, pathways,
    )
    assert doses[1] == pytest.approx(20.0, rel=REL)


def test_route_efficiency_is_unchanged_by_a_declared_measure() -> None:
    core = TransmissionCore.__new__(TransmissionCore)
    profile = {"route_efficiency_multipliers": {"fomite": 0.5}}
    before = dict(core._route_efficiencies(profile))
    resolve_npi(_cfg(m=_measure_block(multipliers={"fomite": 0.1})))
    assert core._route_efficiencies(profile) == before


def test_the_engine_collects_only_hosts_that_carry_multipliers() -> None:
    reached, untouched = _agent(agent_id=1), _agent(agent_id=2)
    measures = resolve_npi(_cfg(m=_measure_block(coverage={"passenger": 1.0})))
    assign_host_npi([reached], measures, np.random.default_rng(0))
    collected = TransmissionCore._npi_route_multipliers([reached, untouched])
    assert set(collected) == {reached.agent_id}


# ── Attribution follows the dose ────────────────────────────────────────

def test_strain_pathway_weights_fold_in_the_host_s_multipliers() -> None:
    weights = {"fomite": 0.5, "droplet": 1.0}
    folded = TransmissionCore._host_pathway_weights(weights, {"fomite": 0.4})
    assert folded["fomite"] == pytest.approx(0.2, rel=REL)
    assert folded["droplet"] == pytest.approx(1.0, rel=REL)


def test_strain_pathway_weights_are_untouched_without_measures() -> None:
    weights = {"fomite": 0.5}
    assert TransmissionCore._host_pathway_weights(weights, None) is weights
    assert TransmissionCore._host_pathway_weights(weights, {}) is weights


# ── No magnitude ships ──────────────────────────────────────────────────

def test_the_module_ships_no_default_measure() -> None:
    assert resolve_npi({"non_pharmaceutical_interventions": {}}) == {}


def test_a_measure_cannot_increase_exposure() -> None:
    with pytest.raises(ValueError):
        NpiMeasure.from_config(
            "m", _measure_block(multipliers={"fomite": 1.2}),
        )
