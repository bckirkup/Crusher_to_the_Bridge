# Ship Function Capacity, Maintenance Degradation, and Wear-Fatigue Channels

> **Status:** Proposed. Nothing in this document describes current behaviour.
> The seams it names exist and are identified by their in-tree identifiers; the
> mechanisms specified in §§3–8 do not exist.

## 1. Why this document exists

Two questions came up together:

1. Can the model assess *ship functions* — food service, housekeeping,
   engineering watch, fishing operations on a fishing platform — as a function
   of crew illness and ship maintenance state?
2. Can the biological-hazard machinery extend to environmental hazards
   (chemical releases, sustained contaminant exposure)?

The answer to both is that most of the required *inputs* are already
first-class simulation state, and the machinery that consumes the outputs —
coverage maps, route scalars, zone closures, susceptibility multipliers —
already exists. What is missing is: a declaration of what a "function" is, a
ship-systems health model (the only genuinely new engine), the per-epoch
capacity readout, the feedback writers that connect capacity to existing
inputs, and a fatigue accumulator for sustained PPE wear.

This spec fixes the data model and the seams before any implementation. It
adopts no constants and authorises no fit.

## 2. What the tree does today

### 2.1 Crew availability is already observable state

Every ingredient of "which crew are actually working this epoch" exists:

- `KorkinAgent` carries `role`, `agent_class`, `work_zone`/`duty_zone`,
  `home_zone`, `dining_zone`, `free_zone`, and an hourly `schedule` whose
  `"Work"` tokens define the shift (`engines/infection_dynamics_bridge.py`).
- `TransmissionCore._on_service_duty` already distinguishes a crew member on
  shift in a service zone from the same crew member at a meal or off watch —
  the channel is the duty *state*, not the room
  (`tests/test_food_service_duty_state.py`).
- `engines/crew_duty_exclusion.py` tracks VSP-mandated removal:
  `excluded_ids`, `food_employee_ids`, the 48 h food-employee / 24 h
  non-food durations, a compliance arm, and release logic that respects
  *other* confinement holds (`_release_cleared_crew`). Exclusion writes into
  `state.quarantined_ids`, so confinement relocation comes free.
- Symptomatic presentation (`agent_has_symptomatic_presentation`) and the
  reporting ladder (`ever_reported_ids`) are per-epoch queryable — and the
  distinction matters: symptomatic-but-unreported crew are *present but
  impaired*, not absent (§4).
- The agent-class taxonomy (`ship_graph.agent_classes` in
  `crusher_labs/config.yaml`: `crew_galley`, `crew_medical`,
  `crew_engineering`, `crew_general`, each with `duty_zone` and named
  schedule templates with `watch_sections`/`night_watch_fraction`) is
  platform-declared. Non-cruise platforms (destroyer, LPD, Enterprise
  bundles) declare their own classes and duty zones — the function registry
  in §3 must resolve against whatever the platform declares, not against a
  fixed cruise taxonomy.

### 2.2 OIS is a scorer, not a capacity model

`compute_operational_impact` + `CostLedger.accumulate_operational_impact` +
`step_operational_impact_accounting` accumulate a per-epoch degradation
score — `per_essential_crew_quarantined`, `per_closed_galley_zone`,
`per_passenger_quarantined`, fleet-PPE weight — that flows into
`decision_engine/utility/features.py` and the economics valuations
(`picard_framework/analysis/economics/valuations.py`). It *counts* degraded
inputs; it does not model *capacity*. "Can the galley still serve dinner" is
a different question from "how many galley crew are quarantined" — the first
needs staffing requirements, redundancy, and system state; the second is one
term of the first.

The OIS call site — `_step_record`, after `step_crew_duty_exclusion` and
`step_quarantine_confinement` — is exactly where a capacity readout belongs:
it reads post-confinement state, same inputs, same breakdown discipline.

### 2.3 The write seams exist

Degraded functions feed back through inputs the engines already read:

