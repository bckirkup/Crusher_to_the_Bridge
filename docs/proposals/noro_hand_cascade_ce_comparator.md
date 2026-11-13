# Norovirus contamination CE comparator

> **Status:** Proposed. **Nothing in this document describes current behaviour.**
> It specifies a candidate continuous/event-driven comparator for the
> hand-mediated contamination loop, under a stricter constraint than the
> solver-gate proposal: **zero new fitted epidemiological constants**.

## 1. Question

The posted-conditioned DS-M pilot (`NORO-HAND-CASCADE-01-SUBSTEPS`) did not
converge through M=12 on five posted seeds: delivered/dose/deposited movement
was seed-dependent and non-monotone, while carrier surface calls grew to
~82k-242k at M=12. The open solver question is therefore no longer "which M"
but whether the contamination loop needs an event-driven reference that is not
another fixed discretization.

This document proposes the **non-minimal sparse active-carrier CE comparator**:
an event-driven solver for the same contamination state contract as DS-M and
M=1, used to test whether fixed-M is failing because of discretization or
because the pooled/touch-share representation is the binding defect.

It is a comparator, similar in spirit to CONTAM-vs-native airflow: same physical
rates, different numerical integration. It is not a new epidemiological model.

## 2. Hard constraint: parameter budget

The user's concern is decisive: the non-minimal model must not become a large
set of unmeasured parameters. Therefore:

- **No new fitted constants.** Nothing in this proposal may be chosen to move
  A4/A8/A9, VSP posting, Park surface measurements, or attack-rate anchors.
- **Reuse existing rates and kernels.** Event clocks are derived from the
  shipped per-hour/per-day rates and transfer fractions already used by the
  discrete paths.
- **No pinch-point expansion in the first CE arm.** Per-surface fomite remains
  out of scope unless existing `per_surface` machinery already carries sourced
  parameters; new areas, servings, or contact rates require a separate
  provenance-register entry before implementation.
- **Grade C is allowed only as a declared assumption**, bounded by sensitivity,
  and never as a fit input. If a mechanism cannot be expressed with existing
  constants, it is out of scope for this comparator.

Existing quantities the CE arm is expected to reuse include, but are not
limited to: `SURFACE_CONTACTS_PER_HOUR`, `CREW_SERVICE_SURFACE_CONTACTS_PER_HOUR`,
`HAND_TO_SURFACE_LOGNORMAL`, `HAND_TO_MOUTH_NORMAL`,
`HAND_TO_FOOD_TRANSFER_FRACTION_RANGE`, `FOOD_HAND_CONTACTS_PER_DAY`,
`FOOD_HANDLER_CONTACT_MULTIPLIER`, `SURFACE_PICKUP_MIN_GEC`,
`hand_hygiene_rate_per_hour`, hand inactivation rates, food growth/decay factors,
surface-pool decay, and the sanitary dwell/visit machinery.

## 3. Scope

In scope for the CE comparator:

- hand maintenance / shedding into hands;
- hand→surface deposits, including carrier-eligible deposits when
  `hand_redeposit_mode = "carriers"`;
- surface→hand pickups;
- sanitary visit deposit/pickup using the existing epoch-drawn visit schedule;
- emesis-patch pickup after epoch-once emesis deposition;
- food-pool hand deposits, pool growth/decay, and ingestion;
- hand hygiene and hand inactivation/decay;
- strain bookkeeping through the existing reservoir composition and
  `hand_strain_by_pathogen` / sparse hand-mix rule.

Out of scope, unchanged from the solver gate:

- infection challenge resolution — still once per epoch after all pathways;
- direct contact, droplet, HVAC airborne, environmental source, caregiver,
  and common-source routes;
- quarantine, NPI, susceptibility, compliance, and all behavioural/sociological
  state;
- renewal boarding defaults, pinch-point disaggregation, direct-contact donor
  sampling, and infection-serial chaining within an epoch;
- anchor fitting and default flips.

## 4. Candidate design

### 4.1 Active set

CE should be sparse: it integrates only units/pathogens with nonzero
contamination state. The active set for an epoch/pathogen is:

- agents with `hand_load_by_pathogen[pathogen] > 0` or a shedding target;
- surface pools above `SURFACE_RESIDUE_FLOOR_GEC`;
- food pools above zero;
- sanitary visit records for the epoch;
- emesis patches deposited epoch-once.

Everything else is skipped, so CE cost scales with contamination activity, not
with ship population.

### 4.2 Event types

First implementation should use the existing kernels, event-ized:

1. **Hand maintenance / shedding-to-hand** — existing `_replenish_hand`
   logic, but evaluated as continuous-time hand load relaxation plus stool /
   practice events where the profile already declares them.
2. **Hand→surface deposit** — directional atomic debit from hand and credit
   to the zone surface pool, using the existing hand-to-surface transfer and
   contact kernels.
3. **Surface→hand pickup** — directional atomic debit from surface pool and
   credit to hand, using existing surface contact rates and pickup gates.
4. **Sanitary exposure** — the epoch-drawn visit schedule is kept; each visit
   is treated as a dwell-weighted exposure event rather than repeated per
   fixed substep.
5. **Emesis-patch pickup** — patch deposits remain epoch-once; pickup is
   event-driven within the epoch after deposition.
6. **Food hand deposit** — hand→food contacts using existing food-contact
   rates and transfer fractions.
7. **Food ingestion** — food-pool consumption/dose accumulation using the
   existing ingestion accounting, but event-ordered rather than once per
   substep.
