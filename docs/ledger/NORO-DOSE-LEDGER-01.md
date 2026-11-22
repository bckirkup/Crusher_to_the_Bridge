# NORO-DOSE-LEDGER-01
**Date:** 2026-11-22
**Commit:** (pending — instrument change this PR)
**Pathogens:** norwalk_gi
**Status:** declared

Joined per-epoch mass-ledger diagnostic for the norovirus hand/fomite
mechanism review (D0′ in the 2026-11-22 review). Edison's first question —
where does deposited material stop between emission and infection — requires
the per-epoch waterfall, not the voyage sums the committed witnesses report:
each stage's mass is conserved in aggregate while the epoch-by-epoch flow can
still strand it.

## Question

For each epoch of each frozen cell, how much mass enters the
hand/fomite system (hand deposits to surfaces, emesis patch deposits, stool
deposits), how much is offered, delivered to hands, moved hand-to-hand,
carried, swallowed, credited by pathway, and converted to hazard — and how
much remains standing in each reservoir at epoch end?

## Mechanism

`tools/noro_diag/per_host_dose_challenge.py` Recorder gains five fields
(`hazard_cum`, `hand_to_hand_moved_gec`, `hand_to_hand_calls`,
`epoch_ledger`, `_ledger_prev`) and `_wrap_fomite` gains one wrapper on
`_per_partner_contact_dose` that sums `moved` mass per call — the only stage
with no existing counter. Every other stage is the per-epoch delta of an
existing pathogen-keyed cumulative counter, flushed in a new epoch observer
that runs after `_ill_census` at the end of `ShipSimulation.step` (after
`_resolve_pathogen_challenge`, so hazard and acquisitions join the same
epoch). Reservoir snapshots are pure reads:
`Σ agent.hand_load_by_pathogen[pid]`,
`Σ core.surface_pools_by_pathogen[pid]`,
`Σ patch.mass over emesis_patch_pools_by_pathogen[pid]`.
Loss terms (wash strip, hand inactivation, cleaning, surface decay) are
deliberately uninstrumented — they are the residual the readout closes as
`start + in − out − end` per reservoir.

RNG neutrality: all new witness points are post-call reads of return values
and standing state; no `rng` draw is added, moved, or consumed. Verified by
the standard gate — a wrapped and unwrapped run of the same seed produce
identical voyages.

Output contract: `epoch_mass_ledger` (list of per-epoch dicts) is added to
the per-seed summary; every existing key is unchanged.

## Campaign

`campaigns/noro/noro_dose_ledger_01/` — block `classic_cruise_1900`, seeds
8000–8019 plus the paired seed 8105/8106 (22 cells), epochs 288, worker
`tools/noro_diag/per_host_dose_challenge.py`, artifact
`per_host_dose_challenge_seed{seed}.json.gz` under
`s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_dose_ledger_01/`.

## Frozen criteria (written before any cell ran)

Audit invariants — a violation is an instrument defect, not a null result:

- `len(epoch_mass_ledger) == 288` on every cell.
- Ledger sums reconcile against the voyage counters on the same dump:
  `Σ deposited_gec == surface_mass_deposited_gec`,
  `Σ (pool_delivered_gec + patch_delivered_gec) == mass_delivered_to_hands_gec`,
  `Σ hand_to_mouth_dose_gec == hand_to_mouth_dose_gec`,
  `Σ hazard == sum_evaluated_hazard`, each within 1e-9 relative.
- `Σ secondaries` equals the acquisitions count; `Σ emesis_events` equals
  the emesis witness total.

Reported, never selected on:

- the per-epoch waterfall ratios (delivered/deposited, swallowed/carried,
  hazard/credited) per cell and pooled over cold vs hot cells;
- reservoir standing mass trajectories (hand, pool, patch) and their
  dwell times;
- the loss residuals per reservoir per epoch;
- hand_to_hand_moved_gec as a share of delivered mass;
- where hazard epochs sit relative to deposit and patch epochs
  (coincident vs lagged).

Selection / decision rules:

- The campaign answers one question: **where does mass stop**. The readout
  names the largest loss reservoir per cell and whether it concentrates in
  specific stages (e.g. delivered→mouth, pool standing stock, patch decay).
- If hazard is carried by epochs where a named stage converts ≥50% of
  entering mass, attenuation is measured there; if mass instead decays as
  standing stock before pickup, the binding term is structural (contact
  timing/coverage), and D2′ (epidemiological-n high-touch sweep) is gated
  ON.
- No model change is proposed from this campaign alone; it gates D2′ and
  scopes D1′.

## Spend

22 cells × 1 vCPU; per-cell wall clock from the canary (the local 24-epoch
smoke ran ~4 min; 288 epochs expected ~45–60 min/cell on Batch).
