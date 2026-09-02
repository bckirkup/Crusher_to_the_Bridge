from __future__ import annotations

import pytest

from engines.transmission_core import EMESIS_VOLUME_ML_RANGE
from telemetry_buffer.observation_model import bounded_screen

PATHOGEN = "norwalk_gi"


def _factor(name: str) -> bounded_screen.Factor:
    for factor in bounded_screen.NOROVIRUS_FACTORS:
        if factor.name == name:
            return factor
    raise AssertionError(f"factor {name!r} is not in the norovirus box")


def _units_at(name: str, unit: float) -> list[float]:
    return [
        unit if factor.name == name else 0.0
        for factor in bounded_screen.NOROVIRUS_FACTORS
    ]


def test_linear_factor_maps_unit_endpoints_to_the_interval() -> None:
    factor = _factor("innate_nonsusceptible_fraction")
    assert factor.value(0.0) == pytest.approx(factor.low)
    assert factor.value(1.0) == pytest.approx(factor.high)


def test_linear_factor_midpoint_is_the_arithmetic_mean() -> None:
    factor = _factor("innate_nonsusceptible_fraction")
    expected = 0.5 * (factor.low + factor.high)
    assert factor.value(0.5) == pytest.approx(expected)


def test_log10_factor_maps_unit_endpoints_to_the_interval() -> None:
    factor = _factor("emesis_titre_gec_per_ml")
    assert factor.value(0.0) == pytest.approx(factor.low)
    assert factor.value(1.0) == pytest.approx(factor.high)


def test_log10_factor_midpoint_is_the_geometric_mean() -> None:
    factor = _factor("emesis_titre_gec_per_ml")
    expected = (factor.low * factor.high) ** 0.5
    assert factor.value(0.5) == pytest.approx(expected)


def test_log10_factor_is_monotone_increasing_in_the_unit_coordinate() -> None:
    factor = _factor("emesis_titre_gec_per_ml")
    values = [factor.value(unit) for unit in (0.0, 0.25, 0.5, 0.75, 1.0)]
    assert values == sorted(values)


def test_overrides_land_under_the_pathogen_id() -> None:
    units = [0.5] * len(bounded_screen.NOROVIRUS_FACTORS)
    overrides = bounded_screen.build_overrides(
        bounded_screen.NOROVIRUS_FACTORS, units, PATHOGEN,
    )
    assert list(overrides) == [PATHOGEN]


def test_overrides_carry_every_factor_key() -> None:
    units = [0.5] * len(bounded_screen.NOROVIRUS_FACTORS)
    profile = bounded_screen.build_overrides(
        bounded_screen.NOROVIRUS_FACTORS, units, PATHOGEN,
    )[PATHOGEN]
    expected = {factor.path[0] for factor in bounded_screen.NOROVIRUS_FACTORS}
    assert set(profile) == expected


@pytest.mark.parametrize("unit", [0.0, 0.5, 1.0])
def test_indexed_emesis_pair_keeps_the_engine_lower_bound(unit: float) -> None:
    """The screened factor is the upper bound; the lower must not move.

    An earlier revision seeded the pair as [0.0, value], which silently moved
    emesis volume's lower bound from the engine default to zero on every
    design point.
    """
    factor = _factor("emesis_volume_ml_high")
    profile = bounded_screen.build_overrides(
        bounded_screen.NOROVIRUS_FACTORS,
        _units_at(factor.name, unit),
        PATHOGEN,
    )[PATHOGEN]
    pair = profile["emesis_volume_ml_range"]
    assert pair[0] == pytest.approx(EMESIS_VOLUME_ML_RANGE[0])


@pytest.mark.parametrize("unit", [0.0, 0.5, 1.0])
def test_indexed_emesis_pair_carries_the_screened_upper_bound(unit: float) -> None:
    factor = _factor("emesis_volume_ml_high")
    profile = bounded_screen.build_overrides(
        bounded_screen.NOROVIRUS_FACTORS,
        _units_at(factor.name, unit),
        PATHOGEN,
    )[PATHOGEN]
    pair = profile["emesis_volume_ml_range"]
    assert pair[1] == pytest.approx(factor.value(unit))


def test_unrecorded_indexed_key_raises_rather_than_defaulting() -> None:
    unknown = bounded_screen.Factor(
        name="unknown_pair_high",
        path=("unknown_pair", 1),
        low=1.0,
        high=2.0,
        transform="linear",
        grade="D",
    )
    with pytest.raises(KeyError, match="unknown_pair"):
        bounded_screen.build_overrides([unknown], [0.5], PATHOGEN)
