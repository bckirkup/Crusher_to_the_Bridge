# COVID-REBASE-01
**Date:** 2026-09-26
**Commit:** 6a7dfe4e
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** 6a7dfe4e

Θ window re-screened on the post-721 base: admissible set EMPTY;
boarding structure measured and is not the takeoff burn. Stage-A cells
ran on the `f280e348` image; stage-2/3 cells on `6a7dfe4e` (design files
only — the engine/data tree is identical).

Readout of record: `docs/covid/covid_rebase_01_readout.md`.
Designs: `picard_framework/runs/covid_rebase_01{,_stage2,_boarding}_design.json`
(frozen criteria verbatim from v11 before any cell ran).
Arrays (AWS Batch EC2 Spot, `picard-covid-boarding-screen` jobdef revs 25–26,
digest-pinned images): stage A `92d51ecc-47b5-4982-9d3e-6bad5375bee9`
(3,200/3,200), stage 2 `41fc6295-0d97-4e89-9584-630890fe5c0e` (80/80),
stage 3 `0c3e9e64-d14f-4824-a6cc-bf9272a06609` (200/200); zero failed
children in any stage. Cells under
`s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_rebase_01{,_stage2,_boarding}/<sha>/cells/`.

## What was re-measured

Every fitted Θ in `docs/covid/covid_open_ledger.md` was void pending a
refit on the post-721 base (REINFECT-01, QUAR-EXEMPT-01, AERO-NEAR-02,
AERO-SPLIT-01, DOSE-FRAIL-01, INDEX-GEOM-01, SEED-ONSET-01 all landed or
re-scored since the v11 stage-2 measured SHA `8cda4c7`). The v11
admissible set {3.16e10, 4.22e10, 5.62e10} was the comparator band.

## Results

1. **Fleet-shape selector (generic voyages, 16-point union lattice × 200
   seeds): admissible set EMPTY.** Interior-lattice medians sit at
   0.00027 (one recorded onset) from 1.78e10 through 1e11 — the v11 band
   rows that read 0.00067–0.00168 now fail the 0.0005 floor — while
   1e12 overshoots (median 0.0154, mean 0.073 > 0.06). The window is
   bracketed in (1e11, 1e12). Mechanism is suppression, not shift:
   seed-paired against v11 refine, recorded onsets fall on 100–128 of
   200 seeds at every shared Θ, and P(takeoff) dropped ~15–20 pp across
   the band. The takeoff tail stays DP-sized (q75 up to 0.017 recorded);
   the median voyage fizzles. covid.H3's near-critical fleet shape has
   no fixed point on this lattice.
2. **Conditional clause (declared replay, v11 band, 20 matched seeds):
   still FAILS at all three points — same ~17× mass class** (takeoff
   q05–q95 1,485–3,493 vs target 197; never contains it; mass in
   [98.5, 394] = 0). Composition changed: median before_share halved to
   0.45–0.66 from v11's 0.77–0.92 (target 0.173 ± 0.10) — the burn now
   lands inside the day-16–30 quarantine window. The Θ 1e9 QUAR-ATTR-V2
   anchor row passes the clause in form (interval-spanning, mass-near-197
   0.09) — a boundary readout, never a candidate; its canary cell
   re-measured 3,365 infections / 0.9068 attack vs the record's
   3,458 / 0.9318.
3. **Boarding structure (10 seed_patch arms × 20 seeds at Θ 4.22e10,
   declared fallback):**
   - Seed-age axis (onset_day ∈ {+3, +1, 0, −1, −3, −5}): takeoff is
     insensitive (19–20/20 everywhere, including a day-0 non-emitter);
     aboard-window acquisitions move ~10× across the span (median 18 →
     207 late-course). The axis moves window composition, not voyage
     outcome.
   - Seed-count axis (count ∈ {1, 2, 4, 8, 32}): window acquisitions
     scale 18 → 2,330 (median share of infections 0.5% → 67%);
     yield/seed saturates (18 → 184 → 73). At the declared geometry the
     day-0→5 window is a median 0.5% of takeoff-class infections and the
     clean index-only bound is a median of 3.
   - **The boarding-debt hypothesis is answered: no.** Majority-of-burn
     requires ≥~8 simultaneous co-primaries — an order of magnitude past
     the record — so the takeoff burn is downstream chains in the
     post-721 compartment structure, not the index ring.
   - Window route split is ~87–90% droplet / ~10–12% hvac_airborne,
     direct_contact ~0, in every arm.

## Consequences for the open ledger

- The void-pending-refit list is unchanged: still no admissible Θ to
  carry. What the rebase adds is that the v11 band is now *known dead*
  on this base rather than merely stale, and the live search space is
  (1e11, 1e12) — a bisection there is the next stage decision.
- INDEX-GEOM-01 and SEED-ONSET-01 are closed as *measured axes*: both
  exist, both are bounded, and neither explains takeoff-class burn at
  the declared geometry. INDEX-GEOM-01's residual question — what the
  correct seed *count* for the record is — is now known to matter above
  count ~4 and to saturate by ~32.
- The conditional clause's failure is now the primary Θ-adjacent
  defect: ~17× onset mass on takeoff, unchanged in class but with the
  pre-split share halved — consistent with the post-721 containment
  compartments absorbing early burn rather than a boarding artifact.
