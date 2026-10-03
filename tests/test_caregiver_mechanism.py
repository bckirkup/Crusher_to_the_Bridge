"""NORO-CAREGIVER-01: party structure, caregiver event, discovery stamp.

Behaviour and invariant tests only (graded sensitivity per
ci-test-design): the party deal fills each berthing pool under the
declared cabin-count distribution, the caregiver event doses the
responder through the standard accumulators under route ``caregiver``,
cleanup mass is netted out of the emesis patch, and the discovery stamp
converts to a syndromic sick-call entry.
"""
from __future__ import annotations

import numpy as np
import pytest

from crusher_labs.modalities.syndromic import SyndromicSurveillance
from engines.infection_dynamics_bridge import (
    IllnessStatus,
    KorkinAgent,
)
from engines.sim_clock import HOURS, SimClock
from engines.transmission_core import TransmissionCore
from orchestrator_init import (
    _party_cabin_counts,
    assign_cabin_mates,
    assign_parties,
)
from telemetry_buffer.agent_axes import (
    COMPLIANCE_COMPLIANT,
    INFECTION_INFECTED,
    PRESENTATION_SYMPTOMATIC,
)

PATHOGEN = "norwalk_gi"
ZONE = "PC_D6_P_F"


def _agent(aid: int, role: str = "passenger") -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=aid,
        role=role,
        immune=False,
        home_zone=ZONE,
        dining_zone="MainDining_L",
        work_zone="Main_Pool_Deck",
        free_zone="Main_Pool_Deck",
        schedule=["Free"] * 24,
    )
    agent.current_location = ZONE
    return agent


def _emitting(aid: int, profile: dict, rng: np.random.Generator) -> KorkinAgent:
    """One symptomatic host mid-emetic illness with a drawn schedule."""
    from engines.transmission_core import draw_emesis_schedule

    agent = _agent(aid)
    agent.infect_with_pathogen(PATHOGEN, 1.0, 0, time_infected=0)
    agent.infections[PATHOGEN]["illness"] = IllnessStatus.SYMPTOMATIC
    agent.infections[PATHOGEN]["onset_time_infected"] = 0
    agent.infections[PATHOGEN]["symptom_axes"] = {
        "vomiting": True,
        "diarrhoea": True,
    }
    draw_emesis_schedule(agent, PATHOGEN, profile, rng)
    return agent


def _profile() -> dict:
    return {
        "symptom_onset_day": 0.0,
        "recovery_day": 5,
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
        "shedding_curve_log10": [11.0] * 12,
        "asymptomatic_shedding_log10": [11.0] * 12,
        "dose_response": {"model": "exponential", "k": 0.01},
    }


def _core(
    caregiver: dict | None = None, seed: int = 7,
) -> TransmissionCore:
    cfg = {"transmission": {"caregiver": caregiver or {}}}
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes={ZONE: 50.0},
        pathogen_profiles={PATHOGEN: _profile()},
        zone_types={ZONE: "Cabin_Corridor"},
        clock=SimClock(epoch_duration_hours=1.0, mode=HOURS),
        cfg=cfg,
    )
    core.initialize_zones([ZONE])
    return core


