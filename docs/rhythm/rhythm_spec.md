# Rhythm layer spec — schedule-conditioned co-presence (SHIP-RHYTHM-01)

> **Status:** Implemented, on by default — SHIP-RHYTHM-01/02,
> `engines/rhythm_layer.py` over `data/rhythm/event_catalogs.json`
> (`rhythm.enabled: false` is the labelled baseline; catalogued cruise
> platforms only — hulls without a catalog entry stay on the baseline
> regardless of the flag). Register rows:
> `docs/parameter_provenance_register.md` §3.6.

This document specifies the daily-rhythm layer the two failure ledgers ask for.
[COVID-TAKEOFF-ATTR-01](../ledger/COVID-TAKEOFF-ATTR-01.md) measured the model's
per-epoch dosed sets at a median 705 hosts with `challenged_share_of_aboard`
pinned at 1.0 on every seed — real exposure sets are bounded and bursty, not
ship-wide and stationary. [NORO-GROWTH-01](../ledger/NORO-GROWTH-01.md) measured
secondary emesis landing in cabins whose only occupants are already immune —
real vomit placement is conditioned on schedule, not independent of it. The
mechanism that produces both properties on a real ship is the **daily program**:
a printed timetable (Princess Patter / Freestyle Daily class documents) that
places hundreds of passengers in the same room at the same clock time and pours
them out together when the event ends.

The layer described here replaces independent per-epoch location draws with
**schedule-conditioned location selection**: agents are assigned to events at
day start, events own their occupants for their windows, and window endings
generate correlated corridor fronts.

## 1. Data foundation

`data/rhythm/event_catalogs.json` carries the transcribed timetables. Every
timetable entry is traceable: either to a named document in the file's
`documents` table (all Tr-class primary sources — scanned or text-extractable
daily programs archived publicly), or to an explicit `class: "notional"` marker
with a `construction_rule` stating how the entry was assembled. Summary of
document coverage:

| Ship-class catalog | Platforms | Documents | Coverage |
|---|---|---|---|
| `mega_cruise` | `mega_cruise_5000` | Sun Princess Patter (sea), Majestic Princess Patter (port), NCL Escape Freestyle Daily (embarkation) | sea, port, embark documented; disembark notional |
| `contemporary_cruise` | `spirit_cruise_3000` | HAL Nieuw Amsterdam THE DAILY (port) + HAL Volendam (sea structure) | sea/port documented; embark/disembark notional |
| `classic_cruise` | `classic_cruise_1900` | HAL Volendam THE DAILY (sea + tender port) | sea, port documented; embark/disembark notional |
| `expedition_cruise` | `expedition_cruise_450` | Silversea Chronicles, Silver Dawn (port, overnight) | port documented; sea/embark/disembark notional-from-documented-hours |
| `starship_galaxy` | `enterprise_galaxy_tng` | `class: notional` — canonical three-watch convention | all notional |
| `starship_constitution` | `enterprise_constitution_tos` | `class: notional` — same convention, all-crew | all notional |

