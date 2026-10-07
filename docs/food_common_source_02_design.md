# FOOD-COMMON-SOURCE-02 design — coupled contamination objects

Status: frozen — the mechanism contract, constants, and admissibility
gates below are frozen before implementation; nothing here may be
revised after it lands. Implementation splits into two legs: **leg 1**
(the provisioned-lot object arm) and **leg 2** (handler/diner
conditioning). This document is the spec for both legs. The scoring
campaign is a later stage with its own frozen admissibility.

## Grounding

Benjamin's redesign direction (2026-10-07, verbatim intent):

> "a distribution of pan contamination that has 1 pan contaminated even
> more rarely and several contaminated on very very rare occasion starts
> to move the shape of the outbreak"

> "the distribution of pans being independent of the course of infection
> doesn't make mechanistic sense, and pans being contaminated should be
> autocorrelated in space and time."

Scope decision (his): design all three arms now; implementation splits —
lot-object arm first, handler/diner conditioning as leg 2.

What v1 measured that this redesign must explain (FOOD-COMMON-SOURCE-01
fleet reads, `docs/norovirus/noro_food_01_readout.md`,
`docs/norovirus/noro_food_02_readout.md`,
`campaigns/noro/age_food_01/LEDGER.md` + per-tier readouts):

- **The excursion signature was produced but the pan draw is the wrong
  shape.** ~58% of pan-window event rows are zero-dose; takers ~10.7
  (exp) / ~25–26 (cls+spr) per live event; the provisioned-lot arm fires
  ~8.5–9.7% of voyages at the shipped U[0.02,0.15] interval against a
  ~0.4–0.9%/voyage anchored posting band — the declared interval sits
  ~10–20× high (*signature recovered, interval sits high* — a
  measurement on an unfitted declared interval, not a defect).
- **Postings are thin.** Posted% ship-rung vs off is ~12× (exp) / ~40×
  (cls), but posted-conditional reported pax AR is only 0.019–0.032
  against the class IQRs ~0.04–0.10 — the events that do happen are
  one-pan clusters too small to look like a foodborne outbreak.
- **The posting ceiling compresses with hull size** — ~1.7–1.9% on the
  3,000-agent hull. A fixed-size one-pan event buys less of the
  3%-of-population wire as the complement grows.
- **iid is the wrong independence.** v1 draws each (shedder, window)
  contamination event independently: a handler who contaminates lunch
  day 3 has no elevated rate at dinner day 3. Physically the same
  contaminated hands work the same station across a shift, and the same
  lot feeds a pan stream until it is exhausted. Contamination has
  autocorrelation in space (one station/zone) and time (contiguous
  windows / the course of infection) that iid cannot express.

The recurring-defect archetype applies here too: v1's lot arm is a
well-mixed draw standing in for a small number of concentrated objects —
one Bernoulli per voyage producing at most one pan, where reality is a
count distribution over persistent objects.

## The mechanism: contamination objects

Replace per-window iid event draws with **contamination objects** —
entities persistent in (station/zone, interval) that emit contaminated
pans while they live. The pan stays the bounded exposure unit and the
witness-event unit (one contaminated pan at one zone's one meal window —
the `common_source_events` row contract is unchanged); what changes is
what makes the pan dirty. An object has a lifecycle, an extent, and
exactly one realized contamination state, shared by every pan it
produces.

Three object kinds, one per source arm:

| kind | binds to | interval | pans emerge from |
|---|---|---|---|
| `provisioned_lot` | (zone, item line) | provisioned → galley receipt → service until exhausted or perished | lot extent: servings ÷ pan size, demand-gated per window |
| `ill_handler` | (agent, work station) | contiguous span: shedding ∧ on-duty ∧ same work zone | one pan per window the handler works in the span |
| `ill_diner` | (agent, self-serve venue) | the diner's infectious course | one pan per infectious meal pass at the venue |

### Leg 1 — the provisioned-lot object (implementation-ready)

