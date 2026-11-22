# DP-REPLAY-ENVIRON-01
**Date:** 2026-11-22
**Commit:** 96971a9e
**Pathogens:** sars_cov2_resp
**Status:** measured
**Scope note:** environs only — no dose figure, no theta

## Scope

Declares the Diamond Princess 2020 behavior-replay environs as a new
`covid_dp_replay_01` design on the dedicated `diamond_princess` hull:
real itinerary, diamond rhythm catalog, hour-level confinement at epoch
391, exercise outings, NIID index clock via `seed_patch`. Design:
`docs/covid/covid_dp_replay_01_design.md`. The boxed_s1s2 diagnostic
(`protocols_covid_pf_dp.json`) is untouched. Nothing is fitted to a
scored anchor.

## Mechanics landed (all under the shipped defaults + declared arm overrides)

- `ScheduledProtocol.start/end_hour_of_day` + `protocol_ids_for_day`
  dealing-day union → confinement binds epoch 391 (5 Feb 07:00) and
  dealing day 16 uses the confinement variant before modifiers bind.
- `diamond` rhythm catalog (`opt_in`, named via
  `rhythm_overrides.catalog`; platform matching alone returns nothing so
  frozen platform-fidelity arms keep the labelled baseline): venue_map,
  embarkation/sea_day/port_day templates, `diamond_confinement` variant
  (meals-to-cabin, service routes, `exercise` block),
  `passenger_disposition` block.
- Exercise machinery: `exercise_outing`/`transit`/`service_route`
  commitments, cohort rollout by `cabin_ventilation_type`, alternate-day
  parity per travelling unit, persistent willingness, bounded parallel
  groups, `outing_zone_for` honored ahead of the home-zone override in
  `_place_agent_epoch`.
- `passenger_disposition` claims uncommitted passenger Free/Meal tokens
  (home 0.75 / outdoor 0.08 / meal-skip 0.55) so the spec's
  "passengers not overusing exterior spaces" budget is declared, not
  emergent from always-dining/always-venue defaults.
- `orchestrator_init` engine-zone projection now carries
  `cabin_ventilation_type` (previously dropped — interior cohort read 0).
- port_call excursions skip the transit-front venue cap; the voyage
  midday residual floor is the binding cap. A port day declaring both
  disembarkation and reembarkation windows deals the real excursion
  window (`EpochState.excursion_window_minutes`; Naha 16:00–20:00)
  instead of the template's generic 09:00–16:00 span.
- New arm keys: `protocols_path`, `rhythm_overrides`
  (catalog, port_day_onboard_midday_residual, exercise,
  passenger_disposition), plus hour-field retiming under
  `scheduled_protocol_window`.

## Measurement (tools/dp_replay_acceptance.py, arm `replay_niid`,
no-transmission voyage, 480 epochs, seed 20200205)

**Measured at:** 96971a9e

Pre-quarantine passenger budgets (person-h / pax / day; spec target in
parens): cabin 14.8 (15), dining 2.76 (2.25), indoor_free 3.7,
corridor 2.0, outdoor 0.9 (0.5), ashore 0.36 avg over 15 days.

Ashore fires only on the six declared port calls: Kagoshima 1,745,
Hong Kong 2,695, Chan May 2,720, Cai Lan 2,656, Keelung 2,755,
Naha 1,814 person-h (Kagoshima inside the declared 10:00–14:00
excursion window, the four middle ports 10:00–15:00, Naha 16:00–20:00).
Every sea day 0.

Confinement witness: epoch 391 fraction-at-home 0.578 (transition hour
with residual pre-declared commitments), epoch 392 1.000, epoch ≥408
1.000.

Exercise — spec §6 rollout honoured exactly: voyage_day 17 (5 Feb,
first confined day) invited 0; voyage_day 18 (6 Feb) interior cohort
only, invited 356 / attended 139, slots ≥13:30; voyage_day 19 interior
350 / 209; voyage_day 20 (8 Feb) interior + exterior invited 1,348 /
attended 607, group max 40 (cap 125). Zero-invite days still emit a
telemetry line.

Crew mess: all meal_seating events seatings=4 staggered with `rolling`
egress so `synchronized_end` cannot claim the corridor epoch.

## Declared approximations / deviations vs the Kosmos spec

- Hourly epochs: 45-min meal = occupancy_share; 60-min dwell =
  best-overlap epoch + 1 corridor transit epoch.
- Shore participation effective ~0.40 (declared 0.50 minus party
  propensity draws); windows are declared approximations.
- Crew service routes are `participation_fraction`-dealt, not the
  Kosmos labor-model staffing solve (spec's own allowed alternative).
- `contact_rate_multiplier` on port days declared neutral 1.0.
- Cabin-classed hours = corridor-zone presence (no stateroom interiors).

## What is open (successor session)

- Checkpoint B local dose diagnostic on `replay_niid`, then the 12-cell
  theta pilot at the declared shortlist; GM transfer after DP.
- Every prior DP/GM replay dose figure stays withdrawn at its own
  `Measured at` SHA (see `covid_open_ledger.md` §1).
