"""Sentinel exposure cells: denominators, offsets, attribution weights.

The point of these checks is that a hazard has a denominator (spec 1.4), that
the offset shrinks with censoring and ascertainment (1.6), and that per-case
port weights follow the incubation clock rather than the itinerary order.
"""

from __future__ import annotations

import math
import os
import sys
from typing import Any

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from picard_framework.analysis.sentinel.exposure import (
    CREW_ABOARD,
    CREW_ASHORE,
    PAX_ABOARD,
    PAX_ASHORE,
    ascertainment_fraction,
    build_exposure_design,
    derived_exposure_totals,
    import_attribution_weights,
    min_inter_port_hours,
    onsets_per_epoch,
)
from picard_framework.analysis.sentinel.incubation import (
    delays_for_pathogen,
    discrete_delay,
    port_resolution_adequate,
)
from picard_framework.analysis.sentinel.itinerary import voyage_from_config
from picard_framework.analysis.sentinel.observations import bundle_from_dict

INCUBATION = delays_for_pathogen(epoch_hours=1.0)[0]


def voyage_config(*, crew_fraction: float = 0.2) -> dict[str, Any]:
    """Two port days on a 6-day, 24-epoch-per-day voyage."""
    return {
        "voyage": {
            "effects_enabled": True,
            "total_epochs": 144,
            "epoch_duration_hours": 1,
            "embarkation_date": "2026-03-01",
            "itinerary": [
                {"day": 1, "type": "embarkation", "port": "Miami", "port_id": "USMIA"},
                {
                    "day": 2,
                    "type": "port_day",
                    "port": "Cozumel",
                    "port_id": "MXCZM",
                    "disembark_fraction": 0.5,
                    "crew_shore_leave_fraction": crew_fraction,
                    "disembark_window_epochs": [2, 4],
                    "reembark_window_epochs": [12, 14],
                },
                {"day": 3, "type": "sea_day"},
                {
                    "day": 4,
                    "type": "port_day",
                    "port": "George Town",
                    "port_id": "KYGEC",
                    "disembark_fraction": 0.4,
                    "crew_shore_leave_fraction": crew_fraction,
                    "disembark_window_epochs": [2, 4],
                    "reembark_window_epochs": [12, 14],
                },
                {"day": 5, "type": "sea_day"},
                {"day": 6, "type": "disembarkation", "port": "Miami", "port_id": "USMIA"},
            ],
        },
    }


def voyage(**kwargs: Any):
    """Sentinel voyage view over ``voyage_config``."""
    return voyage_from_config(
        voyage_config(**kwargs),
        voyage_id="V1",
        ship_id="s1",
        n_passengers=1000,
        n_crew=400,
    )


def case(
    person_id: str,
    onset_epoch: int,
    *,
    crew: bool = False,
    hours: dict[str, float] | None = None,
) -> dict[str, Any]:
    """One clinical case record in schema shape."""
    return {
        "person_id": person_id,
        "onset_epoch": onset_epoch,
        "crew": crew,
        "pathogen": "norovirus",
        "genotype": None,
        "hours_ashore": hours or {},
        "reported_via": "sick_call",
    }


def bundle(cases: list[dict[str, Any]], **extra: Any):
    """Observation bundle with the given cases."""
    payload: dict[str, Any] = {
        "voyage_id": "V1",
        "ship_id": "s1",
        "n_passengers": 1000,
        "n_crew": 400,
        "observation_end_epoch": 144,
        "clinical_cases": cases,
        "wastewater_samples": [],
    }
    payload.update(extra)
    return bundle_from_dict(payload)


def cell_for(design: Any, port_id: str, stratum: str) -> Any:
    """The single cell for a port and stratum."""
    matches = [c for c in design.port_cells if c.port_id == port_id and c.stratum == stratum]
    assert len(matches) == 1, f"expected one {port_id}/{stratum} cell, got {len(matches)}"
    return matches[0]


