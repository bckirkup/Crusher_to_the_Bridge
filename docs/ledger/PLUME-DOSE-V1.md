# PLUME-DOSE-V1
**Date:** 2026-09-24
**Commit:** e5dc885
**Pathogens:** sars_cov2_resp
**Status:** declared

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
