# INFO-SUPPRESS-V1
**Date:** 2026-10-01
**Commit:** cbe3b478
**Pathogens:** sars_cov2_resp
**Status:** measured

The surviving named class after SUPPRESS-V1's `suppression_incapable`:
suppression keyed on the outbreak becoming **known** — the escalation
stoplight reaching a declared status — not on a protocol schedule. The DP
record's incidence peaked at the Feb 5 confinement announcement;
passengers self-isolated and ship operations changed when the
disembarked-case news broke ~Feb 1–3, days before formal quarantine.

Mechanism (default OFF, zero draws when disabled): latches on
`state.trigger_status` ≥ declared rank, then per latched epoch — (a)
`self_isolation_scope` offers voluntary confinement under the shipped
FRED sticky classes (a declined offer writes no `quarantine_refusers`
mark — declining voluntary isolation is not refusing an order); (b)
`closed_zones` cancels venues outright via `engine.cancel_venues`
(removed from all dining/leisure catalogs, assignments re-pointed home,
one-shot); (c) `route_scalars` multiplies `tx_core` channel scalars
(post-`_step_protocols` reset — no compounding). Witness fields land on
`SimulationState`; `cell_payload` echoes the declared block plus
recognition/arming epochs, applied zones, and admitted ids.

Canary (the whole design — no array beyond it): anchor Θ 2.37e11,
declared replay, age 6.8, 1 import, arms {D0_declared, IS01_dp_replay
(scope passengers, 23 closed_zones, direct_contact_scalar 0.5),
IS02_isolation_only} × 14 seeds @20200205 = 42 cells, Batch job
`picard-info-suppress-v1` (`c79d3ac2`), job-def
`picard-covid-boarding-screen:41`, image digest `sha256:48be838b…`,
design `picard_framework/runs/covid_info_suppress_v1_design.json`
(admissibility frozen before any cell ran), readout
`tools/covid_info_suppress_v1_readout.py`.

## Measured (42/42 cells, 0 audit failures)

- **The mechanism fires.** Recognition armed on every conditioned cell
  (takeoff ≥10 recorded onsets): 12/14 seeds per IS arm. Median arming
  day 9.62; probe seed 20200205 armed day 3.04 (SUSPECTED epoch 73,
  CONFIRMED epoch 88). On two late-recognition seeds (armed ~day 18) the
  scheduled SOP-017 sweep had already confined ~2,667 passengers —
  zero volunteers, the channels confirmed parallel: once the formal
  machinery lands the info channel has nobody left.
- **The channel suppresses, seed-paired vs D0 (n=12 takeoff pairs).**
  IS01: Δrecorded_onsets −276 [−459, +2], Δinfections_total −269
  [−446, +2]; IS02 (isolation alone): −215 [−343, 0] / −205 [−325, 0].
  ~8% paired incidence cut — real, mostly carried by mass voluntary
  self-isolation (median ~2,190 admitted of ~2,660 passengers); venue
  closure + the contact scalar adds ~64 infections averted.
- **The named composition check fired.** Row-level takeoff
  before_share moved 0.742 → 0.630 (IS01) / 0.678 (IS02), but the
  seed-paired Δbefore_share is −0.031 [−0.119, +1e-5] (IS01) and −0.033
  [−0.074, +0.006] (IS02): `bshr_composition_only = true` on both arms
  under the frozen criterion (row move ≥0.05 while the paired band
  straddles zero). The timing improvement is takeoff-seed selection,
  not an asymmetric lever.
- **Anchors unlanded** (as designed — the anchors gate landing, never
  selection): conditioned medians rec ~3,100–3,200 vs 197, inf
  ~3,190–3,280 vs [712,960], bshr ~0.63–0.68 vs 0.173. No row satisfies
  the conditional-trajectory clause.

## Verdict

`recognition_suppression_real_bshr_composition_only` — the
information-event channel works as designed (fires on recognition, mass
voluntary isolation, real ~8% paired suppression) but (a) its before_share
move is a takeoff-composition artifact per the frozen check, and (b) an
8% cut ordered at median day 9.6 cannot reach the ~18× count gap or the
0.173 timing split. Where the SOP sweep lands first, the channel adds
nothing at all.