- `merged_modifiers` / protocol `route_scalars`
  (`direct_contact_scalar`, `droplet_scalar`, `hvac_airborne_scalar` on
  `TransmissionCore`, applied multiplicatively at SOP activation),
  `close_zones` → `apply_zone_closures` relocates agents to home zones,
  `zone_occupancy_cap`.
- Surface cleaning is a *static* config map:
  `transmission.surface_cleaning.routine_coverage_by_item_class` in
  `engines/fomite_surfaces.py` attenuates fomite reservoir growth per item
  class. Degraded housekeeping is one indirection: effective coverage =
  declared coverage × staffing capacity.
- Dining allocation is already a platform data model:
  `dining_meal_weights` and `dining_service_type`/`food_contamination_multiplier`
  in `voyage_config.json` / zone records (`ship_operations_spec.md`,
  multi-pathogen §4), consumed by itinerary effects and
  `get_location_for_hour`. Degraded food service is a weight shift, not a
  new pathway.
- `data/config/protocols.json` already carries `costs_per_epoch` with
  `labor_person_hours` — labor bookkeeping exists; it is spend, not
  availability.

### 2.4 Per-agent modulation fields are live

`KorkinAgent` already carries per-pathogen modulation state:
`susceptibility_multiplier` (written by
`engines/pharmaceutical_interventions.py` for prophylaxis acquisition
protection, read in `_merge_pathogen_doses`), `dose_response_susceptibility`
(lazy β-Poisson mixing draw), `frailty_multiplier` (FRAILTY-V1 lazy draw),
`cumulative_exposure`, and the hygiene/hand-state dicts. A fatigue→risk
channel is a writer into `susceptibility_multiplier` — the same path
prophylaxis already uses — not a new field family.

### 2.5 PPE is a fleet scalar today

SOP-004/005 deploy PPE as protocol modifiers (`ppe_transmission_reduction` +
per-route scalars) applied fleet-wide; `non_pharmaceutical_interventions.py`
adds declared per-route dose fractions with a **role coverage map**. There
is no per-agent PPE state, no wear-duration tracking, and no fatigue or
adherence-decay concept. `fatigue` does not appear in the engine vocabulary
at all.

### 2.6 Environmental sources already exist

Multi-pathogen §3 landed: `TransmissionCore.env_contamination` holds
per-pathogen per-zone reservoir mass, the `environmental_source` pathway is
a registered route (`DEFAULT_ROUTE_EFFICIENCY` key), and profiles may
declare `environmental_source` blocks with source zones and emission rates.
Pathogens run as independent concurrent instances with `introduction_epoch`
mid-cruise starts. A chemical hazard's *transport* problem is already
solved; §8 specifies only what remains.

### 2.7 What is absent

- No ship-systems model. "Maintenance" exists only as a ledger cost line
  (`debit_per_test`/`costs_per_epoch` maintenance entries). No system has a
  health state; nothing degrades; nothing is repaired.
- No per-function declaration or capacity readout.
- No fatigue accumulator or wear-hour tracking.
- No mechanism for an absent-but-working distinction (symptomatic
  unreported crew) to degrade a function.

## 3. The function registry

A new `ship_functions` block, declared per platform — in
`data/platforms/<platform>/voyage_config.json` beside `medical_response`,
deep-mergeable via `config_overrides` like `voyage`. Function IDs are
free-form; the registry is platform-agnostic by construction.

Function *vocabulary* is shared across vessel classes — what differs is
which *instances* of each kind a vessel carries and who they serve.
`(function_id, serves)` is the instance key, not `function_id` alone: a
cruise ship carries `food_service` **twice** — `serves: passengers`
(thousands of covers across venue tiers) and `serves: crew` (the crew
mess, feeding the staff themselves) — while a fishing boat carries only
the `crew` instance. What reads as a cruise-unique function is not a
different kind: `entertainment`, `cabin_housekeeping`,
`passenger_food_service` are instances whose `serves` population the
vessel lacks, so a platform with no passengers simply declares no
passenger-serving instances. `serves` takes `passengers` | `crew` |
`both` | `mission` (mission = the vessel's work itself: engineering watch,
fishing ops, flight ops — operational readout and inter-function
dependency, not population behaviour).

