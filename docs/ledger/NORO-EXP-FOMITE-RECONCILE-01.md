# NORO-EXP-FOMITE-RECONCILE-01
**Date:** 2026-09-19
**Commit:** d5f3130
**Pathogens:** norwalk_gi
**Status:** open

`NORO-EMESIS-CANARY-01` left `expedition_cruise_450` with two unexplained
witnesses at main `204ba42`, and declared this entry to explain them. On
expedition seed 8001 the fomite witness recorded 25.943 GEC deposited to
surfaces across six deposit calls while the summed surface mass *offered* at
pickup over 123 delivery calls was 3.278e-28 GEC, with the voyage's whole
credited dose 2.133e-32 GEC and summed evaluated hazard 3.614e-36. On
expedition seed 8106 the same shape appears one hundred and eighty orders of
magnitude lower: 5.952e-218 GEC deposited, 9.016e-217 GEC offered, against a
`max_hand_target_gec` of 13.323 — an ordinary target with an underflow load.
Separately, all four measured expedition seeds recorded `phase_eligible = 0`
with every one of 75,600 emit calls phase-blocked, so emesis was structurally
unexercised on that hull.

The canary could not attribute either signature: it measured one seed per
condition and its witness set was built for the classic hull. This entry is
the attribution, and it changes no constant, profile, or engine path.

## Question

1. **Conservation.** Does the expedition fomite chain conserve surface mass —
   does everything deposited leave the pool through a witnessed term
   (delivered to hands, decayed, cleaned) or remain as residual — or is mass
   disappearing between deposit and offer?
2. **Eligibility.** Why does no expedition host ever reach an emesis-eligible
   clinical phase?

## Instrument

A new read-only diagnostic, `tools/noro_diag/fomite_mass_balance.py`.
`tools/noro_diag/per_host_dose_challenge.py` is *not* modified: its exact
classic replay is the control that `NORO-EMESIS-CANARY-01` validated, and a
change to it would void that check.

The new instrument wraps bound methods on `TransmissionCore` for the duration
of one run and only reads:

* `_deposit_surface_mass` — per epoch, per zone, per *call site* (the calling
  frame's function name), mass deposited.
* `_deliver_fomite_requests` — per epoch, per zone, surface mass offered, mass
  requested, mass delivered. This is the term the canary measured.
* `_record_fomite_pickup` — every delivery on *every* fomite path, including
  the sanitary-venue path in `_sanitary_fomite_exposure`, which does not route
  through `_deliver_fomite_requests` at all.
* `_scale_surface_mass` — every multiplicative removal, per zone, tagged by
  call site, so per-epoch survival decay, `_consume_surface_mass`, and routine
  or SOP surface cleaning are separated rather than summed.
* `_replenish_hand` — per host hand target and hand load.
* `_emesis_phase` and the clinical phase of every host infected with
  `norwalk_gi`, per epoch, so "no host is ever eligible" is measured against
  the phase histogram rather than inferred from a zero counter.

No wrapper draws from the engine's generator and none writes engine state, so
an arm of this instrument differs from a shipped run only by the observations
taken. No `dose_response.alpha` or `.beta` override is written on any arm:
`RNG-FRAILTY-STREAM-01` makes such an arm unpairable at fixed seed.

## Cells, frozen before any cell runs

| Hull | Seeds | Agents | Epochs | Role |
| --- | --- | --- | --- | --- |
| `expedition_cruise_450` | 8001 | 450 | 168 | the seed with ordinary deposits and underflow offers |
| `expedition_cruise_450` | 8106 | 450 | 168 | the seed with underflow deposits, pair seed |
| `classic_cruise_1900` | 8105 | 1,910 | 288 | control: the settled reference voyage |

Shipped default `active_profiles` bundle, declared complements, no override.
Output is written to a hull-specific directory, because the canary established
that this family of instruments names dumps by seed alone and two hulls sharing
one directory overwrite each other.

## Criteria, declared before any cell runs

**Conservation.** For each pathogen and zone, the instrument must close

```text
deposited + initial  ==  delivered + removed_by_decay + removed_by_consume
                         + removed_by_cleaning + residual
```

to 1e-9 relative on the voyage total, and per zone to 1e-6 relative. The
readout is **CONSERVED** if every zone closes and **LEAK** if any zone's
removals and residual do not account for its deposits. A leak is a defect in
the engine's surface bookkeeping and outranks everything else in this entry.

**Attribution.** Conditional on CONSERVED, exactly one of these is accepted,
and the discriminating quantity is declared here rather than chosen after the
dump is read:

* **H1, witness coverage.** The canary's `surface_mass_offered_gec` counts
  only `_deliver_fomite_requests`. Accepted if at least 90% of deposited mass
  lands in zone keys that are never passed to `_deliver_fomite_requests`, and
  the deliveries recorded at `_record_fomite_pickup` account for that mass.
  Under H1 the canary's "deposit versus offer" gap is an artefact of what the
  witness covered, not a conservation failure, and the expedition hull is not
  defective on this axis.
* **H2, removal.** Accepted if cumulative decay plus cleaning removal is at
  least 90% of deposited mass and the end-of-voyage residual is below 1% of
  it. Under H2 the mass is really gone before any host can pick it up, and the
  next question is whether the removal rate is the declared one
  (`CLEAN-OUTBREAK-01` is the archetype).
* **H3, neither.** Deposits are offered and delivered, and the underflow is
  upstream in the hand load. Under H3 the discriminating quantity is the hand
  load trace of the depositing host.

**Eligibility.** The per-epoch phase histogram must be reported for both
hulls. Import scarcity is accepted as the explanation if the expedition
voyages carry at most one imported `norwalk_gi` case and the classic control's
eligible-hosts-per-import rate implies fewer than one eligible host per
expedition voyage. It is a **defect** if any expedition host is recorded in a
symptomatic phase while `_emesis_phase` never returns an eligible phase for
it.

**Void.** A cell whose deposit call count is zero measures nothing about
conservation and is void for the conservation criterion, reported as such.

## Not being done here

No constant, profile, pathogen bundle, platform file, or engine path is
changed. Nothing is fitted or selected on: the seeds are the ones
`NORO-EMESIS-CANARY-01` already measured, named here before this entry's cells
run, and no quantity in the readout chooses a parameter value. α and β are not
reopened; `NORO-SUSCEPT-02`'s chain, `NORO-SUSCEPT-03`'s bound, and
`NORO-DOSE-01`'s cascade are settled inputs. Whether the expedition hull can
ever carry an emesis measurement is a design question for a later entry, not
this one.
