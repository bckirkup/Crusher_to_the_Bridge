> **Status:** Proposed — nothing here is implemented, adopted or authorized to
> run. No constant is changed by this document. It exists so that the choice
> between bounding `HIGH_TOUCH_AREA_M2` and retiring it is made against a
> specification and a price, rather than against a sketch. Measurements quoted
> are attributed to their source file; every dose figure in the repository
> remains withdrawn pending the norovirus refit
> (`docs/norovirus/norovirus_open_ledger.md`).

# Disaggregating the fomite surface pool

## 1. What `HIGH_TOUCH_AREA_M2` actually is

The engine keeps one surface pool per unit and spreads deposited mass uniformly
over a scalar area. `_fomite_surface_area` (`engines/transmission_core.py:5310`)
returns `HIGH_TOUCH_AREA_M2[zone_class]` (`:236-247`; cabin 1.5, dining 8.0,
public 6.0, galley 10.0, crew_mess 4.0, sanitary 0.5 per water closet) times the
configured scale. Pickup divides by it (`:5441-5465`).

That scalar is **not a property of the ship**. It is the quantity the pooled
representation requires in order to convert mass into a concentration. In the
world there is no summed high-touch area of a dining room: there is a set of
objects, each with its own area, its own share of the touches, and its own
contamination history. The sum only becomes a number once the decision to keep
one compartment per zone has already been made.

This is the explanation for the repository's own null. Two literature tranches
(`consensus_tranche_45_high_touch_area.md`, `consensus_tranche_46_touch_behaviour.md`)
registered `∅nr` on summed room-level high-touch area, while recording that the
*inputs* are measured: item counts (Carling 2009, 30.6 evaluated objects per
shipboard public restroom; Lei 2017, 3.3 touchable surfaces per aircraft seat),
per-item areas (Park 2015 toilet seat), and total room surface (Manuja 2019,
Hodgson 2005). Nobody has published the sum because, outside this model, the
sum is not a thing anyone needs. It cannot be closed by more retrieval.

It follows that `HIGH_TOUCH_AREA_M2` is a **lumping parameter wearing structural
units**, and that its six entries look settled only because square metres look
like geometry. It is not ship structure, which is declared sharply and
measurable; it is behavioural — who touches what, how many of them there are,
over what occupancy cycle — and behavioural quantities in this repository are
bounded, shaped and swept, not declared as points.

## 2. What the pooled representation erases

**Surface identity is not tracked anywhere.** A "contact" in this engine is not
a touch on an object; `_fomite_surface_contacts` (`:5361`) returns
`SURFACE_CONTACTS_PER_HOUR[zone_class] * hours_per_epoch` as an *expected
count*, which then enters pickup and deposition as a multiplicative term:

```
request = contacts * (used_fraction * hand_area / surface_area_m2)
          * transfer_efficiency * surface_mass        # :5441-5465
deposit = min(hand, contacts * used_fraction * transfer_efficiency * hand)  # :6922-6934
```

There is no list of touched objects, no which-surface, and no touch degree. The
only sub-zone structure that exists is `EmesisPatch` (`:1701-1715`: `mass`,
`high_touch_area_m2`, `occupant_share`, `epoch`) and the per-stateroom cabin
compartments that `_cabin_compartments` (`:6906`) fans out of `Cabin_Corridor`
zones. Both are precedents for finer state; neither is per-surface.

Three consequences follow, in increasing order of importance.

### 2.1 A cleaning policy cannot be expressed

Cleaning is applied to the pool as a scalar coverage and a log reduction:
`ROUTINE_CLEANING_COVERAGE = 0.37` (Carling 2009, Grade A) and
`ROUTINE_CLEANING_LOG10_REDUCTION = 1.29` (Grade B) at `:249-311`, applied by
`_routine_cleaning_event` (`:2526`) as `multiplier = 10**-log10_reduction` over
the cleanable sub-pool; outbreak response uses coverage 0.58 at 24 events/day
whose "per-surface revisit rate is NOT sourced… declared assumption". Config
(`_parse_surface_cleaning_cfg`, `:1562-1695`) resolves coverage and reduction
per zone class. Nothing finer than a unit key can be addressed.

So "wipe the elevator buttons and the handrails twice a shift" and "clean 15%
more everywhere" are the *same input*. A pooled model can answer whether to
clean more. It is structurally incapable of answering **what to clean**, which
is the operational question during an outbreak, and the one an intervention
study would actually be commissioned to answer. The fluorescent-marker audits
that produced `ROUTINE_CLEANING_COVERAGE` in the first place measure per-object
hit-or-miss coverage; the engine consumes their mean and discards their object
structure.

### 2.2 It is the missing coincidence mechanism

