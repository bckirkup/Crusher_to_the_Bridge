# ROOM-AIR-01-AMBIENT-EXCHANGE-01
**Date:** 2026-11-18
**Commit:** dab0959dde7849a4812a513d4cff6f354fb66425
**Pathogens:** all
**Status:** measured
**Measured at:** 9661da333a6ad2fb8812ab1e509d9bb1cb5b7d41

## Scope

Wires [ROOM-AIR-01](ROOM-AIR-01.md)'s room-air removal map to the declared
`ambient_openings.exchange_m3h` values that the ContamX/native airflow lanes
already carry. Evidence base and owner-accepted semantics:
`docs/audits/2026-11-18_room_air_01_ambient_exchange/README.md`; owner ruling
(2026-11-18): "I think we wire now and then need to run attribution."

The map is additive, not an override: a zone's HVAC removal rate keeps its
existing `ach × hvac_duty` value (duty-0 `oa_fraction: 1.0` extract branches
still take `ach`), and each positive ambient opening adds
`sum(exchange_m3h) / volume_m3`. `exchange_m3h: 0.0` records contribute zero
and never create or replace a map entry, so the zero make-up louvres cannot
override a positive HVAC rate or the undeclared-zone sealed fallback. A null
`exchange_m3h` defers to the declared per-type axis `hvac.ambient_exchange_m3h`
and raises if neither source supplies a rate. Zones with no openings are
byte-identical: the HVAC-only map is preserved as the labelled `ambient_off`
attribution arm.

No platform data, schema, epidemiological constant, anchor fitting, campaign
array, AWS/S3, Parquet or Kosmos work changed.

## Mechanism

`build_zone_air_exchange_map(air_flow_paths, zone_volumes=...,
ambient_exchange_m3h=...)` now folds positive `ambient_openings` exchange
into the room -> ACH map. `ShipSimulation._init_transmission_core` passes the
ship zone volumes and `parse_ambient_exchange_axis(cfg["hvac"])` into that
builder and assigns the result to `TransmissionCore.zone_air_exchange_per_hour`.
The ROOM-AIR-01 consumers are unchanged: `_unit_air_exchange_rate` /
`_room_air_residence_factor` scale room-pool droplet/aerosol, cabin-mate
addback, HVAC downstream delivery, emesis aerosol, flush aerosol and
environmental-pool doses by `f(x) = (1 - e^-x) / x` at
`x = ACH * hours_per_epoch`.

## Census (measured)

`tools/room_air_ambient_exchange_attribution.py` census at the measured SHA:
74 platforms have at least one positive-exchange opening row and 283 zone rows
change; every changed row is an `open_deck` zone (the fleet note's 76
declaring platforms include zero-exchange-only records that contribute no
row). The residence-factor ratio old/new has min 10.5071, median 112.7241,
p90 218.1134 and max 585.7584. Candidate cells: `expedition_cruise_450/
PoolDeck` goes from no HVAC entry to ACH 69.9937 (factor ratio 69.9937);
`mega_cruise_5000` changes five open-deck zones with ratios 11.7053
(`CentralPark`) to 53.7887 (`Sports_Court`). Because the room-pool routes
multiply dose by that residence factor, opened-deck airborne dose falls by
the same ratio wherever those routes fire.

## Stochastic attribution

Criterion declared in the tool docstring before the runs: paired seeds on
`ambient_off` (HVAC-only) vs `ambient_on` (new map), statistic = the
`simulate_hull` COVID witness fields plus the map census; an opened-deck move
is attributed only when the residence factor falls by the declared exchange
ratio, while a stochastic move inside the 5-13% stream-disruption band with no
opened-deck dose witness is unattributed.

Runs: `greg_mortimer_2020` (`expedition_cruise_450`), `theta=1e10`, seeds
20200333/20200334, full voyage. Seed 20200333 is null on every witness field.
Seed 20200334 moves `recorded_onsets` 57 -> 67 (+10, +17.5%),
`onsets_before_split_day` +6, `onsets_on_or_after_split_day` +4,
`campaign_positives` 96 -> 104 (+8, +8.3%) and
`campaign_asymptomatic_positives` 27 -> 19 (-8), with specimens unchanged at
217. At n=2 this hull readout is not separable from RNG-stream disruption: one
seed is null and the other is outside the 13% onsets band, so this entry does
not claim a stochastic reduction from those two seeds. The attributed effect
is the dose-level residence-factor change above; a >=20-seed distribution
would be required to separate rare-event stream noise in the hull counts.

## Norovirus gate

`norwalk_gi` is `airborne_emission_mode: emesis_conditioned` with no
`airborne_emission_fraction`; under the default `profile_conditioned` droplet
emission mode `_droplet_emission_fraction` returns 0 and `_near_field_admits`
refuses it. The only remaining `_room_air_residence_factor` consumer for that
arm is the per-emesis bolus, so the declared expectation is a continuous-
airborne null. No norovirus-arm output moved in the fast-tier validation; any
future material norovirus move is a finding, not an expected consequence.

## ContamX arm

For inter-zone transport, the ContamX arm does **not** consume this ACH map or
`exchange_m3h`: `schemas/air_flow_paths.schema.json` states that
`exchange_m3h` is "Not used by the ContamX lane, which solves the flow."
`ShipSimulation._transport_airborne_pools` moves pathogen mass through
`self.contam_engine.transport_step`, where `build_transport_engine` resolves
the native `ContamTransportEngine` or the ContamX solver from the airflow
paths/layout. Independently, `ShipSimulation` still sets
`tx_core.zone_air_exchange_per_hour` for the `TransmissionCore` occupant-dose
routes regardless of `hvac.transport_engine`, so this change is a native
within-room dose-dilution factor, not a ContamX boundary condition. The
native-vs-ContamX comparison story is therefore unchanged: ContamX keeps its
own solved field for transport; ROOM-AIR-01-AMBIENT-EXCHANGE-01 changes only
the room-pool dose integral.

## Witnesses

- `pytest tests/test_cabin_corridor_transmission.py -k RoomAirRemoval`:
  9 passed, including additive exchange, zero-record inertness, null-axis
  fallback and missing-volume guards.
- `pytest tests/ -m 'not slow' -n auto -q`: 8772 passed, 6 skipped, 1 failed.
  The failure is `tests/test_sentinel_wastewater.py::test_stan_and_numpy_agree_on_the_wastewater_channel`,
  where `CmdStanModel` fails to compile
  `picard_framework/analysis/stan/sentinel_fleet.stan` (semantic error at line
  364); no Stan or wastewater file is touched here.
- `ruff check --select E,F,W,I,C901 --ignore E501,E741 --target-version py311`
  on the changed Python files: passed.
- `python3 scripts/sonar_guard.py engines/transmission_core.py picard_framework/simulation/ship_simulation.py tools/room_air_ambient_exchange_attribution.py`: passed.
- `pre-commit run --files <changed files>`: passed.
- `python3 orchestrator.py`: 24-epoch smoke completed.

Evidence: `tools/room_air_ambient_exchange_attribution.py` and `docs/audits/2026-11-18_room_air_01_ambient_exchange/evidence/ambient_exchange_attribution.json`.
