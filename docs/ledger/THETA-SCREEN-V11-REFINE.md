# THETA-SCREEN-V11-REFINE
**Date:** 2026-09-22
**Commit:** 79a3ac3
**Pathogens:** sars_cov2_resp
**Status:** measured

**Measured at:** 79a3ac3

Stage-1 lattice refinement of `covid_theta_screen_v11` (THETA-SCREEN-V11)
inside the located band. Declared in
`picard_framework/runs/covid_theta_screen_v11_refine_design.json`; readout
`docs/covid/covid_theta_screen_v11_refine_readout.md`. The stage-2 declared
replay it gates is frozen in
`picard_framework/runs/covid_theta_screen_v11_stage2_design.json` before
any stage-2 cell exists.

## Declared (before any cell runs)

The v11 decade-lattice stage 1 (`7660392`, 1,600/1,600 cells) measured an
empty admissible set with the covid.H3 median window bracketed between
Θ 1e10 (median 0.00027, a 1.85× floor miss while IQR and mean pass) and
Θ 1e11 (median 0.0158 overshoot, mean 0.075 > 0.06): any admissible Θ
lives strictly inside (1e10, 1e11). This design re-ran the IDENTICAL
stage-1 cell shape on an eighth-decade interior lattice —
{1.33, 1.78, 2.37, 3.16, 4.22, 5.62, 7.5}e10 × 200 seeds = 1,400 cells,
same seed base 20201001 (rows paired by seed with the decade rows), same
frozen fleet_shape_selector verbatim. The extra runs went to Θ
resolution, not seeds (200 already carries ~3% Binomial SE on a 0.25 tail
share). Tighter grid bought with more runs rather than a further session,
per the user's direction. One-part canary: 50 seeds at Θ 3.16e10 (band
centre, cell indices 600–649 under theta-outer enumeration), spec audit +
non-degeneracy; on a clean read the array proceeds.

## Result

**The admissible set is non-empty: Θ ∈ {3.16e10, 4.22e10, 5.62e10} pass
the fleet-shape selector.** Array
`45cfb31d-eb50-4042-9d6d-17499d9a3934` (1,400 cells, job def
`picard-covid-boarding-screen:15`, image `theta-v11-refine-79a3ac3`
`sha256:ab3c0026...`): 1,400/1,400 SUCCEEDED, zero failures. Canary
`04144ec5-dcf6-4582-b780-642afee00d44` (50 cells at INDEX_OFFSET 600):
spec audit clean — no declared onset/departure, no ascertainment key, 168
epochs, unchanged contract — and non-degenerate.

The band is ~0.25 decades wide and interior: 1.33–2.37e10 fail the
median floor alone (median 0.00027 vs 0.0005) and 7.5e10 fails the median
ceiling (0.0089) AND the mean cap (0.065) — the same clause pair 1e11
failed, so the high-side closure is median-overshoot-with-mean-cap, not
the mean cap alone. P(takeoff) climbs 0.385 → 0.57 across the band.
Conditional-on-takeoff recorded_onsets medians run 129.5–247 with
q05–q95 intervals (~17–1,220) containing the record's 197 at every row —
the free read on the stage-2 clause before any replay cell runs.

No `report_immediately_if` trigger fired (three-point pass, interior
band, mixed failing clauses, zero failures, clean spec audit).

**Stage 2 is now enumerated** per the v11 `stage_2.theta_points` clause:
the union admissible set {3.16, 4.22, 5.62}e10 plus nearest failing
flanks 2.37e10 and 7.5e10 — five points, none on the decade lattice, so
all five run new cells — × 20 matched seeds at base 20200205 = 100
declared-replay cells, verbatim v10 cell shape, scored on takeoff seeds
only by the frozen conditional_trajectory_clause (q05–q95 of
recorded_onsets contains 197 AND median before_share within 0.10 of
0.173; ≥5 takeoff seeds or "insufficient takeoff mass"). Frozen in
`covid_theta_screen_v11_stage2_design.json` in the same change as this
entry.
