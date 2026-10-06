# MEAL-SVC-01 design skeleton — the confinement meal-delivery channel

Status: **superseded by the frozen design — historical draft.** The
owner answered the open decisions (arms A+B, Θ7.9e6 only, replay arms
{D0_declared, ZONE_NARROW}, during-window total reported beside not
gating, section interval at declared ~10–15 cabins Grade C) and the
frozen design landed at `covid_meal_service_01_design.md` — all scoring
surface, verdict grammar and audit invariants live there. This file
stays as the arm-family survey record; nothing below binds any run.

## Question

During SOP-017 confinement on the DP replay, the **only** surviving
crew↔passenger contact is R3 cabin meal delivery
(`_caregiver_service_epoch` — one 5-minute near-field/droplet contact per
re-routed Meal token, ~3/day/host). CW-02 measured the route hot and
under-converting: 128k–166k `service_deliveries` per cell while
confined passengers acquire ~4–19 during-window infections against the
record-implied bound of ≥52, and crew share holds ~0.97 vs the record's
0.29. The flu arm measured the same machinery at fleet scale:
caregiver routes carry 49–55% of onboard-acquired infections on every
hull class (FLU-OPEN-01, #926) — when armed, this channel is
first-order.

Question for this leg: **what does the meal-delivery channel have to be
before the passenger side of the share defect closes?**

## What the engine actually offers (verified against the tree, 2026-10-06)

- **The R3 dose is one-way.** `_caregiver_service_epoch` credits the pair
  dose to the steward only — `dose > 0 and steward in _get_susceptible`
  → `_accumulate(steward, "caregiver", dose)`
  (`engines/transmission_core.py` ~9978–9990). The confined host receives
  nothing. `_caregiver_pair_dose` (~9730) computes "what a visitor
  inhales from the host's emission" — `emitted = _get_shedders([host])`,
  `target = steward`. **A shedding steward delivering to a healthy
  confined passenger delivers zero dose**: the missing passenger mass is
  not under-dosed, the direction does not exist.
- The pair-dose function is roles-swap-capable by inspection — the same
  math with (steward emits, host inhales) is a second call, not new
  dose machinery. The host-side draw would also take the host's
  susceptibility/confinement factors as target.
- **The responder draw is a uniform lottery, not a section.**
  `_draw_service_responder` (~9847) draws uniformly from all unconfined
  crew *per delivery* — `service_function_classes` is declared grammar
  but unpopulated on every shipped hull. Real DP ran assigned room-steward
  sections (~10–15 cabins each, ~3 deliveries daily): a consistent
  steward↔cabin bond that concentrates exposure on a small high-contact
  set and chains cabin-to-cabin on the steward's round. The uniform draw
  dilutes identical contact mass across all working crew — no
  steward-node amplifier, no cabin chain.
- Ready-made dials exist: `CAREGIVER_STEWARD_PROTECTION_FACTOR`
  (0.3, 0.7) attenuates the steward's pickup; `service_episode_minutes`
  (5.0) sets the near-field share; `service_report_probability` is the
  discovery stamp. CG-FLOOR-01 already certified factor-detuning impotent
  on the *pre-quarantine* caregiver leg (DELIVERY-STRUCTURAL) — factor
  arms here are subordinate probes, not the question.
- The CW-02 `crew_window` payload witness exists (confined/working
  counts, realized shares, `service_deliveries`) and extends naturally.
- The pre-quarantine caregiver suspect (ANCHOR-DERIVE-01: ~5–13
  attributed acquisitions inside days 0–4 vs the record's 34 dated mass)
  is a *different* surface — R3 only fires on confined hosts; this leg
  does not touch it.

## Candidate arm families (owner picks)

### A. Direction — `SVC_DIR` (the missing half of the pair)

`transmission.caregiver.roles.service` gains a direction grammar — e.g.
`dose_to_host: true` or `direction: "both"` (shipped default reads as
`"responder"` = status quo). Implementation is the roles-swap call:
`_caregiver_pair_dose(steward_emitting, host_inhaling, …)` credited to
the host when susceptible, under the same `caregiver` route tally (or a
`service_to_host` subkey so attribution survives). The physical claim:
a presymptomatic steward on rounds infects the passengers they serve —
exactly the crew-sheds-on-duty finding CW-01 measured.

Pros: the single most probable answer to "where are the passenger cases"
— zero new structure, one direction. Cons: if it lands, the dose it
delivers is whatever the declared 5-minute share produces — an
*existence* result that then needs the dose question (C) honestly.

### B. Structure — `SVC_SECT` (steward sections)

Replace the per-delivery uniform draw with a sticky assignment — e.g.
`service_responder_mode: "section"`: each confined host (or cabin
block) binds to a steward drawn once at first delivery (or at
confinement activation) and re-used for the voyage; optionally a small
pool per section (1–2 stewards). Concentrates exposure on the record's
working set and opens cabin-to-cabin chaining on one steward's round.

Pros: the record-faithful shape; converts "who keeps working" from a
fraction into named jobs. Cons: real mechanism work — new per-host
assignment state, new draws on the RNG stream (pairing vs CW-02
baselines needs the drift-witness pattern, not bit-identity), a
population-side roster question (does a steward class need to exist, or
is section-assignment a confinement-time structure on `crew_general`?).

### C. Dose/cadence corners — `SVC_DOSE` (subordinate)

Declared corners on `service_episode_minutes` {5, 15}, deliveries per
Meal token {1, 2}, steward protection factor ends — only meaningful
*after* the direction exists (a factor on a missing direction reads
zero everywhere). Carried cheap if A lands.

## Cells, seeds, pairing (sketch)

Replay arms carry the CW-02 result forward rather than re-measuring it:
`{D0_declared, ZONE_NARROW}` (all-crew-working corner and the landed
essential-service arm) × channel arms `{SVC_BASE, SVC_DIR, SVC_DIR+SECT}`
× θ7.9e6 × 20 seeds = 120 cells; optional θ1e6 slice adds 120 (share is
pinned 1.000 there — a lower-bound surface, not scored). Dose corners ride
only if A lands. Canary: `ZONE_NARROW × SVC_DIR` @7.9e6, 20 seeds —
the arm most likely to show the passenger side moving.

## Scoring surface and verdict grammar (sketch — freeze before cells run)

New primary surface, distinct from CW-01/02's during-median grammar:

- **Passenger during-window acquisitions** vs the record-implied bound
  ≥52 (the F13/F14 bound), takeoff-conditional.
- **Crew share** vs 0.29 — the defect's direction, not a threshold.
- **During-window total** stays reported: the honest coupling is that
  landing ~50–115 passengers on top of ZONE_NARROW's crew-driven 334
  *overshoots* [150,350] — the grammar must say whether the band still
  gates or is reported beside (owner decision 4 below; likely reported,
  because the two-sided defect cannot be scored on one total).

Verdict grammar sketch: CHANNEL-FOUND (DIR arm moves passenger
acquisitions materially toward ≥52 with deliveries parity), DOSE-EMPTY
(direction credited, acquisitions unmoved — conversion defect elsewhere,
a different address), MASS-ONLY (passenger side unmoved; the channel's
contribution stays crew-side).

## Audit invariants (sketch)

- **Direction echo**: `delivery.caregiver` resolved block echoes the
  direction on every cell; host-credited dose tally >0 iff a DIR arm —
  a missing echo is a design defect, not a sim result.
- **Realized structure witness**: distinct stewards per confined host
  per cell — uniform ≈ many (dozens), section ≈ 1–2. A SECT arm whose
  realized steward count doesn't collapse is not firing.
- **Deliveries parity**: `service_deliveries` per cell within noise of
  the CW-02 replay rows — mechanism changes must not silently change
  cadence.
- **Crew-side witness**: steward-dose credited and steward acquisition
  counts per arm — the channel is symmetric in the record; report both
  directions.
- CW-02 invariants carried: window/index/propensity/reach echoes
  unchanged.

## Report immediately if

The first DIR canary moves passenger acquisitions into the ≥52
neighbourhood (channel found — stop and report before the array); host-
credited dose is positive but acquisitions don't move (conversion is
blocked downstream — a different defect); a SECT arm's realized distinct-
steward count doesn't collapse (mechanism not armed); deliveries count
departs the CW-02 rows (cadence defect); child failure rate > 5%.

## Non-goals

- No fitting: direction/structure are declared arms; the service dose,
  episode minutes and section size stay declared Grade C — whichever arm
  lands is a magnitude to source afterward, not a constant to adopt.
- No crew subclassing — `CREW_DUTY_MIX` remains its own stage; SECT is a
  confinement-time assignment on `crew_general`, not a spawn-time roster.
- R2 tending, R1 emesis response and the pre-quarantine caregiver suspect
  are untouched — this leg is the during-quarantine service route only.
- The crew-window mass answer stands on its own: this leg does not
  re-run the CW-02 ladder.

## Required deltas before cells run (sketch)

1. `transmission.caregiver.roles.service` grammar: direction field
   (host-credited dose), optional `service_responder_mode` /
   `section_size` for SECT; resolved-block echoes for both.
2. `engines/transmission_core.py`: the roles-swap pair-dose call in
   `_caregiver_service_epoch` (host side susceptibility check +
   `_accumulate` under a distinguishable subkey); the sticky section
   assignment state (per-host steward map, drawn once, on a dedicated
   RNG stream — golden/attribution repin noted).
3. Payload witnesses: per-direction dose tallies
   (`service_dose_to_host_delivered/credited` beside the steward side),
   distinct-steward count per confined host, deliveries parity.
4. Campaign registration under `campaigns/covid/meal_service_01/`,
   design JSON with frozen admissibility, readout pairing against the
   CW-02 replay rows at `2df542ff`.

## Open decisions for the owner

1. Which arms run: A only (direction — smallest possible grid, 80 cells),
   A+B (direction + sections — 120 cells, recommended; the two are
   complementary and B without A can still only infect crew), or A+B+C
   (dose corners ride on the landed DIR arm).
2. θ scope: 7.9e6 only (the landed surface) vs both thetas (+120 cells;
   θ1e6's pinned share makes it a lower-bound reading only).
3. Replay arms: `{D0, ZONE_NARROW}` (recommended — corner + landed arm)
   vs adding FRAC_25 (+40 cells per theta).
4. How the during-window band is scored when the two-sided defect is
   being closed from the passenger side — band still gates, or reported
   beside (recommended: reported beside, flagged in the verdict).
5. Whether steward sections need a sourced section size now, or the
   declared ~10–15-cabin grade-C interval carries the arm.