Two consequences. Instances of one kind need not share parameters: the
cruise `food_service:serves=passengers` instance needs galley crew across
venue tiers and Dining zones; the `food_service:serves=crew` instance
needs the same `crew_galley` class at mess scale — and that is a **shared
staffing pool**: two instances drawing on `crew_galley` compete for the
same watches, so capacity is scored against summed demand across all
instances a class staffs, never each instance against the pool in
isolation (§4). And `crew`-served functions are the subtle ones: the crew
they feed is also the crew that staffs every other function, so a dead
crew mess on a fishing boat degrades `fishing_ops` one step removed (§6.2
second-order channel) — the crew has nowhere else to eat.

```json
"ship_functions": {
  "enabled": false,
  "functions": [
    {
      "function_id": "food_service",
      "serves": "passengers",
      "staffing": {
        "crew_galley": {"required_on_watch": 6, "minimum_on_watch": 2}
      },
      "required_zone_types": ["Galley"],
      "required_systems": ["galley_power", "refrigeration"],
      "capacity_model": "staffing_fraction",
      "feedback": {
        "kind": "dining_weights",
        "degraded_weights": {"buffet": 0.0, "mdr": 0.4, "room_service": 0.6},
        "zone_close_on_loss": []
      }
    },
    {
      "function_id": "food_service",
      "serves": "crew",
      "staffing": {
        "crew_galley": {"required_on_watch": 1, "minimum_on_watch": 1}
      },
      "required_zone_types": ["Mess", "Dining"],
      "required_systems": ["refrigeration"],
      "capacity_model": "bottleneck_min",
      "feedback": {"kind": "readout_only"}
    },
    {
      "function_id": "housekeeping",
      "serves": "passengers",
      "staffing": {"crew_general": {"required_on_watch": 8}},
      "required_zone_types": ["Cabin_Corridor"],
      "required_systems": [],
      "capacity_model": "staffing_fraction",
      "feedback": {
        "kind": "cleaning_coverage_scale"
      }
    },
    {
      "function_id": "entertainment",
      "serves": "passengers",
      "staffing": {"crew_general": {"required_on_watch": 4}},
      "required_zone_types": ["Theater", "Pool_Deck"],
      "required_systems": [],
      "capacity_model": "staffing_fraction",
      "feedback": {"kind": "readout_only"}
    },
    {
      "function_id": "engineering_watch",
      "serves": "mission",
      "staffing": {"crew_engineering": {"required_on_watch": 3, "minimum_on_watch": 1}},
      "required_zone_types": ["Engine"],
      "required_systems": ["propulsion"],
      "capacity_model": "bottleneck_min",
      "feedback": {"kind": "readout_only"}
    },
    {
      "function_id": "navigation",
      "serves": "mission",
      "staffing": {"crew_deck": {"required_on_watch": 3, "minimum_on_watch": 1}},
      "required_zone_types": ["Bridge"],
      "required_systems": ["propulsion"],
      "capacity_model": "bottleneck_min",
      "feedback": {"kind": "readout_only"}
    }
  ]
}
```

A fishing platform declares the same vocabulary — `food_service` in its
only instance, crew-served and non-optional — and its own mission
functions alongside the universal navigation/engineering core:

