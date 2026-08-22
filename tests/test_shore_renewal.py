"""Shore importation interface and linear renewal properties.

The renewal is linear, so it has exact analytic properties (total cases equal
``imports / (1 - R)`` at long horizon, and totals scale exactly with the
importation multiplier).  Those are asserted directly rather than pinned to
golden numbers.
"""

from __future__ import annotations

import numpy as np
import pytest

from picard_framework.analysis.shore import (
    DEPLETION_FRACTION,
    PortCallImportation,
    ShoreRenewalParameters,
    renewal_by_strain,
    renewal_result,
    renewal_trajectory,
)

EPOCH_HOURS = 24.0
LONG_HORIZON = 400


def _params(**overrides: float) -> ShoreRenewalParameters:
    base: dict[str, float] = {
        "r_shore": 0.5,
        "generation_median_hours": 48.0,
        "generation_sigma": 0.6,
        "generation_max_hours": 336.0,
        "population": 200_000,
    }
    base.update(overrides)
    return ShoreRenewalParameters(**base)  # type: ignore[arg-type]


def _pulse(
    *,
    rate: float = 3.0,
    window: int = 5,
    horizon: int = LONG_HORIZON,
    detection: int | None = 5,
) -> PortCallImportation:
    series = tuple(rate if epoch < window else 0.0 for epoch in range(horizon))
    return PortCallImportation(
        port_id="TESTPORT",
        pathogen_id="norwalk_gi",
        epoch_hours=EPOCH_HOURS,
        strain_importations={
            "GII.4": series,
            "GII.17": tuple(0.5 * value for value in series),
        },
        ship_detection_epoch=detection,
    )


class TestImportationValidation:
    """The ship interface refuses inputs it cannot honestly propagate."""

    def test_negative_importations_rejected(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            PortCallImportation(
                port_id="P",
                pathogen_id="norwalk_gi",
                epoch_hours=EPOCH_HOURS,
                strain_importations={"A": (1.0, -1.0)},
                ship_detection_epoch=0,
            )

    def test_non_finite_importations_rejected(self) -> None:
        with pytest.raises(ValueError, match="finite"):
            PortCallImportation(
                port_id="P",
                pathogen_id="norwalk_gi",
                epoch_hours=EPOCH_HOURS,
                strain_importations={"A": (1.0, float("nan"))},
                ship_detection_epoch=0,
            )

    def test_unequal_series_lengths_rejected(self) -> None:
        with pytest.raises(ValueError, match="equal length"):
            PortCallImportation(
                port_id="P",
                pathogen_id="norwalk_gi",
                epoch_hours=EPOCH_HOURS,
                strain_importations={"A": (1.0, 1.0), "B": (1.0,)},
                ship_detection_epoch=0,
            )

    def test_empty_strain_label_rejected(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            PortCallImportation(
                port_id="P",
                pathogen_id="norwalk_gi",
                epoch_hours=EPOCH_HOURS,
                strain_importations={"": (1.0,)},
                ship_detection_epoch=0,
            )

    def test_blank_port_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="port_id"):
            PortCallImportation(
                port_id="",
                pathogen_id="norwalk_gi",
                epoch_hours=EPOCH_HOURS,
                strain_importations={"A": (1.0,)},
                ship_detection_epoch=0,
            )

    def test_blank_pathogen_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="pathogen_id"):
            PortCallImportation(
                port_id="P",
                pathogen_id="",
                epoch_hours=EPOCH_HOURS,
                strain_importations={"A": (1.0,)},
                ship_detection_epoch=0,
            )

    def test_non_positive_epoch_hours_rejected(self) -> None:
        with pytest.raises(ValueError, match="epoch_hours"):
            PortCallImportation(
                port_id="P",
                pathogen_id="norwalk_gi",
                epoch_hours=0.0,
                strain_importations={"A": (1.0,)},
                ship_detection_epoch=0,
            )

    def test_negative_detection_epoch_rejected(self) -> None:
        with pytest.raises(ValueError, match="ship_detection_epoch"):
            PortCallImportation(
                port_id="P",
                pathogen_id="norwalk_gi",
                epoch_hours=EPOCH_HOURS,
                strain_importations={"A": (1.0,)},
                ship_detection_epoch=-1,
            )


