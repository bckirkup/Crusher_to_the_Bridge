# NORO-CARRIER-DISTRIBUTE-01
**Date:** 2026-11-24
**Commit:** #1411
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** a994d8c6

CARRIER-DISTRIBUTE (D3″) campaign per
`docs/norovirus/hand_carrier_distribute_spec.md`, implementation PR
#1411. NORO-EXTERNAL-SEQUESTER-01 measured the hand-reservoir
retention stage working (cold-cell mouth fraction ~3% → ~11% of
delivered mass) with take-off still under the floor — the next
candidate bound was the *source* of hand-reservoir mass: under the
shipped model only shedders deposit to surfaces and donate in contact
draws, so carrier-carried load is a dead end. This campaign adds
`hand_redeposit_mode: "carriers"` (carrier tuples may deposit to
sanitary/surface/food sinks) and `hand_donor_mode: "carriers"`
(carrier tuples may donate in `per_partner_contact` draws), both
default-off and bit-identical at defaults.

## Frozen decision criteria (campaigns/noro/noro_carrier_distribute_01/LEDGER.md)

- Two arms × 20 seeds (8000–8019), stacked on the measured S+R stack
  (`item_instances`, `hand_sequester_fill: "any_load"`,
  `hand_residual_mouthing: "per_epoch"`, `contamination_solver:
  "discrete"`): arm **R** = redeposit=carriers + donor=shedders_only;
  arm **R+D** = both carriers. 8105/8106 stay held.
- Ignites := ≥9 of the 18 previously-cold cells (8000/8006 are
  known-hot) reach Σhazard ≥ 1.1.
- Audit invariants per cell: len-288 epoch ledger; hand partition
  `sources = sinks + residual` ≤1e-9 rel; resolved-mode stamps;
  carrier provenance witness (every carrier depositor/donor traced to
  an earlier witnessed acquisition).

## Result — both arms, seeds 8000–8019 (Measured at: a994d8c6)

Batch arrays `94b2cae4-9d57-44a9-b528-f42bbf31bf79` (R, jobdef :2) and
`c32d3cd8-13ed-4480-b095-3c27d697dad2` (R+D, jobdef :3), image
`sha256:d9752d7253be8c6ac5f0a9123a41868935b96c5c2a610407678be3eef94a0573`,
288 epochs. Exception: the R+D seed-8000 artifact resolves from the
canary run (image sha256:e248e234, code 05830b3a — differs from the
pin only in the S1244 `sv <= 0.0` syntax, semantically identical;
the role lacks s3:DeleteObject so the canary artifact stayed at the
prefix). **All 40 cells passed the frozen audit** — len-288
ledgers; the four counter reconciliations (Σrow hazard vs
`sum_evaluated_hazard`, Σsecondaries vs `transmission.secondaries`,
Σdelivered-to-hands vs `mass_delivered_to_hands_gec`,
Σhand-to-mouth vs `hand_to_mouth_dose_gec`) within ~2e-13 rel
(three of four exact); hand partition closure ≤~8e-15 rel; zero
provenance and zero carrier violations on every cell; resolved
stamps read carriers/shedders_only and carriers/carriers as
designed.

- **The mechanism fired wherever carriers held mass.** Arm R: median
  120 carrier depositors per cold cell (max 749). Arm R+D: median 120
  depositors / 102 donors per cold cell (max 792/765, up to ~44k GEC
  donated on 8018, ~300k on hot 8006). Three cells (8004, 8010, 8015)
  had **zero** carrier depositors on both arms — no carrier ever held
  an accessible ≥1 GEC load there, so the mechanism could not
  participate at all on those seeds; all three sit at σ ≈ 0.
- **Neither arm crosses the take-off gate.** Cold cells ≥1.1:
  arm S+R (prior) **1/18** (8018); arm R **5/18** (8002: 2.60,
  8005: 2.96, 8009: 13.25, 8012: 1.42, 8018: 5.15);
  arm R+D **4/18** (8002: 3.73, 8005: 5.83, 8009: 5.09, 8018: 8.23).
  Cold-cell median σ: 0.264 (S+R) → 0.270 (R) → 0.251 (R+D). Hot
  cells rose under both arms (8000: 34 → 61 / 40; 8006: 134 →
  166 / 201). Per-seed comparisons are directional only — the
  selectors change pool composition, so the draw streams diverge
  (same caveat as EXTERNAL-SEQUESTER).
- **Dose landing is not the bound.** `hosts_for_90pct` median on cold
  cells: 217 (S+R), 148 (R), 166 (R+D) — far above the frozen ~8
  breadth bar on every arm. Mouth fraction of delivered mass held at
  baseline: median 15.2% (S+R), 7.7% (R), 15.5% (R+D); dead-mouth
  share and raw→scaled ratios unchanged (×1.02–1.13).
- **Wall clock** ~290–310 s/cell vs ~293 s on S+R (same 1-vCPU shape).

## Verdict under the frozen rules

**Carrier mass redistribution moves real mass but delivered volume is
still the bound.** The frozen rule's "breadth rises" clause does not
apply verbatim — breadth was already above the ~8 bar at baseline
(217) and stayed there (148/166; per-seed moves are RNG-divergent).
The operative condition holds on either reading: dose landing is
wide and neither arm ignites, so the bound the rule names is the
operative one — aggregate delivered volume / hazard conversion, the
~200× multiplier to hot-cell credited mass. Carriers demonstrably
deposit and donate where they hold load, yet the median cold cell
sits at σ ≈ 0.25 — the same order as every measured arm. Per the
rule: report, change nothing else.

## Follow-ups the spec explicitly does not authorize

- Promotion of either selector to default-on (separate decision).
- The three zero-carrier cells (8004, 8010, 8015) are a separate
  bound: carriers never accumulated ≥1 GEC accessible load there —
  worth one line in the next lever's design (carrier load accrual
  rate vs the sequester/mouthing drains).
- Held seeds 8105/8106 remain reserved for the full-campaign
  decision.
