> **Status:** Handoff record (2026-11-16), authored against `main` = `8d4c1874` after #1269 merged. Reports **no new numbers**: every figure is quoted from the ledger entry that measured it, with that entry's `Measured at` SHA. Read `docs/norovirus/norovirus_open_ledger.md` §1 before quoting any dose figure — every dose figure in the repository remains withdrawn pending the refit.

# Norovirus hand-cascade CE handoff — 2026-11-16

## 1. The question

Decide whether the hand-mediated contamination loop needs a continuous/event-driven (CE) reference, and if so implement it as a comparator — not a new epidemiological model. The posted-conditioned cell is `fl_exp_12d_sens_p06_paxv`, `expedition_cruise_450`, `norwalk_gi`, 288 epochs, seeds 8073/8038/8046/8047/8077 for the DS-M solver work; the paired carrier witness used `classic_cruise_1900` seeds 8105/8106. Observables are deposited/delivered mass, dose, infected/symptomatic, carrier surface/food/sanitary deposits and calls, runtime, mass-balance residual, active-set/event counts, and RNG stream neutrality. Success is a CE arm that either matches M=1 within the solver-gate tolerance on posted cells (close the solver question, keep M=1) or shows a material difference that becomes the reference for deciding whether the pooled/touch-share representation is the binding defect. Failure is a CE arm that cannot be built without new unmeasured parameters; per the proposal that means the non-minimal path is a new model, not a comparator.

## 2. Current hypothesis

Fixed-M is not the solver answer. The repaired carrier-redeposit arm is a real hand-mediated amplification path on the two-seed witness, but the fixed-M DS-M sweep does not converge through M=60 and M=60 is already ~2.9–4.8× the M=1 voyage runtime on the posted cell. The next hypothesis is that the binding constraint is either the within-epoch integration of the hand-mediated contamination loop or the pooled/touch-share/contact-constant representation; the CE comparator exists to separate those before any default or anchor work.

## 3. Evidence for

