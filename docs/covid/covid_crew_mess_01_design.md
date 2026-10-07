# CREW-MESS-01 design — crew-dining attenuation under the confinement order

Status: declared, pre-run. Criteria in this file are frozen before any
cell runs; nothing below is altered after the surface is seen.

## Question

MEAL-SVC-02 landed the confined-passenger bound: `zone_narrow_svc_dir_
sect_cf_lo` (section-bound stewards, `contact_factor_to_host` drawn
U(0.005, 0.02), direction `both`) measured confined-pax median **35** ∈
[26,160] at 20/20 takeoff-conditional seeds — MAGNITUDE-LANDED
(`docs/covid/covid_meal_service_02_readout.md`). The residual it left is
the crew side: during-window crew share **0.841** vs the record's 0.29.
Attribution on those landed cells puts 44–59% of the during-window mass
in the `crew_mess` zone class, ~10–19% in `galley`, ~80–85% of routes
on `droplet`, and only ~3.6% of crew pickups on the service/caregiver
channel.

The physical claim under test: the continuing essential crew (realized
exempt share ~25–31% under SOP-017-NARROW) keep eating in open crew
messes for the whole 16-day confinement window, while the documented
Diamond Princess response was boxed and staggered crew meals. **Where
does crew-dining attenuation during the order put the crew share — and
does the confined-pax bound hold while it moves?**

## Placement mechanics (verified on the merged tree)

- Confined agents (`quarantined_ids`/`isolated_ids`) early-return to
  `home_zone` in `_place_agent` — the mess bath serves only
  **non-confined (exempt, working) crew**.
- Crew Meal tokens resolve `scheduled_token → _resolve_dining_location →
  self.dining_zone`, a fixed venue drawn at spawn capacity-weighted
  over the crew-mess catalog (`Crew_Mess_Main` 700, `CrewMess_Fwd` 350,
  `meal_seatings` 3). Galley-crew schedules carry no Meal tokens.
- The rhythm layer (`rhythm.enabled` shipped true on
  `mega_cruise_5000`) deals a crew-eligible `crew_mess` `meal_seating`
  event (window 06:00–09:30, participation 0.7, rolling egress) that
  commits diners to the mess zones ahead of the token fallback.
  SOP-017-NARROW's name does not trigger the catalog's `confinement`
  variant, so the event deals on every window day.
- Protocol modifiers reach the ship per epoch: `_step_protocols` merges
  active modifiers (`get_merged_modifiers` passes mapping values
  through) and applies them after placement — a one-epoch lag shared by
  every shipped modifier (`close_zones`, scalars, disinfection).
- `droplet_field_split` partition (far_field_share 0.175) and the
  two_box near-field table deals ride unchanged inside each mess.

## Mechanism (frozen)

A new protocol modifier key `crew_meal_service` (a mapping) declared on
SOP-017-family variants, merged like every other modifier and applied
to the engine by `apply_crew_meal_service` in `_step_protocols` —
invoked ahead of the early-return so the falling edge always clears
(same guard the disinfection meter uses). The directive is stored on
the engine and consumed at the tail of `_place_agent`, where it
redirects **crew placements that resolve into a crew-mess zone**
(the committed rhythm event and the Meal-token path land identically).
Crew whose posted `work_zone` is the mess itself are mess staff and are
never redirected — the kitchen still produces the boxes. The mechanism
draws nothing on any RNG stream: the before-window phase stays
bit-paired seed-for-seed with the open arm, and the confinement/off
arms differ only where the directive reaches.

Modes:

- `{"mode": "boxed"}` — mess dining suspended: each crew placement into
  a crew-mess zone resolves to `home_zone` (boxed meal eaten in cabin).
  Sourced rationale: the documented DP crew-meal response — meals
  distributed rather than communal mess seating.
- `{"mode": "capacity", "occupancy_fraction": F}` — a per-(zone, epoch)
  diner counter caps simultaneous mess occupancy at
  `round(F × zone.max_occupancy)`; placements past the cap resolve to
  `home_zone`. First-come ordering follows the engine's deterministic
  placement order. F = 0.10 is the declared hard corner (~105 seats
  across both messes vs ~260–330 exempt crew).