```json
"functions": [
  {
    "function_id": "food_service",
    "serves": "crew",
    "staffing": {"crew_galley": {"required_on_watch": 1, "minimum_on_watch": 1}},
    "required_zone_types": ["Galley", "Mess"],
    "required_systems": ["refrigeration"],
    "capacity_model": "bottleneck_min",
    "feedback": {"kind": "readout_only"}
  },
  {
    "function_id": "navigation",
    "serves": "mission",
    "staffing": {"crew_deck": {"required_on_watch": 2, "minimum_on_watch": 1}},
    "required_zone_types": ["Bridge"],
    "required_systems": ["propulsion"],
    "capacity_model": "bottleneck_min",
    "feedback": {"kind": "readout_only"}
  },
  {
    "function_id": "engineering_watch",
    "serves": "mission",
    "staffing": {"crew_engineering": {"required_on_watch": 1, "minimum_on_watch": 1}},
    "required_zone_types": ["Engine"],
    "required_systems": ["propulsion"],
    "capacity_model": "bottleneck_min",
    "feedback": {"kind": "readout_only"}
  },
  {
    "function_id": "fishing_ops",
    "serves": "mission",
    "staffing": {"crew_deck": {"required_on_watch": 4, "minimum_on_watch": 2}},
    "required_zone_types": ["Fishing_Deck"],
    "required_systems": ["winch", "fish_hold_refrigeration"],
    "capacity_model": "bottleneck_min",
    "feedback": {"kind": "readout_only"}
  },
  {
    "function_id": "catch_processing",
    "serves": "mission",
    "staffing": {"crew_processing": {"required_on_watch": 3}},
    "required_zone_types": ["Factory_Deck"],
    "required_systems": ["processing_line"],
    "capacity_model": "staffing_fraction",
    "feedback": {"kind": "readout_only"}
  }
]
```

Rules:

- **`serves`** takes `passengers` | `crew` | `both` | `mission`: which
  population draws on the function. The axis resolves the vessel-class
  question into three layers: **`mission` is the universal core** —
  navigation and engineering exist on every powered vessel, whatever else
  it carries; **`crew` is the universal sustenance layer** — every crewed
  vessel feeds and berths its own; **`passengers`/`both` appear only where
  a passenger population exists**, so `entertainment` and cruise dining
  are cruise instances of kinds, not cruise kinds. A vessel's function set
  is thus completely described by `serves` coverage — no new
  function-specific code between platform families. `mission` marks
  functions whose output is the vessel's work itself — their degraded
  feedback is operational readout and inter-function dependency, not
  population behaviour. `crew`-served functions are the subtle ones: the
  crew they feed is also the crew that staffs every other function, so a
  dead galley on a fishing boat degrades `fishing_ops` one step removed
  (§6.2 second-order channel).
- **Staffing resolution.** A function names the `agent_class` IDs that staff
  it — resolved against the platform's own `agent_classes` block, not a
  built-in list. Legacy binary platforms (passenger/crew only) may instead
  declare `staffing_by_duty_zone: {"Galley": {...}}`, resolved through each
  crew agent's `duty_zone`/`work_zone`. The two modes are exclusive per
  function.
- **`required_zone_types`** are matched against zone `type` (the
  `zone_type_by_id` map already passed to
  `step_operational_impact_accounting`), or explicit zone IDs via
  `required_zone_ids`. A closed zone (`merged_modifiers.close_zones`,
  SOP-009 path) is an unavailable zone.
- **`required_systems`** reference the systems model in §5.
- **`capacity_model`** is the aggregation rule: `staffing_fraction`
  (capacity = available/required, capped at 1) or `bottleneck_min`
  (capacity = min over all constraints — one missing watch-stander or one
  dead system zeroes the function). A function may declare a
  `capacity_schedule` for time-varying demand (galley peak at meal epochs).
- **`feedback.kind`** selects the writer in §6; `readout_only` means the
  function's capacity is scored and telemetered but writes nothing back.
- **Validation.** The data-contracts layer (`testing-data-contracts`,
  `tools/sanity_checker.py` categories, `test_json_schema_validation.py`)
  gains referential checks: every `staffing` class exists in the platform's
  `agent_classes`, every zone type/id exists in `spatial_layout.json`,
  every system exists in `ship_systems`. An unresolved reference is a load
  error, not a warning — silent partial functions are how campaigns lie.
- **Default.** `enabled: false`; an absent block must leave every seeded
  run bit-identical (the proposals-README discipline), matching the
  `voyage.effects_enabled` precedent.

