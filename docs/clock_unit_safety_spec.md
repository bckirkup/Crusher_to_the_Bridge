# Unit-safety specification

Authored as the implementation contract for making every time-dependent
parameter in the package unit-declared and clock-converted. Evidence:
`naked_epoch_inventory.md`, `naked_epoch_inventory_pass2.md`,
`naked_epoch_findings.md`.

Two defects found in pass 2 are not unit bugs and are listed first because they
dominate everything else.

## D1 — the diurnal schedule is not wired to the clock (highest impact)

`engines/infection_dynamics_bridge.py:1509-1510`

```python
# Representative hour for this epoch (midday activity peak)
hour = 12
```

Every epoch, for every agent, the location schedule is queried at hour 12 with
`randomness = rng.uniform(-1, 1)`, i.e. schedule indices 11-13. For
`PASSENGER_SCHEDULE` those are `Free, Meal:Lunch, Meal:Lunch`; for crew,
`Work, Work, Meal:Lunch`.

Consequences under the hourly clock:

* Passengers are in a dining zone roughly two epochs in three, for all 168
  epochs — about 112 meals per voyage instead of 21.
* Nobody ever sleeps, so cabin occupancy and the cabin-pair contact factor
  essentially never apply; cabin-mate transmission is unreachable.
* Zone occupancy is permanently concentrated in dining zones, which is also
  where the food reservoir lives — so the measured "food is 93-99.9% of
  delivered dose" is produced by this as much as by the food-pool growth bug.
* Hull classes differ in dining-zone count and size, so this is a plausible
  driver of the hull gradient in its own right.

Under the legacy clock (1 epoch = 1 day) "representative midday hour" was a
defensible simplification. It is indefensible hourly.

**Fix:** derive the hour of day from the clock —
`hour = clock.hour_of_day(epoch)` = `int(clock.hours_elapsed(epoch) + voyage_start_hour) % 24`,
keeping `12` for `legacy_epoch_day` so that arm is numerically unchanged. Keep
the `randomness` perturbation, but it must no longer be able to move the agent
across three schedule slots at hourly resolution — clamp its effect to the
current hour's slot ±0 unless the schedule explicitly models spill-over.

## D2 — contact counts are per-epoch, unit-undeclared

`_effective_contacts` returns a Poisson draw with mean
`base_contacts * (n/reference_occupancy)**exponent`, and that count is the
contacts for one epoch (`engines/transmission_core.py:1565-1600`). `base_contacts
= 1.33` and `AVG_R_POOL = [1,2,...]` are per-*day* contact counts (Korkin's
`avgR`). Hourly, every agent makes ~32 contacts/day instead of ~1.33.

**Fix:** `base_contacts_per_day`, `max_contacts_per_day`, and the legacy pool
scaled by `clock.day_fraction_per_epoch`. Note this leaves mechanism A (the
`total_shedding / n_occupants` dilution) and C (per-partner dose draws)
untouched and still open; do not conflate them with this change.

## Clock API to add (engines/sim_clock.py)

`f = hours_per_epoch / 24` (= 1.0 under `legacy_epoch_day`, so every conversion
below is the identity on that arm and legacy numerics are preserved exactly).

| Helper | Definition | Use for |
|---|---|---|
| `day_fraction_per_epoch` | `f` | linear scaling |
| `amount_per_epoch(x_per_day)` | `x * f` | costs, labour, contact counts, accruals |
| `probability_per_epoch(p_per_day)` | `1 - (1 - p) ** f` | per-agent Bernoulli draws |
| `decay_per_epoch(d_per_day)` | `1 - (1 - d) ** f` | fractional loss per step |
| `growth_factor_per_epoch(g_per_day)` | `g ** f` | multiplicative pool growth |
| `survival_from_half_life(t_half_hours)` | `0.5 ** (hours_per_epoch / t_half_hours)` | airborne/surface decay given a half-life |
| `hour_of_day(epoch, start_hour=0)` | `int(hours_elapsed(epoch) + start_hour) % 24`; `12` under legacy | D1 |
| `epochs_for_days(d)` | existing | delays authored in days |

`probability_per_epoch` and `decay_per_epoch` must clamp inputs to `[0, 1]` and
raise on negatives; `growth_factor_per_epoch` requires a factor > 0.

## Renames — every time-dependent key carries its unit

