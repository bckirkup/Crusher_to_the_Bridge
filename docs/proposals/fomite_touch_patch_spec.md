> **Status:** Proposed. Nothing here is implemented or adopted; no constant is
> added, moved or re-sourced; the default `pooled` representation is unchanged
> and a run without the block must stay bit-identical to today's engine. Every
> number quoted is either a repository constant read at its definition site or
> a measurement quoted from its ledger entry with that entry's `Measured at`
> SHA — and every dose figure in the repository remains void pending the
> norovirus refit (`docs/norovirus/norovirus_open_ledger.md` §1).

# TOUCH-PATCH — item-instance touch encounters for ordinary fomite

The stage the 2026-11-22 hand/fomite mechanism review converged on. D0′
(`NORO-DOSE-LEDGER-01`) measured that within-epoch attenuation is real but not
binding; D2′ (`NORO-POOL-PICKUP-01`) measured that delivery mechanics are not
binding either — the per-touch path fills ~100% of what is asked, and what is
asked is ~0 on cold cells. What is left upstream of both is the request itself:
who touches what, and whether contact and contamination are co-located.

## 0. Settled inputs (quoted, not re-derived)

- **`NORO-DOSE-LEDGER-01`** (`docs/ledger/NORO-DOSE-LEDGER-01.md`, measured at
  `1f8a027c`, 22 cells × 288 epochs, `classic_cruise_1900`): the zone pool is
  a write-only reservoir — pooled net gain 215,527 GEC across the campaign,
  non-patch delivered mass ~0.3% of all delivered; 99.7% of delivered mass
  arrives via emesis patches through the discrete per-touch path; ~4% of
  delivered reaches a mouth; secondaries ≈ Σhazard (182/184) — once a dense
  encounter exists, the challenge converts at ~99%.
- **`NORO-POOL-PICKUP-01`** (`docs/ledger/NORO-POOL-PICKUP-01.md`, measured at
  `f9d806ac`, same 22 cells): under `contamination_solver: discrete` the
  per-touch path requests 79.85M GEC, offers 2.147B and delivers 79.66M —
  ~100% fill of requests — yet ~99.9% of delivered is still emesis-patch;
  on cold cells requests are ~0–51k and deliveries the same order as the
  continuous baseline. Verdict under its frozen rule: **the deficit is
  upstream of pickup — deposit placement or encounter structure**; no
  pool-side delivery fix will help. Arm C (`per_surface`) was declined by
  user decision: request volume is upstream of representation.
- **`patchiness_program_brief.md` §3** (`docs/proposals/`): the unresolved
  quantity is **coincidence** — whether a concentrated patch reaches
  *several* hosts through shared event, cell or partner structure; the
  saturating draws in the shipped model are almost all solitary. §6 names
  the recurring defect archetype: a well-mixed pool standing in for a small
  number of concentrated events — "fomite mass smeared over a deck
  footprint" is listed verbatim.
- **`NORO-FOMITE-DISAGG-01`** (`docs/ledger/NORO-FOMITE-DISAGG-01.md`,
  measured `622f99f`): `per_surface + areal + shipped` is an algebraic
  re-expression of `pooled` to ≤2.3e-14 relative — class-level pooling
  cannot add structure because deposits split share-wise across every
  class and requests divide by each class's full enumerated area.
- **`EmesisPatch`** (`engines/transmission_core.py`, in-tree and measured
  hot): the working template — mass carried on `high_touch_area_m2` (the
  footprint's share of the unit inventory, so the patch's density equals
  the zone-wide density at its footprint instead of being smeared) and
  exposure bounded by `occupant_share` (only the occupants the footprint
  reaches draw on it).
- **`NORO-RHYTHM-REREAD-01`** (`docs/ledger/NORO-RHYTHM-REREAD-01.md`,
  measured at `5007b3a4`): rhythm-on *reduced* acquisitions 148.0 → 113.5
  (−23.3%, sign-test p = 0.125) on the 4 take-off-gated pairs of the 8-day
  mega reconstruction. Event scheduling as an amplifier is unverified and
  pending a confirmatory A/B — this spec deliberately creates dense
  encounters **without touching the schedule**.
