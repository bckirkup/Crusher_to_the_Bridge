# COVID-THETA-REFIT-01 — Θ refit on DP under the post-B1-B3 mass budget, GM held-out

**Status:** canary running
**Task:** COVID-THETA-REFIT-01
**Designs:** `picard_framework/runs/covid_theta_refit_01_dp_design.json` (240 cells: 12 θ × 20 seeds),
`picard_framework/runs/covid_theta_refit_01_gm_design.json` (600 cells: 12 θ × 50 seeds)
**Parent measurement:** REPAIR-ISOLATION-01 + diagnosis — ambient/deck sinks live under the new
mass budget absorb the ~12× emission increase; pooled confirmations ≈ flat at ~1,236 vs
pre-repair ~1,351–1,453, but takeoff collapsed to 9/20 and the outbreak tail is capped by
`pathogen_pool_transport=airflow`. The fitted Θ (7.9e6, tranche 25) predates all of it.

## Question

Θ is the COVID arm's single fitted composite (emission scale × per-copy risk; tranche 25
refused separating them). Re-fit it on the DP `boxed_s1s2` replay under the shipped
post-repair stack, then score the refit on held-out Greg Mortimer — the covid_first_look
fit/held-out split enforced (no held-out quantity enters selection).

## Grid

`thetas = [7.9e6] + log-spaced 1e7…1e12 × 11 half-decades` (12 points; 7.9e6 retained as the
TF-01 baseline cross-check: expected pooled lab_confirmed ~1,236). Same grid on both hulls.

| phase | design | seeds | cells |
|---|---|---|---|
| fit (DP `boxed_s1s2`) | `covid_theta_refit_01_dp_design.json` | 20200205–24 (×20) | 240 |
| held-out (GM `hygiene_cycle` default stack) | `covid_theta_refit_01_gm_design.json` | 20200205–54 (×50) | 600 |

Scoring: `merge_fit` (per-θ mean log-residual on covid.T1 recorded_onsets + covid.T3
campaign positives, bootstrap selection frequency, `boundary_pinned` flag) →
`merge_held_out` (GM at fitted θ ± half-decade neighbours: covid.H1 positive share vs
128/217, H2 asym share vs 0.8125, H3 IQR placement, takeoff).

## Runs

| Block | Job ID | Rev | Cells | Status |
|---|---|---|---|---|
| dp_theta_6p90 (canary) | 8f6ebe9a-3b5d-4493-8dea-534eb5e489cb | picard-covid-theta-refit-01:1 | 20 | SUBMITTED |

Artifacts: `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_theta_refit_01/<block>/cell_<seed>.json`

Image: `covid-theta-refit-01-v1` @ `sha256:48a6cd069ced2a897a642ae81df6bd86f1904114091e1721f32e3cd8b57fbf7a`
(base `picard-campaign:base-c053e15f`, built at branch HEAD `c053e15f` on merged main `fdae828b`).

## Canary readout — `dp_theta_6p90` ×20

Pending. Expected: pooled lab_confirmed ≈ TF-01's ~1,236 (same design, same seeds, same
shipped stack — this is the drift cross-check before trusting the rest of the sweep).
