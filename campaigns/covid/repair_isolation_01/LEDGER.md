# COVID-REPAIR-ISOLATION-01 — per-repair paired-arm isolation on DP

**Status:** complete — 120/120 cells, full readout below
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
| all_off_canary | 14b1fa7a-1e30-4eb5-a92c-c62823f80600 | picard-covid-repair-isolation-01:2 | 20 | SUCCEEDED 20/20, read out |
| baseline | 64121f0a-d4a5-4ad3-8009-6680104a07b5 | picard-covid-repair-isolation-01:2 | 20 | SUCCEEDED 20/20, read out |
| room_air_off | 3c28d7c7-cb21-427c-898b-4c6776949bf8 | picard-covid-repair-isolation-01:2 | 20 | SUCCEEDED 20/20, read out |
| nearfield_off | 2af3c351-9aa9-47f4-8431-8447324fa7cb | picard-covid-repair-isolation-01:2 | 20 | SUCCEEDED 20/20, read out |
| pool_off | bdd20586-6239-439d-ab44-f398ed736b54 | picard-covid-repair-isolation-01:2 | 20 | SUCCEEDED 20/20, read out |
| duty0_off | 484a6cdf-8617-4fd0-8972-6dd714647896 | picard-covid-repair-isolation-01:2 | 20 | SUCCEEDED 20/20, read out |

Artifacts: `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_repair_isolation_01/<block>/cell_<seed>.json`

Terminated: `e684cbbf` (rev :1, v1 image) — superseded before any cell
completed so every canary artifact carries the resolved-toggle witnesses.

## Canary readout — `all_off` ×20 (measured at merge SHA on `14b1fa7a`, image v2 @ `ecdb2c9f`)

Audit clean: 20/20 cells, `wrong_engine` and `wrong_toggles` empty — every
payload carries resolved `room_air_removal.map_arm=ambient_off`,
`near_field_air.mode=off`, `pathogen_pool_transport=none`,
`duty0_terminal_mode=sealed`, `transport_engine_resolved=ContamTransportEngine`.

| channel | all_off (n=20) | record | TF-01 shipped (same seeds) | pre-repair ensemble |
|---|---|---|---|---|
| recorded_onsets | median 3.0 [0–23] | 197 | — | — |
| lab_confirmed | median 3.5 [0–31] | 712 | median 10.5 | — |
| takeoff share (≥10 onsets) | 3/20 | always | 9/20 | — |
| pooled lab_confirmed | **156** | — | ~1,236–1,294 | ~1,351–1,453 |
| dated share | 0.74 | 0.277 | ~0.81 | — |
| lab crew share (pooled) | 0.84 | 0.29 | ~0.45–0.75 | — |

**The pre-repair ensemble did not come back — `all_off` yields ~8× fewer
pooled confirmations than the shipped model on the same seeds** (156 vs
~1,236 pooled lab_confirmed, takeoff 3/20 vs 9/20). Confirmations are the
funnel's output, not delivered dose; the dose ratio itself is unmeasured.
Since the witnesses prove all four toggles resolved to their labelled
baselines, either (a) the toggle baselines do not reconstruct the
pre-repair code paths — `mode=none`/sealed inside machinery that exists
is not the same as the machinery being absent (e.g. shed mass may be
routed into a pool that never releases), or (b) another change between
the pre-repair measurement and now removed confirmations upstream of
the funnel. The single-off arms inform but cannot fully discriminate:
each retains three repairs, so a revert that restores takeoff names a
contributing repair, but if every off-arm under-carries the result is
consistent with interacting repairs or incomplete reconstruction as
well as a regression outside the toggle grammar.

## Full readout — 120 cells, audit clean (no wrong engine/toggles/missing)

`baseline` reproduces TRANSPORT-FIT-01 exactly on the same seeds (1,236
pooled lab_confirmed, 9/20 takeoff) — the pairing is exact, not statistical.

| arm | lab_confirmed med [q05–q95] mean | pooled lab | takeoff | paired Δ lab med (mean) |
|---|---|---|---|---|
| baseline | 10.5 [0–145] 61.8 | 1,236 | 9/20 | — |
| duty0_off | 10.5 [0–145] 61.8 | 1,236 | 9/20 | 0.0 (0.0) — bit-identical |
| room_air_off | 10.5 [0–145] 57.5 | 1,149 | 9/20 | 0.0 (−4.4) |
| nearfield_off | 2.5 [0–8] 3.8 | **76** | 1/20 | **−10.5 (−58.0)** |
| pool_off | 7.0 [0–670] 122.5 | **2,449** | 8/20 | −3.0 (**+60.7**) |
| all_off | 3.5 [0–31] 7.8 | 156 | 3/20 | −9.5 (−54.0) |

**Two repairs act in opposite directions, and the regression answer is
"neither removed the record's dose":**

- **AERO-NEAR-02 (near-field two-box) is the dose carrier, not a dose
  remover.** Reverting it collapses pooled confirmations to 76 (−94%) and
  takeoff to 1/20 — the near-field channel contributes nearly all of the
  current ensemble's volume.
- **AERO-CABIN-03 (pool `airflow` transport) suppresses the record-scale
  outbreaks.** `pool_off` doubles pooled volume to 2,449 — *above* the
  pre-repair ensemble — but driven by a few huge cells (lab up to 670,
  onsets up to 569): median paired Δ is slightly negative while the mean
  is +61. The shipped pool transport caps exactly the cells the record
  funnel catches.
- ROOM-AIR-01 (ambient_off map) is ~neutral (−87 pooled, 16/20 cells
  identical); CONTAM-DUTY0-01 (sealed) is a strict no-op — bit-identical
  on every channel.
- `all_off` ≈ `nearfield_off` alone (156 vs 76): when the near-field is
  gone, freeing the pool adds only ~80 pooled confirmations — the pool's
  suppressed volume is mostly near-field volume.

**What this settles:** the four repairs did not remove the pre-repair
ensemble's volume — the two that matter push in opposite directions and
their joint revert (all_off) leaves 156 vs the pre-repair ~1,351–1,453.
The missing pre-repair dose is therefore either not expressible in this
toggle grammar (`mode=none` inside existing machinery ≠ the machinery
absent) or was lost by a change outside B1–B3 between the pre-repair
measurement and the repair branch. The single-off arms cannot

discriminate between those two readings — the next leg is a code-level
diff of what the pre-repair build actually did with shed mass vs what
`pool_transport=none` does now.

## Image

- tag `covid-repair-isolation-01-v2`, digest pinned in `campaign.json`
  (`image_digest` = sha256:37a33aaf…) — built at `ecdb2c9f` (base `picard-campaign:base-ec2bc9f4` + campaign overlay); adds the resolved repair-toggle witnesses to the delivery block and the cell's fail-closed toggle check.
- superseded: v1 at `d4c5e8bd` (sha256:3d1b676a…).
