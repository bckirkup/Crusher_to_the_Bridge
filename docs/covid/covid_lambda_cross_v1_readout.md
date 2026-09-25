# LAMBDA-CROSS-V1 readout — hazard-rate (Θ) response curve

Measured at `8649d31`, AWS Batch job-def `picard-covid-boarding-screen:22`
(image `picard-campaign@sha256:cf604057…6ac2`), array `6f4228ef`, 140/140
cells SUCCEEDED, zero failures, audit invariant held in every cell
(`index_onset_day == -1.0`, `index_shedding_at_day0` true, 140/140).
Canary row (θ ×0.001, indices 120–139) ran first under array `f19598ac` and
its cells were reused idempotently by the full array.

## Per-θ conditional reads (takeoff = recorded_onsets ≥ 10)

| θ mult | θ | takeoff | q05 | median | q95 | band ∋ 197 | near-target share [98.5, 394] | median before_share | infected median |
|--------|---|---------|-----|--------|-----|-----------|--------------------------------|---------------------|-----------------|
| ×1.0    | 4.22e10 | 20/20 | 2,082 | 3,486 | 3,535 | no  | 0.000 | 0.646 | 3,527 |
| ×0.3    | 1.266e10 | 19/20 | 2,288 | 3,117 | 3,481 | no  | 0.000 | 0.281 | 3,393 |
| ×0.1    | 4.22e9  | 19/20 | 477  | 2,792 | 3,351 | no  | 0.000 | 0.114 | 3,048 |
| ×0.03   | 1.266e9 | 12/20 | 18   | 2,458 | 3,280 | yes | 0.083 | 0.201 | 2,738 |
| ×0.01   | 4.22e8  | 10/20 | 12   | 1,327 | 3,058 | yes | 0.000 | 0.169 | 1,816 |
| ×0.003  | 1.266e8 | 6/20  | 241  | 1,807 | 2,924 | no  | 0.167 | 0.202 | 2,093 |
| ×0.001  | 4.22e7  | 8/20  | 130  | 624   | 2,858 | yes | 0.250 | 0.084 | 979   |

Per-seed recorded_onsets vectors are in the cell JSONs under
`s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_lambda_cross_v1/8649d31/cells/cells/`.

## Declared response-curve reads

- **lambda_binding — bound, and it bends the median.** Conditional recorded
  mass is monotone-ish non-decreasing in θ on the scored rows (medians
  624 → 3,486 bottom to top; the ×0.003 takeoff count of 6/20 vs ×0.01's
  10/20 is an inversion inside the bimodal-extinction band, not a reversed
  median). The hazard-rate scale binds the conditional gap.
- **elasticity = 0.216** (log-log slope of conditional median vs θ
  multiplier over the 7 scored rows). For comparison the plume-dose axis
  measured 0.004 (PLUME-DOSE-V1): Θ is ~54× steeper per decade — the dose
  axis's null is rejected — but 0.216 is still shallow: a ×1000 λ cut buys
  only a 5.6× median reduction.
- **crossing:** rows whose takeoff-seed q05–q95 contains 197: θ ×0.03,
  ×0.01, ×0.001. The bands contain 197 through widening left tails and
  thinning takeoff counts, not through mass landing on 197 (near-target
  share peaks at 0.25 on ×0.001).
- **collapse_point:** no row reaches <5/20 takeoff. The grid's bottom
  (×0.001) leaves 8/20 seeds taking off — the cascade sustains on the
  strong seeds even at Σλ ~O(20) first-generation challenges.
- **shape_check:** median before_share falls from 0.646 (×1.0) through
  0.169 (×0.01) to 0.084 (×0.001); the record's 0.173 is crossed inside
  the grid — the hazard scale is what puts onset mass in the
  quarantine window.

## Clause family scoring

- **conditional_trajectory_clause:** satisfied at θ ×0.03, ×0.01, ×0.001 —
  each row's takeoff band contains 197 AND its median before_share is within
  0.10 of 0.173 (0.201, 0.169, 0.084 respectively). This is the first assay
  row family in the campaign line to satisfy it.
- **verdict bands, per-θ:** ×1.0 baseline; ×0.3 inert (−10.6%);
  ×0.1 inert (−19.9%, at the edge); ×0.03 partial (−29.5%, band ∋ 197);
  ×0.01 load_bearing (−61.9%, band ∋ 197, clause satisfied);
  ×0.003 partial (−48.2%, band excludes 197, takeoff 6/20);
  ×0.001 load_bearing (−82.1%, band ∋ 197, clause satisfied).
- **closes_the_gap: no θ row.** Every satisfying row's conditional median
  exceeds the [98.5, 394] band (624–2,458). The clause passes on tails,
  not centres.
- **Curve level: `lambda_bound_but_short`.** The curve bends measurably
  (elasticity 0.216) and rescues the timing shape, but the low end still
  over-produces on surviving takeoff seeds (median 624, near-share 0.25).

## Mechanism verdict

The declared expectation was a steep sigmoid (λ ≫ 1 saturation collapsing
through a λ ≈ 1 band). The measured curve is instead a **shallow bend with
bimodal extinction**: per-challenge λ was already measured tiny
(median 2.8e-6; ROUTE-ATTR-V1 instrument), so Θ works through aggregate
challenge volume (Σλ) and per-generation amplification — halving takeoff
share while surviving cascades still burn large fractions of the ship.
That is why the median is so hard to move: conditioning on takeoff selects
the seeds whose cascade self-sustains.

Per the declared counterfactual: the hazard scale is load-bearing but
insufficient alone — at ×0.001 the survivors still infect ~979 median.
The ~18× conditional gap does not live on the λ axis alone; the residual
factor lives in what survives conditioning (index/day-0 geometry,
seed-structure) or in the observational channel, which ROUTE-ATTR-V1
measured as over-including ~11× (ascertainment ~3.3× × dating ~3.4×).
A hazard scale of θ ×0.001–0.01 combined with a record-consistent channel
would bracket 197 — but no single knob measured so far reaches it.

Non-goal honoured: this maps the response; it selects no θ.

## Structural caveat

All numbers are batch-image CPython 3.11 at `8649d31`; local instrument
reads (λ distributions) were CPython 3.12 and are structural context, not
cross-comparable values. RNG pairing caveat stands: θ rescaling reorders
draws, so reads are distribution-level, never seed-paired.
