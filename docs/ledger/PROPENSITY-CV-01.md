# PROPENSITY-CV-01
**Date:** 2026-10-03
**Commit:** 1d51a01c
**Pathogens:** sars_cov2_resp
**Status:** declared

## Question

PROPENSITY-V1 shipped the missing persistent-propensity term with its
widest unmeasured cell at the centre of the declaration: `cv` 0.8 on the
mean-pinned lognormal unit draw (Grade C, `docs/propensity_v1_spec.md` §4 —
"no cruise-activity attendance variance in the literature; the widest
unmeasured cell in this spec"). How does the DP anchor's verdict respond
as that dispersion traverses its declared cell? If the mechanism's
prediction is *shape*, the response curve over cv — which legs move, in
which direction, and where the curve bends — is the measurement that
precedes any band-array decision. The `covid_propensity_v1` canary has
since measured the shipped 0.8 dead at this anchor (merged #868:
clause FAIL on both arms, seed-paired footprint noise, and the v15
anchor pass historical at its own SHA) — so the screen's question
sharpens to whether *any* point in the declared cv range is live where
the clause is scored, not whether the default is right.

## Declaration

`picard_framework/runs/covid_propensity_cv_screen_design.json` — a
single-axis cv screen at the Theta 1e9 anchor: arms {`CV020`, `CV040`,
`D0_declared` (cv 0.8, the shipped default and the grid's centre),
`CV120`, `CV200`} × the frozen DP replay contract (index onset −1.0,
departure day 5, dwell_weighted, imports 1, 20 matched seeds @20200205,
768 epochs) plus the `PROP_OFF` labelled bit-identical baseline — 120
cells. Every cv arm overrides only the `cv` key, so the resolved
`rhythm.participation_propensity` block differs from the shipped default
in exactly the swept quantity (mode `party`, distribution `lognormal`,
discretionary classes, declared `age_band_mean` all untouched).

This is a screen, not an assay: the v11-lineage clause is scored per arm
verbatim (count leg q05–q95 ∋ 197, timing leg median within 0.10 of
0.173, ≥5 takeoff seeds), but **no cv is selected** — traversing a
declared range to fit the anchor is barred by the same no-fit rule that
froze the constants table. The deliverable is the cv-response curve:
seed-paired (arm − `PROP_OFF`) delta distributions on recorded_onsets /
before_share / infections_total, ordered by declared cv. A clause PASS
on any arm is reported immediately as sensitivity, never as admission —
the anchor is a boundary row.

## Audit invariants (frozen)

- `delivery.participation_propensity` resolves per cell with mode
  `party` and the arm's declared cv (0.8 on `D0_declared`, else the
  override); `off` on `PROP_OFF`. Mismatch = design defect, halts.
- `propensity_draw.units_drawn` > 0 on every armed cell, == 0 on
  `PROP_OFF` (bit-identity witness); per-arm multiplier q95 should read
  ~1.4 / ~1.8 / ~2.5 / ~3.0 / ~3.6 across the grid — a mismatched spread
  means the declared cv never reached the deal.
- `index_onset_day == -1.0`, `index_shedding_at_day0` on every seed;
  `presentation_draw_mode == once_per_course`;
  `hand_reservoir_mode == hygiene_cycle` on every cell.

## Pairing

- `D0_declared` reproduces the `covid_propensity_v1` canary's same-named
  arm seed-for-seed — a cross-run replication row under the same image
  generation.
- Every cell pairs with the v15 stage-2 Theta 1e9 anchor row (cells
  0–19, `campaign/covid_theta_screen_v15_stage2/6efec855/cells/`) for
  the cross-generation drift read — reported, never selected on.

## Interpretation (declared before measurement)

- Monotone suppression toward the record as cv rises = the mechanism
  family is live somewhere inside its declared range; a band sweep is
  the next decision.
- A flat curve at every cv = mechanism-inert-at-anchor, as strong a
  measurement as a negative canary.
- A curve that splits the clause legs (count moves, timing does not) =
  the dispersion moves incidence shape but not detection timing —
  directs the next instrument toward the report channel, not the
  exposure channel.
