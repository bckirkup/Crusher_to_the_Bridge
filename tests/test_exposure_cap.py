"""
test_exposure_cap.py — EXPO-CAP-01 invariants
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The exposure cap (spec ``docs/exposure_cap_spec.md``) bounds how many
distinct susceptible hosts a shedder's pooled droplet/HVAC dose can reach
in one epoch: each shedder draws a Poisson per-epoch contact budget on a
dedicated RNG stream and may dose only a sampled cohort of that size.

The invariants a wrong implementation cannot satisfy:

* the labelled baseline is inert — ``transmission.exposure_cap.enabled:
  false`` leaves the cap inactive, spawns no RNG stream, and (platform
  gate aside) the pre-change code path is untouched;
* the cap applies only where the rhythm catalog declares cruise mixing
  structure — naval and uncatalogued platforms are inert even with the
  flag on;
* a shedder's cohort is bounded by its remaining per-epoch budget, the
  budget is shared between the pooled-droplet and HVAC spends inside one
  epoch, and it resets next epoch;
* budget draws come from ``_exposure_cap_rng``, not the shared engine
  stream, so enabling the cap does not perturb partner or pool draws.
"""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace

import numpy as np
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from engines.rhythm_layer import platform_has_rhythm_catalog  # noqa: E402
from engines.sim_clock import HOURS, SimClock  # noqa: E402
from engines.transmission_core import (  # noqa: E402
    TransmissionCore,
    _parse_exposure_cap_enabled,
)

CATALOGED_LAYOUT = "data/platforms/mega_cruise_5000/spatial_layout.json"
NAVAL_LAYOUT = "data/platforms/destroyer_baseline/spatial_layout.json"


def _cfg(exposure_cap: object = ..., layout: str = CATALOGED_LAYOUT) -> dict:
    tx: dict = {}
    if exposure_cap is not ...:
        tx["exposure_cap"] = exposure_cap
    return {
        "ship_graph": {"spatial_layout": layout},
        "transmission": tx,
    }


def _core(cfg: dict) -> TransmissionCore:
    return TransmissionCore(
        rng=np.random.default_rng(7),
        cfg=cfg,
        clock=SimClock(mode=HOURS),
    )


def _shedder(agent_id: int) -> SimpleNamespace:
    return SimpleNamespace(
        agent_id=agent_id,
        role="passenger",
        agent_class="passenger",
    )


# ── flag parsing ────────────────────────────────────────────────────


def test_flag_absent_defaults_enabled() -> None:
    assert _parse_exposure_cap_enabled({}) is True


def test_flag_false_disables() -> None:
    assert _parse_exposure_cap_enabled(
        {"exposure_cap": {"enabled": False}},
    ) is False


def test_flag_rejects_non_mapping_and_non_bool() -> None:
    with pytest.raises(ValueError, match="mapping"):
        _parse_exposure_cap_enabled({"exposure_cap": True})
    with pytest.raises(ValueError, match="bool"):
        _parse_exposure_cap_enabled({"exposure_cap": {"enabled": "yes"}})


# ── platform gate ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    "platform_id",
    (
        "mega_cruise_5000",
        "spirit_cruise_3000",
        "classic_cruise_1900",
        "expedition_cruise_450",
        "enterprise_galaxy_tng",
        "enterprise_constitution_tos",
    ),
)
def test_catalog_gate_true_on_cruise_platforms(platform_id: str) -> None:
    assert platform_has_rhythm_catalog(platform_id)


@pytest.mark.parametrize(
    "platform_id", ("destroyer_baseline", "messy_cruise_500", ""),
)
def test_catalog_gate_false_off_cruise_platforms(platform_id: str) -> None:
    assert not platform_has_rhythm_catalog(platform_id)


# ── engine construction ─────────────────────────────────────────────


def test_cap_active_on_cataloged_platform_by_default() -> None:
    core = _core(_cfg())
    assert core._exposure_cap_active
    assert core._exposure_cap_rng is not None


def test_flag_off_spawns_no_rng_stream() -> None:
    core = _core(_cfg({"enabled": False}))
    assert not core._exposure_cap_active
    assert core._exposure_cap_rng is None


