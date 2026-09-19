# THETA-V7-01
**Date:** 2026-09-19
**Commit:** e32272d
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** e32272d

## Measurement

`covid_theta_screen_v7` (declared #606, run at `main` = `e32272d`, AWS Batch
array `be88c89e-4b48-4210-a445-2b51fa71a2de`, 3,080/3,080 cells, zero failures)
is the first Theta surface on the repaired arm — host frailty restored
(`DOSE-FRAIL-01`) and the index case departing day 5 (`INDEX-GEOM-01`).

**The pre-registered admissible region is empty.** Zero of 77 (Theta, index
infection age) cells satisfy index geometry, `covid.T1` and `covid.T3` jointly;
zero satisfy index geometry and `covid.T1` together at any Theta on 1e7 to 1e12.
No declared criterion was altered after the surface was seen, and no Theta is
claimed. Full readout with the per-cell table:
`docs/covid/covid_theta_screen_v7_readout.md`.

The two selection criteria are in structural tension along the index-age axis.
The geometry pass fraction depends on index infection age alone (0.0, 0.075,
0.45, 0.675, 0.775, 0.90, 0.92 at ages 0 to 13 d), flat in Theta to seed noise,
so the declared 80% threshold is reachable only at ages 11 to 13 d — where
every Theta on the grid burns (conditional-on-takeoff median 2,400 to 3,300
recorded onsets of 3,711 hosts, attack median given a VSP crossing 0.70 to 0.98,
pre-day-17 onset share 0.30 to 0.99 against the record's 34/197 = 0.17).
Diamond-Princess-sized trajectories *do* occur, at Theta 1e8 to 1e9 and ages 0
to 5 d (conditional-on-takeoff median recorded onsets 108, 400, 939, 1,140,
1,680), together with the fleet shape `covid.H3` wants
(`p(attack <= 0.01)` 0.65 to 0.90, takeoff probability 0.15 to 0.53); those
cells pass `covid.T1`, pass `covid.T3` at Theta 1e9, and fail only geometry.

## Defect exposed: the seed channel cannot declare an observed onset

The record's index was infected about 5 to 6 d before boarding (cough onset
19 January, boarded 20 January; Yamagishi 2020, Eurosurveillance
25(23):2000272, grade A). At age 5 d the geometry gate passes 45% of seeds, not
80%, because `ExplicitSeed` carries an infection age and the seeded host's
incubation period is then drawn free from the profile distribution. The gate
therefore mixes "this replicate drew a short incubation" with "the index boarded
symptomatic", and at the biologically correct age most seeds contradict the
record. This is a seeding-path defect, not a threshold to relax: the explicit
seed channel has no way to declare the index's observed onset date.

## Two misses Theta cannot close

- **Asymptomatic share.** Median asymptomatic share never exceeds 0.43
  (mean 0.40) in any of the 77 cells, against `covid.T4` 320/634 = 0.50 and
  held-out `covid.H2` 104/128 = 0.81. It is monotone *downward* in Theta
  (median 0.41 at 1e7, 0.25 at 1e9, 0.084 at 1e10, 0.002 at 1e12): the
  asymptomatic fraction is emergent from delivered dose rather than a
  natural-history parameter, so raising Theta towards the observed outbreak
  sizes moves away from the observed asymptomatic share.
- **`covid.T3` does not discriminate.** Median campaign specimens 1,598 to
  3,063 and positives 260 to 870 across five decades of Theta: the testing
  campaign saturates against its own capacity before the epidemic does. T3 is
  passed at Theta 1e9 and again at 1e11 to 3.16e11, cells whose attack rates
  differ threefold. It is a capacity test on this hull and should not carry
  selection weight in a successor design.

## Not done here

Stages 2 and 3 of the v7 design (200-voyage fleet-shape ensemble; Greg Mortimer
held-out check) are gated on a non-empty stage-1 shortlist and were not
submitted. Held-out anchors were not used to select anything; `covid.H2` and
`covid.H3` appear only as after-the-fact comparisons.
