# FOOD-COMMON-SOURCE-01 design — synchronized common-source foodborne events

Status: frozen — the mechanism contract, constants, and admissibility
gates below are frozen before implementation; nothing here may be revised
after it lands. The scoring campaign (canary + onset-curve re-readout) is a
later stage with its own frozen admissibility.

> **Status (2026-10-07):** Implemented — the shipped v1 mechanism and the
> `"independent"` labelled baseline of record. The mechanism contract going
> forward is `FOOD-COMMON-SOURCE-02`
> ([food_common_source_02_design.md](food_common_source_02_design.md)):
> contamination objects persistent in (station/zone, interval) replace the
> per-window iid draws. This file remains the record of what shipped and was
> measured (NORO-FOOD-01/02, AGE-FOOD-01).

## Grounding

Benjamin's grounding statements (this campaign line, 2026-10-04):

> "I don't believe necessarily that the defect for norovirus is in the
> reporting chain... it's in the infection process not being spikey during
> those rare events, which may be just a tad too rare, but still, early in
> the cruise."

> "It feels like a lost tail. That is, we have good statistics for the
> medians, but under-dispersed due to the way research works."

> "We know that these kinds of event can cause big outbreaks, and these are
> familiar 'foodborne' outbreaks of the land lubbing kind. So we can
> leverage additional statistical sources."

> "The question really is how does the food get contaminated. From an ill
> passenger or crew in the appropriate mess, or from an ill food service
> worker? It can be either."

> "Apply any mechanism appropriately across the appropriate diversities of
> pathogens; only if it is really noro only does it get noro only" —
> reinforced: "this should be all about food contamination, not just noro."

> "For vibrio, we might have bad oysters - that's a very pathogen specific
> case with unique outcomes. not today's problem."

> On pan retention: military dining facilities keep back a portion from
> each pan for retrospective investigation — institutional recognition
> that *one pan is one bounded common-source unit*. His caveat is also
> correct: that practice chiefly targets time-temperature abuse, which is
> the bacterial variant (held-food growth); viruses do not grow in a held
> pan, so for the armed pathogen the only source of a contaminated pan is
> a human or a contaminated lot.

NORO-ONSET-CURVE-01 (measured `f1ce5c5c`, readout
`norovirus/noro_onset_curve_01_readout.md`, ledger
`docs/ledger/NORO-ONSET-CURVE-01.md`) showed the signature is structurally
absent: every voyage on every hull is a propagated ramp, burst12>0.5 share
= 0.00 across all six big-hull cells and the mega cells (n=308), and all
33 posted voyages sit inside their cell distributions — a volume tail,
not an event subpopulation. The ledger names "synchronized common-source
dose (point-source event)" as the missing excursion generator.

The achievable-tail bound confirms the missing draw is at the
*cohort-exposure* level, not per-host:

- Emesis events reach ~1–4 fomite requesters per episode (footprint
  geometry); the emesis titre band is only 5× (Grade B, Kirby 2016) — no
  tail that could lift a shared exposure.
- The standing `food_pools` are starved to ~0 on every route table and,
  worse, cannot burst even when loaded: ingestion grazes
  `FOOD_INGESTION_FRACTION_PER_DAY` (0.05/day) of the pool per head, so a
  bolus injected into the pool smears across the ~10-day decay window —
  the pool has no draw for "how many hosts ate the same pan at the same
  service".
- Some per-host draws do carry real tails (`shedding_variance_log10`
  σ=1.0; aerosol fraction spans 370×; transfer fraction 150×) — they feed
  *dose size*, never *cohort size*. The under-dispersion Benjamin
  describes lives exactly where no draw exists: how many people share one
  contaminated thing.

This mechanism adds that draw, sourced from the land-based foodborne
outbreak literature (public-health investigations report the exposed-
cohort size and attack fraction per implicated item — precisely the
distribution shipboard literature lacks).

## Structural components

### 1. `common_source_events` — per-pathogen profile block

A new block beside `food_contamination` in each pathogen profile:

```json
"common_source_events": { "enabled": true }
```

