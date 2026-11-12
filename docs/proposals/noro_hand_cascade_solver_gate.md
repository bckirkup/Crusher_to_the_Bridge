# Norovirus hand-cascade solver gate

> **Status:** Proposed. **Nothing in this document describes current behaviour.**
> It is the decision record for choosing the intra-epoch integrator for the
> hand-redeposition mechanism landed as default-off arms in
> `NORO-HAND-CASCADE-01` (`transmission.hand_redeposit_mode`,
> `transmission.intra_epoch_causal_order`).

## 1. Question

Carrier redeposition and causal ordering are no longer hypotheses: the
posted-conditioned witness moved already-posted voyages upward on paired seeds.
The remaining choice is numerical, not mechanistic:

- **DS-M** — fixed `M` discrete substeps inside each 1-hour epoch for the
  hand-mediated contamination loop only;
- **CE** — a continuous/event-driven integrator for the same loop, used either
  as the reference or as the shipped solver if no fixed `M` converges;
- **M=1** — the current ordered/carrier arm, kept as the baseline.

If DS-M wins, `M` is chosen by convergence, not by anchor fit.

## 2. Evidence already in hand

Measured in the posted-conditioned witness (`fl_exp_12d_sens_p06_paxv`,
`expedition_cruise_450`, `norwalk_gi`, 288 epochs, seeds 8073 and 8038):

- `carriers_ordered` exceeded `legacy` on infected, symptomatic, dose,
  delivered mass, and deposited mass on **both** seeds.
- `ordered` alone was positive on both seeds; `carriers` alone was mixed on
  infected count but large on mass/deposited witnesses.
- The earlier small-seed null was a target miss, not a mechanism null.

Inferred: the mechanism belongs in the model. Hypothesis: the missing large,
fast, quarantine-damped events require within-epoch propagation, so the open
problem is whether fixed substeps are enough or whether the contamination loop
needs event ordering.

## 3. Code facts that constrain the design

- One epoch is one hour (`SimClock.DEFAULT_EPOCH_DURATION_HOURS = 1.0`); day
  rates are converted only through `SimClock`.
- Infection challenge is resolved **once per epoch after all pathways**. A host
  infected by this epoch's dose cannot shed again until the next epoch.
- Ordered fomite (`intra_epoch_causal_order=ordered`) already runs sanitary/
  emesis pickup before surface redeposition and defers hand hygiene until after
  food deposits when food contamination is enabled.
- Food contamination runs after fomite, deposits from hands, grows/decays the
  food pool, ingests, and then flushes deferred fomite hygiene.
- `hand_load_by_pathogen` is scalar mass; `hand_strain_by_pathogen` carries one
  dominant lineage for the carrier arm. Surface and food reservoirs already
  have composition bookkeeping.
- Pickup delivery is simultaneous rationing (`_delivery_scale`), not sequential
  depletion. That is a modelling choice that a continuous integrator may need
  to revisit, but it is not itself a solver defect.
- Sanitary visit draws, emesis deposition, prev-zone occupancy, surface-pool
  update, and strain census are epoch-once side effects. A substep loop must
  not repeat them blindly.

## 4. Candidate integrators

### 4.1 Baseline: ordered/carriers at M=1

Already landed. It repairs causal order and the carrier dead-end but still
quantizes contamination to one deposit-then-pickup pass per epoch.

### 4.2 DS-M: fixed-M contamination substeps

Per epoch, repeat only the contamination sub-cycle `M` times:

1. hand maintenance for occupants of contaminated units;
2. sanitary/emesis/fomite surface deposits;
3. surface/sanitary/emesis pickups (dose accumulated, not resolved);
4. food deposits, pool growth/decay, ingestion (dose accumulated);
5. hand hygiene for the substep.

Direct contact, droplet, HVAC airborne, environmental source, caregiver, and
epoch-once bookkeeping stay outside the loop. Infection challenge still runs
once at epoch end on the accumulated dose.

