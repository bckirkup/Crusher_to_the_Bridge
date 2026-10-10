# NORO-ENTRAIN-01 sweep design

> **Status:** frozen — declared before any cell ran; the user gates image
> build, canary and every wave. Admissibility criteria below are the
> contract: a cell is scored against this document, not retro-fitted to
> an anchor.

NORO-ENTRAIN-01 measures two approved levers aimed at raising VSP
posting rates *appropriately per hull*, plus a design-note-only third
leg. It is the next stage of the measurement line after
NORO-FOOD-SCORE-01 (PR #981 readout + PR #982 early-event analysis):

- **Lever A — event shape arm.** Tests whether dose spread across more
  service windows recovers `ind`-like conversion on honest
  contamination objects.
- **Lever B — arriving-shedder proxy.** A one-voyage approximation of
  entrainment: a declared fraction of crew boards already shedding —
  mid-course, high-titer, decaying over weeks — spanning roles and
  weighted toward food handlers.
- **Design note only — full entrainment** (§7): what chained-cruise
  crew carryover would require, scored later by the proxy's effect
  size. Not built.

Deliverable of the design stage: this doc +
`campaigns/noro/noro_entrain_01/` (build.py, generated campaign.json,
manifest `noro_entrain_01_manifest.json`) + ledger row. No engine
changes are made by this design; where an arm needs engine work it is
spec'd as a **mechanism contract** (§4.3, §5.4) so a later
implementation leg is mechanical.

## 1. Settled inputs (do not re-derive)

- Anchors: VSP posting ~0.4–0.9% of voyages; posted-conditional
  reported AR 0.04–0.10 (IQR); hull-scaling compression; outbreak
  shape. No constant is fit to an anchor.
- FOOD-COMMON-SOURCE-02 is shipped and merged: contamination objects
  for provisioned-lot, handler and diner arms — autocorrelated in
  space/time, emergent pan count, multi-pan tail. v1 preserved as
  `"independent"` labelled baselines, bit-identical at draw level.
- SCORE-01 readout (`noro_food_score_01_readout.md`): honest posting
  frequency (D1 partial), burst48 signature recovered on exp (D4),
  posted-conditional AR still thin (0.014–0.021 vs ≥0.04), objects
  under-convert on cls/spr (~0–6% vs `ind`'s 13–43%
  excursion→posting).
- Early-event analysis (`noro_food_score_01_early_event_analysis.md`):
  **size is not the discriminator — seeded-draw shape is.** Object
  events of 317–959 takers convert ~0.1–0.2%; `ind` pan draws (dose
  spread over multiple windows, 26–72 takers) convert 1.4–19.5%. Min
  early-event size preceding a posting: exp none (39/117 postings had
  no early event — propagation alone crosses the low wire ~9–10
  reported pax), cls 26 takers, spr 34 takers. Frequency is not the
  bottleneck on big hulls: cls ~90%, spr ~97% of voyages already have
  ≥1 early shared-dose event. Route decomposition: provisioned lots
  dominate the events that precede postings (exp 74.6%, cls 46.6%,
  spr 27.0% of posted-voyage early events vs 3.9–10.6% of the general
  pool); ill-handler objects — the commonest source — almost never
  drive the voyage-max (3 cls, 1 spr).
- Mega (`MEGA-IMPACT-01`, v1 only): events saturate the 80-taker pan
  ceiling; best reach 0.857 of crew wire / ~0.72 of pax wire — never
  crosses. Objects were never armed on mega.
- Wires (emitted complements): exp 316/134 pax/crew → ≥10/≥5 reported;
  cls 1338/572 → ≥41/≥18; spr 2100/900 → ≥63/≥27. Emitted complements
  everywhere, not nominal.
- On exp, posting does not need food at all (postings on `off`); the
  scored question on exp is shape/AR, on cls/spr it is conversion.

## 2. What the shipped machinery already expresses

Surveyed at `13cf35a5` (post-#982 main). Config paths listed here are
verified present; none of this section assumes engine work.

### 2.1 Lot objects (provisioned-lot arm, `"object"` mode)

Extent is emergent from four draws minted once per object
(`_cs_realize_lot_object`):

| Draw | Config key | Shipped interval |
|---|---|---|
| shelf life (days the item survives) | `lot_shelf_life_days` | (1, 4) int |
| total servings budget | `lot_servings` | (30, 600) loguniform |
| per-window take share | `item_take_share` | (0.10, 0.60) uniform |
| start-day window | `embarkation_lot_window_days` | (1, 3) int |

Per window the object serves `Binomial(cohort, take_share)` demand
capped by `servings_remaining`; pan count **emerges** per window as
`ceil(servings_served / pan_servings)` at `pan_servings` (20, 80) —
not a knob for shape. Titre (`lot_titre_gec_per_g` (1e1, 1e4)
loguniform) and take-share are minted **once per object**; demand and
servings-served are per-window. Objects close on `perished`,
`exhausted`, `source_excluded`, `shedding_ended`, `voyage_end`;
`windows_covered` counts served windows. All four minted-draw keys are
`_COMMON_SOURCE_SPECS` entries → **overridable per tier via
`transmission.common_source.<key>`** (scalar or [lo,hi], fleet-wide or
per-pathogen `common_source_events.<key>`).

### 2.2 Handler/diner objects

Extent = the maximal contiguous run of shedding ∧ on-duty ∧
same-station epochs (`_cs_span_step`). One seeding draw per span at
`handler_span_contamination_probability` (0.01, 0.30) /
`diner_course_contamination_probability` (0.005, 0.15); emit zone +
strain minted once, take-share/pan-size/contacts per-window draws. The
span's length is **emergent from the agent's shedding course — no
config knob exists for agent-object extent** (a knob would be the
contract's `span_max_windows`, §4.3).

### 2.3 Boarding / initial condition

- `boarding_prevalence_points` tier coordinate: `{passenger,
  crew}` role-level prevalence, applied by the boarding axis to the
  pathogen's `initiation` block (shipped point 0.0325/0.0185).
- Boarding hosts arrive **mid-course by construction**: the
  screening-prevalence `engine_window` age draw places each import
  inside its own course and stamps `boarding_state` ∈
  {never_symptomatic, presymptomatic, symptomatic, convalescent,
  incubating, cleared} plus `time_infected` — so `bc*` arms already
  land crew in shedding states (never_symptomatic hosts in their
  shedding window, convalescents) without engine work.
- The initiation report emits `drawn_by_role` and per-state
  `composition` rows per pathogen — the arriving-shedder echo witness
  exists.
- `ship_graph.crew_immune_fraction` → `engine.crew_immune_ratio`
  (IMMUNE-ROLE-01): a crew-only embarkation-immunity fraction;
  shipped = unset → role-blind `IMMUNE_RATIO = 0.2` pool. Immune hosts
  are excluded from seeding.
- Handler-object seeding reads **live shedding state** every armed
  epoch (`_cs_source_eligible`: shedding now, not quarantined, not
  confined, on-duty). A crew host shedding at epoch 0 opens a span at
  its first on-duty epoch — **arrival shedding feeds handler-object
  seeding with no new wiring**.

### 2.4 What config cannot express (→ mechanism contracts)

- **Iso-dose spread**: shipped extent is demand-driven, so every
  config lever that lengthens an object's life also changes total
  takers. A same-expected-dose/different-window-spread arm needs a
  forced-extent draw (§4.3).
- **Seeded-draw cadence**: lot titre/take-share mint once per object;
  `ind` mints once per event. Re-minting per window is an engine
  change (§4.3).
- **Agent-object extent**: span length is shedding-course-emergent;
  capping it is an engine change (§4.3).
- **Class-weighted arriving shedding**: `boarding_prevalence_points`
  is role-level only; `explicit_seeds` is a fiat count (role-only,
  fixed dose), the symptomatic stream is role-level. No surface gives
  a galley-weighted, shedder-conditioned crew fraction (§5.4).

## 3. Frozen grid

Hulls × arms × seeds; fixed coordinates identical to
NORO-FOOD-01/02, AGE-FOOD-01 and SCORE-01 so cells pair
voyage-for-voyage where pairing is free.

### 3.1 Hulls

| Hull | Platform | Agents | Seeds (SCORE-01 list, verbatim) |
|---|---|---|---|
| exp | expedition_cruise_450 | 450 | 8000–8999 |
| cls | classic_cruise_1900 | 1910 | 8105–9104 |
| spr | spirit_cruise_3000 | 3000 | 8105–9104 |

**Mega excluded.** Lever A is definitionally unarmed there (objects
were never armed on mega; the hull runs v1 only) and v1 already
saturates its mechanism's pan ceiling short of the wire — the
measurable question on mega is post-shape, not shape. Lever B would
need the largest arriving-shedder mass of any hull to move a wire its
own mechanism cannot reach. If the cls/spr proxy effect size clears
§6.4's declared gate, mega cells are a declared extension of this
design, not a new design.

### 3.2 Arms

Baselines carried verbatim from SCORE-01 (`off`, `ind`, `ship` =
`lot_object_probability` (0.001, 0.02), handler/diner at shipped
object intervals). Every lever arm sits on the `ship` configuration —
the scored configuration is the counterfactual the levers modify.

| Arm | Meaning | Mechanism |
|---|---|---|
| `off` | whole-mechanism baseline | `common_source.mode: "off"` — no stream, bit-identical |
| `ind` | v1 labelled baseline on the current engine | all three arms `"independent"` |
| `ship` | scored shipped config | objects; lot_object_probability (0.001, 0.02) |
| `a_ext` | **Lever A**: extent multiplier | `ship` + `lot_shelf_life_days` (4, 7) |
| `a_thin` | **Lever A**: diluted spread | `ship` + `item_take_share` (0.04, 0.20) |
| `bc40` | **Lever B**: arriving shedders, low | `ship` + crew boarding prevalence 0.040 |
| `bc80` | **Lever B**: arriving shedders, high | `ship` + crew boarding prevalence 0.080 |
| `bi50` | **Lever B**: immunity carryover | `ship` + `ship_graph.crew_immune_fraction: 0.5` |
| `bmix` | **Lever B**: net-sign cell | `ship` + crew prevalence 0.080 + crew immunity 0.5 |

Arm semantics:

- `a_ext` — shipped shelf-life (1,4) d caps a lot object at ≲4 service
  days (~≤8 meal windows). (4,7) d doubles the minted-life draw at
  shipped demand, servings budget, titre and start-window. Reads as:
  more windows at the same seeded-draw shape — total takers grow with
  extent (demand-limited life). **Declared, not anchored**: chilled
  provisioned items with shelf lives inside a 12-day cruise support
  the interval; it is not chosen to move a score.
- `a_thin` — take-share (0.10,0.60)→(0.04,0.20) thins per-window
  demand ~3× at the midpoint (0.12 vs 0.35): smaller per-window
  servings, longer exhaustion-limited life, more windows per object.
  Reads the dilution direction: if conversion rides on draw count
  over extent rather than per-window mass, `a_thin` converts *above*
  `ship` at *smaller* per-window events; if per-window mass is the
  discriminator it converts *below*. Together `a_ext`/`a_thin`
  bracket the extent direction the shipped interval sits inside —
  they are the config-expressible bounds, not the iso-dose isolation
  (that is `cs_extent`, §4.3).
- `bc40`/`bc80` — crew prevalence raised to declared points 0.040 /
  0.080 (vs shipped 0.0185) with passengers pinned at 0.0325. On the
  shipped composition this lands ~5–11 arriving crew shedders on exp
  (134 crew), ~21–43 on cls, ~36–72 on spr — the one-voyage
  entrainment approximation: crew arriving off a voyage where noro
  was circulating board mid-course, weighted by the shipped class mix
  (galley is 5% of crew by construction). **Declared conflation**:
  the proxy raises *all* crew imports — it cannot distinguish
  "entrained from an outbreak voyage" from "higher community
  prevalence", and it is not handler-weighted or shedder-conditioned.
  The `arriving_shedder` contract (§5.4) is the clean separation; the
  `bc*` arms are its config expressible outer bound and run today.
- `bi50` — crew-only embarkation immunity 0.5 (shipped = role-blind
  0.2 pool): crew sail repeatedly and should carry more prior
  exposure than a first-week passenger. Pure immunity-carryover arm.
- `bmix` — the net-sign cell: shedding carryover (bc80) and immunity
  carryover (bi50) together. Reading `bmix < bc80` = immunity
  dominates; ≈ or > = shedding dominates. Both directions are in the
  grid because the net sign of entrainment is ambiguous by
  construction.

### 3.3 Seeds and pairing

1,000 seeds per cell — the SCORE-01 band-resolution argument carries:
a 0.4–0.9% posting band needs ~4–9 posted voyages per cell minimum to
resolve entry, and thin-cell declarations (§6.5) absorb the tail.
Seed lists are the SCORE-01 lists verbatim (exp 8000–8999, cls/spr
8105–9104), so every arm pairs voyage-for-voyage against the
re-run `off`/`ind`/`ship` baselines and, where the image is
identical, against the landed SCORE-01 cells. Baselines are re-run in
this campaign rather than assumed: the image is whatever main is at
submit, and any sibling default-ON mechanism landing between freeze
and submit voids bit-identity to the `40862b8c` cells — the
in-campaign baselines are the pairing surface; SCORE-01 cells are
prior evidence.

Grid total: 3 hulls × 9 arms × 1,000 = **27,000 voyages** + 48 canary.

### 3.4 Fixed coordinates (every tier)

rung `shipped`; bp32.5c18.5 except `bc40`/`bc80`/`bmix` (crew raised,
passenger pinned 0.0325); nsf29; 288 epochs (12 d); dose_adjustment
7.57; `syndromic_comp65`; embarkation 2026-01-10; `BASE_AGENT_CLASSES`
7-entry shipped mix declared verbatim on every tier (the
`agent_class_fractions` stamp); hull `num_agents` 450/1910/3000;
emitted-complement wires §1.

## 4. Lever A — event shape arm

### 4.1 What the early-event analysis measured

Under `ind`, each early shared-dose event is an independent seeded
draw — titre, take-share, serving mass fresh per event — and a
voyage's early excursion is typically *several* such draws. Under
`"object"`, a lot object's titre and take-share are minted once and
amortized across the object's whole extent: an excursion is one draw
spread over many windows. The measured conversion gap (0.1–0.2% vs
1.4–19.5%) at ~10× larger object events says the discriminator is the
*shape of the seeded draw over windows*, not the delivered mass.

### 4.2 Config arms (run today)

`a_ext` and `a_thin` (§3.2) move extent in opposite directions inside
the shipped draw grammar: `a_ext` lengthens minted life at shipped
demand (more windows, more total takers); `a_thin` thins per-window
demand and stretches exhaustion-limited life (more windows, smaller
per-window events). Neither holds expected total dose fixed — that
is precisely the gap §4.3 fills, and it is declared rather than
worked around because a config-only "normalization" would be a fitted
couple, not a declared arm.

### 4.3 Mechanism contract — `cs_extent` (spec only, no engine work here)

The iso-dose isolation and the cadence isolation both need one small
change each inside `_cs_realize_lot_object` / `_cs_object_serve`. If
implemented, the contract is:

- `transmission.common_source.lot_extent_mode`: `"emergent"` (shipped
  default) | `"declared"`. Under `"declared"`, mint draws
  `extent_windows` from a declared interval and `lot_servings` is
  distributed uniformly over that window count (per-window serving
  cap, leftover to the last window); titre minted once. Arm
  `fx_wide`: extent (12, 24) windows — same expected titre×servings
  dose, ~3–6× shipped window count. Arm `fx_narrow`: extent (2, 4)
  windows — the concentration direction.
- `transmission.common_source.lot_state_redraw`: `"per_object"`
  (shipped default) | `"per_window"`. Under `"per_window"`,
  `lot_titre_gec_per_g` and `item_take_share` re-mint at each served
  window off the same stream, extent untouched — `ind`'s lottery
  cadence on the object's autocorrelated extent. **This is the
  seeded-draw-shape discriminator arm**: if cadence is what separates
  the mechanisms, `redraw` recovers `ind`-like conversion with object
  extent intact.
- Optional companion for agent objects: `handler_span_max_windows` /
  `diner_span_max_windows` — caps the emergent span, each capped
  fragment re-draws its seeding draw. Spec'd but **not required** for
  this stage: lots drive the voyage-max on posted voyages (§1), so the
  shape question is scored on lot arms first.
- Witness fields (added by the implementation leg): `extent_mode` and
  `redraw` echoed on object rows; existing `windows_covered`,
  `servings_served`, `close_reason` and pan bookkeeping already gate
  integrity.
- Ship convention: `lot_extent_mode: "declared"` and
  `lot_state_redraw: "per_window"` are **arm knobs** — config, not
  defaults; shipped behaviour stays the default with `"emergent"` /
  `"per_object"` as the labelled baseline modes. This is an arm
  contract, not a mechanism flip — no default-ON clause applies.
- Draw-order note for the implementation leg: per-window re-mints
  must draw on the object's own stream partition so `"emergent"` /
  `"per_object"` stays bit-identical at shared seeds.

Grid extension rule: when `cs_extent` lands, the arms `fx_wide`,
`fx_narrow`, `redraw` are appended to this campaign as new blocks on
the same seed lists — they are declared here, not re-designed.

## 5. Lever B — arriving-shedder proxy

### 5.1 The gap the proxy fills

`_ImmunityAtEmbarkation`'s own docstring names it: "immunity carried
from one voyage to the next … the carried state remains a structural
gap". The shipped engine gives every host a fresh-voyage initial
condition: imports arrive via a role-level prevalence channel, and
embarkation immunity is one role-blind 0.2 pool. Real crew carry both
directions of last voyage's state — a shedding tail (high titer,
decaying over weeks) and accumulated immunity — weighted toward the
roles that seed objects and the crew wire.

### 5.2 Config arms (run today)

`bc40`/`bc80` raise the crew prevalence coordinate; `bi50` declares
the crew-only immunity carryover; `bmix` is the net-sign cell
(§3.2). The `bc*` arms are the honest outer bound: every mid-course
arrival state already exists under the shipped screening-prevalence
grammar, `drawn_by_role`/`composition` already echoes it, and
arriving shedders seed handler spans through the shipped eligibility
read — the proxy needs zero engine work.

### 5.3 Collision check (required declaration)

Candidate mechanisms surveyed for overlap with the proxy — none is
the same channel:

- `boarding_prevalence_points` — role-level only; the `bc*` arms are
  this surface, declared as the conflating outer bound (§3.2).
- `explicit_seeds` — fiat counts with role ∈ {passenger, crew} and
  fixed `infection_age_days`/dose; can mint *specific* arriving
  shedders but is not a fraction draw and not class-weighted — the
  contract extends its semantics rather than colliding with it.
- `symptomatic_stream` — role-level symptomatic arrivals under
  renewal; subset of the prevalence channel, not shedder-fractioned
  or class-weighted.
- `crew_immune_ratio`/`_ImmunityAtEmbarkation` — the complementary
  direction (immunity, not shedding); `bi50`/`bmix` arm it.
- `preboarding_assessment` — the VSP 3-day declaration screen; gates
  *symptomatic* arrivals, orthogonal to asymptomatic/mid-shedding
  carryover.

No collision found: the clean proxy is a new channel (`arriving_shedder`,
§5.4) sitting after the prevalence and immunity draws.

### 5.4 Mechanism contract — `arriving_shedder` (spec only)

If implemented, the contract is:

- Schema — `initiation.<pathogen>.arriving_shedder`:
  `{mode: "off" | "armed", crew_fraction: <scalar|draw spec>,
  class_weights: {<class_id>: weight}, arrival_age_window_days: [a,b]}`.
  `crew_fraction` is the declared carryover fraction of crew drawing
  arriving-shedding status; `class_weights` weights the draw toward
  food-handler classes (galley-armed crew are the object-seeding
  pathway *and* feed the crew wire); `arrival_age_window_days` bounds
  the drawn infection age to the mid-course shedding band (declared:
  days 3–10 post-infection — high titer, decaying, still inside the
  shedding window by construction).
- Seeded draw semantics: on the initiation stream, **after** the
  immunity pool is drawn and **after** the prevalence channel assigns
  imports — a drawn host is by construction non-immune and
  non-imported. Each eligible crew host draws `crew_fraction`
  weighted by `class_weights`; a drawn host gets
  `infect_with_pathogen(pathogen_id, 0.0, 0, time_infected =
  epochs_for_days(U(arrival_age_window_days)))` and
  `inf["boarding_state"] = "arriving_shedder"`.
- Initial-state landing: reuses the shipped mid-course boarding
  mechanism verbatim — live shedding at epoch 0, so `_cs_source_eligible`
  opens handler spans at the first on-duty epoch and diner objects
  seed identically; **no new wiring on the object side**.
- Witness fields: initiation report gains
  `arriving_shedder: {total, by_class: {<class_id>: n}, age_days: {mean,
  p90}}`; `composition` gains the `arriving_shedder` state row;
  object rows gain `source_boarding_state` so seeded spans attribute
  to arrival-shedding vs community-imported vs uninfected-at-boarding
  sources. Canary gates on all three (§8).
- Arms when implemented: `as40` / `as80` (fraction 0.04 / 0.08 with
  shipped class weights), `as80g` (0.08 with galley-weighted draw —
  the handler-pathway isolation). Appended to this campaign on the
  same seed lists, per §4.3's extension rule.

### 5.5 Interaction with immunity carryover (declared both directions)

- Shedding carryover ↑ early seed rate: more arriving shedders →
  more early handler/diner objects → more early dose events → more
  excursions that convert.
- Immunity carryover ↓ conversion: immune crew cannot be (re)seeded
  and the crew wire's susceptibles thin; net sign on posting is
  ambiguous.
- Order of draws (contract declaration): immunity pool first, then
  prevalence channel, then `arriving_shedder` — so a host is never
  both immune and an arriving shedder, and the fraction reads "of
  non-immune non-imported crew". The `bmix` config cell is the
  coarse version of the same question.

## 6. Scored criteria — pre-declared admissibility

"The wire moves" per lever, declared before any cell runs.

### 6.1 Lever A admissibility

Succeeds if, on cls and/or spr: the early-event → posting conversion
(excursion→posting rate, the §4.1 measure) rises toward the `ind`
cell's measured band (13–43%) versus `ship`'s ~0–6% **while**

- D1 posting frequency does not degrade below `ship`'s measured
  rate on the same hull,
- the D4 burst48 signature is retained on exp (postings still read
  as propagation bursts, not background accretion),
- per-window serving mass (`pw`) and the object-integrity checks of
  §6.3 hold — the arm must move *shape*, not panize dose.

`a_ext`/`a_thin` moving conversion in **opposite** directions is
itself a scored result: it reads extent as the discriminating axis
rather than draw cadence (which `cs_extent`'s `redraw` arm then
tests).

### 6.2 Lever B admissibility

Succeeds if, on the hulls where `ship` is under the 0.4–0.9% band:
`bc*` arms move posting frequency toward or into the band **while**

- posted-conditional median reported AR stays inside the 0.04–0.10
  anchor band — posting must not be bought by import pile-up (a
  voyage with ≥ wire reported imports is not an outbreak; if `bc*`
  posting scales with arriving-shedder counts rather than secondary
  yield, that is a failed proxy, reported as such),
- the D4 burst48 signature is retained — postings still show the
  burst shape, meaning propagation, not import mass, crosses the
  wire,
- `bmix` reads the net-sign question on the same terms: `bmix` vs
  `bc80` posting is the immunity-vs-shedding contrast at fixed
  prevalence.

### 6.3 Must-not-move invariants (every arm)

- `off` cells: zero common-source objects, zero witness — bit-identical
  mechanism absence.
- `ind`/`ship` cells: bit-identical to each other at shared seeds vs
  their own SCORE-01 readings *when the image matches*; otherwise the
  in-campaign baselines are the pairing surface (§3.3).
- Median voyage AR and the non-common-source route shares (contact,
  fomite, air/cabin) within pairing noise of the `ship` cell — the
  levers act on common-source shape and boarding, not on contact
  architecture.
- Object integrity: pan servings inside (20, 80); servings_served ≤
  servings budget; close_reason ∈ the legal set; `windows_covered`
  consistent with minted life on `a_ext` (≤ shipped cap on `ship`).
- Initiation bookkeeping: `composition` counts sum to `drawn_by_role`;
  screened-out tallies consistent with the shipped screen.
- `bi50`/`bmix`: immune-host count echoes the declared fraction;
  immune hosts contribute zero imports and zero seeded objects.

### 6.4 Declared extension gates

- Mega cells enter the grid only if `bc80` lifts spr posting into or
  above the 0.4–0.9% band *with* the burst signature retained —
  otherwise the hull's wire is declared unreachable by this lever and
  mega stays a v1-saturation result.
- `cs_extent`/`arriving_shedder` arms append per §4.3/§5.4 when the
  contracts land; their scored criteria are the same as their parent
  lever's.

### 6.5 Thin-cell handling

Cells posting n = 1–2 are reported **unsmoothed**: raw count out of
1,000, no CI-fitted claim, hull-pooled reads reported alongside
exactly as the SCORE-01 readout did. A lever read does not rest on a
single thin cell — admissibility needs the pooled direction plus at
least one hull with n ≥ 3.

## 7. Design note only — full entrainment (do not build)

What chained-cruise state would require, scored later by the proxy's
effect size:

1. **Voyage-boundary pathogen-state serialization.** Terminal
   infection dicts (active course position, shedding course, emesis
   schedule), immunity markers and quarantine state would have to
   survive embarkation→embarkation — the engine currently
   re-instantiates a fresh population per voyage.
2. **Turnover fraction.** A declared share of crew is replaced each
   voyage; carryover decays with the draw — the proxy's single-voyage
   fraction is the k=1 slice of that process.
3. **Run clustering.** Voyages stop being iid: a crew cohort chains
   outcomes across consecutive cruises, so seeds become
   voyage-series seeds and every readout needs chain-level
   clustering (the current census payload is per-voyage).
4. **Existing substrate**: the Presidio fleet runner already chains
   cruises mechanically (experience store), but agent-state
   persistence across voyages is new engine work.

Decision rule: if `bc80`/`as80` moves posting into band with ~10
arriving crew shedders, chained entrainment is worth the engine
cost; if the wire doesn't move at the proxy's outer bound, the fleet
story is the wrong lever and the measurement line pivots back to
shape (§4).

## 8. Canary and stop order

Smallest block set that gates the new witness fields, all on exp
(cheapest hull), then **STOP** — the user reads the canary before any
wave.

| Block | Seeds | Gates |
|---|---|---|
| `canary_exp_bc80` | 24 (8000–8023) | `drawn_by_role.crew` elevated ≈ mean 10.7 crew imports vs shipped ~2.5; `composition` carries shedding-state rows (never_symptomatic-in-window / convalescent / symptomatic); ≥1 `ill_handler` object with start_epoch ≤48 h on ≥1 voyage **and** its source attribution read — if the census payload lacks source-agent linkage, flag at canary and fold into §5.4's `source_boarding_state` witness before any wave |
| `canary_exp_a_ext` | 12 (8000–8011) | the `lot_shelf_life_days` (4,7) override echoed in run params; ≥1 lot object closing `perished` beyond the shipped 4-day cap **or** `windows_covered` > 8 — proves the extent draw reached the engine; object bookkeeping intact |
| `canary_exp_ship` | 8 (8000–8007) | shipped-config witness on the campaign image: override echo + handler/diner objects present (24-seed lot gate from SCORE-01 carried: zero lot objects in 8 seeds is P≈0.87 — the gate is the echo + agent objects, not a lot firing) |
| `canary_exp_off` | 4 (8000–8003) | zero-witness |

Local smoke before canary submission: `fl_exp_12d_scr_bc80` index 0
must show the prevalence point + class-mix stamp in run params and a
3-member zip. `drawn_by_role`/`composition` presence in the landed
payload is verified at smoke; if the census zip doesn't carry it, the
canary's Lever-B echo criterion is unmeasurable → report, don't
submit.

When `arriving_shedder` lands: `canary_exp_as80` (24) gates the
`arriving_shedder` echo block, the `arriving_shedder` composition
row, and `source_boarding_state` attribution — then STOP identically.

Wave order after a green canary: exp all arms → cls/spr `ship`,
`bc80`, `a_ext` (the highest-information cells) → remainder. Every
wave waits on the user's go.

## 9. AWS wiring (frozen at submit)

Queue `picard-campaign-queue` (Spot; On-Demand fallback only on a
>1 h Spot drought per standing convention); 1 vCPU / 4096 MB / shm
512; image tag `noro-entrain01` built off the merge SHA; s3 prefix
`campaign/noro_entrain_01/`; worker
`tools/noro_diag/growth_chain_census.py`; readout
`tools/noro_diag/outbreak_anchor_readout.py` + the early-event census
read of PR #982. 3-member zip contract (summary.json,
growth_census.json.gz, rss_samples.json) unchanged — **declared
witness shortfall**: object rows do not currently carry source-agent
boarding state; `source_boarding_state` is an `arriving_shedder`
contract deliverable (§5.4), and until it lands the bc80 canary's
seeding-attribution gate reads span start-epoch + import timing, not
per-source identity.

## 10. Report immediately if

- `drawn_by_role`/`composition` rows are absent from the landed
  campaign payload (Lever-B witness unmeasurable — canary gates it
  before any wave).
- The `crew_immune_fraction` override doesn't reach the engine
  (echo check at local smoke).
- A sibling lands a default-ON mechanism touching boarding,
  immunity or common-source draw order between freeze and submit —
  pairing expectations are re-checked and this doc's bit-identity
  clauses amended before submission.
- `a_ext` cannot mint beyond the shipped cap in practice (e.g. an
  upstream clamp on shelf life) — the arm degrades to declared
  no-op and is reported, not re-armed silently.
- Any scored cell contradicts a must-not-move invariant — stop the
  wave, report the pairing evidence.

## 11. Readout plan

`docs/norovirus/noro_entrain_01_readout.md` after the last scored
cell, written against this doc's §6 — per-hull posting rate vs the
0.4–0.9% band (emitted-complement wires), posted-conditional AR vs
0.04–0.10, excursion→posting conversion by arm and route
decomposition (the §4 route table's columns), burst48 signature on
exp, per-window serving shape on `a_ext`/`a_thin`, arriving-shedder
echo tables for `bc*`/`bmix`, must-not-move table. Measured /
inferred / hypothesis separation verbatim.

## 12. Exclusions and non-goals

No engine implementation in this stage (contracts are spec'd, not
built); no cell submission, image build or array work — the user
merges, then gates canary and waves; no mega new runs (§3.1); no
fitting language — every interval above is declared, none chosen to
move a score; no changes to any epidemiological constant.
