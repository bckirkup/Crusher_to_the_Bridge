"""Behaviour of the exposure-concentration and curvature diagnostics.

Sensitivity and invariants, per `.agents/skills/ci-test-design/SKILL.md`. The
quantities under test are diagnostics of the shipped model, not parameters, so
the assertions are analytic properties (Gini bounds, Lorenz ordering, the
linear and saturating limits of the dose-response) rather than recorded values.
"""

import math

import pytest

from telemetry_buffer.observation_model.dose_concentration_readout import (
    coincidence,
    concentration,
    curvature_utilisation,
    patchiness_cost,
    route_sd_streams,
    route_streams,
)


def event(
    dose: float,
    susceptibility: float = 1.0,
    epoch: int = 0,
    agent_id: int = 1,
    zone: str = "Dining_1",
    routes: dict[str, float] | None = None,
):
    """One recorded establishment draw, shaped as the hook records it."""
    return {
        "epoch": epoch,
        "agent_id": agent_id,
        "agent_class": "passenger",
        "zone": zone,
        "pathogen_id": "norwalk_gi",
        "dose": dose,
        "susceptibility": susceptibility,
        "hazard": -math.expm1(-susceptibility * dose),
        "routes": routes if routes is not None else {"direct_contact": dose},
    }


def test_gini_grades_with_concentration():
    """A more unequal stream of the same total scores a higher Gini."""
    streams = [
        [1.0] * 5,
        [2.0, 0.75, 0.75, 0.75, 0.75],
        [4.0, 0.25, 0.25, 0.25, 0.25],
        [4.996, 0.001, 0.001, 0.001, 0.001],
    ]
    ginis = [concentration(s).gini for s in streams]

    assert ginis == sorted(ginis)
    assert ginis[-1] - ginis[0] > 0.5
    assert all(0.0 <= g <= 1.0 for g in ginis)


def test_gini_of_a_flat_stream_is_zero():
    """An equal allocation has no concentration to report."""
    assert concentration([2.5] * 16).gini == pytest.approx(0.0, abs=1e-12)


def test_top_shares_are_ordered_and_bounded():
    """Lorenz shares rise with the quantile and never exceed the whole."""
    conc = concentration([float(i) for i in range(1, 1001)])
    shares = [conc.top_shares[q] for q in (0.001, 0.01, 0.1)]

    assert shares == sorted(shares)
    assert all(0.0 < s <= 1.0 for s in shares)
    assert conc.total == pytest.approx(500500.0)


def test_concentration_ignores_nonpositive_and_empty_streams():
    """Zero-dose host-epochs are not exposures, and an empty stream is safe."""
    assert concentration([0.0, 0.0, 3.0]).count == 1
    empty = concentration([])
    assert empty.count == 0
    assert empty.total == pytest.approx(0.0)
    assert math.isnan(empty.gini)


def test_curvature_utilisation_reaches_the_linear_limit():
    """Small sD leaves establishment proportional to dose: dispersion is inert."""
    tiny = curvature_utilisation([event(1e-9) for _ in range(50)])
    assert tiny["utilisation"] == pytest.approx(1.0, abs=1e-6)
    assert tiny["share_sD_above_1"] == pytest.approx(0.0)


def test_curvature_utilisation_falls_as_the_stream_saturates():
    """Larger sD spends more dose on hosts already certain to be infected."""
    scales = [1e-6, 1e-2, 1.0, 100.0]
    used = [
        curvature_utilisation([event(s) for _ in range(20)])["utilisation"]
        for s in scales
    ]

    assert used == sorted(used, reverse=True)
    assert used[0] > 0.99
    assert used[-1] < 0.02
    assert all(0.0 < u <= 1.0 for u in used)


def test_curvature_reports_where_the_hazard_came_from():
    """One saturated draw beside many dead ones carries the whole hazard."""
    curv = curvature_utilisation(
        [event(50.0)] + [event(1e-12) for _ in range(999)],
    )

    assert curv["share_sD_above_1"] == pytest.approx(0.001)
    assert curv["hazard_share_from_sD_above_1"] > 0.99
    assert curv["max_sD"] == pytest.approx(50.0)


def test_susceptibility_scales_sd_not_dose():
    """The dose-response sees s*D, so frailty moves the regime by itself."""
    frail = curvature_utilisation([event(1.0, susceptibility=1.0)])
    resistant = curvature_utilisation([event(1.0, susceptibility=1e-6)])

    assert frail["utilisation"] < 0.7
    assert resistant["utilisation"] > 0.99


def test_patchiness_cost_is_neutral_in_the_linear_limit():
    """Where the map is linear, how the dose is allocated cannot matter."""
    cost = patchiness_cost([1e-8] * 99 + [1e-6])
    assert cost["realised_over_flat"] == pytest.approx(1.0, abs=1e-4)


def test_patchiness_cost_penalises_a_saturating_allocation():
    """The same total delivered to one host infects fewer than spread over many."""
    total = 100.0
    n = 100
    concentrated = patchiness_cost([total] + [0.0] * (n - 1))
    spread = patchiness_cost([total / n] * n)

    assert concentrated["realised_establishments"] < 1.001
    assert spread["realised_establishments"] > 50.0
    assert concentrated["realised_over_flat"] < spread["realised_over_flat"]
    assert spread["realised_over_flat"] == pytest.approx(1.0, abs=1e-9)


def test_patchiness_cost_never_reports_more_than_flat():
    """1 - exp(-x) is concave, so the flat allocation is the upper bound."""
    for stream in ([1.0, 1.0, 1.0], [10.0, 0.1, 0.01], [5.0, 5.0, 1e-6]):
        cost = patchiness_cost(stream)
        assert cost["realised_over_flat"] <= 1.0 + 1e-12


def test_route_streams_split_dose_and_sd_by_route():
    """Each route's stream carries its own dose, scaled by the host's frailty."""
    events = [
        event(3.0, susceptibility=0.5, routes={"fomite": 2.0, "food": 1.0}),
        event(1.0, susceptibility=0.5, routes={"fomite": 1.0, "food": 0.0}),
    ]

    doses = route_streams(events)
    assert doses["fomite"] == [2.0, 1.0]
    assert doses["food"] == [1.0]

    sd = route_sd_streams(events)
    assert sd["fomite"] == [1.0, 0.5]
    assert "food" in sd


def test_coincidence_separates_a_shared_patch_from_solo_noise():
    """A cell reaching many hosts is correlated exposure; one host is noise."""
    shared = [
        event(10.0, epoch=1, agent_id=i, zone="Dining_1") for i in range(20)
    ]
    solo = [
        event(10.0, epoch=e, agent_id=e, zone=f"Cabin_{e}")
        for e in range(2, 22)
    ]

    assert coincidence(shared)["all_mean_hosts"] == pytest.approx(20.0)
    assert coincidence(shared)["single_host_cell_share"] == pytest.approx(0.0)
    assert coincidence(solo)["all_mean_hosts"] == pytest.approx(1.0)
    assert coincidence(solo)["single_host_cell_share"] == pytest.approx(1.0)


def test_coincidence_top_cell_share_bounded_and_empty_safe():
    """The heaviest cells' share is a fraction, and no events report nothing."""
    events = [
        event(float(i), epoch=i, agent_id=i, zone=f"Zone_{i}")
        for i in range(1, 201)
    ]
    coin = coincidence(events)

    assert 0.0 < coin["top1pct_dose_share"] <= 1.0
    assert coin["cells"] == pytest.approx(200.0)
    assert coincidence([]) == {}
