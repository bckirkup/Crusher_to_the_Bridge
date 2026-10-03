# NORO-CAREGIVER-01 design — party-mediated caregiver mechanism

Status: implemented. The constants and their intervals below were frozen
before any measurement; the mechanism shipped default-ON with `off` as
the labelled baseline. The campaign that scores it is a later stage
with its own frozen admissibility.

## Grounding

Benjamin's grounding statement (this campaign line, 2026-10-02): there
are people who move *toward* emesis and diarrhoea rather than away from
it — the family member, spouse, or caregiver who in the moment (dining
room, stateroom) rushes to clean it up and is not the sick person yet.
In the cholera literature (Ewald's attendant-borne-transmission
argument), the introduction of caregivers shifted the bacteria's
evolutionary course toward serious infection by raising transmission
from severe over mild cases.

NORO-CHANNEL-03 (measured at `d6c51c14`) found the funnel's two broken
links: infected→symptomatic at 0.17–0.41 (declared ~0.6) and
eligible→reported at 0.17–0.32 (declared ~0.4). One mechanism plausibly
feeds both: a cleanup event is a high-dose exposure on the dose physics
that already drives the symptom draw (p(ill)≈0.2 at ~50 GEC, ≈0.64 at
10^5 GEC under the Korkin/Teunis Hill pair), AND it is the discovery
moment — the person who responds has seen the case. Today neither the
transmission nor the observation side models any attendant behaviour:
confined hosts emit into their cabin's fomite pool only, and reports
are self-report hazard only. `f` (cabin-localization share) stays a
bounded null partly because cabin parties and multi-cabin parties are
confounded in every cabin-association measurement (register §3.1) — a
multi-stateroom party structure is the missing identity the confound
needs.

## Structural components

### 1. `party_id` — multi-stateroom travelling parties

New init pass `assign_parties` (orchestrator_init), called after
`assign_cabin_mates`, operating on the same `(home_zone, berth_group)`
berthing pools and recovering the dealt cabins from `cabin_mate_ids` in
the same interleaved order:

- Draw a party **cabin count** per booking from the declared
  distribution below; a party is 1–4 *contiguous cabins* inside one
  berthing pool (adjacent staterooms, as families book). Party members
  = every occupant of those cabins after `assign_cabin_mates` fills
  them in the same order.
- Fields: `agent.party_id` (int, -1 when unassigned),
  `agent.party_member_ids` (frozenset, excludes self).
- Passenger classes only. Crew berthed by department get cabin-mates
  as their responder pool (the responding colleague — crew do not
  travel in family parties; their party set is empty).
- The 4-berth family cabin already models the one-cabin large party;
  this structure adds the multi-cabin party it cannot express.
- Deterministic, in booking order, like `assign_dining_parties` —
  no RNG draws, so the arm does not perturb the engine RNG stream.

### 2. Caregiver response at emesis

Inside `_emit_emesis`, per fired episode (the discrete event the
emesis-conditioned arm already emits):

- With probability `caregiver_response_probability` (per-episode draw),
  one responder is drawn uniformly from the emitter's
  `party_member_ids ∪ cabin_mate_ids`, excluding responders who are
  confined, departed or ashore (they cannot physically reach the
  event); a mildly symptomatic party member can still respond.
