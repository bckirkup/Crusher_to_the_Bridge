"""Fleet sentinel source+market channels: provisioning, embarkation, covariates.

The reverse-inference revision of
``docs/sentinel/sentinel_source_market_revision.md``: provisioned servings are
a per-serving hazard channel pooled per source_id, boarded carriers are a
per-capita prevalence pooled per embarkation market, and voyage covariates
multiply all import channels. These tests cover the contract — schema parsing,
Stan data assembly, forward-incidence sensitivity, and the design-only confound
flags — without sampling (the slow recovery suite covers the walk).
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from picard_framework.analysis.sentinel.fleet import (  # noqa: E402
    market_home_confounded,
    source_home_confounded,
    summarize_market_hazards,
    summarize_source_hazards,
)
from picard_framework.analysis.sentinel.observations import (  # noqa: E402
    bundle_from_dict,
)
from picard_framework.analysis.stan._sentinel_fleet_data import (  # noqa: E402
    FleetRates,
    fleet_forward_incidence,
)
from tests.test_sentinel_fleet import fleet_data, fleet_voyage  # noqa: E402


def _provisioning(window=(10, 72), pax=12000, crew=3000):
    return {
        "MIA-PROV-01": {
            "servings_total": {"passenger": pax, "crew": crew},
            "service_window_epochs": list(window),
        },
    }


def _embarkation():
    return {"markets": {"passenger": "NA-CARIB", "crew": "LATAM-CREW"}}


def _fleet(**kwargs):
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


def _rates(data, **overrides):
    base = dict(
        lambda_visit=[1e-4] * data["NV"],
        lambda_aboard=[1e-5] * data["S"],
        r_onboard=[0.6] * data["S"],
    )
    base.update(overrides)
    return FleetRates(**base)


def test_bundle_parses_provisioning_embarkation_and_covariates() -> None:
    bundle = bundle_from_dict(
        {
            "voyage_id": "V1",
            "ship_id": "s",
            "clinical_cases": [],
            "provisioning": {
                "SRC": {
                    "servings_total": {"passenger": 10, "crew": 4},
                    "service_window_epochs": [5, 9],
                },
            },
            "embarkation": {
                "markets": {"passenger": "MKT-P", "crew": "MKT-C"},
                "n_boarded": {"crew": 500},
            },
            "covariates": {"child_fraction": 0.08},
        },
    )
    assert bundle.provisioning[0].source_id == "SRC"
    assert bundle.provisioning[0].servings_total["passenger"] == 10.0
    assert bundle.provisioning[0].service_window_epochs == (5, 9)
    assert bundle.provisioning[0].first_service_epoch == 5
    assert bundle.embarkation.markets["crew"] == "MKT-C"
    assert bundle.embarkation.n_boarded == {"crew": 500.0}
    assert bundle.covariates["child_fraction"] == pytest.approx(0.08)


def test_provisioning_rejects_bad_shapes() -> None:
    base = {"voyage_id": "V1", "ship_id": "s", "clinical_cases": []}
    with pytest.raises(ValueError, match="service_window"):
        bundle_from_dict(
            {**base, "provisioning": {"SRC": {"servings_total": {"passenger": 1}}}},
        )
    with pytest.raises(ValueError, match="unknown stratum"):
        bundle_from_dict(
            {
                **base,
                "provisioning": {"SRC": {"servings_per_epoch": {"galley": [1]}}},
            },
        )
    with pytest.raises(ValueError, match="negative"):
        bundle_from_dict(
            {
                **base,
                "provisioning": {
                    "SRC": {
                        "servings_total": {"passenger": -1},
                        "service_window_epochs": [1, 3],
                    },
                },
            },
        )
    with pytest.raises(ValueError, match="markets"):
        bundle_from_dict({**base, "embarkation": {"markets": {}}})


def test_data_builder_lays_out_the_new_channels() -> None:
    fleet = _fleet(provisioning=_provisioning(), embarkation=_embarkation())
    data, meta = fleet_data(fleet)

    assert data["NS"] == 1
    assert data["NM"] == 2
    assert data["market_idx"] == [[2, 1], [2, 1]]  # sorted: LATAM-CREW, NA-CARIB
    assert data["embark_persons"] == [[1000.0, 400.0]] * 2
    assert data["embark_epoch"] == [1, 1]
    prov = np.asarray(data["prov_servings"])
    assert prov.shape == (2, 2, data["Tmax"], 1)
    # 63-epoch window: total spread uniformly, groups on their own rows.
    assert prov[0, 0, :, 0].sum() == pytest.approx(12000)
    assert prov[0, 1, :, 0].sum() == pytest.approx(3000)
    assert prov[0, 0, 9, 0] > 0 and prov[0, 0, 8, 0] == 0
    assert meta["sources"][0]["source_id"] == "MIA-PROV-01"
    assert meta["sources"][0]["voyages"] == ["A1", "B1"]
    assert meta["sources"][0]["total_servings"] == pytest.approx(30000)
    assert meta["sources"][0]["first_service_epoch"] == {"A1": 10, "B1": 10}
    assert {m["market_id"] for m in meta["markets"]} == {"LATAM-CREW", "NA-CARIB"}


def test_per_epoch_servings_form_is_taken_as_declared() -> None:
    provisioning = {
        "SRC": {"servings_per_epoch": {"passenger": [5, 5, 5], "crew": [1, 1, 1]}},
    }
    data, meta = fleet_data(_fleet(provisioning=provisioning))
    prov = np.asarray(data["prov_servings"])
    assert prov[0, 0, :3, 0].tolist() == [5.0, 5.0, 5.0]
    assert prov[0, 1, :3, 0].tolist() == [1.0, 1.0, 1.0]
    assert prov[0, 0, 3, 0] == 0.0


def test_covariates_line_up_across_the_fleet() -> None:
    fleet = [
        fleet_voyage(
            voyage_id="A1",
            ship_id="shipA",
            embarkation_date="2026-03-02",
            ports=((2, "MXCZM"),),
            covariates={"child_fraction": 0.05},
        ),
        fleet_voyage(
            voyage_id="B1",
            ship_id="shipB",
            embarkation_date="2026-03-02",
            ports=((2, "MXCZM"),),
            # no covariates: a missing name reads as 0, not absent
        ),
        fleet_voyage(
            voyage_id="C1",
            ship_id="shipC",
            embarkation_date="2026-03-09",
            ports=((2, "KYGEC"),),
            covariates={"child_fraction": 0.12, "avg_age": 55.0},
        ),
    ]
    data, meta = fleet_data(fleet)
    assert data["K"] == 2
    assert meta["covariate_names"] == ["avg_age", "child_fraction"]
    assert data["X"] == [[0.0, 0.05], [0.0, 0.0], [55.0, 0.12]]


def test_forward_incidence_grades_with_the_new_channels() -> None:
    """Graded sensitivity: several channel settings, monotone ordering."""
    data, _ = fleet_data(_fleet(provisioning=_provisioning(),
                                embarkation=_embarkation()))
    none = _rates(data)
    prov_only = _rates(data, kappa=[1e-3])
    market_only = _rates(data, epsilon=[0.05, 0.02])
    both = _rates(data, kappa=[1e-3], epsilon=[0.05, 0.02])
    totals = {
        k: [float(i.sum()) for i in fleet_forward_incidence(data, r)[0]]
        for k, r in (
            ("none", none), ("prov", prov_only), ("mkt", market_only),
            ("both", both),
        )
    }
    for v in range(2):
        assert totals["prov"][v] > totals["none"][v]
        assert totals["mkt"][v] > totals["none"][v]
        assert totals["both"][v] > totals["prov"][v]
        assert totals["both"][v] > totals["mkt"][v]
    # prov channel adds exactly servings x kappa in expectation, plus whatever
    # secondaries those imports renew: bounded below by the imports themselves.
    delta = totals["prov"][0] - totals["none"][0]
    assert 15.0 - 1e-6 <= delta < 40.0
    # market imports land at embark_epoch: 1000*0.02 + 400*0.05 = 40
    mkt_delta = totals["mkt"][0] - totals["none"][0]
    assert 40.0 - 1e-6 <= mkt_delta < 120.0


def test_market_channel_lands_at_the_embark_epoch() -> None:
    data, _ = fleet_data(_fleet(embarkation=_embarkation()))
    none = _rates(data, epsilon=[0.0, 0.0])
    crew_mkt = _rates(data, epsilon=[0.05, 0.0])
    base = fleet_forward_incidence(data, none)[0][0]
    with_mkt = fleet_forward_incidence(data, crew_mkt)[0][0]
    delta = with_mkt - base
    # crew market = index 1 (LATAM-CREW): 0.05 * 400 = 20, all at epoch 0.
    assert delta[1, 0] == pytest.approx(20.0)
    assert delta[0, 0] == pytest.approx(0.0)
    # past the embark epoch the only movement is renewal of those imports —
    # nonzero but tiny, never a fresh import term.
    assert delta[0, 1] == pytest.approx(0.0, abs=1e-6)
    assert (delta[1, 1:] >= -1e-9).all()


def test_susceptibility_scales_imports_not_aboard() -> None:
    data, _ = fleet_data(_fleet(provisioning=_provisioning()))
    susc_none = _rates(data, kappa=[1e-3])
    susc_two = _rates(data, kappa=[1e-3], susceptibility=[2.0] * data["V"])
    inc0 = fleet_forward_incidence(data, susc_none)[0][0]
    inc1 = fleet_forward_incidence(data, susc_two)[0][0]
    # the prov channel (15 imports) doubles; the aboard baseline (35.2) does
    # not move, so the extra incidence is at least the doubled imports.
    assert inc1.sum() - inc0.sum() >= 15.0 - 1e-6


def test_confound_flags_fire_when_home_port_and_timing_coincide() -> None:
    fleet = _fleet(provisioning=_provisioning(), embarkation=_embarkation(),
                   embark_window=(10, 16), disembark_window=(10, 14))
    _, meta = fleet_data(fleet)
    # Both voyages embark USMIA and the source starts serving inside the embark
    # window (epoch 10 <= day-1 end), so both flags fire.
    assert source_home_confounded(meta) == frozenset({"MIA-PROV-01"})
    assert market_home_confounded(meta) == frozenset({"LATAM-CREW", "NA-CARIB"})


def test_confound_flags_clear_when_service_starts_after_embark() -> None:
    _, meta = fleet_data(
        _fleet(provisioning=_provisioning(window=(48, 96)),
               embarkation=_embarkation(), embark_window=(10, 16), disembark_window=(10, 14)),
    )
    assert source_home_confounded(meta) == frozenset()
    # the market flag is about the shared home port, not serving times
    assert market_home_confounded(meta) == frozenset({"LATAM-CREW", "NA-CARIB"})


def test_confound_flags_clear_when_home_ports_differ() -> None:
    voyages = _fleet(provisioning=_provisioning(), embarkation=_embarkation(),
                     embark_window=(10, 16), disembark_window=(10, 14))
    # Rehome ship B at Port Canaveral: markets/sources no longer share one port.
    voyages[1] = fleet_voyage(
        voyage_id="B1",
        ship_id="shipB",
        embarkation_date="2026-03-02",
        ports=((2, "KYGEC"), (5, "MXCZM")),
        provisioning=_provisioning(),
        embarkation={"markets": {"passenger": "NA-CARIB", "crew": "LATAM-CREW"}},
        embark_window=(10, 16),
        disembark_window=(10, 14),
        home_port_id="USPCV",
    )
    _, meta = fleet_data(voyages)
    assert source_home_confounded(meta) == frozenset()
    assert market_home_confounded(meta) == frozenset()


def test_empty_channels_keep_the_old_data_shape() -> None:
    data, meta = fleet_data(_fleet())
    assert data["NS"] == 0 and data["NM"] == 0 and data["K"] == 0
    assert meta["sources"] == [] and meta["markets"] == []
    # and the forward path is unchanged
    inc = fleet_forward_incidence(data, _rates(data))[0]
    assert float(inc[0].sum()) > 0.0


def test_summaries_read_the_new_columns() -> None:
    fleet = _fleet(provisioning=_provisioning(), embarkation=_embarkation(),
                   embark_window=(10, 16), disembark_window=(10, 14))
    data, meta = fleet_data(fleet)
    draws = 25
    posterior = {
        "kappa[1]": np.full(draws, 1e-3),
        "imported_cases_source[1]": np.full(draws, 15.0),
        "attribution_share_source[1]": np.full(draws, 0.2),
        "epsilon[1]": np.full(draws, 0.05),
        "epsilon[2]": np.full(draws, 0.02),
        "imported_cases_market[1]": np.full(draws, 20.0),
        "imported_cases_market[2]": np.full(draws, 20.0),
        "attribution_share_market[1]": np.full(draws, 0.1),
        "attribution_share_market[2]": np.full(draws, 0.1),
    }
    sources = summarize_source_hazards(posterior, meta)
    markets = summarize_market_hazards(posterior, meta)
    assert sources[0].source_id == "MIA-PROV-01"
    assert sources[0].hazard_mean == pytest.approx(1e-3)
    assert sources[0].n_voyages == 2
    assert sources[0].home_confounded
    assert {m.market_id for m in markets} == {"LATAM-CREW", "NA-CARIB"}
    assert markets[0].prevalence_mean == pytest.approx(0.05)
    assert all(m.home_confounded for m in markets)
