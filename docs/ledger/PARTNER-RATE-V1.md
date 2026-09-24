# PARTNER-RATE-V1
**Date:** 2026-09-24
**Commit:** 1264f60
**Pathogens:** sars_cov2_resp
**Status:** declared

Partner-rate sensitivity assay on the AERO-SPLIT-01 droplet-partition
architecture: the first measured response surface for the ~18× conditional-size
gap since the partition became the shipped default. Declared in
`picard_framework/runs/covid_partner_rate_assay_v1_design.json` (frozen before
any assay cell ran). Nothing in this entry is a result; it moves to measured
when the canary is read out.

## Declared (before any cell runs)

AERO-SPLIT-01's probe (measured at e20008d) halved the non-takeoff seed's
events but left the takeoff-seed day-0–2 spike standing (68.7% → 57.1% share) —
plume per-partner dose keeps ring infections near-certain at the shipped
CONTACT-ARCH-01 partner rates, and the conditional gap stands at ~3,470–3,520
recorded onsets on takeoff seeds vs the record's 197. This assay asks whether
the ring's *reach* — the partner rate itself — binds that gap.

Same declared replay as the stage-2 cell shape (Θ 4.22e10, onset_day −1.0,
dwell_weighted sanitary visits, imports 1, infection_age 3.3, the same 20 seeds
at base 20200205, full 32-day voyage). Nine arms × 20 seeds = 180 cells:

- R0_declared — shipped table at multiplier 1.00 (baseline, empty overrides).
- R1–R7 — `transmission_overrides.activity_contacts` replaces the block
  wholesale with the shipped rates scaled ×{0.25, 0.50, 0.75, 1.25, 1.50,
  1.75, 2.00}.
- R8_pool_witness — `droplet_field_split.mode: off`, the pool-era baseline on
  current main; execution witness against the pre-partition stage-2 row.

Axis binding was verified in the tree before freeze: under `partition`,
`_proximity_shedder_ids` draws the ring's partner count from
`activity_contacts[activity][role]` — scaling `rates_per_hour` IS scaling the
ring's reach, and no new arm grammar was needed. The local preflight smoke
(`tools/covid_partner_rate_smoke.py`) proves the override lands in the run
spec, scales the engine's parsed table and the ring-path partner draws ~4× at
×0.25, and draws nothing under `off` — executing the bit-identical-baseline
claim.

Frozen scoring: the stage-2 conditional clause family per arm (takeoff-seed
gate ≥10 recorded onsets; q05–q95 vs 197; before_share vs 0.173), plus the
declared response-curve reads — reach binding (monotonicity), log-log
elasticity, the elbow (does ANY multiplier's q05–q95 contain 197), and the R0
vs R8 witness delta. Declared counterfactual: if even 0.25× over-produces, the
next suspect is per-partner plume dose (β) or the ring definition, not reach.
Declared RNG caveat: rate scaling changes draw values, so all reads are
distribution-level, never seed-paired; the off witness draws nothing on the
proximity path and is not pairable either.

This is not a v2 revival: B7 swept the same table on the pre-partition
architecture where it bounded only the direct-contact path (~0% of measured
events); under partition the table bounds the droplet carrier's near-field
reach — a different question.

## Report immediately if

- the canary row (R1_rate_0p25, 20 seeds at INDEX_OFFSET 20) is read out —
  stop after it; the user decides the array;
- any arm's conditional q05–q95 contains 197;
- any arm collapses takeoff below ~5/20;
- the multiplier does not bind the proximity ring at runtime — spec-lands but
  inert is a bug signature, not physics;
- any cell's audit invariant fails (index_onset_day ≠ −1.0 or
  index_shedding_at_day0 false); or the child failure rate exceeds 5%.