- **Frozen Paper-1 block**: `sanitary_visit_mode: "none"` resolves on the
  22 cells, so the shared-head venue carries zero fomite exposure in this
  campaign; nothing here re-arms it.
- **RNG caveat (from NORO-POOL-PICKUP-01)**: arm choice perturbs the RNG
  stream; per-seed arm contrasts are not paired realizations — pooled
  readouts are the unit of evidence.

## 1. What is wrong with the present structure

One line of code is the whole defect. `_fomite_pickup_request_for_area`
computes each target's request as

```text
request = contacts × used_fraction × (hand_area / surface_area) × transfer_eff × mass
```

and the ordinary zone pool calls it with `surface_area` = the unit's **entire
declared high-touch inventory** (`HIGH_TOUCH_AREA_M2[zone_class]`: cabin 1.5,
dining 8.0, public 6.0, galley 10.0, crew_mess 4.0, sanitary 0.5 per WC —
Grade C declared). With `hand_area` drawn U(445, 535) cm² ≈ 0.049 m²,
`used_fraction` U(0.008, 0.25) and `transfer_eff` lognormal(−2.1, 1.4)
(median ≈ 0.12), a dining touch reaches for

```text
0.049 / 8.0 ≈ 6.1e-3  ×  ~0.13 used_fraction  ×  ~0.12 eff  ≈ 1e-4
```

of whatever mass the pool holds. The pool holds deposits, but a touch never
meets a deposit: a deposit of mass *D* is smeared instantly and uniformly
over the full inventory, so *no touch, ever, lands on the object the
depositing hand actually touched*. Coincidence — several susceptibles
touching the same contaminated object — is structurally impossible in the
pooled arm and in `per_surface`, which spreads the same mass share-wise
across a class's whole enumerated fleet (and is measured identical to
`pooled` under `areal` shares).

The emesis patch escapes this only because a bolus deposits on a declared
footprint: same formula, small denominator, bounded exposure set. Ordinary
deposits have no equivalent structure — that is the measured cold-cell
request of ~0.

## 2. Design principle — concentrate on placement, not magnitude

Keep every rate, fraction and kernel at its shipped value and provenance.
The only change is *where a deposit lands* and *what a touch samples*: both
become item-instance events inside the unit's already-declared inventory
(`ZONE_ITEM_SETS` × `ITEM_AREA_M2`, the enumeration NORO-FOMITE-DISAGG-01
landed and NORO-TOUCH-SHARE-01 graded). This adds **no new physical
constant**: item counts, per-item areas and touch shares already exist as
declared Grade C content; the quantum floor `SURFACE_PICKUP_MIN_GEC = 1`
applies per instance instead of per pool. If a later measurement wants a
different count, share or area, that is a declared-table revision under
`model-parameter-provenance`, not part of this arm.

## 3. Mechanism

Selector: a third value of the existing representation knob,
`transmission.fomite_representation: item_instances` (alongside `pooled`
and `per_surface`; absent or `pooled` leaves every code path below
untouched and bit-identical).

### 3.1 Item instances

Under `shared` item reading (the reading NORO-TOUCH-SHARE-01's declared
table enumerates), each unit expands its `UnitInventory` into named
instances `(unit_key, item_class, index)` with `index` in `1..counts[class]`
and area `area_each_m2[class]` — under `area_basis: shipped` the same
renormalization `per_surface` applies, so a unit's total enumerated area
equals its pooled denominator and the arm changes only the *partition* of
the same declared area, never its sum. Per-occupant item groups
(`table_top_per_seat`, `chair_touched`, `small_panel`,
`tableware_per_seat`) stay out of scope exactly as in NORO-TOUCH-SHARE-01:
the engine has no zone `max_occupancy` at unit resolution and no seat/berth
binding for shared zones; owner-bound items are a declared follow-up arm
(§7), not part of this one.

