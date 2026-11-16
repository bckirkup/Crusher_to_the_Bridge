# NORO-HAND-REDEPOSIT-STREAM-01
**Date:** 2026-11-16
**Commit:** 2271f2c1
**Pathogens:** norwalk_gi
**Status:** closed

Defect/fix: `transmission.hand_redeposit_mode: carriers` was not a
stream-preserving amplification arm. `_replenish_hand` had a carriers-only
branch for non-shedding hosts with picked-up hand load: it decayed the load by
inactivation and returned before the configured `hand_reservoir_mode` practice
cycle, so the carriers arm suppressed the non-shedder stool/hygiene/self-contact
RNG/event stream that `shedders_only` runs.
`FOOD-SUPPLY-01-REDEPOSIT-WORST` measured that collapse (`stool_calls` about
1.58-1.60M down to about 96k-168k, `continuous_path_calls` down, and
`total_quarantine_person_epochs` down on every pair), so its carriers-vs-
`shedders_only` contrast was a bundled arm, not a clean redeposit effect.

Fix: `_replenish_hand` no longer branches on `hand_redeposit_mode`; hand
maintenance is shared across `shedders_only` and `carriers`. `carriers` now
changes only hand-deposit eligibility and carrier strain carry
(`_get_hand_depositors`, surface/sanitary/food hand deposits, and carrier
pickup strain attribution). In `hygiene_cycle`, a stool event on a
`target <= 0` host still consumes the defecation/wash draw stream but does not
queue protected sequestration or set a stool-linked target; only shedding
targets can add protected copies from that visit. Own-environment self-contact also no longer uses
the stool-linked shedding target as a ceiling for `target <= 0` hosts, so a
carrier's self-contact moves own-environment mass onto the hand instead of
wiping the accessible load. The carriers arm is therefore the declared
amplification test: the same non-shedder maintenance stream, plus whole-copy
hand redeposition.

Validation: `python3 -m pytest tests/test_hand_redeposit_cascade.py -q`
passed (16 tests), including a paired guard that a non-shedding whole-copy
carrier produces the same hand load, protected/pending compartments,
own-environment pool, carriage propensity, practice draws, wet-transfer state,
and inactivation rate under `shedders_only` and `carriers` on matched seeds; a
residue-floor guard showing carriers no longer has a special zero/pop path; a
self-contact guard showing `target <= 0` carriers conserve hand + own-pool
mass while reloading from that pool; and a stool-event guard showing a forced
non-shedding carrier event queues no protected pending/load and does not raise
the accessible load.

Invalidation: the `FOOD-SUPPLY-01-REDEPOSIT-WORST` carriers-arm numbers are
historical for the carriers mechanism as of this entry; they measured the
suppressed-replenish bundled arm. The `target <= 0` protected-sequestration
gate applies in every `hand_redeposit_mode`, so prior non-shedder protected
hand-mass trajectories are historical after this entry as well.
`hand_redeposit_mode` remains `shedders_only` by default. No anchor fitting or
campaign rerun is implied by this entry.