class TestImportationHelpers:
    """Derived quantities on the ship interface."""

    def test_totals_and_horizon(self) -> None:
        importation = _pulse(rate=2.0, window=4, horizon=10)
        assert importation.horizon == 10
        assert importation.total_importations == pytest.approx(12.0)
        assert importation.total_by_strain["GII.4"] == pytest.approx(8.0)
        assert importation.total_by_strain["GII.17"] == pytest.approx(4.0)

    def test_combined_is_the_strain_sum(self) -> None:
        importation = _pulse(rate=2.0, window=4, horizon=10)
        expected = np.array([3.0] * 4 + [0.0] * 6)
        np.testing.assert_allclose(importation.combined(), expected)

    def test_empty_strain_map_is_legal(self) -> None:
        importation = PortCallImportation(
            port_id="P",
            pathogen_id="norwalk_gi",
            epoch_hours=EPOCH_HOURS,
            strain_importations={},
            ship_detection_epoch=None,
        )
        assert importation.horizon == 0
        assert importation.total_importations == pytest.approx(0.0)
        assert importation.combined().size == 0

    def test_mapping_round_trip(self) -> None:
        importation = _pulse(horizon=8)
        rebuilt = PortCallImportation.from_mapping(importation.as_dict())
        assert rebuilt == importation

    def test_round_trip_without_detection_epoch(self) -> None:
        importation = _pulse(horizon=8, detection=None)
        rebuilt = PortCallImportation.from_mapping(importation.as_dict())
        assert rebuilt.ship_detection_epoch is None
        assert rebuilt == importation


class TestParameterValidation:
    """``R_shore`` and the generation interval are required, not defaulted."""

    def test_r_shore_is_required(self) -> None:
        with pytest.raises(TypeError):
            ShoreRenewalParameters(  # type: ignore[call-arg]
                generation_median_hours=48.0,
                generation_sigma=0.6,
                generation_max_hours=336.0,
                population=1000,
            )

    def test_negative_r_shore_rejected(self) -> None:
        with pytest.raises(ValueError, match="r_shore"):
            _params(r_shore=-0.1)

    def test_non_positive_generation_median_rejected(self) -> None:
        with pytest.raises(ValueError, match="generation_median_hours"):
            _params(generation_median_hours=0.0)

    def test_non_positive_generation_sigma_rejected(self) -> None:
        with pytest.raises(ValueError, match="generation_sigma"):
            _params(generation_sigma=0.0)

    def test_non_positive_generation_max_rejected(self) -> None:
        with pytest.raises(ValueError, match="generation_max_hours"):
            _params(generation_max_hours=-1.0)

    def test_non_finite_parameter_rejected(self) -> None:
        with pytest.raises(ValueError, match="finite"):
            _params(r_shore=float("inf"))

    def test_population_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match="population"):
            _params(population=0)

    def test_generation_distribution_is_a_normalised_pmf(self) -> None:
        distribution = _params().generation_distribution(EPOCH_HOURS)
        assert sum(distribution.pmf) == pytest.approx(1.0)


