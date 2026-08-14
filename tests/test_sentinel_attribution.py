"""Sentinel attribution: the Stan data contract and the forward model.

Split from the validation suite on purpose. These are the cheap invariants —
shapes, port order, raw-vs-effective hours, the strict renewal lag, truncation
at the horizon — and they are what catch a silently mis-assembled data block,
which no amount of sampling would flag.
"""

from __future__ import annotations

import math
import os
import re
import sys
from typing import Any

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from picard_framework.analysis.sentinel.exposure import (
    PAX_ASHORE,
    build_exposure_design,
)
from picard_framework.analysis.sentinel.incubation import delays_for_pathogen
from picard_framework.analysis.sentinel.itinerary import voyage_from_config
from picard_framework.analysis.sentinel.observations import bundle_from_dict
from picard_framework.analysis.stan._sentinel_data import (
    CREW,
    GROUPS,
    PASSENGER,
    attribution_ports,
    build_sentinel_attribution_data,
    expected_onsets_from_data,
    forward_incidence,
)

INCUBATION, GENERATION = delays_for_pathogen(epoch_hours=1.0)

STAN_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "picard_framework",
    "analysis",
    "stan",
    "sentinel_attribution.stan",
)


def voyage_config(
    *,
    crew_fraction: float = 0.2,
    total_epochs: int = 96,
) -> dict[str, Any]:
    """Two port days (day 2 and day 3) on a four-day, 24-epoch-per-day voyage."""
    return {
        "voyage": {
            "effects_enabled": True,
            "total_epochs": total_epochs,
            "epoch_duration_hours": 1,
            "embarkation_date": "2026-03-01",
            "itinerary": [
                {"day": 1, "type": "embarkation", "port": "Miami", "port_id": "USMIA"},
                {
                    "day": 2,
                    "type": "port_day",
                    "port": "Cozumel",
                    "port_id": "MXCZM",
                    "disembark_fraction": 0.6,
                    "crew_shore_leave_fraction": crew_fraction,
                    "disembark_window_epochs": [2, 4],
                    "reembark_window_epochs": [12, 14],
                },
                {
                    "day": 3,
                    "type": "port_day",
                    "port": "George Town",
                    "port_id": "KYGEC",
                    "disembark_fraction": 0.6,
                    "crew_shore_leave_fraction": crew_fraction,
                    "disembark_window_epochs": [2, 4],
                    "reembark_window_epochs": [12, 14],
                },
                {"day": 4, "type": "disembarkation", "port": "Miami", "port_id": "USMIA"},
            ],
        },
    }


def voyage(**kwargs: Any):
    return voyage_from_config(
        voyage_config(**kwargs),
        voyage_id="V1",
        ship_id="s1",
        n_passengers=1000,
        n_crew=400,
    )


def bundle(
    onset_epochs: list[int] | None = None,
    *,
    observation_end_epoch: int = 96,
    crew: bool = False,
):
    cases = [
        {
            "person_id": f"p{i}",
            "onset_epoch": epoch,
            "crew": crew,
            "pathogen": "norovirus",
            "genotype": None,
            "hours_ashore": {},
            "reported_via": "sick_call",
        }
        for i, epoch in enumerate(onset_epochs or [])
    ]
    return bundle_from_dict(
        {
            "voyage_id": "V1",
            "ship_id": "s1",
            "n_passengers": 1000,
            "n_crew": 400,
            "observation_end_epoch": observation_end_epoch,
            "clinical_cases": cases,
            "wastewater_samples": [],
        },
    )


def stan_data(
    onset_epochs: list[int] | None = None,
    *,
    observation_end_epoch: int = 96,
    crew_fraction: float = 0.2,
    crew_cases: bool = False,
    ascertainment: float = 1.0,
) -> tuple[dict[str, Any], dict[str, Any]]:
    v = voyage(crew_fraction=crew_fraction)
    b = bundle(
        onset_epochs,
        observation_end_epoch=observation_end_epoch,
        crew=crew_cases,
    )
    design = build_exposure_design(v, b, INCUBATION, ascertainment=ascertainment)
    return build_sentinel_attribution_data(design, v, b, INCUBATION, GENERATION)


def test_data_block_matches_the_assembled_keys() -> None:
    """Every declared Stan datum is supplied, and nothing extra is sent."""
    with open(STAN_FILE, encoding="utf-8") as fh:
        text = fh.read()
    block = re.search(r"^data \{(.*?)^\}", text, re.MULTILINE | re.DOTALL)
    assert block is not None, "sentinel_attribution.stan has no data block"
    declared = set(
        re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*;", re.sub(r"//.*", "", block.group(1))),
    )
    data, _ = stan_data([40])
    assert declared == set(data), f"declared {sorted(declared)} vs sent {sorted(data)}"


