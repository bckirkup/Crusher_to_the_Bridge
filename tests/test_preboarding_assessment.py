"""The VSP 4.1.1.2 pre-boarding assessment: declaration screen, two arms.

The derivation of record is docs/norovirus/preboarding_assessment.md. These
tests pin the arm's shape — graded sensitivity over the declaration and
denial coordinates, the count invariants, and the default-off inertness
fingerprint — not a fitted outcome.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import numpy as np
import pytest

from engines.infection_dynamics_bridge import KorkinAgent
from engines.initiation import (
    BoardingSpec,
    PreboardingAssessment,
    PreboardingRoleSpec,
    _assess_boarder,
    _PreboardingTallies,
    draw_boarding_cohort,
    resolve_initiation_plan,
)
from engines.sim_clock import HOURS, SimClock
from orchestrator_epoch import step_mid_cruise_introductions
from orchestrator_init import (
    init_multi_pathogen,
    preboarding_reportable_ids,
)
from orchestrator_types import SimulationState

PATHOGEN = "norwalk_gi"
ZONE = "Cabin_A"
PASSENGERS = 120
CREW = 60
ONSET_DAYS = 1.0
RECOVERY_DAYS = 3
SHEDDING_DAYS = 15.0
PRESYMPTOMATIC_DAYS = 0.5
CHRONIC_FRACTION = 0.0
CHRONIC_SPEC = {"duration_log10_mean": 0.0, "duration_log10_sd": 0.0}


def _clock() -> SimClock:
    return SimClock(epoch_duration_hours=1.0, mode=HOURS)


def _agent(agent_id: int, role: str = "passenger") -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=agent_id,
        role=role,
        immune=False,
        home_zone=ZONE,
        dining_zone=ZONE,
        work_zone=ZONE,
        free_zone=ZONE,
        schedule=["Free"] * 4,
    )
    agent.clock = _clock()
    agent.current_location = ZONE
    return agent


class _FakeEngine:
    """Minimal engine surface used by the initiation entry points."""

    def __init__(
        self, passengers: int = PASSENGERS, crew: int = CREW,
    ) -> None:
        self.agents = [_agent(index, "passenger") for index in range(passengers)]
        self.agents += [
            _agent(passengers + index, "crew") for index in range(crew)
        ]
        self.clock = _clock()
        self.initiation_manifest: dict[str, Any] = {"mode": "legacy"}

    def initialize_pathogen(self, _pid: str) -> None:
        return None


def _profile(**overrides: Any) -> dict[str, Any]:
    """A boarding-eligible profile: no fiat index case, full clocks."""
    profile: dict[str, Any] = {
        "base_susceptibility": 1.0,
        "introduction_epoch": 0,
        "symptom_onset_day": ONSET_DAYS,
        "recovery_day": RECOVERY_DAYS,
        "shedding_duration_days": SHEDDING_DAYS,
        "presymptomatic_shedding_days": PRESYMPTOMATIC_DAYS,
        "severity_model": {
            "states": [
                "asymptomatic", "subclinical", "mild", "moderate",
                "severe_critical",
            ],
            "base_probabilities": [0.25, 0.55, 0.19, 0.009, 0.001],
        },
        "chronic_shedder_fraction": CHRONIC_FRACTION,
        "chronic_shedding_duration_days": dict(CHRONIC_SPEC),
        "clinical_presentation": {
            "symptom_axis_probabilities": {
                "vomiting": 1.0,
                "diarrhoea_given_vomiting": 1.0,
            },
            "phases": [
                {
                    "name": "acute",
                    "features": ["vomiting"],
                    "dpi_min": 0,
                    "dpi_max": 2,
                },
            ],
        },
        "emesis_episodes_range": [2, 4],
        "emesis_total_shed_gec_range": [1e6, 1e6],
    }
    profile.update(overrides)
    return profile


def _role(**overrides: Any) -> dict[str, Any]:
    block = {
        "enabled": True,
        "declaration_compliance": 1.0,
        "recall_halflife_days": None,
        "reportable": False,
        "denial_probability": 0.0,
    }
    block.update(overrides)
    return block


def _cfg(
    preboarding: dict[str, Any] | None,
    passenger: float = 0.5,
    crew: float = 0.5,
    **overrides: Any,
) -> dict[str, Any]:
    block: dict[str, Any] = {
        "state_split": {
            "never_symptomatic_fraction": 0.20,
            "presymptomatic_share_of_presenting": 0.04,
        },
    }
    if overrides.get("rate_mode") != "renewal":
        block["prevalence"] = {"passenger": passenger, "crew": crew}
    block.update(overrides)
    if preboarding is not None:
        block["preboarding_assessment"] = preboarding
    return {"initiation": {"boarding": {"enabled": True, PATHOGEN: block}}}


def _resolve(
    preboarding: dict[str, Any] | None,
    profile: dict[str, Any] | None = None,
    **overrides: Any,
) -> BoardingSpec:
    profiles = {PATHOGEN: profile or _profile()}
    plan = resolve_initiation_plan(_cfg(preboarding, **overrides), profiles)
    (spec,) = plan.boarding
    return spec


def _assessment(**overrides: Any) -> dict[str, Any]:
    block: dict[str, Any] = {
        "lookback_days": 30,
        "crew": _role(reportable=True),
        "passenger": _role(declaration_compliance=0.5, reportable=False),
        "notes": "test fixture",
    }
    block.update(overrides)
    return block


def _role_spec(enabled: bool = True, **overrides: Any) -> PreboardingRoleSpec:
    fields = {
        "enabled": enabled,
        "declaration_compliance": 1.0,
        "recall_halflife_days": None,
        "reportable": False,
        "denial_probability": 0.0,
    }
    fields.update(overrides)
    return PreboardingRoleSpec(**fields)


def _draw_assessments(
    role_spec: PreboardingRoleSpec,
    onset_age: float,
    n: int,
    seed: int,
    lookback: float = 30.0,
) -> tuple[int, int, int]:
    """(eligible, declared, screened_out) over n hosts at one onset age."""
    assessment = PreboardingAssessment(
        lookback_days=lookback,
        crew=role_spec,
        passenger=_role_spec(enabled=False),
    )
    tallies = _PreboardingTallies.empty()
    rng = np.random.default_rng(seed)
    for index in range(n):
        _assess_boarder(
            assessment, tallies, _agent(index, "crew"), "crew",
            onset_age, rng,
        )
    return (
        tallies.eligible["crew"],
        tallies.declared["crew"],
        tallies.screened_out["crew"],
    )


class TestDeclarationSensitivity:
    """Graded sensitivity over the declaration form c * 2 ** (-a / h)."""

    def test_compliance_scales_declared(self) -> None:
        declared = [
            _draw_assessments(
                _role_spec(declaration_compliance=c), 1.0, 400, 7,
            )[1]
            for c in (0.0, 0.25, 0.5, 1.0)
        ]
        assert declared[0] == 0
        assert declared[-1] == 400
        assert declared == sorted(declared)
        assert declared[1] < declared[2]

    def test_perfect_recall_declares_at_compliance(self) -> None:
        # h = null means no decay: p = c whatever the onset age.
        eligible, declared, _ = _draw_assessments(
            _role_spec(declaration_compliance=1.0), 2.5, 100, 11,
        )
        assert eligible == 100
        assert declared == 100

    def test_halflife_decays_in_onset_age(self) -> None:
        declared = [
            _draw_assessments(
                _role_spec(
                    declaration_compliance=1.0, recall_halflife_days=1.0,
                ),
                age, 400, 13,
            )[1]
            for age in (0.0, 1.0, 2.0, 3.0)
        ]
        assert declared[0] == 400
        assert declared == sorted(declared, reverse=True)
        assert declared[0] > declared[1] > declared[2] > declared[3]

    def test_denial_moves_declared_to_screened_out(self) -> None:
        _, declared, screened = _draw_assessments(
            _role_spec(denial_probability=0.0), 1.0, 200, 17,
        )
        assert declared == 200
        assert screened == 0
        _, declared, screened = _draw_assessments(
            _role_spec(denial_probability=1.0), 1.0, 200, 17,
        )
        assert declared == 200
        assert screened == 200

    def test_a_denied_host_is_never_reportable(self) -> None:
        assessment = PreboardingAssessment(
            lookback_days=30.0,
            crew=_role_spec(reportable=True, denial_probability=1.0),
            passenger=_role_spec(enabled=False),
        )
        tallies = _PreboardingTallies.empty()
        rng = np.random.default_rng(19)
        for index in range(100):
            admitted = _assess_boarder(
                assessment, tallies, _agent(index, "crew"), "crew", 1.0, rng,
            )
            assert not admitted
        assert tallies.screened_out["crew"] == 100
        assert not tallies.reportable["crew"]

    def test_onset_outside_the_lookback_consumes_no_draw(self) -> None:
        assessment = PreboardingAssessment(
            lookback_days=3.0,
            crew=_role_spec(reportable=True),
            passenger=_role_spec(enabled=False),
        )
        tallies = _PreboardingTallies.empty()
        rng = np.random.default_rng(23)
        _assess_boarder(
            assessment, tallies, _agent(0, "crew"), "crew", 5.0, rng,
        )
        assert tallies.eligible["crew"] == 0
        # No declaration draw was consumed.
        assert rng.random() == pytest.approx(
            np.random.default_rng(23).random(),
        )

    def test_a_disabled_role_consumes_no_draw(self) -> None:
        assessment = PreboardingAssessment(
            lookback_days=30.0,
            crew=_role_spec(enabled=False),
            passenger=_role_spec(enabled=False),
        )
        tallies = _PreboardingTallies.empty()
        rng = np.random.default_rng(29)
        admitted = _assess_boarder(
            assessment, tallies, _agent(0, "crew"), "crew", 1.0, rng,
        )
        assert admitted
        assert tallies.eligible["crew"] == 0


class TestResolution:
    """The block validates like the rest of the boarding block."""

    def test_absent_block_is_inert(self) -> None:
        assert _resolve(None).preboarding is None

    def test_shipped_shape_resolves(self) -> None:
        spec = _resolve(_assessment())
        assert spec.preboarding is not None
        assert spec.preboarding.lookback_days == pytest.approx(30.0)
        assert spec.preboarding.crew.reportable is True
        assert spec.preboarding.passenger.reportable is False

    def test_disabled_roles_still_resolve(self) -> None:
        spec = _resolve({
            "lookback_days": 3,
            "crew": {"enabled": False},
            "passenger": {"enabled": False},
            "notes": "off",
        })
        assert spec.preboarding is not None
        assert not spec.preboarding.crew.enabled

    def test_passenger_reportable_is_a_load_error(self) -> None:
        with pytest.raises(ValueError, match="crew-only"):
            _resolve(_assessment(
                passenger=_role(reportable=True),
            ))

    @pytest.mark.parametrize(
        ("role_block", "match"),
        [
            (_role(declaration_compliance=1.5), "outside"),
            (_role(declaration_compliance=-0.1), "outside"),
            (_role(recall_halflife_days=0), "positive"),
            (_role(recall_halflife_days=-1), "positive"),
            (_role(denial_probability=1.5), "outside"),
            (_role(denial_probability=-0.1), "outside"),
        ],
    )
    def test_role_coordinates_are_bounded(
        self, role_block: dict[str, Any], match: str,
    ) -> None:
        with pytest.raises(ValueError, match=match):
            _resolve(_assessment(crew=role_block))

    def test_negative_lookback_is_refused(self) -> None:
        with pytest.raises(ValueError, match="negative"):
            _resolve(_assessment(lookback_days=-1))

    def test_unknown_keys_are_refused(self) -> None:
        with pytest.raises(ValueError, match="unknown keys"):
            _resolve(_assessment(lookback_years=3))
        with pytest.raises(ValueError, match="unknown keys"):
            _resolve(_assessment(
                crew=_role(declaration_rate=1.0),
            ))

    def test_a_non_mapping_block_is_refused(self) -> None:
        with pytest.raises(ValueError, match="must be a mapping"):
            _resolve("yes")


class TestCohortDraw:
    """The arm over a whole draw: invariants and the screened-out sink."""

    def _draw(
        self,
        preboarding: dict[str, Any] | None,
        seed: int = 41,
        **overrides: Any,
    ) -> Any:
        spec = _resolve(preboarding, **overrides)
        agents = [_agent(i) for i in range(200)] + [
            _agent(400 + i, "crew") for i in range(100)
        ]
        return draw_boarding_cohort(
            spec, agents, _profile(), _clock(),
            np.random.default_rng(seed),
        ), agents

    def test_off_path_reports_no_preboarding(self) -> None:
        report, _ = self._draw(None)
        assert report.preboarding is None
        assert report.preboarding_reportable_ids == ()

    def test_declared_leq_eligible_and_screened_leq_declared(self) -> None:
        report, _ = self._draw(_assessment())
        for role in ("passenger", "crew"):
            arm = report.preboarding[role]
            assert 0 <= arm["declared"] <= arm["eligible"]
            assert 0 <= arm["screened_out"] <= arm["declared"]
            assert arm["preboarding_reportable"] <= (
                arm["declared"] - arm["screened_out"]
            )

    def test_denial_one_removes_the_eligible_cohort(self) -> None:
        report, agents = self._draw(_assessment(
            crew=_role(reportable=True, denial_probability=1.0),
            passenger=_role(
                declaration_compliance=1.0, denial_probability=1.0,
            ),
        ))
        arm_crew = report.preboarding["crew"]
        arm_pax = report.preboarding["passenger"]
        assert arm_crew["screened_out"] == arm_crew["declared"]
        assert arm_pax["screened_out"] == arm_pax["declared"]
        # Every screened-out host left the drawn cohort and holds no record.
        boarded = {
            agent.agent_id
            for agent in agents
            if PATHOGEN in agent.infections
        }
        assert len(boarded) == sum(report.drawn_by_role.values())
        assert "screened_out" not in report.composition

    def test_reportable_crew_ids_are_recorded(self) -> None:
        report, agents = self._draw(_assessment(
            passenger=_role(declaration_compliance=0.0),
        ))
        ids = set(report.preboarding_reportable_ids)
        crew_arm = report.preboarding["crew"]
        assert len(ids) == crew_arm["preboarding_reportable"]
        assert crew_arm["eligible"] > 0
        # Reportable ids all belong to crew who actually boarded infected.
        boarded_crew = {
            a.agent_id for a in agents
            if PATHOGEN in a.infections and a.role == "crew"
        }
        assert ids <= boarded_crew
        # Passengers are never reportable: the clause is crew-only.
        assert report.preboarding["passenger"]["preboarding_reportable"] == 0

    def test_reportable_off_records_no_ids(self) -> None:
        report, _ = self._draw(_assessment(
            crew=_role(reportable=False),
            passenger=_role(declaration_compliance=0.0),
        ))
        assert report.preboarding["crew"]["declared"] > 0
        assert report.preboarding_reportable_ids == ()


class TestManifestAndWiring:
    """The readout carries the arm; the ids reach ever_reported_ids."""

    def test_manifest_carries_the_assessment(self) -> None:
        engine = _FakeEngine()
        profiles = {PATHOGEN: _profile()}
        cfg = _cfg(_assessment())
        init_multi_pathogen(
            engine, profiles, cfg, np.random.default_rng(43),
        )
        entry = engine.initiation_manifest["boarding"][PATHOGEN]
        arm = entry["preboarding_assessment"]
        assert arm["lookback_days"] == 30
        assert set(arm["crew"]) >= {
            "eligible", "declared", "screened_out", "preboarding_reportable",
            "declaration_compliance", "recall_halflife_days",
            "reportable", "denial_probability",
        }
        assert len(engine.preboarding_reportable_ids) == (
            arm["crew"]["preboarding_reportable"]
        )

    def test_epoch_zero_ids_reach_the_live_state(self) -> None:
        engine = _FakeEngine()
        profiles = {PATHOGEN: _profile()}
        cfg = _cfg(_assessment(
            passenger=_role(declaration_compliance=0.0),
        ))
        init_multi_pathogen(
            engine, profiles, cfg, np.random.default_rng(47),
        )
        ids = preboarding_reportable_ids(engine)
        assert ids
        state = SimulationState(ever_reported_ids=set(ids))
        assert ids <= state.ever_reported_ids
        # The counter readout is len(ever_reported_ids): the declared crew
        # case is a reported case without passing the sick-call ladder.
        assert len(state.ever_reported_ids) == len(ids)

    def test_a_later_port_call_unions_its_reportable_ids(self) -> None:
        engine = _FakeEngine()
        profiles = {
            PATHOGEN: _profile(
                introduction_epoch=6,
                boarding={
                    "enabled": True,
                    "prevalence": {"passenger": 0.5, "crew": 0.5},
                    "state_split": {
                        "never_symptomatic_fraction": 0.20,
                        "presymptomatic_share_of_presenting": 0.04,
                    },
                    "preboarding_assessment": _assessment(
                        passenger=_role(declaration_compliance=0.0),
                    ),
                },
            ),
        }
        init_multi_pathogen(
            engine, profiles,
            {"initiation": {"boarding": {"enabled": True}}},
            np.random.default_rng(53),
        )
        assert not preboarding_reportable_ids(engine)
        state = SimulationState()
        step_mid_cruise_introductions(
            6, engine, profiles, np.random.default_rng(59), state=state,
        )
        ids = preboarding_reportable_ids(engine)
        assert ids
        assert ids <= state.ever_reported_ids


class TestDefaultInertness:
    """The arm off is bit-for-bit the pre-arm draw.

    CHANGE DETECTOR: the fingerprint and RNG cursor pin this file's renewal
    draw harness with the arm absent — captured on main before the arm
    existed (the profile fixture differs from test_symptomatic_boarding's,
    so the fingerprint is this file's own). If it moves, the arm is not
    inert: investigate, do not update the constants.
    """

    _INERTNESS_FINGERPRINT = (
        "7bf75b719bf69ca14ce9818617ef64bde393b4d8c7e57eb5ceec603ce8d2b61e"
    )
    _INERTNESS_RNG_NEXT = 0.8120945066557737

    def _run(self, preboarding: dict[str, Any] | None) -> tuple[str, float]:
        spec = _resolve(preboarding, rate_mode="renewal", renewal={
            "case_incidence_per_1000_py": {"passenger": 39.0, "crew": 39.0},
            "detectable_duration_days": 28.0,
        })
        rng = np.random.default_rng(123)
        agents = [_agent(i) for i in range(200)] + [
            _agent(200 + i, "crew") for i in range(100)
        ]
        report = draw_boarding_cohort(
            spec, agents, _profile(illness_duration={
                "draw": "empirical_survival",
                "unit": "days",
                "survival": [
                    {"day": 0, "probability": 1.0},
                    {"day": 1, "probability": 0.63},
                    {"day": 2, "probability": 0.355},
                    {"day": 3, "probability": 0.22},
                    {"day": 4, "probability": 0.13},
                    {"day": 5, "probability": 0.079},
                    {"day": 6, "probability": 0.057},
                    {"day": 7, "probability": 0.03},
                    {"day": 8, "probability": 0.023},
                    {"day": 9, "probability": 0.019},
                    {"day": 13, "probability": 0.0},
                ],
            }),
            _clock(), rng,
        )
        records = sorted(
            (
                agent.agent_id,
                agent.infections[PATHOGEN]["boarding_state"],
                agent.infections[PATHOGEN]["time_infected"],
            )
            for agent in agents
            if PATHOGEN in agent.infections
        )
        payload = {
            "records": records,
            "drawn": report.drawn_by_role,
            "composition": {
                state: count
                for state, count in report.composition.items()
                if count
            },
        }
        fingerprint = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode(),
        ).hexdigest()
        return fingerprint, rng.random()

    def test_the_absent_block_is_the_pre_arm_draw(self) -> None:
        fingerprint, rng_next = self._run(None)
        assert fingerprint == self._INERTNESS_FINGERPRINT
        assert rng_next == pytest.approx(
            self._INERTNESS_RNG_NEXT, abs=1e-15,
        )

    def test_the_disabled_block_is_the_pre_arm_draw(self) -> None:
        fingerprint, rng_next = self._run({
            "lookback_days": 3,
            "crew": {"enabled": False},
            "passenger": {"enabled": False},
            "notes": "off",
        })
        assert fingerprint == self._INERTNESS_FINGERPRINT
        assert rng_next == pytest.approx(
            self._INERTNESS_RNG_NEXT, abs=1e-15,
        )
