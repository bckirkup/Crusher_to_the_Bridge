# THETA-SCREEN-V12
**Date:** 2026-09-27
**Commit:** 51285178
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** f42901aa

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

Measured on image `covid-theta-v12-f42901aa` (jobdef rev 27): 1,860 cells,
0 failures. Endpoint drift check — all 400 seed-paired cells at Θ 1e11 and
1e12 are byte-identical to rebase_01 at `f280e348`; the engine path is
unchanged.

**Stage 1 — the window is real. Admissible set = {1.33e11, 1.78e11,
2.37e11, 3.16e11, 4.22e11}.** Median recorded attack climbs monotonically
through the H3 window (0.00054 → 0.0062); 1e11 fails the floor (0.00027),
5.62e11/7.5e11/1e12 fail the ceiling (0.0097/0.0109/0.0154, and means over
the 0.06 cap at the top two). Window edges resolve to ~0.1 decade:
lower ∈ (1e11, 1.33e11], upper ∈ [4.22e11, 5.62e11).

**Stage 2 — the clause fails at every admissible Θ, same ~17× mass class
as v11.** Takeoff-mass and before_share composition (declared replay,
20 seeds at base 20200205; clause needs the takeoff seeds' q05–q95 of
recorded_onsets to contain 197 and median before_share within 0.10 of
0.173):

| Θ | role | n_takeoff | rec. onsets q05/med/q95 | before_share med | clause |
|---|------|-----:|----------------------|-----------------|:------:|
| 1e9 | anchor | 11/20 | 85 / 862 / 3,164 | 0.087 | PASS (boundary — not selectable) |
| 1e11 | boundary | 20/20 | 2,966 / 3,471 / 3,523 | 0.699 | FAIL |
| 1.33e11 | admissible | 20/20 | 2,877 / 3,500 / 3,534 | 0.789 | FAIL |
| 1.78e11 | admissible | 20/20 | 2,693 / 3,496 / 3,538 | 0.876 | FAIL |
| 2.37e11 | admissible | 20/20 | 2,563 / 3,468 / 3,551 | 0.905 | FAIL |
| 3.16e11 | admissible | 20/20 | 2,407 / 3,484 / 3,570 | 0.921 | FAIL |
| 4.22e11 | admissible | 20/20 | 2,393 / 3,513 / 3,564 | 0.920 | FAIL |
| 5.62e11 | flank | 20/20 | 2,190 / 3,390 / 3,565 | 0.956 | FAIL |

Every admissible row saturates takeoff seeds at ~2,200–3,580 recorded
onsets — the q05 floor alone is 11–15× the record's 197 — and
before_share rises monotonically with Θ (0.70 → 0.96): more transmission
pulls the burn earlier into the pre-split window. The only clause pass is
the Θ1e9 anchor, a fleet-shape-inadmissible boundary row.

**Verdict: same outcome, different coordinate.** The bracket contains a
real admissible interior set, but no admissible Θ passes the conditional
clause and the clause's only pass sits outside the admissible band. The
takeoff trajectory is saturated throughout the window — the residual is
mechanism-shaped, not Θ-shaped. The Θ axis inside the bracket is
exhausted.

Full readout: `docs/covid/covid_theta_screen_v12_readout.md`; surfaces
`covid_theta_screen_v12{,_stage2}_surface.csv`, drift table
`covid_theta_screen_v12_pairs.csv`.
