# NORO-HAND-CASCADE-01
**Date:** 2026-11-10
**Commit:** b0b0483c
**Pathogens:** all
**Status:** open

First implementation stage of the hand/fomite cascade repair. The measured
defect is ledger `NORO-DOSE-01`: non-shedding hosts can carry hand mass, but
hand-mediated source routes gated on shedding status, so carriers were dead
ends and surface/hand propagation could not chain. The same audit found the
epoch order backwards for same-hour spillover: legacy fomite deposits and
picks up once per epoch before food deposits and before end-of-epoch hygiene,
so a contaminated hand could not redeposit within the occupied-space window
that the transfer kernels describe.

This entry records the landed arm, not a campaign result. No anchor was
fitted and no VSP/Park/attack-rate target was used to choose a constant.

## Landed mechanism (default-off arms)

`transmission.hand_reposit_mode` is `shedders_only` by default; the labelled
arm `carriers` lets a non-shedder with a whole-copy hand load
(`pickup_gate_open`, currently the 1 GEC pickup gate) act as a hand
depositor for surface, sanitary-venue, and food hand-transfer paths.
`_get_hand_depositors` returns shedders plus those carriers; sub-copy hands
remain excluded. `_replenish_hand` has a carrier guard: a non-shedding host
with picked-up mass decays that mass by the declared inactivation rate
without drawing stool-event or hygiene-practice events it cannot produce.

`transmission.intra_epoch_causal_order` is `legacy` by default; the labelled
arm `ordered` runs the fomite phase as sanitary/emesis pickup before surface
deposits, surface redeposition before zone pickup, and defers end-of-epoch
hand hygiene until after food deposits when food contamination is enabled.
With food contamination disabled or absent, ordered fomite still ends with
the same hygiene pass inside the fomite phase.

Carrier lineage is deliberately narrow: pickup records the dominant source
strain on `agent.hand_strain_by_pathogen`, and carrier redeposition falls
back to `unresolved` when no single lineage is known. This is a bookkeeping
bridge, not a full hand-mixture state; mixture carriers need the strain-state
work tracked outside this entry.

## Evidence and limits

Local guards in `tests/test_hand_redeposit_cascade.py` assert the default
legacy gates, the whole-copy carrier gate, hand→surface mass conservation for
a carrier deposit, carrier hand decay without shedder practice draws, and
the ordered hygiene deferral/flush. Existing fomite, per-surface, direct-hand,
strain-ledger, and stool-event tests remain the legacy bit-identity checks.

Not landed here: `M>1` substeps or a continuous/event-driven intra-epoch
integrator, pinch-point surface/food disaggregation, hand-to-hand donor
sampling for carriers, renewal boarding defaults, and any default flip. The
arms stay default-off until paired-seed witnesses show truncated carrier
mass, pool gain, third-party pickup, hand→mouth dose, strain attribution,
and cross-pathogen RNG effects are material. Direct-contact partner sampling
is still shedder-weighted, so carrier eligibility is currently wired for
surface/sanitary/food hand deposits, not for choosing contact partners.
