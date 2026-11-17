# NORO-HAND-CASCADE-01-CE-FEASIBILITY
**Date:** 2026-11-16
**Commit:** 72807d4f
**Pathogens:** norwalk_gi
**Status:** open

Scope: feasibility decision for `docs/proposals/noro_hand_cascade_ce_comparator.md`
under the zero-new-fitted-constants budget, after the 2026-11-16 handoff. No
engine code changed, no constants added, and nothing was fitted to VSP, Park,
attack-rate, or passenger/crew anchors. This entry reports no new measurements;
quoted figures are from the cited measured ledger entries.

## Decision

- **Implementable within budget:** only the staged-aggregate scheduled-event CE —
  pooled fomite + food + sanitary + emesis-patch pickup, reusing the existing
  per-hour/per-day rates and transfer kernels, with
  `transmission.contamination_solver: "event"` default off and legacy/`discrete`
  bit-identical.
- **Not implementable within budget:** a literal per-contact CE. The contact
  audit (`NORO-HAND-CASCADE-01-CONTACT-AUDIT`, PR #1206, measured at `0bcfca80`)
  found the binding gaps are areal/contact geometry, per-item touch shares, hand
  wet/dry state dynamics, bare-hand food-contact rate, food-handler per-shift
  shedding probability, food item/serving structure, sanitary fixture and
  within-visit sequence, and upstream person-contact architecture. Those need
  either new Grade C declaration axes or a separate provenance-register entry;
  the CE proposal already excludes pinch-point/per-surface expansion.

## Why this is not a stop

`NORO-HAND-CASCADE-01-CONTACT-AUDIT` already records that staged aggregate CE can
reuse the existing kernels without new fitted constants. The contact-binding
probe (`NORO-HAND-CASCADE-01-CONTACT-BINDING`, PR #1215, measured at `b47596b1`)
says the posted `fl_exp_12d_sens_p06_paxv` cells are dominated by
`common_source_food` (95.79–99.85% of route-ledger mass), with hand-mediated food
deposits only 0.014–0.259% of surface deposit mass and fomite acquired share
0.14–4.09%. CE is therefore a solver/secondary-process comparator, not a
posted-tail repair.

Owner clarification for this stage: the target is the within-epoch hand-process
update and a believable secondary-contamination share — on the order of ~10% of
cases not directly tied to one large contaminated-food service event — not
closure of total cruise attack rate or the VSP tail.

## Next decision

For the clarified hand-process goal, implement the staged-aggregate CE arm
exactly as scoped in `docs/proposals/noro_hand_cascade_ce_comparator.md`:
`transmission.contamination_solver: "event"` default off, legacy/discrete
bit-identical, no per-surface expansion, zero new fitted constants; then add the
CE arm to `tools/noro_diag/hand_cascade_witness.py` and run posted seeds
8073/8038/8046/8047/8077 before any default or anchor discussion. If the objective
is instead the posted-event tail, pivot to common-source food binding before
paying the CE implementation cost.

## Do not reopen

- Do not fit any constant to VSP/Park/attack-rate/passenger-crew anchors, and do
  not choose an `M` or CE detail because it improves A4/A8/A9.
- Do not flip `transmission.hand_redeposit_mode`,
  `transmission.intra_epoch_causal_order`, or `transmission.intra_epoch_substeps`
  defaults from this evidence.
- Do not add pinch-point/per-surface expansion, new areas, servings, or contact
  rates to the first CE arm without a separate provenance-register entry.
- Do not submit a campaign array before the campaign-preflight gate; local
  paired-seed witnesses come first.
