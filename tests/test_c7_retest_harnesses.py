"""Behaviour of the two C7 re-test harnesses.

The re-tests exist because their conclusions were drawn on a structure that
no longer exists, so what is fenced here is the reasoning each harness does
*after* the simulation: the decay window, the mechanism span, the plateau
verdict, and the role ratio's treatment of an empty denominator. Simulation
runs are not exercised; they are the slow part and they are not what these
functions decide.
"""

from __future__ import annotations

import math

import pytest

from scripts.alsved_airborne_check import (
    ALSVED_COPIES_PER_M3,
    as_implemented,
    containment,
    episode_aerosol_mass_gec,
    implied_volume,
    window_mean_factor,
)
from scripts.release_axis_role_retest import (
    SCORED_OUTPUTS,
    plateau_report,
    role_ratio,
    summarise,
    surveillance_overrides,
)

PROFILE = {
    "emesis_total_shed_gec_range": [1e5, 1e8],
    "emesis_episodes_range": [1, 7],
    "emesis_aerosol_fraction_range": [7.2e-7, 2.67e-4],
}


def _point(passenger: float, crew: float) -> dict[str, dict[str, float]]:
    values = {
        "ever_ill_attack_rate_passenger": passenger,
        "ever_ill_attack_rate_crew": crew,
        "reported_case_attack_rate_passenger": passenger,
        "reported_case_attack_rate_crew": crew,
    }
    return {
        name: {"mean": values.get(name, 0.0), "sd": 0.0, "values": []}
        for name in SCORED_OUTPUTS
    }


class TestWindowMeanFactor:
    """A decaying reservoir's mean over a window, as a factor of its peak."""

    def test_bounded_below_one(self) -> None:
        assert 0.0 < window_mean_factor(1.1, 3.0) < 1.0

    def test_longer_half_life_retains_more(self) -> None:
        factors = [window_mean_factor(h, 3.0) for h in (0.5, 1.1, 4.0, 24.0)]
        assert factors == sorted(factors)

    def test_approaches_one_for_slow_decay(self) -> None:
        assert window_mean_factor(1e6, 3.0) == pytest.approx(1.0, abs=1e-5)

    def test_one_half_life_window_is_analytic(self) -> None:
        # Mean of 2**(-t/h) over one half-life is 1 / (2 ln 2).
        assert window_mean_factor(2.0, 2.0) == pytest.approx(
            1.0 / (2.0 * math.log(2.0)),
        )

    def test_degenerate_inputs_do_not_decay(self) -> None:
        assert window_mean_factor(0.0, 3.0) == pytest.approx(1.0)
        assert window_mean_factor(1.1, 0.0) == pytest.approx(1.0)


class TestEpisodeAerosolMass:
    """The per-episode aerosolised mass spans the mechanism's endpoints."""

    def test_endpoints_are_ordered_and_wide(self) -> None:
        low, high = episode_aerosol_mass_gec(PROFILE)
        assert 0.0 < low < high
        # 3 logs of shed total, 0.85 log of episode count, 2.6 logs of
        # fraction: the span is the reason a single measured concentration
        # cannot discriminate inside it.
        assert math.log10(high / low) > 6.0

    def test_scales_linearly_with_the_fraction(self) -> None:
        doubled = dict(PROFILE, emesis_aerosol_fraction_range=[1.44e-6, 5.34e-4])
        base_low, base_high = episode_aerosol_mass_gec(PROFILE)
        low, high = episode_aerosol_mass_gec(doubled)
        assert low == pytest.approx(2.0 * base_low)
        assert high == pytest.approx(2.0 * base_high)

    def test_episode_count_only_partitions_the_total(self) -> None:
        single = dict(PROFILE, emesis_episodes_range=[1, 1])
        base_low, base_high = episode_aerosol_mass_gec(PROFILE)
        low, high = episode_aerosol_mass_gec(single)
        assert low == pytest.approx(7.0 * base_low)
        assert high == pytest.approx(base_high)

    def test_missing_keys_fall_back_to_engine_constants(self) -> None:
        assert episode_aerosol_mass_gec({}) == episode_aerosol_mass_gec(PROFILE)