class TestPartyDeal:
    """The booking unit spans staterooms per the declared distribution."""

    def test_every_passenger_gets_a_unique_party(self) -> None:
        zones = [{"name": ZONE, "type": "Cabin_Corridor", "cabin_size": 2}]
        agents = [_agent(aid) for aid in range(1, 21)]
        assign_cabin_mates(agents, zones)
        assign_parties(agents, {})
        ids = {a.party_id for a in agents}
        assert all(a.party_id >= 0 for a in agents)
        assert len(ids) == len({
            tuple(sorted({a.agent_id, *a.party_member_ids})) for a in agents
        })

    def test_cabin_mates_stay_in_one_party(self) -> None:
        zones = [{"name": ZONE, "type": "Cabin_Corridor", "cabin_size": 2}]
        agents = [_agent(aid) for aid in range(1, 21)]
        assign_cabin_mates(agents, zones)
        assign_parties(agents, {})
        for a in agents:
            assert a.cabin_mate_ids <= a.party_member_ids
            for mid in a.cabin_mate_ids:
                mate = next(b for b in agents if b.agent_id == mid)
                assert mate.party_id == a.party_id

    def test_crew_is_not_a_travelling_party(self) -> None:
        zones = [{"name": ZONE, "type": "Cabin_Corridor", "cabin_size": 2}]
        agents = [_agent(aid) for aid in range(1, 9)]
        agents += [_agent(aid, role="crew") for aid in range(21, 25)]
        assign_cabin_mates(agents, zones)
        assign_parties(agents, {})
        assert all(a.party_id == -1 for a in agents if a.role == "crew")
        assert all(a.party_id >= 0 for a in agents if a.role == "passenger")

    def test_multi_cabin_parties_cover_their_members(self) -> None:
        zones = [{"name": ZONE, "type": "Cabin_Corridor", "cabin_size": 2}]
        agents = [_agent(aid) for aid in range(1, 41)]
        assign_cabin_mates(agents, zones)
        graph_cfg = {
            "agent_classes": [
                {
                    "class_id": agents[0].agent_class,
                    "party_cabins_distribution": {1: 0.5, 2: 0.5},
                }
            ]
        }
        assign_parties(agents, graph_cfg)
        sizes = {
            len({a.agent_id, *a.party_member_ids}) for a in agents
        }
        assert sizes <= {2, 4}
        assert 4 in sizes

    def test_cabin_counts_are_deterministic_and_fill_the_pool(self) -> None:
        dist = {1: 0.75, 2: 0.18, 3: 0.05, 4: 0.02}
        for n in (1, 3, 17, 40, 113):
            seq = _party_cabin_counts(n, dist)
            assert seq == _party_cabin_counts(n, dist)
            assert sum(seq) == n
            assert all(1 <= s <= 4 for s in seq)


class TestCaregiverEvent:
    """One responder's cleanup: dose under route caregiver, mass removed."""

    def _scene(self, **caregiver: object) -> tuple:
        core = _core(caregiver=caregiver)
        emitter = _emitting(1, _profile(), np.random.default_rng(3))
        responder = _agent(2)
        emitter.party_id = 0
        responder.party_id = 0
        emitter.party_member_ids = frozenset({2})
        responder.party_member_ids = frozenset({1})
        core._agents_by_id = {1: emitter, 2: responder}
        return core, emitter, responder

    def test_responder_is_dosed_under_the_caregiver_route(self) -> None:
        core, emitter, responder = self._scene(
            response_probability=(1.0, 1.0),
            report_probability=(1.0, 1.0),
            steward_fallback=False,
        )
        doses: dict[int, float] = {}
        pw: dict[int, dict[str, float]] = {}
        contacted = core._caregiver_response(
            emitter, PATHOGEN, 1, 1.0e6, 7.8, doses, pw,
        )
        assert contacted > 0.0
        assert contacted <= 1.0e6
        assert doses.get(2, 0.0) == pw.get(2, {}).get("caregiver", 0.0)
        assert doses.get(2, 0.0) > 0.0
        assert emitter.caregiver_report_due_epoch == 1

    def test_steward_fallback_when_no_party_responds(self) -> None:
        core = _core(caregiver={
            "response_probability": (0.0, 0.0),
            "steward_response_probability": (1.0, 1.0),
            "report_probability": (0.0, 0.0),
        })
        emitter = _emitting(1, _profile(), np.random.default_rng(3))
        steward = _agent(9, role="crew")
        core._agents_by_id = {1: emitter, 9: steward}
        doses: dict[int, float] = {}
        pw: dict[int, dict[str, float]] = {}
        contacted = core._caregiver_response(
            emitter, PATHOGEN, 1, 1.0e6, 7.8, doses, pw,
        )
        assert contacted > 0.0
        assert core.caregiver_telemetry["steward_responses"] == 1

    def test_off_mode_is_silent(self) -> None:
        core, emitter, responder = self._scene(mode="off")
        contacted = core._caregiver_response(
            emitter, PATHOGEN, 1, 1.0e6, 7.8, {}, {},
        )
        assert contacted == pytest.approx(0.0)
        assert emitter.caregiver_report_due_epoch is None

    def test_off_mode_draws_no_rng(self) -> None:
        """Labelled baseline: the arm leaves the RNG stream untouched."""
        core, emitter, responder = self._scene(mode="off")
        state = core.rng.bit_generator.state
        core._caregiver_response(
            emitter, PATHOGEN, 1, 1.0e6, 7.8, {}, {},
        )
        assert core.rng.bit_generator.state == state

    def test_no_available_responder_returns_zero(self) -> None:
        core = _core(caregiver={
            "response_probability": (1.0, 1.0),
            "steward_fallback": False,
        })
        emitter = _emitting(1, _profile(), np.random.default_rng(3))
        mate = _agent(2)
        emitter.party_member_ids = frozenset({2})
        mate.current_location = "Isolated_In_Quarters"
        core._agents_by_id = {1: emitter, 2: mate}
        assert core._caregiver_response(
            emitter, PATHOGEN, 1, 1.0e6, 7.8, {}, {},
        ) == pytest.approx(0.0)

    def test_cleanup_mass_is_netted_out_of_the_patch(self) -> None:
        core, emitter, _responder = self._scene(
            response_probability=(1.0, 1.0),
            report_probability=(0.0, 0.0),
            steward_fallback=False,
        )
        profile = _profile()
        emitter.clock = core.clock
        doses: dict[int, float] = {}
        pw: dict[int, dict[str, float]] = {}
        pool_gain = 0.0
        for epoch in range(20):
            emitter.infections[PATHOGEN]["time_infected"] = epoch
            pool_gain += core._deposit_emesis(
                emitter, PATHOGEN, ZONE, epoch, profile, doses, pw,
            )
        records = emitter.emesis_deposition_records_by_pathogen[PATHOGEN]
        assert records
        touched = [r for r in records if r["caregiver_contacted"] > 0.0]
        assert touched, "forced response should have answered an episode"
        for r in touched:
            assert r["pool_gain"] < r["surface_load"] * r["touchable_fraction"]


