# ISO-QUARTERS-01
**Date:** 2026-10-07
**Commit:** b154e43b
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 7c0559b7f991361ca9eff570bceecb81300a5b32

Two legs of one defect on the confined-quarters emesis channel, on the
`noro_age_food_01_defpair` measurement (22/24 cells with
`service_deliveries` > 0, 0/24 with steward-side
`service_dose_credited`):

1. **The sentinel drop.** `_epoch_zone_occupants` removes a host at
   `Isolated_In_Quarters` (with `Ashore`/`Departed`) before the fomite
   deposit pass — physically the host is still in its stateroom, where
   the bolus lands, so its emesis deposited nowhere. `isolated_ids` is
   a dormant channel today — no production code populates it — but the
   sentinel is a real placement the engine can hold, and the gap binds
   the moment any arm uses it.
2. **The compartment read.** On a Cabin_Corridor hull every emesis
   emit — confined or free — files its `EmesisPatch` under the
   stateroom compartment key `<zone>::cabinN`, while
   `_caregiver_service_surface_dose` read
   `pools.get(host.home_zone)`, the parent block key no emit ever
   writes to. The measured confined population is the *quarantined*
   set (`current_location` stays the home zone): they already emit
   correctly under the compartment key; the read never found it. On a
   compartmented hull every steward-side surface-dose figure was a
   gate artefact, not mechanism state.

Repair (`transmission.isolated_quarters_deposits`, `deposits_only`
default-ON; `off` is the labelled bit-identical baseline):

- `_isolated_quarters_deposits` runs in `_pathway_fomite` after
  `_fomite_hand_deposits`: each host at `Isolated_In_Quarters` emits
  its due emesis into `_emesis_deposit_unit(agent)` — the stateroom
  compartment on a Cabin_Corridor home zone, the zone itself
  elsewhere — with every draw on the dedicated spawned stream
  `_ISOLATED_DEPOSIT_STREAM_KEY`, so the new emits never reorder the
  shared stream and a voyage with no isolated host is bit-identical
  to `off`. Deposit-only: the host joins no pickup or contact draw.
- `_caregiver_service_surface_dose` resolves the read through the
  same `_emesis_deposit_unit(host)`, so a confined host's patch is
  found where the emit filed it. `off` keeps the parent-key read.

Smoke (`tools/noro_diag/isolated_quarters_smoke.py`, committed):
`fl_cls_12d_scr_gen_ship` index 0, seed 8105, 288 epochs — the verbatim
defpair cell:

- verbatim arm: 94 emesis emits across 41 `::cabinN` compartment keys;
  `service_deliveries` 1304, steward-side `service_dose_credited`
  **5103** (0 on every measured defpair cell).
- `--isolate-confined` arm (the epoch observer mirrors
  `state.quarantined_ids` into `state.isolated_ids`, holding every
  confined host under the `Isolated_In_Quarters` sentinel): 38 hosts
  isolated by voyage end, 4 of them emitters — their boluses filed at
  their own quarters' compartment keys
  (`PC_D9_P_A::cabin1069`, `PC_D4_P_A::cabin1433`,
  `PC_D8_S_F::cabin1708`; a fourth emitter's `PoolDeck` row is a
  free-era emit predating its confinement); 19 compartment patch pools
  at end of voyage; `service_deliveries` 595, steward-side
  `service_dose_credited` **8392**. A different voyage realization
  from the verbatim arm (confinement routing changes the confined
  population's evolution) — the channel fires either way.
- baseline pair: `--mode off` voyage fingerprint ≡ parent `b154e43b`
  uninstrumented fingerprint on the same spec+seed — **bit-identical**
  (compared over the full `_voyage_blocks` JSON).

**Withdrawal:** every service-side dose figure on the emetic channel
(`service_dose_credited`, `service_dose_delivered` through the patch
pickup) measured before this change is historical — the parent-key
read guaranteed a zero on compartmented hulls.

**Open:** pickup eligibility of the isolated host itself — it shares
the stateroom pool it deposits into and currently takes zero exposure
by construction (owner question, not decided here); hand-shed deposits
and sanitary flushes from the sentinel are likewise unhandled
(emesis only in this change).