def test_shapes_and_port_order() -> None:
    data, meta = stan_data([30, 40, 50])
    assert meta["ports"] == ["KYGEC", "MXCZM"]  # alphabetical, not itinerary order
    assert data["P"] == 2
    assert data["G"] == len(GROUPS) == 2
    assert np.asarray(data["onsets"]).shape == (2, data["T"])
    assert np.asarray(data["ashore_hours"]).shape == (2, data["T"], 2)
    assert np.asarray(data["aboard_hours"]).shape == (2, data["T"])
    assert len(data["w_gen_raw"]) == data["L_gen"]
    assert len(data["f_inc_raw"]) == data["L_inc"]
    assert meta["port_visit_keys"]["MXCZM"].startswith("MXCZM@")


def test_hours_are_raw_so_censoring_is_not_applied_twice() -> None:
    """The Stan model truncates the convolution; the offset must not pre-discount."""
    v = voyage()
    b = bundle([40], observation_end_epoch=96)
    design = build_exposure_design(v, b, INCUBATION, ascertainment=0.5)
    data, meta = build_sentinel_attribution_data(design, v, b, INCUBATION, GENERATION)

    ashore = np.asarray(data["ashore_hours"])
    for i, port_id in enumerate(meta["ports"]):
        cells = [c for c in design.port_cells if c.port_id == port_id]
        raw = sum(c.person_hours_ashore for c in cells)
        effective = sum(c.effective_person_hours for c in cells)
        assert effective < raw, "fixture should have a censoring/ascertainment discount"
        assert ashore[:, :, i].sum() == pytest.approx(raw)
    # ascertainment is passed as data instead, once
    assert data["ascertainment"] == pytest.approx(0.5)


def test_ashore_hours_land_only_in_ashore_epochs() -> None:
    data, meta = stan_data([40])
    ashore = np.asarray(data["ashore_hours"])
    czm = ashore[:, :, meta["ports"].index("MXCZM")].sum(axis=0)
    occupied = np.nonzero(czm)[0] + 1
    # day 2 = epochs 25..48; ashore window is inside it
    assert occupied.min() >= 25
    assert occupied.max() <= 48


def test_aboard_hours_are_net_of_shore_leave() -> None:
    ashore_on = np.asarray(stan_data([40], crew_fraction=0.5)[0]["aboard_hours"])
    ashore_off = np.asarray(stan_data([40], crew_fraction=0.0)[0]["aboard_hours"])
    crew = GROUPS.index(CREW)
    assert ashore_on[crew].sum() < ashore_off[crew].sum()
    assert (ashore_on >= 0.0).all()


def test_onsets_split_by_person_group() -> None:
    pax = np.asarray(stan_data([40, 41])[0]["onsets"])
    crew = np.asarray(stan_data([40, 41], crew_cases=True)[0]["onsets"])
    assert pax[GROUPS.index(PASSENGER)].sum() == 2
    assert pax[GROUPS.index(CREW)].sum() == 0
    assert crew[GROUPS.index(CREW)].sum() == 2


def test_onsets_past_the_window_are_dropped_not_piled_on_the_last_epoch() -> None:
    data, _ = stan_data([40, 200])
    assert np.asarray(data["onsets"]).sum() == 1


def test_generation_weights_are_strictly_lagged() -> None:
    data, _ = stan_data([40])
    w = np.asarray(data["w_gen_raw"])
    assert w.size == GENERATION.weights.size - 1
    assert np.allclose(w, GENERATION.strictly_lagged().weights[1:])


def test_no_ashore_exposure_is_an_error_not_a_silent_zero() -> None:
    v = voyage_from_config(
        {
            "voyage": {
                "effects_enabled": True,
                "total_epochs": 48,
                "epoch_duration_hours": 1,
                "embarkation_date": "2026-03-01",
                "itinerary": [
                    {"day": 1, "type": "embarkation", "port": "Miami", "port_id": "USMIA"},
                    {"day": 2, "type": "sea_day"},
                ],
            },
        },
        voyage_id="V1",
        ship_id="s1",
        n_passengers=100,
        n_crew=40,
    )
    b = bundle([10], observation_end_epoch=48)
    design = build_exposure_design(v, b, INCUBATION)
    assert attribution_ports(design) == ()
    with pytest.raises(ValueError, match="no port has positive ashore exposure"):
        build_sentinel_attribution_data(design, v, b, INCUBATION, GENERATION)