class TestCaregiverDiscovery:
    """The stamp converts to a sick-call entry through the attendant path."""

    @staticmethod
    def _agent_dict(**extra: object) -> dict:
        agent = {
            "agent_id": 1,
            "infection_state": INFECTION_INFECTED,
            "symptom_presentation": PRESENTATION_SYMPTOMATIC,
            "compliance_status": COMPLIANCE_COMPLIANT,
            "pathogen_infections": {
                "norwalk_gi": {
                    "pathogen_id": "norwalk_gi",
                    "illness": "SYMPTOMATIC",
                    "symptom_severity": "subclinical",
                },
            },
        }
        agent.update(extra)
        return agent

    def test_stamp_reports_regardless_of_self_report_hazard(self) -> None:
        profile = {
            "norwalk_gi": {
                "severity_model": {
                    "states": ["asymptomatic", "subclinical", "mild"],
                    "base_probabilities": [0.25, 0.5, 0.25],
                },
                "observation_model": {
                    "syndrome_case_eligibility_by_severity": [0, 0, 0],
                    "reporting_probability_by_severity_pre_recognition": [
                        0, 0, 0,
                    ],
                    "reporting_probability_by_severity_post_recognition": [
                        0, 0, 0,
                    ],
                    "episode_reporting_window_days": 2.0,
                },
            },
        }
        syn = SyndromicSurveillance(
            background_noise_rate=0.0,
            symptom_severity_profiles=profile,
            rng=np.random.default_rng(7),
        )
        agent = self._agent_dict(caregiver_report_due_epoch=3)
        out = syn.query_ground_truth({"epoch": 3, "agents": [agent]})
        assert out["sick_call_agents"] == [1]
        assert out["caregiver_report_ids"] == [1]

    def test_stamp_on_a_subclinical_host_reports_nothing(self) -> None:
        syn = SyndromicSurveillance(
            background_noise_rate=0.0,
            rng=np.random.default_rng(7),
        )
        agent = self._agent_dict(
            caregiver_report_due_epoch=3,
            symptom_presentation="ASYMPTOMATIC",
        )
        agent["pathogen_infections"]["norwalk_gi"]["illness"] = (
            "ASYMPTOMATIC"
        )
        out = syn.query_ground_truth({"epoch": 3, "agents": [agent]})
        assert out["sick_call_agents"] == []
        assert out["caregiver_report_ids"] == []
