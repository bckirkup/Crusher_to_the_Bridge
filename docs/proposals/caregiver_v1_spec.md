# CAREGIVER-V1 — cross-pathogen caregiver mechanism spec

**Status:** Declared. **Nothing in this document describes current behaviour.**
It fixes the grammar — trigger modes, responder pools, route couplings,
reallocation semantics — and the per-pathogen factor table that every
caregiver implementation must conform to. No engine code is written here.

NORO-CAREGIVER-01 (#855, `docs/norovirus/noro_caregiver_01_design.md`) is the
norovirus instantiation of the `episode` role, already shipped default-ON.
This spec is its parent grammar: it names the shared declaration surface,
generalizes the mechanism to the three caregiver roles, and declares which
cells of the factor table each campaign is licensed to write. It is written
to be ready when the noro funnel campaign's measurements land — they refine
cells of §5, they do not conflict with it.

## 1. Grounding

Benjamin (2026-10-02): "the party mechanism remains but the caregiver roles
are different." A caregiver is a member of an ill host's committed social
structure — travelling party, cabin-mates, or service crew — whose exposure
to that host upgrades conditionally on the host's illness, and whose response
constitutes discovery of the case. The party *structure* is pathogen-neutral
(bookings, berths, service duties); the caregiver *role* is pathogen-shaped:
what the attendant walks toward, how long the exposure lasts, and which
routes it lands on all differ.

Ewald's attendant-borne argument is the evolutionary version of the same
statement: the caregiver channel preferentially propagates the courses
severe enough to need care.

## 2. The three roles

| role | trigger mode | responder pool | exposure shape | pathogens |
|---|---|---|---|---|
| R1 `cleanup` | `episode` — fires per emitted emesis event **wherever it lands** (cabin, dining room, deck — the trigger is location-agnostic) | family first: `party_member_ids ∪ cabin_mate_ids`; steward fallback when no family responder draws — the crew channel answers *emesis events*, not symptomatic persons | discrete bolus: cleanup contacts × event `surface_load` → fomite pickup → hand→mouth; the responder's class sets the **protection factor** — family grabs a napkin (factor 1.0), steward cleans with gloves/protocol (factor < 1, §5) | norwalk_gi (shipped); any future emetic course |
| R2 `tending` | `course` — binds for the host's symptomatic window | `party_member_ids ∪ cabin_mate_ids`, one designated primary responder, **age-weighted**; **no crew channel** — crew will not rush to a coughing person | sustained: elevated co-presence in the host's cabin over declared tending hours, landing on cabin-air / near-field / droplet channels | sars_cov2_resp, influenza_a |
| R3 `service` | `service` — fires per service event to a confined host | crew assigned to the cabin-service function; uniform-crew fallback — the only **crew-only** role | discrete short episode per delivery: one near-field/droplet contact per meal delivered to a confined cabin | all pathogens |

Unmodeled today: `rhythm_layer.meals_to_cabin` re-routes a confined host's
Meal tokens to `home_zone` and creates **no** crew-delivery contact — R3 is
the role that closes that gap. R2 is also unmodeled: cabin-mates are already
exempted from `confinement_isolation_factor` (`NON_MATE_CONFINEMENT_CONTACT_FACTOR`
= 0.01 applies only to non-mates), but that exemption is uniform co-presence,
not illness-conditional tending.

**Crew participation matrix** (decided 2026-10-03): R1 has a crew channel
(steward cleanup is a duty — gloves and protocol apply); R2 has none (tending
is a family behaviour); R3 is crew-only (service is a duty). The R1 crew
responder takes the *same role* — cleanup of the event — but at a discounted
exposure, because the steward follows the vomitus-cleanup procedure while the
family responder improvises a napkin and is embarrassed.

## 3. Grammar

All caregiver state lives under `transmission.caregiver` — the config tree
NORO-CAREGIVER-01 shipped; V1 owns the layout from here.

```
transmission.caregiver.mode: on | off          # on is the shipped default; off is
                                               # the labelled pre-change baseline,
                                               # draws no RNG, counter-only audit
transmission.caregiver.<role>.enabled: bool    # per-role, per-pathogen-profile
transmission.caregiver.<role>.trigger: episode | course | service
transmission.caregiver.<role>.response_probability: interval
transmission.caregiver.<role>.exposure: <role-specific factor block, §5>
transmission.caregiver.<role>.report_probability: interval
transmission.caregiver.care_response_by_host_age_band: {child, adult, elderly}  # §3 age axis
transmission.caregiver.responder_protection_factor: {family: 1.0, steward: interval}  # §3
transmission.caregiver.budget_mode: reallocate | additive   # §6
```

- **Illness trigger.** A host is *care-eligible* for R2/R3 when
  `will_present ∧ symptomatic` (the course-mode trigger is symptom onset,
  not confinement — confinement arrives late under SOP and on DP came days
  into the outbreak; gating on it would suppress the window where tending
  matters most). R1's trigger is the emitted episode itself, at whatever
  location the emesis lands. A confined, departed, or `LOCATION_ASHORE`
  responder cannot be drawn — the responder must be able to physically
  reach the host/event, matching NORO-CAREGIVER-01's exclusion.
- **Age conditioning (decided 2026-10-03).** Care-eligibility is
  **U-shaped in host age**: children and the elderly draw care; the
  working-age adult draws least. Declared as a per-age-band multiplier on
  `response_probability` (`care_response_by_host_age_band`, §5) — not a
  second trigger. The responder draw is weighted toward adults: within a
  family party the capable adult tends; an elderly spouse still responds
  when they are the only partner. On an elderly-skewed hull (DP) the age
  axis mostly collapses to adult–adult couples; on noro/family cruises it
  is the shape of the whole mechanism.
- **Per-party assignment.** R1 draws one responder per episode (shipped),
  family first, steward fallback. R2 designates **one primary caregiver**
  per ill host for the course of the illness — drawn once at symptom onset
  from the susceptible responder pool, age-weighted, stable across epochs
  (spouses do not rotate); if no susceptible pool member exists, no
  caregiver is designated. The designation ends on host recovery,
  departure, or the caregiver's own symptomatic onset (they become a
  care-eligible host themselves).
