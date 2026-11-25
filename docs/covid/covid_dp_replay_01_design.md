# DP-REPLAY-ENVIRON-01 — Diamond Princess behavior replay environs

> **Status:** implemented. Deliverable: a declared replay arm on the
> dedicated `diamond_princess` hull with a real-2020 activity schedule,
> confinement-era exercise outings, and a local movement-acceptance
> readout. Checkpoint B (index-only dose diagnostic) is measured — see
> ledger `DP-REPLAY-DOSE-DIAG-01`; the 12-cell theta pilot (Checkpoint C)
> is the next session's decision. Nothing here is fitted to an anchor.

Source spec: Kosmos `DP_BEHAVIOR_SPEC.md` (third-party proposal; adopted
where the engine can express it, adapted where it cannot) plus
`THETA_AFTER_BEHAVIOR.md` (external Kosmos proposal) and
`FINAL_REFERENCE_RECONCILIATION.md` / `ENGINEERING_HANDOFF.md` /
`dp_movement_ref/`.

The primary source for the 23 January clock is NIID's *Field Briefing*
corrigendum. The Hong Kong clinical case history agrees. Yamagishi et al.
report 19 January. [Index-clock evidence](../ledger/DP-INDEX-CLOCK-EVIDENCE-01.md)

## What runs

`picard_framework/runs/covid_dp_replay_01_design.json`, arms:

- `replay_baseline` — shipped `diamond_princess_2020` verbatim (mega hull,
  SOP-017 days 16–30 whole-day, journal index clock). Empty overrides per
  the arm grammar.
- `replay_niid` — the replay: dedicated hull + diamond rhythm catalog +
  real itinerary + confinement at epoch 391 + corrected NIID clock
  (`seed_patch` onset_day 3.0 = 23 Jan, infection_age_days 2.8; implied
  incubation 5.8 d unchanged).
- `replay_journal` — same environs at the journal clock (onset −1 =
  19 Jan, age 6.8) as the correction's sensitivity bracket.

### Mechanics landed

| Piece | Where | What |
|-------|-------|------|
| Hour-level SOP activation | `engines/scenario_schedule.py` | `start_hour_of_day`/`end_hour_of_day` on `ScheduledProtocol`; quarantine binds at epoch 391 (day 16, 07:00) |
| Dealing-day union | `picard_framework/simulation/ship_simulation.py` | `protocol_ids_for_day` unions protocols opening later the same day into `active_sop_names` so day 16 deals the confinement variant before modifiers bind |
| `diamond` rhythm catalog | `data/rhythm/event_catalogs.json` | `opt_in` catalog (skipped by platform matching so other dedicated-hull arms keep the labelled baseline; named by `rhythm_overrides.catalog`): `venue_map` + embarkation/sea_day/port_day templates + `diamond_confinement` sop_variant (effects + `additional_events` service routes + `exercise` block) + `passenger_disposition`. Its `platforms` list is documentation only. |
| Exercise outings | `engines/rhythm_layer.py` | `exercise_outing`/`exercise_transit`/`service_route` commitments (priority 8), `_deal_exercise` rollout/parity/willingness/caps, `outing_zone_for`, `exercise_telemetry` |
| Confined-agent release | `engines/infection_dynamics_bridge.py` | `_place_agent_epoch` honors `outing_zone_for` ahead of the home-zone override |
| Passenger disposition | `engines/rhythm_layer.py` | `location_for` claims uncommitted Free/Meal tokens at declared shares (persistent party cabin preference 0.75, outdoor 0.08, meal skip 0.55) |
| Ventilation passthrough | `orchestrator_init.py` | `cabin_ventilation_type` reaches engine zones (interior/exterior cohort proxy) |
| port_call capacity | `engines/rhythm_layer.py` | excursions skip the transit-front venue cap; the residual floor is the binding cap |
| Arm keys | `picard_framework/covid_boarding_screen.py` | `protocols_path`, `rhythm_overrides` (`catalog`, `port_day_onboard_midday_residual`, `exercise`, `passenger_disposition`); retimer covers hour fields |
| DP protocols | `data/config/protocols_covid_dp_dedicated.json` | SOP-017-DEDICATED: confinement + crew exempt + DP work zones + staggered crew mess (seatings 4) |
| Acceptance harness | `tools/dp_replay_acceptance.py` | no-transmission voyage (explicit_seeds emptied) → person-hour budgets, confinement witness, exercise telemetry |

### Declared approximations (epoch resolution)

- 45-min meals = `occupancy_share` of the window; 60-min outing dwell =
  the epoch with max overlap + 1 corridor transit epoch.
- Excursion hours: a port day declaring both `disembarkation_window` and
  `reembarkation_window` overrides the port_call template's span with the
  real excursion window (Naha: 16:00–20:00), plumbed via
  `EpochState.excursion_window_minutes`.
- Cabin occupancy is corridor-zone presence (hourly resolution; no
  stateroom interiors).
- Interior/exterior cohort = `cabin_ventilation_type`
  (`interior_hvac` vs `balcony_partial`) on the home corridor.
- Shore participation 0.50 declared (0.35/0.65 sensitivities available
  via `disembark_fraction`); port windows declared approximations.
- port_day `contact_rate_multiplier` declared neutral 1.0 — aboard
  mixing change comes from the dealt schedule and ashore absence, not
  the platform's un-measured voyage defaults.
- Crew roster is the scenario's declared `crew_general` complement;
  service routes are `participation_fraction`-dealt, not the Kosmos
  labor-model staffing solve (the spec's own declared alternative).
- Late Naha port (13:30–23:00) declared via shifted windows.
- Early-return days 14–15 (Feb 3–4) declared `sea_day` — aboard,
  routine continues.

## Acceptance readout

`python3 tools/dp_replay_acceptance.py --num-epochs 480` on the
`replay_niid` arm, no transmission (explicit_seeds emptied): person-hour
budgets vs the Kosmos sea-day targets, confinement witness at epoch 391,
port-day ashore turnout, exercise telemetry by day. Numbers live in the
ledger entry `docs/ledger/DP-REPLAY-ENVIRON-01.md`.

## Refusals

- Nothing fitted to T1/T3/T4/H5 or GM anchors; those stay held.
- The boxed_s1s2 diagnostic arm (`protocols_covid_pf_dp.json`) is
  untouched.
- No epidemiological constant changed.
