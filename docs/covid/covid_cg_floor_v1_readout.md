# CG-FLOOR-01 corner probe — R2 tending at the declared floor: DELIVERY-STRUCTURAL

> **Status:** Findings (2026-10-04). Campaign measured at `3eae8a2f`
> (image `picard-campaign@sha256:f906128e…` / tag
> `campaign-e0d43979-cgfloor`, jobdef `picard-covid-boarding-screen:55`,
> queue `picard-analysis-queue`, prefix
> `campaign/covid_cg_floor_v1/3eae8a2f/cells/`).

ANCHOR-DERIVE-01 (`docs/covid/covid_anchor_derivation_v1.md`) certified
the clause targets mechanism-independent and named the suspect:
CAREGIVER-V1's pre-quarantine delivery — ~5–13 caregiver-attributed
acquisitions per takeoff seed inside the index's days-0–4 window
against a record whose entire pre-6-Feb dated mass is 34 onsets. Its §5
declared this probe: at the two measured leg-crossing rows, pin the R2
tending dose factors at the bottom of their declared intervals while
holding the designation/discovery shape at shipped, and read whether
the disjoint leg half-planes move.

Design `picard_framework/runs/covid_cg_floor_v1_design.json`: {Θ1e6,
Θ7.9e6} × {`D0_declared`, `CG_LOW`} × 20 seeds = 80 cells on the
verbatim `diamond_princess_2020` replay contract. `CG_LOW` sets
`transmission.caregiver.tending.tending_copresence_multiplier` to the
degenerate range [1.5, 1.5] (declared U[1.5, 3.0]) and
`tending_hours_per_day` to [2.0, 2.0] (declared U[2.0, 6.0]) — the
declared floor, no new constants; `response_probability` U[0.5, 0.9],
`report_probability` U[0.3, 0.7], the designation grammar and
`budget_mode: reallocate` all stay shipped — the held-constant half of
the experiment. The verdict grammar (DELIVERY-BOUNDED /
DELIVERY-STRUCTURAL / SUB-IGNITION) is frozen in `admissibility` before
any cell ran. Submitted as one 80-cell array (`2f51598b`) on the
bracket overlay image + this design file. 80/80 cells SUCCEEDED, zero
audit failures — `delivery.caregiver.roles.tending` echoes the corner
on every CG_LOW cell and the shipped ranges on every D0 cell.

## Replication check (the in-design canary)

The two `D0_declared` rows re-run cells already of record — the floor
probe's Θ1e6 row and the bracket's Θ7.9e6 row. **20/20 bit-identical
per row, max|delta| 0** modulo `cell.index`/`design_id` bookkeeping:
the image chain is engine-identical to the refit generation for the
third time in a row (canary Θ1e9, floor, bracket and now these rows).

## Clause scorecard (per row, takeoff-conditional)

| Θ | arm | takeoff | rec q05/med/q95 | before_share med | count | timing | clause |
|--:|-----|--------:|------------------|-----------------:|:-----:|:------:|:------:|
| 1e6 | D0_declared | 19/20 | 149 / 331 / 760 | 0.051 | **PASS** | FAIL | FAIL |
| 1e6 | CG_LOW | 19/20 | 126 / 377 / 592 | 0.053 | **PASS** | FAIL | FAIL |
| 7.9e6 | D0_declared | 19/20 | 496 / 634 / 1,540 | 0.075 | FAIL | pass | FAIL |
| 7.9e6 | CG_LOW | 19/20 | 502 / 661 / 1,014 | 0.077 | FAIL | pass | FAIL |

## The verdict: DELIVERY-STRUCTURAL

Seed-paired deltas (CG_LOW − D0_declared, n = 19 per row):

| Θ | Δrecorded_onsets q05/med/q95 | Δbefore_share q05/med/q95 | Δinfections_total med |
|--:|------------------------------|---------------------------|-----------------------:|
| 1e6 | −177 / **0** / +392 | −0.052 / **0.000** / +0.037 | 0 |
| 7.9e6 | −241 / **0** / +179 | −0.082 / **0.000** / +0.100 | 0 |

Per the frozen grammar: neither row clause-passed, and each failing leg
is unmoved within seed-paired noise — at 7.9e6 the count band's q05
edge did not drop toward 197 (496 → 502, a hair *away*), and at 1e6
the before_share median did not rise toward 0.073 (0.051 → 0.053, one
draw-noise unit). The disjoint half-planes are not reachable by
detuning the declared dose factors → **DELIVERY-STRUCTURAL**.

## The load-bearing witness: the tally did not move

| Θ | arm | caregiver aboard-window pooled | caregiver share of aboard acquisitions | mass_near_197 |
|--:|-----|-------------------------------:|---------------------------------------:|--------------:|
| 1e6 | D0_declared | 105 | 0.53 | 0.474 |
| 1e6 | CG_LOW | 104 | 0.44 | 0.632 |
| 7.9e6 | D0_declared | 138 | 0.47 | 0.000 |
| 7.9e6 | CG_LOW | 135 | 0.38 | 0.000 |

(`during_quarantine` caregiver = 0 on all four rows — the structural
confined-responder finding ANCHOR-DERIVE-01 already established.)

The corner worked as designed — the echo proves the floor reached the
engine — and the caregiver-route tally answered 105 → 104 and 138 →
135: **essentially unchanged**. The dose factors scale the dose *per
tending visit*; at the declared floor each visit still delivers enough
dose for the route to credit acquisitions. What produces the ~5–7
attributed acquisitions per takeoff seed inside days 0–4 is not how
much dose a visit delivers but **that a designation exists at all** —
the response_probability draw at first symptomatic epoch, the
report/discovery channel, and the pair's existence. Those components
were deliberately held at shipped, and the leg map's literal zero
median deltas are the measurement: the disjointness lives in the
mechanism's designation/discovery shape, not in its dose constants.

A caveat stated for honesty: the deltas' per-seed spreads are wide
(±200–400 onsets), so small per-leg movement under the noise floor is
not excluded — but the grammar's bar is convergence, and nothing moved
in its direction; the count leg even sits marginally further away at
7.9e6.

## What this closes and what it opens

The chain of record is now three certified links deep:

1. **θ-shaped?** No — WINDOW-EMPTY-ORDERED on [1e6, 1e9], disjoint
   leg half-planes (THETA-REFIT-01, merged through `04d6ef18`).
2. **Anchor-shaped?** No — the 197/0.173 targets are measured-direct
   record quantities, mechanism-independent (ANCHOR-DERIVE-01, PR
   #887, `ed7925f3`).
3. **Factor-shaped?** No — DELIVERY-STRUCTURAL here: the declared R2
   factor box cannot reach the caregiver contribution; the suspect
   narrows to the designation/discovery shape itself
   (`tending_response_probability`, `tending_report_probability`, and
   the designation's existence), or to where the clause is scored.

The stated-limitation witness stands: payloads carry route tallies on
acquisitions, not route-tagged dated onsets — the caregiver share of
dated onsets remains unmeasurable without an engine emit change
(recorded in the design's `rejected_alternatives`).

## Run note

One 80-cell array, indices 0–79, `picard-analysis-queue`, ~75 min wall
(CE warm; ~40 concurrent children). Zero audit failures, zero child
failures. The overlay image adds only the design file to the bracket
image, so cell engine semantics are identical to the refit generation.
Two stray jobdef revisions (53, 54) were registered from a stale rev-1
spec during setup — unused, underegistrable on the deploy role;
rev 55 is the submitted revision and carries the verified
`--index-offset` command.