def test_prior_medians_must_be_positive_rates() -> None:
    v = voyage()
    b = bundle([40])
    design = build_exposure_design(v, b, INCUBATION)
    with pytest.raises(ValueError, match="prior medians must be positive"):
        build_sentinel_attribution_data(
            design, v, b, INCUBATION, GENERATION, hazard_prior_median=0.0,
        )


def test_prior_means_are_log_rates_per_person_hour() -> None:
    data, _ = stan_data([40])
    assert data["hazard_log_prior_mean"] == pytest.approx(math.log(1e-4))
    assert data["baseline_log_prior_mean"] == pytest.approx(math.log(1e-5))


# --- forward model -------------------------------------------------------


def test_zero_hazards_give_zero_expected_onsets() -> None:
    data, _ = stan_data([40])
    mu = expected_onsets_from_data(
        data, lambda_port=[0.0, 0.0], lambda_aboard=0.0, r_onboard=0.9,
    )
    assert mu.sum() == 0.0, "secondaries cannot appear without an index infection"


def test_expected_onsets_scale_linearly_in_the_hazard_without_secondaries() -> None:
    data, _ = stan_data([40])
    one = expected_onsets_from_data(
        data, lambda_port=[1e-5, 1e-5], lambda_aboard=0.0, r_onboard=0.0,
    )
    ten = expected_onsets_from_data(
        data, lambda_port=[1e-4, 1e-4], lambda_aboard=0.0, r_onboard=0.0,
    )
    assert ten.sum() == pytest.approx(10.0 * one.sum())


def test_r_onboard_adds_only_later_onsets() -> None:
    data, _ = stan_data([40])
    kwargs = {"lambda_port": [1e-5, 1e-5], "lambda_aboard": 0.0}
    inc_off, _ = forward_incidence(data, r_onboard=0.0, **kwargs)
    inc_on, _ = forward_incidence(data, r_onboard=0.8, **kwargs)
    first = int(np.nonzero(inc_off.sum(axis=0))[0][0])
    assert inc_on[:, first] == pytest.approx(inc_off[:, first])
    assert inc_on.sum() > inc_off.sum()


def test_truncation_at_the_horizon_loses_late_onsets() -> None:
    """A port call one day before the window closes cannot show all its onsets."""
    long_data, _ = stan_data([40], observation_end_epoch=96)
    short_data, _ = stan_data([40], observation_end_epoch=80)
    kwargs = {"lambda_port": [1e-5, 1e-5], "lambda_aboard": 0.0, "r_onboard": 0.0}
    long_mu = expected_onsets_from_data(long_data, **kwargs)
    short_mu = expected_onsets_from_data(short_data, **kwargs)
    assert short_mu.sum() < long_mu.sum()
    # and the loss is the incubation tail, not the exposure: same ashore hours
    assert np.asarray(short_data["ashore_hours"]).sum() == pytest.approx(
        np.asarray(long_data["ashore_hours"]).sum(),
    )


def test_ascertainment_scales_expected_onsets() -> None:
    full, _ = stan_data([40], ascertainment=1.0)
    half, _ = stan_data([40], ascertainment=0.5)
    kwargs = {"lambda_port": [1e-5, 1e-5], "lambda_aboard": 0.0, "r_onboard": 0.3}
    assert expected_onsets_from_data(half, **kwargs).sum() == pytest.approx(
        0.5 * expected_onsets_from_data(full, **kwargs).sum(),
    )


def test_incidence_respects_the_group_secondary_share() -> None:
    data, _ = stan_data([40])
    incidence, _ = forward_incidence(
        data, lambda_port=[1e-5, 1e-5], lambda_aboard=1e-6, r_onboard=0.9,
    )
    share = np.asarray(data["secondary_share_raw"], dtype=float)
    share = share / share.sum()
    assert share[GROUPS.index(PASSENGER)] > share[GROUPS.index(CREW)]
    assert incidence[GROUPS.index(PASSENGER)].sum() > incidence[GROUPS.index(CREW)].sum()


def test_pax_ashore_cells_exist_for_both_ports() -> None:
    """Guards the group mapping the data builder relies on."""
    v = voyage()
    b = bundle([40])
    design = build_exposure_design(v, b, INCUBATION)
    ashore_ports = {c.port_id for c in design.port_cells if c.stratum == PAX_ASHORE}
    assert ashore_ports == {"MXCZM", "KYGEC"}
