# COVID Theta screen v7: the admissible region is empty

> **Status:** Findings (2026-09-19). Campaign `covid_theta_screen_v7`, declared
> in `picard_framework/runs/covid_theta_screen_v7_design.json` (#606) and run on
> AWS Batch at `main` = `e32272d`, image
> `picard-campaign:theta-screen-v7-7ff6dd0`, array job
> `be88c89e-4b48-4210-a445-2b51fa71a2de` on `picard-campaign-queue`.
> 3,080 of 3,080 cells completed, zero failures, no `--allow-partial`.
> Cells: `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_theta_screen_v7/`.
> Merge command: `python3 tools/fit_covid_theta.py screen --design
> picard_framework/runs/covid_theta_screen_v7_design.json --cells <synced cells dir>`.
> No Theta is claimed here, and no figure below may be quoted as a fit.

The screen is the first Theta surface on the repaired arm: host frailty
restored (`DOSE-FRAIL-01`, #603) and the Diamond Princess index case departing
at Hong Kong on day 5 (`INDEX-GEOM-01`, #605). 11 half-decade Thetas from 1e7
to 1e12 x 7 index infection ages (0, 3, 5, 7, 9, 11, 13 d) x 40 seeds, one
declared import, `dwell_weighted` sanitary visits, admissibility pre-registered
in the design file before any cell ran.

## Result

**Zero of the 77 (Theta, age) cells satisfy all three declared criteria.** No
cell satisfies index geometry and `covid.T1` together, at any Theta.

| criteria met | cells |
|---|---|
| index geometry + T1 + T3 | none |
| T1 + T3, geometry failed | Theta 1e9 at ages 0, 3, 5; Theta 3.16e9 at age 5 |
| geometry + T3, T1 failed | Theta 1e11 and 3.16e11 at ages 11, 13 |
| geometry + T1 | none |

The two selection criteria are not merely both unmet; they are in direct
tension along the infection-age axis, and the tension is structural rather than
a matter of resolution.

## Why the two criteria cannot be met at once

The index-geometry pass fraction is a function of index infection age *only* —
0.0, 0.075, 0.45, 0.675, 0.775, 0.90, 0.92 at ages 0 to 13 — and is flat in
Theta to within seed noise. It has to be: the gate asks whether the seeded host
has already had onset by day 0, which is decided by the host's own incubation
draw against its boarding infection age, not by how infectious the ship is. The
declared 80% threshold is therefore reachable only at ages 11 to 13 d.

At ages 11 to 13 d every Theta on the grid burns. Conditional on takeoff
(>= 10 recorded onsets), median recorded onsets are 2,400 to 3,300 of 3,711
hosts, attack-rate median given a VSP crossing is 0.70 to 0.98, and the
pre-day-17 onset share is 0.30 to 0.99 against Diamond Princess's 34/197 =
0.17. The record is 197 recorded onsets and roughly a 0.19 attack rate with 83%
of onsets *after* the 5 February quarantine. Nothing on the age >= 11 band comes
within an order of magnitude of that trajectory.

Diamond-Princess-sized trajectories do exist on this surface, at Theta 1e8 to
1e9 and index ages 0 to 5 d: conditional-on-takeoff median recorded onsets 108
(Theta 1e8, age 0, 6 takeoffs of 40), 400 (1e8, age 3), 939 (1e8, age 5),
1,140 (3.16e8, age 3), 1,680 (1e9, age 0). Those are the cells that pass T1,
and at Theta 1e9 they pass T3 as well. They also carry the fleet shape the
held-out `covid.H3` record wants — `p(attack <= 0.01)` of 0.65 to 0.90 with a
takeoff probability of 0.15 to 0.53, i.e. most voyages extinguishing and a
minority burning. They fail only the index-geometry gate.

So the empty region is not "Theta is wrong everywhere". It is: the band where
the outbreak is the right size is the band where the seeded index is *not*
symptomatic at boarding, and the model has no way to place a symptomatic index
aboard without also placing the epidemic 6 to 11 days further along.

## The criterion is unreachable at the record's own geometry

The record's index was infected roughly 5 to 6 d before boarding — cough onset
19 January, boarded 20 January (Yamagishi 2020, Eurosurveillance
25(23):2000272, grade A). At age 5 d the geometry gate passes in 45% of seeds,
not 80%, because the seeded host's incubation period is drawn free from the
profile distribution and then compared against the age. The gate as declared
conflates two different things: *did this replicate happen to draw a short
incubation*, and *did the index board symptomatic*. The record fixes the
second. Filtering seeds cannot recover it — at the biologically correct age the
majority of seeds contradict the record.

This is a model defect at the seeding path, not a threshold to be relaxed after
seeing the surface: the explicit-seed channel has no way to declare an observed
onset date, so it cannot seed the host the record describes.

## Two misses Theta cannot close

**Asymptomatic share.** Across all 77 cells the median asymptomatic share never
exceeds 0.43 (mean 0.40), against `covid.T4`'s 320/634 = 0.50 on Diamond
Princess and `covid.H2`'s 104/128 = 0.81 on Greg Mortimer. It is monotone
*downward* in Theta — median 0.41 at Theta 1e7 age 11, 0.25 at 1e9, 0.084 at
1e10, 0.002 at 1e12 — because in this model the asymptomatic fraction is an
emergent consequence of the delivered dose rather than a natural-history
parameter. Raising Theta to reach the observed outbreak sizes therefore *moves
away* from the observed asymptomatic share. No Theta reconciles the two.

**T3 does not discriminate.** Median campaign specimens run 1,598 to 3,063 and
campaign positives 260 to 870 across five decades of Theta, because the testing
campaign saturates against its own capacity well before the epidemic does.
`covid.T3` (634 of 3,063) is passed at Theta 1e9 and again at 1e11 to 3.16e11,
cells whose attack rates differ by a factor of three. On this hull T3 is a test
of assay capacity, not of transmission, and should not carry selection weight
in a successor design.

## Consequences

Stages 2 and 3 declared in the same design file (the 200-voyage fleet-shape
ensemble and the Greg Mortimer held-out check) are gated on a non-empty stage-1
shortlist and are **not** submitted. Held-out anchors were not consulted to
select anything here; `covid.H2` and `covid.H3` appear above only as
comparisons after the fact.

No criterion in the design file was altered after the surface was seen, and no
Theta is claimed. The next declared step is the seeding-path fix — an index
whose onset date is declared from the record rather than redrawn — after which
the nearest region (Theta 1e8 to 1e9, index ages 0 to 7 d) can be re-screened
with the geometry gate satisfied by construction instead of by filtering.
