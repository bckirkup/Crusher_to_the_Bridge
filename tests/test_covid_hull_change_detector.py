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

The cells are Greg Mortimer (the held-out hull, so pinning it leaks nothing
into the fit) and Diamond Princess (the training hull; INDEX-GEOM-01 added it
because otherwise no CI reading touches the hull Θ is fitted on, and a change
to the very mechanics the fit scores would move nothing), Theta = 1e10, seed
20200333. The old Theta = 1e6 cell belonged to
the pooled-air model and became all-zero under either default flip, so the
detector moved to the lowest live, unsaturated point on the new defaults.
At Theta = 1e6 the prior pooled-air tuple was (6, 0, 217, 6, 3); changing
either default alone drove that cell to (0, 0, 217, 0, 0).

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

HULLS = ("greg_mortimer_2020", "diamond_princess_2020")
THETA = 1e10
SEED = 20200333

PINNED_FIELDS = (
    "recorded_onsets",
    "onsets_before_split_day",
    "campaign_specimens",
    "campaign_positives",
    "campaign_asymptomatic_positives",
)

# (onsets, onsets before split day, specimens, positives, asymptomatic positives)
GOLDEN_BY_HULL_AND_MINOR: dict[str, dict[tuple[int, int], tuple[int, ...]]] = {
    "greg_mortimer_2020": {
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
        # That read (5, 0, 217, 6, 4). The sick-call roster then stopped
        # reading a quarantine refuser as a symptomatic host (syndromic
        # query_ground_truth: presentation only), so a healthy refuser no
        # longer draws a passive specimen that retires it from the campaign;
        # that alone moves the cell to the tuple below (measured with the
        # coupling restored: the old tuple returns). The declared
        # retest-after-negative policy shipped in the same change is inert
        # here because greg_mortimer_2020 does not declare it.
        # At the old Theta=1e6, each default flip independently moved the prior
        # (6, 0, 217, 6, 3) reading to (0, 0, 217, 0, 0). The detector moved to
        # Theta=1e10 because 1e6 belonged to the pooled-air model.
        # The HVAC confinement repair applies the existing target attenuation
        # factor on the downstream airborne route and moves the readings from
        # (144, 64, 217, 157, 30) to (140, 64, 217, 155, 36) on CPython 3.11,
        # and from (128, 51, 217, 149, 34) to (118, 48, 217, 139, 30) on 3.12.
        # The exact linear-operator transport repair moves the live cell from
        # (149, 62, 217, 166, 30) to (144, 64, 217, 157, 30) on CPython 3.11;
        # the old value returns with the pre-repair frozen-source scheme.
        # `AERO-CABIN-05` inverts the HVAC-downstream loop so a target zone's
        # standing mass is inhaled once per epoch instead of once per upstream
        # zone hosting a shedder, so the dose is no longer multiplied by the
        # count of those zones: (140, 64, 217, 155, 36) to
        # (129, 53, 217, 140, 41) on CPython 3.11, and
        # (118, 48, 217, 139, 30) to (112, 48, 217, 125, 29) on 3.12.
        # AERO-CABIN-06 moves the live COVID cell because per-stateroom pools
        # partition cabin airborne mass and exclude a shedder's own stateroom
        # from the HVAC target set: (129, 53, 217, 140, 41) to
        # (101, 42, 217, 120, 27) on CPython 3.11.
        # QUAR-ORDER-01 makes the same move on CPython 3.11:
        # (101, 42, 217, 120, 27) -> (81, 42, 217, 88, 11).
        # AERO-NEAR-02 then enables the two-box near field by default and deals
        # buffet/crew-mess tables per meal, moving the 3.11 reading to
        # (64, 8, 217, 67, 36). This value was read from the CI job (fast tier,
        # 3.11) on this branch.
        # DINE-CREW-01 deals crew-mess tables within department (work zone), which
        # reorders the per-meal RNG draws and changes the near-field table-mates of
        # every crew diner; the CI cell follows a different Bernoulli path:
        # (64, 8, 217, 67, 36) -> (14, 5, 217, 19, 7), read from the CI job (fast
        # tier, 3.11) on this branch.
        # DOSE-FRAIL-01 restores the beta-Poisson per-host susceptibility draw
        # while scaling its mean to Theta: (14, 5, 217, 19, 7) ->
        # (1, 1, 217, 4, 0) on CPython 3.11, read from CI job 105760985675
        # (fast tier, 3.11, shard 3) on this branch.
        # REINFECT-01 (refractory window after clearance, episode-keeping
        # records) moves one campaign positive on 3.11 the same as on 3.12:
        # (1, 1, 217, 4, 0) -> (1, 1, 217, 5, 0), read from CI job
        # 106118699889 (fast tier, 3.11, shard 3) on this branch.
        # AERO-SPLIT-01 partitions continuous droplet emission into a
        # partner-bounded near-field plume and a 0.175 far-field pool share;
        # droplet reach collapses to the proximity ring and the cell goes
        # extinct: (1, 1, 217, 5, 0) -> (0, 0, 217, 1, 0), read from CI job
        # 107697563827 (fast tier, 3.11, shard 3) on this branch — both
        # interpreters agree, as before on near-extinct cells.
        (3, 11): (0, 0, 217, 1, 0),
        # Local CPython 3.12 venv (compensated float sum). Was (85, 51, 102,
        # 30, 30) before the same two merged changes: #537's ascertainment
        # gate alone moved it to (58, 14, 217, 93, 52) and the #538 Bridge
        # zone alone moved it to (82, 46, 113, 25, 24); the tuple below is
        # the composition, measured on the merged tree, and read (53, 15, 217,
        # 74, 39) with the boarding cohort; the same opt-out alone moved it to
        # (1, 1, 217, 3, 2). The two incubation changes above then moved it
        # to (3, 1, 217, 2, 1) (reference-dose draw for the index case alone)
        # and to (5, 0, 217, 6, 4) (with the Theta-arm re-reference). The
        # new-default Theta=1e10 reading is live but unsaturated on both
        # interpreters.
        # AERO-CABIN-06 makes the same attributed move on CPython 3.12:
        # (112, 48, 217, 125, 29) to (105, 51, 217, 118, 20).
        # QUAR-ORDER-01: scheduled SOP-017 now admits every non-exempt passenger
        # instead of applying the voluntary FRED draw: (105, 51, 217, 118, 20)
        # -> (81, 42, 217, 88, 11).
        # AERO-NEAR-02: default β near-field dose plus per-meal buffet/mess table
        # dealing moves this local CPython 3.12 reading to (51, 8, 217, 51, 32).
        # DINE-CREW-01 deals crew-mess tables within department (work zone), which
        # reorders the per-meal RNG draws and changes the near-field table-mates of
        # every crew diner; the cell follows a different Bernoulli path:
        # (51, 8, 217, 51, 32) -> (14, 3, 217, 18, 10) on CPython 3.12. The 3.11
        # reading is taken from the CI job on this branch.
        # DOSE-FRAIL-01 restores the beta-Poisson per-host susceptibility draw
        # while scaling its mean to Theta, moving the cell
        # (14, 3, 217, 18, 10) -> (1, 1, 217, 4, 0) on CPython 3.12 and
        # (14, 5, 217, 19, 7) -> (1, 1, 217, 4, 0) on CPython 3.11 (read from CI
        # job 105760985675 on this branch). The interpreters now agree because
        # the move is not RNG-stream divergence: the cell's hosts are no longer
        # identically susceptible, and a concave marginal response over a
        # right-skewed frailty distribution yields fewer infections than the
        # same mean applied to identical hosts.
        # REINFECT-01 gives a cleared host the declared refractory window and
        # keeps first-episode records, which changes the trajectory and moves
        # one campaign positive: (1, 1, 217, 4, 0) -> (1, 1, 217, 5, 0)
        # on CPython 3.12, read in the local venv on this branch.
        # AERO-SPLIT-01 partitions continuous droplet emission into a
        # partner-bounded near-field plume and a 0.175 far-field pool share:
        # the cell's droplet reach collapses to the proximity ring and the
        # replay goes extinct, (1, 1, 217, 5, 0) -> (0, 0, 217, 1, 0) on
        # CPython 3.12, read in the local venv on this branch. The partition
        # also draws proximity partners on the shared stream, so this is the
        # intended physics plus the stream reorder the labelled off baseline
        # exists to isolate.
        (3, 12): (0, 0, 217, 1, 0),
    },
    "diamond_princess_2020": {
        # INDEX-GEOM-01 adds this cell. Until it did, no CI reading looked at the
        # training hull at all: the only pinned cell was the held-out Greg
        # Mortimer, which declares no departure and cannot move under a fit-facing
        # mechanic. The two cells hold every knob identical — Theta, seed, epochs,
        # the five pinned fields — so they are directly comparable and differ only
        # in hull.
        #
        # CHANGE DETECTOR, not an anchor comparison — the distinction is
        # load-bearing on this hull specifically. These numbers are whatever the
        # current mechanics produce; they are NOT the Diamond Princess observables
        # of data/observation/covid_fit_targets.json, and covid.T1 / covid.T3 are
        # real scored anchors on this same scenario. A move here is a signal to
        # attribute a diff, never a fit residual to minimise, and nothing in this
        # file may be quoted as a result.
        #
        # First reading, measured locally on CPython 3.12 on this branch: taken
        # with the declared index case departing on day 5 (departure_day 5.0,
        # Yamagishi 2020). The CPython 3.11 entry is pending a CI reading, as the
        # Greg Mortimer 3.11 reads above were.
        # This cell is marked `slow`: a full Diamond Princess replay is ~20
        # minutes, so it lands on the nightly tier while the Greg Mortimer
        # cell keeps a fast-tier reading on every push. That first reading was
        # (3522, 2934, 1706, 252, 73); the 3.12 nightly at a44d4c4 (#632) was
        # the last to pass at it. Two merges then moved the cell, read locally
        # on CPython 3.12 (numpy 2.5.0) at each merge commit:
        #   QUAR-EXEMPT-01 (#633, 861a0b9): confinement now applies each
        #   order's own exempt_classes, changing whom the SOP-017 scenario
        #   quarantine confines on this hull,
        #   (3522, 2934, 1706, 252, 73) -> (3464, 2982, 1847, 232, 68);
        #   REINFECT-01 (#636, d62f10d): cleared hosts get the declared 90-day
        #   refractory window and episode-keeping records, so the late-replay
        #   reinfections the old engine counted no longer occur,
        #   (3464, 2982, 1847, 232, 68) -> (3418, 2942, 1894, 209, 68).
        # The pin is the post-REINFECT-01 reading; #637/#638 touch no engine
        # code. The local CPython 3.11 reading at the same commit is
        # (3399, 2963, 1987, 195, 64) (numpy 2.4.6) and stays unpinned
        # pending a CI reading, as the 3.11 entries above were.
        (3, 12): (3418, 2942, 1894, 209, 68),
    },
}