## 4. The availability read

One predicate, defined once, consumed by every function:

```python
def available_for_duty(agent, epoch, state, exclusion_tracker) -> DutyState:
    """Absent entirely vs. present-but-impaired vs. fit."""
```

returns `ABSENT` when the agent is in `excluded_ids`, `quarantined_ids`,
`isolated_ids`, or on a non-Work schedule token; `IMPAIRED` when on-watch
but symptomatic (presented or unreported — the sick-call ladder is
*detection*, not physiology; a crew member vomiting at their station is
still at their station until reported and excluded); `FIT` otherwise.

`IMPAIRED` maps to a declared `symptomatic_effectiveness ∈ [0,1]` on the
function's staffing entry — how much of a shift a symptomatic crew member
delivers. No source exists; it ships as a declared operational arm defaulting
to a stated value, swept in campaigns, never tuned to an anchor — the same
discipline `crew_duty_exclusion.compliance_fraction` documents in its
module header.

`on_watch` resolution reuses the schedule/`_on_service_duty` logic; it does
not reimplement it. Functions that need "on watch *and* at a duty zone" use
the class's `duty_zone`; generic watch functions use the schedule token
alone (a galley worker off shift in the crew mess is not staffing the
galley).

Because `(function_id, serves)` instances share crew classes, the read
computes class pools once per epoch — `fit_in_pool[class]`,
`impaired_in_pool[class]` — then scores each instance against the *summed*
`required_on_watch` of every instance that draws that class. The cruise
example's two `food_service` instances both draw `crew_galley`: passenger
dining and the crew mess compete for the same galley watches, so a galley
shortfall hits both capacities jointly rather than each reading the pool as
if it were private.

## 5. Ship systems and maintenance

The one new engine. `engines/ship_systems.py`: a small registry of named
systems with health state, beside `crew_duty_exclusion.py` in ownership
style — data and transitions, no epidemiological content.

```json
"ship_systems": [
  {
    "system_id": "refrigeration",
    "health_start": 1.0,
    "degradation": {"rate_per_day": 0.005, "model": "linear"},
    "repair": {"labor_class": "crew_engineering", "rate_per_person_hour": 0.02},
    "failure_threshold": 0.3,
    "effects": {"food_service": {"capacity_multiplier_at_failure": 0.0}}
  }
]
```

- `health ∈ [0,1]` degrades at the declared rate while the simulation runs
  and is repaired by labor drawn from `available_for_duty` crew of the named
  class — this is where the staffing read and the systems model meet:
  repairs consume watch-hours, so a depleted engineering watch both loses
  the `engineering_watch` function *and* falls behind on repairs, which
  cascades into every function depending on that system.
- Below `failure_threshold` the system is failed; `effects` declare what
  each dependent function's capacity multiplies by (0.0 = the function is
  dead until repaired).
- Initial health, degradation rates, and repair rates are **declared
  operational parameters with a provenance grade at definition**, never
  fitted — same register discipline as any constant. Where no maritime
  source exists the entry carries its null-source declaration, the
  `medical_clearance_delay_hours` precedent.
- Maintenance *prioritization* (which system gets repair labor when several
  are degraded) is a policy — the decision-engine seam exists
  (`decision_engine/policy.py`, `protocol_filter`), and the Stackelberg
  authorization path (`authorize_sop_subset`) could gate whether repair
  allocation is operator-chosen. v1 ships a declared `repair_priority`
  ordering on the block; policy-driven allocation is a follow-on, not a
  blocker.

## 6. Capacity readout and feedback writers

### 6.1 The epoch step

`step_ship_function_capacity` runs in `_step_record` alongside
`step_operational_impact_accounting` — after confinement and duty exclusion
have settled, before `record_epoch` — and emits:

```json
"function_capacity": {
  "food_service": {"capacity": 0.67, "binding": "staffing",
                   "available_on_watch": 4, "required_on_watch": 6},
  "housekeeping": {"capacity": 1.0, "binding": null}
}
```