class TestRenewalProperties:
    """Exact analytic consequences of a linear renewal."""

    @pytest.mark.parametrize("r_shore", [0.0, 0.3, 0.5, 0.7])
    def test_total_matches_geometric_sum(self, r_shore: float) -> None:
        importation = _pulse()
        result = renewal_result(importation, _params(r_shore=r_shore))
        expected = importation.total_importations / (1.0 - r_shore)
        assert result.total_cases == pytest.approx(expected, rel=1e-6)

    def test_totals_scale_linearly_in_importations(self) -> None:
        params = _params(r_shore=0.6)
        base = renewal_result(_pulse(rate=3.0), params).total_cases
        tripled = renewal_result(_pulse(rate=9.0), params).total_cases
        assert tripled == pytest.approx(3.0 * base)

    def test_trajectory_scales_linearly_epoch_by_epoch(self) -> None:
        params = _params(r_shore=0.6)
        base = renewal_result(_pulse(rate=3.0), params).trajectory
        tripled = renewal_result(_pulse(rate=9.0), params).trajectory
        np.testing.assert_allclose(tripled, 3.0 * base, rtol=1e-12, atol=1e-12)

    def test_zero_importations_give_zero_cases(self) -> None:
        result = renewal_result(_pulse(rate=0.0), _params(r_shore=0.9))
        assert result.total_cases == pytest.approx(0.0)
        assert result.attack_fraction == pytest.approx(0.0)
        assert not result.depletion_regime

    def test_empty_strain_map_gives_an_empty_trajectory(self) -> None:
        importation = PortCallImportation(
            port_id="P",
            pathogen_id="norwalk_gi",
            epoch_hours=EPOCH_HOURS,
            strain_importations={},
            ship_detection_epoch=None,
        )
        result = renewal_result(importation, _params())
        assert result.trajectory.size == 0
        assert result.total_cases == pytest.approx(0.0)
        assert result.total_by_strain == {}

    def test_single_epoch_horizon_has_no_secondary_cases(self) -> None:
        importation = PortCallImportation(
            port_id="P",
            pathogen_id="norwalk_gi",
            epoch_hours=EPOCH_HOURS,
            strain_importations={"A": (4.0,)},
            ship_detection_epoch=0,
        )
        result = renewal_result(importation, _params(r_shore=0.9))
        assert result.total_cases == pytest.approx(4.0)

    def test_r_shore_at_least_one_is_flagged_unbounded(self) -> None:
        result = renewal_result(_pulse(horizon=60), _params(r_shore=1.2))
        assert result.unbounded_growth

    def test_sub_critical_r_shore_is_not_flagged_unbounded(self) -> None:
        result = renewal_result(_pulse(horizon=60), _params(r_shore=0.99))
        assert not result.unbounded_growth

    def test_depletion_regime_flags_a_large_attack_fraction(self) -> None:
        params = _params(r_shore=0.5, population=10)
        result = renewal_result(_pulse(horizon=60), params)
        assert result.attack_fraction > DEPLETION_FRACTION
        assert result.depletion_regime

    def test_small_attack_fraction_is_not_flagged(self) -> None:
        result = renewal_result(_pulse(horizon=60), _params(r_shore=0.5))
        assert result.attack_fraction < DEPLETION_FRACTION
        assert not result.depletion_regime

    def test_trajectory_helper_matches_the_strain_sum(self) -> None:
        importation = _pulse(horizon=60)
        params = _params(r_shore=0.4)
        combined = renewal_trajectory(
            importation.combined(),
            params,
            epoch_hours=importation.epoch_hours,
        )
        by_strain = renewal_by_strain(importation, params)
        stacked = sum(by_strain.values())
        np.testing.assert_allclose(combined, stacked, rtol=1e-12, atol=1e-12)


class TestInvariants:
    """Bounds that must hold at a realistic horizon."""

    @pytest.mark.parametrize("r_shore", [0.0, 0.4, 0.8, 1.1])
    def test_trajectories_are_non_negative_and_finite(self, r_shore: float) -> None:
        result = renewal_result(_pulse(horizon=120), _params(r_shore=r_shore))
        assert np.all(result.trajectory >= 0.0)
        assert np.all(np.isfinite(result.trajectory))

    def test_per_strain_totals_sum_to_the_combined_total(self) -> None:
        result = renewal_result(_pulse(horizon=120), _params(r_shore=0.6))
        assert sum(result.total_by_strain.values()) == pytest.approx(result.total_cases)

    def test_attack_fraction_matches_total_over_population(self) -> None:
        params = _params(r_shore=0.6, population=5_000)
        result = renewal_result(_pulse(horizon=120), params)
        assert result.attack_fraction == pytest.approx(result.total_cases / 5_000)