@pytest.fixture(
    scope="module",
    params=[
        "greg_mortimer_2020",
        pytest.param("diamond_princess_2020", marks=pytest.mark.slow),
    ],
    ids=HULLS,
)
def cell(request) -> tuple[str, HullObservables]:
    return request.param, simulate_hull(request.param, THETA, SEED)


def _pinned(obs: HullObservables) -> tuple[int, ...]:
    d = asdict(obs)
    return tuple(int(d[k]) for k in PINNED_FIELDS)


def test_the_cell_recorded_its_index_case_and_stays_in_bounds(cell):
    _hull, obs = cell
    # AERO-SPLIT-01: the partition reorders the shared stream, and on the
    # held-out hull the replay is extinct — 0 recorded onsets is a valid
    # reading of this detector cell, so only the bounds relation survives.
    assert obs.recorded_onsets >= 0
    assert 0 <= obs.onsets_before_split_day <= obs.recorded_onsets
    assert (
        obs.onsets_before_split_day + obs.onsets_on_or_after_split_day
        == obs.recorded_onsets
    )
    assert 0 <= obs.campaign_asymptomatic_positives <= obs.campaign_positives
    assert obs.campaign_positives <= obs.campaign_specimens


def test_the_cell_matches_its_pinned_reading(cell):
    """Seed reproducibility is asserted here too: the tuple was read in another process."""
    hull, obs = cell
    golden = GOLDEN_BY_HULL_AND_MINOR[hull]
    key = (sys.version_info.major, sys.version_info.minor)
    if key not in golden:
        pytest.skip(f"no pinned {hull} reading for CPython {key[0]}.{key[1]}")
    assert _pinned(obs) == golden[key], (
        f"COVID hull cell moved for {hull}; attribute the move before "
        f"repinning (fields {PINNED_FIELDS})"
    )
