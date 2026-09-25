# PLUME-DOSE-V1
**Date:** 2026-09-24
**Commit:** e5dc885
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** 2bcdeb7

Per-partner plume-dose and ring-composition assay on the AERO-SPLIT-01
droplet-partition architecture, opened by PARTNER-RATE-V1's measured
negative on the reach axis. Declared in
`picard_framework/runs/covid_plume_dose_assay_v1_design.json` (frozen
before any assay cell ran). Nothing in this entry is a result; it moves
to measured when the canary is read out.

## Declared (before any cell runs)

PARTNER-RATE-V1 (measured at 37dc215, Batch job-def rev 19) cut
`activity_contacts.rates_per_hour` to ×0.25 on the same 20 takeoff seeds
and recorded 1,275–3,525 conditional onsets (q05 2,457 / median 3,474 /
q95 3,518) vs the record's 197 — the band does not contain 197, the ring
is dose-saturated, not reach-limited. Its declared counterfactual named
the next suspects: per-partner plume dose (β) or the ring definition.

This assay maps both, on the same declared Diamond Princess replay at
Θ 4.22e10, `droplet_field_split: partition`, the same 20 seeds at base
20200205 — 10 arms, 200 cells:

- **Dose sweep** D1–D4 at multipliers {0.05, 0.10, 0.25, 0.50}× via
  `transmission_overrides.near_field_air.interzonal_airflow_m3_per_hour`
  = {4080, 2040, 816, 408} m³/h (the partition-form dose is ∝ 1/β;
  shipped β 204 stands at D0). The low end is a declared mechanism
  probe, not a parameter proposal.
- **Knockout arms** K1–K4 zero the sampled ring per activity (dining,
  work, cabin+corridor, leisure) — the ring-definition probe the
  existing arm grammar can express; fixed rings (cabin-mate, meal
  tables) persist by construction and the shared direct-contact table
  confound is declared.
- **W_pool_witness**: `mode: off` at shipped constants — the pool-era
  baseline on current main.

Frozen reads: dose_binding / linearity / elbow / collapse_point on the
dose curve, the knockout table vs D0, and the witness delta. Declared
counterfactual both directions: if even 0.05× dose over-produces, dose
is not the binder either — the suspect moves to the ring's fixed
structure or the observational channel; if a dose arm collapses takeoff
or contains 197, dose is load-bearing and the curve locates the scale
the record's number lives at — a map, never a tuned β.

Canary: D1_dose_0p05, all 20 seeds (INDEX_OFFSET 20), then STOP and
report — the array is the user's decision.

## Measured (full array, 2bcdeb7, Batch job-def rev 20)

All 200 cells measured; canary D1 read first (array
`24a6733d-8340-4079-afd1-1abf2defc1bf`), then the full array
(`09526af1-c234-4398-b95e-d2cd319dbc5c`) by user decision; image digest
`sha256:aca8d6b8…` built from merged main; results under
`s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_plume_dose_assay_v1/2bcdeb7/cells/cells/`.
0% child failures; audit invariant held on 200/200 cells. Readout:
`docs/covid/covid_plume_dose_assay_v1_readout.md`.

**Declared counterfactual fired: dose is not the binder, and the sampled
ring does not carry the mass.** Conditional recorded mass (takeoff seeds,
recorded_onsets ≥ 10) vs the record's 197: D0 3,486 / D1 ×0.05 3,435 / D2
×0.10 3,448 / D3 ×0.25 3,462 / D4 ×0.50 3,453 (medians) — log-log
elasticity 0.004 over a 20× dose range; no arm's q05–q95 contains 197 at
any grid point (no dose-only closure scale); collapse_point unmeasured
(×0.05 still clears the gate at 19/20). Knockouts: K1–K4 medians
3,441–3,492 at 20/20 takeoff — no single activity's sampled ring is
load-bearing. Witness: W_pool 3,517 vs D0 3,486 — partition and pool are
indistinguishable on this metric. Tail events (RNG-reordered,
distribution-level): seed 20200217 → 0 on all dose arms and W; seed
20200222 → 54/31 on D1/D2. Standing suspects per the counterfactual: the
fixed cabin-mate/meal-table rings, the seeded index's day-0 exposure
geometry, or the observational channel.