- `{"mode": "staggered", "seatings": S}` — rising-edge schedule
  surgery: every crew agent's Meal tokens move from their dealt sitting
  to sitting `agent_id % S` (position swap inside `agent.schedule`,
  seatings spread the meal block across S consecutive hours; S = 4 so
  targets never collide — crew meal blocks sit ≥5 h apart). Schedules
  restore verbatim at the falling edge. Physically: four seatings per
  meal instead of a single service.

Witnesses: every cell echoes `crew_window.crew_meal_service` —
`{mode, params, active_epochs, diner_redirects}` — where
`diner_redirects` is the count of placements diverted to `home_zone`
while the directive is active (== 0 by construction on the open arm).

## Arm semantics (fixed here before cells run)

All arms ride the verbatim CW-02 replay contract and the landed
MEAL-SVC-02 config — `direction: both`, `service_responder_mode:
"section"`, `service_section_cabins: [10, 15]`, `contact_factor_to_host:
[0.005, 0.02]` — on `scheduled_protocol_id` swaps of the SOP-017 slot.
Each new protocol is verbatim SOP-017-NARROW (unreachable
`scenario_calendar` trigger, identical `confine_all_to_quarters` +
`confinement_enforced` + `exempt_classes` + `exempt_work_zones`) plus
its `crew_meal_service` modifier:

| arm_id | protocol | `crew_meal_service` |
|---|---|---|
| `d0_svc_base` | shipped SOP-017 | absent — shipped default verbatim (empty overrides per the arm grammar); widest crew-share corner |
| `sect_mess_open` | SOP-017-NARROW | absent — landed corner verbatim; pairing base + drift witness |
| `sect_mess_boxed` | SOP-017-MESSBOX | `{mode: boxed}` |
| `sect_mess_stag4` | SOP-017-MESSSTAG | `{mode: staggered, seatings: 4}` |
| `sect_mess_cap10` | SOP-017-MESSCAP | `{mode: capacity, occupancy_fraction: 0.10}` |

5 arms × 20 seeds = **100** cells. The open arm is both the pairing base
and the drift witness against the MEAL-SVC-02 landed row
(`zone_narrow_svc_dir_sect_cf_lo`: takeoff 11/20, confined-pax 35,
during-total 238, crew share 0.841, deliveries ~162k) — NOT expected
bit-identical across intervening merges; deliveries parity and the
confined-pax band are the binding comparisons.

## Replay contract (verbatim CW-02)

`diamond_princess_2020`, `voyage_mode: declared`, SOP-017 days 16–30,
`infection_age_days` 6.8, `imports` 1, `sanitary_visit_mode`
`dwell_weighted`, seeds 20200205–20200224 (the matched 20-seed set),
`takeoff_recorded_onsets` 10, `seed_ring_readout` true, Θ7.9e6 only.

## Scoring surface (frozen)

- **Primary:** during-window crew share vs the record's 0.29 — the
  pre-run target band is declared **(0.2, 0.4)**: inside the band the
  mess channel carried the residual; above it a residual channel
  remains; below it the mechanism over-reaches.
- **Guard:** confined-pax during-window mass stays in the landed band
  ([26,160] context; median ~35) within seed-paired noise — the mess is
  a crew venue, so a passenger-side move is a shared-zone defect, not a
  finding.
- **Mechanism witness:** `during_quarantine_by_zone_class.crew_mess`
  mass falls on armed cells (ordering expectation: boxed ≪ cap10 ≈
  stag4 < open), `diner_redirects > 0` on armed cells, `== 0` on open.
- **Cadence parity:** `service_deliveries` per cell within 15% of the
  landed row's ~162k — the meal-policy seam must not move the steward
  channel.
- **During-window total** reported beside [150,350] — not gating.

## Verdict grammar (frozen)

- **MESS-CHANNEL-CLOSED** — armed arm lands crew share inside (0.2, 0.4)
  with the confined-pax band holding.
- **STILL-HIGH** — crew share moves measurably but lands > 0.4: the
  residual rides another venue (galley, work zones); the bracket narrows
  but the mess is not the whole answer.
- **OVER-CLOSED** — crew share < 0.2: the declared intervention
  over-corrects the crew channel.
- **UNMOVED** — crew share within seed-paired noise of the open arm:
  the mechanism never reached the mess (audit the echo first).
- **PAX-COLLATERAL** — confined-pax mass departs the landed band beyond
  seed-paired noise: a shared-zone defect; report immediately.