- **Responder protection factor.** The R1 responder's exposure dose is
  scaled by `responder_protection_factor`: family responder 1.0 (napkin
  cleanup — full pickup), crew steward < 1 (gloves and the documented
  vomitus-cleanup procedure attenuate hand pickup and the hand→mouth
  term). Same role, different physics per responder class.
- **Route couplings.** The caregiver dose composes through the pathogen's
  own channels with no new dose constants: R1 rides fomite pickup and
  hand→mouth as shipped; R2 multiplies the responder's cabin co-presence
  share for the tending window, which lands the upgrade on cabin-compartment
  air (AERO-CABIN-01), the near-field ring (AERO-SPLIT-01) and the
  cabin-mate droplet addback; R3 creates one bounded near-field/droplet
  episode per delivery event. Every credit flows through the standard
  accumulators under route `caregiver`, so susceptibility gates, the
  secretor gate, route attribution and the presentation draw all apply
  unchanged.
- **Discovery.** A response stamps the emitter for the next syndromic pass
  (`via: caregiver` attribution), exactly as shipped — the report bypasses
  the self-report hazard because it arrives through the attendant. Each
  role carries its own `report_probability`: the attendant's evidence of
  illness is not the same under a vomit event (R1, unambiguous) as under a
  coughing cabin-mate (R2) or a door-drop delivery (R3).
- **RNG.** Draws only under `mode: on`, on the engine stream; `off` draws
  nothing so paired-seed attribution stays clean. Deterministic: identical
  seed + config → identical event counts.

## 4. Party structure is shared, not redeclared

`party_id` / `party_member_ids` (`assign_parties`, orchestrator_init) and
`party_cabins_distribution` {1:0.75, 2:0.18, 3:0.05, 4:0.02} (Grade C,
occupancy-bounded) are shipped identity data. R2 and R3 read the same
structures; this spec adds nothing to the assignment layer. Dining-party
membership is **not** in the responder pool for R2/R3 — a table-mate checks
in; a cabin/party mate tends. Declared default.

## 5. Declared factors with provenance

Frozen before measurement per convention. Intervals are boxes, not fits;
central values are declarations.