def test_ascertainment_is_multiplicative_and_bounded() -> None:
    assert ascertainment_fraction() == 1.0
    assert ascertainment_fraction(reporting=0.5, care_seeking=0.5) == pytest.approx(0.25)
    assert ascertainment_fraction(
        reporting=0.8,
        care_seeking=0.5,
        testing=0.5,
    ) == pytest.approx(0.2)
    for bad in ({"reporting": 0.0}, {"care_seeking": 1.2}, {"testing": -0.1}):
        with pytest.raises(ValueError, match="must be in"):
            ascertainment_fraction(**bad)


def test_derived_denominators_scale_with_fraction_and_hours() -> None:
    """No ashore ledger (a field voyage): denominators come off the schedule."""
    totals = derived_exposure_totals(voyage(crew_fraction=0.25))
    # 500 passengers ashore x 10 h (window midpoints 3 -> 13)
    assert totals["MXCZM"]["person_hours_passenger"] == pytest.approx(5000.0)
    assert totals["MXCZM"]["n_passengers_ashore"] == pytest.approx(500.0)
    assert totals["MXCZM"]["person_hours_crew"] == pytest.approx(1000.0)
    assert totals["KYGEC"]["person_hours_passenger"] == pytest.approx(4000.0)

    doubled = derived_exposure_totals(voyage(crew_fraction=0.5))
    assert doubled["MXCZM"]["person_hours_crew"] == pytest.approx(2000.0)


def test_crew_denominator_is_zero_only_when_shore_leave_is_zero() -> None:
    """The PR 3 gate, seen from the estimator side."""
    off = derived_exposure_totals(voyage(crew_fraction=0.0))
    on = derived_exposure_totals(voyage(crew_fraction=0.1))
    assert off["MXCZM"]["person_hours_crew"] == 0.0
    assert on["MXCZM"]["person_hours_crew"] > 0.0


def test_recorded_exposure_totals_win_over_the_reconstruction() -> None:
    observed = {
        "MXCZM": {
            "person_hours_passenger": 123.0,
            "person_hours_crew": 45.0,
            "n_passengers_ashore": 20,
            "n_crew_ashore": 6,
        },
    }
    design = build_exposure_design(
        voyage(),
        bundle([], exposure_totals=observed),
        INCUBATION,
    )
    pax = cell_for(design, "MXCZM", PAX_ASHORE)
    assert pax.person_hours_ashore == pytest.approx(123.0)
    assert pax.n_persons == 20
    # Ports absent from the ledger stay empty rather than borrowing the schedule.
    assert cell_for(design, "KYGEC", PAX_ASHORE).person_hours_ashore == 0.0
    assert cell_for(design, "KYGEC", PAX_ASHORE).log_offset is None


def test_offset_shrinks_with_censoring_and_ascertainment() -> None:
    full = build_exposure_design(voyage(), bundle([]), INCUBATION)
    partial = build_exposure_design(
        voyage(),
        bundle([]),
        INCUBATION,
        ascertainment=ascertainment_fraction(reporting=0.5),
    )
    early = cell_for(full, "MXCZM", PAX_ASHORE)
    late = cell_for(full, "KYGEC", PAX_ASHORE)

    # Both ports are far enough from the end here that censoring is mild,
    # but the later one is always censored at least as hard as the earlier.
    assert late.observed_fraction <= early.observed_fraction
    assert early.censor_epochs_remaining > late.censor_epochs_remaining
    assert early.effective_person_hours <= early.person_hours_ashore

    halved = cell_for(partial, "MXCZM", PAX_ASHORE)
    assert halved.effective_person_hours == pytest.approx(
        early.effective_person_hours * 0.5,
    )
    assert halved.log_offset == pytest.approx(early.log_offset - math.log(2.0))


def test_a_last_port_call_is_censored_hard() -> None:
    """1.6, at cell level: the last port sees only a fraction of its onsets."""
    cfg = voyage_config()
    cfg["voyage"]["total_epochs"] = 96  # disembark right after the second port
    late_voyage = voyage_from_config(
        cfg,
        voyage_id="V1",
        ship_id="s1",
        n_passengers=1000,
        n_crew=400,
    )
    design = build_exposure_design(late_voyage, bundle([]), INCUBATION)
    early = cell_for(design, "MXCZM", PAX_ASHORE)
    late = cell_for(design, "KYGEC", PAX_ASHORE)
    assert late.observed_fraction < 0.6 < early.observed_fraction
    assert late.censoring_corrected
    assert late.effective_person_hours < late.person_hours_ashore


