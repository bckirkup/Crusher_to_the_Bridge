# FOOD-COMMON-SOURCE-01
**Date:** 2026-10-04
**Commit:** 9b9425a6
**Pathogens:** norwalk_gi
**Status:** open

Implements the frozen design
[`docs/food_common_source_01_design.md`](../food_common_source_01_design.md):
synchronized common-source foodborne events — **one contaminated pan at
one Dining zone in one meal window** — to recover the spiky-outbreak
tail NORO-ONSET-CURVE-01 showed structurally absent (burst12>0.5 share
0.00, n=308). Food contamination is the vehicle, not noro: the mechanism
is generic end-to-end, armed per-pathogen via `common_source_events` in
the profile; `norwalk_gi` is armed in `active_profiles.json` and
`norwalk_only.json`.

## What shipped

- Three source kinds — `provisioned_lot`, `ill_handler`, `ill_diner` —
  at most one event per (zone, meal window), first fired wins, draw
  order lot → handler → diner.
- Event windows are `Meal:*` contiguous-token blocks keyed
  `(pathogen_id, zone, token, day_index)`; the lot arm picks one
  (zone, token, day) inside the embarkation span (day-index < 3) on a
  two-stage uniform draw at the first armed epoch.
- `transmission.common_source.mode`: **`on` shipped default** (the
  better physics ships on), `off` the labelled pre-mechanism baseline.
  Every draw — per-voyage rates, lot plan, per-window Bernoulli,
  take-share, titres — runs on a dedicated stream spawned
  `SeedSequence(entropy, spawn_key=(0xF00D,))` **only when armed**:
  `mode: off` and unarmed profiles draw nothing anywhere and stay
  bit-identical.
- Per-voyage rate draws happen once at init per armed pathogen — the
  between-voyage dispersion is where the outbreak tail lives.
- Cohort = the zone's assigned diners scheduled on the meal token, not
  quarantined/ashore/departed; take-share Bernoulli per cohort member,
  capped at `pan_servings` by uniform subset. Takers are credited on
  first presence in `zone_occupants[zone]` inside the window (the
  `meal_seatings` stagger) — a dose only exists where the diner
  actually ate.
- Delivery rides `_accumulate(agent_id, "common_source_food", dose, ...)`
  — the food_contamination route efficiency, host NPI and
  susceptibility merge unchanged; `PATHWAY_EFFICIENCY_KEYS` maps
  `common_source_food → food_contamination`.
- Lot pans mint an imported lineage via `strain_registry.mint(
  origin="imported:lot")` + `single_strain_mix`; handler/diner pans use
  `build_emission_mix` over the shedder's deposit.
- Deposits compose exactly as `_food_deposits`: contacts × per-contact
  transfer × hand load, depleting the hand — no new mass scale.
- `food_safety_posture`: per-platform VSP-conditioned scalar ≥ 0
  multiplying handler/diner event probabilities only (scores are
  measured, ships are not all 100%); `transmission.common_source.`
  `food_safety_posture` overrides, `lot_posture_coupling` is the
  declared extension switch (default off). Precedence: transmission
  block > platform layout > 1.0.
- Telemetry: `matrix.common_source_events` witness records (event_id,
  source kind/agent, posture, pan mass, per-serving dose, cohort,
  takers, lot titre), `matrix.common_source_exposures` per-taker rows,
  `core.common_source_telemetry` counters; both lists added to
  `simulation_history.schema.json`.

## Admissibility — all nine frozen gates verified

`tests/test_common_source_events.py` (15 tests, green):

1. `mode: off` → zero events/doses/records, no stream spawned, shared
   RNG bit-identical.
2. Unarmed profile → zero events, no stream.
3. Forced lot event has the frozen geometry (Dining zone, `Meal:*`
   token, embarkation window, full witness fields).
4. Handler arm needs a shedding agent on service duty; a quarantined
   (reported-symptomatic) handler never sources; the diner arm only
   exists at `PER_MEAL_TABLE_DINING_SERVICE_TYPES` (buffet/crew-mess),
   never at plated service.
5. Credited dose never exceeds pan mass; equals per-serving × takers
   credited.
6. Takers are dosed under the `common_source_food` pathway key.
7. Same seed → identical events and exposures.
8. Quarantined/ashore/non-cohort agents never take a serving.
9. Posture multiplies event frequency only; `food_safety_posture: 1.0`
   records 1.0 and reproduces the same draws.

## Non-goals held

No campaign run (the scoring canary is a later stage), no vibrio/
campylobacter/other profiles armed, no time-temperature growth, no
multi-lot voyages, no shared-air mass-gathering events (scaffolding
only), no embarkation-cohort arm, no observation machinery.

## Constants

Frozen constant table shipped as `COMMON_SOURCE_*_RANGE` module
constants with per-constant provenance comments; register rows in
`docs/parameter_provenance_register.md` §3.12. Per-pathogen overrides
live inside `common_source_events` (a later pathogen's literature
replaces constants, not the mechanism).