| pathogen | role | factor | declared | grade | provenance |
|---|---|---|---|---|---|
| norwalk_gi | R1 | all constants | **incorporated by reference** — NORO-CAREGIVER-01 design doc §Constants, frozen at #855 | B/C as shipped | provisional: the funnel campaign (in flight) is licensed to refine these cells; nothing else may move them |
| norwalk_gi | R3 | `service_contact_per_delivery` | 1 near-field episode × 5 min per delivery; 3 deliveries/day | C declared | ∅ measured — nobody has timed a cabin meal drop; marked a field gap in the HIGH_TOUCH_AREA_M2 sense |
| sars_cov2_resp | R2 | `tending_copresence_multiplier` | U[1.5, 3.0], central 2.0 | C declared | Bounded **above** by the check, not fitted to it: Kordsmeyer 2022 infected cabin-mate aOR 3.27 [0.97–11.07] (Grade B, Tr) is the total cabin-mate risk the repaired structure must *reproduce* (tranche-35 rule: a check in the A5 class, never a fit input). Household SAR context: Jing 2020 13.8–19.3%, Gallagher 2023 28% — bounds plausibility only |
| sars_cov2_resp | R2 | `tending_hours_per_day` | U[2, 6] h/day | C declared | ∅ shipboard tending-time measurement exists — a field gap, declared not invented |
| sars_cov2_resp | R2 | `report_probability` | U[0.30, 0.70] per designation | C declared | DP passengers reached the medical centre through attendants and companions, not only self-assessment; interval centres "a tended case is more likely to report than a self-assessed one", consistent with the shipboard-capture bound used for noro's ceiling |
| sars_cov2_resp | R3 | `service_contact_per_delivery` | as noro R3 | C declared | same ∅-measured field gap |
| sars_cov2_resp | R3 | `report_probability` | U[0.10, 0.40] per delivery | C declared | a door-drop is weaker discovery than tending; strictly below R2's floor |
| influenza_a | R2 | all factors | same declared intervals as sars_cov2_resp, central 2.0 | C declared | household SAR literature is thinner for flu (~10–20% class); a dedicated influenza tending source is an open sourcing task — same intervals declared pending it |
| all | R2/R3 | `response_probability` | R2 U[0.50, 0.90] per designation draw; R3 deliveries always occur (p=1 — the service duty is a duty) | C declared | R2 admits "no one steps up"; R3 is duty-bound, not voluntary |
| all | R1/R2 | `care_response_by_host_age_band` | {child: ×1.5, adult: ×1.0, elderly: ×1.25} on `response_probability`, capped at 1.0 — U-shape | C declared | U-shape in who receives care (children + elderly). Direction supported by Balachandran 2023 (household AGE, n=570 primary cases): secondary transmission aOR 2.2 when the primary case was <5y, aOR 3.3 at 5–17y — Grade B for the child end; the elderly end is inferred from frailty/dependency, flagged as the weaker half. Open refinement — a dedicated caregiving-by-age source would tighten it |
| all | R1 | `responder_protection_factor` | steward U[0.3, 0.7], central 0.5; family fixed 1.0 | C declared | Gloves/procedure attenuate both fomite pickup and hand→mouth on the steward's cleanup visit; the VSP vomitus-cleanup SOP is documented practice (the duty exists), but the dose discount it produces is unmeasured — declared, flagged standing liability alongside tending_hours |

## 6. Reallocation semantics

Caregiver hours are **reallocated** contact budget, not added contact:

- R2/R3 responders' tending hours are removed from their non-ring venue
  draws in proportion (`budget_mode: reallocate`, shipped default): time
  spent in the ill host's cabin is time not spent in pooled contact
  elsewhere. The mechanism therefore concentrates the caregiver's own
  exposure onto the cabin — it does not add ship-level contact.
- R1 is exempt: a cleanup episode is minutes-scale; its reallocation would
  be unmeasurable.
- `budget_mode: additive` is the labelled alternative arm for attribution —
  it answers "is reallocation load-bearing?" without changing the default.

Directional prediction, declared before measurement: caregivers shift their
own risk from venues onto the cabin, so the channel produces cabin-clustered
secondaries (and crew-service secondaries under R3) rather than a uniform
attack-rate lift.

## 7. Supersession and the sibling campaign

- This spec owns the names: `transmission.caregiver.*`, `party_id`,
  `party_member_ids`, route label `caregiver`, `via: caregiver`, and the
  telemetry key namespace.
- NORO-CAREGIVER-01 remains the authoritative norovirus implementation. Its
  shipped config tree (`transmission.caregiver.mode` + flat sub-parameters)
  predates the role layout above; where a future noro change touches the
  same surface it converges to this grammar (per-role `enabled`, trigger
  declared per role). No immediate refactor is required — the grammar is a
  target, not a mandate to rewrite shipped code.