@pytest.mark.parametrize("ascertainment", [0.0, 1.5])
def test_impossible_ascertainment_is_refused(ascertainment: float) -> None:
    itinerary = voyage()
    observations = bundle([])
    with pytest.raises(ValueError, match="ascertainment"):
        build_exposure_design(
            itinerary,
            observations,
            INCUBATION,
            ascertainment=ascertainment,
        )


def test_attribution_follows_the_incubation_clock() -> None:
    """A single-port case is attributed there; timing beats itinerary order."""
    v = voyage()
    # MXCZM ashore epochs are 26-38, KYGEC 74-86. An onset at 108 is ~1.3 d
    # after KYGEC and ~3.4 d after MXCZM: norovirus says KYGEC.
    both = case("P1", 108, hours={"MXCZM": 8.0, "KYGEC": 8.0})
    weights = import_attribution_weights(
        bundle([both]).clinical_cases[0],
        v,
        INCUBATION,
    )
    assert sum(weights.values()) == pytest.approx(1.0)
    assert weights["KYGEC"] > 0.9

    # Move the onset to just after the first port and the answer flips.
    early = import_attribution_weights(
        bundle([case("P1", 60, hours={"MXCZM": 8.0, "KYGEC": 8.0})]).clinical_cases[0],
        v,
        INCUBATION,
    )
    assert early["MXCZM"] == pytest.approx(1.0)


def test_attribution_is_graded_in_hours_ashore() -> None:
    v = voyage()
    onset = 100  # inside both ports' incubation reach
    balanced = import_attribution_weights(
        bundle([case("P1", onset, hours={"MXCZM": 8.0, "KYGEC": 8.0})]).clinical_cases[0],
        v,
        INCUBATION,
    )
    lopsided = import_attribution_weights(
        bundle([case("P1", onset, hours={"MXCZM": 8.0, "KYGEC": 1.0})]).clinical_cases[0],
        v,
        INCUBATION,
    )
    assert lopsided["MXCZM"] > balanced["MXCZM"]
    assert sum(lopsided.values()) == pytest.approx(1.0)


def test_cases_with_no_reachable_exposure_get_no_port_weight() -> None:
    v = voyage()
    aboard = bundle([case("P1", 100)]).clinical_cases[0]
    assert import_attribution_weights(aboard, v, INCUBATION) == {}

    # Onset before the port call cannot have been acquired there.
    impossible = bundle([case("P2", 30, hours={"KYGEC": 8.0})]).clinical_cases[0]
    assert import_attribution_weights(impossible, v, INCUBATION) == {}

    # Unknown port ids are ignored rather than fabricating a cell.
    unknown = bundle([case("P3", 100, hours={"ZZZZZ": 8.0})]).clinical_cases[0]
    assert import_attribution_weights(unknown, v, INCUBATION) == {}


def test_expected_cases_conserve_the_ashore_case_count() -> None:
    cases = [
        case("P1", 60, hours={"MXCZM": 8.0}),
        case("P2", 105, hours={"MXCZM": 6.0, "KYGEC": 9.0}),
        case("C1", 100, crew=True, hours={"KYGEC": 5.0}),
        case("P3", 120),  # aboard the whole voyage
    ]
    design = build_exposure_design(voyage(), bundle(cases), INCUBATION)
    total_expected = sum(c.expected_cases for c in design.port_cells)
    assert total_expected == pytest.approx(3.0, abs=1e-6)  # P3 contributes nothing
    # Modal (integer) counts assign each ashore case to exactly one cell.
    assert sum(c.cases for c in design.port_cells) == 3
    assert cell_for(design, "KYGEC", CREW_ASHORE).cases == 1
    assert cell_for(design, "MXCZM", CREW_ASHORE).cases == 0