8. **Hand hygiene / inactivation** — existing hygiene probability and
   inactivation decay applied continuously over event gaps.

Transfers are directional and atomic: debit source, credit sink, carry
wet/dry/protected hand state and strain attribution. No symmetric exchange.

### 4.3 Time integration

Two acceptable first implementations, in order of preference:

1. **Scheduled-event CE:** draw next-event times per active agent/unit from
   epoch-start rates, process events in time order, decay pools continuously
   over gaps, and refresh rates for affected agents/units after each event.
   This is the comparator target.
2. **Gillespie/thinning CE:** exact event-driven sampling with upper-bound
   thinning for mass-dependent rates. More faithful but more complex; only if
   scheduled-event CE shows ordering artifacts.

Either way, `SimClock` remains the only day↔epoch converter. Event times are
in hours within the epoch; substep-style fixed "10-minute" assumptions are
forbidden.

### 4.4 RNG discipline

This is the main implementation risk. Requirements:

- paired seeds remain the floor;
- event draws must not silently consume the shared host RNG stream in an
  order-dependent way;
- prefer dedicated streams spawned from the engine RNG for CE event keys,
  analogous to the sanitary-visit stream;
- event keys should be deterministic functions of `(seed, epoch, pathogen,
  unit, agent, event_type, sequence)` so runs are reproducible;
- stream neutrality must be checked: CE off/legacy paths remain bit-identical,
  and CE on is a labelled different stochastic realization unless proven
  otherwise.

## 5. State and conservation contract

Same as the solver gate, tightened for CE:

- mass conservation: hand + surface + food + delivered + dose residual per
  voyage; no arm may create mass;
- strain lineage: sparse hand strain mix or explicitly declared unresolved
  mass; single-id `hand_strain_by_pathogen` is acceptable only if conservation
  tests bound mis-attribution;
- wet/dry/protected hand state carried across events;
- quarantine/NPI/susceptibility fixed within an epoch;
- epoch-once side effects are not repeated per event: sanitary schedule draw,
  stool venue exposure cap, isolated-quarter deposits, emesis deposition,
  surface-pool update, prev-zone occupancy, and strain census.

## 6. Witnesses and decision rule

Run on the same posted-conditioned cells/seeds as the DS-M pilot before any
engine default discussion. Predeclare:

- carrier deposit mass/calls by route;
- hand==0 rate entering food and pan deposit paths;
- hop-depth proxy;
- food/pan deposit mass and food-pool trajectory;
- delivered mass, dose, infected, symptomatic, role attack rates, VSP crossing;
- mass-conservation residual, active-set size, event count, runtime;
- RNG stream-neutrality checks.

Decision rule:

1. If CE matches M=1 within the solver-gate tolerance on posted cells, keep
   M=1 and close the solver question.
2. If CE matches DS-M only at high M, or CE materially differs from all fixed-M
   arms, use CE as the reference and decide whether the pooled/touch-share
   representation needs a separate sourced mechanism proposal.
3. If CE cannot be implemented without new unmeasured parameters, stop and
   report: that means the non-minimal path is a new model, not a comparator.

Tolerance remains the solver-gate proposal's: deposited/delivered mass and
dose within 10% relative error and same sign of posted-conditioned effect;
infection-count movement is reported, not gated.

### 6.1 Alternative hypothesis: contact/behavioural constants are binding

CE cannot repair a shortage of contacts. If CE agrees with M=1, or all fixed-M
arms converge to the same deposited/delivered/dose, the solver is not the
binding constraint; the next suspect is the upstream constants that decide who
contacts what, when, and how much: surface/contact rates, sanitary visit
frequency/dwell, food-handler versus diner contacts, hand hygiene/inactivation,
occupancy/duty schedules, and quarantine/compliance timing. Those constants are
not all "sociological", but they are the ABM's contact/behaviour layer.

Before proposing any change there, measure which are binding: active-set size
and event counts, hand occupancy versus Liu, carrier mass entering food/pan,
sanitary visits/dwell realised, food-handler versus diner contact split,
quarantine epoch timing, and per-route delivered mass. Classify each as
measured, inferred, or Grade C. Any revision still needs independent evidence or
a declared sensitivity range; VSP/attack-rate fitting remains forbidden.

## 7. Implementation path

1. **This proposal** — freeze scope and parameter budget.
2. **Engine arm** — `transmission.contamination_solver: "event"` default off,
   with legacy/`discrete` bit-identical; scoped to pooled fomite + food +
   sanitary, no per-surface expansion.
3. **Unit guards** — M=1 equivalence is not required for CE; instead require
   conservation, event-count sanity, and off-path bit-identity.
4. **Witness harness** — add CE arm to `tools/noro_diag/hand_cascade_witness.py`
   and run the posted seeds already used for DS-M.
5. **Decision ledger** — record CE vs M=1/DS-M before any default or anchor work.

## 8. Non-goals

- No anchor fitting and no default flip in the CE comparator PR.
- No new epidemiological constants without provenance; no silent Grade C
  expansion.
- No pinch-point disaggregation in the first CE arm.
- No direct-contact carrier donor sampling or infection-serial chaining.
- No behavioural/sociological layer changes; quarantine, compliance, NPI, and
  susceptibility remain outside the contamination solver.
- This proposal does not diagnose or repair behavioural/contact constants; it
  only determines whether the solver is binding.
- No campaign submission; local paired-seed witnesses first.