## Audit invariants (halt the readout on failure)

- `quarantine_witness` echoes on every cell: window [16,30], activated;
  `exempt_classes` the shipped four; `exempt_work_zones` echoed verbatim
  (the 11-zone list) on every arm.
- `crew_window.crew_meal_service` echoes `mode` + params + `active_
  epochs` + `diner_redirects` on every cell; absent/mismatched halts.
- `index_onset_day == -1.0`; `index_shedding_at_day0` true.
- Droplet split echo (0.175, 0.0) on every cell.
- Deliveries parity vs the landed row (~162k ±15%).
- `diner_redirects == 0` on `sect_mess_open`; `> 0` on every armed cell
  (mechanism fired).
- Passenger-side placement into crew-mess zones stays ~zero by
  construction (the redirect reads crew placements only); report any
  passenger mess occupancy drift as the shared-zone defect.
- Open arm reproduces the MEAL-SVC-02 landed row's qualitative
  behaviour (confined-pax band, crew share ~0.84 class) or the run
  reports as drift.

## Report immediately if

- The open arm doesn't reproduce the landed corner's behaviour on the
  current merge (drift) — stop and report before any array.
- Mess zones can't be attenuated without moving passenger dining
  (PAX-COLLATERAL) — a shared-zone defect to surface.
- The canary lands crew share inside (0.2, 0.4) — near-landing; stop
  and report before any further cells.
- `diner_redirects` reads 0 on an armed cell, or the echo is missing.
- Child failure rate > 5%.

## Execution (frozen)

AWS Batch via `campaigns/covid/crew_mess_01/` through `scripts/campaign`:
5 blocks × 20 seeds; jobdef `picard-covid-crew-mess-01`, image
`covid-crew-mess-01` pinned by digest built at the implementation SHA,
S3 prefix `campaign/covid_crew_mess_01/`, queue `picard-analysis-queue`
(On-Demand; Fargate fallback `picard-analysis-fargate-queue`), 1 vCPU /
2048 MB per cell.

Preflight per `campaign-preflight`: this file + the design JSON frozen
before any cell runs; local smoke on a window-retimed probe
(`scheduled_protocol_window` → days 2–3, `--num-epochs` capped) proving
the modifier reaches the mess zones (armed cell echoes the directive +
redirects > 0; output contract unchanged); `--dry-run` count = 100;
pinned image digest + jobdef revision recorded; manifest in S3; canary
`sect_mess_boxed` @Θ7.9e6 (20 seeds) read out and reported — STOP after
the canary; the full grid is the owner's call.

Canary pick (designer's choice, recorded): **`sect_mess_boxed`** — the
documented DP response and the strongest intervention; it reads the
mechanism end-to-end (event + token paths both redirected) and is the
corner where a shared-zone defect would be loudest.

## Non-goals

- No reopening of the `contact_factor_to_host` ladder or the
  uniform-vs-section question (settled by MEAL-SVC-02 — the landed
  values ride every arm verbatim).
- No crew duty/exemption machinery changes (CW-02 settled; the exempt
  set and the lottery are untouched).
- No fitting to the 0.29 record share: modes and their constants are
  declared interventions with sourced rationales, not tuned values.
- No passenger dining changes; no galley intervention (the ~10–19%
  galley channel is a separate seam).

## Rejected alternatives

- **Rhythm-catalog SOP effects** (`meal_seating@crew_mess:
  delivered_to_cabin` / `capacity_multiplier`) — the catalog variant
  would cancel the committed `crew_mess` event but cannot reach the
  Meal-token fallback that places non-committed crew in `dining_zone`;
  `meals_to_cabin` re-routes passengers only. A placement-level
  directive covers both feeders with one mechanism.
- **`close_zones` on the messes** — the order-level closer relocates
  occupants once at the epoch boundary and does not repoint future Meal
  tokens or rhythm commitments at them; a sustained close plus a
  dining-zone repoint is strictly more invasive than the diner-level
  redirect and would strand mess-posted staff.
- **`info_suppression` venue cancellation** — permanent and
  recognition-latched; the intervention must live and die with the
  order window.
- **Near-field/`droplet_field_split` scalars on mess zones** — a
  transmission-side attenuation reaches the bath but leaves occupancy
  unphysical (the mess is still full); the declared interventions are
  meal-policy changes, so they act on placement, not on dose terms.
