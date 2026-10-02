# COVID-THETA-V15
**Date:** 2026-10-02
**Commit:** 6efec855
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** 6efec855

Declared before any v15 cell ran (PR #828, merged `6efec855`).
Re-admission of the admissible Θ band AND the declared Diamond
Princess replay under the repaired presentation draw: PRESENT-SHARE-01
(PR #825, merged `890bfce3`) made `presentation_draw_mode:
once_per_course` the shipped default — the declared share of courses
draws once at the incubation crossing instead of re-rolling as a
per-day hazard through `NOT_ILL` — so the THETA-SCREEN-V14 admissible
set {1.33e11..4.22e11}, admitted under the defective daily-hazard
spend on image `covid-theta-v14-02740187`, is stale, and the v13
stage-2 clause surface of record (`edb7fc41`) predates the repair.
This stage re-runs the v14 lattice verbatim (same 9-point
eighth-decade lattice, same seeds, same frozen selectors) plus the
declared replay the v14 enumeration never executed — single arm
`once_per_course` — pairing stage 2 seed-for-seed against the v13
stage-2 cells, the last executed replay surface.

## Declared

Designs (criteria verbatim from v14/v13 — `fleet_shape_selector`,
`conditional_trajectory_clause`, `index_geometry` audit invariant —
plus a new `audit_invariants` echo pair this stage exists to enforce:
`delivery.presentation_draw_mode == "once_per_course"` and
`delivery.hand_reservoir_mode == "hygiene_cycle"` on every cell):

- `picard_framework/runs/covid_theta_screen_v15_design.json` — stage 1,
  generic voyages, 9 Θ × 200 seeds at base 20201001 = 1,800 cells.
- `picard_framework/runs/covid_theta_screen_v15_stage2_design.json` —
  stage 2, declared replay (onset_day −1.0, departure_day 5.0,
  dwell_weighted, imports 1, infection_age 6.8, 20 seeds at base
  20200205, 768 epochs). Points list is the candidate universe
  (Θ 1e9 anchor + nine lattice Θ); the parent's frozen theta_points
  rule selects which rows submit. The stage-2 design declares a
  single baseline arm because `cell_payload` gates the `delivery`
  echo block on `design.arms` — an armless declared design would
  ship a lean payload with no draw-mode echo to audit.

## Measured

Stage 1 (1,800/1,800 cells, 0 audit failures, 0 child failures):
**admissible set {1.78e11, 2.37e11, 3.16e11, 4.22e11, 5.62e11}** —
one lattice notch up at each edge vs the v14 band {1.33e11..4.22e11},
a reversion to the v13 coordinates. The direction matches the repair's
signature: with ~31% of courses never presenting, recorded counts sit
lower at a given transmission scale, so the median floor needs one
notch more Θ to clear. Seed-paired vs v14: recorded-onset medians
delta ≈ 0 everywhere (0 to −6), the q05 floor drops −31 to −108
(deeper fizzle tail), q95 flat; `suppression_candidate` false at every
row; takeoff-class flips 1–5/200. Interior-bounded window: floor fails
below, ceiling fails above.

Stage 2 (160/160 cells under the frozen rule — anchor + flanks
{1.33e11, 7.5e11} + the five admissible rows; 0 audit failures, 0
child failures, `rule_missing`/`rule_extra` both empty): **the clause
fails at every admissible interior Θ.** Takeoff seeds saturate at
medians ~2,546–2,596 recorded onsets (q05 floors 1,444–1,743, 7–9× the
record's 197) and before_share medians 0.73–0.96 vs the 0.173±0.10
leg, rising with Θ. The Θ1e9 anchor again passes alone (takeoff n 10,
q05–q95 [153–2438] ∋ 197, before_share 0.090 within tolerance) — a
fleet-shape-inadmissible boundary row, reported never selected.
Anchor re-measurement on seed 20200205 (3,378 / 0.9102) sits inside
cross-generation drift of the QUAR-ATTR-V2 record (3,365 / 0.9068).

Seed-paired vs the v13 stage-2 cells: median recorded_onsets deltas
**−751 to −938** per lattice row — the once-per-course spend removed
~800 median recorded onsets per ignited seed, the largest
mechanism-level move the replay surface has registered — and the
failure still stands by ~10×. The repair moved the recorded mass in
the intended direction without bending the saturation shape: **the
presentation channel was a real defect and is not the DP residual.**

## Verdict

Clause fails at every admissible Θ under the repaired draw; the
admissible set of record on this engine is {1.78e11 … 5.62e11} and no
Θ is admitted. The residual remains mechanism-shaped. Readout:
`docs/covid/covid_theta_screen_v15_readout.md`; cells of record
`s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_theta_screen_v15{,_stage2}/6efec855/cells/`;
surfaces `docs/covid/covid_theta_screen_v15_surface.csv`,
`docs/covid/covid_theta_screen_v15_pairs.csv`.