Naval platforms (`destroyer_baseline`, `fletcher_class_destroyer`,
`legend_class_nsc`, `san_antonio_class_lpd`) and legacy hulls
(`messy_cruise_500`, `expedition_cruise_300`) are **out of scope** for this
task; naval watch structure is already covered by SCHED-WATCH-01 (#723).

## 2. Event-class taxonomy

Every catalog entry has an `event_class`; the class fixes participation draw
semantics and egress coupling:

| Event class | Semantics | Egress |
|---|---|---|
| `meal_seating` | Agent eats at the venue for `occupancy_share` of the window; seating stagger inside the window is delegated to the existing `stagger_meal_seating` | `synchronized_end` for MDR seatings, `rolling` for buffets |
| `show_performance` | Captive seated attendance for ~the whole window | `synchronized_end` — the strongest pour-out source |
| `scheduled_activity` | Timed participatory blocks (trivia, classes, lectures) | `synchronized_end` |
| `open_venue` | Posted-hours continuous venues (casino, pool, spa, shops, lounges) | `rolling` — no coherent front |
| `embarkation_flow` | Boarding surge; every passenger passes through the gangway once | `rolling` (arrival-poisson) |
| `disembarkation_flow` | Staggered off-load by group call | `windowed` |
| `port_call` | Gangway/tender open window; participation = going ashore | `windowed` (deadline-driven return front) |
| `watch_turnover` | Crew watch-section boundaries; off-going section egresses to cabins/mess as on-coming occupies posts | `synchronized_end` |
| `cleaning_rotation` | Crew service passes through cabin corridors and public venues | `rolling` |
| `queue_event` | Front events that pack a corridor/lobby (tender tickets, muster, photo ops, excursion dispatch) | `windowed` |

## 3. Per-class fields

Each catalog event carries:

- `window`: `[start, end]` ship-local. Windows may wrap midnight.
- `venue_roles` → resolved to zone ids by the catalog's `venue_map`
  (verbatim zone ids from `data/platforms/*/spatial_layout.json`).
- `eligible`: `role_groups` and, where relevant, `classes`. **Engine-room,
  bridge, galley, and crew-mess venues are class-scoped**: only duty-posted
  crew classes (`crew_engineering`, `crew_galley`, watch classes on
  starships) may be assigned to them; `cleaning_rotation` is restricted to the
  housekeeping/services classes. Passengers are never eligible for
  `crew_mess`/`watch_turnover`/`cleaning_rotation` events.
- `participation_fraction`: per-occurrence Bernoulli draw over the eligible
  population (per-day for events occurring once). For `open_venue` this is
  the probability of visiting at all during the window; dwell inside is
  `occupancy_share` of the window.
- `occupancy_share`: fraction of the window a drawn participant spends in the
  venue; `1.0` for watch/muster.
- `egress_mode`: `synchronized_end` | `rolling` | `windowed`.
- `source`: document citation with an evidence line, or
  `{class: "notional", rule: ...}`.

## 4. Occupancy model

### 4.1 Day-template selection and assignment

Each epoch carries a day type from the voyage itinerary
(`sea_day`, `port_day`, `embarkation`, `disembarkation` — the existing
`voyage` block's day types) and an SOP state. The active template is
`baseline_day_templates[day_type]` transformed by the active `sop_variant`.

At the first epoch of each ship day (or at embarkation), every agent is dealt
an **itinerary**: for each event in the template for which the agent is
eligible, a Bernoulli(`participation_fraction`) draw decides attendance.
Draws are per-agent and independent across events, with the constraint that
overlapping committed events are resolved by priority
(`meal_seating` > `watch_turnover`/`duty` > `show_performance` >
`scheduled_activity` > `queue_event` > `open_venue`) — an agent assigned to
two overlapping events occupies the higher-priority one.

During an epoch, an assigned agent occupies the event venue. An unassigned
agent falls back to the existing location logic: sleep window → cabin;
Free hours → `free_zone_rotation_probability` / `weighted_zone_choice`;
Work → `duty_zone`. **The rhythm layer partitions the Free block**: inside a
committed event window the event wins; between events the old draw applies.

### 4.2 The pour-out mechanism

Every `synchronized_end` event ends on a shared clock: at `window.end`, all
occupants egress over an **egress front** of duration `egress_front_minutes`
(default interval in §3.6). During the front, egressing agents occupy the
venue's `transit` corridor zones (`gangway_corridor`, `promenade`,
`cabin_corridor` as mapped) before re-resolving to their next location.
Consequences, by construction:

- corridor occupancy spikes are *correlated with the program clock* — the
  19:30 and 21:00/21:30 show endings and the post-dinner seating ends are the
  dominant fronts, each flushing hundreds of agents through the same few
  corridors within ~15 minutes;
- exposure sets become **bounded**: the set of agents sharing a venue during
  an event is the attendance draw (≤ venue capacity), not the ship;
- exposure sets become **bursty**: between fronts, corridors carry only
  rolling-venue and transit traffic.

### 4.3 Sleep and between-event fill

Outside events, the existing `Sleep` token already drives cabin occupancy;
the layer adds a sleep-window occupancy curve so that "in cabin" has a
time-of-day profile rather than a binary token edge. Anchored to ATUS
share-asleep-by-clock-hour (Basner et al. 2007; Davis et al. 2023): the
fraction asleep/in-cabin is near-unity over ~01:00–05:00 and falls to a
shoulder by ~07:00–09:00. Crew curves are shifted by watch section
(gamma-section crew sleep 09:00–15:00 class off-watch window under the
three-watch convention; cruise hotel crew get the MLC 2006 Regulation 2.3
rest floor of ≥10 h per 24 h, modelled as a declared off-duty cabin block).

### 4.4 Port-day occupancy

On `port_day` the gangway event dominates: participating passengers are
**ashore** (off-ship state — they occupy no zone) between their individual
departure and return draws inside the `port_call` window, subject to the
existing `onboard_passenger_fraction` (0.30) as the midday residual and the
`dining_demand_multiplier` for meals. The return front (last tender /
all-aboard deadline) is a `queue_event` — a correlated compression of
returning passengers at the gangway. Port-day rhythm constants are used
**only** for port-day rows (per the task instruction that the onshore GPS
corpus is usable only there).

### 4.5 Post-prandial emesis coupling

For the norovirus arm, emesis episode timing is modulated by a
post-prandial window: the per-epoch emesis hazard is multiplied by
`post_prandial_emesis_multiplier` for `post_prandial_window_minutes` after a
completed `meal_seating` participation, and by its complement elsewhere.
**This coupling is thin in the literature for norovirus specifically** — the
deeper Consensus search in this session found no norovirus-specific
meal-timing study; the mechanism is physiologically defensible via gastric
emptying / gastrocolic response (Vijayvargiya 2018 OR ≈ 2.0 for vomiting
under delayed gastric emptying; Carbone 2021 nausea elevation ~90 min
post-meal; Zelner 2013 infectiousness spike at symptom onset). It therefore
enters the register as a **`declared` wide interval flagged as a candidate
E-tier query** — the weakest defensible bound, not a sourced constant.

### 4.6 SOP conditioning (baseline → decay)

Each catalog carries `sop_variants` keyed on `protocols.json` names. The
decay process is ordered:

1. **Baseline** — documented template.
2. **Heightened sanitation** (`Surface Disinfection Protocol`, `Increased
   Diagnostic Cadence`): capacity multipliers on `open_venue` and
   `scheduled_activity`; `cleaning_rotation` frequency rises.
3. **Outbreak level** (`VSP-Threshold Mass Isolation`, `Galley Closure &
   Meal Isolation`, `Selective Passenger Confinement (Diamond Princess)`):
   buffet self-service cancelled or crew-served, shows and scheduled
   activities cancelled, port-call events suspended; dining shifts toward
   MDR/crew-served and cabin delivery for the confined subset.
4. **Confinement** (`General Confinement to Quarters`, `Replayed Cabin
   Quarantine of All Passengers`): all passenger events cancelled, meals
   delivered to cabins, `cleaning_rotation` reduced to essential passes;
   `watch_turnover` is unchanged (watches still stand).

## 5. Mapping to the failure ledgers

| Ledger measurement | Mechanism that addresses it |
|---|---|
| Per-epoch dosed sets: median 705 hosts, q95 ≈ 3,621 ≈ whole ship (COVID-TAKEOFF-ATTR-01) | **Co-presence partition**: the dosed set during an event is its attendance draw bounded by venue capacity (a Main_Theater show seats 2,000 on mega, not 7,000); between events the set is the small rolling/transit population |
| `challenged_share_of_aboard` = 1.0 on all 20 seeds | **Co-presence partition + class scoping**: crew-only venues (engine rooms, galleys, crew mess) and class-scoped eligibility mean a sick passenger can never challenge the engine-room population, so challenged share is structurally < 1 |
| Secondary vomits land in cabins whose occupants are already immune (NORO-GROWTH-01) | **Meal-cyclic emesis + sleep window + confinement conditioning**: emesis timing is modulated post-prandially and by the in-cabin curve; vomits land where the host actually is at that hour — the cabin at night, a dining venue after meals, or an event venue mid-program — not a stationary draw; under confinement the cabin landing is the *correct* behaviour |
| ~5–10% challenge fraction implied by ~197 takeoff onsets | **Egress fronts + bounded sets**: the infectious agent's per-epoch co-presence is its event cohort, so a single seeded host challenges tens–hundreds per epoch (venue-sized), reaching ship-scale exposure only by moving through successive events across days |

## 6. Constants introduced (all registered in §3.6)

| Constant | Role | Interval | Shape | Class |
|---|---|---|---|---|
| `meal_participation_fraction` (breakfast/lunch/dinner, per service type) | attendance draw per meal event | per-meal spans in catalog; declared 0.15–0.95 by service type and day type | U | C (Tr-derived windows; participation declared) |
| `event_participation_fraction` (per event class) | attendance draw | declared per class (shows 0.25–0.4; activities 0.25–0.4; open venues 0.2–0.45; muster/port-call 1.0) | U | C |
| `occupancy_share` | fraction of window inside venue | declared per class (shows 0.95; meals 0.2–0.6; open 0.2–0.5) | U | C |
| `egress_front_minutes` | pour-out front duration | [5, 20] min declared | U | ∅lit — declared |
| `corridor_transit_minutes` | transit occupancy during egress | [3, 15] min declared | U | ∅lit — declared |
| `post_prandial_emesis_multiplier` | emesis hazard multiplier inside post-meal window | [1.0, 3.0] declared; **candidate E-tier query** | U | ∅lit — declared |
| `post_prandial_window_minutes` | window length after meal end | [30, 120] min declared (Carbone ~90 min anchor) | U | B-adjacent, declared |
| `asleep_in_cabin_share(h)` | sleep-window cabin occupancy curve | ATUS share-asleep curve; night plateau [0.85, 1.0], shoulders declared | empirical | B |
| `crew_offduty_cabin_hours` | MLC rest block in cabin | [10, 14] h per 24 h (MLC 2006 Reg 2.3 floor ≥10 h; Baumler 6-on/6-off) | U | M (regulation) / B (practice) |
| `port_day_onboard_fraction(h)` | time-varying aboard share on port days | midday residual 0.15–0.45 declared around existing 0.30 default; Juneau survey (mean 5.3 h ashore, 70% tours) | U-shaped | B (port-day rows only) |
| `port_return_front_concentration` | share of ashore passengers returning in last tender hour | [0.3, 0.7] declared | U | ∅lit — declared |
| `muster_participation` | muster drill attendance | 1.0 (SOLAS mandatory) | point | M (regulation) |
| `cleaning_passes_per_day` | stateroom service frequency | 2 declared (AM service + PM turndown) | point | C (hotel convention) |
| `sop_capacity_multiplier` (per variant per class) | capacity decay under SOPs | [0.3, 1.0] declared per level | U | C (declared policy) |

## 7. What the layer does not do

- It does not fit any constant to A1/A2/A5/A8/A9 outcomes; every
  participation fraction is `declared` and wide.
- It does not change venues or topology — `venue_map` only names existing
  zones.
- It does not touch the Θ screen, the dose ledger, or anchor scoring.
- Port-day constants are used only for port-day rows; no onshore datum is
  applied to a sea-day mechanism.

## 8. Implementation posture (successor session)

Implementation is a separate session: build the rhythm engine behind a
labelled baseline (`rhythm.enabled: false` keeps today's independent-draw
behaviour byte-identical), wire `event_catalogs.json` per platform, run the
bounded Lev re-rank on the two ledger metrics (median dosed-set size should
fall toward venue scale; challenged_share should drop below 1.0; secondary
vomit placement should shift onto non-immune cabin occupancy).
