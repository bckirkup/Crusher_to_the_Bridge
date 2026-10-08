# CREW-BERTH-01
**Date:** 2026-10-07
**Commit:** a1961d17
**Pathogens:** sars_cov2_resp
**Status:** declared

Crew berthing and work-cohort confinement arms on the verbatim
`diamond_princess_2020` replay — the seam named by the CREW-MESS-01
berth attribution (docs/covid/covid_open_ledger.md): ~73% of the boxed
row's during-window crew events are occupational, ~27% berth-zone.

Two new confinement-order modifiers, both deterministic (zero draws on
any stream — voyage-RNG ordering and off/baseline bit-identity hold by
construction):

- `crew_berthing` — partitions each realized cabin-berthing pool
  `(home_zone, berth_group, cabin_size≥2)` on the order's declared
  exempt set, re-deals `cabin_mate_ids` status-pure and
  anchor-preserving (a cabin's min-id member staying in its pool keeps
  the stateroom/compartment key); `mode: rezone` additionally swaps
  working crew in whole-berth units into a declared `berth_zones`
  block, its confined occupants out (round-robin by ascending
  agent_id). Restored verbatim at the falling edge.
- `crew_work_cohorts` — `mode: shift_split` rewrites working-crew
  schedules so each contiguous `Work` block splits into
  `ceil(len/pods)` turns, `pod = agent_id % pods` keeps one turn and
  the rest read `Rest` (resolves `home_zone`, off-watch, day sanitary
  rate — no Sleep draw). Steward/delivery pool is not schedule-gated,
  so deliveries parity is structural.

Six arms: `shipped_baseline` (empty-override shipped SOP-017 corner —
the arm grammar's required first arm) plus five `SOP-017-*` diagnostic
counterfactuals all riding boxed meal service verbatim:
`mess_boxed_base` (drift witness vs CREW-MESS-01's boxed canary),
`berth_cohort`, `berth_rezone` (D4 block), `work_pods` (2 pods),
`combined` (= rezone + pods, the canary arm).
Replay contract verbatim CW-02. Design frozen pre-run:
`docs/covid/covid_crew_berth_01_design.md` +
`picard_framework/runs/covid_crew_berth_01_design.json`.

Frozen scoring surface: crew share target (0.2,0.4) vs record 0.29;
confined-pax guard [26,160]; deliveries parity ~162k ±15%; verdict
grammar BERTH-CHANNEL-CLOSED / CEILING-SHORT / OVER-CLOSED / UNMOVED /
PAX-COLLATERAL / DRIFT. Execution: one 20-seed `combined` canary block,
then stop and report — the full ladder runs only on the owner's
go-ahead.
