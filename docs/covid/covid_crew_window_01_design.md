# CREW-WINDOW-01 design — the during-quarantine working-crew channel

Status: declared, pre-run. Criteria in this file are frozen before any
cell runs; nothing below is altered after the surface is seen.

## Question

The during-quarantine mass (days 16–30) is now **bracketed by two
measured corners**:

| arm (20 seeds, takeoff-conditional medians) | Θ1e6 | Θ7.9e6 |
|---|---:|---:|
| `D0_declared` — shipped SOP-017, all four crew classes exempt | 678 | 730 |
| `SOP-017-ALLHANDS` — historically false, `exempt_classes []` | 27 | 105 |
| record-informed band (NIID during-window dated mass scaled to infections) | **150–350** |  |

(D4 measured `6ea3093d`; band from `docs/covid/covid_believability_map_v1.md`.)

The truth sits strictly between the corners: DP crew really did keep
working essential service through the quarantine (so ALLHANDS is the
wrong shape — it overshoots the collapse), but the model's working-crew
channel delivers ~2–5× the record-informed mass. The question this
design answers: **which sourceable attenuation of the working-crew
channel lands the during-window median inside [150, 350] while leaving
the before-phase seed-paired unmoved?**

This is an arm-level differencing design on the verbatim
`diamond_princess_2020` replay contract, on the same grammar and grid as
D4 (`covid_quar_suppression_v1`), now also carrying the AGE-WITNESS-01
band tallies (PR #902).

## What the record and the sourcing actually offer

Four candidate mechanisms, ordered by how much of them is *sourced*
versus *declared*:

### A. Crew duty exclusion — `CREWDUTY` (sourced rule; mechanism Tr, magnitude C)

The regulated world's term for "symptomatic crew stop working": VSP 2018
Operations Manual §4.4.1.1.1 (tranche 33, **Tr** — regulatory text) makes
symptomatic crew isolation **required, unconditional and immediate** —
food employees isolated until 48 h symptom-free, nonfood 24 h — vs
passengers for whom the same manual only *advises* isolation. Three
properties matter and none is a number to fit: it attaches to the first
symptomatic crew member with no outbreak threshold (the model's only
symptomatic confinement, SOP-008, is gated at ALERT — never reached on
this replay); it removes the host from the service zones where the crew
contact machinery amplifies them; and its duration is stated by the
regulation. COVID-era caveat, declared: the cited paragraph is the
gastroenteritis (AGE) rule; the DP-era practice is the mechanism class
(symptomatic crew off duty), not the 24/48 h magnitudes, which are
carried as declared Grade C intervals {24 h, 48 h} by food status.

Model expression — needs a real protocol, not an arm trick:
`confine_symptomatic_to_quarters` exists as a modifier, but an order's
single `exempt_classes` governs both its confinement paths
(`orchestrator_epoch.py`: symptomatic confinement skips exempted
classes), so folding it into the SOP-017 slot is a no-op on exempt crew.
The record's two orders are different orders (MHLW passenger-quarantine
order vs the duty rule), so the honest shape is a **concurrent second
scheduled entry**:

- new protocol `SOP-018` in `data/config/protocols.json`:
  `confine_symptomatic_to_quarters`, `exempt_classes []`, trigger
  `scenario_calendar` (unreachable by design, like SOP-017), declared
  description: replayed crew duty exclusion, days 16–30;
- new arm key `scheduled_protocol_add` (append a schedule entry;
  ~25 lines beside `_swap_scheduled_protocol`) — D4's grammar can't
  express a second order today;
- the quarantine-witness audit then asserts BOTH orders present:
  `quarantine_witness.protocol_ids` ⊇ {SOP-017, SOP-018}.

### B. Exemption scope — `EXEMPT_ESSENTIAL` (declared counterfactual, partially sourced)

Free under the shipped grammar: a `SOP-017-ESSENTIAL` protocols entry
whose `exempt_classes` is a subset of the shipped four
(`crew_engineering`, `crew_galley`, `crew_general`, `crew_medical`),
applied by the existing `scheduled_protocol_id` swap — identical
window, identical modifiers, narrower exemption.

Sourcing for the subset: the record's phrase is "essential service" —
NIID/Yamagishi describe crew continuing meal delivery to cabins, medical
operations and engineering watches. `crew_engineering` + `crew_medical`
are unambiguous (essential in any reading); `crew_galley` likely (food
service continued — R3 service in the caregiver grammar); `crew_general`
(stewards/room attendants) is the contested class — documented crew
living in shared berths doing cabin service is the channel the record's
crew case cluster (deck-3 restaurant staff, PMC7403638) indicts.
Declared Grade C; run two variants:

- `EXEMPT_ENGMED` = {engineering, medical} — the narrow reading;
- `EXEMPT_ESSENTIAL` = {engineering, medical, galley} — the medium reading.

### C. Crew-mess far-field reach — `MESS_ATTEN` (declared ladder, Grade C — reads the attenuation function, not a fitted point)

54–58% of during-window acquisitions ride the crew_mess zone class
(D4 pooled tallies), where the pooled droplet far field challenges
hundreds of hosts per epoch — the roomful-at-once regime. The far-field
split itself is a declared Grade C liability (AERO-SPLIT-01
`far_field_share` ∈ [0.05, 0.30]). This arm is a **declared attenuation
ladder on the mess channel's effective reach**, not a refit:

