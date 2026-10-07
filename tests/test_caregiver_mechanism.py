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
        # CAREGIVER-V1 presence gate: the ring member must be in the
        # event's compartment — same stateroom for a cabin emesis.
        emitter.cabin_mate_ids = frozenset({2})
        responder.cabin_mate_ids = frozenset({1})
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
            emitter, PATHOGEN, 1, ZONE, 1.0e6, 7.8, doses, pw,
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
            emitter, PATHOGEN, 1, ZONE, 1.0e6, 7.8, doses, pw,
        )
        assert contacted > 0.0
        assert core.caregiver_telemetry["steward_responses"] == 1

    def test_off_mode_is_silent(self) -> None:
        core, emitter, responder = self._scene(mode="off")
        contacted = core._caregiver_response(
            emitter, PATHOGEN, 1, ZONE, 1.0e6, 7.8, {}, {},
        )
        assert contacted == pytest.approx(0.0)
        assert emitter.caregiver_report_due_epoch is None

    def test_off_mode_draws_no_rng(self) -> None:
        """Labelled baseline: the arm leaves the RNG stream untouched."""
        core, emitter, responder = self._scene(mode="off")
        state = core.rng.bit_generator.state
        core._caregiver_response(
            emitter, PATHOGEN, 1, ZONE, 1.0e6, 7.8, {}, {},
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
            emitter, PATHOGEN, 1, ZONE, 1.0e6, 7.8, {}, {},
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


class TestCaregiverV1:
    """CAREGIVER-V1: role grammar, presence gate, R2 tending, R3 service.

    Invariants and graded sensitivity only: the grammar resolves to the
    declared role tree, a ring member answers only when physically at the
    event, the designation lifecycle is once-per-course and retires on
    recovery, and a Meal token at a confined host produces exactly one
    service delivery whose dose lands under route ``caregiver``.
    """

    @staticmethod
    def _symptomatic_host(aid: int = 1) -> KorkinAgent:
        host = _emitting(aid, _profile(), np.random.default_rng(3))
        host.infections[PATHOGEN]["will_present"] = True
        return host

    @staticmethod
    def _family_pair() -> tuple:
        """Host + capable adult ring member sharing a stateroom."""
        host = TestCaregiverV1._symptomatic_host(1)
        cg = _agent(2)
        cg.age_band = "adult"
        host.party_member_ids = frozenset({2})
        cg.party_member_ids = frozenset({1})
        host.cabin_mate_ids = frozenset({2})
        cg.cabin_mate_ids = frozenset({1})
        return host, cg

    def test_role_grammar_resolves_to_the_declared_tree(self) -> None:
        core = _core(caregiver={
            "budget_mode": "additive",
            "care_response_by_host_age_band": {
                "child": 2.0, "adult": 1.0, "elderly": 1.1,
            },
            "responder_protection_factor": {"steward": (0.1, 0.2)},
            "tending": {
                "enabled": {"*": True},
                "response_probability": (0.7, 0.7),
            },
        })
        block = core.caregiver_resolved_block()
        assert block["mode"] == "on"
        assert block["budget_mode"] == "additive"
        assert block["roles"]["tending"]["enabled"] == {"*": True}
        assert block["roles"]["tending"]["response_probability"] == [0.7, 0.7]
        assert block["responder_protection_factor"]["steward"] == [0.1, 0.2]
        assert block["care_response_by_host_age_band"]["child"] == pytest.approx(2.0)

    def test_flat_keys_parse_as_cleanup_shorthand(self) -> None:
        core = _core(caregiver={"response_probability": (0.5, 0.5)})
        assert core._cg_cleanup["response_probability"] == (0.5, 0.5)
        assert core._cg_cleanup["steward_fallback"] is True
        # The shipped V1 defaults: tending respiratory-only, service on.
        assert not core._cg_role_enabled(core._cg_tending, "norwalk_gi")
        assert core._cg_role_enabled(core._cg_service, "norwalk_gi")

    def test_presence_gate_sends_absent_ring_to_the_steward(self) -> None:
        core = _core(caregiver={
            "response_probability": (1.0, 1.0),
            "steward_response_probability": (1.0, 1.0),
            "report_probability": (0.0, 0.0),
        })
        emitter = self._symptomatic_host(1)
        mate, _cg = self._family_pair()
        mate.agent_id = 2
        emitter.party_member_ids = frozenset({2})
        emitter.cabin_mate_ids = frozenset({2})
        mate.cabin_mate_ids = frozenset({1})
        mate.current_location = "Main_Pool_Deck"  # aboard, not at the event
        steward = _agent(9, role="crew")
        core._agents_by_id = {1: emitter, 2: mate, 9: steward}
        contacted = core._caregiver_response(
            emitter, PATHOGEN, 1, ZONE, 1.0e6, 7.8, {}, {},
        )
        assert contacted > 0.0
        assert core.caregiver_telemetry["caregiver_responses"] == 0
        assert core.caregiver_telemetry["steward_responses"] == 1

    def test_steward_protection_discounts_the_steward_own_dose(self) -> None:
        core = _core(caregiver={
            "response_probability": (0.0, 0.0),
            "steward_response_probability": (1.0, 1.0),
            "report_probability": (0.0, 0.0),
            "responder_protection_factor": {"steward": (0.0, 0.0)},
        })
        emitter = self._symptomatic_host(1)
        steward = _agent(9, role="crew")
        core._agents_by_id = {1: emitter, 9: steward}
        contacted = core._caregiver_response(
            emitter, PATHOGEN, 1, ZONE, 1.0e6, 7.8, {}, {},
        )
        # The surface still loses what the cleanup touched; the gloved
        # steward keeps none of it on their own hand.
        assert contacted > 0.0
        assert (
            core.caregiver_telemetry["caregiver_dose_delivered"]
            == pytest.approx(0.0)
        )

    def test_designation_relocates_under_reallocate(self) -> None:
        core = _core(caregiver={
            "tending": {
                "enabled": {"*": True},
                "response_probability": (1.0, 1.0),
                "report_probability": (1.0, 1.0),
                "tending_hours_per_day": (24.0, 24.0),
            },
        })
        host, cg = self._family_pair()
        core._agents_by_id = {1: host, 2: cg}
        moves = core.caregiver_epoch_setup(1, [host, cg])
        assert moves == {2: ZONE}
        assert 2 in core._cg_absorbed_ids
        assert core.caregiver_telemetry["tending_designations"] == 1
        assert host.caregiver_report_due_epoch == 1
        occupants = core._epoch_zone_occupants([host, cg], 1)
        assert cg not in occupants.get(ZONE, [])
        assert host in occupants.get(ZONE, [])

    def test_additive_keeps_the_caregiver_in_the_pools(self) -> None:
        core = _core(caregiver={
            "budget_mode": "additive",
            "tending": {
                "enabled": {"*": True},
                "response_probability": (1.0, 1.0),
                "report_probability": (0.0, 0.0),
                "tending_hours_per_day": (24.0, 24.0),
            },
        })
        host, cg = self._family_pair()
        core._agents_by_id = {1: host, 2: cg}
        moves = core.caregiver_epoch_setup(1, [host, cg])
        assert moves == {}
        assert core._cg_absorbed_ids == set()

    def test_refusal_is_once_per_course(self) -> None:
        core = _core(caregiver={
            "tending": {
                "enabled": {"*": True},
                "response_probability": (0.0, 0.0),
            },
        })
        host, cg = self._family_pair()
        core._agents_by_id = {1: host, 2: cg}
        for epoch in range(1, 4):
            assert core.caregiver_epoch_setup(epoch, [host, cg]) == {}
        # The failed onset draw holds for the course — one refusal, not
        # one per symptomatic epoch.
        assert core.caregiver_telemetry["tending_refusals"] == 1

    def test_designation_retires_on_host_recovery(self) -> None:
        core = _core(caregiver={
            "tending": {
                "enabled": {"*": True},
                "response_probability": (1.0, 1.0),
                "report_probability": (0.0, 0.0),
                "tending_hours_per_day": (24.0, 24.0),
            },
        })
        host, cg = self._family_pair()
        core._agents_by_id = {1: host, 2: cg}
        assert core.caregiver_epoch_setup(1, [host, cg]) == {2: ZONE}
        host.infections[PATHOGEN]["illness"] = IllnessStatus.RECOVERED
        assert core.caregiver_epoch_setup(2, [host, cg]) == {}
        assert core._cg_designations == {}

    def test_service_delivery_on_a_confined_hosts_meal_token(self) -> None:
        core = _core(caregiver={
            "service": {
                "enabled": {"*": True},
                "report_probability": (1.0, 1.0),
            },
        })
        host = self._symptomatic_host(1)
        host.current_location = "Isolated_In_Quarters"
        host.schedule = ["Meal:Main"] * 24
        steward = _agent(9, role="crew")
        core._agents_by_id = {1: host, 9: steward}
        doses: dict[int, float] = {}
        pw: dict[int, dict[str, float]] = {}
        core._caregiver_pathogen_epoch(1, PATHOGEN, _profile(), doses, pw)
        assert core.caregiver_telemetry["service_deliveries"] == 1
        assert core.caregiver_telemetry["service_reports"] == 1
        assert host.caregiver_report_due_epoch == 1
        assert core.caregiver_telemetry["service_dose_credited"] > 0.0
        assert doses.get(9, 0.0) > 0.0

    def test_service_skips_an_unconfined_host(self) -> None:
        core = _core(caregiver={"service": {"enabled": {"*": True}}})
        host = self._symptomatic_host(1)  # aboard, free
        host.schedule = ["Meal:Main"] * 24
        steward = _agent(9, role="crew")
        core._agents_by_id = {1: host, 9: steward}
        core._caregiver_pathogen_epoch(1, PATHOGEN, _profile(), {}, {})
        assert core.caregiver_telemetry["service_deliveries"] == 0

    def test_service_emetic_pickup_drains_the_patch(self) -> None:
        from engines.transmission_core import EmesisPatch

        profile = _profile()
        profile["airborne_emission_mode"] = "emesis_conditioned"
        core = _core(caregiver={
            "service": {
                "enabled": {"*": True},
                "report_probability": (0.0, 0.0),
                "service_touches": (3, 3),
            },
        })
        host = self._symptomatic_host(1)
        host.current_location = "Isolated_In_Quarters"
        host.schedule = ["Meal:Main"] * 24
        steward = _agent(9, role="crew")
        core._agents_by_id = {1: host, 9: steward}
        patch = EmesisPatch(
            mass=1.0e6,
            high_touch_area_m2=2.0,
            occupant_share=1.0,
            epoch=0,
        )
        core.emesis_patch_pools_by_pathogen.setdefault(
            PATHOGEN, {},
        )[ZONE] = [patch]
        core._caregiver_pathogen_epoch(1, PATHOGEN, profile, {}, {})
        assert core.caregiver_telemetry["service_deliveries"] == 1
        assert patch.mass < 1.0e6

    @staticmethod
    def _service_dose(caregiver: dict, profile: dict | None = None) -> float:
        core = _core(caregiver={"service": dict(caregiver)})
        host = TestCaregiverV1._symptomatic_host(1)
        return core._caregiver_service_dose(
            host, _agent(9, role="crew"), 1, PATHOGEN,
            profile if profile is not None else _profile(),
        )

    def test_service_contact_factor_scales_pair_dose(self) -> None:
        """A fixed factor multiplies the respiratory pair dose exactly —
        the dedicated stream never touches the shared draws, so
        dose(f) == f x dose(1.0) at one seed; a [lo, hi] window lands in
        [lo x full, hi x full]."""
        full = self._service_dose({"contact_factor": 1.0})
        assert full > 0.0
        assert self._service_dose({"contact_factor": 0.5}) == pytest.approx(
            0.5 * full
        )
        assert self._service_dose({"contact_factor": 0.0}) == pytest.approx(0.0)
        bounded = self._service_dose({"contact_factor": (0.2, 0.4)})
        assert 0.2 * full <= bounded <= 0.4 * full

    def test_service_contact_factor_limits_emetic_pickup(self) -> None:
        """The factor scales the nominal patch take: less mass lifted,
        less mass removed — dose and drain both halve at 0.5."""
        from engines.transmission_core import EmesisPatch

        profile = _profile()
        profile["airborne_emission_mode"] = "emesis_conditioned"

        def run(factor: float) -> tuple[float, float]:
            core = _core(caregiver={
                "service": {
                    "contact_factor": factor,
                    "service_touches": (3, 3),
                },
            })
            patch = EmesisPatch(
                mass=1.0e6, high_touch_area_m2=2.0,
                occupant_share=1.0, epoch=0,
            )
            core.emesis_patch_pools_by_pathogen.setdefault(
                PATHOGEN, {},
            )[ZONE] = [patch]
            dose = core._caregiver_service_dose(
                self._symptomatic_host(1), _agent(9, role="crew"),
                1, PATHOGEN, profile,
            )
            return dose, patch.mass

        full_dose, full_mass = run(1.0)
        half_dose, half_mass = run(0.5)
        assert full_dose > 0.0
        assert half_dose == pytest.approx(0.5 * full_dose)
        assert half_mass > full_mass

    def test_service_contact_factor_zero_keeps_the_discovery(self) -> None:
        """f=0 is a dose discount, not a channel removal: the delivery
        and its report stamp still land — limited contact does not cost
        the confinement feed."""
        core = _core(caregiver={
            "service": {
                "enabled": {"*": True},
                "report_probability": (1.0, 1.0),
                "contact_factor": 0.0,
            },
        })
        host = self._symptomatic_host(1)
        host.current_location = "Isolated_In_Quarters"
        host.schedule = ["Meal:Main"] * 24
        steward = _agent(9, role="crew")
        core._agents_by_id = {1: host, 9: steward}
        doses: dict[int, float] = {}
        core._caregiver_pathogen_epoch(1, PATHOGEN, _profile(), doses, {})
        assert core.caregiver_telemetry["service_deliveries"] == 1
        assert core.caregiver_telemetry["service_reports"] == 1
        assert host.caregiver_report_due_epoch == 1
        assert core.caregiver_telemetry["service_dose_credited"] == pytest.approx(0.0)
        assert doses.get(9, 0.0) == pytest.approx(0.0)

    def test_service_contact_factor_baseline_spawns_no_stream(self) -> None:
        """Fixed factors draw nothing — the labelled baseline
        ``contact_factor: 1.0`` spawns no dedicated stream."""
        fixed = _core(caregiver={"service": {"contact_factor": 1.0}})
        assert fixed._service_contact_rng is None
        assert fixed._cg_service_contact == ("fixed", 1.0)
        uniform = _core(caregiver={"service": {"contact_factor": (0.1, 0.2)}})
        assert uniform._cg_service_contact == ("uniform", 0.1, 0.2)
        assert uniform._service_contact_rng is not None

    def test_service_contact_factor_malformed_fails_at_spec(self) -> None:
        for bad in ("off", 1.5, -0.1, (0.8, 0.2), (0.1, 0.2, 0.3), True):
            with pytest.raises(ValueError):
                _core(caregiver={"service": {"contact_factor": bad}})

    def test_epoch_setup_mode_off_draws_no_rng(self) -> None:
        core = _core(caregiver={"mode": "off"})
        host, cg = self._family_pair()
        state = core.rng.bit_generator.state
        assert core.caregiver_epoch_setup(1, [host, cg]) == {}
        assert core.rng.bit_generator.state == state


class TestMealSvc01:
    """MEAL-SVC-01: the steward->host direction and steward sections.

    Behaviour and invariant tests only: ``direction: "both"`` credits a
    susceptible confined host the roles-swap dose under route
    ``service_to_host`` (a non-shedding steward delivers zero), an
    already-infected host is delivered-not-credited, and
    ``service_responder_mode: "section"`` binds each cabin block to one
    steward drawn once on the dedicated stream — leaving the voyage RNG
    untouched and collapsing the realized distinct-steward count.
    """

    @staticmethod
    def _confined_host(aid: int = 1) -> KorkinAgent:
        host = _agent(aid)
        host.current_location = "Isolated_In_Quarters"
        host.schedule = ["Meal:Main"] * 24
        return host

    @staticmethod
    def _emitting_steward(aid: int = 9) -> KorkinAgent:
        steward = TestCaregiverV1._symptomatic_host(aid)
        steward.role = "crew"
        steward.party_id = -1
        return steward

    def test_dir_credits_a_susceptible_confined_host(self) -> None:
        core = _core(caregiver={
            "service": {
                "enabled": {"*": True},
                "direction": "both",
                "report_probability": (0.0, 0.0),
            },
        })
        host = self._confined_host(1)
        steward = self._emitting_steward(9)
        core._agents_by_id = {1: host, 9: steward}
        doses: dict[int, float] = {}
        pw: dict[int, dict[str, float]] = {}
        core._caregiver_pathogen_epoch(1, PATHOGEN, _profile(), doses, pw)
        assert core.caregiver_telemetry["service_deliveries"] == 1
        assert core.caregiver_telemetry["service_dose_to_host_delivered"] > 0.0
        assert core.caregiver_telemetry["service_dose_to_host_credited"] > 0.0
        assert doses.get(1, 0.0) == pytest.approx(
            pw.get(1, {}).get("service_to_host", 0.0)
        )
        assert doses.get(1, 0.0) > 0.0

    def test_dir_a_non_shedding_steward_delivers_zero(self) -> None:
        core = _core(caregiver={
            "service": {
                "enabled": {"*": True},
                "direction": "both",
                "report_probability": (0.0, 0.0),
            },
        })
        host = TestCaregiverV1._symptomatic_host(1)
        host.current_location = "Isolated_In_Quarters"
        host.schedule = ["Meal:Main"] * 24
        steward = _agent(9, role="crew")
        core._agents_by_id = {1: host, 9: steward}
        doses: dict[int, float] = {}
        pw: dict[int, dict[str, float]] = {}
        core._caregiver_pathogen_epoch(1, PATHOGEN, _profile(), doses, pw)
        # The shipped direction still dosed the steward off the shedding
        # host; the reverse direction found nothing to inhale.
        assert core.caregiver_telemetry["service_dose_credited"] > 0.0
        assert core.caregiver_telemetry[
            "service_dose_to_host_delivered"
        ] == pytest.approx(0.0)
        assert core.caregiver_telemetry[
            "service_dose_to_host_credited"
        ] == pytest.approx(0.0)
        assert doses.get(1, 0.0) == pytest.approx(0.0)

    def test_dir_an_infected_host_is_delivered_not_credited(self) -> None:
        core = _core(caregiver={
            "service": {
                "enabled": {"*": True},
                "direction": "both",
                "report_probability": (0.0, 0.0),
            },
        })
        host = TestCaregiverV1._symptomatic_host(1)
        host.current_location = "Isolated_In_Quarters"
        host.schedule = ["Meal:Main"] * 24
        steward = self._emitting_steward(9)
        core._agents_by_id = {1: host, 9: steward}
        doses: dict[int, float] = {}
        pw: dict[int, dict[str, float]] = {}
        core._caregiver_pathogen_epoch(1, PATHOGEN, _profile(), doses, pw)
        assert core.caregiver_telemetry["service_dose_to_host_delivered"] > 0.0
        assert core.caregiver_telemetry[
            "service_dose_to_host_credited"
        ] == pytest.approx(0.0)
        assert pw.get(1, {}).get("service_to_host", 0.0) == pytest.approx(0.0)

    def test_emetic_profile_has_no_reverse_dose(self) -> None:
        profile = _profile()
        profile["airborne_emission_mode"] = "emesis_conditioned"
        core = _core(caregiver={
            "service": {
                "enabled": {"*": True},
                "direction": "both",
                "report_probability": (0.0, 0.0),
            },
        })
        host = self._confined_host(1)
        steward = self._emitting_steward(9)
        core._agents_by_id = {1: host, 9: steward}
        core._caregiver_pathogen_epoch(1, PATHOGEN, profile, {}, {})
        assert core.caregiver_telemetry["service_deliveries"] == 1
        assert core.caregiver_telemetry[
            "service_dose_to_host_delivered"
        ] == pytest.approx(0.0)

    def test_responder_direction_is_the_shipped_status_quo(self) -> None:
        core = _core(caregiver={
            "service": {"enabled": {"*": True}},
        })
        host = self._confined_host(1)
        steward = self._emitting_steward(9)
        core._agents_by_id = {1: host, 9: steward}
        doses: dict[int, float] = {}
        core._caregiver_pathogen_epoch(1, PATHOGEN, _profile(), doses, {})
        assert core._cg_service["direction"] == "responder"
        assert core.caregiver_telemetry["service_deliveries"] == 1
        assert core.caregiver_telemetry[
            "service_dose_to_host_delivered"
        ] == pytest.approx(0.0)
        assert doses.get(1, 0.0) == pytest.approx(0.0)

    def test_section_binds_one_steward_per_host(self) -> None:
        core = _core(caregiver={
            "service": {
                "enabled": {"*": True},
                "service_responder_mode": "section",
                "report_probability": (0.0, 0.0),
            },
        })
        host = self._confined_host(1)
        crew = {aid: _agent(aid, role="crew") for aid in range(9, 14)}
        core._agents_by_id = {1: host, **crew}
        for epoch in range(1, 4):
            core._caregiver_pathogen_epoch(
                epoch, PATHOGEN, _profile(), {}, {},
            )
        stewards = core._service_stewards_by_host[1]
        assert len(stewards) == 1
        bound = core._service_section_steward.values()
        assert stewards == set(bound)
        assert core.caregiver_telemetry["service_section_steward_draws"] == 1
        assert core.caregiver_telemetry["service_deliveries"] == 3

    def test_section_neighbour_hosts_share_the_bound_steward(self) -> None:
        core = _core(caregiver={
            "service": {
                "enabled": {"*": True},
                "service_responder_mode": "section",
                "report_probability": (0.0, 0.0),
            },
        })
        host_a = self._confined_host(1)
        host_b = self._confined_host(2)
        crew = {aid: _agent(aid, role="crew") for aid in range(9, 14)}
        core._agents_by_id = {1: host_a, 2: host_b, **crew}
        core._caregiver_pathogen_epoch(1, PATHOGEN, _profile(), {}, {})
        assert core._service_stewards_by_host[1]
        assert (
            core._service_stewards_by_host[1]
            == core._service_stewards_by_host[2]
        )

    def test_section_draws_leave_the_voyage_stream_untouched(self) -> None:
        core = _core(caregiver={
            "service": {
                "enabled": {"*": True},
                "service_responder_mode": "section",
            },
        })
        host = self._confined_host(1)
        crew = {aid: _agent(aid, role="crew") for aid in range(9, 14)}
        core._agents_by_id = {1: host, **crew}
        state = core.rng.bit_generator.state
        first = core._draw_service_responder(1, host)
        second = core._draw_service_responder(1, host)
        assert core.rng.bit_generator.state == state
        assert first is not None
        assert first is second

    def test_section_rebinds_an_unavailable_steward(self) -> None:
        core = _core(caregiver={
            "service": {
                "enabled": {"*": True},
                "service_responder_mode": "section",
                "report_probability": (0.0, 0.0),
            },
        })
        host = self._confined_host(1)
        crew = {aid: _agent(aid, role="crew") for aid in range(9, 14)}
        core._agents_by_id = {1: host, **crew}
        core._caregiver_pathogen_epoch(1, PATHOGEN, _profile(), {}, {})
        bound_id = next(iter(core._service_stewards_by_host[1]))
        crew[bound_id].current_location = "Isolated_In_Quarters"
        core._caregiver_pathogen_epoch(2, PATHOGEN, _profile(), {}, {})
        stewards = core._service_stewards_by_host[1]
        assert len(stewards) == 2
        assert bound_id in stewards
        assert core.caregiver_telemetry["service_section_steward_draws"] == 2


class TestMealSvc02:
    """MEAL-SVC-02: ``contact_factor_to_host`` on the host direction.

    Behaviour and invariant tests only: the declared scalar/interval
    attenuates the steward->host credit alone — the steward-side dose
    keeps the shared realized draw, the shared stream's realization is
    untouched, and every realized host factor is recorded for the
    lottery witness. Absent means the shared draw (status quo).
    """

    @staticmethod
    def _host_credit_core(service: dict) -> TransmissionCore:
        return _core(caregiver={
            "service": {
                "enabled": {"*": True},
                "direction": "both",
                "report_probability": (0.0, 0.0),
                **service,
            },
        })

    def _deliver(self, core: TransmissionCore) -> dict[int, float]:
        host = TestMealSvc01._confined_host(1)
        steward = TestMealSvc01._emitting_steward(9)
        core._agents_by_id = {1: host, 9: steward}
        doses: dict[int, float] = {}
        core._caregiver_pathogen_epoch(
            1, PATHOGEN, _profile(), doses, {},
        )
        return doses

    def test_scalar_scales_the_host_dose_only(self) -> None:
        """A declared scalar multiplies the roles-swap pair dose exactly
        while the steward-side tally keeps the shared draw."""
        full = self._host_credit_core({"contact_factor_to_host": 1.0})
        self._deliver(full)
        half = self._host_credit_core({"contact_factor_to_host": 0.5})
        self._deliver(half)
        full_dose = full.caregiver_telemetry[
            "service_dose_to_host_delivered"
        ]
        half_dose = half.caregiver_telemetry[
            "service_dose_to_host_delivered"
        ]
        assert full_dose > 0.0
        assert half_dose == pytest.approx(0.5 * full_dose)
        # The steward side takes the same shared draw on both cores.
        assert half.caregiver_telemetry[
            "service_dose_delivered"
        ] == pytest.approx(full.caregiver_telemetry[
            "service_dose_delivered"
        ])

    def test_off_credits_zero_but_the_delivery_fires(self) -> None:
        core = self._host_credit_core({"contact_factor_to_host": 0.0})
        self._deliver(core)
        assert core.caregiver_telemetry["service_deliveries"] == 1
        assert core.caregiver_telemetry[
            "service_dose_to_host_credited"
        ] == pytest.approx(0.0)
        assert core._service_host_factor_stats["n"] == 1
        assert core._service_host_factor_stats["sum"] == pytest.approx(0.0)

    def test_absent_uses_the_shared_draw(self) -> None:
        core = self._host_credit_core({})
        self._deliver(core)
        assert core._cg_service_to_host_contact is None
        assert core._cg_service["contact_factor_to_host_mode"] == "shared"
        factor = core._service_host_factor_sample[0]
        lo, hi = 0.05, 0.3  # shipped CAREGIVER_SERVICE_CONTACT_FACTOR
        assert lo <= factor <= hi
        # The resolved block echoes the effective spec (the shared
        # tuple) even though nothing was declared.
        assert core._cg_service["contact_factor_to_host"] == [0.05, 0.3]

    def test_uniform_draws_on_its_own_stream(self) -> None:
        core = self._host_credit_core(
            {"contact_factor_to_host": (0.005, 0.02)},
        )
        assert core._service_host_contact_rng is not None
        voyage_state = core.rng.bit_generator.state
        shared_state = core._service_contact_rng.bit_generator.state
        factor = core._service_host_contact_factor(0.5)
        assert 0.005 <= factor <= 0.02
        assert core.rng.bit_generator.state == voyage_state
        assert (
            core._service_contact_rng.bit_generator.state == shared_state
        )

    def test_fixed_and_shared_spawn_no_host_stream(self) -> None:
        fixed = self._host_credit_core({"contact_factor_to_host": 0.01})
        assert fixed._service_host_contact_rng is None
        shared = self._host_credit_core({})
        assert shared._service_host_contact_rng is None

    def test_malformed_fails_at_spec(self) -> None:
        for bad in ("off", 1.5, -0.1, (0.8, 0.2), (0.1, 0.2, 0.3), True):
            with pytest.raises(ValueError):
                self._host_credit_core({"contact_factor_to_host": bad})
        with pytest.raises(ValueError, match="contact_factor_to_host"):
            self._host_credit_core({"contact_factor_to_host": 1.5})

    def test_responder_direction_draws_no_host_factor(self) -> None:
        core = _core(caregiver={
            "service": {
                "enabled": {"*": True},
                "contact_factor_to_host": (0.005, 0.02),
                "report_probability": (0.0, 0.0),
            },
        })
        self._deliver(core)
        assert core.caregiver_telemetry["service_deliveries"] == 1
        assert core._service_host_factor_stats["n"] == 0
