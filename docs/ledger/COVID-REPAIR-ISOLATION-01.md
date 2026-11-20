# COVID-REPAIR-ISOLATION-01
**Date:** 2026-11-20
**Commit:** ecdb2c9f
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** ecdb2c9f

Paired-arm isolation of the four airflow repairs on the DP `boxed_s1s2`
@ Θ7.9e6 replay — which of B1–B3 removed the dose the record funnel was
catching. 120 cells (6 arms × seeds 20200205–24), native transport only
(solver axis closed by COVID-TRANSPORT-FIT-01), zero failures, audit
clean: every payload carries resolved `room_air_removal.map_arm`,
`near_field_air.mode`, `pathogen_pool_transport`, `duty0_terminal_mode`
witnesses, and the cell fails closed on a mismatch. Campaign
`campaigns/covid/repair_isolation_01`, image `covid-repair-isolation-01-v2`
(sha256:37a33aaf…), jobdef `picard-covid-repair-isolation-01:2`.

## Result — two repairs act in opposite directions; the missing
pre-repair volume is not explained by the toggles

`baseline` reproduces TRANSPORT-FIT-01 exactly (1,236 pooled
lab_confirmed, 9/20 takeoff) — pairing is exact, not statistical.
Paired per-seed deltas (off-arm − baseline), all channels:

| arm | pooled lab_confirmed | takeoff | paired Δ lab median (mean) |
|---|---|---|---|
| baseline | 1,236 | 9/20 | — |
| duty0_off (sealed, CONTAM-DUTY0-01) | 1,236 | 9/20 | 0.0 (0.0) — bit-identical |
| room_air_off (ambient_off, ROOM-AIR-01) | 1,149 | 9/20 | 0.0 (−4.4) |
| nearfield_off (mode off, AERO-NEAR-02) | **76** | 1/20 | **−10.5 (−58.0)** |
| pool_off (transport none, AERO-CABIN-03) | **2,449** | 8/20 | −3.0 (**+60.7**) |
| all_off | 156 | 3/20 | −9.5 (−54.0) |

- **AERO-NEAR-02 (near-field two-box) is the dose carrier, not a dose
  remover.** Reverting it collapses pooled confirmations −94% (76 vs
  1,236) and takeoff to 1/20 — the near-field channel contributes nearly
  all of the current ensemble's volume.
- **AERO-CABIN-03 (pool `airflow` transport) suppresses the record-scale
  outbreaks.** `pool_off` doubles pooled volume to 2,449 — above the
  pre-repair ensemble (~1,351–1,453) — driven by a few huge cells (lab
  up to 670, onsets up to 569): median paired Δ is −3.0 while the mean
  is +60.7. The shipped pool transport caps exactly the cells the record
  funnel catches.
- ROOM-AIR-01 (ambient_off map) is ~neutral (16/20 cells identical);
  CONTAM-DUTY0-01 (sealed) is bit-identical on every channel.
- `all_off` ≈ `nearfield_off` (156 vs 76): with the near-field gone,
  freeing the pool adds only ~80 pooled confirmations — the volume the
  pool suppresses is mostly near-field volume.

## What this settles

The four repairs did not remove the pre-repair ensemble's volume: the
two that matter push in opposite directions, and their joint revert
leaves 156 vs the pre-repair ~1,351–1,453. Confirmations are the
funnel's output, not delivered dose; the dose ratio is unmeasured. The
missing pre-repair volume is therefore either not expressible in this
toggle grammar (`mode=none` inside machinery that exists ≠ the
machinery absent) or was lost by a change outside B1–B3 between the
pre-repair measurement and the repair branch. The single-off arms
cannot discriminate between those two readings — each retains three
repairs. Next leg: a code-level diff of what the pre-repair build did
with shed mass vs what `pool_transport=none`/`near_field off` do now.

Ledger `campaigns/covid/repair_isolation_01/LEDGER.md` holds the runs
table, per-channel tables and audit block.