- `MESS_0P5` / `MESS_0P25`: `transmission_overrides` (or
  `profile_route_efficiency_multipliers` — exact key pinned at preflight
  against the engine's actual far-field term) scaling the during-window
  mess delivery to {0.5, 0.25} of declared.
- Purpose: read the band's attenuation function — how much the
  mess-channel alone has to weaken to move the tail — as an *inverse*
  read. Whatever lands the band is a magnitude the literature must then
  corroborate (mess occupancy staggering, meal schedules), not a number
  to adopt silently.

### D. Berth compartment — named, not in this design

Tranche 35's structural suspect: the night compartment is the corridor
ward (~87 hosts/CC zone on the mega hull) with the cabin inert, and
roommate draws ignore department/shift correlation. That repair is
contact-graph restructuring — open-ledger item, too heavy for an arm.
Recorded here so the residual reads correctly: if A–C land the median
but not the role split, the berth ward is the next suspect, not another
attenuation axis.

## Cells, seeds, pairing

Grid: `{Θ1e6, Θ7.9e6}` × `{D0_declared, CREWDUTY, EXEMPT_ENGMED,
EXEMPT_ESSENTIAL, MESS_0P5, MESS_0P25}` × 20 seeds (20200205–20200224,
the matched set) = **240 cells** on the verbatim replay contract
(infection_age_days 6.8, imports 1, `dwell_weighted`, SOP-017 days
16–30). D0 rows pair seed-for-seed with every arm and double as the
drift witness against `6ea3093d` (HOST-AGE-01 merged since — the D0
delta vs the recorded row IS the armed-arm drift measurement).

## Frozen admissibility and verdict grammar

Every field DP-BELIEF-01/D4 scored is read per arm, plus the
AGE-WITNESS-01 tallies (`infections_by_age_band`,
`during_window_by_age_band`, `dated_onsets_by_age_band`) against the
NIID decade curve as a *shape witness*, never a fit target.

Per arm per theta, seed-paired vs the in-design D0 row:

- **CHANNEL-LANDED** — takeoff-conditional median
  `infections_during_quarantine` inside [150, 350] AND
  `infections_before_quarantine` unmoved within seed-paired noise AND
  during-window crew share moves measurably toward the record's 0.29.
- **UNDER-ATTENUATED** — median moves toward but stays above the band:
  report residual size, crew share, and the band-side miss.
- **OVER-ATTENUATED** — median lands below the band: joins ALLHANDS as
  too-strong; the bracket narrows but no candidate conforms.
- **UNMOVED** — seed-paired delta inside RNG-reorder noise: the arm
  never reached the channel (audit the witness echo first).

`D0_declared` is scored on the clause (T1 recorded/before-share) and
total band [712, 960]; every other arm is non-scoring context — these
are discriminating probes of a channel, not candidates to adopt
verbatim. `SOP-017-ALLHANDS` is NOT re-run: its corner is measured.

## Audit invariants (halt the campaign on failure)

- `quarantine_witness` echoes on every cell: window `[16,30]`,
  `activated` true; `exempt_classes` equals the arm's declared set
  (four classes on D0, subset on EXEMPT_*, all four on CREWDUTY/MESS_*
  — the second order confines symptomatic exempt-class members through
  its own empty exemption list; CREWDUTY cells must echo both
  protocol ids in `protocol_ids`).
- `index_onset_day == -1.0`, `index_shedding_at_day0` true on every cell.
- `propensity_draw.units_drawn > 0`; `delivery.caregiver.mode` resolves
  `on`; `presentation_draw_mode == 'once_per_course'`;
  `hand_reservoir_mode == 'hygiene_cycle'`.

## Report immediately if

Any audit invariant fails; a CREWDUTY cell echoes a missing SOP-018
order; any non-D0 arm's during-window median lands inside the band with
before-mass unmoved (a live CHANNEL-LANDED candidate — stop and report);
or child failure rate exceeds 5%.

## Non-goals

- No constant is tuned to the band or the age curve — every arm is a
  sourced rule or a declared counterfactual/ladder.
- The passenger cabin channel (D2's `dated_onsets_by_cabin_prior_case`
  witness) is a separate leg; `confined_passenger_infections_during_`
  `quarantine` vs the ≥52 bound is reported but not scored here.
- Berth-compartment restructuring (tranche 35's item) is out of scope
  for arm grammar.
- The dating overshare (D1's route-tagged dated onsets) is orthogonal.

## Required deltas before cells run

1. `data/config/protocols.json`: `SOP-018` (concurrent symptomatic-crew
   confinement) and `SOP-017-ESSENTIAL` / `SOP-017-ENGMED` (exemption
   subsets — pick exact ids at write time).
2. Arm grammar: `scheduled_protocol_add` in `ARM_OVERRIDE_KEYS` +
   `_apply_*` (appends a `scenario_schedule.protocols` entry);
   `quarantine_witness` already records `protocol_ids` plural — extend
   its audit to expect the pair.
3. The MESS arm's exact override key, pinned at preflight against the
   shipped far-field term (`transmission_overrides` vs
   `profile_route_efficiency_multipliers`).
4. Design file `picard_framework/runs/covid_crew_window_01_design.json`
   carrying this grid, the arm override blocks, and this verdict
   grammar verbatim in `admissibility`.

Execution: the campaign-preflight gate in full — local smoke proving
each override reaches the engine, dry-run count = 240, image at current
main generation, canary = one arm row (20 seeds) read out before the
array.
