"""The ceiling on the cabin-localization fraction f (#12): bound, not value."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from orchestrator_init import default_cabin_size
from telemetry_buffer.observation_model import cabin_localization_ceiling as clc
from telemetry_buffer.observation_model import park_surface_check as psc

PLATFORMS = Path(__file__).resolve().parents[1] / "data" / "platforms"


def _layout(platform: str) -> dict:
    with (PLATFORMS / platform / "spatial_layout.json").open(encoding="utf-8") as fh:
        return json.load(fh)


def test_pure_double_occupancy_is_the_registers_one_half() -> None:
    """0.5 is a special case of the identity, reproduced from the arithmetic."""
    plan = clc.ceiling_from_cabin_sizes({2: 1000})
    assert plan == (2000, 1000, 0.5)


def test_the_ceiling_rises_with_occupants_per_cabin_and_falls_with_singles() -> None:
    singles = clc.ceiling_from_cabin_sizes({1: 100}).ceiling
    doubles = clc.ceiling_from_cabin_sizes({2: 100}).ceiling
    triples = clc.ceiling_from_cabin_sizes({3: 100}).ceiling
    quads = clc.ceiling_from_cabin_sizes({4: 100}).ceiling
    assert singles == 0.0
    assert singles < doubles < triples < quads
    assert doubles == pytest.approx(0.5)
    assert triples == pytest.approx(2.0 / 3.0)
    assert quads == pytest.approx(0.75)


def test_impossible_berthing_plans_are_refused_rather_than_returned() -> None:
    with pytest.raises(ValueError):
        clc.ceiling_from_berths(0, 0)
    with pytest.raises(ValueError):
        clc.ceiling_from_berths(10, 0)
    with pytest.raises(ValueError):
        clc.ceiling_from_berths(10, 11)
    with pytest.raises(ValueError):
        clc.ceiling_from_occupancy_index(0.0)


def test_the_occupancy_index_identity_reproduces_a_published_berth_census() -> None:
    """Symphony's double-occupancy guest count is exactly twice its staterooms.

    That is the operators' own definition of the index denominator, so the
    conversion from a published occupancy percentage to occupants per cabin is
    not an assumption of ours.
    """
    assert clc.SYMPHONY_GUESTS_DOUBLE == 2 * clc.SYMPHONY_STATEROOMS
    ceilings = clc.symphony_ceilings()
    assert ceilings["double"] == pytest.approx(0.5)
    assert ceilings["maximum"] == pytest.approx(0.587, abs=5e-4)
    assert clc.ceiling_from_occupancy_index(1.0) == pytest.approx(ceilings["double"])


def test_published_occupancy_puts_the_ceiling_above_one_half() -> None:
    """Every published operator-year since the restart sits at or above 0.5."""
    low, high = clc.published_ceiling_interval()
    assert low == pytest.approx(0.5)
    assert high == pytest.approx(clc.ceiling_from_occupancy_index(1.085))
    assert high == pytest.approx(0.5392, abs=5e-4)
    for index in clc.PUBLISHED_OCCUPANCY_INDEX.values():
        assert clc.ceiling_from_occupancy_index(index) >= 0.5


@pytest.mark.parametrize(
    "platform",
    ["mega_cruise_5000", "classic_cruise_1900", "spirit_cruise_3000",
     "expedition_cruise_450"],
)
def test_cruise_hulls_are_not_berthed_at_a_flat_one_half(platform: str) -> None:
    """Crew triples put every cruise hull's own ceiling above 0.5."""
    layout = _layout(platform)
    whole = clc.platform_ceiling(layout, default_cabin_size)
    crew = clc.platform_ceiling(layout, default_cabin_size, clc.is_crew_cabin_zone)
    passengers = clc.platform_ceiling(
        layout,
        default_cabin_size,
        lambda zone_id: not clc.is_crew_cabin_zone(zone_id),
    )
    assert 0.53 < whole.ceiling < 0.56
    assert crew.ceiling > whole.ceiling > passengers.ceiling
    assert passengers.ceiling <= 0.5
    assert whole.occupants == crew.occupants + passengers.occupants


def test_the_naval_hulls_single_cabins_pull_the_ceiling_the_other_way() -> None:
    """A berthing plan with singles bounds f below a half, not above it."""
    ceiling = clc.platform_ceiling(
        _layout("enterprise_constitution_tos"),
        default_cabin_size,
    )
    assert ceiling.ceiling < 0.5


def test_the_emesis_location_sweep_is_a_different_quantity() -> None:
    """The Park harness's sweep is not bounded by the transmission ceiling.

    If the two were one quantity, most of the sweep would be inadmissible; the
    test records that they are not, so the names cannot re-merge silently.
    """
    _, high = clc.published_ceiling_interval()
    assert max(psc.EMESIS_IN_OWN_CABIN_SWEEP) == 1.0
    assert sum(1 for f in psc.EMESIS_IN_OWN_CABIN_SWEEP if f > high) == 4
    assert not hasattr(psc, "CABIN_LOCALIZATION_SWEEP")


def test_the_report_states_the_ceiling_and_refuses_a_value() -> None:
    text = clc.report()
    assert "f = 0 is not excluded" in text
    assert "central value" in text
    assert "floor of this ceiling" in text