def test_flag_on_is_inert_on_naval_platform() -> None:
    core = _core(_cfg({"enabled": True}, layout=NAVAL_LAYOUT))
    assert not core._exposure_cap_active
    assert core._exposure_cap_rng is None


def test_flag_absent_is_inert_on_naval_platform() -> None:
    core = _core(_cfg(..., layout=NAVAL_LAYOUT))
    assert not core._exposure_cap_active


# ── budget mechanics ────────────────────────────────────────────────


def test_cohort_is_bounded_by_budget() -> None:
    """A shedder whose Poisson budget is forced small cannot dose more
    distinct hosts than the budget allows."""
    core = _core(_cfg())
    susceptibles = [_shedder(100 + i) for i in range(50)]
    shedder = _shedder(1)

    class _TinyRng:
        def poisson(self, mean: float) -> int:
            return 3

        def choice(self, n: int, size: int, replace: bool) -> np.ndarray:
            return np.arange(size)

    core._exposure_cap_rng = _TinyRng()
    cohort = core._exposure_cap_cohort(
        [(shedder, "Unit", "Zone")], susceptibles, 0, "pathogen_x",
    )
    assert cohort == {100, 101, 102}
    # Budget spent: the second call in the same epoch returns nothing.
    assert core._exposure_cap_budget(
        shedder, "Unit", "Zone", 0, "pathogen_x",
    ) == 0
    cohort = core._exposure_cap_cohort(
        [(shedder, "Unit", "Zone")], susceptibles, 0, "pathogen_x",
    )
    assert cohort == set()


def test_budget_resets_each_epoch() -> None:
    core = _core(_cfg())
    susceptibles = [_shedder(100 + i) for i in range(50)]
    shedder = _shedder(1)

    class _TinyRng:
        def poisson(self, mean: float) -> int:
            return 2

        def choice(self, n: int, size: int, replace: bool) -> np.ndarray:
            return np.arange(size)

    core._exposure_cap_rng = _TinyRng()
    core._exposure_cap_cohort(
        [(shedder, "Unit", "Zone")], susceptibles, 0, "pathogen_x",
    )
    cohort = core._exposure_cap_cohort(
        [(shedder, "Unit", "Zone")], susceptibles, 1, "pathogen_x",
    )
    assert cohort == {100, 101}


def test_cohort_is_bounded_by_susceptible_count() -> None:
    """More budget than susceptibles must not index past the list."""
    core = _core(_cfg())
    susceptibles = [_shedder(100 + i) for i in range(4)]
    shedder = _shedder(1)

    class _BigRng:
        def poisson(self, mean: float) -> int:
            return 999

        def choice(self, n: int, size: int, replace: bool) -> np.ndarray:
            assert size == n  # k was clamped to the susceptible count
            return np.arange(size)

    core._exposure_cap_rng = _BigRng()
    cohort = core._exposure_cap_cohort(
        [(shedder, "Unit", "Zone")], susceptibles, 0, "pathogen_x",
    )
    assert cohort == {100, 101, 102, 103}


def test_cap_draws_do_not_touch_shared_rng() -> None:
    """Budget sampling reads only _exposure_cap_rng; the engine's own
    stream position is unchanged by a cohort draw."""
    rng = np.random.default_rng(11)
    core = TransmissionCore(rng=rng, cfg=_cfg(), clock=SimClock(mode=HOURS))
    susceptibles = [_shedder(100 + i) for i in range(30)]
    shedder = _shedder(1)

    rng_copy = np.random.default_rng(11)
    expected = rng_copy.random(8)  # consume the copy to the same point
    core._exposure_cap_cohort(
        [(shedder, "Unit", "Zone")], susceptibles, 0, "pathogen_x",
    )
    np.testing.assert_array_equal(rng.random(8), expected)


def test_budget_mean_uses_polymod_fallback_rate() -> None:
    """Without a CONTACT-ARCH-01 block the epoch mean is the POLYMOD daily
    rate prorated by the clock — the same rate the partner draw uses."""
    core = _core(_cfg())
    shedder = _shedder(1)
    mean = core._exposure_cap_rate(shedder, "Unit", "Zone", 0)
    expected = (
        core.clock.amount_per_epoch(13.4)
        * float(core.voyage_contact_multiplier)
    )
    assert mean == pytest.approx(expected)
