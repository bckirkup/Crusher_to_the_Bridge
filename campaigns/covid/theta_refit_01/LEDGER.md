# COVID-THETA-REFIT-01 — Θ refit on DP under the post-B1-B3 mass budget, GM held-out

**Status:** canary complete — awaiting go on the 23 fleet blocks
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
| dp_theta_6p90 (canary) | 8f6ebe9a-3b5d-4493-8dea-534eb5e489cb | picard-covid-theta-refit-01:1 | 20 | SUCCEEDED 20/20, read out |
| dp_theta_7p00 | 6268b476-6fe8-40d9-a387-4aee5e52035c | :1 | 20 | SUBMITTED |
| dp_theta_7p50 | 25547508-15d2-49a8-9442-d590ef3da383 | :1 | 20 | SUBMITTED |
| dp_theta_8p00 | 43d10ff3-507d-49c1-933f-69056e6dc4a3 | :1 | 20 | SUBMITTED |
| dp_theta_8p50 | 186da10f-902f-4868-ad4d-43c4ede84795 | :1 | 20 | SUBMITTED |
| dp_theta_9p00 | 9628318a-f9be-4039-9650-c97bfd63a105 | :1 | 20 | SUBMITTED |
| dp_theta_9p50 | ece0005a-8307-4d9c-a994-88133a1335db | :1 | 20 | SUBMITTED |
| dp_theta_10p00 | 9ff6be8c-40e1-44ff-ba9e-eb3096672504 | :1 | 20 | SUBMITTED |
| dp_theta_10p50 | a42241be-11e5-4cd4-8c3c-85cdceab9392 | :1 | 20 | SUBMITTED |
| dp_theta_11p00 | 7793f6ce-855f-45ac-905d-27eb8b853262 | :1 | 20 | SUBMITTED |
| dp_theta_11p50 | 7f6ddf32-acb4-452b-b7da-7a7c6ab3d4fb | :1 | 20 | SUBMITTED |
| dp_theta_12p00 | 94a15beb-59a4-4802-90ff-2f0a13a86d91 | :1 | 20 | SUBMITTED |
| gm_theta_6p90 | 3b14b2da-e912-499a-98f0-12a707beb4e5 | :1 | 50 | SUBMITTED |
| gm_theta_7p00 | 2be88473-3484-4719-8f9a-ca3b71539c29 | :1 | 50 | SUBMITTED |
| gm_theta_7p50 | bbda0216-0c3e-4da5-82f6-50724c688d5e | :1 | 50 | SUBMITTED |
| gm_theta_8p00 | 83a27607-23bc-47f7-82cb-62ddcc7d6f7c | :1 | 50 | SUBMITTED |
| gm_theta_8p50 | 7917d482-a3d2-4a47-a105-78554475383d | :1 | 50 | SUBMITTED |
| gm_theta_9p00 | da892fb1-afd6-407b-be57-1ca4a990d887 | :1 | 50 | SUBMITTED |
| gm_theta_9p50 | 2c194335-54bb-417a-b92e-ac4a07042811 | :1 | 50 | SUBMITTED |
| gm_theta_10p00 | 95005bf9-6ff7-406c-aac3-8feb93d51292 | :1 | 50 | SUBMITTED |
| gm_theta_10p50 | 397bfa4a-786c-407a-a9ac-04927e2d5c73 | :1 | 50 | SUBMITTED |
| gm_theta_11p00 | b8a00e11-a55c-47a4-a195-9de2f7b368a5 | :1 | 50 | SUBMITTED |
| gm_theta_11p50 | 2bac1362-08fe-430f-9e5a-42cd86a5d9f8 | :1 | 50 | SUBMITTED |
| gm_theta_12p00 | b61e9c48-3974-4c2e-84cf-b5a58b78647e | :1 | 50 | SUBMITTED |

Artifacts: `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_theta_refit_01/<block>/cell_<seed>.json`

Image: `covid-theta-refit-01-v1` @ `sha256:48a6cd069ced2a897a642ae81df6bd86f1904114091e1721f32e3cd8b57fbf7a`
(base `picard-campaign:base-c053e15f`, built at branch HEAD `c053e15f` on merged main `fdae828b`).

## Canary readout — `dp_theta_6p90` ×20 (measured at `8dee1ce6`, image v1 @ `c053e15f`)

Audit clean: 20/20 cells loaded, 0 findings — every payload carries
`design_id=covid_theta_refit_01_dp`, `arm_id=baseline`, all four shipped toggles
(ambient_on / two_box / airflow / extract), and `transport_engine_resolved=ContamTransportEngine`.

**Drift cross-check passes exactly.** Pooled `lab_confirmed_total` = **1,236** —
identical to TF-01/REPAIR-ISOLATION-01 baseline on the same seeds. Per-seed
`campaign_positives` and `recorded_onsets` are equal on all 20 seeds vs the RI-01
baseline arm (payloads differ only in audit-echo fields). Ensemble shape unchanged:
takeoff 9/20, median campaign_positives 10.0, median recorded_onsets 8.0.

The θ=7.9e6 anchor point reproduces the shipped stack, so the rest of the sweep is
measuring Θ, not drift.