Old keys stay accepted for one release, read as the unit they were authored in
(per *day* for everything in group 1/2/3 below, per *hour* where noted), and
emit a deprecation warning. Loader-level, not call-site-level.

| Old | New | Authored grid |
|---|---|---|
| `growth_rate_per_epoch` (food) | `growth_rate_per_day` | day |
| `decay_rate_per_epoch` (food) | `decay_rate_per_day` | day |
| `colonization_rate_per_epoch` | `colonization_rate_per_day` | day |
| `spore_decay_rate_per_epoch` | `spore_decay_rate_per_day` | day |
| `exposure_probability_per_epoch` | `exposure_probability_per_day` | day |
| `SURFACE_DECAY_RATE` (module const) | profile `surface_decay_log10_per_day` + `DEFAULT_SURFACE_DECAY_LOG10_PER_DAY` | day |
| `ENV_DECAY_RATE`, `AIRBORNE_COMPOSITION_RETENTION` | profile `airborne_half_life_hours` via `survival_from_half_life` | hour |
| `baseline_surveillance_costs_per_epoch` | `baseline_surveillance_costs_per_day` | day |
| `sick_call_probability` | `sick_call_probability_per_day` | day |
| noise category `probability` | `probability_per_day` | day |
| `within_host_mutation_rate`, `recombination_rate` | `*_per_day` | day |
| wearable confounder `prevalence` | `prevalence_per_day` | day |
| `base_contacts`, `max_contacts` | `base_contacts_per_day`, `max_contacts_per_day` | day |
| `phase_durations` (epochs) | `phase_durations_days` | day |
| `incubation_epochs` | `incubation_days` | day |
| `activation_delay_epochs` | `activation_delay_hours` | see below |
| `reluctant_delay_epochs` | `reluctant_delay_hours` | hour (48 h) |
| `detection_delay_epochs` | `detection_delay_hours` | hour |
| `crew_screening_interval_epochs` | `crew_screening_interval_hours` | hour |
| `census_interval_epochs` | `census_interval_hours` | hour |
| `sampling_interval_epochs` | `sampling_interval_hours` | hour (6 h) |
| `tat_epochs` | `tat_hours` | hour |
| escalation decision delay epochs | `*_delay_hours` | hour |
| `embarkation/disembark/reembark_window_epochs` | `*_window_hours_of_day` | hour-of-day |
| `shore_infection_probability` | `shore_infection_probability_per_hour` | hour (matches Sentinel lambda_p, per person-hour) |
| `py_contam_bridge.HOURS_PER_EPOCH` | `clock.hours_per_epoch` (no constant) | hour |

Mutation on *transmission* (`mutation_rate`) is per infection event, not per
epoch — leave it alone but document it as event-scoped. Per-test diagnostic
sensitivity/specificity, per-read error rates, quarantine-compliance class
assignment (sticky, once per agent) and initialization draws are event- or
run-scoped: document, do not convert.

## Literature values

Surface persistence on hard non-porous surfaces at ~20-23 C, authored as a
log10 reduction of viable titre per day (`surface_decay_log10_per_day`), the
unit the sources measure in; `surface_fraction_per_day` in
`engines/transmission_core.py` is the one place it becomes the fractional
daily loss the clock consumes, as f = 1 - 10**-k:

| Pathogen | Value | Anchor |
|---|---|---|
| `norwalk_gi` | 0.124939 log10/d (T90 ~= 8 d) | hNV/MNV/FCV tenacity on stainless steel and plastic over 70 d at RT (Res. Note, J Food Prot); MNV-1 6.2-log loss by d30 residue-free = 0.21 log/d (Takahashi et al., PLoS ONE 2011, e21951); Verhaelen et al., Food Microbiol 2019 |
| `sars_cov2_resp` | 1.301030 log10/d | half-life 5.6 h on stainless steel (van Doremalen et al., NEJM 2020;382:1564) |
| influenza A | 1.221849 log10/d | viable 24-48 h on steel/plastic, t½ ~= 6 h (Bean et al., J Infect Dis 1982;146:47) |
| default | 0.301030 log10/d | conservative midpoint for unparameterised agents |

The old global 0.05/epoch is retained by nobody: read as per-day it is far too
slow for the respiratory agents and roughly right for norovirus; the per-pathogen
split is the actual literature statement. Norovirus 0.25/day should be carried
as a sensitivity axis (0.20-0.38 spans the two anchors).