`docs/proposals/patchiness_program_brief.md` §3 states the unresolved quantity
for the whole norovirus thread: not marginal dose variance, which is already
extreme, but **coincidence** — whether a concentrated patch reaches *several*
hosts through shared event, cell or partner structure. It records that the
measured cell statistics say it currently does not, because the saturating draws
are almost all solitary, and that the within-zone exposure multiplier is redrawn
at exposure, "so it is not a spatial hotspot". §6 names the recurring archetype:
"a well-mixed pool standing in for a small number of concentrated events",
listing "fomite mass smeared over a deck footprint" explicitly.

A shared surface is exactly a coincidence structure: a persistent object that
one host contaminates and several later hosts draw from. Per-surface state is
the smallest change that supplies it, and it supplies it without declaring a new
variance law — the concentration comes from the touch-degree distribution, which
is measured, not from a heavy tail nobody has fitted (a fit the brief's §4
explicitly refuses).

The same brief records that fomite's delivered-vs-flat establishment ratio is
0.762 — partly linear, unlike food and HVAC at ≈1.000 or direct contact's
saturated 0.034. A hotspot introduced here is therefore neither inert nor
wasted, which is not true of most places one could add structure.

### 2.3 One unsourced number moves a scored observation channel

`transmission_core.py:438-442` states that the scale is "multiplied onto
`_fomite_surface_area`'s single choke point so the pickup denominator, the emesis
`touchable_fraction`, the EmesisPatch area and the surface-swab density
denominator all move together" — confirmed at `:5837-5840`, `:5887-5891` and
`zone_high_touch_area_cm2` (`:3438-3444`). So the unsourced scalar also sets
simulated swab positivity, an observation channel the model is scored against.
Bounding it leaves that coupling in place; deriving it from per-item state
replaces it with a quantity that has a referent.

## 3. The design

### 3.1 Item classes, not physical objects

The single decision that makes this affordable: track **item classes**, not
individual objects. A zone's shared inventory is represented as a handful of
classes (door lever, flush actuator, tap set, button/dispenser, grab rail,
table plane, chair, work plane, utensil, toilet seat), each with a count, a
per-item area and a share of the zone's touches. Within a class, objects are
pooled; across classes, the touch distribution's heavy tail is preserved. That
keeps the degree structure that matters — two of thirteen hotel-lobby fomites
carrying 54% of touches (Ackerley 2025), a degree-14 water-dispenser button
among 1,490 coded surfaces (Zhang 2018) — without carrying 1,490 objects.

The class sets and per-item areas **already exist in-tree** as
`ZONE_ITEM_SETS` and `ITEM_AREA_M2` in
`tools/noro_diag/high_touch_area_envelope.py`, enumerated under the operational
definition fixed by ledger `NORO-HIGH-TOUCH-DEFINITION-01` (merged, Status:
open). They are currently diagnostic inputs only. This design promotes them to
engine state; it does not invent them.

### 3.2 State

Per `(unit_key, pathogen_id, item_class)`:

| field | meaning | source of the input |
|---|---|---|
| `count` | items of the class in the unit | Carling 2009, Lei 2017, occupancy-coupled for seats |
| `area_m2_each` | touched extent of one item | `ITEM_AREA_M2` (Grade C declared, Park 2015 for the seat) |
| `touch_share` | share of the unit's contacts landing on the class | Jin 2022 T/R classes, Zhang 2018/2021, Ackerley 2025 |
| `mass` | deposited mass on the class | engine state |
| `cleanable_mass` | the reachable share, as the pool already tracks | existing `surface_pools_cleanable_by_pathogen` |
| `last_cleaned_epoch` | for revisit-interval policies | engine state |

`unit_key` keeps its present meaning — zone name or cabin compartment
(`CABIN_COMPARTMENT_SEPARATOR`, `:920`) — so the cabin fan-out is inherited
rather than redesigned.

### 3.3 Deposition and pickup

Deposition allocates a shedder's hand transfer across classes **in proportion to
`touch_share`**, not to area: contamination follows hands, which is the whole
point of the ethidium-bromide elevator button. Pickup draws a susceptible's
expected contacts across classes by the same weights, and reads each class's own
density `mass / (count * area_m2_each)`. The existing cap
(`min(surface_mass, request)`) and the aggregate over-demand scaling
(`_deliver_fomite_requests`) apply per class.

`HIGH_TOUCH_AREA_M2` then stops being read by pickup. The zone's high-touch area
becomes a **derived roll-up**, `sum(count * area_m2_each)`, reported as a
diagnostic and used where a single areal denominator is still genuinely needed
(the swab density and the emesis touchable fraction, §2.3), so those channels
inherit a derived quantity instead of a declared one.