into the epoch record / ledger epoch summary (the OIS precedent), so
telemetry, the dashboard, `decision_engine/utility/features.py`, and the
economics valuations all consume it without new plumbing. A function's
capacity, not a score: capacity is per-function and interpretable, which is
what downstream consumers (utility features, campaign readouts) can weight.

### 6.2 Feedback writers

Each `feedback.kind` is a declared writer into an existing input seam:

| kind | Writes | Consumed by |
|------|--------|-------------|
| `cleaning_coverage_scale` | effective coverage = declared `routine_coverage_by_item_class` × housekeeping capacity | `fomite_surfaces` reservoir growth |
| `dining_weights` | swaps `dining_meal_weights` to `degraded_weights` below a declared capacity threshold | `get_location_for_hour` / voyage dining layer |
| `zone_modifiers` | emits `close_zones`/`zone_occupancy_cap` entries into `merged_modifiers` when capacity hits a declared threshold | `apply_zone_closures`, occupancy caps |
| `route_scalar_scale` | recomputes a named `*_scalar` on `TransmissionCore` from capacity each epoch | dose pathways |
| `readout_only` | nothing | — |

Writer rules, because this is where the loop can go wrong:

- **Writers write inputs; engines own physics.** A feedback writer never
  introduces a dose term or a contact kernel — it sets values in slots the
  engine already reads (coverage map, weights dict, modifier list, scalar
  attribute). New physics is a separate proposal.
- **Scalars are recomputed, not compounded.** SOP route scalars multiply
  cumulatively at activation (`setattr(tx_core, ch, attr * scalar)`); a
  capacity-driven scalar must instead store the epoch-computed absolute
  value, or the ship drifts a few percent per epoch with no protocol ever
  firing. The writer restores the baseline before applying its own value —
  the identity behavior an absent block already guarantees.
