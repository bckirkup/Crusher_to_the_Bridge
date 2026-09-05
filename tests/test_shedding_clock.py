"""The shedding clock is separate from the illness clock.

``recovery_day`` is the illness duration and ``shedding_duration_days`` the
infectious period; a host that has stopped being ill can still be shedding, and
it keeps emitting on the curve it presented on.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from engines.infection_dynamics_bridge import (
    IllnessStatus,
    InfectionStatus,
    KorkinAgent,
    environmental_release_log10_per_day,
)
from engines.natural_history import advance_infections
from engines.sim_clock import HOURS, SimClock
from engines.transmission_core import TransmissionCore

REPO_ROOT = Path(__file__).resolve().parent.parent
PATHOGEN = "test_pathogen"
ZONE = "Cabin_A"
ONSET_DAYS = 1.0
RECOVERY_DAYS = 3
SHEDDING_DAYS = 15.0
SYMPTOMATIC_CURVE = [11.0 - 0.1 * index for index in range(15)]
ASYMPTOMATIC_CURVE = [7.0] * 15


def _clock() -> SimClock:
    return SimClock(epoch_duration_hours=1.0, mode=HOURS)


def _profile(**overrides: Any) -> dict[str, Any]:
    profile: dict[str, Any] = {
        "recovery_day": RECOVERY_DAYS,
        "shedding_duration_days": SHEDDING_DAYS,
        "symptom_onset_day": ONSET_DAYS,
        "shedding_curve_log10": list(SYMPTOMATIC_CURVE),
        "asymptomatic_shedding_log10": list(ASYMPTOMATIC_CURVE),
        "environmental_faecal_release_log10_g_per_epoch": 0.0,
        "presymptomatic_shedding_days": 0.5,
        # eta 0 keeps an unpresented host unpresented, so the asymptomatic
        # arm is deterministic without touching the progression seam.
        "illness_probability": {"eta": 0.0, "gamma": 0.095},
        "clinical_presentation": {
            "phases": [
                {
                    "name": "acute",
                    "dpi_min": 0,
                    "dpi_max": 2,
                    "features": ["vomiting"],
                },
                {
                    "name": "resolving",
                    "dpi_min": 3,
                    "dpi_max": None,
                    "features": ["watery_diarrhea"],
                },
            ],
        },
    }
    profile.update(overrides)
    return profile


def _agent(*, presented: bool, clock: SimClock | None = None) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=1,
        role="passenger",
        immune=False,
        home_zone=ZONE,
        dining_zone=ZONE,
        work_zone=ZONE,
        free_zone=ZONE,
        schedule=["Free"] * 4,
    )
    agent.clock = clock or _clock()
    agent.current_location = ZONE
    agent.infect_with_pathogen(PATHOGEN, 1e4, 0, time_infected=0)
    infection = agent.infections[PATHOGEN]
    infection["incubation_days"] = ONSET_DAYS
    if presented:
        infection["illness"] = IllnessStatus.SYMPTOMATIC
        infection["presented"] = True
        infection["onset_time_infected"] = round(
            ONSET_DAYS * agent.clock.epochs_per_day,
        )
        agent.emesis_episode_schedule_by_pathogen[PATHOGEN] = [0.5]
        agent.emesis_episode_load_by_pathogen[PATHOGEN] = 1e6
    return agent


@dataclass(frozen=True)
class _Sample:
    days: float
    status: InfectionStatus
    illness: IllnessStatus
    shedding: float
    hand_target: float


def _run(
    agent: KorkinAgent,
    profile: dict[str, Any],
    horizon_days: float,
    *,
    seed: int = 7,
) -> list[_Sample]:
    """Step the real progression seam and sample state once per epoch."""
    rng = np.random.default_rng(seed)
    clock = agent.clock
    trace: list[_Sample] = []
    for epoch in range(round(horizon_days * clock.epochs_per_day)):
        infection = agent.infections[PATHOGEN]
        trace.append(_Sample(
            days=clock.days_elapsed(infection["time_infected"] or 0),
            status=infection["status"],
            illness=infection["illness"],
            shedding=agent.get_pathogen_shedding(PATHOGEN, profile),
            hand_target=agent.get_pathogen_hand_target(PATHOGEN, profile),
        ))
        advance_infections(
            agent, {PATHOGEN: profile}, rng, epoch=epoch,
        )
    return trace


def _first(trace: list[_Sample], predicate: Any) -> _Sample:
    matches = [sample for sample in trace if predicate(sample)]
    assert matches, "no sample satisfied the predicate"
    return matches[0]


def _clearance_day(trace: list[_Sample]) -> float:
    return _first(
        trace, lambda sample: sample.status == InfectionStatus.RECOVERED,
    ).days


class TestIllnessAndSheddingClocksSeparate:
    def test_illness_clears_while_infection_stays_open(self) -> None:
        profile = _profile()
        trace = _run(_agent(presented=True), profile, 20.0)
        epoch_days = 1.0 / _clock().epochs_per_day

        recovered = _first(
            trace, lambda sample: sample.illness == IllnessStatus.RECOVERED,
        )
        assert recovered.days >= ONSET_DAYS + RECOVERY_DAYS
        assert recovered.days < ONSET_DAYS + RECOVERY_DAYS + epoch_days
        assert recovered.status == InfectionStatus.INFECTED

    def test_shedding_spans_the_convalescent_window_then_stops(self) -> None:
        profile = _profile()
        trace = _run(_agent(presented=True), profile, 20.0)
        illness_end = ONSET_DAYS + RECOVERY_DAYS
        shedding_end = ONSET_DAYS + SHEDDING_DAYS

        convalescent = [
            sample for sample in trace
            if illness_end <= sample.days < shedding_end
        ]
        assert len(convalescent) > 200
        assert min(sample.shedding for sample in convalescent) > 0.0
        cleared = [sample for sample in trace if sample.days >= shedding_end]
        assert cleared
        assert max(sample.shedding for sample in cleared) == pytest.approx(0.0)

    def test_infection_clears_at_the_shedding_duration(self) -> None:
        profile = _profile()
        trace = _run(_agent(presented=True), profile, 20.0)
        epoch_days = 1.0 / _clock().epochs_per_day

        clearance = _clearance_day(trace)
        assert clearance >= ONSET_DAYS + SHEDDING_DAYS
        assert clearance < ONSET_DAYS + SHEDDING_DAYS + epoch_days

    def test_shedding_duration_grades_the_clearance_day(self) -> None:
        durations = [RECOVERY_DAYS, 8.0, 15.0, 25.0]
        clearances = [
            _clearance_day(_run(
                _agent(presented=True),
                _profile(shedding_duration_days=duration),
                float(duration) + 3.0,
            ))
            for duration in durations
        ]

        assert clearances == sorted(clearances)
        assert clearances[-1] - clearances[0] > 20.0
        for duration, clearance in zip(durations, clearances, strict=True):
            assert clearance == pytest.approx(
                ONSET_DAYS + float(duration), abs=0.1,
            )

    def test_absent_field_keeps_the_single_clock(self) -> None:
        # A profile that omits the field says the two clocks coincide, and must
        # clear on recovery_day exactly as it did before they were split.
        without = _profile()
        without.pop("shedding_duration_days")
        equal = _profile(shedding_duration_days=float(RECOVERY_DAYS))
        longer = _profile()

        absent_clearance = _clearance_day(
            _run(_agent(presented=True), without, 10.0),
        )
        equal_clearance = _clearance_day(
            _run(_agent(presented=True), equal, 10.0),
        )
        longer_clearance = _clearance_day(
            _run(_agent(presented=True), longer, 20.0),
        )

        assert absent_clearance == pytest.approx(
            ONSET_DAYS + RECOVERY_DAYS, abs=0.1,
        )
        assert absent_clearance == pytest.approx(equal_clearance)
        assert longer_clearance > absent_clearance

    def test_extended_illness_carries_shedding_with_it(self) -> None:
        # max() rule: a chronic host whose illness outlasts the shedding
        # duration keeps shedding until the illness ends.
        extension = 20
        agent = _agent(presented=True)
        agent.chronic_pathogen_mods[PATHOGEN] = {
            "recovery_day_extension": extension,
        }
        profile = _profile()
        trace = _run(agent, profile, 30.0)
        illness_end = ONSET_DAYS + RECOVERY_DAYS + extension

        past_the_shedding_duration = _first(
            trace, lambda sample: sample.days >= ONSET_DAYS + SHEDDING_DAYS,
        )
        assert past_the_shedding_duration.shedding > 0.0
        assert past_the_shedding_duration.illness == IllnessStatus.SYMPTOMATIC
        assert _clearance_day(trace) == pytest.approx(illness_end, abs=0.1)

    def test_host_can_still_be_infectious_at_debarkation(self) -> None:
        profile = _profile()
        voyage_days = 10.0
        trace = _run(_agent(presented=True), profile, voyage_days)

        final = trace[-1]
        assert voyage_days < ONSET_DAYS + SHEDDING_DAYS
        assert final.status == InfectionStatus.INFECTED
        assert final.shedding > 0.0


class TestCurveIsFixedAtPresentation:
    def test_presented_host_reads_the_symptomatic_tail(self) -> None:
        profile = _profile()
        clock = _clock()
        trace = _run(_agent(presented=True, clock=clock), profile, 20.0)

        emissions: list[float] = []
        for day_index in (4, 7, 10, 13):
            sample = _first(
                trace,
                lambda s, day=day_index: s.days >= ONSET_DAYS + day,
            )
            expected = clock.amount_per_epoch(
                10.0 ** SYMPTOMATIC_CURVE[day_index],
            )
            assert sample.illness == IllnessStatus.RECOVERED
            assert sample.shedding == pytest.approx(expected, rel=1e-9)
            emissions.append(sample.shedding)

        asymptomatic_level = clock.amount_per_epoch(
            10.0 ** ASYMPTOMATIC_CURVE[0],
        )
        assert min(emissions) > 100.0 * asymptomatic_level
        assert emissions == sorted(emissions, reverse=True)

    def test_unpresented_host_stays_on_the_asymptomatic_curve(self) -> None:
        profile = _profile()
        clock = _clock()
        trace = _run(_agent(presented=False, clock=clock), profile, 20.0)

        for day_index in (2, 6, 12):
            sample = _first(
                trace,
                lambda s, day=day_index: s.days >= ONSET_DAYS + day,
            )
            expected = clock.amount_per_epoch(
                10.0 ** ASYMPTOMATIC_CURVE[day_index],
            )
            assert sample.illness == IllnessStatus.NOT_ILL
            assert sample.shedding == pytest.approx(expected, rel=1e-9)

        assert _clearance_day(trace) == pytest.approx(
            ONSET_DAYS + SHEDDING_DAYS, abs=0.1,
        )

    def test_hand_target_survives_illness_clearance(self) -> None:
        profile = _profile()
        trace = _run(_agent(presented=True), profile, 20.0)
        convalescent = [
            sample for sample in trace
            if ONSET_DAYS + RECOVERY_DAYS
            <= sample.days
            < ONSET_DAYS + SHEDDING_DAYS
        ]

        assert min(sample.hand_target for sample in convalescent) > 0.0
        assert all(
            np.isfinite(sample.hand_target) for sample in convalescent
        )


def _shipped(pathogen_id: str) -> dict[str, Any]:
    path = REPO_ROOT / "data" / "pathogens" / "active_profiles.json"
    with path.open(encoding="utf-8") as handle:
        profiles = json.load(handle)["pathogens"]
    return next(
        profile for profile in profiles
        if profile["pathogen_id"] == pathogen_id
    )


class TestShippedRespiratoryArmReachesItsCurve:
    """The COVID arm's two clocks, against the profile the model ships.

    #51: the arm carried a 15-point curve and no shedding duration, so it
    cleared at ``recovery_day`` 7 and the tail was unreachable. The sourced
    interval is the upper-respiratory RNA-positivity duration, [10.8, 18.4] d.
    """

    def test_the_two_clocks_are_declared_and_differ(self) -> None:
        covid = _shipped("sars_cov2_resp")
        duration = covid["shedding_duration_days"]

        assert covid["recovery_day"] == 7
        assert duration > covid["recovery_day"]
        assert 10.8 <= duration <= 18.4
        assert duration == len(covid["shedding_curve_log10"])
        assert duration == len(covid["asymptomatic_shedding_log10"])

    @pytest.mark.parametrize("presented", [True, False])
    def test_every_authored_curve_index_is_emitted(
        self, presented: bool,
    ) -> None:
        covid = _shipped("sars_cov2_resp")
        curve_key = (
            "shedding_curve_log10" if presented
            else "asymptomatic_shedding_log10"
        )
        if not presented:
            # eta 0 holds the host off the symptomatic curve for the whole
            # course; every other field stays as shipped.
            covid["illness_probability"] = dict(
                covid["illness_probability"], eta=0.0,
            )
        clock = _clock()
        release = environmental_release_log10_per_day(covid)
        trace = _run(
            _agent(presented=presented, clock=clock),
            covid,
            float(covid["shedding_duration_days"]) + 3.0,
        )

        for index, log10_value in enumerate(covid[curve_key]):
            sample = _first(
                trace, lambda s, day=index: s.days >= ONSET_DAYS + day,
            )
            expected = clock.amount_per_epoch(
                10.0 ** (log10_value - release),
            )
            assert sample.status == InfectionStatus.INFECTED
            assert sample.shedding == pytest.approx(expected, rel=1e-9)

    def test_illness_ends_on_recovery_day_and_shedding_outlasts_it(
        self,
    ) -> None:
        covid = _shipped("sars_cov2_resp")
        illness_end = ONSET_DAYS + covid["recovery_day"]
        shedding_end = ONSET_DAYS + covid["shedding_duration_days"]
        trace = _run(_agent(presented=True), covid, shedding_end + 3.0)

        recovered = _first(
            trace, lambda sample: sample.illness == IllnessStatus.RECOVERED,
        )
        assert recovered.days == pytest.approx(illness_end, abs=0.1)
        assert recovered.status == InfectionStatus.INFECTED
        convalescent = [
            sample for sample in trace
            if illness_end <= sample.days < shedding_end
        ]
        assert min(sample.shedding for sample in convalescent) > 0.0
        assert _clearance_day(trace) == pytest.approx(shedding_end, abs=0.1)


class TestEmesisStaysIllnessLinked:
    def _core(self, profile: dict[str, Any], clock: SimClock) -> TransmissionCore:
        core = TransmissionCore(
            rng=np.random.default_rng(11),
            zone_volumes={ZONE: 50.0},
            pathogen_profiles={PATHOGEN: profile},
            zone_types={ZONE: "Cabin_Corridor"},
            clock=clock,
        )
        core.initialize_zones([ZONE])
        return core

    def test_no_emesis_after_illness_clears(self) -> None:
        profile = _profile()
        clock = _clock()
        agent = _agent(presented=True, clock=clock)
        rng = np.random.default_rng(7)
        epochs = round((ONSET_DAYS + RECOVERY_DAYS + 1.0) * clock.epochs_per_day)
        for epoch in range(epochs):
            advance_infections(
                agent, {PATHOGEN: profile}, rng, epoch=epoch,
            )

        infection = agent.infections[PATHOGEN]
        assert infection["illness"] == IllnessStatus.RECOVERED
        assert infection["status"] == InfectionStatus.INFECTED
        assert PATHOGEN not in agent.emesis_episode_schedule_by_pathogen
        assert PATHOGEN not in agent.emesis_episode_load_by_pathogen
        assert PATHOGEN not in agent.emesis_deposition_records_by_pathogen

        core = self._core(profile, clock)
        agent.emesis_episode_schedule_by_pathogen[PATHOGEN] = [0.5]
        agent.emesis_episode_load_by_pathogen[PATHOGEN] = 1e6
        core._deposit_emesis(agent, PATHOGEN, ZONE, epochs, profile)

        assert not agent.emesis_deposition_records_by_pathogen.get(PATHOGEN)