- **`NORO-HAND-CASCADE-01-SUBSTEPS-M60`** (`docs/ledger/NORO-HAND-CASCADE-01-SUBSTEPS-M60.md`, measured at `af8dda30`; PR #1269): completes the predeclared fixed-M sweep through M=60. Every consecutive refinement pair exceeds the 10% deposited/delivered/dose tolerance on at least one posted seed; the smallest worst-seed maximum absolute relative change is still 73.0% (deposited, M24→M60). Runtime is 59.7–71.7 s/voyage at M=1, 114.0–169.9 s at M=24, and 183.9–301.8 s at M=60. Mass balance closes with max absolute error 7.1e-9 GEC (relative ≤ 4.7e-15) and `delivered_to_reservoir_gec` is 0.0 on every re-run row.
- **`NORO-HAND-CASCADE-01-SUBSTEPS-CURRENT`** (`docs/ledger/NORO-HAND-CASCADE-01-SUBSTEPS-CURRENT.md`, measured at `605f9841`; PR #1265): the current-main re-pilot still did not converge through M=12 on the same five posted seeds; M=2/4/12 are non-monotone within seeds and inconsistent across seeds, with carrier surface calls growing to roughly 44k–115k at M=12 without a stable deposited/delivered/dose limit.
- **`NORO-HAND-REDEPOSIT-STREAM-01-WITNESS`** (`docs/ledger/NORO-HAND-REDEPOSIT-STREAM-01-WITNESS.md`, measured at `bae0d181`; PR #1263): the stream-preserving `carriers` arm produced nonzero carrier surface/food deposits and higher delivered/dose on both `classic_cruise_1900` seeds 8105/8106 versus `shedders_only`; seed 8105 also moved infected/symptomatic. This is directional evidence, not a default-flip gate.
- **`NORO-HAND-REDEPOSIT-STREAM-01`** (`docs/ledger/NORO-HAND-REDEPOSIT-STREAM-01.md`; PR #1261): `_replenish_hand` no longer branches on `hand_redeposit_mode`, so `carriers` isolates deposit eligibility/strain carry instead of bundled carrier-carriage effects.

## 4. Evidence against / unexplained

- The paired carrier witness is only two seeds and carrier sanitary deposits were 0 on both; it shows the mechanism can fire, not that it should be default.
- The fixed-M sequence is non-monotone and seed-dependent, so there is no monotone refinement trend to extrapolate; infection-count movement is reported, not gated, in the solver-gate tolerance.
- The M≤60 sweep reused the M=2/4/12 rows from `605f9841` because `605f9841..0b79b716` had no relevant diff for the engine/platform/pathogen files; that reuse is recorded in the M60 ledger but means the sweep is not a single-commit rerun.
- The M60 ledger states no separate substep RNG-stream probe was run; RNG stream neutrality for CE remains a predeclared guard, not a measured result.
- The CE proposal's alternative hypothesis is still live: if CE agrees with M=1, or all fixed-M arms converge to the same deposited/delivered/dose, the solver is not binding and the next suspect is the upstream contact/behaviour constants (`docs/proposals/noro_hand_cascade_ce_comparator.md` §6.1).

## 5. PRs landed this session

In dependency order:

1. #1261 — stream-preserving carrier redeposit repair; ledger `NORO-HAND-REDEPOSIT-STREAM-01`.
2. #1263 — paired-seed carrier redeposit witness; ledger `NORO-HAND-REDEPOSIT-STREAM-01-WITNESS`.
3. #1265 — current-main DS-M M≤12 re-pilot; ledger `NORO-HAND-CASCADE-01-SUBSTEPS-CURRENT`.
4. #1269 — DS-M M≤24/M≤60 sweep arms/runtime and solver-branch ledger; `NORO-HAND-CASCADE-01-SUBSTEPS-M60`.

## 6. Running jobs

None from this session. All witnesses were local diagnostic runs driven by `tools/noro_diag/hand_cascade_witness.py`; the commands are recorded in the ledger entries above and the JSON outputs under `reports/noro_diag/` are reproducible local artifacts, not committed campaign outputs. No AWS Batch array was submitted.

## 7. What is now void

No committed measurement is withdrawn by this handoff. The standing withdrawals in `docs/norovirus/norovirus_open_ledger.md` §1 still apply, including every dose figure pending refit. Already-recorded invalidations remain in force: the bundled `FOOD-SUPPLY-01-REDEPOSIT-WORST` carriers-arm numbers are historical for the pre-repair bundled arm per `NORO-HAND-REDEPOSIT-STREAM-01`, and the older fixed-engine DS-M pilot rows are historical after platform/HVAC data changes per `NORO-HAND-CASCADE-01-CONTACT-BINDING`; the current reprobe and M≤60 sweep are the live fixed-M record.

## 8. The single open decision

**Implement the CE contamination-loop comparator exactly as scoped, or stop and report if the scope cannot be met without new unmeasured parameters.** The next session should follow `docs/proposals/noro_hand_cascade_ce_comparator.md`: engine arm `transmission.contamination_solver: "event"` default off, scoped to pooled fomite + food + sanitary + emesis-patch pickup with no per-surface expansion, zero new fitted constants, legacy/discrete bit-identical, then add the CE arm to `tools/noro_diag/hand_cascade_witness.py` and run the same posted seeds. The settling evidence is whether existing rates/kernels can be event-ized within that budget; if not, the proposal's decision rule says stop and report that the non-minimal path is a new model.

## 9. Do not reopen

- Do not fit any constant to VSP/Park/attack-rate/passenger-crew anchors, and do not choose an `M` or CE detail because it improves A4/A8/A9.
- Do not flip `transmission.hand_redeposit_mode`, `transmission.intra_epoch_causal_order`, or `transmission.intra_epoch_substeps` defaults from this evidence; M=1 is not privileged, but no measured arm has earned a default move.
- Do not treat the two-seed carriers witness as a default-flip gate or as an effect size.
- Do not add pinch-point/per-surface expansion, new areas, servings, or contact rates to the first CE arm without a separate provenance-register entry.
- Do not submit a campaign array before the campaign-preflight gate; local paired-seed witnesses come first.
- Do not quote dose figures from this thread; `norovirus_open_ledger.md` §1 keeps every dose figure void pending refit.
