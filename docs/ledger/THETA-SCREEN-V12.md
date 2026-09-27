# THETA-SCREEN-V12
**Date:** 2026-09-27
**Commit:** 51285178
**Pathogens:** sars_cov2_resp
**Status:** declared

Declared before any v12 cell ran. Bisection of the bracketed H3-admissible
window (1e11, 1e12) on the post-721 base, per COVID-REBASE-01 (PR #733):
interior medians ~0.00027 from 1.78e10 through 1e11 (selector floor fails),
1e12 overshoots (median 0.0154). This stage materialises the bisection to
eighth-decade resolution as a fixed lattice — the two endpoints as boundary
rows plus interior {1.33, 1.78, 2.37, 3.16, 4.22, 5.62, 7.5}e11 — then
re-measures the conditional clause at each admissible point.

## Declared

Designs (frozen criteria verbatim from v11, carried through rebase_01 —
`fleet_shape_selector`, `conditional_trajectory_clause`, `index_geometry`
audit invariant, `h3_role_change`):

- `picard_framework/runs/covid_theta_screen_v12_design.json` — stage 1,
  generic voyages, 9 Θ × 200 seeds at base 20201001 = 1,800 cells.
  Endpoint rows are bracket-verification boundaries, never candidates.
- `picard_framework/runs/covid_theta_screen_v12_stage2_design.json` —
  stage 2, declared replay (onset_day −1.0, departure_day 5.0,
  dwell_weighted, imports 1, infection_age 6.8, 20 seeds at base
  20200205, 768 epochs). Points list is the candidate universe (Θ 1e9
  QUAR-ATTR-V2 anchor + nine lattice Θ); the parent's frozen rule
  selects which rows submit — admissible set + flanks, the
  window-straddling pair on an empty-but-crossed surface, or nothing if
  the window is illusory.

Selection: admissible set = interior Θ passing the fleet-shape selector
whose replay cells pass the conditional clause; boundary hits are
reported, never selected. Stage 3 (greg_mortimer_2020, H1/H2) stays held
out and gated on stage 2.

## Campaign gate

AWS canary of 60 cells before the array — 20 cells each at Θ 1e11,
3.16e11 (interior midpoint), 1e12 (INDEX_OFFSET 0/800/1600,
ARRAY_SIZE 20). Bracket verification on the v12 image: 1e11 below the
selector window, 1e12 above it, every generic spec free of declared
onset_day/departure_day/molecular_ascertainment_start_day. The full
1,800-cell array commits only on a clean bracket-verification readout.

## Report immediately if

The bracket contains no admissible point (monotone overshoot/undershoot
at both ends — the engine needs a mechanism, not a Θ); the clause passes
only at a boundary endpoint; the takeoff transition sits outside the
bracket; any stage-1 spec carries a declared onset_day/departure_day;
endpoint rows disagree with the seed-paired rebase_01 read beyond a
20/200 takeoff band; or child failures exceed 5%.

## Result

_To be filled at readout: admissible Θ set (or empty), conditional clause
per admissible point, takeoff-mass and before_share composition table._