Stochastic rule, frozen before implementation: every per-hour rate/contact
rate is divided by `M`; count-like draws use the substep probability
`1 - exp(-rate/M)` rather than `Poisson(rate)/M` rounding, so `M=1` is
bit-identical to the ordered arm and larger `M` is a refinement, not a new
process. This must be verified by an `M=1` equivalence guard.

### 4.3 CE: continuous/event-driven reference

For each occupied unit, draw touch/contact/hygiene/inactivation events in
continuous time within the epoch. Transfers are directional and atomic:
hand→surface, surface→hand, hand→hand, hand→food, food→mouth. Pools decay
continuously. Dose accumulates and infection still resolves once per epoch.

CE is the numerical reference for convergence and the fallback if DS-M shows
ordering artifacts. It is not proposed as the first implementation because it
needs event-key/RNG discipline that the current paired-seed harness does not yet
provide.

## 5. State contract for any M>1 or CE arm

- Mass conservation: hand + surface + food + delivered + dose residual is
  measured per voyage; no arm may create mass.
- Strain lineage: either a sparse hand strain mix or an explicitly declared
  unresolved-mass rule; single-id `hand_strain_by_pathogen` is acceptable only
  if conservation tests bound the mis-attribution.
- Wet/dry/protected hand state is carried across substeps/events.
- RNG: paired seeds remain the floor; substep/event keys must not silently
  break stream neutrality. `carriers` already changes RNG consumption versus
  `shedders_only`, so carrier arms need stream-neutrality checks, not just
  paired seeds.
- Quarantine/NPI/susceptibility are fixed within an epoch; substeps do not
  re-draw host state.
- `SimClock` remains the only day↔epoch converter; substep duration is
  `clock.hours_per_epoch / M`, never a hard-coded "10 minutes".

## 6. Witnesses and decision rule

Run on posted-conditioned cells selected from SENSITIVITY-01 scan rows, across
hulls, with paired seeds and enough replicates for rare-event uncertainty.
Predeclare before running:

- carrier deposit mass/calls by route (surface, sanitary, food);
- hand==0 rate entering `_food_deposits` and `_cs_pan_deposit`;
- hop-depth proxy: carrier→surface→third-party hand→surface→hand;
- food/pan deposit mass and food-pool trajectory;
- delivered mass, dose, infected, symptomatic, role attack rates, VSP crossing;
- mass-conservation residual and runtime.

Convergence test: DS-M vs CE and DS-M vs DS-2M on the same seeds. Proposed
tolerance: deposited/delivered mass and dose within 10% relative error and the
same sign of the posted-conditioned effect; infection-count movement may be
stochastic and is reported, not gated, at this stage.

Decision rule:

1. If DS-M converges to CE by `M ≤ 12` and passes conservation/RNG guards,
   implement DS-M* as a default-off arm, measure anchors, then decide default.
2. If no `M ≤ 60` converges, or convergence requires an M whose runtime is
   campaign-prohibitive, implement CE for the contamination loop only.
3. If ordered/carriers at M=1 already matches CE within tolerance on posted
   cells, keep M=1 and close the solver question.

No `M` is chosen because it improves A4/A8/A9.

## 7. Implementation path

Minimal path first: extract the ordered fomite+food contamination sequence
into a substep-callable unit with epoch-once side effects guarded, add
`transmission.intra_epoch_substeps` defaulting to 1, and extend
`tools/noro_diag/hand_cascade_witness.py` to sweep M. Only if that extraction
proves invasive should a reduced-order solver gate be built first.

Spec-faithful path, if needed: sparse active-carrier event integration over
contaminated hands/surfaces/food, reusing existing surface/touch-share
machinery before adding pinch-point slots.

## 8. Non-goals

- No anchor fitting and no default flip in the solver PR.
- No renewal boarding change; that remains its own PR.
- No pinch-point disaggregation, direct-contact carrier donor sampling, or
  infection-serial chaining within an epoch.
- No claim that a fixed `M=6` is correct by inspection; `M=6` is only one
  candidate in the sweep.