def test_aboard_cases_land_in_the_voyage_baseline_not_a_port() -> None:
    cases = [
        case("P1", 60, hours={"MXCZM": 8.0}),
        case("P2", 90),
        case("C1", 100, crew=True),
    ]
    design = build_exposure_design(voyage(), bundle(cases), INCUBATION)
    baselines = {b.stratum: b for b in design.baseline_cells}
    assert set(baselines) == {PAX_ABOARD, CREW_ABOARD}
    assert baselines[PAX_ABOARD].cases == 1
    assert baselines[CREW_ABOARD].cases == 1
    assert baselines[PAX_ABOARD].person_hours_aboard > 0.0
    # One baseline per stratum per voyage, not one per port call: the same
    # person stays aboard at every port and must not be counted twice.
    assert len(design.baseline_cells) == 2


def test_baseline_hours_net_out_the_time_spent_ashore() -> None:
    totals = {
        "MXCZM": {
            "person_hours_passenger": 5000.0,
            "person_hours_crew": 1000.0,
            "n_passengers_ashore": 500,
            "n_crew_ashore": 100,
        },
    }
    design = build_exposure_design(
        voyage(),
        bundle([], exposure_totals=totals),
        INCUBATION,
    )
    baselines = {b.stratum: b for b in design.baseline_cells}
    assert baselines[PAX_ABOARD].person_hours_aboard == pytest.approx(
        1000 * 144 - 5000.0,
    )
    assert baselines[CREW_ABOARD].person_hours_aboard == pytest.approx(
        400 * 144 - 1000.0,
    )


def test_design_carries_the_onset_curve_for_the_renewal_term() -> None:
    cases = [case("P1", 3), case("P2", 3), case("P3", 7)]
    design = build_exposure_design(voyage(), bundle(cases), INCUBATION)
    counts = design.onset_counts()
    assert counts.size == 144
    assert counts[2] == 2.0
    assert counts[6] == 1.0
    assert counts.sum() == 3.0


def test_onsets_past_the_window_are_dropped_not_clamped() -> None:
    cases = bundle([case("P1", 5)]).clinical_cases
    assert onsets_per_epoch(cases, 3) == (0, 0, 0)
    assert onsets_per_epoch(cases, 0) == ()


def test_repeat_calls_to_one_port_pool_into_a_single_cell() -> None:
    cfg = voyage_config()
    cfg["voyage"]["itinerary"][3]["port_id"] = "MXCZM"  # second call, same port
    cfg["voyage"]["itinerary"][3]["port"] = "Cozumel"
    repeat = voyage_from_config(
        cfg,
        voyage_id="V1",
        ship_id="s1",
        n_passengers=1000,
        n_crew=400,
    )
    design = build_exposure_design(repeat, bundle([]), INCUBATION)
    pax = cell_for(design, "MXCZM", PAX_ASHORE)
    assert pax.n_calls == 2
    # Hours are ledgered per port id, so both calls' hours are in the cell.
    assert pax.person_hours_ashore == pytest.approx(5000.0 + 4000.0)
    # Censoring follows the later call (day 4, reembark window ends at epoch 87).
    assert pax.censor_epochs_remaining == 144 - 87


def test_min_inter_port_interval_gates_port_level_claims() -> None:
    v = voyage()
    assert min_inter_port_hours(v) == pytest.approx(48.0)
    assert port_resolution_adequate(INCUBATION, min_inter_port_hours(v))

    single = voyage_from_config(
        {
            "voyage": {
                "total_epochs": 48,
                "epoch_duration_hours": 1,
                "itinerary": [{"day": 1, "type": "sea_day"}],
            },
        },
        voyage_id="V1",
        ship_id="s1",
    )
    assert min_inter_port_hours(single) == math.inf


def test_slow_incubation_spreads_one_case_across_both_ports() -> None:
    """Where 1.8 bites: a flat, wide delay cannot separate the two calls."""
    flat = discrete_delay(name="flat", weights=[1.0] * 200, epoch_hours=1.0)
    weights = import_attribution_weights(
        bundle([case("P1", 140, hours={"MXCZM": 8.0, "KYGEC": 8.0})]).clinical_cases[0],
        voyage(),
        flat,
    )
    assert weights["MXCZM"] == pytest.approx(weights["KYGEC"], rel=0.05)
    assert not port_resolution_adequate(flat, min_inter_port_hours(voyage()))
