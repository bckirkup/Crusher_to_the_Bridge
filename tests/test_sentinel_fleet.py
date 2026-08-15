"""Fleet sentinel model: the Stan data contract, visit keys, and crew repeats.

The cheap invariants, split from the sampling suite for the same reason as the
single-ship split: a fleet data block can be mis-assembled in ways no amount of
sampling would flag — two ships' calls pooled into one visit that should be two,
a padded epoch leaking into the likelihood, a crew repeat count computed in
whatever order the voyages happened to be listed in.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Sequence

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from picard_framework.analysis.sentinel.exposure import build_exposure_design
from picard_framework.analysis.sentinel.itinerary import voyage_from_config
from picard_framework.analysis.sentinel.observations import bundle_from_dict
from picard_framework.analysis.stan._sentinel_fleet_data import (
    FleetRates,
    FleetVoyage,
    aboard_hours_by_ship,
    build_sentinel_fleet_data,
    fleet_forward_incidence,
    visit_hours,
)
from tests.test_sentinel_attribution import GENERATION, INCUBATION

N_PASSENGERS = 1000
N_CREW = 400


def fleet_voyage(
    *,
    voyage_id: str,
    ship_id: str,
    embarkation_date: str,
    ports: Sequence[tuple[int, str]],
    total_epochs: int = 168,
    observation_end_epoch: int | None = None,
    onset_epochs: Sequence[int] = (),
    crew_onset_epochs: Sequence[int] = (),
    crew_fraction: float = 0.2,
    wastewater_samples: Sequence[dict[str, Any]] = (),
) -> FleetVoyage:
    """One voyage of the fleet: ``ports`` as ``(voyage_day, port_id)`` pairs."""
    itinerary: list[dict[str, Any]] = [
        {"day": 1, "type": "embarkation", "port": "Miami", "port_id": "USMIA"},
    ]
    n_days = total_epochs // 24
    called = dict(ports)
    for day in range(2, n_days):
        port_id = called.get(day)
        if port_id is None:
            itinerary.append({"day": day, "type": "sea_day"})
            continue
        itinerary.append(
            {
                "day": day,
                "type": "port_day",
                "port": port_id,
                "port_id": port_id,
                "disembark_fraction": 0.6,
                "crew_shore_leave_fraction": crew_fraction,
                "disembark_window_epochs": [2, 4],
                "reembark_window_epochs": [12, 14],
            },
        )
    itinerary.append(
        {"day": n_days, "type": "disembarkation", "port": "Miami", "port_id": "USMIA"},
    )
    config = {
        "voyage": {
            "effects_enabled": True,
            "total_epochs": total_epochs,
            "epoch_duration_hours": 1,
            "embarkation_date": embarkation_date,
            "itinerary": itinerary,
        },
    }
    voyage = voyage_from_config(
        config,
        voyage_id=voyage_id,
        ship_id=ship_id,
        n_passengers=N_PASSENGERS,
        n_crew=N_CREW,
    )
    end = observation_end_epoch if observation_end_epoch is not None else total_epochs
    cases = [
        {
            "person_id": f"{voyage_id}-p{i}",
            "onset_epoch": epoch,
            "crew": False,
            "pathogen": "norovirus",
            "genotype": None,
            "hours_ashore": {},
            "reported_via": "sick_call",
        }
        for i, epoch in enumerate(onset_epochs)
    ] + [
        {
            "person_id": f"{voyage_id}-c{i}",
            "onset_epoch": epoch,
            "crew": True,
            "pathogen": "norovirus",
            "genotype": None,
            "hours_ashore": {},
            "reported_via": "sick_call",
        }
        for i, epoch in enumerate(crew_onset_epochs)
    ]
    bundle = bundle_from_dict(
        {
            "voyage_id": voyage_id,
            "ship_id": ship_id,
            "n_passengers": N_PASSENGERS,
            "n_crew": N_CREW,
            "observation_end_epoch": end,
            "clinical_cases": cases,
            "wastewater_samples": [dict(s) for s in wastewater_samples],
        },
    )
    design = build_exposure_design(voyage, bundle, INCUBATION)
    return FleetVoyage(design=design, voyage=voyage, bundle=bundle)


def two_ship_fleet(**kwargs: Any) -> list[FleetVoyage]:
    """Two ships crossing over at MXCZM in the same week — the pooling case.

    Ship A calls MXCZM then KYGEC; ship B calls KYGEC then MXCZM the same week.
    The crossover is what separates a port effect from an itinerary position
    (spec 3): without it, "second port of the cruise" and "George Town" are the
    same column.
    """
    return [
        fleet_voyage(
            voyage_id="A1",
            ship_id="shipA",
            embarkation_date="2026-03-02",
            ports=((2, "MXCZM"), (5, "KYGEC")),
            **kwargs,
        ),
        fleet_voyage(
            voyage_id="B1",
            ship_id="shipB",
            embarkation_date="2026-03-02",
            ports=((2, "KYGEC"), (5, "MXCZM")),
            **kwargs,
        ),
    ]


def fleet_data(voyages: Sequence[FleetVoyage]) -> tuple[dict[str, Any], dict[str, Any]]:
    return build_sentinel_fleet_data(voyages, INCUBATION, GENERATION)


def test_visits_pool_across_ships_within_a_calendar_week() -> None:
    """Same port, same week, two ships: one visit, two voyages pointing at it."""
    data, meta = fleet_data(two_ship_fleet())

    assert data["V"] == 2
    assert data["S"] == 2
    assert data["P"] == 2
    # Two ports x one week, not four voyage-ports: this is the pooling.
    assert data["NV"] == 2
    assert data["W"] == 1
    keys = [v["visit_key"] for v in meta["visits"]]
    assert keys == ["KYGEC@2026-W10", "MXCZM@2026-W10"]
    # every voyage-port cell points at a visit, and both ships share both visits
    assert data["visit_idx"] == [[1, 2], [1, 2]]
    assert data["visit_port"] == [1, 2]
    assert data["visit_week"] == [1, 1]


def test_visits_separate_across_calendar_weeks() -> None:
    """The same port a month later is a different visit, and a different week."""
    voyages = [
        fleet_voyage(
            voyage_id="A1",
            ship_id="shipA",
            embarkation_date="2026-03-02",
            ports=((2, "MXCZM"),),
        ),
        fleet_voyage(
            voyage_id="A2",
            ship_id="shipA",
            embarkation_date="2026-04-06",
            ports=((2, "MXCZM"),),
        ),
    ]
    data, meta = fleet_data(voyages)
    assert data["P"] == 1
    assert data["NV"] == 2
    assert data["W"] == 2
    assert [v["visit_key"] for v in meta["visits"]] == [
        "MXCZM@2026-W10",
        "MXCZM@2026-W15",
    ]
    # one port, two visits: the hierarchy is what pools them
    assert data["visit_port"] == [1, 1]
    assert data["visit_week"] != [1, 1]


def test_crew_repeat_counts_earlier_calls_by_the_same_ship() -> None:
    """Repeat exposure is per ship, in embarkation order, and starts at zero."""
    voyages = [
        fleet_voyage(
            voyage_id="A3",
            ship_id="shipA",
            embarkation_date="2026-05-04",
            ports=((2, "MXCZM"),),
        ),
        fleet_voyage(
            voyage_id="A1",
            ship_id="shipA",
            embarkation_date="2026-03-02",
            ports=((2, "MXCZM"),),
        ),
        fleet_voyage(
            voyage_id="B1",
            ship_id="shipB",
            embarkation_date="2026-04-06",
            ports=((2, "MXCZM"),),
        ),
    ]
    data, meta = fleet_data(voyages)
    repeats = {
        v["voyage_id"]: v["crew_repeat"].get("MXCZM", 0.0) for v in meta["voyages"]
    }
    # A1 sails first, so A3 is shipA's second call; shipB's own first call is 0
    assert repeats == {"A1": 0.0, "A3": 1.0, "B1": 0.0}
    assert data["crew_repeat"][0] == [1.0]  # A3, as supplied (index 0)
    assert data["crew_repeat"][1] == [0.0]
    assert data["crew_repeat"][2] == [0.0]


def test_only_crew_carry_the_repeat_and_ratio_terms() -> None:
    """``is_crew`` marks the group the crew multiplier applies to."""
    data, meta = fleet_data(two_ship_fleet())
    assert meta["groups"] == ["passenger", "crew"]
    assert data["is_crew"] == [0, 1]

    flat = FleetRates(
        lambda_visit=[1.0e-3] * data["NV"],
        lambda_aboard=[0.0] * data["S"],
        r_onboard=[0.0] * data["S"],
    )
    doubled = FleetRates(
        lambda_visit=flat.lambda_visit,
        lambda_aboard=flat.lambda_aboard,
        r_onboard=flat.r_onboard,
        crew_ratio=2.0,
    )
    base, _ = fleet_forward_incidence(data, flat)
    with_ratio, _ = fleet_forward_incidence(data, doubled)
    # passengers untouched, crew exactly doubled
    np.testing.assert_allclose(with_ratio[0][0], base[0][0])
    np.testing.assert_allclose(with_ratio[0][1], 2.0 * base[0][1])


def test_ragged_horizons_pad_without_entering_the_likelihood() -> None:
    """A short voyage is padded to Tmax; T[v] is what every loop stops at."""
    voyages = [
        fleet_voyage(
            voyage_id="A1",
            ship_id="shipA",
            embarkation_date="2026-03-02",
            ports=((2, "MXCZM"),),
            total_epochs=168,
        ),
        fleet_voyage(
            voyage_id="B1",
            ship_id="shipB",
            embarkation_date="2026-03-02",
            ports=((2, "MXCZM"),),
            total_epochs=168,
            observation_end_epoch=96,
        ),
    ]
    data, _ = fleet_data(voyages)
    assert data["Tmax"] == 168
    assert data["T"] == [168, 96]
    short_onsets = np.asarray(data["onsets"][1])
    assert short_onsets.shape == (2, 168)
    assert short_onsets[:, 96:].sum() == 0
    short_aboard = np.asarray(data["aboard_hours"][1])
    assert short_aboard[:, 96:].sum() == 0.0
    # and the forward model returns only the observed window
    _, mu = fleet_forward_incidence(
        data,
        FleetRates(
            lambda_visit=[1.0e-3] * data["NV"],
            lambda_aboard=[1.0e-6] * data["S"],
            r_onboard=[0.3] * data["S"],
        ),
    )
    assert mu[0].shape[1] == 168
    assert mu[1].shape[1] == 96


def test_denominators_are_raw_hours_not_censoring_discounted() -> None:
    """Hours are offsets; censoring enters once, through the truncation.

    Passing PR 4's censoring-discounted effective hours *and* truncating the
    convolution would discount the same censoring twice (spec 1.6).
    """
    voyages = two_ship_fleet()
    data, meta = fleet_data(voyages)
    hours = visit_hours(data)
    assert hours.shape == (data["NV"],)
    reported = np.asarray(
        [meta["person_hours_ashore"][v["visit_key"]] for v in meta["visits"]],
    )
    np.testing.assert_allclose(hours, reported, rtol=1e-6)

    raw = sum(
        cell.person_hours_ashore for fv in voyages for cell in fv.design.port_cells
    )
    np.testing.assert_allclose(float(hours.sum()), raw, rtol=1e-6)
    aboard = aboard_hours_by_ship(data)
    assert aboard.shape == (data["S"],)
    assert float(aboard.min()) > 0.0


def test_generation_weights_start_at_a_positive_lag() -> None:
    """No same-epoch secondary transmission: w_gen is indexed from lag 1."""
    data, _ = fleet_data(two_ship_fleet())
    expected = GENERATION.strictly_lagged().weights[1:]
    np.testing.assert_allclose(data["w_gen_raw"], expected)
    assert data["L_gen"] == expected.size


def test_priors_leave_room_for_the_fleet_time_effect() -> None:
    """The time scale is not shrunk below the port scale.

    Shrinking it would resolve the port-vs-fleet-time confounding by fiat, in
    favour of the ports — the failure mode the spec calls out (3).
    """
    data, _ = fleet_data(two_ship_fleet())
    assert data["time_sd_prior_scale"] >= data["port_sd_prior_scale"]
    assert data["visit_sd_prior_scale"] > 0.0
    assert data["r_sd_prior_scale"] > 0.0


def test_meta_carries_the_orders_the_posterior_indices_refer_to() -> None:
    data, meta = fleet_data(two_ship_fleet())
    assert meta["model"] == "sentinel_fleet"
    assert meta["ports"] == ["KYGEC", "MXCZM"]
    assert meta["ships"] == ["shipA", "shipB"]
    assert meta["weeks"] == ["2026-W10"]
    assert [v["voyage_id"] for v in meta["voyages"]] == ["A1", "B1"]
    assert meta["epoch_duration_hours"] == 1.0
    assert meta["port_resolution_adequate"] is True
    assert len(meta["visits"]) == data["NV"]
    for visit in meta["visits"]:
        assert visit["port_id"] in meta["ports"]
        assert visit["week"] in meta["weeks"]
        assert visit["person_hours_ashore"] > 0.0


def test_undated_itinerary_does_not_pool_with_another_ship() -> None:
    """Without dates, two ships cannot be aligned, so their visits stay apart."""
    voyages = [
        fleet_voyage(
            voyage_id="A1",
            ship_id="shipA",
            embarkation_date="2026-03-02",
            ports=((2, "MXCZM"),),
        ),
        fleet_voyage(
            voyage_id="B1",
            ship_id="shipB",
            embarkation_date="2026-03-02",
            ports=((2, "MXCZM"),),
        ),
    ]
    dated, _ = fleet_data(voyages)
    assert dated["NV"] == 1  # same week, pooled

    undated = [
        FleetVoyage(
            design=fv.design,
            voyage=_strip_dates(fv.voyage),
            bundle=fv.bundle,
        )
        for fv in voyages
    ]
    data, meta = fleet_data(undated)
    assert data["NV"] == 2, "undated visits were pooled on an invented coincidence"
    assert data["W"] == 2
    assert [v["visit_key"] for v in meta["visits"]] == [
        "MXCZM@A1/d2",
        "MXCZM@B1/d2",
    ]


def _strip_dates(voyage: Any) -> Any:
    """The same voyage with every calendar date removed."""
    import dataclasses

    calls = tuple(
        dataclasses.replace(call, calendar_date=None) for call in voyage.port_calls
    )
    return dataclasses.replace(voyage, embarkation_date=None, port_calls=calls)


def test_fleet_needs_a_voyage_and_a_shared_epoch_grid() -> None:
    with pytest.raises(ValueError, match="at least one voyage"):
        build_sentinel_fleet_data([], INCUBATION, GENERATION)

    import dataclasses

    voyages = two_ship_fleet()
    odd = FleetVoyage(
        design=voyages[1].design,
        voyage=dataclasses.replace(voyages[1].voyage, epoch_duration_hours=2.0),
        bundle=voyages[1].bundle,
    )
    with pytest.raises(ValueError, match="share an epoch duration"):
        build_sentinel_fleet_data([voyages[0], odd], INCUBATION, GENERATION)
