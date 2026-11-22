# DP-REPLAY-ENVIRON-01
**Date:** 2026-11-22
**Commit:** 4f92bd69
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
- `diamond` rhythm catalog: venue_map, embarkation/sea_day/port_day
  templates, `diamond_confinement` variant (meals-to-cabin, service
  routes, `exercise` block), `passenger_disposition` block.
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
  midday residual floor is the binding cap.
- New arm keys: `protocols_path`, `rhythm_overrides`
  (port_day_onboard_midday_residual, exercise, passenger_disposition),
  plus hour-field retiming under `scheduled_protocol_window`.

## Measurement (tools/dp_replay_acceptance.py, arm `replay_niid`,
no-transmission voyage, 480 epochs, seed 20200205, at branch head)

Pre-quarantine passenger budgets (person-h / pax / day; spec target in
parens): cabin 13.3 (15), dining 2.55 (2.25), indoor_free 3.4,
corridor 1.8, outdoor 0.81 (0.5), ashore 0.62 avg.

Ashore fires only on the six declared port calls (Kagoshima, Hong Kong,
Chan May, Cai Lan, Keelung, Naha): ~4.2–4.6k person-h/day ≈ ~1,050 pax
× ~4 h inside the 09:00–16:00 window; every sea day 0.

Confinement witness: epoch 391 fraction-at-home 0.556 (transition hour),
epoch 392 0.986, epoch ≥408 0.9996.

Exercise (interior `interior_hvac` first, exterior `balcony_partial`
at offset 2): day_offset 0 (voyage_day 17, 6 Feb, slots ≥13:30)
invited 356 interior / attended 165; offset 1 invited 350 / 184;
offset 2 (8 Feb) invited 1,348 / 680; offset 3 1,318 / 685. Groups
12/day, max size ≤75 (cap 125). ~49% willingness observed. Interior
cohort size ~710 pax ≈ inside-cabin complement.

Quarantine-segment pax: ~25.5 h/day cabin-classed, 0.3 h outdoor
(exercise), ≤0.3 h corridor. Crew: 26.6 cabin, 2.55 dining (staggered
crew mess, seatings 4), 1.7 indoor free.

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
