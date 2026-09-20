# NORO-EXP-FOMITE-RECONCILE-01
**Date:** 2026-09-19
**Commit:** d5f3130
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** c004a15

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
* `_hand_carriage_propensity`, `_stationary_hand_load` and
  `_stool_event_occurs` — the hand reservoir's own initialisation: the per-host
  beta carriage propensity, the load a host first seen mid-illness starts at,
  and whether a defecation event ever refills it. These three were added after
  the classic control cell had already run, because the first expedition cell
  showed an ordinary hand *target* against an underflow *load* and the term had
  to be named; the two expedition cells were then re-run with the full witness
  set, and the classic dump carries the hand target/load witness but not these
  three fields.
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

## Measured

Three cells, `tools/noro_diag/fomite_mass_balance.py`, dumps committed under
`docs/norovirus/noro_exp_fomite_reconcile_01/`.

**Conservation: CONSERVED in all three cells.** The surface-mass book closes to
3.4e-16 relative on the voyage total and 7.9e-16 on the worst zone, against a
declared tolerance of 1e-9 and 1e-6. There is no leak, and the canary's
"25.943 deposited versus 3.278e-28 offered" is therefore not a conservation
failure. Every gram deposited is accounted for by a witnessed removal or by
the end-of-voyage residual:

| Term | classic 8105 | expedition 8001 | expedition 8106 |
| --- | --- | --- | --- |
| deposited (GEC) | 220.318 | 25.943 | 5.952e-218 |
| `_disinfect_zone` | 111.391 (50.6%) | 17.626 (67.9%) | 3.366e-219 (5.7%) |
| `_update_surface_pools` decay | 52.406 (23.8%) | 7.522 (29.0%) | 2.493e-218 (41.9%) |
| `_consume_surface_mass` (picked up) | 30.419 (13.8%) | 5.145e-30 (2e-31) | 1.618e-218 (27.2%) |
| `_routine_cleaning_event` | 26.055 (11.8%) | 3.588e-4 (0.001%) | 1.471e-218 (24.7%) |
| residual at disembarkation | 0.047 (0.02%) | 0.794 (3.1%) | 3.212e-220 (0.5%) |
| balance error, relative | 3.4e-16 | 1.5e-16 | 1.8e-16 |

**Attribution, seed 8001: the deposit reached a zone that was never offered to
anyone, and disinfection took it.** All 25.943 GEC of the voyage's deposits
landed in a single zone, `CC_D2_A::cabin380`, which `_deliver_fomite_requests`
was never called on — zero offers in 168 epochs — because the cabin's only
occupant was the shedding host itself and a pickup needs a susceptible
occupant. The declared H1 clause on coverage is met at its limit (100% of
deposited mass in never-offered zones, criterion 90%), but H1's second clause
fails: those grams were not delivered anywhere else either. H2's first clause
is met (disinfection plus decay remove 96.9%, criterion 90%) and its second
fails narrowly (3.1% residual against a 1% criterion). The honest reading is
that neither hypothesis as declared is the whole answer and the measurement is
compound: **deposit into a single-occupant confined cabin, no susceptible ever
offered it, removal dominated by SOP disinfection (67.9%) and surface decay
(29.0%)**. This is reported as measured rather than folded into whichever
hypothesis it came closest to.

**Attribution, seed 8106: H3, the underflow is upstream in the hand load.**
Here the pool *was* offered (74 delivery calls on the depositing zone) and
delivered, so nothing is lost between deposit and offer; the whole chain simply
runs at 1e-218. The instrument caught the term: `_stationary_hand_load`
returned an initial hand load of 1.622e-217 GEC for a host whose hand *target*
was 13.323 GEC, from an inactivation rate of 1.0025 per hour against a
defecation rate of 0.01094 events per day. The initialisation is the backward
recurrence time of the event process decayed at the hand inactivation rate, and
with a ~1 h e-folding time against a ~91-day expected recurrence the exponent
underflows. No stool event fired in 323 draws over the voyage, so the load was
never refilled: 156 of 156 target-positive calls underflowed.