### 3.2 Deposit placement

`_shedder_surface_deposits` keeps its shipped mass formula unchanged
(`contacts × presence × used_fraction × hand→surface eff × hand_load`,
capped at the hand). Under `item_instances` the deposit is then placed,
not pooled: each of the shedder's `contacts` surface touches this substep
is an iid draw — item class from the resolved `touch_share`, then a uniform
instance within the class — and the deposit is split equally across the
per-contact draws, so each touched instance receives `deposit / contacts`
on its own `area_each` footprint. A hand that touched 30 objects
contaminates ~30 objects at object density; the zone's other instances
receive nothing. Strain/composition attribution attaches to the unit
reservoir as today.

### 3.3 Pickup

`_fomite_zone_pickup` keeps its shipped request formula per touch. Under
`item_instances` each of the target's `contacts` touches samples one
reachable instance by the same rule (class by `touch_share`, uniform
instance) and requests

```text
used_fraction × hand_area / area_each(instance) × transfer_eff × mass(instance)
```

capped at the instance's mass and gated per instance by
`pickup_gate_open(instance_mass)` (the same 1-GEC quantum, moved from the
unit pool to the instance — an untouched or sub-copy instance contributes
0 and consumes no further draws). Delivery scaling is unchanged in law:
`_delivery_scale` over the substep's total requested against the unit's
total standing mass, then `_record_fomite_pickup` / hand→mouth exactly as
shipped. A susceptible whose touches all land on clean instances requests
0 — that *is* the measured structure: most touches land on clean objects,
and a contaminated shared item is touched by `touch_share / count ×
contacts × n_susceptibles` draws over its contaminated lifetime, each hit
a concentrated dose. Coincidence is generated, not asserted.

### 3.4 State and bookkeeping

Instance mass lives in a sparse map keyed `(unit_key, pathogen_id,
item_class, index)`; uncontaminated instances carry no state (a unit's
catalog is the enumeration, not stored mass). The unit-total pool
(`surface_pools_by_pathogen`) is mirrored exactly as `PerSurfaceFomiteState`
mirrors it — deposits add, delivery consumes, decay/disinfection/routine
cleaning apply the unit's uniform retention across contaminated instances —
so `zone_item_class_state`, the epoch mass ledger, and every existing
counter reconcile against the pooled aggregate within the same 1e-9
tolerances the current witness freezes. The arm draws its item-index draws
on the dedicated fomite stream (`_fomite_rng`); the baseline arm draws
nothing new, and arm-vs-baseline stream divergence on a shared seed is
disclosed per the §0 caveat — pooled, not paired, readouts.

## 4. Why this and not the alternatives already declined

- **vs `per_surface` (D2′ arm C):** measured-identical to `pooled` under
  `areal` shares; class-level mass still divides by the class's whole
  enumerated fleet. Item instances are the non-degenerate case of the same
  enumeration — the difference is a touch meeting *an object*, not a share.
- **vs magnitude levers:** the handoff's bound arithmetic — 500× pooled
  dose lifts mean take-off only to ~30% (19/22 cells stay cold); no
  delivery or deposit magnitude closes the gap. Placement is the lever the
  measurements name.
- **vs event scheduling (D3′):** unverified and sign-suspect pending the
  confirmatory A/B; this arm changes no schedule, occupancy or co-presence —
  dense encounters arise from item sharing within the existing activity
  pattern.
- **vs D1′ carrier donor eligibility:** orthogonal engine change about who
  may deposit; this arm is about where deposits land and what touches hit.

## 5. Concentration bound — why this can ignite (bound, not result)

Per-touch request on a contaminated instance vs the same mass on the zone
pool, from shipped constants:

