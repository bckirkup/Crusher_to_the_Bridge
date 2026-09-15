"""One end-to-end COVID hull cell as a labelled change detector.

The composite-Theta campaign (covid_first_look_v1) is distributional, so no
single cell decides anything there. This module exists for a different reason:
so that a shared engine change — initiation, boarding, contact structure,
syndromic onset handling — that moves the COVID arm is *noticed* when it
lands, rather than a campaign later. Note the limit: a last-bit float change
anywhere on the transmission path re-rolls the seed's trajectory and moves
this cell by ~5–13% without changing the engine's scale, so a failure here
says "attribute the move", not "the scale changed" (see
docs/covid/covid_first_look_readout.md).

The cell is the cheapest one on the grid: Greg Mortimer (the held-out hull, so
pinning it leaks nothing into the fit), Theta = 1e6, seed 20200333, ~15 s. It
was measured on AWS Batch and reproduced bit-for-bit in the campaign image and
in a local CPython 3.11 environment. Under the declared scenario (one index
case, no boarding cohort) this cell does not take off: a one-import Greg
Mortimer run at Theta 1e6 goes extinct in most seeds (0-8 onsets over seeds
20200333-20200348 on both interpreters), so the bound below is that the index
case was ascertained at all, not that an outbreak followed.

CHANGE DETECTOR, not a correctness check. The pinned values are not
independently derived; they only pin current behaviour. If a deliberate change
moves them, attribute the move to a specific part of the diff, then update
them and say why. Failing means "something moved", not "something broke".

The golden is keyed by interpreter minor version because CPython 3.12 changed
builtin ``sum()`` to compensated (Neumaier) summation for floats. Route-dose
and shedding totals in engines/transmission_core.py pass through ``sum()``, so
the same seed follows a different Bernoulli path on 3.12 than on 3.11 — that,
not an entropy leak, is why the identical cell read 85 onsets locally and 96 on
Batch. Both interpreters are deterministic on their own; they simply disagree.
Neither numpy (2.4.6 vs 2.5.0) nor scipy (1.17.1 vs 1.18.1) moves the cell.
"""

from __future__ import annotations

import sys
from dataclasses import asdict

import pytest

from picard_framework.covid_theta_fit import HullObservables, simulate_hull

HULL = "greg_mortimer_2020"
THETA = 1e6
SEED = 20200333

PINNED_FIELDS = (
    "recorded_onsets",
    "onsets_before_split_day",
    "campaign_specimens",
    "campaign_positives",
    "campaign_asymptomatic_positives",
)

# (onsets, onsets before split day, specimens, positives, asymptomatic positives)
GOLDEN_BY_PYTHON_MINOR: dict[tuple[int, int], tuple[int, ...]] = {
    # CI and the Batch worker image (picard-campaign, CPython 3.11). The
    # covid_first_look_v1 cell held_out_greg_mortimer_2020_theta1e6p00_
    # seed20200333.json read (96, 52, 106, 36, 36) before either of two
    # merged changes moved it: the molecular ascertainment gate (#537,
    # scenario field molecular_ascertainment.start_day, closing the
    # passive swab channel until the day-20 screen) alone moved it to
    # (68, 20, 217, 104, 59), and the expedition_cruise_450 Bridge zone
    # (#538, shared_sanitary_zones) re-weights the crew work-zone draws
    # and alone moved it to (74, 42, 113, 21, 21). The tuple below is the
    # composition, repinned from CI job test (fast tier, 3.11) on the
    # merged tree. It read (47, 14, 217, 70, 37) while the COVID hull spec
    # left the ship-wide boarding channel open for sars_cov2_resp, so every
    # cell boarded a prevalence-drawn cohort (profile 1% passengers, 0.6%
    # crew, epoch 6) on top of the declared index case; the opt-out in
    # HullScenario._initiation_block removes that cohort and alone moved
    # the cell to (1, 1, 217, 3, 2) (campaign image, CPython 3.11.16).
    # Two incubation changes then moved it, each measured alone on this
    # cell: an infection with no inoculum on record (the declared index
    # case) is drawn at the reference dose instead of the literal-zero
    # floor (natural_history.incubation_days; median 5.8 d, not 14.5 d),
    # which alone gives (3, 1, 217, 2, 1); and the composite-Theta arm
    # re-references the incubation dose term to the N50 of the exponential
    # model it installs, ln 2 / Theta (covid_theta_fit.theta_profile_
    # overrides), so secondary cases are no longer all drawn at the
    # ceiling either, which on top gives the tuple below. Both
    # interpreters agree on this cell now: it is a near-extinct run with
    # few Bernoulli draws for the two float-sum paths to disagree on.
    (3, 11): (5, 0, 217, 6, 4),
    # Local CPython 3.12 venv (compensated float sum). Was (85, 51, 102,
    # 30, 30) before the same two merged changes: #537's ascertainment
    # gate alone moved it to (58, 14, 217, 93, 52) and the #538 Bridge
    # zone alone moved it to (82, 46, 113, 25, 24); the tuple below is
    # the composition, measured on the merged tree, and read (53, 15, 217,
    # 74, 39) with the boarding cohort; the same opt-out alone moved it to
    # (1, 1, 217, 3, 2). The two incubation changes above then moved it
    # to (3, 1, 217, 2, 1) (reference-dose draw for the index case alone)
    # and to the tuple below (with the Theta-arm re-reference).
    (3, 12): (5, 0, 217, 6, 4),
}


@pytest.fixture(scope="module")
def cell() -> HullObservables:
    return simulate_hull(HULL, THETA, SEED)


def _pinned(obs: HullObservables) -> tuple[int, ...]:
    d = asdict(obs)
    return tuple(int(d[k]) for k in PINNED_FIELDS)


def test_the_cell_recorded_its_index_case_and_stays_in_bounds(cell):
    assert cell.recorded_onsets >= 1
    assert 0 <= cell.onsets_before_split_day <= cell.recorded_onsets
    assert (
        cell.onsets_before_split_day + cell.onsets_on_or_after_split_day
        == cell.recorded_onsets
    )
    assert 0 <= cell.campaign_asymptomatic_positives <= cell.campaign_positives
    assert cell.campaign_positives <= cell.campaign_specimens


def test_the_same_seed_reproduces_the_same_cell(cell):
    again = simulate_hull(HULL, THETA, SEED)
    assert _pinned(again) == _pinned(cell)


def test_the_cell_matches_its_pinned_reading(cell):
    key = (sys.version_info.major, sys.version_info.minor)
    if key not in GOLDEN_BY_PYTHON_MINOR:
        pytest.skip(f"no pinned reading for CPython {key[0]}.{key[1]}")
    assert _pinned(cell) == GOLDEN_BY_PYTHON_MINOR[key], (
        "COVID hull cell moved; attribute the move before repinning "
        f"(fields {PINNED_FIELDS})"
    )