Seed 8001 shows the same mechanism with an unremarkable draw. Its host's
carriage propensity was 0.248 (the voyage drew 0.0005, 0.0048, 0.072, 0.098,
0.248, 0.265), its initial load 6.103e-28 GEC against a 12.971 GEC target, from
a 1.116 per hour inactivation rate and a 2.4-day backward recurrence. Three
stool events fired in 968 draws, and the hand sat at its target in exactly 2 of
168 target-positive calls. **Hand load is a spike-and-crash process: at the
ceiling in the epoch of a defecation event and ~27 log10 below it a day later.**
The classic control has the same shape — 867 of 960 target-positive calls
underflowed, 9 at target, max load 139,244.870 GEC — so this is a hand-model
property, not an expedition defect. What differs is that 1,910 agents supply a
host whose spikes land in shared zones, and 450 agents with one import do not.

**Eligibility: import scarcity, not a defect.** Both expedition voyages carried
exactly one `norwalk_gi` host, and that host was never symptomatic: all 168
`_emesis_phase` calls on it returned at the `infected_but_no_symptomatic_phase`
condition, so no call ever reached the `vomiting`-feature test. The classic
control reached `eligible` 24 times, from 1 symptomatic host of 5 infected,
phase `acute`. At the control's 1 symptomatic host per 5 infected, an
expedition voyage with ≤1 import expects ≤0.2 symptomatic hosts, so
`phase_eligible = 0` is the ordinary outcome of hull size. No expedition host
was recorded symptomatic while `_emesis_phase` refused it, which was the
declared defect condition.

**Incidental measurement, not in the declared criteria.** On the classic
control, mass delivered to hands (33.029 GEC over 1,917 delivery calls) exceeds
the mass debited from the pools for those deliveries (30.419 GEC) by 2.610 GEC,
7.9% of delivered and 1.2% of deposit. `_consume_surface_mass` debits the pool
by the *ratio* `(previous - delivered) / previous` applied to the pool's
current mass, so a pool that changed between the read and the debit loses a
different absolute amount than the hands gained. Both expedition cells match
exactly (ratio and absolute coincide when one delivery empties one zone), so
this is a classic-hull-visible, sub-decade effect. It does not change any
conclusion here and it is not attributed; it is filed below.

## Conclusion

The expedition fomite chain is **not broken**. Its books conserve to machine
precision, and both canary signatures are explained by measured terms:

1. The deposit/offer gap is a *dead-end zone* plus *disinfection*, not a lost
   mass — the single infected host deposits into its own confined cabin, which
   has no susceptible occupant to offer it to, and SOP disinfection removes two
   thirds of it.
2. The 1e-218 magnitudes are the hand reservoir's stationary initialisation
   underflowing when the hand inactivation rate (~1 per hour) is three to four
   orders above the defecation rate (~0.01–0.25 per day). The same underflow is
   present on the classic hull and is invisible there only because some host
   eventually spikes.
3. `phase_eligible = 0` is hull size: one import per voyage and a control
   symptomatic rate of 1 in 5.

`NORO-EMESIS-CANARY-01`'s prospective withdrawal of the expedition emesis and
fomite readings can be lifted: those numbers are correct readings of a hull
that structurally cannot carry the measurement, and the NO-GO on the two-hull
emesis design stands for that reason rather than for a suspected defect.

## Recommendation

Run `NORO-EMESIS-SIZE-01` on `classic_cruise_1900` only, 20 paired seeds, α and
β untouched. Expedition is not a defective arm to repair; it is a hull with too
few imports to size a rare host-level mechanism, and adding it to a sizing
campaign buys void cells at 4 min each.

Two entries are filed, neither started:

* `NORO-HAND-STATIONARY-01` — whether the spike-and-crash hand reservoir is the
  intended reading of Liu 2013, given that the stationary initialisation
  underflows to denormal values and that the hand is at its measured ceiling in
  ~1% of shedding epochs. This is a provenance question before it is a code
  question, and it is upstream of every fomite dose in the model.
* `NORO-SURFACE-CONSUME-01` — the 7.9% ratio-versus-absolute mismatch between
  mass delivered to hands and mass debited from the pool in
  `_consume_surface_mass`.

Still inherited and unstarted from `NORO-DOSE-01`:
`NORO-CARRIER-REDEPOSIT-01` and `NORO-TRANSFER-PRODUCT-01`.