class TestConcentrationComparison:
    """Dilution volume, not the fraction, decides the as-implemented answer."""

    def test_concentration_falls_with_volume(self) -> None:
        mass = (1.0, 1e4)
        wide = as_implemented(mass, {"min_m3": 900.0, "max_m3": 1200.0}, 1.0, 1.0)
        assert (
            wide["smallest_zone"]["instant_copies_per_m3_high"]
            > wide["largest_zone"]["instant_copies_per_m3_high"]
        )

    def test_ventilation_and_window_attenuate(self) -> None:
        volumes = {"min_m3": 900.0, "max_m3": 1200.0}
        plain = as_implemented((1.0, 1e4), volumes, 1.0, 1.0)
        damped = as_implemented((1.0, 1e4), volumes, 0.5, 0.5)
        assert damped["largest_zone"]["window_mean_copies_per_m3_high"] == (
            pytest.approx(
                0.25 * plain["largest_zone"]["window_mean_copies_per_m3_high"],
            )
        )

    def test_containment_tracks_the_measured_range(self) -> None:
        volumes = {"min_m3": 900.0, "max_m3": 1200.0}
        measured_low, measured_high = ALSVED_COPIES_PER_M3
        far_below = containment(as_implemented((1e-6, 1e-3), volumes, 1.0, 1.0))
        assert not far_below["largest_zone"]["overlaps_measured"]
        inside = containment(
            as_implemented((1.0, measured_high * 1200.0), volumes, 1.0, 1.0),
        )
        assert inside["largest_zone"]["overlaps_measured"]
        assert inside["largest_zone"]["ratio_high_to_measured_low"] == (
            pytest.approx(measured_high / measured_low)
        )

    def test_implied_volume_inverts_the_measurement(self) -> None:
        measured_low, measured_high = ALSVED_COPIES_PER_M3
        implied = implied_volume((10.0, 1000.0), 1.0)
        assert implied["low_m3"] == pytest.approx(10.0 / measured_high)
        assert implied["high_m3"] == pytest.approx(1000.0 / measured_low)
        assert implied["low_m3"] < implied["high_m3"]


class TestPlateauVerdict:
    """The plateau claim is a span against a seed spread, not a word."""

    def test_identical_output_is_reported_as_identical(self) -> None:
        per_value = {"8": _point(0.1, 0.05), "24": _point(0.1, 0.05)}
        report = plateau_report(per_value, 8.0)
        assert report["ever_ill_attack_rate_passenger"]["identical"]
        assert report["ever_ill_attack_rate_passenger"]["span"] == pytest.approx(0.0)

    def test_a_moving_axis_is_not_a_plateau(self) -> None:
        per_value = {"8": _point(0.30, 0.05), "24": _point(0.10, 0.05)}
        report = plateau_report(per_value, 8.0)["ever_ill_attack_rate_passenger"]
        assert not report["identical"]
        assert report["span"] == pytest.approx(0.20)

    def test_span_is_measured_against_the_top_seed_spread(self) -> None:
        per_value = {"8": _point(0.30, 0.05), "24": _point(0.10, 0.05)}
        per_value["24"]["ever_ill_attack_rate_passenger"]["sd"] = 0.05
        report = plateau_report(per_value, 8.0)["ever_ill_attack_rate_passenger"]
        assert report["span_over_floor"] == pytest.approx(4.0)

    def test_values_below_the_edge_are_excluded(self) -> None:
        per_value = {
            "4": _point(0.90, 0.05),
            "8": _point(0.10, 0.05),
            "24": _point(0.10, 0.05),
        }
        assert plateau_report(per_value, 8.0)[
            "ever_ill_attack_rate_passenger"
        ]["identical"]

    def test_no_value_above_the_edge_has_no_verdict(self) -> None:
        assert plateau_report({"4": _point(0.9, 0.05)}, 8.0) == {}


class TestRoleRatio:
    """An empty crew arm has no ratio, and must not be reported as parity."""

    def test_ratio_is_passenger_over_crew(self) -> None:
        ratios = role_ratio(_point(0.06, 0.02))
        assert ratios["ever_ill"] == pytest.approx(3.0)
        assert ratios["reported_case"] == pytest.approx(3.0)

    def test_inversion_is_reported_below_one(self) -> None:
        assert role_ratio(_point(0.02, 0.06))["ever_ill"] == pytest.approx(1 / 3)

    def test_zero_crew_yields_no_ratio(self) -> None:
        assert role_ratio(_point(0.06, 0.0))["ever_ill"] is None


class TestSurveillanceArms:
    """Arms come from the campaign manifest, not from restated overrides."""

    def test_shipped_arm_leaves_response_live(self) -> None:
        overrides = surveillance_overrides("syndromic")
        assert overrides["diagnostic_cascade"] == {"enabled": False}
        assert "observation" not in overrides

    def test_counterfactual_arm_disables_observation_and_response(self) -> None:
        overrides = surveillance_overrides("none_true")
        assert overrides["observation"] == {"enabled": False}
        assert overrides["syndromic"]["sick_call_probability"] == pytest.approx(0.0)

    def test_unknown_arm_is_refused(self) -> None:
        with pytest.raises(KeyError):
            surveillance_overrides("not_an_arm")


class TestSummarise:
    """Seed draws are summarised without being averaged away."""

    def test_mean_sd_and_draws_are_all_reported(self) -> None:
        draws = [
            {name: 0.2 for name in SCORED_OUTPUTS},
            {name: 0.4 for name in SCORED_OUTPUTS},
        ]
        point = summarise(draws)["attack_rate"]
        assert point["mean"] == pytest.approx(0.3)
        assert point["sd"] == pytest.approx(0.1414213562, rel=1e-6)
        assert point["values"] == [0.2, 0.4]

    def test_single_seed_has_no_spread(self) -> None:
        point = summarise([{name: 0.2 for name in SCORED_OUTPUTS}])["attack_rate"]
        assert point["sd"] == pytest.approx(0.0)