### 3.4 The neutrality identity, which is the gate

With `touch_share` set proportional to each class's area share, and no
per-class cleaning or deletion, the per-surface model must reduce **exactly** to
the pooled model at the same total area. Uniform density over classes whose
weights are areal is algebraically the pooled case. That identity is the
acceptance test: if the arm does not reproduce the pooled arm to floating-point
tolerance at paired seeds under uniform weights, the implementation is wrong
rather than the model being different. Every subsequent result is then
attributable to the degree distribution, not to the refactor.

Selected by `transmission.fomite_representation: pooled | per_surface`, with
`pooled` as the labelled default, following the repository's convention of
keeping a labelled pre-change baseline for paired attribution
(`cabin_air_mode`, `pathogen_pool_transport`, `contact_mode`).

### 3.5 Cleaning becomes addressable

A cleaning policy becomes a set of targeted classes with a per-class coverage
and revisit interval, so `ROUTINE_CLEANING_COVERAGE` is recovered as the
touch-weighted average of per-class coverages rather than replaced. The existing
config block gains an optional `by_item_class` alongside `by_zone_class`, and
"target the high-degree classes" becomes a policy the model can be asked about.
No new cleaning constant is adopted by this document; the declared outbreak
revisit rate stays declared and stays flagged.

## 4. Cost

Zone counts, from `data/platforms/<hull>/spatial_layout.json`:

| hull | zones | of which Cabin_Corridor |
|---|---:|---:|
| expedition_cruise_450 | 47 | 16 |
| classic_cruise_1900 | 79 | 42 |
| spirit_cruise_3000 | 115 | 57 |
| mega_cruise_5000 | 192 | 93 |

Cabin corridors fan into per-berth compartments at runtime, so effective pool
keys exceed the zone count — on `mega_cruise_5000`, order 2,500 keys once
staterooms are counted. At ~10 item classes per key and one pathogen, that is
order 10^4–10^5 floats: memory is not the constraint.

Runtime is. The fomite section is O(units × agents) today
(`_pathway_fomite` `:6877`, loops at `:6908-6943` and `:6945-6978`), and
per-class pickup multiplies the inner term by the number of classes a
susceptible's contacts are spread over. Bounded by design at ~10, with decay
(`_update_surface_pools` `:7532`) also scaling by the same factor. The honest
envelope is **up to ~10× the fomite section**, which is one of five routes, so
plausibly 2–4× a whole voyage before optimisation, and closer to 1.5× if
per-class pickup is vectorised or the class count per draw is capped.

Against the measured baseline — `docs/norovirus/admissible_region_37.md:28`,
640 simulations at 168 epochs and 450 agents in 3 h 40 min on two workers,
≈21 s/voyage — a Sobol feasibility cell that currently costs 3–4 h would cost
roughly 8–15 h at the same size, or the same wall clock on 2–4× the workers.
That is a real but affordable price, and it is the number the decision should be
made against.

## 5. The 2020 no-touch door retrofit as a validation case

This is the sharpest available test of a per-surface representation — removing
door levers is a **surface-class deletion**, which the pooled model cannot
express at all (it can only scale everything) — and the in-tree evidence is
weaker than it first appears in three specific ways. All three were checked, and
none of them is fatal, but the test has to be stated as a bound rather than as a
confirmation.

**There is no era that isolates 2020.** `era_for` (`fetch_vsp_outbreaks.py:751`)
assigns `legacy_pre2004` before 2004, `pre` through 2019-12-31, `shutdown`
through 2021-12-31, and `post` thereafter; `SCORED_ERAS = ("pre", "post")`
(`vsp_class_era_scoring.py:106`) and shutdown "is never pooled into either
scored arm". The retrofit year sits inside the discarded stratum, and the scored
contrast is pre-2020 against 2022-onward. Per hull the postings are expedition
21/12, classic 95/8, spirit 130/43, mega 16/3, against
`MIN_POSTINGS_FOR_TARGET = 10` — so **two of four hulls have no post-era A4
target at all**, which also bears on the all-hulls feasibility question
separately from this design.

**The retrofit is one line of a confounded bundle.** `era_configuration_sets.py:343`
registers `surfaces.touchless_fittings` as *unrepresented*: "Touchless fittings,
crew/passenger zoning and cleanable materials: direction clear, magnitude
unmeasured, trade-press sourcing only", and
`post_covid_configuration_sources.md:210` lists measured efficacy for touchless
fittings among the explicitly unsourceable. The post era also carries buffet
service changes, zoning, cleanable materials, cleaning intensity and altered
ascertainment. No design can attribute a post-era change to doors.

