"""ROOM-AIR-PAIRED-VALIDATION-01 blocker B2: the primary endpoint in the reader.

Stub simulations only: no voyage is stepped here. The reader is shown to
carry the whole-hull ``cumulative_ever_infected`` that the run summary
writer emits, to leave every reader that does not ask for it untouched, and
to be unable to move a transmission output. Empirical paired-voyage
neutrality is unmeasured.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

import picard_framework.covid_theta_fit as ctf
from orchestrator_record import _summary_counts
from orchestrator_types import SimulationState
from picard_framework.covid_first_look import observables_from_payload
from picard_framework.covid_theta_fit import (
    HullObservables,
    observables_from_modality,
    simulate_hull,
    voyage_end_cumulative_ever_infected,
)
from tools import room_air_ambient_exchange_attribution as attr_mod

SCENARIO = "diamond_princess_2020"
LEGACY_KEYS = {
    "scenario_id", "theta", "seed", "recorded_onsets",
    "onsets_before_split_day", "onsets_on_or_after_split_day",
    "passenger_onsets_before", "passenger_onsets_after",
    "crew_onsets_before", "crew_onsets_after", "campaign_specimens",
    "campaign_positives", "campaign_asymptomatic_positives",
    "positive_share", "asymptomatic_share",
}


class _StubSyndromic:
    def onset_observation_curve(self, pathogen_id: str) -> dict:
        return {16: {"passenger": 2, "crew": 1}, 18: {"passenger": 1}}

    def campaign_specimen_log(self, pathogen_id: str) -> list:
        return [{"positive": True, "symptomatic_at_specimen": False}]


def _summary(ever_infected: set[int]) -> dict:
    """The run-summary writer's own output for a synthetic four-host hull."""
    agents = [
        {
            "agent_id": aid,
            "agent_class": "passenger" if aid < 3 else "crew_general",
            "infection_state": "susceptible",
        }
        for aid in range(1, 5)
    ]
    engine = SimpleNamespace(
        agents=[SimpleNamespace(microflora_disruption_status=0) for _ in agents],
    )
    return _summary_counts(
        agents, engine, SimulationState(ever_infected_ids=ever_infected),
        {"sick_call_count": 0},
    )


def _stub_sim(counts: list[int], num_epochs: int | None = None) -> SimpleNamespace:
    history = [
        {"epoch": i, "summary": _summary(set(range(1, n + 1)))}
        for i, n in enumerate(counts)
    ]
    return SimpleNamespace(
        num_epochs=len(counts) if num_epochs is None else num_epochs,
        state=SimpleNamespace(simulation_history=history),
        modalities={"syndromic": _StubSyndromic()},
    )


def _read(obs_kwargs: dict | None = None) -> HullObservables:
    return observables_from_modality(
        _StubSyndromic(), scenario_id=SCENARIO, theta=1e8, seed=3,
        split_day=17, turn_day=16, **(obs_kwargs or {}),
    )


@pytest.mark.parametrize("counts", [[0], [1, 1, 2], [0, 3, 4, 4]])
def test_endpoint_is_the_last_summary_count(counts: list[int]) -> None:
    value = voyage_end_cumulative_ever_infected(_stub_sim(counts))
    assert value == counts[-1]
    assert 0 <= value <= 4


def test_endpoint_tracks_the_summary_writer() -> None:
    values = [
        voyage_end_cumulative_ever_infected(_stub_sim([n])) for n in range(5)
    ]
    assert values == sorted(values) and len(set(values)) == 5


def test_an_unfinished_run_has_no_voyage_end_endpoint() -> None:
    with pytest.raises(ValueError, match="voyage-end"):
        voyage_end_cumulative_ever_infected(_stub_sim([1, 2], num_epochs=3))


def test_simulate_hull_carries_the_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sim = _stub_sim([1, 2, 3])
    monkeypatch.setattr(ctf, "run_fit_spec", lambda raw, repo_root: sim)
    first = simulate_hull(SCENARIO, 1e8, 3, num_epochs=3)
    second = simulate_hull(SCENARIO, 1e8, 3, num_epochs=3)
    assert first.cumulative_ever_infected == 3
    assert first.as_dict()["cumulative_ever_infected"] == 3
    assert first == second
    # Every field the reader already carried is what the modality reader gave.
    legacy = first.as_dict()
    legacy.pop("cumulative_ever_infected")
    assert legacy == _read().as_dict()


def test_readers_that_do_not_ask_are_unchanged() -> None:
    obs = _read()
    assert obs.cumulative_ever_infected is None
    assert set(obs.as_dict()) == LEGACY_KEYS


@pytest.mark.parametrize("endpoint", [None, 0, 7])
def test_payload_round_trip_keeps_the_endpoint(endpoint: int | None) -> None:
    obs = HullObservables(
        **{**_read().__dict__, "cumulative_ever_infected": endpoint},
    )
    assert observables_from_payload({"observables": obs.as_dict()}) == obs


def _paired(monkeypatch: pytest.MonkeyPatch, endpoints: dict | None) -> dict:
    def fake(scenario_id, theta, seed, mode, num_epochs=None):
        value = None if endpoints is None else endpoints[mode]
        return HullObservables(
            **{**_read().__dict__, "seed": seed,
               "cumulative_ever_infected": value},
        )

    monkeypatch.setattr(attr_mod, "_simulate_hull_with_map_mode", fake)
    return attr_mod.paired_hull_runs(SCENARIO, 1e8, [7])["by_seed"]["7"]


@pytest.mark.parametrize(
    ("off", "on"), [(5, 5), (9, 4), (2, 6)],
)
def test_paired_tool_reports_the_on_minus_off_endpoint(
    monkeypatch: pytest.MonkeyPatch, off: int, on: int,
) -> None:
    pair = _paired(monkeypatch, {"ambient_off": off, "ambient_on": on})
    assert pair["ambient_off"]["cumulative_ever_infected"] == off
    assert pair["ambient_on"]["cumulative_ever_infected"] == on
    delta = pair["paired_delta_on_minus_off"]
    assert delta["cumulative_ever_infected"] == on - off
    # Identical arms (the sealed-mode expectation) give an all-zero pair.
    if off == on:
        assert set(delta.values()) == {0}


def test_paired_tool_without_the_endpoint_is_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pair = _paired(monkeypatch, None)
    for block in pair.values():
        assert "cumulative_ever_infected" not in block
