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
| all_off_canary | 14b1fa7a-1e30-4eb5-a92c-c62823f80600 | picard-covid-repair-isolation-01:2 | 20 | RUNNING |
| baseline | 64121f0a-d4a5-4ad3-8009-6680104a07b5 | picard-covid-repair-isolation-01:2 | 20 | RUNNING (owner go 2026-11-20) |
| room_air_off | 3c28d7c7-cb21-427c-898b-4c6776949bf8 | picard-covid-repair-isolation-01:2 | 20 | RUNNING |
| nearfield_off | 2af3c351-9aa9-47f4-8431-8447324fa7cb | picard-covid-repair-isolation-01:2 | 20 | RUNNING |
| pool_off | bdd20586-6239-439d-ab44-f398ed736b54 | picard-covid-repair-isolation-01:2 | 20 | RUNNING |
| duty0_off | 484a6cdf-8617-4fd0-8972-6dd714647896 | picard-covid-repair-isolation-01:2 | 20 | RUNNING |

Artifacts: `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_repair_isolation_01/<block>/cell_<seed>.json`

Terminated: `e684cbbf` (rev :1, v1 image) — superseded before any cell
completed so every canary artifact carries the resolved-toggle witnesses.

## Image

- tag `covid-repair-isolation-01-v2`, digest pinned in `campaign.json`
  (`image_digest` = sha256:37a33aaf…) — built at `ecdb2c9f` (base `picard-campaign:base-ec2bc9f4` + campaign overlay); adds the resolved repair-toggle witnesses to the delivery block and the cell's fail-closed toggle check.
- superseded: v1 at `d4c5e8bd` (sha256:3d1b676a…).