Airborne half-life (`airborne_half_life_hours`), decay only — ventilation is
applied separately by the CONTAM/ventilation factors:

| Pathogen | Value | Anchor |
|---|---|---|
| `sars_cov2_resp` | 1.1 h | aerosol half-life 1.1 h (van Doremalen 2020) |
| influenza A | 1.5 h | aerosol persistence at moderate RH |
| `norwalk_gi` | 1.1 h | no direct anchor — flagged placeholder, sensitivity axis |

Food reservoir:

* `norwalk_gi.growth_rate_per_day = 0.0`. Viruses do not replicate in food; the
  0.3 was never biologically admissible. Same for `norovirus_gii4`.
* Bacterial foodborne agents keep their authored per-day growth
  (`vibrio` 0.5, `campylobacter` 0.2).
* `decay_rate_per_day = 0.1` retained as an explicit placeholder.

Background non-infectious sick-call load (`probability_per_day`), from
shipboard medical-encounter incidence — 15.4 physician visits per 1,000
person-days for active medical care, of which motion sickness 4.2, infections
3.5, injury 2.0 (expedition Antarctic cruises, J Travel Med 2014;21:e12126;
mainstream cruise rates are lower, so this is the conservative end):

| Category | Old (per epoch) | New (per day) |
|---|---|---|
| seasickness | 0.008 | 0.0042 |
| fatigue / other | 0.005 | 0.0030 |
| minor_injury | 0.002 | 0.0020 |

Total 0.92%/person-day, versus the 30.5%/person-day the hourly runs actually
used.

Retained values, now unit-declared rather than changed:
`sick_call_probability_per_day = 0.70`, `exposure_probability_per_day = 0.1`,
baseline surveillance $55/day + 2 labour-hours/day.

Contacts: `base_contacts_per_day = 13.4` at `reference_occupancy = 50`,
`max_contacts_per_day = 40`. Anchor: POLYMOD mean ~13 contacts/person/day
(Mossong et al., PLoS Med 2008), which supersedes Korkin's `avgR` 1-2/day —
that was an R0-calibration artefact for a well-mixed compartment with no
zones, no reservoirs and no dose-response, and it cannot be read as a contact
rate here. `exponent` stays 0.5 pending the mechanism A/C work.

Protocol activation (`activation_delay_hours`): SOP-008 6, SOP-010 6,
SOP-011 24, SOP-009 0. These were `2/2/4` epochs, ambiguous between 2-4 days
(day-authored reading) and 2-4 hours (hourly reading); neither is a literature
value. 6 h reflects the time to brief crew and place symptomatic cases in
cabins; 24 h for SOP-011 reflects the Diamond Princess interval between
decision and confinement. Flagged as a modelling choice, not a fit.

## Guard against regression

`tests/test_clock_units.py`:

1. Every conversion helper is the identity under `legacy_epoch_day`.
2. Known hourly values: `decay_per_epoch(0.05)` = 0.00213,
   `probability_per_epoch(0.70)` = 0.0489, `amount_per_epoch(55)` = 2.2917,
   `growth_factor_per_epoch(1.2)` = 1.00762, `survival_from_half_life(5.6)` =
   0.8825.
3. Source/config scan: no JSON/YAML key matching `_per_epoch$` or
   `_epochs$` outside an explicit allowlist (run-length and bookkeeping fields
   such as `total_epochs`, `num_epochs`, `default_epochs`, `active_since_epoch`),
   and no module constant matching `_(RATE|FRACTION|PROBABILITY|DECAY)$` used in
   a `*=`/`+=` statement inside a per-epoch method outside an allowlist. The
   scan must fail on new violations, with the message naming the file and key.
4. One end-to-end assertion per group: a 24-epoch hourly run and a 1-epoch
   legacy run agree to within Monte-Carlo error on food-pool mass, surface-pool
   mass, baseline cost accrued, and expected background sick calls.

## Out of scope (separate changes, do not fold in)

* Mechanism A (`total_shedding / n_occupants` dilution) and C (per-partner
  contact dose draws).
* Food-pool conservation: the pool is not depleted by the agents eating from
  it, so ingestion creates mass. Real defect, separate change.
* Droplet `concentration * volume` volume cancellation.
* Release from confinement on recovery.
* `tat_epochs = 0` in every shipped cascade tier (instantaneous lab results).
* Re-fitting `dose_adjustment`. Nothing is refit until D1, D2 and the unit
  conversions land and route shares are re-measured.
