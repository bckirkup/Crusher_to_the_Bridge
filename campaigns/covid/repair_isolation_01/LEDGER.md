# COVID-REPAIR-ISOLATION-01 — per-repair paired-arm isolation on DP

**Status:** canary running on Batch
**Task:** COVID-REPAIR-ISOLATION-01
**Design:** `picard_framework/runs/covid_repair_isolation_01_dp_design.json` (6 arms × 20 seeds = 120 cells)
**Parent measurement:** TRANSPORT-FIT-01 full readout — takeoff collapsed to 9/20, median lab_confirmed 10.5 vs record 712, pooled volume preserved by a few record-scale cells; solver choice outcome-identical.

## Question

Which of the four airflow repairs removed the delivered dose the boxed_s1s2
record funnel was catching? One repair at a time returns to its labelled
pre-change baseline on the same seeds, plus `all_off` (the whole pre-repair
model, cross-checked against the pre-repair ensemble ~1,351–1,453 pooled
lab_confirmed) and `baseline` (shipped, re-run at this revision for exact
seed pairs).

## Arms (native transport only — solver axis is closed)

| arm | toggle | pre-change baseline |
|---|---|---|
| baseline | — (shipped) | — |
| room_air_off | `transmission.room_air_removal.map_arm` | `ambient_off` (AHU-only map; ROOM-AIR-01) |
| nearfield_off | `transmission.near_field_air.mode` | `off` (no two-box table channel) |
| pool_off | `hvac.pathogen_pool_transport` | `none` (AERO-CABIN-03) |
| duty0_off | `hvac.duty0_terminal_mode` | `sealed` (CONTAM-DUTY0-01) |
| all_off | all four | pre-repair model |

## Runs

| Block | Job ID | Rev | Cells | Status |
|---|---|---|---|---|
| all_off_canary | e684cbbf-893b-4e9a-91e3-6f49f728a744 | picard-covid-repair-isolation-01:1 | 20 | RUNNING |
| baseline | — | — | 20 | pending owner go |
| room_air_off | — | — | 20 | pending owner go |
| nearfield_off | — | — | 20 | pending owner go |
| pool_off | — | — | 20 | pending owner go |
| duty0_off | — | — | 20 | pending owner go |

Artifacts: `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_repair_isolation_01/<block>/cell_<seed>.json`

## Image

- tag `covid-repair-isolation-01-v1`, digest pinned in `campaign.json`
  (`image_digest` = sha256:3d1b676a…) — built at `d4c5e8bd` (base `picard-campaign:base-d4c5e8bd` + campaign overlay).
