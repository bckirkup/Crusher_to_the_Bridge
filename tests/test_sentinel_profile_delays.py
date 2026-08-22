"""The sentinel incubation catalog is a projection of the pathogen profiles.

Two representations of the same quantity drifted apart once already (catalog
norovirus median 33 h against a profile median of 28.8 h), and nothing failed.
These tests are the thing that fails: the unit conversion is pinned, the drift
check is run against the shipped bundle and the shipped catalog, and every
projected field is shown to move the resulting pmf, so a stale catalog cannot
pass by matching on the fields that do not matter.
"""

from __future__ import annotations

import copy
import math
from typing import Any

import pytest

from picard_framework.analysis.sentinel.incubation import (
    LOGNORMAL,
    delays_for_pathogen,
    load_delay_catalog,
    lognormal_delay,
)
from picard_framework.analysis.sentinel.profile_delays import (
    HOURS_PER_DAY,
    active_profiles,
    incubation_delay_for_profile,
    incubation_drift,
    project_incubation,
)

PROFILE_INCUBATION = {
    "distribution": "lognormal",
    "median_days": 1.2,
    "dispersion": 1.56,
    "min_days": 0.1,
    "max_days": 6.0,
}


def profile(**overrides: Any) -> dict[str, Any]:
    """A minimal profile carrying an incubation block."""
    incubation = dict(PROFILE_INCUBATION)
    incubation.update(overrides)
    return {"pathogen_id": "test_pathogen", "incubation": incubation}


# --- the unit conversion itself ------------------------------------------------


def test_projection_converts_days_to_hours_and_gsd_to_log_sigma() -> None:
    """The one conversion this module exists to state."""
    spec = project_incubation(PROFILE_INCUBATION, pathogen_id="test_pathogen")
    assert spec["family"] == LOGNORMAL
    assert spec["median_hours"] == pytest.approx(1.2 * HOURS_PER_DAY)
    assert spec["sigma"] == pytest.approx(math.log(1.56))
    assert spec["min_hours"] == pytest.approx(0.1 * HOURS_PER_DAY)
    assert spec["max_hours"] == pytest.approx(6.0 * HOURS_PER_DAY)


def test_dispersion_is_geometric_not_log_scale() -> None:
    """A GSD read as a log-sigma would inflate the kernel ~3.5x here.

    Guards the one substitution that silently produces a plausible pmf: the
    projected sigma must be log(1.56)=0.45, not 1.56.
    """
    spec = project_incubation(PROFILE_INCUBATION, pathogen_id="test_pathogen")
    assert spec["sigma"] < 1.0
    assert spec["sigma"] != pytest.approx(PROFILE_INCUBATION["dispersion"])


def test_missing_bounds_fall_back_to_the_simulator_defaults() -> None:
    """A profile that omits min/max gets the engine's clamps, not zero/infinity."""
    sparse = {"median_days": 2.0, "dispersion": 1.5}
    spec = project_incubation(sparse, pathogen_id="sparse")
    assert spec["min_hours"] == pytest.approx(0.5 * HOURS_PER_DAY)
    assert spec["max_hours"] == pytest.approx(30.0 * HOURS_PER_DAY)


def test_gamma_profile_refuses_to_project() -> None:
    """The catalog is lognormal-only; a gamma profile needs a recorded decision."""
    with pytest.raises(ValueError, match="lognormal-only"):
        project_incubation(
            {"distribution": "gamma", "median_days": 1.2, "dispersion": 1.5},
            pathogen_id="gamma_pathogen",
        )


def test_missing_median_refuses_to_project() -> None:
    with pytest.raises(ValueError, match="median_days"):
        project_incubation({"dispersion": 1.5}, pathogen_id="no_median")


@pytest.mark.parametrize("dispersion", [1.0, 0.45])
def test_dispersion_at_or_below_one_refuses_to_project(dispersion: float) -> None:
    """A dispersion <= 1 is a log-sigma pasted into a GSD field."""
    with pytest.raises(ValueError, match="geometric standard deviation"):
        project_incubation(
            {"median_days": 1.2, "dispersion": dispersion},
            pathogen_id="bad_dispersion",
        )


def test_profile_without_incubation_block_has_no_kernel() -> None:
    """13 of 15 shipped profiles are still fixed-onset; that must be explicit."""
    with pytest.raises(ValueError, match="no incubation block"):
        incubation_delay_for_profile({"pathogen_id": "legacy"})


# --- different inputs, different pmfs -----------------------------------------


def test_a_longer_median_shifts_the_kernel_later() -> None:
    fast = incubation_delay_for_profile(profile(median_days=1.2))
    slow = incubation_delay_for_profile(profile(median_days=2.4))
    assert slow.quantile_hours(0.5) > fast.quantile_hours(0.5)
    assert slow.mean_hours > fast.mean_hours


def test_a_wider_dispersion_widens_the_kernel() -> None:
    tight = incubation_delay_for_profile(profile(dispersion=1.2))
    wide = incubation_delay_for_profile(profile(dispersion=2.2))
    assert wide.iqr_hours > tight.iqr_hours


def test_the_minimum_removes_early_mass() -> None:
    """Left truncation is real: mass below min_days is gone, not squeezed in."""
    unbounded = incubation_delay_for_profile(profile(min_days=0.0))
    floored = incubation_delay_for_profile(profile(min_days=0.75))
    assert unbounded.weight_at(0) > 0.0
    # 0.75 d = 18 h, so the first 18 one-hour bins must be empty.
    assert floored.mass_within(17) == pytest.approx(0.0)
    assert floored.quantile_hours(0.5) > unbounded.quantile_hours(0.5)


