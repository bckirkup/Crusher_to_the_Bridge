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
    _parse_exposure_cap_include_fixed_rings,
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


def _ring_agent(
    agent_id: int,
    *,
    immune: bool = False,
    infected: bool = False,
    departed: bool = False,
    ashore: bool = False,
    location: str = "Cabin",
    cabin_mate_ids: frozenset = frozenset(),
    dining_zone: str = "",
    dining_party_ids: frozenset = frozenset(),
    current_activity: str = "",
) -> SimpleNamespace:
    """The KorkinAgent surface the fixed-ring contact count reads."""
    return SimpleNamespace(
        agent_id=agent_id,
        role="passenger",
        immune=immune,
        is_infected_with=lambda pid: infected,
        has_departed=lambda epoch: departed,
        ashore=ashore,
        current_location=location,
        cabin_mate_ids=cabin_mate_ids,
        dining_zone=dining_zone,
        dining_party_ids=dining_party_ids,
        current_activity=current_activity,
        schedule=[],
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


# ── RING-CAP-V1: fixed rings spend the budget first ─────────────────


def test_include_fixed_rings_defaults_off() -> None:
    assert _parse_exposure_cap_include_fixed_rings({}) is False
    assert _parse_exposure_cap_include_fixed_rings(
        {"exposure_cap": {"enabled": True}},
    ) is False


def test_include_fixed_rings_rejects_non_bool() -> None:
    with pytest.raises(ValueError, match="bool"):
        _parse_exposure_cap_include_fixed_rings(
            {"exposure_cap": {"include_fixed_rings": "yes"}},
        )


def test_flag_off_leaves_budget_untouched_by_rings() -> None:
    """The v13 baseline: ring partners present but the cohort still
    draws the full Poisson budget."""
    core = _core(_cfg())
    shedder = _ring_agent(1, cabin_mate_ids=frozenset({2, 3}))
    core._agent_by_id = {
        a.agent_id: a
        for a in (shedder, _ring_agent(2), _ring_agent(3))
    }

    class _TinyRng:
        def poisson(self, mean: float) -> int:
            return 5

    core._exposure_cap_rng = _TinyRng()
    assert core._exposure_cap_budget(
        shedder, "Unit", "Zone", 0, "pathogen_x",
    ) == 5


def test_cabin_mates_spend_budget_when_flag_on() -> None:
    """Each susceptible cabin mate with a co-presence share consumes one
    unit of the shedder's budget before the pooled cohort draws."""
    core = _core(_cfg({"enabled": True, "include_fixed_rings": True}))
    shedder = _ring_agent(1, cabin_mate_ids=frozenset({2, 3, 4}))
    infected_mate = _ring_agent(4, infected=True)
    core._agent_by_id = {
        a.agent_id: a
        for a in (shedder, _ring_agent(2), _ring_agent(3), infected_mate)
    }

    class _TinyRng:
        def poisson(self, mean: float) -> int:
            return 5

    core._exposure_cap_rng = _TinyRng()
    # Two open mates (2, 3) spend; the infected mate forms no dose.
    assert core._exposure_cap_budget(
        shedder, "Unit", "Zone", 0, "pathogen_x",
    ) == 3


def test_dealt_table_and_fixed_party_spend_when_flag_on() -> None:
    """A dealt meal-table entry or a fixed dining party on a Meal token
    both count; neither counts when the shedder did not dine."""
    core = _core(_cfg({"enabled": True, "include_fixed_rings": True}))
    shedder = _ring_agent(
        1,
        dining_zone="Buffet",
        current_activity="Meal",
        cabin_mate_ids=frozenset(),
    )
    partners = {p.agent_id: p for p in (_ring_agent(7), _ring_agent(8))}
    core._agent_by_id = {1: shedder, **partners}
    core._meal_tables[("Buffet", 0)] = {1: (0, frozenset({7, 8}))}
    assert core._fixed_ring_contacts(shedder, 0, "pathogen_x") == {7, 8}

    # Fixed party: no dealt entry, Meal token required.
    core._meal_tables.clear()
    shedder.dining_party_ids = frozenset({7})
    assert core._fixed_ring_contacts(shedder, 0, "pathogen_x") == {7}
    shedder.current_activity = "Promenade"
    assert core._fixed_ring_contacts(shedder, 0, "pathogen_x") == set()


def test_ring_contacts_isolated_or_departed_partners_do_not_spend() -> None:
    core = _core(_cfg({"enabled": True, "include_fixed_rings": True}))
    shedder = _ring_agent(1, cabin_mate_ids=frozenset({2, 3, 4}))
    core._agent_by_id = {
        1: shedder,
        2: _ring_agent(2, location="Isolated_In_Quarters"),
        3: _ring_agent(3, departed=True),
        4: _ring_agent(4),
    }
    assert core._fixed_ring_contacts(shedder, 0, "pathogen_x") == {4}


def test_flag_on_still_draws_only_cap_rng() -> None:
    """Ring accounting adds no draws: the shared engine stream is
    untouched by a flag-on budget computation."""
    rng = np.random.default_rng(13)
    core = TransmissionCore(
        rng=rng,
        cfg=_cfg({"enabled": True, "include_fixed_rings": True}),
        clock=SimClock(mode=HOURS),
    )
    shedder = _ring_agent(1, cabin_mate_ids=frozenset({2}))
    core._agent_by_id = {1: shedder, 2: _ring_agent(2)}
    rng_copy = np.random.default_rng(13)
    expected = rng_copy.random(8)
    core._exposure_cap_budget(shedder, "Unit", "Zone", 0, "pathogen_x")
    np.testing.assert_array_equal(rng.random(8), expected)
