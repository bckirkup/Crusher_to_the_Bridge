# CAREGIVER-ATTR-01
**Date:** 2026-10-04
**Commit:** b932d0e9
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** b932d0e9

## Question

PR #868 measured that the Θ1e9 Diamond Princess anchor row — the only
clause pass ever recorded, at `6efec855` (takeoff 10/20, q05 153, band
∋197) — fails on the merged tree (PROP_OFF: 20/20, q05 1,190, Δ med
+1,634 vs v15). PROPENSITY-V1 was exonerated by its own off arm. Which
merge in `6efec855..main` moved the anchor off its pass region?

## Declaration

`picard_framework/runs/covid_caregiver_off_v1_design.json` (PR #872):
`{D0_declared, CG_OFF} × Θ1e9 × 20 seeds` at the verbatim v15 stage-2
replay contract. `CG_OFF` writes `transmission.caregiver.mode = off` on
the propensity-off tree (PROP_OFF's surface is the drifted reference).
Verdict grammar frozen pre-run: RESTORATION (CG_OFF clause-passes →
CAREGIVER-V1 is the mover) or EXONERATION (CG_OFF still ≈2,300 → bisect
the remaining window merges).

## Measured

40/40 cells, 0 audit failures (`docs/covid/covid_caregiver_off_v1_readout.md`).

**RESTORATION — CAREGIVER-V1 is the mover.** CG_OFF clause-passes on
both legs: takeoff 11/20, recorded q05/med/q95 10/1,559/2,428 (band
∋197), before_share median 0.200 against the 0.173±0.10 leg — the same
median v15 recorded. D0_declared on the same image stays drifted
(19/20, q05 1,518) and replicates the PROPENSITY-V1 canary's D0 arm
bit-identically (max |Δ| = 0, all 20 seeds) — the engine is exactly the
canary generation's. Seed-paired: CG_OFF − v15 = −46 median onsets on
10 takeoff pairs (statistically the same surface); CG_OFF − PROP_OFF =
−762 [−2,330, +1,238], which is the caregiver channel's fill-in of the
v15 fizzle margin. Witnesses: `caregiver.mode` echoes on/off 40/40;
pooled caregiver-route dose 248 on D0 vs 0 on CG_OFF; propensity
units_drawn 0 on all CG_OFF cells (bit-identity on that arm).

The clause's only passing cell on the shipped-default tree therefore
exists on the `caregiver.mode: off` tree. Whether the caregiver
mechanism's effect on the DP anchor is itself correct is the follow-up
question — this entry settles only the attribution.

Run note: both on-demand EC2 CEs stalled at scale-out; the array ran on
Fargate (`picard-covid-boarding-screen-fargate:1`,
`picard-analysis-fargate-queue`).
