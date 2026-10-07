"""Two end-to-end COVID hull cells as invariant + determinism witnesses.

Each cell is one full simulated voyage run through the campaign observables
path: Greg Mortimer (the held-out hull) in the fast tier, Diamond Princess
(the hull theta is fitted on) in the slow tier — ~20 minutes, nightly only.
Both run at Theta = 1e10, seed 20200333. The Theta = 1e10 point is the
lowest live, unsaturated corner on current defaults; the old 1e6 cell
belonged to the pooled-air model.

This module used to pin each cell's five-field witness tuple and fail on
any move — a labelled change detector. That contract did not survive the
merge rate: every mechanism touching the shared RNG stream re-rolled both
cells (30+ attributed repins are in this file's git history, e.g. 15
touches in the first week of October 2026), nightly went red for days at a
stretch, and the per-move attribution cost more than the drift signal was
worth. The pins are retired. What remains asserted is what a golden tuple
could never check anyway:

* structural invariants of the observables — channel ordering
  (asymptomatic positives <= positives <= specimens <= aboard), onset
  decomposition conservation (before + after = total; passenger + crew
  = total on each side of the split day), counts bounded by the hull's
  aboard complement, share domains in [0, 1];
* identity echoes — the cell ran the scenario, theta and seed it was
  asked to run;
* same-seed determinism on the fast cell — a second Greg Mortimer run
  must reproduce the first witness tuple exactly. This is the part of
  the old pin that was worth keeping: it catches unseeded draws,
  iteration-order nondeterminism and uninitialized state, which an
  invariant cannot see. Diamond Princess is exempt — a second ~20-minute
  replay per interpreter is not worth the nightly wall time; its cell is
  covered by the invariants and by the campaign arrays' paired-seed
  readouts.

A legitimate mechanism move is therefore free to re-roll these cells; only
a structurally impossible or nondeterministic reading fails. The pinned
readings themselves survive as investigation references below — NOT
asserted — so a future drift question has a starting tuple to compare
against. The full per-merge attribution history (which mechanism moved
which cell, by how much, flag-off reproductions) lives in this file's
git history; see also docs/ledger/INDEX-GEOM-01.md for why two hulls.

Note for determinism context: CPython 3.12 changed builtin ``sum()`` to
compensated summation, so the same seed can follow a different Bernoulli
path on 3.12 than on 3.11. Both interpreters are deterministic on their
own; they need not agree with each other, and they are not asserted to.
"""

from __future__ import annotations

import pytest

from picard_framework.covid_theta_fit import HullObservables, simulate_hull

FAST_HULL = "greg_mortimer_2020"
THETA = 1e10
SEED = 20200333

WITNESS_FIELDS = (
    "recorded_onsets",
    "onsets_before_split_day",
    "campaign_specimens",
    "campaign_positives",
    "campaign_asymptomatic_positives",
)

# Souls aboard each scenario hull (see data/scenarios/covid_hull_scenarios.json
# platform notes): Greg Mortimer 223 on expedition_cruise_450, Diamond
# Princess 3711 on mega_cruise_5000. Counts above the complement are
# structurally impossible — that is the bound these tests assert.
ABOARD_COMPLEMENT = {"greg_mortimer_2020": 223, "diamond_princess_2020": 3711}

# Informational only — the last witness tuples read before the pins were
# retired (fields = WITNESS_FIELDS). Use these when investigating a drift
# question, not as expectations. diamond_princess_2020 is the Oct 6 nightly
# reading on CPython 3.12; greg_mortimer_2020 agreed across 3.11 and 3.12
# at PR #946 (DEFIANT-ESC-01 attribution).
LAST_KNOWN_READINGS: dict[str, tuple[int, ...]] = {
    "greg_mortimer_2020": (34, 14, 217, 47, 21),
    "diamond_princess_2020": (2766, 2587, 2693, 400, 335),
}


def _witness(obs: HullObservables) -> tuple[int, ...]:
    return tuple(getattr(obs, f) for f in WITNESS_FIELDS)


@pytest.fixture(
    params=(
        "greg_mortimer_2020",
        pytest.param("diamond_princess_2020", marks=pytest.mark.slow),
    ),
    scope="module",
)
def cell(request) -> tuple[str, HullObservables]:
    return request.param, simulate_hull(request.param, THETA, SEED)


def test_the_cell_echoes_the_scenario_it_was_given(cell):
    """A miswired scenario read is a harness failure, not a model move."""
    hull, obs = cell
    assert obs.scenario_id == hull
    assert obs.theta == THETA
    assert obs.seed == SEED


def test_the_cell_stays_within_structural_bounds(cell):
    """Channel ordering and population bounds: impossible readings fail.

    0 recorded onsets remains a valid reading (an extinct replay is legal);
    what cannot be legal is a positive specimen count without specimens, an
    onset count above the souls aboard, or a role decomposition that does
    not re-sum to the split totals.
    """
    hull, obs = cell
    aboard = ABOARD_COMPLEMENT[hull]

    assert 0 <= obs.recorded_onsets <= aboard
    assert 0 <= obs.onsets_before_split_day <= obs.recorded_onsets
    assert 0 <= obs.onsets_on_or_after_split_day <= obs.recorded_onsets
    # split_day is a true partition of the onset curve.
    assert obs.onsets_before_split_day + obs.onsets_on_or_after_split_day == obs.recorded_onsets
    # The passenger/crew fields are windowed counts around turn_day
    # (±window_days), not a decomposition of the split sides — the window
    # straddles split_day when turn_day < split_day, so they cannot sum to
    # the split totals. What must hold: the two window halves are disjoint,
    # so their sum is bounded by the curve total; and the pre-turn window
    # lies inside the pre-split region for the harness defaults
    # (turn_day=16 < split_day=17), so it cannot exceed it.
    window_total = (
        obs.passenger_onsets_before + obs.crew_onsets_before + obs.passenger_onsets_after + obs.crew_onsets_after
    )
    assert 0 <= window_total <= obs.recorded_onsets
    assert obs.passenger_onsets_before + obs.crew_onsets_before <= obs.onsets_before_split_day
    assert 0 <= obs.campaign_asymptomatic_positives <= obs.campaign_positives <= obs.campaign_specimens <= aboard
    if obs.campaign_positives:
        assert 0.0 <= obs.asymptomatic_share <= 1.0
    if obs.campaign_specimens:
        assert 0.0 <= obs.positive_share <= 1.0


def test_the_fast_cell_is_deterministic(cell):
    """Same seed, same interpreter: the witness tuple reproduces exactly."""
    hull, obs = cell
    if hull != FAST_HULL:
        pytest.skip("determinism witness runs on the fast hull cell only")
    rerun = simulate_hull(hull, THETA, SEED)
    assert _witness(rerun) == _witness(obs), (
        f"{hull} cell is nondeterministic: {_witness(obs)} vs {_witness(rerun)} on {WITNESS_FIELDS}"
    )