Absent or `enabled: false` ⇒ the pathogen can never fire an event: zero
draws, zero doses, identical runs to today. `norwalk_gi` is armed in v1;
every other active profile (`sars_cov2_resp`, `influenza_a`, and the
Edison set's vibrio/campylobacter entries) ships unarmed — their arming is
a later per-pathogen sourcing pass (vibrio's oyster-lot literature is its
own problem per the grounding). Optional per-pathogen overrides (item
titre range, item take share) live inside the block so a later pathogen's
literature replaces constants rather than the mechanism.

### 2. The event unit: one pan at one zone's one meal window

An event contaminates **one pan** served at **one Dining zone** during
**one meal window** — the same bounded unit that pan-retention practice
assumes. A meal window is the contiguous epochs of a `Meal:Breakfast/
Lunch/Dinner` token block at that venue (honoring the venue's
`meal_seatings` stagger, which already deals diners to slots). Sites: any
Dining zone for the upstream sources (a handler contaminates during prep
or service regardless of service type; a contaminated lot is served
wherever it was provisioned). The diner-mediated arm additionally
requires self-serve service — `PER_MEAL_TABLE_DINING_SERVICE_TYPES`
(`buffet`, `crew_mess`) — since a diner cannot contaminate a plated MDR
dish from the dining room floor.

### 3. The source draw — how the pan gets contaminated

Per event the source is drawn, not assumed. Three source kinds, at most
one event per (zone, meal window) — first fired source wins:

- **`provisioned_lot`** — a boarded lot arrives contaminated. At voyage
  init a Bernoulli draw on `lot_event_probability` decides whether the
  voyage carries one; on a hit the event is scheduled at a uniform-random
  meal window at a uniform-random Dining zone within the first
  `embarkation_lot_window_days` of the cruise — early-cruise by
  construction, matching the "early in the cruise" observation and the
  physical fact that fresh provisioned items surface in the first
  services. This arm needs no onboard shedder, so it fires even on
  voyages where import seeds nothing.
- **`ill_handler`** — a food employee shedding while on service duty
  contaminates the pan they are working. Each meal window, for each
  shedding agent with `_on_service_duty(agent, zone, epoch)` true, one
  Bernoulli draw on `handler_event_probability`. Sabrià 2016 (59.1% of
  exposed food/health workers NoV+, >70% asymptomatic at titres
  comparable to symptomatic shedders) is what keeps this arm live: the
  VSP `crew_duty_exclusion` rule removes only *identified/reported*
  symptomatic food employees (48-h symptom-free clause), so under the
  shipped policy the residual source pool is asymptomatic, pre-
  symptomatic, and unreported shedders — the documented hole, not a
  defect of the policy.
- **`ill_diner`** — a shedding diner at a self-serve venue contaminates a
  pan via utensil/pan-edge contacts during their pass. Each meal window
  at each self-serve zone, per shedding diner present, one Bernoulli draw
  on `diner_event_probability`. The cohort is the same-zone diners in
  that window (a v1 simplification — the contaminated pan serves the
  seating cohort alongside/after the shedder rather than a strict
  after-them tail; flagged as such).

The handler and diner arms are *emergent*: they fire only when a shedding
host stands at the service, so their early-cruise rate inherits the
existing embarkation/import prevalence and shedding curves — no new
timing parameter. This is the "a tad too rare" knob's natural home:
per-shedder event probabilities are the sweep axis.

The realized source mix is a *measurement*, not a parameter: Clough 2018
(47 definite food-handler outbreaks vs 27 contaminated-at-source in the
systematic review) is the sanity prior the witness telemetry is compared
against — not fitted to.

**`food_safety_posture` — the VSP-conditioned rate modifier.** The
per-shedder event probabilities above are not flat across the fleet: a
per-platform scalar `food_safety_posture` multiplies the handler and
diner event probabilities (the arms whose firing depends on the ship's
own hygiene practice). It is sourced, not declared: the public VSP
inspection database scores every ship twice yearly and itemizes
violations in the food-handling categories — a measured per-ship posture
distribution, and precisely the covariate that explains why Mouchtouri's
45 outbreaks over 26 ships are not uniform (outbreak-prone ships exist).
v1 default is 1.0 for platforms without a posture entry; the
score→multiplier functional form is a declared linear map (Grade C,
swept in the canary) over a measured input — never fitted to outbreak
anchors. Application to `lot_event_probability` is a declared switch,
default off: a provisioned lot boards contaminated upstream of the
ship's galley practice, and only storage/handling-on-board arguments
couple it to the platform score.

### 4. Exposed cohort and serving dose

- Cohort = agents assigned to the zone (`dining_zone == zone`) who are
  present and dining during the event window (scheduled activity begins
  `Meal`, not `Work`/`Sleep`, not confined, departed or ashore) — the
  same occupant logic `_deal_meal_tables` already uses.
- Each cohort member draws Bernoulli(`item_take_share`) → takers. A pan
  holds `pan_servings` servings; if takers exceed servings, a uniform
  subset of size `pan_servings` is served (crowded-service bound);
  `servings_taken = min(takers, pan_servings)`.
- Dose per serving:
  - `provisioned_lot`: `lot_titre_gec_per_g × serving_mass_g` (the lot's
    own titre — a distribution draw, not a shedder state).
  - `ill_handler` / `ill_diner`: the shedder's pan deposit computed the
    way `_food_deposits` composes it — contacts × per-contact transfer
    draw (`HAND_TO_FOOD_TRANSFER_FRACTION_RANGE`) × hand load — divided
    by `pan_servings`. Handler contact count reuses
    `FOOD_HAND_CONTACTS_PER_DAY × FOOD_HANDLER_CONTACT_MULTIPLIER` pro-
    rated to the window (no new constant); diner contacts take
    `diner_contacts_per_event`. Pan→serving transfer is declared
    lossless (conservative upper bound; no retention constant invented).
    Credited mass is bounded by the deposit: Σ credited ≤ pan_mass.
- Delivery is the standard challenge path: `_accumulate(agent_id,
  "common_source_food", dose, agent_doses, agent_pathway_doses,
  attribution)` once per taker in the epoch they are present;
  `_resolve_pathogen_challenge` then applies susceptibility, the
  secretor gate, and the dose-response unchanged. `PATHWAY_EFFICIENCY_
  KEYS` gains `"common_source_food": "food_contamination"` so the food
  portal's route efficiency applies to servings exactly as to grazed
  pool shares — same portal, same efficiency.
- Strain attribution: handler/diner events carry the source agent's
  lineage through the normal `_draw_source`/`_inherit_strain` path
  (source id recorded on the witness). Lot events introduce an imported
  lineage drawn from the embarkation genotype distribution and tagged
  `imported:lot` — the provisioning supply carries its own genotype,
  which is also what a real outbreak investigation would find.
- Every taker is credited (an eaten serving is a real dose regardless of
  status); infection resolves per-agent through the standard challenge,
  including the superinfection path for already-infected takers.

### 5. Dedicated RNG stream

All draws come off a dedicated stream keyed like `_FRAILTY_STREAM_KEY`
(`_COMMON_SOURCE_STREAM_KEY`), deterministic per seed and order-
independent. `mode: off` draws nothing on any stream, so the baseline is
bit-identical by construction.

## Constants (frozen, graded)

| constant | interval / value | grade | source |
|---|---|---|---|
| `lot_event_probability` | U[0.02, 0.15] per voyage | C declared-bounded | Per-voyage probability a contaminated provisioned item reaches service. Bounded below by posted-outbreak incidence: Mouchtouri 2024 (*Eurosurveillance*) counted 45 cruise outbreaks across 26 ships with foodborne vehicles the minority share (person-to-person dominant in 35/45), and NEARS retail data (Moritz 2023, MMWR) give ~0.3 reported foodborne outbreaks per establishment-year — a ship running ~60 meal services per voyage sits in the same order of magnitude. Bounded above by contaminated-lot prevalence (Dirks 2025: 44% sequence-positive market-ready oysters) netting out sub-outbreak events that never surface. Declared sweep axis — not a fit. |
| `handler_event_probability` | U[0.005, 0.10] per (shedding handler, service window) | C declared-bounded | ∅ direct per-shift measurement. Bounded by NEARS: ~40% of outbreaks with identified contributing factors implicate an ill worker (Moritz 2023), and only 16.1% of establishments had all four ill-worker policy components — ill handlers commonly work. Sabrià 2016 (*J Clin Virol*) supplies the asymptomatic-shedding precondition (59.1% of exposed workers NoV+, >70% asymptomatic, comparable titres). Per-shedder-service rate is ∅lit → declared interval, swept. |
| `diner_event_probability` | U[0.001, 0.05] per (shedding diner, meal) | C declared | ∅ — no study reports a per-meal contamination probability for an infectious self-serve diner. Shared-service contamination events are documented (Papafragkou 2024 wedding buffet; multiple Norwalk-family buffet investigations) but rarer than handler events in the investigation record — interval sits strictly below the handler arm's. |
| `embarkation_lot_window_days` | U-int[1, 3] | C declared | Fresh provisioned lots surface in the first services; perishables turn over within days. Documentary provisioning practice — no literature measurement. |
| `item_take_share` | U[0.10, 0.60] per diner | C declared | Item-exposure fractions among diners in buffet investigations span roughly a tenth to a majority of the meal cohort (Papafragkou 2024: 41% of interviewed guests ate the implicated fruit salad). |
| `pan_servings` | U-int[20, 80] | C declared | Hotel-pan/buffet service practice — a pan serves tens of portions. Documentary; the pan as the bounded exposure unit matches the retained-sample practice in the grounding. |
| `serving_mass_g` | U[50, 250] | C declared | Documentary portion sizes. |
| `lot_titre_gec_per_g` | log-U[1e1, 1e4] | B | Contaminated-item titres from outbreak investigations: Flannery 2013 oyster lots >1e3 copies/g digestive tissue; produce/RTE items sit lower. Interval spans the reported range; log-uniform draw because the underlying distribution is multiplicative and heavy-tailed. |
| `diner_contacts_per_event` | U-int[1, 5] | C declared | A diner contacts shared utensils and the pan's edge a handful of times per pass; no literature measurement. |
| `food_safety_posture` | per-platform scalar ≥0; v1 default 1.0 | input **B**, map C declared | Public VSP inspection database — per-ship inspection scores and itemized food-handling violations (twice-yearly, every cruise vessel in US trade). The posture input is measured; the score→rate-multiplier map is a declared linear form, swept in the canary — the distinction matters: we measure which ships are sloppy, we declare how much sloppiness buys. |
| pan→serving retention | 1.0 (lossless) | C declared bound | Deposited mass distributes across servings unattenuated — the conservative direction; no retention constant invented (∅). |

Derived, not new: handler contacts per service =
`FOOD_HAND_CONTACTS_PER_DAY × FOOD_HANDLER_CONTACT_MULTIPLIER ×`
window share; per-contact transfer = `HAND_TO_FOOD_TRANSFER_FRACTION_
RANGE`; shedder hand load = the agent's existing `hand_load_by_pathogen`
state (which inherits the σ=1.0 shedding tail — the event size
distribution couples to a real measured tail rather than a declared one).

## Arm modes

`transmission.common_source.mode` — `on` (shipped default: the mechanism
is the better physics, so it ships on, per the standing convention),
`off` (the labelled pre-change baseline for paired attribution).
Sub-parameters live under `transmission.common_source.*` and are ignored
under `off`. The per-pathogen `common_source_events.enabled` gate applies
within `on`; both gates must pass for an event to exist.

## Telemetry

- Witness records (`matrix.common_source_events`): `event_id`, window
  epoch range, `zone`, `service_type`, `source_kind` ∈ {provisioned_lot,
  ill_handler, ill_diner}, `source_agent_id` (null for lot),
  `food_safety_posture` applied, `pan_mass` or `lot_titre`,
  `cohort_size`, `servings_taken`, per-serving dose, taker ids.
- Per-taker records on `matrix.common_source_exposures` mirroring
  `food_contamination_exposures`.
- Counters (`core.common_source_telemetry`): events fired by source kind,
  takers served, dose credited.
- `acquired_particles_by_route` and the pathway breakdown carry
  `common_source_food`, so the onset-curve readout and dominant-route
  attribution see event acquisitions directly — no readout changes
  needed to falsify the hypothesis.

## Admissibility / test gates (frozen)

1. `mode: off` produces zero events, zero `common_source_food` pathway
   doses, zero witness records, and a bit-identical run to the
   pre-mechanism tree (dedicated stream, no engine.rng draws).
2. A profile without `common_source_events` (or `enabled: false`) fires
   zero events under `mode: on` — sars-cov-2, influenza, vibrio and
   campylobacter runs are unchanged by construction.
3. Forced lot event (`lot_event_probability` = 1): an event lands inside
   the embarkation window at a Dining zone; cohort ⊆ that zone's present
   diners; realized take share matches the declared interval within
   sampling error; credited mass ≤ lot mass.
4. Handler arm fires only when a shedding agent has `_on_service_duty`
   in that zone that window; under the shipped duty-exclusion policy a
   reported symptomatic handler never sources an event (asymptomatic and
   unreported shedders may). Diner arm fires only at
   `PER_MEAL_TABLE_DINING_SERVICE_TYPES` zones.
5. Mass conservation: Σ credited doses ≤ pan deposit (handler/diner) or
   `lot_titre × serving_mass × servings` (lot); per-serving dose is
   monotonically non-decreasing in titre and in shedder hand load.
6. A forced high-titre event produces same-window acquisitions
   attributed `common_source_food`; a zero-titre event produces none —
   the dose-response passthrough is what makes events spikey, not an
   infection override.
7. Determinism: identical seed + config ⇒ identical event set.
8. Cohort integrity: every dosed agent was present in the event zone
   during the event window; no agent dosed twice for one event.
9. `food_safety_posture` enters only the event-rate draws: a posture
   sweep moves event frequency, never dose size, and a platform at
   posture 1.0 (or no posture entry) is bit-identical to the
   unconditioned arm.

## Non-goals

- Vibrio, campylobacter, and every other unarmed profile: zero events by
  construction until their own sourcing pass (the oyster-lot literature
  is pathogen-specific with unique outcomes, per the grounding).
- Time-temperature abuse / growth-in-pan modelling — the bacterial
  variant; the armed pathogen does not grow in held food (profile
  `growth_rate_per_day` already 0).
- Multi-lot voyages (>1 contaminated lot per voyage) and diner-arm
  "subsequent-cohort" refinement — declared v1 bounds.
- **Shared-air mass-gathering events** (muster drill, show, choir — a
  mass cohort sharing one airspace for an hour): the COVID-shaped member
  of this design space and a plausible part of the serious COVID misses,
  but a different delivery pathway (near-field/HVAC, not ingestion) and
  its own bounded stage — declared here so the event/cohort/witness
  scaffolding is built to admit it, not so it ships armed.
- Embarkation-cohort arm (a travelling party boards incubating from one
  contaminated meal ashore) — import-side generator, different block.
- Observation-side machinery (retained pan samples, investigation
  attribution) — the pan is the exposure unit only; no assay channel.
- No campaign. Measurement is the next stage: canary ≥20 seeds at one
  cell + onset-curve re-readout, then stop and report.

## Report-immediately triggers

- Events firing at ≫1 per voyage under mid-interval parameters — the
  detector is firing per-epoch or per-diner instead of per-window.
- `common_source_food` carrying >50% of transmissions at default
  intervals — over-delivery, revisit the titre/mass intervals before any
  campaign.
- Zero events under forced `lot_event_probability = 1` — the init-time
  draw or scheduling is dead.
- Any dose credited to an agent absent from the event zone/window, or a
  cohort larger than the venue's seated capacity — a bug, not a result.
- Realized source mix wildly off the Clough prior (47 handler : 27
  at-source definite) across a canary — a detector asymmetry, not a
  finding.
