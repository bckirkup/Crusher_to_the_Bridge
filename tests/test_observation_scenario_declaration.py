"""The observation model's ascertainment vectors as a declaration (#27).

The fifteen numbers behind a VSP-posted case are assumed, not measured, and
one empirical aggregate constrains them jointly rather than individually. So
what is tested here is not their values -- no test may assert those, since
nothing identifies them -- but the three properties that keep the declaration
honest: every number says it is declared, uncertainty travels as whole
coherent ladders, and switching ladders changes what the observer records.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from crusher_labs.modalities.syndromic import SyndromicSurveillance
from orchestrator_init import (
    SCENARIO_VECTORS,
    _validate_symptom_severity_profiles,
)
from picard_framework.pathogen_overrides import apply_pathogen_overrides
from telemetry_buffer.observation_model.bounded_screen import (
    observation_scenario_patch,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLE = "active_profiles"
PATHOGEN = "norwalk_gi"

INFECTION_INFECTED = "INFECTED"
PRESENTATION_SYMPTOMATIC = "SYMPTOMATIC"
COMPLIANCE_COMPLIANT = "COMPLIANT"


@pytest.fixture
def profile() -> dict[str, Any]:
    """The shipped norovirus profile, as authored."""
    path = REPO_ROOT / "data" / "pathogens" / f"{BUNDLE}.json"
    bundle = json.loads(path.read_text(encoding="utf-8"))
    for entry in bundle["pathogens"]:
        if entry["pathogen_id"] == PATHOGEN:
            return entry
    raise AssertionError(f"{PATHOGEN} missing from {BUNDLE}")


def _agent(severity: str) -> dict[str, Any]:
    return {
        "agent_id": 1,
        "infection_state": INFECTION_INFECTED,
        "symptom_presentation": PRESENTATION_SYMPTOMATIC,
        "compliance_status": COMPLIANCE_COMPLIANT,
        "pathogen_infections": {
            PATHOGEN: {
                "pathogen_id": PATHOGEN,
                "illness": "SYMPTOMATIC",
                "symptom_severity": severity,
            },
        },
    }


def _hazards(observation: dict[str, Any]) -> dict[str, tuple[float, float]]:
    """Pre- and post-recognition sick-call hazard per severity rung."""
    profiles = {
        PATHOGEN: {
            "severity_model": {
                "states": [
                    "asymptomatic",
                    "subclinical",
                    "mild",
                    "moderate",
                    "severe_critical",
                ],
                "base_probabilities": [0.25, 0.55, 0.19, 0.009, 0.001],
            },
            "observation_model": observation,
        },
    }
    surveillance = SyndromicSurveillance(
        background_noise_rate=0.0,
        symptom_severity_profiles=profiles,
        rng=np.random.default_rng(7),
    )
    return {
        severity: (
            surveillance._severity_hazard(
                _agent(severity), outbreak_recognized=False,
            ),
            surveillance._severity_hazard(
                _agent(severity), outbreak_recognized=True,
            ),
        )
        for severity in ("subclinical", "mild", "moderate", "severe_critical")
    }


class TestTheDeclarationSaysItIsOne:
    def test_the_observation_block_declares_its_class_and_its_source(
        self,
        profile: dict[str, Any],
    ) -> None:
        """A grade and prose, because none of these numbers was measured."""
        observation = profile["observation_model"]
        assert observation["evidence_grade"].startswith("C")
        notes = observation["notes"]
        assert "declared" in notes
        assert "not identified" in notes

    def test_uncertainty_is_carried_by_whole_ladders(
        self,
        profile: dict[str, Any],
    ) -> None:
        """More than one scenario, each complete, each with an origin."""
        prior = profile["observation_model"]["prior"]
        assert prior["type"] == "scenario_set"
        scenarios = prior["scenarios"]
        assert len(scenarios) >= 2
        for name, scenario in scenarios.items():
            assert set(scenario) == {*SCENARIO_VECTORS, "source"}, name
            assert scenario["source"].strip()

    def test_the_shipped_profile_runs_the_scenario_it_names(
        self,
        profile: dict[str, Any],
    ) -> None:
        _validate_symptom_severity_profiles({PATHOGEN: profile})


class TestAnIncoherentScenarioSetIsRefused:
    def test_an_unnamed_active_scenario_is_refused(
        self,
        profile: dict[str, Any],
    ) -> None:
        invalid = deepcopy(profile)
        invalid["observation_model"]["prior"]["active_scenario"] = "invented"
        with pytest.raises(ValueError, match="must name a declared scenario"):
            _validate_symptom_severity_profiles({PATHOGEN: invalid})

    def test_editing_the_vectors_beside_a_stale_name_is_refused(
        self,
        profile: dict[str, Any],
    ) -> None:
        """The failure this exists to catch: a free edit wearing a name."""
        invalid = deepcopy(profile)
        invalid["observation_model"][
            "reporting_probability_by_severity_post_recognition"
        ] = [0, 0.9, 0.95, 0.97, 1]
        with pytest.raises(ValueError, match="does not match scenario"):
            _validate_symptom_severity_profiles({PATHOGEN: invalid})

    def test_a_scenario_moving_only_one_vector_is_refused(
        self,
        profile: dict[str, Any],
    ) -> None:
        invalid = deepcopy(profile)
        partial = {
            "reporting_probability_by_severity_post_recognition": [
                0, 0.2, 0.5, 0.9, 1,
            ],
            "source": "a component sweep in a scenario's clothing",
        }
        invalid["observation_model"]["prior"]["scenarios"]["partial"] = partial
        with pytest.raises(ValueError, match="must have length 5"):
            _validate_symptom_severity_profiles({PATHOGEN: invalid})

    @pytest.mark.parametrize(
        ("mutation", "match"),
        [
            ({"type": "uniform_box"}, "must be 'scenario_set'"),
            ({"scenarios": {}}, "non-empty object"),
        ],
    )
    def test_a_prior_that_is_not_a_scenario_set_is_refused(
        self,
        profile: dict[str, Any],
        mutation: dict[str, Any],
        match: str,
    ) -> None:
        invalid = deepcopy(profile)
        invalid["observation_model"]["prior"].update(mutation)
        with pytest.raises(ValueError, match=match):
            _validate_symptom_severity_profiles({PATHOGEN: invalid})

    def test_an_impossible_ladder_inside_a_scenario_is_refused(
        self,
        profile: dict[str, Any],
    ) -> None:
        """A scenario is still an observation process: ordered, bounded."""
        invalid = deepcopy(profile)
        scenario = deepcopy(
            invalid["observation_model"]["prior"]["scenarios"]["base_reporting"],
        )
        scenario["reporting_probability_by_severity_post_recognition"] = [
            0, 0.9, 0.4, 0.96, 1,
        ]
        invalid["observation_model"]["prior"]["scenarios"]["inverted"] = scenario
        with pytest.raises(ValueError, match="non-decreasing"):
            _validate_symptom_severity_profiles({PATHOGEN: invalid})


class TestScenariosReachTheObserver:
    def test_each_declared_scenario_is_a_runnable_profile(
        self,
        profile: dict[str, Any],
    ) -> None:
        """Switching scenario resolves to a profile the loader accepts."""
        for name in profile["observation_model"]["prior"]["scenarios"]:
            patch = observation_scenario_patch(BUNDLE, PATHOGEN, name)
            resolved = apply_pathogen_overrides(
                {PATHOGEN: deepcopy(profile)},
                {PATHOGEN: {"observation_model": patch}},
            )
            _validate_symptom_severity_profiles(resolved)
            prior = resolved[PATHOGEN]["observation_model"]["prior"]
            assert prior["active_scenario"] == name
            assert len(prior["scenarios"]) == len(
                profile["observation_model"]["prior"]["scenarios"],
            )

    def test_an_undeclared_scenario_cannot_be_run(self) -> None:
        with pytest.raises(KeyError, match="declares no observation scenario"):
            observation_scenario_patch(BUNDLE, PATHOGEN, "wishful")

    def test_switching_scenario_moves_what_the_observer_records(
        self,
        profile: dict[str, Any],
    ) -> None:
        """The declaration has consequences, and they are where it argues.

        isolation_avoidance_post_recognition argues that anticipated cabin
        isolation suppresses mild presentation once an outbreak is known, and
        that severe cases stay hard to conceal. So the post-recognition hazard
        must fall on the mild rungs, hold at the top of the ladder, and the
        pre-recognition hazard must not move at all.
        """
        observation = profile["observation_model"]
        base = _hazards(observation)
        scenario = observation["prior"]["scenarios"][
            "isolation_avoidance_post_recognition"
        ]
        alternative = _hazards(
            {
                **observation,
                **{key: scenario[key] for key in SCENARIO_VECTORS},
            },
        )
        for severity in ("subclinical", "mild"):
            assert alternative[severity][1] < base[severity][1], severity
        assert alternative["severe_critical"][1] == pytest.approx(
            base["severe_critical"][1],
        )
        for severity, (pre, _post) in base.items():
            assert alternative[severity][0] == pytest.approx(pre), severity