def test_the_maximum_truncates_the_tail() -> None:
    short = incubation_delay_for_profile(profile(max_days=3.0))
    long = incubation_delay_for_profile(profile(max_days=12.0))
    assert short.max_lag < long.max_lag
    assert short.mean_hours < long.mean_hours


def test_a_coarser_epoch_grid_keeps_the_distribution_it_discretizes() -> None:
    """The grid is a property of the run, so hours must survive regridding."""
    hourly = incubation_delay_for_profile(profile(), epoch_hours=1.0)
    six_hourly = incubation_delay_for_profile(profile(), epoch_hours=6.0)
    assert six_hourly.max_lag < hourly.max_lag
    assert six_hourly.mean_hours == pytest.approx(hourly.mean_hours, rel=0.15)


def test_left_truncation_is_conditional_not_renormalized_away() -> None:
    """A floored pmf still sums to 1 and is stochastically later throughout."""
    floored = incubation_delay_for_profile(profile(min_days=0.5))
    assert sum(floored.pmf) == pytest.approx(1.0)
    unbounded = incubation_delay_for_profile(profile(min_days=0.0))
    for lag in (12, 24, 36):
        assert floored.mass_within(lag) <= unbounded.mass_within(lag) + 1e-12


def test_min_hours_beyond_max_hours_is_rejected() -> None:
    with pytest.raises(ValueError, match="no support"):
        lognormal_delay(
            name="inverted",
            median_hours=28.8,
            sigma=0.44,
            epoch_hours=1.0,
            min_hours=200.0,
            max_hours=144.0,
        )


def test_negative_min_hours_is_rejected() -> None:
    with pytest.raises(ValueError, match="must not be negative"):
        lognormal_delay(
            name="negative",
            median_hours=28.8,
            sigma=0.44,
            epoch_hours=1.0,
            min_hours=-1.0,
            max_hours=144.0,
        )


# --- drift ---------------------------------------------------------------------


def test_the_shipped_catalog_matches_the_shipped_profiles() -> None:
    """The check this module exists for. Edit the profile, re-project, not this."""
    drift = incubation_drift(load_delay_catalog(), active_profiles())
    assert drift == (), "\n".join(drift)


def test_the_catalog_kernel_and_the_profile_kernel_are_the_same_pmf() -> None:
    """Same claim, checked through the two code paths that build a pmf.

    Bin masses agree to ~1e-8: the catalog's sigma is rounded to six decimals
    for readability, which is the same slack ``DRIFT_RTOL`` allows.
    """
    profiles = active_profiles()
    catalog = load_delay_catalog()
    for name, entry in catalog["distributions"].items():
        pathogen_id = entry.get("pathogen_id")
        if not pathogen_id:
            continue
        from_catalog = delays_for_pathogen(name, catalog=catalog)[0]
        from_profile = incubation_delay_for_profile(profiles[pathogen_id])
        assert from_catalog.pmf == pytest.approx(from_profile.pmf, abs=1e-6), name


def test_a_profile_edit_is_reported_as_drift() -> None:
    """The failure mode: profile moves, catalog does not."""
    profiles = copy.deepcopy(active_profiles())
    profiles["norwalk_gi"]["incubation"]["median_days"] = 2.0
    drift = incubation_drift(load_delay_catalog(), profiles)
    assert any("median_hours" in message for message in drift), drift


def test_each_projected_field_is_drift_checked() -> None:
    """Every field of the projection, one at a time, so none is decorative."""
    profiles = active_profiles()
    catalog = copy.deepcopy(load_delay_catalog())
    entry = catalog["distributions"]["norovirus"]["incubation"]
    for field, value in (
        ("median_hours", 33.0),
        ("sigma", 0.42),
        ("min_hours", 6.0),
        ("max_hours", 120.0),
        ("family", "discrete"),
    ):
        mutated = copy.deepcopy(catalog)
        mutated["distributions"]["norovirus"]["incubation"][field] = value
        drift = incubation_drift(mutated, profiles)
        assert any(field in message for message in drift), (
            f"{field}: catalog {entry[field]} -> {value} was not reported"
        )


def test_a_dropped_catalog_field_is_drift_not_a_default() -> None:
    catalog = copy.deepcopy(load_delay_catalog())
    del catalog["distributions"]["norovirus"]["incubation"]["min_hours"]
    drift = incubation_drift(catalog, active_profiles())
    assert any("missing from catalog" in message for message in drift), drift


def test_a_catalog_entry_naming_an_unknown_pathogen_is_drift() -> None:
    """The link rotting from the other end: profile renamed or removed."""
    catalog = copy.deepcopy(load_delay_catalog())
    catalog["distributions"]["norovirus"]["pathogen_id"] = "not_a_pathogen"
    drift = incubation_drift(catalog, active_profiles())
    assert any("bundle does not define" in message for message in drift), drift


def test_an_unanchored_profile_is_drift() -> None:
    """A linked profile that loses its incubation block silently un-anchors."""
    profiles = copy.deepcopy(active_profiles())
    del profiles["norwalk_gi"]["incubation"]
    drift = incubation_drift(load_delay_catalog(), profiles)
    assert any("unanchored" in message for message in drift), drift


def test_unlinked_catalog_entries_are_not_drift() -> None:
    """measles is a sentinel-side counter-example, not a simulator pathogen."""
    catalog = copy.deepcopy(load_delay_catalog())
    measles = catalog["distributions"]["measles"]
    assert "pathogen_id" not in measles
    measles["incubation"]["median_hours"] = 400.0
    assert incubation_drift(catalog, active_profiles()) == ()
