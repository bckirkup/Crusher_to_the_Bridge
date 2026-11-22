# NORO-DOSE-LEDGER-01
**Date:** 2026-11-22
**Commit:** #1392
**Pathogens:** norwalk_gi
**Status:** measured (22 cells, AWS Batch picard-noro-dose-ledger-01:1)

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
- Ledger sums reconcile against the voyage counters on the same dump,
  each within 1e-9 relative:
  `Σ net_surface_gain_gec == surface_mass_deposited_gec`,
  `Σ delivered_to_hands_gec == mass_delivered_to_hands_gec`,
  `Σ (hand_to_mouth_dose_gec + flow_mouth_dose_gec)` equals the voyage
  mouth-dose counters,
  `Σ hazard == sum_evaluated_hazard`.
- Semantics pinned, because two fields are easy to misread:
  `net_surface_gain_gec` is the pool's net per-epoch change (pickups
  cancel deposits in-epoch), not gross emission;
  `delivered_to_hands_gec` already contains `patch_delivered_gec` —
  patches deliver through the shared `_deliver_fomite_requests`, so
  patch mass is a subset, never an addend;
  `discrete_requested/offered_gec` see only the discrete `_deliver`
  calls, not the solver's `pickup_mass`.
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

## Result — measured 2026-11-22 (22 cells, 288 epochs, jobdef :1)

**Status:** measured.

**Measured at:** `1f8a027c` (instrument + review fixes; engine
unchanged since the declaration). Image
`picard-campaign@sha256:958502fdb33283d41db65dbbd937791e687945311e4a7fbf842d14fe67ec652f`,
jobdef `picard-noro-dose-ledger-01:1`, cells seeds 8000–8019 + 8105/8106.

All frozen invariants passed on all 22 cells (len-288 ledgers; sums
reconcile to voyage counters within 1e-9; `Σ secondaries == acquired_ids`;
`Σ emesis_events` matches the emesis witness).

Pooled mass ledger (GEC):

| stage | pooled |
|---|---|
| net surface gain | 215,527 |
| delivered to hands | 24,707,373 |
| — of which emesis patch | 24,640,696 (99.7%) |
| mouth dose (discrete + solver-integrated) | 1,006,596 (532k + 475k) |
| hand→hand moved | 4,061 |
| Σhazard → secondaries | 184.1 → 182 |

Per-cell structure:

- Hot cells are patch cells. Every high-hazard cell (8000: 31.0, 8006:
  146.0, 8105: 1.1) is ≥98% patch-delivered; the largest hazard epochs
  inside them are `common_source_food` bursts (1.5–22M GEC/epoch
  credited) that ignite the chain, after which the tail runs on
  patch-fomite + caregiver mass (fomite credits 100–150k GEC in patch
  epochs).
- The zone pool is a write-only reservoir: cold cells deposit 65–14,129
  GEC net gain yet deliver ~0–4k total; pooled over all cells,
  non-patch delivered mass is ~0.3% of delivered.
- Delivered→mouth conversion ~4% pooled — the hand reservoir sheds
  ~96% of delivered mass to wash/decay before swallowing.
- Hand→hand moved mass is negligible everywhere (≤2k GEC/cell) — the
  multi-hop leg contributes nothing measurable under the freeze.
- Secondaries ≈ Σhazard at the cell level (182/184): once a dense
  encounter exists, the challenge converts at ~99%.

Verdict on Edison's attenuation-vs-structure question: within-epoch
attenuation is real (96% delivered→mouth loss) but is not the binding
term — the binding term is structural: ordinary pooled fomite never
delivers, so interpersonal propagation exists only where an emesis
event lands a concentrated patch in an occupied unit. Take-off
requires dense-encounter structure, not magnitude.