- **Thresholded, not continuous, by default.** `dining_weights` and
  `zone_modifiers` fire on declared capacity thresholds (e.g. "below 0.5
  sustained for 4 epochs → buffet closes"), matching the SOP/stoplight
  convention of discrete operational states; continuous modulation stays on
  `cleaning_coverage_scale`/`route_scalar_scale` where the consumer is
  already a smooth input.
- **`crew`-served functions get a second-order staffing channel.** When a
  crew-served function degrades (galley down, mess closed), its consumers
  *are the staff*: missed or degraded meals accumulate on the serving crew
  as a `sustenance_deficit` — a declared input to the fatigue accumulator
  in §7 (the same write any other fatigue source makes) and, if the
  platform declares it, to `symptomatic_effectiveness`-style impairment in
  §4. This is how a fishing boat's dead galley propagates into
  `fishing_ops` without any function named "morale". The channel is
  declared per function (`feedback.crew_sustenance: true`) and defaults
  off — a cruise ship's passengers are not a staffing input, and enabling
  it there would silently couple the passenger outbreak into crew
  performance, which is exactly the kind of unscoped widening the registry
  exists to prevent.
- **Feedback is optional per function and off with the block.** A platform
  with `ship_functions.enabled: false` is the labelled baseline; each
  function's `feedback` may additionally be disabled to run
  readout-but-no-feedback arms (capacity measured, behavior unchanged —
  the canary configuration for attribution).

## 7. PPE wear-fatigue channel

Sustained PPE use degrades the wearer: fatigue, reduced compliance, and —
the user's specific mechanism — elevated risk of secondary conditions
(mask/respirator microclimate → sinonasal complaints; occlusion/friction →
skin barrier damage and infection). The channel is additive pieces, each
riding an existing pattern.

### 7.1 The PPE type registry

PPE is not one object. Surgical masks, N95/FFP respirators, powered
air-purifying respirators (PAPR), latex/nitrile gloves, and chemical gloves
differ on every axis the model cares about, so the unit of declaration is
a `ppe_types` registry in the protocol/NPI config:

```json
"ppe_types": {
  "surgical_mask": {"fatigue_rate_per_epoch": 0.2, "heat_load": 0.1,
                    "dexterity_impairment": 0.0},
  "n95":            {"fatigue_rate_per_epoch": 0.5, "heat_load": 0.3,
                    "dexterity_impairment": 0.0},
  "papr":           {"fatigue_rate_per_epoch": 0.8, "heat_load": 0.6,
                    "dexterity_impairment": 0.15},
  "latex_gloves":   {"fatigue_rate_per_epoch": 0.1, "heat_load": 0.0,
                    "dexterity_impairment": 0.1},
  "chemical_gloves":{"fatigue_rate_per_epoch": 0.3, "heat_load": 0.2,
                    "dexterity_impairment": 0.3}
}
```

- **Protection stays where it is.** Efficacy remains on the protocol —
  SOP-004/005's `ppe_transmission_reduction` and route scalars — but the
  NPI measure's coverage map keys each covered class/role to a `ppe_type`
  (medical staff → `n95` + `latex_gloves`; cleanup detail →
  `chemical_gloves`; a chemical-release SOP would draw from the same
  registry for PAPR/respirator, §8). Legacy measures with no type declare
  a platform-default type so existing campaigns are unaffected.
- **Fatigue is per-type.** `fatigue_rate_per_epoch` replaces the per-
  protocol `ppe_fatigue_rate_per_epoch` shorthand from v1 of this spec —
  the registry is where the ordering (PAPR > N95 > surgical is a declared
  ordering, not a shipped number) lives, and an agent covered by several
  types at once accumulates their sum.
- **`dexterity_impairment` feeds back into §4/§5 capacity** — it scales the
  effective watch-hours an impaired wearer delivers to functions needing
  manual work (repair labor in §5 most directly): an engineer in PAPR and
  chemical gloves repairs slower. This is the loop the fatigue channel
  otherwise misses: stricter PPE during an outbreak *itself* degrades
  maintenance capacity, which degrades systems, which degrades functions.
- **Secondary conditions are type-keyed** (§7.4): each type may declare
  its own `fatigue_conditions` profile — occlusion dermatitis on gloves,
  sinonasal complaints on respirators, heat stress on PAPR — rather than
  one pooled risk.

### 7.2 The accumulator

`KorkinAgent.ppe_wear_hours` becomes `ppe_wear_hours_by_type`: incremented
each epoch the agent is under an active PPE protocol **and** covered by
it — NPI measures already carry the coverage map (now typed), so coverage
is read not assumed. The accumulator contribution is Σ hours × type
`fatigue_rate_per_epoch`; absent type = zero fatigue, so legacy protocols
are unaffected.

Wear-hours is one *input* to fatigue, not fatigue itself. The accumulator
is `fatigue_score`, fed by declared sources: PPE wear (this section) and
the `sustenance_deficit` a degraded crew-served function writes (§6.2).
Keeping the accumulator a sum of declared contributions — rather than a
PPE-specific counter — is what lets the same downstream consumers
(§7.3 compliance, §7.4 conditions) read one number whatever produced it.

### 7.3 Fatigue → compliance decay

The refuser/compliance pattern already exists
(`CrewDutyExclusionTracker.complies()` sticky draws,
`state.quarantine_refusers`, `compliance_log`, FRED bimodal classes). Wear
fatigue modulates *effective coverage*: above a declared
`fatigue_refusal_threshold`, covered agents draw refusal on the declared
`fatigue_refusal_probability_per_epoch` — a refuser's host-level NPI
reductions drop out for subsequent epochs. The sticky-draw convention and
the compliance log give the audit trail for free.

### 7.4 Fatigue → secondary conditions

Type-keyed, as §7.1 declares — a type's `fatigue_conditions` block names
only the sequelae it plausibly induces. Two honest variants, picked per
condition by mechanism:

- **Endogenous (non-transmissible) condition.** Sinonasal symptoms or skin
  barrier damage that is not infectious: wear-hours drive a per-epoch
  incidence rate on a declared `fatigue_conditions` block
  (`condition_id`, `rate_per_wear_hour`, `symptomatic: true`). Onset writes
  the agent into the *existing* symptomatic-presentation path, so
  sick-call, duty exclusion, VSP counters, and OIS all see it with zero new
  machinery. This is the recommended variant for PPE sequelae.
- **Transmissible secondary pathogen** (e.g. a skin staph that then
  spreads): a normal pathogen profile — zero-shedding is expressible
  (`shedding_curve` flat at baseline, or a profile declaring no shedding
  routes) — plus wear-hours mapped onto
  `agent.susceptibility_multiplier[pathogen_id]` via a declared
  `fatigue_susceptibility` map. This is the write `pharmaceutical_interventions`
  already performs, pointed the other direction; the dose machinery,
  natural history, and cascade all run unchanged.

Both variants are declared per pathogen/condition with sources where the
literature supplies them (mask-associated acne/dermatitis, sinonasal
symptom rates) and null-source declarations where it does not. No new dose
constant may be fitted to an anchor — the register's rules apply unchanged.

## 8. Environmental hazards (adjacent extension)

The chemical-hazard question lands almost entirely on shipped machinery;
the missing pieces are named here so the hazard work, when scoped, does not
re-litigate transport:

- **Exists**: per-profile independent mass pools per zone, substance decay
  constants, CONTAM/native HVAC transport, fomite deposition,
  `environmental_source` zone reservoirs (multi-pathogen §3, implemented),
  `introduction_epoch` scheduling, the strain-resolved dose ledger, and a
  profile-pluggable `dose_response.model`.
- **Missing, and additive**: (a) a non-infectious effect arm —
  cumulative-exposure toxicity (Haber c·t or a threshold model) as a
  `dose_response` variant producing presentation/incapacitation without
  incubation or shedding; reusing the symptomatic state buys sick-call,
  exclusion, and OIS for free; (b) detection that is not a pathogen assay —
  the `air_sniffer_sample`/surface-swab modality surfaces generalize to
  chemical sensors, wastewater sequencing does not; (c) naming — a
  `category: "chemical"` profile is honest even though the files say
  `pathogens`, or a `data/hazards/` directory with the same schema.

That work is a separate proposal; this spec only fixes that function
capacity and fatigue reads must be **hazard-agnostic** — they read
symptomatic/absent/covered state, never pathogen IDs — so a chemical
incapacitation feeds `available_for_duty` identically to a norovirus one.

## 9. Staging

1. **Readout first.** Function registry + availability read + capacity
   telemetry + schema validation, `enabled: false`. No feedback, no
   systems. This is the instrumentation lesson: the metric the campaign
   must answer must exist before the campaign.
2. **Ship systems** (`ship_systems` + repair-labor draw + failure effects).
3. **Feedback writers**, one `kind` per PR, `cleaning_coverage_scale`
   first — it is the smallest closed loop (staffing → coverage → fomite
   reservoir → dose).
4. **Fatigue channel** (accumulator → compliance decay → condition arms).
5. Hazard arm last and separately specced — it needs §8(a)/(b), none of
   which this spec implements.

Each stage is its own PR with `enabled: false` shipped semantics; capacity
arms and feedback arms are selectable per campaign via `config_overrides`.

## 10. Non-goals and discipline

- No epidemiological constant is added, moved, or fitted here. Degradation
  rates, repair rates, `symptomatic_effectiveness`, fatigue rates, refusal
  probabilities, and condition incidences are **operational declarations**:
  they carry sources or explicit null-source declarations at definition,
  they may be swept, and they may not be tuned to VSP/attack-rate/passenger
  anchors. The provenance register's rules apply verbatim.
- No pathogen physics changes. Writers touch input slots only.
- Absent `ship_functions`/`ship_systems`/fatigue blocks must leave all
  seeded runs bit-identical.
- `proposals/` filing rule: this document moves to `docs/` root when the
  registry and readout (stage 1) exist in-tree.