**Voyage plan draw** (one set of draws per voyage per armed pathogen,
on the common-source stream, after the roster exists — same scheduling
point as v1's `_cs_plan_lots`):

1. Bernoulli on `lot_object_probability`: whether the voyage carries any
   contaminated provisioned lot. Decoupled from `food_safety_posture`
   unless `lot_posture_coupling` is on (carried over from v1 — the lot
   boards contaminated upstream of galley practice).
2. Conditional on ≥1: the object count K = 1 + extra, where each extra
   object is an independent Bernoulli on `extra_lot_probability`
   (geometric tail — `P(K ≥ k+1 | K ≥ k) = q`). The distribution is the
   design point: one object is rare, several are very very rare, and the
   count is a distribution rather than v1's 0-or-1.

**Object realization** (once per object):

- **Zone + item line**: uniform over Dining zones that serve at least
  one meal window (v1's served-window test), then a nominal item label
  drawn uniform over `LOT_ITEM_LINES` — a traceability label on the
  witness (shellfish / salad leaf / fresh produce / deli / bakery /
  dairy / garnish), no rate effect. The (zone, item) pair is the
  object's station: every pan it emits is served there — the spatial
  autocorrelation.
- **Start window**: uniform over the zone's served windows whose
  day-index < `embarkation_lot_window_days` (v1 constant carried over —
  fresh provisioned lots surface in the first services).
- **`lot_servings` S**: log-uniform, the lot's edible extent.
- **`lot_titre_gec_per_g` T**: drawn ONCE per object (v1 interval
  carried over). One realized contamination state for the whole object —
  every pan it emits carries T.
- **`item_take_share` τ**: drawn once per object — it is the same item
  for its whole life, so its appeal is an object property, not a
  per-window one.
- **Imported lineage**: minted once per object through the existing
  `_cs_lot_mix` path (`origin="imported:lot"`, genotype from the
  embarkation prior) — a lot is one contaminated batch, one strain;
  every taker it doses inherits that mix.

**Object lifecycle** — at each meal window the bound zone serves, while
the object is alive:

- Demand = Binomial(cohort_present, τ) — the same cohort/take-share
  machinery as v1 (assigned, scheduled on the meal token, not
  quarantined/ashore/departed).
- `servings_served = min(demand, servings_remaining)`.
- Pans emitted this window = `ceil(servings_served / pan_servings)` —
  `pan_servings` drawn once per window (v1 constant carried over). The
  station replenishes the pan while the lot lasts; when the lot runs dry
  mid-window the item is 86'd and later demand goes unserved. **Pan
  count emerges from object extent** — S, the cohort's demand, and the
  window cadence — never from a drawn count.
- Each emitted pan is a witness event row (`common_source_events`, same
  fields as v1 plus `object_id` and `pan_serial`) and credits its takers
  through the identical `_cs_credit_pending` presence-staggered path.
  Per-serving dose = T × `serving_mass_g` (drawn per pan, as v1 drew per
  event). Σ credited across the object ≤ T × serving_mass × S — mass
  conservation bound replaces v1's per-pan bound with the object's.
- `servings_remaining −= servings_served`. Demand zero leaves the lot
  intact — it waits for the next service.
- **Death**: `servings_remaining ≤ 0` (exhaustion), or day-index >
  start_day + `lot_shelf_life_days` (perishability — residual servings
  discarded), or voyage end.

This is the autocorrelation the grounding asks for: contiguous windows,
one station, one contamination state; a small lot exhausts in its first
window (= v1's single pan, now rarer because the voyage probability is
lower), a large lot runs several windows and can put multiple pans out
in parallel on a big-service window.

**Space**: one (zone, item) station per object. A multi-zone spread
(same supplier lot split across galleys) is covered only through the
`extra_lot_probability` count tail — declared scope bound, flagged.

### Leg 2 — handler and diner objects (specified, implementation later)

v1 draws Bernoulli(rate × posture) per (shedding agent, window) —
independent across windows. Leg 2 conditions on the realized shedding
agent: **an object is seeded once per contamination-relevant span of
the agent's infectious course, and emits pans over the contiguous
windows that span covers** — the same persistent-object semantics as
the lot arm.

- **`ill_handler` object** — a *span* is a maximal contiguous run of
  epochs where agent is shedding (same eligibility as v1:
  `get_pathogen_shedding > 0`, not quarantined, not confined) AND
  `_on_service_duty(agent, work_zone, epoch)` at the SAME work zone.
  At span start: one seeding draw on
  `handler_span_contamination_probability` (× `food_safety_posture`,
  the same hygiene-practice modifier as v1). Seeded ⇒ one contaminated
  pan per service window the handler works in that span — the pan they
  handle — so one shedding shift produces a run of pans at one station,
  and the run's length emerges from the span (and from when the
  exclusion policy pulls them, which terminates the object). Deposits
  compose per pan exactly as v1 — contacts × per-contact transfer ×
  hand load, depleting the hand — so pans late in a span carry less as
  the hand draws down (intra-object dose decay, a real measured tail,
  not a declared one). Pans land at the handler's work zone when it is
  a Dining zone (v1 scope); a handler whose work zone is galley-typed
  (name contains "Galley" per `_service_zones`) contaminates the pan
  stream it feeds: one Dining zone drawn once per object — declared
  simplification, flagged (no galley→venue wiring exists in the
  platform model today).
- **`ill_diner` object** — the course is the agent's whole infectious
  window at their assigned self-serve venue (`dining_zone` ∈
  `PER_MEAL_TABLE_DINING_SERVICE_TYPES`, unchanged). One seeding draw
  per infectious course on `diner_course_contamination_probability`
  (× posture). Seeded ⇒ each meal pass at the venue while shedding and
  unexcluded emits one contaminated pan (the pan/utensil set they
  touch) — repeat contamination by the same diner across successive
  meals, autocorrelated through their infection course rather than iid
  per meal.
- Both arms keep the v1 exclusions (reported symptomatic under
  `crew_duty_exclusion`/quarantine never sources; confinement suspends
  — and terminates — the object; a later eligible span re-seeds on a
  fresh draw) and the strain inheritance through the realized agent's
  resident strain / `_draw_source` → `_inherit_strain` path, taken ONCE
  per object (the shedder's strain does not change inside a span).
- Multiple objects may emit pans into the same (zone, window): v1's
  "first fired source wins" exclusivity was a single-pan-per-window
  construction and is dropped under object semantics — two shedding
  diners at the same buffet contaminating different pans is now
  expressible, and is part of the multi-pan tail. Per object per window
  the cap is one pan (handler: the pan they work; diner: the pan they
  take), lot arm excepted (replenishment can emit several).

### Modes

Per-arm mode keys under `transmission.common_source` — the leg split
needs each arm's physics flippable independently:

- `lot_mode: "object"` (shipped default — the better physics ships on)
  / `"independent"` — the labelled v1 baseline: the v1 lot code path
  preserved, consuming the identical draws it consumed before
  (per-voyage Bernoulli on `lot_event_probability`, two-stage
  (zone, token, day) pick, single pan).
- `handler_mode` / `diner_mode`: `"object"` (default once leg 2 lands;
  until then the arms run the v1 path regardless) / `"independent"`.
- `transmission.common_source.mode` (`on`/`off`) is unchanged: `off`
  spawns no stream and is bit-identical to the pre-mechanism engine.
  Unarmed profiles (`common_source_events.enabled` absent/false) get
  no objects and no draws under any mode — zero-rate by construction.

### RNG draw discipline

Everything stays on the dedicated `_COMMON_SOURCE_STREAM_KEY` stream —
spawned only when armed, so `mode: off` and unarmed profiles draw
nothing anywhere and stay bit-identical.

**One physical contamination event shares ONE realized draw across
every dose direction it produces.** The object IS the physical event:
its titre (lot), its strain mix, its item take-share, and its source
identity are drawn once per object and shared by every pan and serving
it emits. Per-window/per-pan draws that remain (demand binomial, pan
servings, serving mass, shedder per-pan transfer) are properties of the
service and the shedder's evolving hand — not of the contamination
event — so they draw per window without breaking the discipline.

**Where draws differ from v1, per-seed pairing cannot attribute.** The
voyage draw changes shape (Bernoulli+geometric count vs one Bernoulli),
the lot plan draws object fields v1 never had (item, S, shelf life), the
emit loop consumes demand/pan draws v1 consumed per event, and leg 2
replaces per-window Bernoulli with per-span/per-course seeding draws.
Inside this re-roll band paired seeds re-roll, per the
stochastic-attribution skill: attribution of the mechanism's effect is
**distribution-level contrast** — same seed lists on both arms,
paired-difference statistics on the fleet outputs — never a claim that
seed N's v1 voyage maps to seed N's object voyage. The `independent`
baseline modes exist so the contrast is run on the current engine, not
against an old commit.

### Constants (frozen, graded)

New leg-1 constants:

| constant | interval / value | grade | source |
|---|---|---|---|
| `lot_object_probability` | U[0.001, 0.02] per voyage, P(≥1 object) | C declared-bounded | Composed bound: posted-outbreak incidence ~0.3–0.5%/voyage (VSP/Mouchtouri rates — the measured anchor) divided by the measured excursion→posting conversion ~0.43 (NORO-FOOD-01 readout §2) ≈ 0.7–1.2% required object frequency; interval brackets the composed point and sits below the contaminated-lot prevalence ceiling v1 cited (Dirks 2025 market-ready lots) netting sub-outbreak events. Supersedes `lot_event_probability` (deleted under object mode — no alias; it remains only inside the `"independent"` baseline). Declared sweep axis — not a fit. |
| `extra_lot_probability` | U[0.02, 0.25] per extra object, P(K≥k+1 \| K≥k) | C declared | Co-contaminated provisioning receipt — one supplier batch spanning several item lines in a single load. ∅ direct per-receipt measurement; the multi-vehicle share in investigation records (Clough 2018: outbreaks with several implicated items are the minority tail) bounds the shape, not the value — the tail knob for "several on very very rare occasion". |
| `lot_servings` | log-U[30, 600] servings | C declared | Documentary provisioning units: a shellfish sack ~100–200 pieces, produce cases tens of portions — order-of-magnitude units, log-uniform because provisioning sizes are multiplicative. ∅ per-lot shipboard measurement. The object's extent; pans emerge from it. |
| `lot_shelf_life_days` | U-int[1, 4] | C declared | Fresh perishables hold ~1–3 days refrigerated; the object's maximum live span. Documentary; bounds the interval half of (station, interval). |

Carried over unchanged from FOOD-COMMON-SOURCE-01 (same sourcing,
same grades — see the v1 table): `embarkation_lot_window_days`
U-int[1,3], `item_take_share` U[0.10,0.60] (now drawn per object),
`pan_servings` U-int[20,80], `serving_mass_g` U[50,250],
`lot_titre_gec_per_g` log-U[1e1,1e4] (now drawn per object),
`food_safety_posture` per-platform scalar (now multiplies seeding
probabilities), `lot_posture_coupling` default off,
`diner_contacts_per_event` U-int[1,5], `HAND_TO_FOOD_TRANSFER_FRACTION_
RANGE` + `FOOD_HAND_CONTACTS_PER_DAY` × `FOOD_HANDLER_CONTACT_
MULTIPLIER` deposit composition, pan→serving retention 1.0.

New leg-2 constants:

| constant | interval / value | grade | source |
|---|---|---|---|
| `handler_span_contamination_probability` | U[0.01, 0.30] per (shedding, on-duty, same-station) span | C declared | ∅ per-shift contamination measurement (unchanged from v1's null). Declared via v1-equivalence arithmetic: v1's per-window E ≈ 0.05 × ~1–2 service windows per duty span ≈ 0.05–0.10 per span; the interval brackets that and leaves tail room — same bounds argument as v1 (NEARS ~40% ill-worker implication, Sabrià 2016 asymptomatic pool), re-denominatored from per-window to per-span. Supersedes `handler_event_probability` under object mode. |
| `diner_course_contamination_probability` | U[0.005, 0.15] per infectious course | C declared | ∅ per-meal contamination measurement (unchanged). v1-equivalence: per-meal E ≈ 0.025 × ~10 infectious meals ≈ 0.25 expected events per infectious diner course — the per-course seeding interval sits below that, trading event count for clustered shape (each seeded course emits a pan per infectious pass). Supersedes `diner_event_probability` under object mode. |

### Witness / exposure record schema

- `matrix.common_source_objects` — NEW top-level list, one row per
  object: `object_id`, `pathogen_id`, `source_kind`, `source_agent_id`
  (null for lot), `zone`, `item_label` (lot) / work or dining zone
  (handler/diner), `seeded_epoch`, `exhausted_epoch` (or null at
  voyage end), `end_reason` ∈ {exhausted, perished, source_excluded,
  shedding_ended, voyage_end}, `windows_covered`, `pans_emitted`,
  `servings_served`, `lot_servings` + `lot_titre_gec_per_g` (lot only),
  `strain_id` (or mix ref).
- `matrix.common_source_events` — same fields as v1 **plus** `object_id`
  and `pan_serial` (pan index within its object). The event unit stays
  one pan at one zone's one meal window — every v1 readout that counts
  pan-window rows still parses.
- `matrix.common_source_exposures` — gains `object_id`; one row per
  (taker, pan). An agent present across two of an object's windows can
  be dosed twice — once per pan, physically right (they ate the item
  twice); never twice for one pan.
- `core.common_source_telemetry` — adds `objects_<kind>`,
  `pans_emitted`, `object_windows`, `multi_pan_windows`,
  `objects_exhausted`, `objects_perished`; keeps `events_<kind>` (now
  counts pan rows), `takers_served`, `dose_credited`.
- `simulation_history.schema.json` gains the object list and the new
  fields at implementation (leg 1).

## Measurement / readout plan (pre-declared)

Which settled diagnostics the mechanism is **expected to move**, and
which it **must not** — the admissibility criteria for the scoring
campaign:

Expected to move:

1. **Posting-frequency overshoot** — object frequency declared ~1% ⇒
   posted share should drop toward the ~0.3–0.5% anchor band from
   FOOD-01's 2–7%, not by tuning but because objects are rarer and
   individually bigger. Excursion-voyage share ≈ object-voyage share.
2. **Thin posted-conditional AR** — multi-pan, multi-window objects
   produce larger per-object clusters ⇒ posted-conditional reported
   pax AR should rise toward the class IQRs (~0.04–0.10) from
   0.019–0.032. THE "shape of the outbreak" move.
3. **Hull-scaling compression** — a bigger object buys more of the
   3%-of-population wire ⇒ the ~1.7–1.9% posting ceiling on the
   3,000-agent hull should lift relative to FOOD-01.
4. **Outbreak shape / burst metrics** — declare honestly: a
   single-window pan concentrates acquisitions into ~4–6 epochs and
   v1 scored on burst12; a multi-window object spreads its cluster over
   contiguous windows, so burst12 on excursion voyages may FALL even as
   the tail grows — **burst48 (or a declared cluster-window metric) is
   the discriminator for objects spanning windows**, and the readout
   must report excursion-vs-rest on both. The tail that matters is the
   posting tail and posted-conditional AR above.
5. **Event-row composition** — lot pans carry titre > 0 always, so the
   ~58% zero-dose row share should fall (handler/diner deposit rows
   keep v1's zero-dose mechanism); takers/event and arm-mix reads
   change as multi-pan objects emit more, smaller rows.
6. **Multi-pan tail** — voyages with ≥2 contaminated pans (distinct
   pans, same or different objects) exist at a measurable rate that v1
   could not express: the telemetry's `multi_pan_windows` and
   objects-per-voyage distribution are the new diagnostics of record.

Must NOT move (invariants — a move here is a defect signal):

- **Median infection AR / median acquisitions** — the mechanism is a
  tail: object voyages are ~1%, so medians should be unmoved within
  noise.
- **Unrelated pathway counts** — contact, aerosol, HVAC, fomite, pool
  routes untouched; `common_source_food` remains a small route share
  (FOOD-01 measured 1.2–8.9%; objects may raise the per-object share
  but the >50% over-delivery alarm stands).
- **Non-object voyages** — a voyage carrying no objects must be
  indistinguishable in distribution from the `"independent"` baseline's
  no-lot voyages.
- **`mode: off` and `"independent"` baselines** — bit-identical
  reproduction, as admissibility below.

Readout mechanics carry over: `tools/noro_diag/common_source_readout.py`
gains an object view (objects/voyage, pans/object, windows/object,
end_reason mix); the anchor/onset readouts are unchanged at the metric
level (burst12 reported alongside burst48 per point 4). Canary ≥20
seeds at one cell, then stop and report — user decides the fleet.

## Admissibility / test gates (frozen)

Leg 1:

1. `mode: off` → zero objects, zero events, zero doses, zero records;
   no stream spawned; shared RNG bit-identical.
2. `lot_mode: "independent"` → the v1 lot path produces bit-identical
   events and draws to the pre-change tree (same stream consumption).
3. Forced `lot_object_probability` = 1, `extra_lot_probability` = 0 →
   exactly one object, seeded inside the embarkation window at a served
   Dining zone; forced `extra_lot_probability` = 1 → K > 1 (the tail
   exists); object count distribution responds to both knobs only
   through the count — never through pan size or dose.
4. **One object, one draw**: every pan an object emits carries the same
   titre and the same strain mix; two objects carry independent ones.
5. Emergence: `Σ servings_served ≤ lot_servings`; pans emitted =
   ceil-per-window demand, never drawn; an object with `servings_
   remaining` > 0 and remaining shelf life stays alive across an
   empty-demand window.
6. Perishability: no pan after start_day + `lot_shelf_life_days`;
   `end_reason` recorded correctly at exhaustion, perishing, voyage
   end.
7. Mass conservation: Σ credited ≤ T × serving_mass × lot_servings;
   per-serving dose monotone in titre.
8. Determinism: identical seed + config ⇒ identical object set, event
   set, exposures.
9. Cohort integrity: every dosed agent was present in the object's zone
   during the emitting window; ≤1 serving per (agent, pan); an agent
   may be dosed at most once per pan and may legitimately dose on two
   different pans of the same object.
10. Posture: `food_safety_posture` enters seeding probabilities only
    (handler/diner leg, and lot only under `lot_posture_coupling`);
    never pan size, titre, or dose.
11. Unarmed profiles produce zero objects under every mode.

Leg 2 (frozen now, gated at that leg's PR):

12. A handler object exists only inside a shedding ∧ on-duty ∧
    same-work-zone span; terminates on exclusion/shedding end/station
    change; a reported symptomatic handler never seeds.
13. A diner object emits only at `PER_MEAL_TABLE_DINING_SERVICE_TYPES`
    venues during the diner's infectious passes.
14. Two objects emitting into one (zone, window) produce two pans and
    two witness rows — no first-wins exclusivity under object mode.
15. The span/course seeding draws are per (agent, span/course): the
    same agent at the same station produces correlated pans; strain
    inheritance rides the agent's resident strain once per object.

## Non-goals

- Engine implementation — this document is the spec; leg 1 and leg 2
  are separate implementation PRs.
- No constant fitting; every interval above is declared and stays a
  sweep axis.
- No campaign submission under this design; the scoring campaign gets
  its own frozen admissibility.
- No changes to the illness/reporting funnel machinery.
- No arming of `sars_cov2_resp`, `influenza_a`, vibrio, campylobacter or
  any other profile — zero objects by construction until their own
  sourcing pass.
- Mid-voyage provisioning (port re-supply), galley→venue wiring, a
  per-item service-pattern distribution, and multi-zone lot splits —
  declared simplifications flagged in the arm sections, each a possible
  later axis, none spec'd here.
- Shared-air mass-gathering events, embarkation-cohort arm, retained-
  pan observation machinery — carried over as v1's non-goals.
