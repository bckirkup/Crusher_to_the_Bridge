# NORO-GROWTH-01-RERANK
**Date:** 2026-09-27
**Commit:** fae3a49f
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** ece42dbf

SHIP-RHYTHM-02 re-rank of the NORO-GROWTH-01 (`ce8e3020`) link census on
`fl_spr_12d` with the day-program rhythm layer ON — same manifest, same
ignited seed set, same instrument. The question the re-rank answers: does
schedule-conditioned placement move the named ~zero link (secondary emesis
landing on already-immune cabins) or leave it standing?

## Cohort

The 11 ignited `fl_spr_12d` seeds that carry all 18 baseline
challenge-acquired hosts (8105, 8114, 8124, 8129, 8132, 8135, 8137, 8148,
8156, 8158, 8159) re-run under
`tools/noro_diag/growth_chain_census.py`, verbatim spec (spirit_cruise_3000,
n=3000, 288 epochs, `syndromic_comp65`, dose_adjustment 7.57), rhythm
default-on. Measured on the PR #742 tree (ece42dbf); the same-session
merges on main (#743) touch no simulation draws — spelling
canonicalization and `superseded_by` metadata only — so the numbers stand
against fae3a49f.

## Headline moves vs baseline

- Ignition: 10/11 voyages ignited (8159's index emit produced no filed
  patch under rhythm).
- Challenge-acquired hosts: **13 on the same 11 seeds** (baseline 18) —
  the schedule-partitioned exposure set thins secondary acquisition at
  the margin, without annihilating it (8114: 2→5, 8158: 3→4; most other
  seeds drop to 0–1).
- Secondary sheds scale up: 8.06M GEC pooled (baseline 449k), 29 emitted
  emesis draws filing 302M GEC of patch (baseline 221M) — confined
  symptomatics shed more under sleep/post-prandial cabin coupling.
- **Placement onto non-immune occupancy — the named metric — improves
  but does not flip.** Acquired-sourced patch sweeps meet a susceptible
  in 1,014 of 2,262 mass-bearing unit-epochs (**44.8%**, baseline 32%);
  zero-susceptible sweeps **84.7%** (baseline 91%); mass never seen by a
  susceptible **83.6%** (baseline 89%). Deposited surface mass, however,
  concentrates *more* in cabins: 1.04M of 1.11M GEC acquired-sourced
  deposits land on cabin_fittings (baseline split was inverted: 68k
  cabin vs 272k shared).
- Delivered pickup mass roughly doubles: acquired-sourced patch pickup
  7.42M GEC (baseline 3.46M) plus 96k zone-pool.
- Conversion stays at naive rate: acquired-sourced hazard expectation
  4.22 vs **3 observed** acquired-sourced acquisitions (baseline: 1.32
  vs 4 — the baseline overshoot was the lucky venue landings).
- Total acquisitions 13 across 11 ignited seeds; the chain remains
  subcritical — no compounding voyages.

## Per-run named link (rhythm vs baseline)

| seed | baseline link | rhythm link |
|---|---|---|
| 8105 | L3 | L0 (no secondaries) |
| 8114 | L4 | intact end-to-end |
| 8124 | L4 | L0 |
| 8129 | intact | L4 |
| 8132 | L4 | L4 |
| 8135 | L3 | L0 |
| 8137 | intact | L4 |
| 8148 | L4 | L4 |
| 8156 | L4 | L0 |
| 8158 | L4 | intact end-to-end |
| 8159 | L4 | cold (not ignited) |

L4 dominates the survivors: challenge events now draw on acquired mass
(hazard 4.22) but convert at/below naive rate — the remaining blocker is
the frailty-draw lottery, not placement.

## Verdict

The rhythm layer measurably shifts secondary-emesis exposure toward
non-immune occupancy (co-presence 32→45%, unseen mass 89→84%, delivered
pickup ×2.1) and halves secondary acquisitions on this seed set. The
named ~zero link stands in weakened form: ~5/6 of patch mass still lands
where no susceptible can touch it, and the surviving block is now the L4
frailty draw rather than the L3 occupancy miss. No constants moved; the
re-rank changes placement, not parameters.

## Instruments

`tools/noro_diag/growth_chain_census.py` + `growth_chain_readout.py`,
run zips under local `growth_runs/fl_spr_12d/` (scratch; this table is
the durable record), readout JSON
`telemetry_buffer/noro_rhythm_rerank.json`.