**The knee is measured, and it is not where the framing puts it.** From
`telemetry_buffer/observation_model/vsp_covid_discontinuity_findings.md`
(bootstrap and permutation 10,000 replicates, seed 20260830; every statistic
conditional on VSP posting a voyage, because VSP publishes no voyage
denominator), norovirus-confirmed postings, pre n=194 against post n=52:

| statistic | post/pre | p |
|---|---:|---:|
| A7a passenger median attack-rate ratio | 0.897 | 0.1439 |
| A7b crew median attack-rate ratio | **1.518** | **0.0008** |
| A7c difference-in-differences, passenger over crew | 0.591 | 0.0001 |
| tail share ≥15% | 0.072 → 0.019 | 0.2048 (Fisher) |

So the passenger median moved mildly and not significantly — the "engineering
change alone didn't eliminate transmission" reading is correct, and stronger
than it looks in the tail (in the 1000+-passenger fleet-composition control the
≥15% share goes 0.049 → 0.000, 0/48, p=0.2214). But the **only significant
movement is crew attack rates going up**, and a fomite-reducing retrofit does
not predict that. Whatever the post era did, it redistributed risk between
passengers and crew more clearly than it lowered it.

**What the case can therefore be.** Not identification, and not a target to fit.
A **signed consistency bound**: with the lever class deleted and buttons, rails,
tables, taps and seats retained, the per-surface arm must predict a reduction in
passenger attack rate that is (i) strictly nonzero — a model in which door
levers carry no weight has the degree distribution wrong — and (ii) small
enough to sit inside the observed non-significance at n=194/52. An architecture
predicting elimination from deleting one high-degree class is falsified by the
data as it stands. That is a real constraint on the degree weights and it costs
no new anchor; it must not be promoted into a scored anchor, because the
contrast is confounded and the stratum that would carry it is discarded.

## 6. What this retires, and what it does not

Retires: `HIGH_TOUCH_AREA_M2` as a free parameter in the pickup path, and with
it the position that one unsourced scalar per zone class sets the magnitude of
the fomite route and of simulated swab positivity together.

Does **not** retire the uncertainty. The per-item areas remain Grade C declared
geometry, and dining, crew_mess and public remain ~99% driven by a declared
0.12 m² place-setting footprint and a 0.15 m² chair (ledger
`NORO-HIGH-TOUCH-DEFINITION-01`). What changes is the *shape* of the
uncertainty: from one quantity nobody has measured or can measure, to roughly
ten quantities that are each measurable in principle and several of which are
already measured. That is a reduction in unsourcedness and an improvement in
falsifiability, not a closure — and the per-class touch shares become the new
place where declaration hides, so they carry grades from the start.

Also unchanged: nothing here addresses the `SURFACE_CONTACTS_PER_HOUR["cabin"]`
= 17.9/h provenance defect recorded in
`consensus_tranche_46_touch_behaviour.md` §2 (Yuan 2024's four named surfaces —
desks, cellphones, keyboards, mice — are personal, not shared). That numerator
repair is prior to, and independent of, this denominator work.

## 7. The decision

| | option | what it buys | what it costs |
|---|---|---|---|
| **A** | Put a shaped prior on `HIGH_TOUCH_AREA_M2` per zone class and sweep it | Honest uncertainty now, no architecture change, fits the existing gate | Keeps a free parameter with no referent in the fomite route and in a scored observation channel; cannot answer what to clean; supplies no coincidence |
| **B** | Build the per-surface representation | Retires the parameter; supplies the coincidence structure `patchiness_program_brief.md` §3 says is the open mechanism; makes cleaning policy and class deletion expressible | 2–4× voyage cost; new engine state; the per-class touch shares become the new declared quantity |
| **C** | A now, B next, sequenced | Nothing blocks on the architecture; the sweep bounds the parameter that B then derives, so the two are a cross-check rather than a substitution | Two pieces of work; the sweep's output is superseded by construction |

Recommended: **C**, with B scoped as its own session and its acceptance gate the
neutrality identity of §3.4 rather than any anchor. A is cheap, is the correct
present description of our knowledge, and its interval is the thing B's derived
roll-up should be checked against.

## 8. Rules this inherits

- No parameter may be sourced by which value reproduces an anchor, and a frozen
  interval is not widened because a fit fails
  (`patchiness_program_brief.md` §5).
- The 2020 contrast of §5 is a consistency bound, never a scored anchor and
  never a fitting target.
- Nothing in this document is authorized to be built or run without an explicit
  decision. No constant is changed, no area is adopted, no campaign is
  submitted.
- `.agents/skills/model-parameter-provenance/SKILL.md` before any
  epidemiological quantity; the open ledger before quoting any dose figure.