| zone class | pooled area m² | example item | item area m² | areal lift |
|---|---|---|---|---|
| dining | 8.0 | utensil 0.005 | ~1,600× |
| public | 6.0 | door_lever 0.0016 | ~3,750× |
| cabin | 1.5 | flush_actuator 0.0010 | ~1,500× |
| galley | 10.0 | button_or_dispenser 0.005 | ~2,000× |

A touch that samples a contaminated instance requests ~`eff × instance_mass`
(the areal factor ≈ 0.049/item_area exceeds 1 and caps at the instance), i.e.
~10²–10³× the per-touch request the same mass would yield pooled. Whether
ordinary deposits concentrate *enough* mass per instance to push request →
delivered → mouth → hazard over the challenge floor on cold cells is exactly
what the campaign measures; this spec claims only that the arm creates the
dense-encounter structure the pooled representation provably lacks, using no
new physical input.

## 6. Frozen criteria (for `noro_touch_patch_01`, written before any cell runs)

Arm on the same 22 frozen `classic_cruise_1900` cells (seeds 8000–8019 +
8105/8106, 288 epochs, `norwalk_gi`), same instrumented worker and epoch mass
ledger as NORO-DOSE-LEDGER-01 / NORO-POOL-PICKUP-01, `continuous` baseline
already measured — one new arm `item_instances` per cell.

Audit invariants — a violation is an instrument defect, not a null result:

- `len(epoch_mass_ledger) == 288` on every cell; the four counter
  reconciliations within 1e-9 relative (net surface gain, delivered to
  hands, mouth channels, hazard) as in the frozen D0′/D2′ audit.
- `Σ instance_mass(unit, pathogen)` reconciles to `surface_pools_by_pathogen`
  per epoch within 1e-9 relative (mass conservation across the new partition).
- The worker stamps `fomite_representation_resolved: "item_instances"` (the
  D2′ "resolved" convention), so a dropped override is a witnessed fact.
- Baseline-identity gate: a wrapped/unwrapped run on one seed is
  bit-identical, and `pooled` mode under the new code is bit-identical to
  the pre-change tree.

Reported, never selected on, per cell:

- request, offer, delivered split by delivery path (instance vs patch) —
  the same columns the D2′ ledger reports;
- per-instance hit distribution: touches landing on contaminated
  instances, and the **coincidence count** — distinct susceptibles served
  by the same contaminated instance (the quantity patchiness_program_brief
  §3 named open);
- standing mass by instance class and its dwell time vs decay/cleaning;
- Σhazard, secondaries, take-off per cell; cell wall-clock multiplier vs
  the pooled arm.

Selection / decision rules:

- **Ignites:** take-off on previously cold cells crosses the pre-declared
  gate (to be frozen in the campaign design — e.g. ≥ a set fraction of
  cold cells with Σhazard ≥ the hot-cell floor measured in D0′) → the
  missing structure was encounter placement; promotion to default-on and
  `pooled` as labelled baseline is a *separate* change and decision.
- **Requests rise but take-off does not:** item encounters deliver mass
  but the mouth/hand-reservoir/challenge stage still strands it — the
  bound moves downstream; report the waterfall, change nothing else.
- **Requests stay ~0:** contact count × per-instance hit probability is
  itself below the ignition density — the deficit is event-level (how many
  susceptibles share one object's contaminated window), which hands the
  next question to the activity/event layer with a measured bound.

## 7. Out of scope / follow-ups this spec does not authorize

- Owner-bound and per-occupant items (seat, berth, place setting) — needs a
  unit-resolution occupancy/seat binding the engine does not yet declare;
  the strongest co-location structure and a deliberate second arm.
- Any schedule, rhythm, event-catalog or co-presence change (D3′ pending).
- Carrier donor eligibility (D1′), `sanitary_visit_mode`, food pathway.
- Any change to a shipped constant, contact rate, item table value or
  touch share; the `declared` touch-share table is unchanged.
- Campaign submission — gated on user approval of this design, then the
  usual preflight (smoke → dry-run count → pinned digest → canary).