- If no responder fires and the steward arm is on,
  `steward_response_probability` draws one crew steward (uniform over
  the ship's available crew) — VSP requires documented immediate
  cleanup of vomitus events.
- Episodes with an empty responder pool (solo traveller, no steward
  draw) proceed as today — no response.

### 3. Caregiver exposure

The responder's dose composes entirely from the emesis event's own
physics — no fitted scale:

- `cleanup_contacts` drawn uniform-int over the sourced interval; per
  contact the hand picks up
  `surface_load × fingerpad_share(deposition_area) × transfer_efficiency`
  reusing `_fomite_pickup_request_for_area` semantics on the bolus
  footprint (`emesis_deposition_area_m2`), then `_hand_to_mouth_dose`
  delivers the existing hand→mouth fraction. No new dose constants.
- The dose is credited through the standard epoch accumulators under
  route `caregiver` (`_accumulate` into `agent_doses` /
  `agent_pathway_doses`), and the epoch's per-pathogen challenge
  resolves infection exactly as for every other route — susceptibility,
  the secretor gate, route attribution and the dose-conditional
  presentation draw all apply unchanged. `acquired_particles_by_route`
  and the matrix pathway breakdown carry `caregiver`, so the strain
  registry counts severe-course sources correctly (the Ewald channel
  is a measured consequence, not a parameter).
- Cleanup captures the contacted share of the event's touchable mass:
  the episode's `pool_gain` is reduced by the caregiver's contacted
  surface mass (min(pool_gain, touched)) — response both exposes the
  responder and partially removes the patch. Emesis deposition records
  carry `caregiver_contacted`.
- Only susceptible responders are credited (the same gate the fomite
  route applies); an already-infected responder's exposure still loads
  their hand and, where a second lineage can establish, follows the
  standard superinfection path.
- The responder's proximity-inhalation share of the episode's
  `aerosol_load` is deliberately NOT added: the aerosol share is
  ≤2.67e-4 of the bolus, already reaches the responder through the
  zone airborne pool, and a second count would double-count it.
  Declared conservative.

### 4. Discovery → report

- At each response, draw `caregiver_report_probability` once; on a hit,
  stamp `agent.caregiver_report_due_epoch = epoch` on the **emitter**
  (the ill host). One stamp per illness (first hit wins).
- The stamp persists across epochs until the host reports through any
  channel or stops being symptomatic — the episode that prompted the
  response is over either way; a fresh emesis episode re-stamps.
  `_consume_caregiver_stamps` clears it after the syndromic pass, so a
  leftover stamp cannot leak into a later illness.
- The syndromic pass reads the stamp in `_collect_sick_call_roster`:
  a stamped, symptomatic, not-isolated agent is appended to
  `sick_call_ids`/`true_positive_ids` with `caregiver_report_ids`
  attribution, bypassing the self-report hazard and its trust
  restacking (the report arrives through the attendant, not the
  patient). `_step_biology` runs before `_step_surveillance`, so a
  same-epoch stamp reports same-epoch — the escort-to-infirmary delay
  is the epoch itself.
- Attribution is telemetry only: `caregiver_report_ids` in the
  syndromic result splits the third link by channel next campaign.

## Constants (frozen, graded)

| constant | interval / value | grade | source |
|---|---|---|---|
| `party_cabins_distribution` | {1:0.75, 2:0.18, 3:0.05, 4:0.02} default per class | C declared | No published cruise party-size distribution exists (∅, two Consensus phrasings). Bounded by occupancy arithmetic: lower-berth occupancy 105–108.5% (CCL/RCL FY2024, register §3.1) implies ~5–17% of cabins hold 3+ occupants — multi-person parties are real but their cabin count is a declaration, not a measurement. |
| `caregiver_response_probability` | U[0.40, 0.90] per episode | C declared | ∅ measured — no study reports the share of acute AGE episodes drawing an attendant inside a travelling party. Interval centres "someone usually responds when a party member vomits in their presence" and admits alone-and-unattended at the floor. |
| `caregiver_cleanup_contacts` | U-int[9, 34] per response | **B** | Overbey et al. 2021, *J Hosp Infect* (DOI 10.1016/j.jhin.2021.08.006): environmental service workers touch ~9 fomites per patient-room visit, up to 34 — a cleaning visit in a soiled room, the analogous setting. `R` (Results). |
| `steward_response_probability` | U[0.60, 0.95] when no party responder | C declared | VSP Ops Manual requires documented immediate vomitus cleanup; the compliance share is ∅. |
| `caregiver_report_probability` | U[0.20, 0.70] per response | C declared, bounded | Bounded below by community AGI care-seeking: US 19–20% (KPNW CAGE), Ireland 19.5%, Canada 20.4%, France 33% (van Cauteren 2011) — Grade B analogues — and at/above Wikswo 2011's realized shipboard capture 0.60 at the ceiling, since an *attended* case is more likely to reach the infirmary than a self-assessed one. |

## Arm modes

`transmission.caregiver.mode` — `on` (shipped default: the mechanism is
the better physics, so it ships on, per the standing convention), `off`
(the labelled pre-change baseline for paired attribution).
Sub-parameters live under `transmission.caregiver.*` and are ignored
under `off`. `parties` are assigned regardless — the structure is
identity data, not a mechanism — but nothing reads them under `off`.

## Telemetry

- Agent fields: `party_id`, `party_member_ids`,
  `caregiver_report_due_epoch` (serialized into the agent export).
- Engine counters (`core.caregiver_telemetry`): `caregiver_responses`,
  `steward_responses`, `caregiver_dose_delivered`,
  `caregiver_dose_credited`, `caregiver_reports`.
- Emesis deposition records carry `caregiver_contacted`.
- Syndromic results carry `caregiver_report_ids`.
- Infection attribution flows through the standard challenge: the
  matrix pathway breakdown and `acquired_particles_by_route` carry
  `caregiver`; strain attribution sees severe-course seeding.

## Admissibility / test gates (frozen)

1. `assign_parties` realized distribution matches the declared weights
   within sampling error across a full platform; parties occupy
   contiguous cabins inside one berthing pool; `party_id` unique per
   booking.
2. `mode: off` produces zero caregiver events, zero caregiver
   transmissions, and zero `via: caregiver` reports — identical draws
   to the pre-mechanism tree modulo RNG-stream order (assert the
   counters, not bit-equality).
3. `mode: on` with `response_probability` forced to 1.0 fires a
   response on every eligible episode; dose delivered is positive,
   scales monotonically with emesis titre (graded sensitivity), and
   never exceeds the episode's own load (dose ≤ episode_load).
4. A stamped emitter appears in `sick_call_ids` at the same-epoch
   syndromic pass with `caregiver_report_ids` attribution; unstamped
   agents report only via the existing hazard (regression: syndromic
   self-report path unchanged under `off`).
5. Cleanup reduces episode `pool_gain` by the contacted share and
   never below zero.
6. Determinism: identical seed + identical config → identical
   caregiver event count (RNG draws come off `engine.rng` under `on`;
   `off` draws nothing).

## Non-goals

- No party-level shared susceptibility (FUT2 secretor-status party
  draws) — separate mechanism, separately sourced.
- No caregiver-mediated *isolation* improvement or care that reduces
  the emitter's own duration — unmeasured, out of scope.
- No party-level dining guarantees beyond the booking order: dining
  bookings now group by `party_member_ids` (a multi-cabin family dines
  together and may straddle adjacent tables); cabins remain the
  grouping where no party exists.
- No campaign. Measurement against the CHANNEL-03 funnel is the next
  stage: canary ≥20 seeds at one cell, then stop and report.

## Report-immediately triggers

- Caregiver infection rate >10% of all transmissions at default
  intervals — would indicate the contact composition over-delivers.
- Zero caregiver responses at `response_probability` 0.9 — the
  responder pool is empty somewhere it should not be (check party
  assignment and steward arm).
- Any caregiver report arriving for an asymptomatic or non-emetic
  course — stamps only fire on emesis episodes; a mismatch is a bug.
