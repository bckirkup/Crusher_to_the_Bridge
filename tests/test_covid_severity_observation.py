"""The SARS-CoV-2 severity and observation models (#31).

Two seams enter the tree with this arm, and the tests below are about the
seams rather than the numbers: severity now reads the host's age band, and
PCR positivity now reads the day of infection a specimen was taken on. Both
are graded sweeps — a band ladder and a day ladder — because a golden on
either would pass on a knob that had stopped being read.

The shipped values themselves are checked only as contracts (distributions
that sum, denominators that agree, refusals that stay refused), never as
change-detectors: the register owns their provenance.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from crusher_labs.modalities.syndromic import SyndromicSurveillance
from engines.natural_history import (
    draw_symptom_severity,
    host_age_band,
    severity_probabilities,
)
from orchestrator_init import _validate_symptom_severity_profiles

REPO_ROOT = Path(__file__).resolve().parent.parent
PATHOGEN = "sars_cov2_resp"
_STATES = [
    "asymptomatic", "subclinical", "mild", "moderate", "severe_critical",
]
# Oldest first, so an assertion reads in the direction severity moves.
_BANDS_OLDEST_FIRST = ["75+", "senior", "55+", "50-64", "adult", "18-24", "5-17"]


def _shipped(pathogen_id: str = PATHOGEN) -> dict[str, Any]:
    path = REPO_ROOT / "data" / "pathogens" / "active_profiles.json"
    with path.open(encoding="utf-8") as handle:
        profiles = json.load(handle)["pathogens"]
    return next(
        profile for profile in profiles
        if profile["pathogen_id"] == pathogen_id
    )


def _severe_share(profile: dict[str, Any], band: str, draws: int = 4000) -> float:
    rng = np.random.default_rng(11)
    severe = sum(
        draw_symptom_severity(profile, rng, band) == "severe_critical"
        for _ in range(draws)
    )
    return severe / draws


class TestShippedSeverityContract:
    def test_the_ladder_is_a_distribution_in_every_band(self) -> None:
        severity = _shipped()["severity_model"]

        assert severity["states"] == _STATES
        vectors = [severity["base_probabilities"]]
        vectors += list(severity["base_probabilities_by_age_band"].values())
        for vector in vectors:
            assert len(vector) == 5
            assert all(0.0 <= float(value) <= 1.0 for value in vector)
            assert sum(float(value) for value in vector) == pytest.approx(1.0)

    def test_a_band_moves_the_case_mix_and_never_the_presenting_fraction(
        self,
    ) -> None:
        """The draw renormalises over the symptomatic states.

        A band whose asymptomatic entry differed from the reference vector's
        would declare a presenting fraction the draw then discards, so the
        band could silently disagree with ``symptomatic_fraction`` in a way
        no output would show.
        """
        profile = _shipped()
        severity = profile["severity_model"]
        asymptomatic = float(severity["base_probabilities"][0])

        assert profile["symptomatic_fraction"] == pytest.approx(
            1.0 - asymptomatic,
        )
        for vector in severity["base_probabilities_by_age_band"].values():
            assert float(vector[0]) == pytest.approx(asymptomatic)

    def test_the_dose_conditional_presentation_mechanism_is_gone(self) -> None:
        """#31 replaces the Hill pair with a measured proportion.

        Both keys at once is two parameterisations of one quantity, and the
        arm's own value was an unattributed near-neighbour of norovirus's.
        """
        profile = _shipped()

        assert "illness_probability" not in profile
        assert 0.0 < profile["symptomatic_fraction"] < 1.0

    def test_the_refuted_asymptomatic_shedding_offset_is_a_null(self) -> None:
        profile = _shipped()

        assert (
            profile["asymptomatic_shedding_log10"]
            == profile["shedding_curve_log10"]
        )
        assert "REFUTED" in profile["asymptomatic_shedding_notes"]

    def test_the_arm_declares_one_pcr_sensitivity_parameterisation(self) -> None:
        observation = _shipped()["observation_model"]
        curve = observation["assay_sensitivity_by_time_since_infection"]

        assert observation.get("assay_sensitivity") is None
        assert len(curve) > 1
        assert all(0.0 <= float(value) <= 1.0 for value in curve)
        # Detectability rises to a peak and decays; it is not monotone, so
        # what is asserted is the shape's two ends against its interior.
        assert max(curve) > curve[0]
        assert max(curve) > curve[-1]

    def test_active_screening_is_off_so_the_baseline_stays_passive(
        self,
    ) -> None:
        """The campaigns the scored hulls ran are #33's, not this profile's.

        Diamond Princess tested daily and Greg Mortimer tested ship-wide;
        both reach hosts who never presented. Baking them into the sampling
        vector here would make the held-out score circular.
        """
        observation = _shipped()["observation_model"]

        assert observation["active_screening"]["enabled"] is False
        assert observation["syndrome_case_eligibility_by_severity"][0] == (
            pytest.approx(0.0)
        )


class TestAgeConditionedSeverityDraw:
    def test_severe_share_grades_with_the_band_ladder(self) -> None:
        profile = _shipped()
        shares = [_severe_share(profile, band) for band in _BANDS_OLDEST_FIRST]

        assert shares == sorted(shares, reverse=True)
        assert shares[0] - shares[-1] > 0.05
        assert shares[0] > 3.0 * shares[-1]

    def test_the_declared_vector_is_what_an_unnamed_band_reads(self) -> None:
        severity = _shipped()["severity_model"]

        assert severity_probabilities(severity, "band_no_config_declares") == (
            [float(value) for value in severity["base_probabilities"]]
        )
        assert severity_probabilities(severity, "") == (
            [float(value) for value in severity["base_probabilities"]]
        )

    def test_a_flat_profile_still_draws_from_its_one_vector(self) -> None:
        """Compatibility: the age ladder is optional, not required."""
        flat = {
            "severity_model": {
                "states": _STATES,
                "base_probabilities": [0.25, 0.55, 0.19, 0.009, 0.001],
            },
        }
        rng = np.random.default_rng(3)
        drawn = {draw_symptom_severity(flat, rng, "75+") for _ in range(200)}

        assert drawn <= set(_STATES[1:])
        assert "subclinical" in drawn

    def test_the_draw_never_returns_the_asymptomatic_state(self) -> None:
        profile = _shipped()
        rng = np.random.default_rng(5)
        drawn = {
            draw_symptom_severity(profile, rng, band)
            for band in _BANDS_OLDEST_FIRST for _ in range(200)
        }

        assert drawn <= set(_STATES[1:])
        assert "asymptomatic" not in drawn

    def test_a_host_without_a_band_reads_the_declared_vector(self) -> None:
        class BareHost:
            """The minimal host the presentation draw is exercised with."""

        class BandedHost:
            age_band = "75+"

        assert host_age_band(BareHost()) == ""
        assert host_age_band(BandedHost()) == "75+"


def _specimen_profile(
    curve: list[float] | None = None,
    scalar: float | None = None,
) -> dict[str, dict[str, Any]]:
    observation: dict[str, Any] = {
        "lab_sampling_probability_by_severity": [0.0, 0.0, 1.0, 1.0, 1.0],
    }
    if curve is not None:
        observation["assay_sensitivity_by_time_since_infection"] = curve
    if scalar is not None:
        observation["assay_sensitivity"] = scalar
    return {
        PATHOGEN: {
            "severity_model": {"states": _STATES},
            "observation_model": observation,
        },
    }


def _positive_share(
    profile: dict[str, dict[str, Any]],
    epochs_infected: int,
    agents: int = 400,
) -> float:
    population = [
        {
            "agent_id": aid,
            "pathogen_infections": {
                PATHOGEN: {
                    "status": "INFECTED",
                    "illness": "SYMPTOMATIC",
                    "symptom_severity": "mild",
                    "time_infected": epochs_infected,
                },
            },
        }
        for aid in range(agents)
    ]
    surveillance = SyndromicSurveillance(
        symptom_severity_profiles=profile,
        rng=np.random.default_rng(7),
    )
    result = surveillance.collect_specimens(
        population, 1, [agent["agent_id"] for agent in population],
    )
    return result["lab_confirmed_count"] / max(result["lab_sampled_count"], 1)


class TestTimeVaryingAssaySensitivity:
    _CURVE = [0.0, 0.2, 0.4, 0.6, 0.8]

    def test_positivity_grades_with_the_day_the_specimen_is_taken(self) -> None:
        profile = _specimen_profile(curve=self._CURVE)
        shares = [_positive_share(profile, day) for day in range(5)]

        assert shares == sorted(shares)
        assert shares[0] == pytest.approx(0.0)
        assert shares[-1] > 0.6
        for day, share in enumerate(shares[1:], start=1):
            assert share == pytest.approx(self._CURVE[day], abs=0.08)

    def test_the_last_entry_is_held_past_the_end_of_the_curve(self) -> None:
        """Like a shedding curve, so a long infection stays detectable."""
        profile = _specimen_profile(curve=self._CURVE)
        tail = [_positive_share(profile, day) for day in (4, 9, 30)]

        assert tail[0] == pytest.approx(tail[1], abs=0.06)
        assert tail[1] == pytest.approx(tail[2], abs=0.06)

    def test_a_scalar_profile_is_flat_in_time(self) -> None:
        """Negative control: the day axis is inert without a curve."""
        profile = _specimen_profile(scalar=0.5)
        shares = [_positive_share(profile, day) for day in (0, 4, 30)]

        assert max(shares) - min(shares) < 0.08
        assert all(0.35 < share < 0.65 for share in shares)

    def test_an_uninfected_host_never_tests_positive(self) -> None:
        profile = _specimen_profile(curve=[1.0, 1.0, 1.0])
        population = [
            {
                "agent_id": 1,
                "pathogen_infections": {
                    PATHOGEN: {
                        "status": "EXPOSED",
                        "illness": "SYMPTOMATIC",
                        "symptom_severity": "mild",
                        "time_infected": 1,
                    },
                },
            },
        ]
        surveillance = SyndromicSurveillance(
            symptom_severity_profiles=profile,
            rng=np.random.default_rng(9),
        )
        result = surveillance.collect_specimens(population, 1, [1])

        assert result["lab_confirmed_count"] == 0


def _authored(**observation: Any) -> dict[str, dict[str, Any]]:
    model: dict[str, Any] = {
        "syndrome_case_eligibility_by_severity": [0.0, 0.0, 1.0, 1.0, 1.0],
        "reporting_probability_by_severity_pre_recognition": [
            0.0, 0.0, 0.2, 0.7, 1.0,
        ],
        "reporting_probability_by_severity_post_recognition": [
            0.0, 0.0, 0.4, 0.9, 1.0,
        ],
        "lab_sampling_probability_by_severity": [0.0, 0.0, 0.5, 0.9, 1.0],
        "episode_reporting_window_days": 7.0,
    }
    model.update(observation)
    return {
        PATHOGEN: {
            "severity_model": {
                "states": _STATES,
                "base_probabilities": [0.31, 0.0, 0.669, 0.0164, 0.0046],
            },
            "observation_model": model,
        },
    }


class TestLoaderRefusals:
    def test_the_shipped_arm_loads(self) -> None:
        _validate_symptom_severity_profiles({PATHOGEN: _shipped()})

    def test_a_curve_beside_a_scalar_is_refused(self) -> None:
        profiles = _authored(
            assay_sensitivity=0.8,
            assay_sensitivity_by_time_since_infection=[0.1, 0.9],
        )
        with pytest.raises(ValueError, match="one quantity"):
            _validate_symptom_severity_profiles(profiles)

    @pytest.mark.parametrize("curve", [[], [0.5, 1.4], [0.5, -0.1]])
    def test_a_curve_that_is_not_probabilities_is_refused(
        self, curve: list[float],
    ) -> None:
        with pytest.raises(ValueError, match="assay_sensitivity"):
            _validate_symptom_severity_profiles(
                _authored(assay_sensitivity_by_time_since_infection=curve),
            )

    def test_an_unimplemented_curve_shape_stays_unimplemented(self) -> None:
        with pytest.raises(NotImplementedError, match="assay"):
            _validate_symptom_severity_profiles(
                _authored(
                    assay_sensitivity_by_time_since_infection={"day_1": 0.4},
                ),
            )

    def test_a_band_that_moves_the_asymptomatic_share_is_refused(self) -> None:
        profiles = _authored()
        profiles[PATHOGEN]["severity_model"]["base_probabilities_by_age_band"] = {
            "75+": [0.20, 0.0, 0.60, 0.15, 0.05],
        }
        with pytest.raises(ValueError, match="case mix"):
            _validate_symptom_severity_profiles(profiles)

    def test_a_band_vector_that_is_not_a_distribution_is_refused(self) -> None:
        profiles = _authored()
        profiles[PATHOGEN]["severity_model"]["base_probabilities_by_age_band"] = {
            "75+": [0.31, 0.0, 0.60, 0.15, 0.05],
        }
        with pytest.raises(ValueError, match="sum to 1.0"):
            _validate_symptom_severity_profiles(profiles)
