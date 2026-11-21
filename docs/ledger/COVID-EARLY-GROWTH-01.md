# COVID-EARLY-GROWTH-01
**Date:** 2026-11-21
**Commit:** 87e8e3bb2f756c6698be5fe337814a955c2a40e4
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** 87e8e3bb2f756c6698be5fe337814a955c2a40e4

Pure-readout growth decomposition over the committed COVID-SEED-RING-01 cells
(40 cells, both arms at θ=3.162e8, `tools/covid_early_growth_readout.py`,
evidence `reports/early_growth_01/seed_ring_01_growth_table.md`) — the
follow-up the NULL-PLACEMENT verdict named: does the record-timed overshoot
sit in early growth or the post-quarantine tail?

## Verdict: early growth carries the overshoot — the model's pre-quarantine
contact field is too dense once founders exist

- On the 8 record-timed cells (ignition ≤9, both arms): day-16 cumulative
  infections median **1,373 vs the record's whole-voyage band [712,960]** —
  the overshoot is in place before quarantine opens, not after.
  Before-day-17 recorded onsets median 383 vs the record's 34 (~11×).
- Early igniters then saturate at ~2,700–3,100 infections by day ~20–34
  regardless of founder count (25 founders → 3,136; 10 founders → 2,842):
  susceptible depletion, not damping, is the ceiling.
- The un-damped tail is a different regime: on the 30 late/non-igniting
  nonzero cells, post-day-16 fold median 6.3 — the ~R≈1 confinement problem
  QUAR-TAIL-01 named — but on record-timed cells post-16 growth is only
  +23–49% (the pool is already gone).
- Late igniters that land the mass (d34 median 440; band cells ~500–850)
  ignite ~10 d late. **No cell in either arm lands timing and mass together**
  — consistent with the refit surface's empty admissible set
  (COVID-H5-RESCORE-01) but now explained mechanistically.

## What this says about Θ

Θ is confounded on DP: the same composite scales the founder-stage yield and
the post-founder growth rate. The record's shape — a big day-0–5 founder
burst, then growth that produces ~800 infections total — needs those
decoupled: a dense embarkation-window contact field that relaxes to a lower
settled-voyage field. The homogeneous field splits the difference: too sparse
to reliably draw a record-class founder pool (median 2.5), too dense to stop
over-producing once one exists (~1.4–1.5×/day sustained through day 15).

Consequences:

- **SEED-RING-02, if commissioned, is not just a founder arm.** A surge
  declaration that lifts founders but leaves the post-founder field
  homogeneous predicts founder+ignition legs land and the mass leg still
  fails. The honest frozen prediction must include the surge *expiring* —
  the embarkation-crowd venues carry elevated exposure for the boarding
  window only.
- Alternatively the deficit is a missing voyage-stage contact decay
  (embarkation crowds vs settled cruise routine) rather than anything in the
  dose path — a contact-structure question, not a θ question.
- The "record was an outlier draw" reading is bounded: 8/40 cells ignite on
  time (P≈0.2 — the real voyage isn't a freak draw on timing), but the mass
  leg fails on every achievable early-igniting trajectory.
- GM held-out scoring at this θ inherits the same two-regime structure;
  the founder lottery is platform-independent.

## Standing

- Do not re-run founder-lifting arms without a voyage-stage contact
  declaration on the same campaign; founders alone cannot land the clause.
- The trajectory clause's mass leg (q05–q95 contains 197) is unreachable at
  right-sized θ under the current homogeneous contact field — the contract
  question this raises (envelope scoring vs a voyage-stage declaration) is
  an owner call, same footing as conditioned capture and FRAQMB_DUTY.

Evidence: `reports/early_growth_01/seed_ring_01_growth_table.md`;
tool: `tools/covid_early_growth_readout.py`; ops:
`campaigns/covid/seed_ring_01/LEDGER.md`.