- The funnel re-measurement campaign in flight is **licensed to write** the
  noro cells of §5 (response probability, cleanup contacts, report
  probability) — its measured values replace the provisional intervals as
  measured entries. It is not licensed to move any respiratory cell.
- Any noro-side work beyond episode mode (e.g. an R3 service arm for
  norovirus, or an R2 course-mode arm should one ever be declared) is
  declared here, not in the sibling session's scope.

## 8. Conformance criteria for implementations

1. `mode: off` produces zero caregiver events, zero `caregiver`-route
   transmissions, zero `via: caregiver` reports — identical draws to the
   pre-mechanism tree modulo RNG order (assert counters, not bit-equality).
2. Cell payloads echo the resolved caregiver block — mode, per-role
   enabled/trigger/factor, responder counts — under `delivery.caregiver` so
   readouts can audit the declared mechanism the way `presentation_draw_mode`
   and `hand_reservoir_mode` are echoed now.
3. Route attribution under the `caregiver` label in
   `acquired_particles_by_route`, the matrix pathway breakdown, and the
   strain registry (severe-course seeding is the Ewald channel — measured
   consequence, not a parameter).
4. Telemetry counters per role per pathogen: designations, episodes,
   responses, dose delivered/credited, reports.
5. A frozen constants table per pathogen in that pathogen's design doc
   before any measurement — the NORO-CAREGIVER-01 §Constants convention.

## 9. Measurement hooks (what later campaigns score)

- **COVID (DP replay):** caregiver on/off paired seeds on the declared
  replay cells. The channel is the mechanism that can move the *shape* leg —
  cabin clustering, crew-vs-passenger split — without moving Θ; the clause
  and admissibility grammar are reused verbatim.
- **Influenza:** confined-cruise replay, secondary-attack by cabin cluster.
- **Norovirus:** the funnel re-measurement already in flight against
  CHANNEL-03's two broken links.
- **Cross-cutting audit:** caregiver share of transmissions per role —
  the >10% report-immediately bound carries over per role, not per pathogen.

## 10. Non-goals

- No engine code, no constant fitting, no Θ refit, no adoption claim.
- Noro constants are not redeclared — §5 incorporates them by reference.
- No party-level shared susceptibility (FUT2 party draws) — separate
  mechanism, separately sourced (carried from NORO-CAREGIVER-01 non-goals).
- No caregiver-mediated isolation improvement or care that shortens the
  host's own course — unmeasured, out of scope.
- No dining-party responder pool for R2/R3 (§4 declared default).

## 11. Decisions taken (2026-10-03, Benjamin) and what remains open

1. **R2 responder count — DECIDED.** One designated primary caregiver,
   matching family caregiving; the all-ring arm stays in the grammar for
   attribution only.
2. **R2 trigger floor — DECIDED.** Any symptomatic course; the skew lives
   in `response_probability` (age bands), not a harder gate. Crew does not
   respond to a coughing person — the R2 responder pool is family-only.
3. **R1 coverage — DECIDED, widened.** The episode trigger is
   location-agnostic: a public dining-room emesis draws the same response
   machinery as a cabin one (family responder if a ring member is present
   and draws, steward otherwise — the steward's gloved cleanup at
   `responder_protection_factor`, the family member's napkin at 1.0).
4. **R3 service function — DECIDED.** Cabin-service function first,
   uniform-crew fallback.
5. **R3 discovery — DECIDED.** Delivery contacts stamp the host at the R3
   report probability — the steward sees the case.
6. **Age axis — DECIDED shape.** U-shaped `care_response_by_host_age_band`
   on the host side (children + elderly elevated); adult-weighted
   responder draw on the caregiver side.
7. **Crew participation — DECIDED as a matrix.** R1 crew channel yes
   (steward, protection-discounted); R2 no; R3 crew-only.

Still open: (a) whether the R3 delivery contact on a public emesis should
*also* act as a shallow exposure channel for nearby crew who approach but
don't take the cleanup role — declared out of scope for V1, candidate for
a follow-on if the funnel campaign under-delivers; (b) the elderly end of
the age-band table is the weakest provenance cell — a dedicated
caregiving-by-age source would tighten it.
